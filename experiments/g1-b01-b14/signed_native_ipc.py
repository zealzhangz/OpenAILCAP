"""B14 real Saltcorn UID Native Apply Broker: verify Kernel Ed25519 before SQL.

The signing private key is NEVER available to this process. Native UID is
still able to bypass its own Broker and write its SQLite DB; B14 independent
auditor and Router detect tested SQL tampering, but cannot prevent it.
"""
from __future__ import annotations
import argparse
import grp
import json
import os
import signal
import sys
import threading
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"g1-b01-b13"))
from native_ipc import Broker,make_server
from signed_projection import verify_event,SignatureRefused


class SignedBroker(Broker):
    def __init__(self,db,consumer_uid,public_hex):
        super().__init__(db,consumer_uid,-1)
        self.public_hex=public_hex
    def execute(self,role,uid,body):
        if uid!=self.consumer_uid:
            return {"ok":False,"error":"PEER_UID_FORBIDDEN"}
        if role!="consumer":
            return {"ok":False,"error":"IPC_ROLE_FORBIDDEN"}
        if isinstance(body,dict) and body.get("op")=="apply":
            if set(body)!={"op","batch"} or not isinstance(body["batch"],dict):
                return {"ok":False,"error":"SIGNED_BATCH_INVALID"}
            batch=body["batch"]
            if set(batch)!={"app","after","events"} or (
                not isinstance(batch["events"],list) or
                len(batch["events"])>100
            ):
                return {"ok":False,"error":"SIGNED_BATCH_INVALID"}
            try:
                unsigned=[verify_event(e,self.public_hex)
                          for e in batch["events"]]
            except SignatureRefused as exc:
                return {"ok":False,"error":exc.code}
            body={"op":"apply","batch":{
                "app":batch["app"],"after":batch["after"],"events":unsigned}}
        return super().execute(role,uid,body)


def main():
    p=argparse.ArgumentParser()
    for name in ("db","socket","ready","public-key-file"):
        p.add_argument("--"+name,required=True)
    p.add_argument("--consumer-uid",type=int,required=True)
    args=p.parse_args()
    if not (args.db.startswith("/tmp/s1-b14-project-") and
            args.db.endswith("/runtime-private/projection-v1.sqlite") and
            args.socket.startswith("/tmp/s1-b14-project-")):
        raise SystemExit("B14_SCOPE_INVALID")
    public_path=Path(args.public_key_file)
    if public_path.stat().st_mode&0o222:
        raise SystemExit("B14_PINNED_PUBLIC_KEY_MUTABLE")
    public_hex=public_path.read_text().strip()
    if len(bytes.fromhex(public_hex))!=32:
        raise SystemExit("B14_PUBLIC_KEY_INVALID")
    if os.path.lexists(args.socket):
        raise SystemExit("B14_SOCKET_ALREADY_EXISTS")
    broker=SignedBroker(args.db,args.consumer_uid,public_hex)
    server=make_server(args.socket,"ailcapb14pipe","consumer",broker)
    stop=threading.Event()
    def terminate(_sig,_frame):stop.set()
    signal.signal(signal.SIGTERM,terminate)
    signal.signal(signal.SIGINT,terminate)
    worker=threading.Thread(target=server.serve_forever,daemon=True)
    worker.start()
    Path(args.ready).write_text(json.dumps({
        "uid":os.getuid(),"pid":os.getpid(),"signature":"Ed25519",
        "privateKeyPresent":False}))
    Path(args.ready).chmod(0o644)
    print("S1_B14_SIGNED_NATIVE_READY|"+str(os.getuid()),flush=True)
    try:stop.wait()
    finally:
        server.shutdown()
        server.server_close()
        try:os.unlink(args.socket)
        except FileNotFoundError:pass


if __name__=="__main__":
    main()
