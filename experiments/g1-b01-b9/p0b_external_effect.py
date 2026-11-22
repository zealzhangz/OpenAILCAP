"""G1 W20 real external side-effect HTTP service, independent Linux UID/SQLite.

Only used in the same B9 research CI fixture. Different from Kernel and
Native/Publisher/Consumer identity. A committed effect and its receipt are
ONE real SQLite transaction; first NEW request deliberately delays its
response AFTER commit, so Kernel receives an actual HTTP timeout with the
effect already committed. A separate authenticated GET by unchanged
changeId reveals the real outcome. No LLM, Docker, or fake in-memory record.
"""
from __future__ import annotations
import argparse
import hashlib
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from hmac import compare_digest
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import time
from urllib.parse import unquote,urlsplit

CID=re.compile(r"^[a-zA-Z0-9_-]{4,96}$")
RECORD=re.compile(r"^[a-f0-9]{18}$")
TABLE="external_effects"
ROUTE="/v1/contract-effects"
MAX_BODY=4096


def canon(x):
    return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(",",":"))


def digest(x):
    return hashlib.sha256(canon(x).encode()).hexdigest()


def scope(db):
    p=Path(db)
    if (not str(p).startswith("/tmp/s1-b9-derive-") or
        not str(p).endswith("/external-private/effects.sqlite")):
        raise RuntimeError("EXTERNAL_DB_SCOPE")
    if (p.parent.stat().st_uid!=os.getuid() or
        p.parent.stat().st_mode&0o077):
        raise RuntimeError("EXTERNAL_DB_PRIVATE")


