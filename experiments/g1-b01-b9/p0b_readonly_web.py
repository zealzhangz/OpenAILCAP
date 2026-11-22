"""P0-B B17-style read-only projection behind B14+B15 source-fresh publisher.

A DIFFERENT non-root Linux UID than Kernel, Saltcorn and Publisher. Single FD
read of immutable-in-use B15-shaped SQLite, B14 Ed25519 verification, live B2
release.read freshness on EVERY HTTP request (before & after read), bounded
escaped HTML. Never uses Saltcorn sessions/CLI or any write method.

During B2 pointer advance before Publisher swap, returns 503 rather than
silently serving unverified stale HTML. No production HA/SSO nor Form/Code/
Workflow parity. This route is a bounded contracts-list read-only projection.
"""
from __future__ import annotations
import argparse
from contextlib import closing
import hashlib
from html import escape
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
from urllib.error import HTTPError,URLError
from urllib.request import Request,urlopen

from p0b_signed_release import verify,ReleaseSignatureRejected,canon

ROUTE="/view/s1_contract_list"
MAX_BYTES=1048576
MAX_ROWS=256
ROWS=("contract_no","title","amount_minor","status")
TABLES={"published_contracts","published_state"}
LABELS={"contract_no":"Contract Number","title":"Title",
        "amount_minor":"Amount in CNY cents","status":"Status"}

class SnapshotDenied(Exception):
    def __init__(self,code):
        super().__init__(code)
        self.code=code


def _rows_digest(rows):
    return hashlib.sha256(canon(sorted(rows,key=lambda x:x["contract_no"])
                                ).encode()).hexdigest()


