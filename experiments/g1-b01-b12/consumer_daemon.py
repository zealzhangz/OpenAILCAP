"""B12 research-only durable background B2 -> real Saltcorn native projector.

Controller holds a source pull token; Saltcorn UID only receives JSON batch
on stdin. Controller currently requires CI sudo runuser privilege to start
native worker: this is NOT a production privilege-separated service design.
Native SQLite receipt/cursor is the checkpoint; never persist an independent
ahead-of-native checkpoint. Each poll audits *all* mapped derived rows even
when there are no new events, then pulls a bounded batch and atomically applies.
Source outage and worker crashes are retried, no silent cursor advancement.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PREFIX="S1_B12_"
ALLOWED_STATES={"STARTING","CAUGHT_UP","APPLIED","SOURCE_UNAVAILABLE",
                "NATIVE_UNAVAILABLE","DERIVED_DRIFT","STOPPING"}


class Failed(Exception):
    def __init__(self,code):
        self.code=code
        super().__init__(code)


def run_native(config,script,extra=(),payload=None):
    argv=["sudo","-n","runuser","-u",config["nativeUser"],"--",
          sys.executable,config["sourceDir"]+"/"+script,
          "--db",config["nativeDb"],*extra]
    try:
        result=subprocess.run(argv,input=payload,text=True,
                              capture_output=True,timeout=10)
    except (OSError,subprocess.TimeoutExpired):
        raise Failed("NATIVE_WORKER_UNAVAILABLE") from None
    if result.returncode:
        if "NATIVE_DERIVED_ROW_DRIFT" in result.stdout or (
            "DERIVED_DRIFT" in result.stdout
        ):
            raise Failed("DERIVED_DRIFT")
        raise Failed("NATIVE_WORKER_REJECTED")
    for line in result.stdout.splitlines():
        if line.startswith(PREFIX):
            return json.loads(line.partition("|")[2])
    raise Failed("NATIVE_WORKER_NO_RESULT")


def pull(config,after):
    request=Request(config["sourceUrl"],
                    data=json.dumps({"after":after,"limit":20}).encode(),
                    headers={"Content-Type":"application/json",
                             "Authorization":"Bearer "+config["token"]},
                    method="POST")
    try:
        with urlopen(request,timeout=3) as response:
            if response.status!=200:
                raise Failed("SOURCE_UNAVAILABLE")
            result=json.loads(response.read(128*1024))
    except (HTTPError,URLError,OSError,TimeoutError,ValueError):
        raise Failed("SOURCE_UNAVAILABLE") from None
    if (not isinstance(result,dict) or
        result.get("app")!="app-a" or result.get("after")!=after or
        type(result.get("head")) is not int or
        result["head"]<after or not isinstance(result.get("events"),list) or
        len(result["events"])>20):
        raise Failed("SOURCE_RESPONSE_INVALID")
    if result["head"]>after and not result["events"]:
        raise Failed("SOURCE_MISSING_EVENTS")
    return result


def step(config):
    audit=run_native(config,"audit_native.py")
    if not audit.get("clean"):
        raise Failed("DERIVED_DRIFT")
    state=run_native(config,"native_checkpoint.py")
    cursor=state["lastSeq"]
    source=pull(config,cursor)
    if not source["events"]:
        return {"state":"CAUGHT_UP","cursor":cursor,
                "head":source["head"],"lag":0,"applied":0}
    batch={"app":"app-a","after":cursor,"events":source["events"]}
    result=run_native(config,"native_apply.py",
                      payload=json.dumps(batch))
    after=result["lastSeq"]
    if after<cursor or after>source["head"]:
        raise Failed("CONSUMER_CURSOR_INVALID")
    return {"state":"APPLIED","cursor":after,
            "head":source["head"],"lag":source["head"]-after,
            "applied":result["applied"]}


def write_status(path,data):
    # No token, native env or authority DB path ever written to status.
    data={"state":data["state"],"cursor":data.get("cursor"),
          "head":data.get("head"),"lag":data.get("lag"),
          "applied":data.get("applied",0),
          "failures":data.get("failures",0),
          "pid":os.getpid(),"timestamp":time.time()}
    tmp=path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data,sort_keys=True)+"\n")
    os.chmod(tmp,0o600)
    os.replace(tmp,path)


def validate_config(cfg):
    if set(cfg)!={"sourceUrl","token","nativeUser","nativeDb",
                 "sourceDir","intervalMs"}:
        raise Failed("CONFIG_INVALID")
    if (not cfg["sourceUrl"].startswith("http://127.0.0.1:") or
        not cfg["sourceUrl"].endswith("/v4/apps/app-a/projection/pull") or
        len(cfg["token"])<24 or cfg["nativeUser"]!="ailcapb12salt" or
        not cfg["nativeDb"].startswith("/tmp/s1-b12-project-") or
        "/runtime-private/projection-v1.sqlite" not in cfg["nativeDb"] or
        not cfg["sourceDir"].endswith("/g1-b01-b12") or
        type(cfg["intervalMs"]) is not int or not 50<=cfg["intervalMs"]<=2000):
        raise Failed("CONFIG_INVALID")


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--config",required=True)
    p.add_argument("--status",required=True)
    args=p.parse_args()
    cfgpath=Path(args.config)
    if cfgpath.stat().st_mode & 0o077:
        raise SystemExit("CONFIG_NOT_PRIVATE")
    cfg=json.loads(cfgpath.read_text())
    validate_config(cfg)
    status=Path(args.status)
    if status.parent.stat().st_mode & 0o077:
        raise SystemExit("STATUS_DIR_NOT_PRIVATE")
    stop=False
    def on_stop(_sig,_frame):
        nonlocal stop
        stop=True
    signal.signal(signal.SIGTERM,on_stop)
    signal.signal(signal.SIGINT,on_stop)
    write_status(status,{"state":"STARTING"})
    failures=0
    last={}
    while not stop:
        try:
            last=step(cfg)
            failures=0
        except Failed as e:
            failures+=1
            last={"state":("DERIVED_DRIFT" if e.code=="DERIVED_DRIFT"
                           else "SOURCE_UNAVAILABLE" if
                           e.code.startswith("SOURCE_")
                           else "NATIVE_UNAVAILABLE"),
                  "error":e.code}
        last["failures"]=failures
        write_status(status,last)
        # Bounded retry delay; no retry spin. No token in logs.
        time.sleep(min(cfg["intervalMs"]/1000*max(1,failures),1.0))
    write_status(status,{"state":"STOPPING","failures":failures})
    return 0


if __name__=="__main__":
    raise SystemExit(main())
