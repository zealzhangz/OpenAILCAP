"""B15 independent sixth-UID signed B2 / physical Native verified publisher.

Only public four-column business rows and a signed-source checkpoint are
published. Never copies Saltcorn authentication/session/plugin tables.
Single immutable-in-use SQLite file is built privately, fsynced and atomically
os.replace()d. Source/Native are checked before and after staging.
This is a controller-invoked research publisher, not an HA/CDC daemon.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import sqlite3
import stat
import sys
import uuid
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"g1-b01-b14"))
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"g1-b01-b13"))
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"g1-b01-b10"))
from guard_router import source_events
from native_ipc import native_snapshot
from router import query_current_release,Refused

FIELDS={"contract_no","title","amount_minor","status"}
SNAP_TABLES={"published_contracts","published_state"}


def canon(obj):
    return json.dumps(obj,sort_keys=True,ensure_ascii=False,separators=(",",":"))


def rows_digest(rows):
    return hashlib.sha256(canon(sorted(rows,key=lambda x:x["contract_no"])).encode()).hexdigest()


def compare_source_native(config):
    release=query_current_release(config["kernelPort"],config["kernelReadToken"])
    if release!={"version":config["version"],"hash":config["manifestHash"]}:
        raise Refused(503,"PUBLISH_RELEASE_CHANGED")
    head,expected=source_events(config)  # B14 verifies every Ed25519 signature
    physical=native_snapshot(config["nativeDb"])  # actual SQLite read-only
    if not physical["clean"] or physical["cursor"]!=head or (
        physical["receiptCount"]!=head
    ) or physical["mappingCount"]!=len(expected) or (
        {r["contract_no"]:r for r in physical["rows"]}!=expected
    ) or len(physical["rows"])!=len(expected):
        raise Refused(503,"PUBLISH_SOURCE_NATIVE_MISMATCH")
    return head,expected


def read_published(path,publisher_uid,manifest_hash):
    target=Path(path)
    try:
        s=target.stat()
        if (not stat.S_ISREG(s.st_mode) or s.st_uid!=publisher_uid or
            s.st_mode&0o022 or s.st_nlink!=1):
            raise Refused(503,"PUBLISHED_FILE_OWNERSHIP_INVALID")
        with sqlite3.connect(
            "file:"+str(target)+"?mode=ro&immutable=1",uri=True,timeout=2
        ) as db:
            db.row_factory=sqlite3.Row
            tables={x[0] for x in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            if tables!=SNAP_TABLES:
                raise Refused(503,"PUBLISHED_SCHEMA_UNEXPECTED")
            state=db.execute(
                "SELECT head,rows_digest,manifest_hash FROM published_state"
            ).fetchall()
            if len(state)!=1 or state[0]["manifest_hash"]!=manifest_hash:
                raise Refused(503,"PUBLISHED_RELEASE_MISMATCH")
            rows=[dict(r) for r in db.execute(
                "SELECT contract_no,title,amount_minor,status "
                "FROM published_contracts ORDER BY contract_no")]
        if rows_digest(rows)!=state[0]["rows_digest"]:
            raise Refused(503,"PUBLISHED_ROWS_DIGEST_MISMATCH")
        return {"head":state[0]["head"],"rows":rows,
                "digest":state[0]["rows_digest"]}
    except (OSError,sqlite3.Error,TypeError,ValueError):
        raise Refused(503,"PUBLISHED_SNAPSHOT_UNAVAILABLE") from None


def publish(config):
    output=Path(config["output"])
    if (not str(output).startswith("/tmp/s1-b15-project-") or
        not str(output).endswith("/published-private/published.sqlite") or
        not str(config["nativeDb"]).startswith("/tmp/s1-b15-project-") or
        not str(config["nativeDb"]).endswith(
            "/runtime-private/projection-v1.sqlite")):
        raise Refused(503,"PUBLISH_PATH_SCOPE_INVALID")
    folder=output.parent
    if folder.stat().st_uid!=os.getuid() or folder.stat().st_mode&0o002:
        raise Refused(503,"PUBLISH_DIRECTORY_NOT_PRIVATE")
    head,expected=compare_source_native(config)
    rows=sorted(expected.values(),key=lambda x:x["contract_no"])
    digest=rows_digest(rows)
    temp=folder/(".staging-"+uuid.uuid4().hex+".sqlite")
    try:
        fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        os.close(fd)
        with sqlite3.connect(temp) as db:
            db.execute("CREATE TABLE published_contracts("
                       "contract_no TEXT PRIMARY KEY,title TEXT NOT NULL,"
                       "amount_minor INTEGER NOT NULL,status TEXT NOT NULL)")
            db.execute("CREATE TABLE published_state("
                       "head INTEGER NOT NULL,rows_digest TEXT NOT NULL,"
                       "manifest_hash TEXT NOT NULL)")
            db.executemany(
                "INSERT INTO published_contracts VALUES(?,?,?,?)",
                [(r["contract_no"],r["title"],r["amount_minor"],r["status"])
                 for r in rows])
            db.execute("INSERT INTO published_state VALUES(?,?,?)",
                       (head,digest,config["manifestHash"]))
            db.commit()
        # Re-check B2 + real Native after staging. Concurrent change => reject.
        new_head,new_expected=compare_source_native(config)
        if new_head!=head or new_expected!=expected:
            raise Refused(503,"PUBLISH_SOURCE_MOVED_DURING_BUILD")
        os.chmod(temp,0o640)
        # Verify staging using the SAME read-only schema used by the Router.
        verified=read_published(temp,os.getuid(),config["manifestHash"])
        if verified["head"]!=head or verified["digest"]!=digest:
            raise Refused(503,"PUBLISH_STAGING_INVALID")
        with open(temp,"rb") as handle:os.fsync(handle.fileno())
        os.replace(temp,output)  # single-file atomic pointer swap
        directory_fd=os.open(folder,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(directory_fd)
        finally:os.close(directory_fd)
        return {"head":head,"contracts":len(rows),"digest":digest,
                "uid":os.getuid(),"onlyPublicProjection":True}
    finally:
        if temp.exists():temp.unlink()


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--config",required=True)
    args=p.parse_args()
    path=Path(args.config)
    if path.stat().st_mode&0o077:
        raise SystemExit("PUBLISH_CONFIG_NOT_PRIVATE")
    config=json.loads(path.read_text())
    if set(config)!={"output","nativeDb","sourceUrl","sourceToken",
                    "publicKeyHex","kernelPort","kernelReadToken",
                    "version","manifestHash"}:
        raise SystemExit("PUBLISH_CONFIG_SHAPE_INVALID")
    try:
        result=publish(config)
        print("S1_B15_PUBLISH|"+json.dumps(result),flush=True)
    except Refused as exc:
        print("S1_B15_PUBLISH_REJECT|"+exc.code,flush=True)
        raise SystemExit(2)


if __name__=="__main__":
    main()