def load_snapshot(path,publisher_uid,public_key):
    """Hardened B17 single-FD reader, no trust in public snapshot's self-hash."""
    try:
        file=Path(path)
        parent=file.parent.lstat()
        if (not stat.S_ISDIR(parent.st_mode) or
            parent.st_uid!=publisher_uid or parent.st_mode&0o022):
            raise SnapshotDenied("SNAPSHOT_PARENT_UNTRUSTED")
        fd=os.open(file,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        try:
            s=os.fstat(fd)
            if (not stat.S_ISREG(s.st_mode) or s.st_uid!=publisher_uid or
                s.st_mode&0o022 or s.st_nlink!=1 or
                not 0<s.st_size<=MAX_BYTES):
                raise SnapshotDenied("SNAPSHOT_FILE_UNTRUSTED")
            with os.fdopen(fd,"rb",closefd=False) as stream:
                raw=stream.read(MAX_BYTES+1)
            if len(raw)!=s.st_size:
                raise SnapshotDenied("SNAPSHOT_CHANGED_WHILE_READ")
        finally:
            os.close(fd)
        with closing(sqlite3.connect(":memory:")) as db:
            db.deserialize(raw)
            db.execute("PRAGMA query_only=ON")
            db.execute("PRAGMA trusted_schema=OFF")
            db.row_factory=sqlite3.Row
            tables=list(db.execute("SELECT name,type FROM sqlite_master"))
            if ({x["name"] for x in tables if x["type"]=="table"}!=TABLES
                or any(x["type"] in ("trigger","view") for x in tables)):
                raise SnapshotDenied("SNAPSHOT_SCHEMA_UNEXPECTED")
            expected={
                "published_contracts":list(ROWS),
                "published_state":["version","manifest_hash","pack_hash",
                                   "view_columns","rows_digest","signed_release"]}
            for name,fields in expected.items():
                if [x["name"] for x in db.execute(
                    "PRAGMA table_info("+name+")")]!=fields:
                    raise SnapshotDenied("SNAPSHOT_COLUMNS_UNEXPECTED")
            state=db.execute(
                "SELECT * FROM published_state LIMIT 2").fetchall()
            if len(state)!=1:
                raise SnapshotDenied("SNAPSHOT_STATE_COUNT")
            state=state[0]
            signed=json.loads(state["signed_release"])
            try:payload=verify(signed,public_key)
            except ReleaseSignatureRejected:
                raise SnapshotDenied("SNAPSHOT_SIGNATURE_INVALID") from None
            columns=json.loads(state["view_columns"])
            if (payload["manifestHash"]!=state["manifest_hash"] or
                payload["projectionPackHash"]!=state["pack_hash"] or
                payload["version"]!=state["version"] or
                payload["viewColumns"]!=columns):
                raise SnapshotDenied("SNAPSHOT_RELEASE_METADATA_DRIFT")
            rows=[dict(x) for x in db.execute(
                "SELECT contract_no,title,amount_minor,status "
                "FROM published_contracts ORDER BY contract_no LIMIT ?",
                (MAX_ROWS+1,))]
            if len(rows)>MAX_ROWS or (
                not rows or
                len({x["contract_no"] for x in rows})!=len(rows)):
                raise SnapshotDenied("SNAPSHOT_ROW_LIMIT")
            for row in rows:
                for k in ("contract_no","title","status"):
                    if (type(row[k]) is not str or
                        not 0<len(row[k])<=4096):
                        raise SnapshotDenied("SNAPSHOT_TEXT_INVALID")
                if type(row["amount_minor"]) is not int or (
                    not 0<=row["amount_minor"]<=2**53-1):
                    raise SnapshotDenied("SNAPSHOT_AMOUNT_INVALID")
            if _rows_digest(rows)!=state["rows_digest"]:
                raise SnapshotDenied("SNAPSHOT_ROWS_DIGEST_INVALID")
            return {"payload":payload,"rows":rows,
                    "digest":state["rows_digest"]}
    except SnapshotDenied:
        raise
    except (OSError,ValueError,TypeError,sqlite3.Error):
        raise SnapshotDenied("SNAPSHOT_UNAVAILABLE") from None


def current_head(config):
    url=config["kernelBase"]+"/v3/apps/app-a/tools/release.read"
    request=Request(url,data=b"{}",headers={
        "Authorization":"Bearer "+config["kernelReadToken"],
        "Content-Type":"application/json"},method="POST")
    try:
        with urlopen(request,timeout=4) as resp:
            if resp.status!=200:
                raise SnapshotDenied("B2_CURRENT_SOURCE_UNAVAILABLE")
            body=json.loads(resp.read(262145))
    except (OSError,HTTPError,URLError,TimeoutError,ValueError):
        raise SnapshotDenied("B2_CURRENT_SOURCE_UNAVAILABLE") from None
    if (not isinstance(body,dict) or set(body)!={
        "version","manifestHash","draftRevision","definitions"} or
        type(body["version"]) is not int or
        not isinstance(body["manifestHash"],str)):
        raise SnapshotDenied("B2_CURRENT_SOURCE_MALFORMED")
    return body["version"],body["manifestHash"],body["draftRevision"]


def render(data):
    p=data["payload"]
    columns=p["viewColumns"]
    head="".join("<th>"+escape(LABELS[k])+"</th>" for k in columns)
    body="".join("<tr>"+"".join(
        "<td>"+escape(str(row[col]),quote=True)+"</td>"
        for col in columns)+"</tr>" for row in data["rows"])
    # Untrusted strings are always escaped; no executable scripts/form.
    return (f'<!doctype html><html lang="en"><meta charset="utf-8">'
            f'<title>Contracts signed release {p["version"]}</title>'
            f'<body data-release="{p["version"]}">'
            '<h1>Contracts</h1><table><thead><tr>'+head+
            '</tr></thead><tbody>'+body+
            '</tbody></table></body></html>').encode("utf-8")


def server(config):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*_):pass
        def reply(self,status,body,release=None):
            self.send_response(status)
            self.send_header("Content-Type","text/html; charset=utf-8")
            self.send_header("Content-Length",str(len(body)))
            self.send_header("Cache-Control","no-store")
            self.send_header("Content-Security-Policy",
                "default-src 'none'; frame-ancestors 'none'; "
                "base-uri 'none'; form-action 'none'")
            self.send_header("X-Content-Type-Options","nosniff")
            self.send_header("X-OpenAILCAP-ReadOnly","B14-B15-B17")
            if release is not None:
                self.send_header("X-OpenAILCAP-Release",str(release))
            self.end_headers()
            self.wfile.write(body)
        def do_GET(self):
            if self.path!=ROUTE:
                return self.reply(404,b"Not found")
            try:
                old=current_head(config)
                data=load_snapshot(config["snapshot"],
                                   config["publisherUid"],config["publicKeyHex"])
                p=data["payload"]
                if old!=(p["version"],p["manifestHash"],p["draftRevision"]):
                    raise SnapshotDenied("SNAPSHOT_NOT_LATEST_SOURCE")
                html=render(data)
                if current_head(config)!=old:
                    raise SnapshotDenied("B2_SOURCE_MOVED_DURING_RENDER")
                return self.reply(200,html,release=p["version"])
            except SnapshotDenied:
                return self.reply(503,b"Verified published snapshot unavailable")
            except (BrokenPipeError,ConnectionResetError):
                return
        def do_POST(self):
            return self.reply(405,b"Read-only public route")
        do_PUT=do_PATCH=do_DELETE=do_POST
    return ThreadingHTTPServer(("127.0.0.1",0),Handler)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--config",required=True)
    ap.add_argument("--ready",required=True)
    a=ap.parse_args()
    cfgpath=Path(a.config)
    if cfgpath.stat().st_mode&0o077 or cfgpath.stat().st_uid!=os.getuid():
        raise SystemExit("P0B_READONLY_CONFIG_NOT_PRIVATE")
    config=json.loads(cfgpath.read_text())
    if set(config)!={"kernelBase","kernelReadToken","publicKeyHex",
                     "snapshot","publisherUid"}:
        raise SystemExit("P0B_READONLY_CONFIG_INVALID")
    if config["publisherUid"]==os.getuid():
        raise SystemExit("P0B_PUBLISHER_READER_SAME_UID")
    with server(config) as web:
        Path(a.ready).write_text(json.dumps({
            "uid":os.getuid(),"port":web.server_port,
            "readOnly":True}),encoding="utf-8")
        Path(a.ready).chmod(0o644)
        print("P0B_READONLY_READY|"+str(web.server_port),flush=True)
        web.serve_forever(poll_interval=.1)

if __name__=="__main__":
    main()
