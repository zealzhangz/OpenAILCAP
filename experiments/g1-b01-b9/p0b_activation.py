"""G1 P0-B: one B2 SQLite atomic active-publication pointer (B9-only).

The B2 source release and B11 event/record oracle are read in the SAME
BEGIN IMMEDIATE transaction that CAS-writes active snapshot metadata,
epoch and idempotent activation receipt. A candidate is a separately
fsynced, content-addressed Publisher-UID SQLite file verified with the
same B17 single-FD parser BEFORE the Kernel commits this sole visible
activation pointer. It is NOT atomic with arbitrary B2 publish/rollback
commands or an external FS crash, and cannot claim zero HTTP 503 windows.

Only B9 Kernel UID executes this module, on its ORIGINAL authority.sqlite;
public Reader sees only the scoped publication.read JSON (no authority DB).
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import sqlite3
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"g1-b01-b2"))
from schema_core import canon,sha,CHANGE
from p0b_authority_business import read_business_on_connection,AuthorityDataRejected

HEX=re.compile(r"^[0-9a-f]{64}$")
ACTIVATION_KEYS={"changeId","expectedEpoch","candidateSha256",
                 "expectedVersion","expectedOutboxHead"}


class ActivationRejected(Exception):
    def __init__(self,status,code):
        super().__init__(code)
        self.status=status
        self.code=code


def initialize(db_path):
    with sqlite3.connect(db_path,timeout=10) as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS p0b_public_activations(
          app TEXT PRIMARY KEY,
          epoch INTEGER NOT NULL,
          candidate_sha TEXT NOT NULL,
          release_version INTEGER NOT NULL,
          manifest_hash TEXT NOT NULL,
          draft_revision INTEGER NOT NULL,
          outbox_head INTEGER NOT NULL,
          rows_digest TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS p0b_activation_receipts(
          app TEXT NOT NULL,
          change_id TEXT NOT NULL,
          actor TEXT NOT NULL,
          request_hash TEXT NOT NULL,
          response TEXT NOT NULL,
          PRIMARY KEY(app,change_id)
        );
        """)


def source_in_tx(db):
    # B2 CURRENT published pointer, immutable release row and B11 mutable
    # business head are read under the SAME B2 transaction/snapshot.
    row=db.execute(
        "SELECT a.current_release AS active_version,"
        "r.version,r.manifest,r.hash,r.draft_revision "
        "FROM apps a LEFT JOIN releases r "
        "ON r.app=a.app AND r.version=a.current_release "
        "WHERE a.app='app-a'"
    ).fetchone()
    if row is None or row["active_version"] is None or row["version"] is None:
        raise ActivationRejected(503,"ACTIVATION_NO_B2_PUBLISHED_RELEASE")
    try:
        definition=json.loads(row["manifest"])
    except (ValueError,TypeError):
        raise ActivationRejected(503,"ACTIVATION_B2_RELEASE_MALFORMED") from None
    if sha(definition)!=row["hash"]:
        raise ActivationRejected(503,"ACTIVATION_B2_RELEASE_HASH_DRIFT")
    try:
        b11=read_business_on_connection(db)
    except AuthorityDataRejected as err:
        raise ActivationRejected(503,err.code) from None
    return {
        "version":row["version"],
        "manifestHash":row["hash"],
        "draftRevision":row["draft_revision"],
        "outboxHead":b11["head"],
        "rowsDigest":b11["rowsDigest"]
    }


def active_row(db):
    row=db.execute(
        "SELECT epoch,candidate_sha,release_version,manifest_hash,"
        "draft_revision,outbox_head,rows_digest "
        "FROM p0b_public_activations WHERE app='app-a'"
    ).fetchone()
    if row is None:
        return 0,None
    data={
        "snapshotSha256":row["candidate_sha"],
        "version":row["release_version"],
        "manifestHash":row["manifest_hash"],
        "draftRevision":row["draft_revision"],
        "outboxHead":row["outbox_head"],
        "rowsDigest":row["rows_digest"]
    }
    return row["epoch"],data


def read(dbpath):
    with sqlite3.connect(dbpath,timeout=10,isolation_level=None) as db:
        db.row_factory=sqlite3.Row
        db.execute("BEGIN")
        try:
            source=source_in_tx(db)
            epoch,active=active_row(db)
            db.commit()
            return {"app":"app-a","epoch":epoch,
                    "active":active,"source":source}
        except BaseException:
            if db.in_transaction:db.rollback()
            raise


