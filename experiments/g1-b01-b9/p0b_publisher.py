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
sys.path.insert(0,str(HERE.parent/"g1-b01-b14"))
from signed_projection import verify_event,SignatureRefused
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


def current_business(cfg):
    """B9-only capability requires release.read, no record write grant."""
    req=Request(cfg["kernelBase"]+"/v3/apps/app-a/tools/business.head",
                data=b"{}",method="POST",headers={
                    "Authorization":"Bearer "+cfg["kernelReadToken"],
                    "Content-Type":"application/json"})
    try:
        with urlopen(req,timeout=5) as r:
            if r.status!=200:
                raise PublishRejected("PUBLISH_B2_BUSINESS_UNAVAILABLE")
            value=json.loads(r.read(2049))
    except (OSError,HTTPError,URLError,TimeoutError,ValueError):
        raise PublishRejected("PUBLISH_B2_BUSINESS_UNAVAILABLE") from None
    if (not isinstance(value,dict) or set(value)!={
        "app","head","rowsDigest"} or value["app"]!="app-a" or
        type(value["head"]) is not int or value["head"]<0 or
        not isinstance(value["rowsDigest"],str)):
        raise PublishRejected("PUBLISH_B2_BUSINESS_HEAD_INVALID")
    return {"head":value["head"],"rowsDigest":value["rowsDigest"]}


def verified_business_events(cfg,candidate,payload):
    # B14 signs individual B11 event-time payloads; source is not a
    # caller-controlled dictionary or Saltcorn seed.
    signed=candidate.get("signedEvents")
    if (not isinstance(signed,list) or len(signed)>1000 or
        len(signed)!=payload["outboxHead"]):
        raise PublishRejected("PUBLISH_SIGNED_BUSINESS_HEAD_INVALID")
    actual={}
    for index,event in enumerate(signed,1):
        try:
            unsigned=verify_event(event,cfg["publicKeyHex"])
        except SignatureRefused:
            raise PublishRejected("PUBLISH_B11_EVENT_SIGNATURE_INVALID") from None
        if (unsigned["app"]!="app-a" or
            unsigned["model"]!="model.contracts" or
            unsigned["seq"]!=index or
            type(unsigned["version"]) is not int or
            unsigned["version"]<1 or
            not isinstance(unsigned["cells"],dict) or
            set(unsigned["cells"])!=ROWS_FIELDS):
            raise PublishRejected("PUBLISH_B11_OUTBOX_SEQUENCE_INVALID")
        body={k:unsigned[k] for k in (
            "app","seq","model","recordId","version","cells")}
        if hashlib.sha256(canon(body).encode()).hexdigest()!=unsigned["eventHash"]:
            raise PublishRejected("PUBLISH_B11_EVENT_HASH_INVALID")
        previous=actual.get(unsigned["recordId"])
        if ((previous is not None and
             unsigned["version"]!=previous["version"]+1) or
            (previous is None and unsigned["version"]!=1)):
            raise PublishRejected("PUBLISH_B11_RECORD_VERSION_GAP")
        actual[unsigned["recordId"]]={
            "version":unsigned["version"],"cells":unsigned["cells"]}
    rows=[data["cells"] for data in actual.values()]
    if len({row["contract_no"] for row in rows})!=len(rows):
        raise PublishRejected("PUBLISH_B11_DUPLICATE_BUSINESS_ID")
    if rows_digest(rows)!=payload["rowsDigest"]:
        raise PublishRejected("PUBLISH_B11_SIGNED_ROWS_DIGEST_MISMATCH")
    return sorted(rows,key=lambda x:x["contract_no"])


def bound_source(cfg,candidate):
    if not isinstance(candidate,dict) or set(candidate)!={
        "signedRelease","signedEvents","nativeOracle"
    }:
        raise PublishRejected("PUBLISH_CANDIDATE_SHAPE")
    try:
        signed=candidate["signedRelease"]
        payload=verify(signed,cfg["publicKeyHex"])
    except ReleaseSignatureRejected:
        raise PublishRejected("PUBLISH_SOURCE_SIGNATURE_REJECTED") from None
    signed_rows=verified_business_events(cfg,candidate,payload)
    business=current_business(cfg)
    if business!={"head":payload["outboxHead"],
                 "rowsDigest":payload["rowsDigest"]}:
        raise PublishRejected("PUBLISH_B2_RECORD_DATA_STALE")
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
    normalized=sorted(rows,key=lambda x:x["contract_no"])
    if normalized!=signed_rows:
        raise PublishRejected("PUBLISH_NATIVE_ROWS_NOT_B2_SIGNED")
    return payload,normalized


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


def publish(cfg,candidate,*,prepare_only=False):
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
        if prepare_only:
            # Immutable content-addressed candidate is never the public
            # pointer. Only Kernel can commit activation; a failure here
            # leaves active/public snapshot completely unchanged.
            directory=out.parent/"candidates"
            mode=directory.stat()
            if (not stat.S_ISDIR(mode.st_mode) or
                mode.st_uid!=os.getuid() or mode.st_mode&0o027):
                raise PublishRejected("PUBLISH_CANDIDATE_FOLDER_UNTRUSTED")
            artifact_hash=snap["artifactSha256"]
            target=directory/(artifact_hash+".sqlite")
            try:
                os.link(tmp,target)
            except FileExistsError:
                # A colliding SHA-named file is safe only if all its bytes
                # and signed source have independently verified equality.
                old=load_snapshot(target,os.getuid(),cfg["publicKeyHex"])
                if old["artifactSha256"]!=artifact_hash or old["payload"]!=payload:
                    raise PublishRejected("PUBLISH_CANDIDATE_NAME_COLLISION")
            else:
                tmp.unlink()  # published hard-link now has st_nlink==1
            if target.stat().st_nlink!=1:
                raise PublishRejected("PUBLISH_CANDIDATE_NOT_IMMUTABLE_IN_USE")
            folder_fd=os.open(directory,os.O_DIRECTORY|os.O_RDONLY)
            try:os.fsync(folder_fd)
            finally:os.close(folder_fd)
            return {"version":payload["version"],"manifestHash":payload["manifestHash"],
                    "rows":len(rows),"rowsDigest":digest,"ownerUid":os.getuid(),
                    "prepared":True,"snapshotSha256":artifact_hash,
                    "activationRequired":True}
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
    pa.add_argument("--prepare",action="store_true")
    a=pa.parse_args()
    cfgfile=Path(a.config)
    if cfgfile.stat().st_mode&0o077 or cfgfile.stat().st_uid!=os.getuid():
        raise SystemExit("P0B_PUBLISHER_CONFIG_NOT_PRIVATE")
    cfg=json.loads(cfgfile.read_text())
    if set(cfg)!={"output","kernelBase","kernelReadToken",
                 "publicKeyHex","packTemplate"}:
        raise SystemExit("P0B_PUBLISHER_CONFIG_INVALID")
    try:
        result=publish(cfg,json.loads(Path(a.candidate).read_text()),
                       prepare_only=a.prepare)
        print(("P0B_PREPARED|" if a.prepare else "P0B_PUBLISHED|")+
              canon(result),flush=True)
    except PublishRejected as ex:
        print("P0B_PUBLISH_REJECT|"+ex.code,flush=True)
        raise SystemExit(2)

if __name__=="__main__":
    main()
