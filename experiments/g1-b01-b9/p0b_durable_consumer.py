"""G1 P0-B real unprivileged durable B14 signed source consumer.

Reuses the existing B14 pull/IPC step: no sudo, Kernel key/DB nor Native
SQLite access; Native UID signed broker persists cursor+receipts together
with rows in one transaction. Daemon restarted -> checkpoint retrieved
from Native, NOT an unsafe local cursor. 100ms bounded retry on outages.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import signal
import sys
import time

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"g1-b01-b14"))
import consumer_daemon as b14

ALLOWED={"sourceUrl","token","nativeSocket","intervalMs"}


def config_file(path):
    path=Path(path)
    if path.stat().st_uid!=os.getuid() or path.stat().st_mode&0o077:
        raise RuntimeError("P0B_CONSUMER_CONFIG_DAC_INVALID")
    cfg=json.loads(path.read_text())
    if (not isinstance(cfg,dict) or set(cfg)!=ALLOWED or
        not cfg["sourceUrl"].startswith("http://127.0.0.1:") or
        not cfg["sourceUrl"].endswith(
            "/v5/apps/app-a/projection/signed-pull") or
        len(cfg["token"])<32 or
        not cfg["nativeSocket"].startswith("/tmp/s1-b9-derive-") or
        not cfg["nativeSocket"].endswith("/consumer-ipc/signed.sock") or
        type(cfg["intervalMs"]) is not int or
        not 50<=cfg["intervalMs"]<=1000):
        raise RuntimeError("P0B_CONSUMER_CONFIG_INVALID")
    return cfg


def status(path,*,state,cursor=None,head=None,applied=0,failures=0,error=None):
    output={"state":state,"cursor":cursor,"head":head,"applied":applied,
            "failures":failures,"error":error,"pid":os.getpid()}
    temp=Path(str(path)+".tmp")
    temp.write_text(json.dumps(output,sort_keys=True))
    temp.chmod(0o600)
    os.replace(temp,path)


def replay(config):
    """Deliberately replay signed source events from ZERO via REAL IPC.

    Prove B11 native durable receipts suppress duplicate rows and detect
    tampering. Called only in a test under the same consumer UID.
    """
    checkpoint=b14.run_native(config,"native_checkpoint.py")
    current=checkpoint["lastSeq"]
    pulled=b14.pull(config,0)
    if pulled["head"]!=current or len(pulled["events"])!=current:
        raise RuntimeError("P0B_REPLAY_INPUT_NOT_CAUGHT_UP")
    result=b14.run_native(config,"native_apply.py",
                          payload=json.dumps({"app":"app-a","after":0,
                                              "events":pulled["events"]}))
    print("P0B_REPLAY|"+json.dumps({
        "before":current,"after":result["lastSeq"],
        "applied":result["applied"],"replayed":result["replayed"]
    }),flush=True)


def serve(config,status_path):
    path=Path(status_path)
    if path.parent.stat().st_uid!=os.getuid() or (
        path.parent.stat().st_mode&0o077):
        raise RuntimeError("P0B_CONSUMER_STATUS_PRIVATE")
    done=False
    def stop(_sig,_frame):
        nonlocal done
        done=True
    signal.signal(signal.SIGTERM,stop)
    signal.signal(signal.SIGINT,stop)
    failures=0
    status(path,state="STARTING")
    while not done:
        try:
            # The native broker audits all rows and receipt continuity on
            # EVERY poll before asking the source for new events.
            result=b14.step(config)
            failures=0
            status(path,state=result["state"],cursor=result["cursor"],
                   head=result["head"],applied=result["applied"])
        except b14.Failed as exc:
            failures+=1
            code=exc.code
            state=("DERIVED_DRIFT" if code=="DERIVED_DRIFT" else
                   "SOURCE_UNAVAILABLE" if code.startswith("SOURCE_") else
                   "NATIVE_UNAVAILABLE")
            status(path,state=state,failures=failures,error=code)
        time.sleep(min(config["intervalMs"]/1000*max(1,failures),1.0))
    status(path,state="STOPPING",failures=failures)


if __name__=="__main__":
    pa=argparse.ArgumentParser()
    pa.add_argument("--config",required=True)
    pa.add_argument("--status")
    pa.add_argument("--replay",action="store_true")
    a=pa.parse_args()
    cfg=config_file(a.config)
    if a.replay:
        replay(cfg)
    elif a.status:
        serve(cfg,a.status)
    else:
        raise SystemExit("P0B_CONSUMER_REQUIRES_STATUS_OR_REPLAY")
