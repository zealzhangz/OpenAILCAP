"""P0-B B15-style atomic immutable-in-use public SQLite publisher.

Runs under separate non-root publisher UID. Verifies B14 Ed25519 signed
Kernel CURRENT B2 release, directly queries current B2 release before AND
after building, checks exact B9 projector and independent Native SQL oracle
carried by the trusted test coordinator. Atomically replaces a single
unprivileged read-only snapshot. Never receives private signing key, Native
credentials, Docker socket, or writable authority SQLite.

Source business ROWS are a test-only Saltcorn seed, NOT B2's authority data.
No global cross-DB transaction, PKI, Form/Workflow or code parity implied.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import sys
import uuid
from urllib.error import HTTPError,URLError
from urllib.request import Request,urlopen

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"g1-b01-b2"))
from p0b_signed_release import verify,ReleaseSignatureRejected,canon
from projector import compile_release,check_compiled
from schema_core import sha

MAX_ROWS=256
ROWS_FIELDS={"contract_no","title","amount_minor","status"}
SCHEMA={"published_contracts","published_state"}

class PublishRejected(Exception):
    def __init__(self,code):
        super().__init__(code)
        self.code=code


def rows_digest(rows):
    return hashlib.sha256(canon(sorted(
        rows,key=lambda r:r["contract_no"])).encode()).hexdigest()


def current_release(cfg):
    url=cfg["kernelBase"]+"/v3/apps/app-a/tools/release.read"
    req=Request(url,data=b"{}",method="POST",headers={
        "Authorization":"Bearer "+cfg["kernelReadToken"],
        "Content-Type":"application/json"})
    try:
        with urlopen(req,timeout=5) as response:
            if response.status!=200:
                raise PublishRejected("PUBLISH_KERNEL_UNAVAILABLE")
            body=json.loads(response.read(262145))
    except (OSError,HTTPError,URLError,TimeoutError,ValueError):
        raise PublishRejected("PUBLISH_KERNEL_UNAVAILABLE") from None
    if not isinstance(body,dict) or set(body)!={
        "version","manifestHash","draftRevision","definitions"
    } or sha(body["definitions"])!=body["manifestHash"]:
        raise PublishRejected("PUBLISH_KERNEL_RELEASE_INVALID")
    return body


def bound_source(cfg,candidate):
    if not isinstance(candidate,dict) or set(candidate)!={
        "signedRelease","nativeOracle"
    }:
        raise PublishRejected("PUBLISH_CANDIDATE_SHAPE")
    try:
        signed=candidate["signedRelease"]
        payload=verify(signed,cfg["publicKeyHex"])
    except ReleaseSignatureRejected:
        raise PublishRejected("PUBLISH_SOURCE_SIGNATURE_REJECTED") from None
    current=current_release(cfg)
    if (current["version"]!=payload["version"] or
        current["manifestHash"]!=payload["manifestHash"] or
        current["draftRevision"]!=payload["draftRevision"]):
        raise PublishRejected("PUBLISH_SOURCE_NOT_LATEST")
    try:
        projected=compile_release(current,cfg["packTemplate"])
        check_compiled(projected)
    except Exception:
        raise PublishRejected("PUBLISH_DEPENDENCY_OR_PACK_INVALID") from None
    if (projected["projectionPackHash"]!=payload["projectionPackHash"] or
        current["definitions"]["view.contracts"]["columns"]!=
            payload["viewColumns"]):
        raise PublishRejected("PUBLISH_SIGNED_PROJECTOR_MISMATCH")
    native=candidate["nativeOracle"]
    if not isinstance(native,dict) or set(native.get("viewColumns",[]))!=set(
        payload["viewColumns"]
    ) or native.get("viewColumns")!=payload["viewColumns"]:
        raise PublishRejected("PUBLISH_NATIVE_VIEW_MISMATCH")
    rows=native.get("businessRows")
    if not isinstance(rows,list) or not 0<len(rows)<=MAX_ROWS:
        raise PublishRejected("PUBLISH_NATIVE_ROWS_INVALID")
    seen=set()
    for row in rows:
        if not isinstance(row,dict) or set(row)!=ROWS_FIELDS:
            raise PublishRejected("PUBLISH_NATIVE_ROW_SHAPE")
        for col in ("contract_no","title","status"):
            if not isinstance(row[col],str) or not 0<len(row[col])<=4096:
                raise PublishRejected("PUBLISH_NATIVE_TEXT_INVALID")
        if (type(row["amount_minor"]) is not int or
            not 0<=row["amount_minor"]<=2**53-1 or
            row["contract_no"] in seen):
            raise PublishRejected("PUBLISH_NATIVE_VALUE_INVALID")
        seen.add(row["contract_no"])
    return payload,sorted(rows,key=lambda x:x["contract_no"])


def _path_checks(cfg):
    out=Path(cfg["output"])
    if not (str(out).startswith("/tmp/s1-b9-derive-") and
            str(out).endswith("/published-private/published.sqlite") and
            cfg["kernelBase"].startswith("http://127.0.0.1:")):
        raise PublishRejected("PUBLISH_PATH_SCOPE_INVALID")
    folder=out.parent
    mode=folder.stat()
    if (not stat.S_ISDIR(mode.st_mode) or mode.st_uid!=os.getuid() or
        mode.st_mode&0o027):
        raise PublishRejected("PUBLISH_FOLDER_UNTRUSTED")
    return out


def publish(cfg,candidate):
    out=_path_checks(cfg)
    payload,rows=bound_source(cfg,candidate)
    digest=rows_digest(rows)
    tmp=out.parent/(".p0b-stage-"+uuid.uuid4().hex+".sqlite")
    try:
        fd=os.open(tmp,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        os.close(fd)
        with sqlite3.connect(str(tmp)) as db:
            db.execute("CREATE TABLE published_contracts("
                       "contract_no TEXT PRIMARY KEY,title TEXT NOT NULL,"
                       "amount_minor INTEGER NOT NULL,status TEXT NOT NULL)")
            db.execute("CREATE TABLE published_state("
                       "version INTEGER NOT NULL,manifest_hash TEXT NOT NULL,"
                       "pack_hash TEXT NOT NULL,view_columns TEXT NOT NULL,"
                       "rows_digest TEXT NOT NULL,signed_release TEXT NOT NULL)")
            db.executemany("INSERT INTO published_contracts VALUES(?,?,?,?)",
                           [(r["contract_no"],r["title"],r["amount_minor"],
                             r["status"]) for r in rows])
            db.execute("INSERT INTO published_state VALUES(?,?,?,?,?,?)",(
                payload["version"],payload["manifestHash"],
                payload["projectionPackHash"],canon(payload["viewColumns"]),
                digest,canon(candidate["signedRelease"])))
            db.commit()
        os.chmod(tmp,0o640)
        # Test injected build/install failure BEFORE an observable swap.
        if os.environ.get("P0B_INJECT_BUILD_FAILURE")=="1":
            raise PublishRejected("PUBLISH_BUILD_FAILURE_INJECTED")
        # Source and Native were independently verified before staging;
        # require unchanged B2 pointer/hash at the very last step.
        again,actual=bound_source(cfg,candidate)
        if again!=payload or actual!=rows:
            raise PublishRejected("PUBLISH_SOURCE_MOVED_DURING_BUILD")
        # Verify raw staging through exactly the reader parser before swap.
        from p0b_readonly_web import load_snapshot
        snap=load_snapshot(tmp,os.getuid(),cfg["publicKeyHex"])
        if (snap["payload"]!=payload or snap["rows"]!=rows or
            rows_digest(snap["rows"])!=digest):
            raise PublishRejected("PUBLISH_STAGED_SNAPSHOT_NOT_VERIFIED")
        with open(tmp,"rb") as f:os.fsync(f.fileno())
        os.replace(tmp,out)
        folder_fd=os.open(out.parent,os.O_DIRECTORY|os.O_RDONLY)
        try:os.fsync(folder_fd)
        finally:os.close(folder_fd)
        return {"version":payload["version"],"manifestHash":payload["manifestHash"],
                "rows":len(rows),"rowsDigest":digest,"ownerUid":os.getuid(),
                "singleFileAtomicSwap":True}
    finally:
        if tmp.exists():tmp.unlink()


def main():
    pa=argparse.ArgumentParser()
    pa.add_argument("--config",required=True)
    pa.add_argument("--candidate",required=True)
    a=pa.parse_args()
    cfgfile=Path(a.config)
    if cfgfile.stat().st_mode&0o077 or cfgfile.stat().st_uid!=os.getuid():
        raise SystemExit("P0B_PUBLISHER_CONFIG_NOT_PRIVATE")
    cfg=json.loads(cfgfile.read_text())
    if set(cfg)!={"output","kernelBase","kernelReadToken",
                 "publicKeyHex","packTemplate"}:
        raise SystemExit("P0B_PUBLISHER_CONFIG_INVALID")
    try:
        result=publish(cfg,json.loads(Path(a.candidate).read_text()))
        print("P0B_PUBLISHED|"+canon(result),flush=True)
    except PublishRejected as ex:
        print("P0B_PUBLISH_REJECT|"+ex.code,flush=True)
        raise SystemExit(2)

if __name__=="__main__":
    main()
