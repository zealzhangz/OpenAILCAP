"""B13 real Saltcorn-UID Unix socket broker: peer UID + DAC, narrow ops.

Two separate AF_UNIX sockets with disjoint Linux groups:
consumer: audit, checkpoint, apply (untrusted event payload; source signature
           is NOT verified, so a compromised consumer could forge data).
guard: snapshot ONLY, never apply, no Saltcorn auth tables or tokens.
This is a research IPC prototype; not a general-purpose OS plugin server.
"""
from __future__ import annotations
import argparse
import grp
import json
import os
import signal
import socket
import socketserver
import sqlite3
import struct
import sys
import threading
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"g1-b01-b11"))
from apply_worker import apply,Refused,digest

MAX_FRAME=128*1024


def native_snapshot(db_path):
    with sqlite3.connect("file:"+str(db_path)+"?mode=ro",uri=True,timeout=3) as db:
        db.row_factory=sqlite3.Row
        db.execute("BEGIN")
        cursor=db.execute("SELECT last_seq FROM b11_projection_cursor "
                          "WHERE app='app-a'").fetchone()[0]
        receipts=[r[0] for r in db.execute(
            "SELECT seq FROM b11_projection_receipts WHERE app='app-a' "
            "ORDER BY seq").fetchall()]
        mappings=db.execute("SELECT contract_no,cells_hash FROM b11_record_map "
                            "WHERE app='app-a'").fetchall()
        rows=[dict(r) for r in db.execute(
            "SELECT contract_no,title,amount_minor,status FROM s1_contracts "
            "ORDER BY contract_no").fetchall()]
        db.commit()
    expected={r["contract_no"]:r["cells_hash"] for r in mappings}
    actual={r["contract_no"]:digest(r) for r in rows}
    clean=(receipts==list(range(1,cursor+1)) and
           expected==actual and len(expected)==len(mappings) and
           len(actual)==len(rows))
    return {"clean":clean,"cursor":cursor,"rows":rows,
            "receiptCount":len(receipts),"mappingCount":len(mappings)}


class Broker:
    def __init__(self,db,consumer_uid,router_uid):
        self.db=db
        self.consumer_uid=consumer_uid
        self.router_uid=router_uid
        self.lock=threading.RLock()
    def execute(self,role,uid,body):
        allowed_uid=self.consumer_uid if role=="consumer" else self.router_uid
        if uid!=allowed_uid:
            return {"ok":False,"error":"PEER_UID_FORBIDDEN"}
        if not isinstance(body,dict) or set(body) not in (
            {"op"},{"op","batch"}
        ):
            return {"ok":False,"error":"IPC_ARGUMENTS_INVALID"}
        op=body.get("op")
        if role=="guard" and (op!="snapshot" or set(body)!={"op"}):
            return {"ok":False,"error":"GUARD_READ_ONLY"}
        if role=="consumer" and op not in ("audit","checkpoint","apply"):
            return {"ok":False,"error":"CONSUMER_OP_FORBIDDEN"}
        if (op=="apply")!=(set(body)=={"op","batch"}):
            return {"ok":False,"error":"IPC_ARGUMENTS_INVALID"}
        with self.lock:
            try:
                if op=="apply":
                    result=apply(self.db,body["batch"])
                elif op in ("audit","snapshot"):
                    snap=native_snapshot(self.db)
                    result=({"clean":snap["clean"],
                             "cursor":snap["cursor"],
                             "mapped":snap["mappingCount"],
                             "receipts":snap["receiptCount"]}
                            if op=="audit" else snap)
                else:
                    result={"lastSeq":native_snapshot(self.db)["cursor"]}
                return {"ok":True,"result":result}
            except (Refused,sqlite3.Error,ValueError,TypeError) as exc:
                return {"ok":False,"error":getattr(
                    exc,"code","NATIVE_SQL_OR_BATCH_REJECTED")}


def make_server(sock_path,group,role,broker):
    class Handler(socketserver.StreamRequestHandler):
        def handle(self):
            try:
                creds=self.request.getsockopt(
                    socket.SOL_SOCKET,socket.SO_PEERCRED,12)
                _,uid,_=struct.unpack("3i",creds)
                raw=self.rfile.readline(MAX_FRAME+2)
                if len(raw)>MAX_FRAME or not raw.endswith(b"\n"):
                    result={"ok":False,"error":"FRAME_TOO_LARGE_OR_INCOMPLETE"}
                else:
                    result=broker.execute(role,uid,json.loads(raw))
            except (OSError,ValueError,UnicodeError,json.JSONDecodeError):
                result={"ok":False,"error":"IPC_INVALID_FRAME"}
            self.wfile.write((json.dumps(result,separators=(",",":"))+"\n").encode())
            self.wfile.flush()
    class Server(socketserver.ThreadingMixIn,socketserver.UnixStreamServer):
        daemon_threads=True
        allow_reuse_address=False
    server=Server(sock_path,Handler)
    os.chown(sock_path,-1,grp.getgrnam(group).gr_gid)
    os.chmod(sock_path,0o660)
    return server


def main():
    p=argparse.ArgumentParser()
    for name in ("db","consumer-socket","guard-socket","ready"):
        p.add_argument("--"+name,required=True)
    p.add_argument("--consumer-uid",type=int,required=True)
    p.add_argument("--router-uid",type=int,required=True)
    args=p.parse_args()
    if not (args.db.startswith("/tmp/s1-b13-project-") and
            args.db.endswith("/runtime-private/projection-v1.sqlite")):
        raise SystemExit("IPC_DB_SCOPE_INVALID")
    for path in (args.consumer_socket,args.guard_socket):
        if not path.startswith("/tmp/s1-b13-project-"):
            raise SystemExit("IPC_PATH_SCOPE_INVALID")
        if os.path.lexists(path):
            raise SystemExit("IPC_SOCKET_ALREADY_EXISTS")
    broker=Broker(args.db,args.consumer_uid,args.router_uid)
    c=make_server(args.consumer_socket,"ailcapb13pipe","consumer",broker)
    g=make_server(args.guard_socket,"ailcapb13guard","guard",broker)
    stop=threading.Event()
    def terminate(_sig,_frame):
        stop.set()
    signal.signal(signal.SIGTERM,terminate)
    signal.signal(signal.SIGINT,terminate)
    workers=[threading.Thread(target=x.serve_forever,daemon=True)
             for x in (c,g)]
    for w in workers:w.start()
    ready=Path(args.ready)
    ready.write_text(json.dumps({"uid":os.getuid(),"pid":os.getpid(),
        "consumerSocket":args.consumer_socket,"guardSocket":args.guard_socket}))
    ready.chmod(0o644)
    print("S1_B13_NATIVE_IPC_READY|"+json.dumps({"uid":os.getuid()}),flush=True)
    try:stop.wait()
    finally:
        for server in (c,g):
            server.shutdown()
            server.server_close()
        for path in (args.consumer_socket,args.guard_socket):
            try:os.unlink(path)
            except FileNotFoundError:pass


if __name__=="__main__":
    main()
