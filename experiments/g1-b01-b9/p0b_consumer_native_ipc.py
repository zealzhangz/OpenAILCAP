"""G1 P0-B privileged Saltcorn UID *only* signed-IPC apply endpoint.

Reuse B13 SO_PEERCRED/AF_UNIX DAC and B14 Ed25519 SignedBroker. Consumer
UID has NO authority DB, Native DB, signing private key, or sudo privilege.
Native-UID Broker verifies each B14 signature BEFORE native SQLite B11
atomic row/map/receipt/cursor transaction; no untrusted raw SQL.
"""
from __future__ import annotations
import argparse
import grp
import json
import os
from pathlib import Path
import signal
import sqlite3
import sys
import threading

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"g1-b01-b11"))
sys.path.insert(0,str(HERE.parent/"g1-b01-b13"))
sys.path.insert(0,str(HERE.parent/"g1-b01-b14"))
from apply_worker import ensure_tables
from native_ipc import make_server,native_snapshot
from native_oracle import inspect as native_inspect
from signed_native_ipc import SignedBroker

PATH_SUFFIX="/runtime-private/projection-p0b-consumer.sqlite"


class PublisherOracleBroker:
    """Native owner UID: Publisher may observe ONLY bounded verified view
    metadata, SQL rows and durable cursor; cannot apply events or read auth.
    Socket peer creds + DAC keep Plugin/Consumer/Renderer out.
    """
    def __init__(self,db,publisher_uid):
        self.db=db
        self.publisher_uid=publisher_uid

    def execute(self,role,uid,body):
        if role!="publisher" or uid!=self.publisher_uid:
            return {"ok":False,"error":"PUBLISHER_PEER_UID_FORBIDDEN"}
        if not isinstance(body,dict) or body!={"op":"oracle"}:
            return {"ok":False,"error":"PUBLISHER_ORACLE_READ_ONLY"}
        try:
            native=native_inspect(self.db)
            snap=native_snapshot(self.db)
            if (not snap["clean"] or snap["rows"]!=native["businessRows"] or
                snap["receiptCount"]!=snap["cursor"] or
                snap["mappingCount"]!=len(native["businessRows"])):
                return {"ok":False,"error":"PUBLISHER_NATIVE_SQL_DRIFT"}
            if len(native["businessRows"])>256:
                return {"ok":False,"error":"PUBLISHER_NATIVE_ROW_LIMIT"}
            return {"ok":True,"result":{
                "cursor":snap["cursor"],"receiptCount":snap["receiptCount"],
                "nativeOracle":native}}
        except (sqlite3.Error,ValueError,TypeError):
            return {"ok":False,"error":"PUBLISHER_NATIVE_SQL_UNAVAILABLE"}



def scoped(db):
    if not (db.startswith("/tmp/s1-b9-derive-") and
            db.endswith(PATH_SUFFIX)):
        raise RuntimeError("P0B_NATIVE_CONSUMER_DB_SCOPE_INVALID")
    path=Path(db)
    if (path.stat().st_uid!=os.getuid() or
        path.stat().st_mode&0o022):
        raise RuntimeError("P0B_NATIVE_SQLITE_DAC_INVALID")


def initialize(db):
    scoped(db)
    with sqlite3.connect(db,timeout=10) as con:
        ensure_tables(con)
        con.commit()
    state=native_snapshot(db)
    if not state["clean"] or state["cursor"]!=0 or state["rows"]:
        raise RuntimeError("P0B_INITIAL_NATIVE_NOT_EMPTY")
    return state


