"""B14 real independent auditor Linux UID: direct read-only physical SQLite.

Distinct from Saltcorn UID. No Native Broker dependency, no Saltcorn tokens,
no write API. Reader's code and socket directory are not writable by Saltcorn
UID. File group grants only SQLite read, not write. A hostile Saltcorn UID can
still alter DB bytes and revoke reader access (=> guard 503).
"""
from __future__ import annotations
import argparse
import json
import os
import signal
import sys
import threading
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"g1-b01-b13"))
from native_ipc import Broker,make_server,native_snapshot


def main():
    p=argparse.ArgumentParser()
    for key in ("db","socket","ready"):
        p.add_argument("--"+key,required=True)
    p.add_argument("--router-uid",type=int,required=True)
    args=p.parse_args()
    if not (args.db.startswith("/tmp/s1-b14-project-") and
            args.db.endswith("/runtime-private/projection-v1.sqlite") and
            args.socket.startswith("/tmp/s1-b14-project-")):
        raise SystemExit("B14_AUDITOR_SCOPE_INVALID")
    # Real OS permission check; read-only open must succeed, write open
    # must be forbidden before the listener starts.
    fd=os.open(args.db,os.O_RDONLY)
    os.close(fd)
    try:
        fd=os.open(args.db,os.O_WRONLY)
        os.close(fd)
    except PermissionError:
        pass
    else:
        raise SystemExit("B14_AUDITOR_MUST_NOT_HAVE_DB_WRITE")
    native_snapshot(args.db)
    if os.path.lexists(args.socket):
        raise SystemExit("B14_AUDIT_SOCKET_ALREADY_EXISTS")
    broker=Broker(args.db,-1,args.router_uid)
    server=make_server(args.socket,"ailcapb14guard","guard",broker)
    stop=threading.Event()
    def terminate(_sig,_frame):stop.set()
    signal.signal(signal.SIGTERM,terminate)
    signal.signal(signal.SIGINT,terminate)
    worker=threading.Thread(target=server.serve_forever,daemon=True)
    worker.start()
    Path(args.ready).write_text(json.dumps({
        "uid":os.getuid(),"pid":os.getpid(),
        "directSQLiteRead":True,"directSQLiteWrite":False,
        "nativeIPCRequired":False}))
    Path(args.ready).chmod(0o644)
    print("S1_B14_INDEPENDENT_AUDITOR_READY|"+str(os.getuid()),flush=True)
    try:stop.wait()
    finally:
        server.shutdown()
        server.server_close()
        try:os.unlink(args.socket)
        except FileNotFoundError:pass


if __name__=="__main__":
    main()
