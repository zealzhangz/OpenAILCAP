"""B13 real unprivileged consumer UID over constrained AF_UNIX IPC.

The Consumer has no sudo privileges, no direct Saltcorn DB access, and no
Kernel DB access. It sends bounded JSON batches over an OS-ACL and peer-UID
gated socket to a Saltcorn-UID native broker. Compromised Consumer can still
forge source events: B2 source event hashes are not signatures.
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
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PREFIX="S1_B13_"
ALLOWED_STATES={"STARTING","CAUGHT_UP","APPLIED","SOURCE_UNAVAILABLE",
                "NATIVE_UNAVAILABLE","DERIVED_DRIFT","STOPPING"}


class Failed(Exception):
    def __init__(self,code):
        self.code=code
        super().__init__(code)


def run_native(config,script,extra=(),payload=None):
    ops={"audit_native.py":"audit",
         "native_checkpoint.py":"checkpoint",
         "native_apply.py":"apply"}
    if script not in ops or extra:
        raise Failed("NATIVE_OPERATION_FORBIDDEN")
    command={"op":ops[script]}
    if payload is not None:
        if ops[script]!="apply":
            raise Failed("NATIVE_PAYLOAD_NOT_ALLOWED")
        try:command["batch"]=json.loads(payload)
        except ValueError:raise Failed("NATIVE_PAYLOAD_INVALID") from None
    try:
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as conn:
            conn.settimeout(3)
            conn.connect(config["nativeSocket"])
            conn.sendall((json.dumps(command,separators=(",",":"))+"\n").encode())
            with conn.makefile("rb") as stream:
                raw=stream.readline(131073)
        if len(raw)>131072 or not raw.endswith(b"\n"):
            raise Failed("NATIVE_RESPONSE_INVALID")
        result=json.loads(raw)
    except (OSError,TimeoutError,ValueError):
        raise Failed("NATIVE_WORKER_UNAVAILABLE") from None
    if not isinstance(result,dict) or set(result) not in (
        {"ok","result"},{"ok","error"}
    ):
        raise Failed("NATIVE_RESPONSE_INVALID")
    if result["ok"] is not True:
        raise Failed("DERIVED_DRIFT" if result.get("error")==
                     "NATIVE_DERIVED_ROW_DRIFT" else
                     "NATIVE_WORKER_REJECTED")
    return result["result"]


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
    if set(cfg)!={"sourceUrl","token","nativeSocket","intervalMs"}:
        raise Failed("CONFIG_INVALID")
    if (not isinstance(cfg["sourceUrl"],str) or
        not cfg["sourceUrl"].startswith("http://127.0.0.1:") or
        not cfg["sourceUrl"].endswith("/v4/apps/app-a/projection/pull") or
        not isinstance(cfg["token"],str) or len(cfg["token"])<24 or
        not isinstance(cfg["nativeSocket"],str) or
        not cfg["nativeSocket"].startswith("/tmp/s1-b13-project-") or
        not cfg["nativeSocket"].endswith("/ipc/consumer.sock") or
        type(cfg["intervalMs"]) is not int or
        not 50<=cfg["intervalMs"]<=2000):
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