def serve(db,sock,ready,public_key_file,consumer_uid,
          publisher_sock,publisher_uid):
    scoped(db)
    socket=Path(sock)
    if not (str(socket).startswith("/tmp/s1-b9-derive-") and
            str(socket).endswith("/consumer-ipc/signed.sock") and
            socket.parent.stat().st_uid==os.getuid()):
        raise RuntimeError("P0B_CONSUMER_SOCKET_SCOPE_INVALID")
    if socket.exists() or socket.is_symlink():
        raise RuntimeError("P0B_CONSUMER_SOCKET_ALREADY_EXISTS")
    public=Path(public_key_file)
    if public.stat().st_mode&0o222:
        raise RuntimeError("P0B_PINNED_PUBLIC_KEY_MUTABLE")
    pubhex=public.read_text().strip()
    if len(bytes.fromhex(pubhex))!=32:
        raise RuntimeError("P0B_PINNED_PUBLIC_KEY_BAD")
    if consumer_uid==os.getuid() or consumer_uid<=0:
        raise RuntimeError("P0B_CONSUMER_NOT_SEPARATE_UID")
    broker=SignedBroker(db,consumer_uid,pubhex)
    listener=make_server(str(socket),"ailcapb9ipc","consumer",broker)
    pubpath=Path(publisher_sock)
    if (not str(pubpath).startswith("/tmp/s1-b9-derive-") or
        not str(pubpath).endswith("/publisher-ipc/oracle.sock") or
        pubpath.parent.stat().st_uid!=os.getuid() or
        pubpath.parent.stat().st_mode&0o007 or
        pubpath.exists() or pubpath.is_symlink() or
        publisher_uid==os.getuid() or publisher_uid==consumer_uid or
        publisher_uid<=0):
        raise RuntimeError("P0B_PUBLISHER_IPC_SCOPE_INVALID")
    pubbroker=PublisherOracleBroker(db,publisher_uid)
    publisher_listener=make_server(
        str(pubpath),"ailcapb9pubipc","publisher",pubbroker)
    stop=threading.Event()
    def halt(_sig,_frame):stop.set()
    signal.signal(signal.SIGTERM,halt)
    signal.signal(signal.SIGINT,halt)
    worker=threading.Thread(target=listener.serve_forever,daemon=True)
    worker.start()
    pub_worker=threading.Thread(
        target=publisher_listener.serve_forever,daemon=True)
    pub_worker.start()
    Path(ready).write_text(json.dumps({
        "uid":os.getuid(),"pid":os.getpid(),
        "socket":str(socket),"signatures":"B14-Ed25519",
        "consumerUid":consumer_uid,"publisherUid":publisher_uid,
        "publisherSocket":str(pubpath)
    }))
    Path(ready).chmod(0o644)
    print("P0B_NATIVE_SIGNED_IPC_READY|"+str(os.getuid()),flush=True)
    try:stop.wait()
    finally:
        listener.shutdown()
        publisher_listener.shutdown()
        listener.server_close()
        publisher_listener.server_close()
        socket.unlink(missing_ok=True)
        pubpath.unlink(missing_ok=True)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--db",required=True)
    p.add_argument("--init",action="store_true")
    p.add_argument("--inspect",action="store_true")
    p.add_argument("--socket")
    p.add_argument("--ready")
    p.add_argument("--public-key-file")
    p.add_argument("--consumer-uid",type=int)
    p.add_argument("--publisher-socket")
    p.add_argument("--publisher-uid",type=int)
    a=p.parse_args()
    if a.inspect:
        scoped(a.db)
        print("P0B_NATIVE_DURABLE_ORACLE|"+json.dumps(native_snapshot(a.db)),flush=True)
    elif a.init:
        print("P0B_NATIVE_EMPTY_INITIALIZED|"+
              json.dumps(initialize(a.db)),flush=True)
    else:
        if not all((a.socket,a.ready,a.public_key_file,a.consumer_uid,
                    a.publisher_socket,a.publisher_uid)):
            raise SystemExit("P0B_SIGNED_NATIVE_ARGS_REQUIRED")
        serve(a.db,a.socket,a.ready,a.public_key_file,a.consumer_uid,
              a.publisher_socket,a.publisher_uid)