def initialize(db):
    scope(db)
    with sqlite3.connect(db,timeout=10) as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS external_effects(
          change_id TEXT PRIMARY KEY,
          record_id TEXT NOT NULL,
          contract_no TEXT NOT NULL,
          workflow_version INTEGER NOT NULL,
          workflow_status TEXT NOT NULL,
          action TEXT NOT NULL,
          payload_hash TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS external_receipts(
          change_id TEXT PRIMARY KEY,
          request_hash TEXT NOT NULL,
          response TEXT NOT NULL,
          FOREIGN KEY(change_id) REFERENCES external_effects(change_id)
        );
        """)


def validate(body):
    if not isinstance(body,dict) or set(body)!={
        "changeId","recordId","contractNo","workflowVersion",
        "workflowStatus","action"}:
        return False
    return (isinstance(body["changeId"],str) and CID.fullmatch(body["changeId"])
            and isinstance(body["recordId"],str)
            and RECORD.fullmatch(body["recordId"])
            and isinstance(body["contractNo"],str)
            and re.fullmatch(r"HT-[0-9]{4}-[0-9]{6}",body["contractNo"])
            and type(body["workflowVersion"]) is int
            and body["workflowVersion"]>=2
            and body["workflowStatus"] in (
                "PendingLevel1","PendingLevel2","Approved","Rejected")
            and body["action"]=="CONTRACT_WORKFLOW_NOTIFICATION")


def write_effect(db,body):
    if not validate(body):
        return 422,{"error":"EXTERNAL_PAYLOAD_INVALID"},False
    cid=body["changeId"]
    h=digest(body)
    with sqlite3.connect(db,timeout=10,isolation_level=None) as c:
        try:
            c.execute("BEGIN IMMEDIATE")
            prior=c.execute(
                "SELECT request_hash,response FROM external_receipts "
                "WHERE change_id=?",(cid,)).fetchone()
            if prior:
                if prior[0]!=h:
                    c.rollback()
                    return 409,{"error":"EXTERNAL_CHANGE_ID_REUSED"},False
                c.commit()
                return 200,{**json.loads(prior[1]),"replayed":True},False
            c.execute("INSERT INTO external_effects VALUES (?,?,?,?,?,?,?)",(
                cid,body["recordId"],body["contractNo"],
                body["workflowVersion"],body["workflowStatus"],
                body["action"],h))
            response={"changeId":cid,"decision":"COMMITTED",
                      "recordId":body["recordId"],
                      "contractNo":body["contractNo"],
                      "workflowVersion":body["workflowVersion"],
                      "payloadHash":h,"replayed":False}
            c.execute("INSERT INTO external_receipts VALUES (?,?,?)",
                      (cid,h,canon(response)))
            count=c.execute("SELECT COUNT(*) FROM external_effects").fetchone()[0]
            c.commit()
            return 200,response,count==1
        except BaseException:
            if c.in_transaction:c.rollback()
            raise


def read_receipt(db,cid):
    if not CID.fullmatch(cid):
        return 422,{"error":"EXTERNAL_CHANGE_ID_INVALID"}
    with sqlite3.connect(db,timeout=10,isolation_level=None) as c:
        c.row_factory=sqlite3.Row
        c.execute("BEGIN")
        row=c.execute(
            "SELECT e.*,r.request_hash,r.response FROM external_effects e "
            "JOIN external_receipts r USING(change_id) WHERE change_id=?",
            (cid,)).fetchone()
        c.commit()
    if row is None:
        return 404,{"changeId":cid,"decision":"NOT_FOUND"}
    x=dict(row)
    return 200,{
        "changeId":cid,"decision":"COMMITTED",
        "payloadHash":x["payload_hash"],
        "effect":{"recordId":x["record_id"],
                  "contractNo":x["contract_no"],
                  "workflowVersion":x["workflow_version"],
                  "workflowStatus":x["workflow_status"],
                  "action":x["action"]},
        "receipt":json.loads(x["response"])
    }


def inspect(db):
    scope(db)
    with sqlite3.connect("file:"+str(db)+"?mode=ro",uri=True) as c:
        c.row_factory=sqlite3.Row
        c.execute("BEGIN")
        effects=[dict(x) for x in c.execute(
            "SELECT * FROM external_effects ORDER BY change_id")]
        receipts=[dict(x) for x in c.execute(
            "SELECT * FROM external_receipts ORDER BY change_id")]
        c.commit()
        return {"effects":effects,"receipts":receipts,"uid":os.getuid()}


def serve(config,ready):
    os.umask(0o077)
    p=Path(config)
    if p.stat().st_uid!=os.getuid() or p.stat().st_mode&0o077:
        raise RuntimeError("EXTERNAL_CONFIG_NOT_PRIVATE")
    c=json.loads(p.read_text())
    if (not isinstance(c,dict) or set(c)!={
        "db","sendToken","queryToken","delayFirstMs","port"} or
        type(c["port"]) is not int or not 1024<=c["port"]<=65535 or
        not isinstance(c["sendToken"],str) or len(c["sendToken"])<30 or
        not isinstance(c["queryToken"],str) or len(c["queryToken"])<30 or
        c["sendToken"]==c["queryToken"] or
        type(c["delayFirstMs"]) is not int or
        not 500<=c["delayFirstMs"]<=5000):
        raise RuntimeError("EXTERNAL_CONFIG_INVALID")
    initialize(c["db"])
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*_):pass
        def reply(self,status,data):
            raw=canon(data).encode()
            try:
                self.send_response(status)
                self.send_header("Cache-Control","no-store")
                self.send_header("Content-Type","application/json")
                self.send_header("Content-Length",str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
            except (BrokenPipeError,ConnectionResetError):
                return
        def authorized(self,kind):
            raw=self.headers.get("Authorization","")
            token=c["sendToken"] if kind=="send" else c["queryToken"]
            return (raw.startswith("Bearer ") and
                    compare_digest(raw[7:],token))
        def do_POST(self):
            if urlsplit(self.path).path!=ROUTE:
                return self.reply(404,{"error":"NOT_FOUND"})
            if not self.authorized("send"):
                return self.reply(401,{"error":"EXTERNAL_SENDER_FORBIDDEN"})
            try:
                n=int(self.headers.get("Content-Length","-1"))
                if not 2<=n<=MAX_BODY:
                    return self.reply(422,{"error":"FRAME_SIZE_INVALID"})
                body=json.loads(self.rfile.read(n))
                code,result,first=write_effect(c["db"],body)
                if first:
                    # The actual effect AND receipt were committed to a
                    # physically independent DB before HTTP reply timeout.
                    time.sleep(c["delayFirstMs"]/1000)
                return self.reply(code,result)
            except (ValueError,TypeError,sqlite3.Error):
                return self.reply(422,{"error":"INVALID_REQUEST"})
        def do_GET(self):
            path=urlsplit(self.path).path
            prefix=ROUTE+"/receipts/"
            if not path.startswith(prefix):
                return self.reply(404,{"error":"NOT_FOUND"})
            if not self.authorized("read"):
                return self.reply(401,{"error":"EXTERNAL_RECEIPT_FORBIDDEN"})
            cid=unquote(path[len(prefix):])
            if "/" in cid or len(cid)>96:
                return self.reply(422,{"error":"EXTERNAL_CID_INVALID"})
            status,result=read_receipt(c["db"],cid)
            return self.reply(status,result)
        do_PUT=do_PATCH=do_DELETE=do_POST

    with ThreadingHTTPServer(("127.0.0.1",c["port"]),Handler) as server:
        Path(ready).write_text(canon({
            "port":server.server_port,"pid":os.getpid(),
            "uid":os.getuid()}))
        Path(ready).chmod(0o644)
        print("P0B_EXTERNAL_READY|"+str(server.server_port),flush=True)
        server.serve_forever(poll_interval=.1)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--config")
    p.add_argument("--ready")
    p.add_argument("--inspect")
    a=p.parse_args()
    if a.inspect:
        print("P0B_EXTERNAL_SQL|"+canon(inspect(a.inspect)),flush=True)
    else:
        if not a.config or not a.ready:
            raise SystemExit("EXTERNAL_CONFIG_READY_REQUIRED")
        serve(a.config,a.ready)