class Activation:
    def __init__(self,dbpath):
        self.dbpath=str(dbpath)
        root=Path(dbpath).parent.parent
        if not (str(root).startswith("/tmp/s1-b9-derive-") and
                str(dbpath).endswith("/authority-private/authority.sqlite")):
            raise ActivationRejected(500,"ACTIVATION_AUTHORITY_SCOPE_INVALID")
        self.folder=root/"published-private"/"candidates"
        self.key=Path(dbpath).parent/"p0b-release-ed25519.key"
        self.publisher_uid=pwd.getpwnam("ailcapb9pub").pw_uid

    def read(self):
        return read(self.dbpath)

    def _candidate(self,digest):
        folder=self.folder
        st=folder.stat()
        if (st.st_uid!=self.publisher_uid or st.st_mode&0o022):
            raise ActivationRejected(503,"ACTIVATION_CANDIDATE_FOLDER_UNTRUSTED")
        if self.key.stat().st_uid!=os.getuid() or (
            self.key.stat().st_mode&0o077):
            raise ActivationRejected(503,"ACTIVATION_SIGNING_KEY_INVALID")
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives import serialization
        secret=Ed25519PrivateKey.from_private_bytes(self.key.read_bytes())
        public=secret.public_key().public_bytes(
            serialization.Encoding.Raw,serialization.PublicFormat.Raw).hex()
        from p0b_readonly_web import load_snapshot,SnapshotDenied
        try:
            candidate=load_snapshot(folder/(digest+".sqlite"),
                                    self.publisher_uid,public)
        except (SnapshotDenied,OSError,ValueError):
            raise ActivationRejected(409,"ACTIVATION_CANDIDATE_INVALID") from None
        if candidate["artifactSha256"]!=digest:
            raise ActivationRejected(409,"ACTIVATION_CANDIDATE_BYTES_MISMATCH")
        return candidate["payload"]

    def activate(self,actor,cmd,*,fail_before_commit=False):
        if (not isinstance(cmd,dict) or set(cmd)!=ACTIVATION_KEYS or
            not isinstance(cmd["changeId"],str) or
            not CHANGE.fullmatch(cmd["changeId"]) or
            type(cmd["expectedEpoch"]) is not int or
            cmd["expectedEpoch"]<0 or
            type(cmd["expectedVersion"]) is not int or
            cmd["expectedVersion"]<1 or
            type(cmd["expectedOutboxHead"]) is not int or
            cmd["expectedOutboxHead"]<0 or
            not isinstance(cmd["candidateSha256"],str) or
            not HEX.fullmatch(cmd["candidateSha256"])):
            raise ActivationRejected(422,"ACTIVATION_COMMAND_INVALID")
        hash_request=sha({"action":"publication.activate",**cmd})
        with sqlite3.connect(self.dbpath,timeout=10,isolation_level=None) as db:
            db.row_factory=sqlite3.Row
            db.execute("PRAGMA busy_timeout=10000")
            try:
                db.execute("BEGIN IMMEDIATE")
                prior=db.execute(
                    "SELECT actor,request_hash,response "
                    "FROM p0b_activation_receipts "
                    "WHERE app='app-a' AND change_id=?",
                    (cmd["changeId"],)).fetchone()
                if prior:
                    if (prior["actor"]!=actor or
                        prior["request_hash"]!=hash_request):
                        raise ActivationRejected(409,"ACTIVATION_CHANGE_ID_REUSED")
                    result=json.loads(prior["response"])
                    db.commit()
                    return {**result,"replayed":True}
                source=source_in_tx(db)
                epoch,old=active_row(db)
                if epoch!=cmd["expectedEpoch"]:
                    raise ActivationRejected(409,"ACTIVATION_EPOCH_CONFLICT")
                if (source["version"]!=cmd["expectedVersion"] or
                    source["outboxHead"]!=cmd["expectedOutboxHead"]):
                    raise ActivationRejected(409,"ACTIVATION_B2_SOURCE_MOVED")
                payload=self._candidate(cmd["candidateSha256"])
                if {k:payload[k] for k in source}!=source:
                    raise ActivationRejected(409,"ACTIVATION_SOURCE_NOT_CURRENT")
                target={"snapshotSha256":cmd["candidateSha256"],**source}
                new_epoch=epoch if old==target else epoch+1
                if old!=target:
                    db.execute(
                        "INSERT INTO p0b_public_activations "
                        "(app,epoch,candidate_sha,release_version,manifest_hash,"
                        "draft_revision,outbox_head,rows_digest) "
                        "VALUES ('app-a',?,?,?,?,?,?,?) "
                        "ON CONFLICT(app) DO UPDATE SET "
                        "epoch=excluded.epoch,candidate_sha=excluded.candidate_sha,"
                        "release_version=excluded.release_version,"
                        "manifest_hash=excluded.manifest_hash,"
                        "draft_revision=excluded.draft_revision,"
                        "outbox_head=excluded.outbox_head,"
                        "rows_digest=excluded.rows_digest",
                        (new_epoch,cmd["candidateSha256"],source["version"],
                         source["manifestHash"],source["draftRevision"],
                         source["outboxHead"],source["rowsDigest"]))
                result={"decision":"ACTIVATED" if old!=target else "NO_CHANGE",
                        "epoch":new_epoch,"active":target,
                        "changeId":cmd["changeId"],"replayed":False}
                db.execute(
                    "INSERT INTO p0b_activation_receipts VALUES (?,?,?,?,?)",
                    ("app-a",cmd["changeId"],actor,hash_request,
                     canon(result)))
                if fail_before_commit:
                    raise ActivationRejected(503,"ACTIVATION_FAILURE_INJECTED")
                db.commit()
                return result
            except BaseException:
                if db.in_transaction:db.rollback()
                raise
