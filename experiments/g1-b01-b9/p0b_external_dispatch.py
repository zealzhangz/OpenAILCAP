"""G1 W20 Kernel-UID adapter: genuine external business UNKNOWN & changeId.

This is NOT a generic external effects framework. Source is a REAL B2
workflow-advanced record, checked in original private authority.sqlite and
same B11 transactional outbox. A deterministic changeId and exact request
are persisted BEFORE one actual external POST. On response timeout state is
UNKNOWN; NEVER retry with a new ID. The external response is independently
queried by original changeId and crosschecked against its business effect
and receipt, then confirmed in B2. Separate external UID owns side-effect DB.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
from urllib.error import HTTPError,URLError
from urllib.parse import quote
from urllib.request import Request,urlopen

from p0b_authority_business import (
    read_business_on_connection,AuthorityDataRejected)

FIELDS=("recordId","contractNo","workflowVersion","workflowStatus","action")
ACTION="CONTRACT_WORKFLOW_NOTIFICATION"
DB_TABLE="p0b_external_dispatch_jobs"
MAX_REPLY=16384


class ExternalDenied(Exception):
    def __init__(self,code):
        self.code=code
        super().__init__(code)


def canon(x):
    return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(",",":"))


def digest(x):
    return hashlib.sha256(canon(x).encode()).hexdigest()


def read_cfg(path):
    p=Path(path)
    if p.stat().st_uid!=os.getuid() or p.stat().st_mode&0o077:
        raise ExternalDenied("KERNEL_EXTERNAL_CONFIG_DAC")
    cfg=json.loads(p.read_text())
    if (not isinstance(cfg,dict) or
        set(cfg)!={"authorityDb","externalBase","sendToken","queryToken",
                   "timeoutMs"} or
        not cfg["authorityDb"].startswith("/tmp/s1-b9-derive-") or
        not cfg["authorityDb"].endswith("/authority-private/authority.sqlite") or
        not cfg["externalBase"].startswith("http://127.0.0.1:") or
        type(cfg["timeoutMs"]) is not int or
        not 70<=cfg["timeoutMs"]<=400 or
        len(cfg["sendToken"])<30 or len(cfg["queryToken"])<30 or
        cfg["sendToken"]==cfg["queryToken"]):
        raise ExternalDenied("KERNEL_EXTERNAL_CONFIG_INVALID")
    if (Path(cfg["authorityDb"]).parent.stat().st_uid!=os.getuid() or
        Path(cfg["authorityDb"]).parent.stat().st_mode&0o077):
        raise ExternalDenied("KERNEL_EXTERNAL_DB_SCOPE")
    return cfg


def connect(dbpath):
    db=sqlite3.connect(dbpath,timeout=10,isolation_level=None)
    db.row_factory=sqlite3.Row
    db.execute("PRAGMA busy_timeout=10000")
    return db


def ensure(dbpath):
    with connect(dbpath) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS p0b_external_dispatch_jobs(
          change_id TEXT PRIMARY KEY,
          record_id TEXT NOT NULL,
          record_version INTEGER NOT NULL,
          request_json TEXT NOT NULL,
          request_hash TEXT NOT NULL,
          state TEXT NOT NULL,
          attempts INTEGER NOT NULL,
          remote_receipt TEXT
        )""")


def source_record(db,record_id):
    if not isinstance(record_id,str) or not re.fullmatch(r"[0-9a-f]{18}",record_id):
        raise ExternalDenied("EXTERNAL_RECORD_ID_INVALID")
    try:
        b11=read_business_on_connection(db)
    except AuthorityDataRejected as err:
        raise ExternalDenied(err.code) from None
    item=db.execute(
        "SELECT record_id,version,content FROM records "
        "WHERE app='app-a' AND model='model.contracts' AND record_id=?",
        (record_id,)).fetchone()
    if item is None:
        raise ExternalDenied("EXTERNAL_WORKFLOW_RECORD_NOT_FOUND")
    cells=json.loads(item["content"])
    events=[e for e in b11["events"] if e["recordId"]==record_id]
    if (not events or
        events[-1]["version"]!=item["version"] or
        events[-1]["cells"]!=cells or
        cells["status"]!="PendingLevel1" or
        item["version"]!=2):
        raise ExternalDenied("EXTERNAL_WORKFLOW_SOURCE_NOT_CONFIRMED")
    return {
        "recordId":record_id,"contractNo":cells["contract_no"],
        "workflowVersion":item["version"],"workflowStatus":cells["status"],
        "action":ACTION}


def make_command(dbpath,record_id):
    with connect(dbpath) as db:
        db.execute("BEGIN")
        try:
            payload=source_record(db,record_id)
            db.commit()
        except BaseException:
            if db.in_transaction:db.rollback()
            raise
    cid="p0bnotify_"+hashlib.sha256(
        (payload["recordId"]+":"+str(payload["workflowVersion"])).encode()
    ).hexdigest()[:40]
    return {"changeId":cid,**payload}


def post(url,token,payload,timeout):
    request=Request(url,data=canon(payload).encode(),method="POST",headers={
        "Authorization":"Bearer "+token,
        "Content-Type":"application/json"})
    try:
        with urlopen(request,timeout=timeout) as res:
            data=res.read(MAX_REPLY)
            return res.status,json.loads(data)
    except HTTPError as err:
        return err.code,json.loads(err.read(MAX_REPLY))
    except (OSError,URLError,TimeoutError,ValueError):
        raise ExternalDenied("EXTERNAL_REPLY_UNKNOWN") from None


def get(url,token):
    req=Request(url,method="GET",
                headers={"Authorization":"Bearer "+token})
    try:
        with urlopen(req,timeout=3) as r:
            return r.status,json.loads(r.read(MAX_REPLY))
    except HTTPError as e:
        return e.code,json.loads(e.read(MAX_REPLY))
    except (OSError,URLError,TimeoutError,ValueError):
        raise ExternalDenied("EXTERNAL_RECEIPT_QUERY_UNKNOWN") from None


def job(dbpath,cid):
    with connect(dbpath) as db:
        row=db.execute(
            "SELECT * FROM p0b_external_dispatch_jobs WHERE change_id=?",
            (cid,)).fetchone()
    return dict(row) if row else None


def new_send(cfg,record_id):
    command=make_command(cfg["authorityDb"],record_id)
    cid=command["changeId"]
    hash_request=digest(command)
    with connect(cfg["authorityDb"]) as db:
        try:
            db.execute("BEGIN IMMEDIATE")
            # Source must STILL match exactly under the same B2 TX as
            # durable SUBMITTED journal creation.
            expected={"changeId":cid,**source_record(db,record_id)}
            if expected!=command:
                raise ExternalDenied("EXTERNAL_SOURCE_MOVED")
            existing=db.execute(
                "SELECT request_hash,state,remote_receipt "
                "FROM p0b_external_dispatch_jobs WHERE change_id=?",
                (cid,)).fetchone()
            if existing:
                if existing["request_hash"]!=hash_request:
                    raise ExternalDenied("EXTERNAL_CHANGE_ID_REUSED")
                db.commit()
                return {"decision":existing["state"],"changeId":cid,
                        "attempts":job(cfg["authorityDb"],cid)["attempts"],
                        "externalPostReplayed":False}
            db.execute(
                "INSERT INTO p0b_external_dispatch_jobs VALUES "
                "(?,?,?,?,?,'SUBMITTED',1,NULL)",
                (cid,record_id,command["workflowVersion"],
                 canon(command),hash_request))
            db.commit()
        except BaseException:
            if db.in_transaction:db.rollback()
            raise
    try:
        code,result=post(cfg["externalBase"]+"/v1/contract-effects",
                         cfg["sendToken"],command,cfg["timeoutMs"]/1000)
    except ExternalDenied:
        with connect(cfg["authorityDb"]) as db:
            db.execute(
                "UPDATE p0b_external_dispatch_jobs SET state='UNKNOWN' "
                "WHERE change_id=? AND state='SUBMITTED'",(cid,))
        return {"decision":"UNKNOWN","changeId":cid,"attempts":1,
                "safeToAutoRetry":False}
    if code==200 and result.get("decision")=="COMMITTED" and (
        result.get("payloadHash")==hash_request):
        with connect(cfg["authorityDb"]) as db:
            db.execute(
                "UPDATE p0b_external_dispatch_jobs "
                "SET state='CONFIRMED',remote_receipt=? "
                "WHERE change_id=? AND state='SUBMITTED'",
                (canon(result),cid))
        return {"decision":"CONFIRMED","changeId":cid,"attempts":1,
                "safeToAutoRetry":False}
    with connect(cfg["authorityDb"]) as db:
        db.execute(
            "UPDATE p0b_external_dispatch_jobs SET state='OPERATOR_REQUIRED' "
            "WHERE change_id=?",(cid,))
    return {"decision":"OPERATOR_REQUIRED","changeId":cid,
            "attempts":1,"externalStatus":code}


def reconcile(cfg,record_id):
    command=make_command(cfg["authorityDb"],record_id)
    cid=command["changeId"]
    row=job(cfg["authorityDb"],cid)
    if row is None:
        return {"decision":"NOT_DISPATCHED","changeId":cid}
    if row["request_json"]!=canon(command) or row["request_hash"]!=digest(command):
        raise ExternalDenied("EXTERNAL_RECONCILE_SOURCE_CHANGED")
    if row["state"]=="CONFIRMED":
        return {"decision":"CONFIRMED","changeId":cid,
                "attempts":row["attempts"],"replayed":True}
    try:
        code,body=get(cfg["externalBase"]+"/v1/contract-effects/receipts/"+
                      quote(cid,safe=""),cfg["queryToken"])
    except ExternalDenied:
        return {"decision":"UNKNOWN","changeId":cid,
                "attempts":row["attempts"],"safeToAutoRetry":False}
    if code==404 and body.get("decision")=="NOT_FOUND":
        with connect(cfg["authorityDb"]) as db:
            db.execute("UPDATE p0b_external_dispatch_jobs "
                       "SET state='OPERATOR_REQUIRED' WHERE change_id=?",(cid,))
        return {"decision":"OPERATOR_REQUIRED","changeId":cid,
                "attempts":row["attempts"],"safeToAutoRetry":False}
    if code!=200 or body.get("decision")!="COMMITTED":
        raise ExternalDenied("EXTERNAL_RECEIPT_INVALID")
    if (body.get("changeId")!=cid or
        body.get("payloadHash")!=digest(command) or
        not isinstance(body.get("effect"),dict) or
        body["effect"]!={k:command[k] for k in FIELDS} or
        body.get("receipt",{}).get("payloadHash")!=digest(command)):
        raise ExternalDenied("EXTERNAL_BUSINESS_RECEIPT_CONFLICT")
    with connect(cfg["authorityDb"]) as db:
        db.execute("UPDATE p0b_external_dispatch_jobs "
                   "SET state='CONFIRMED',remote_receipt=? "
                   "WHERE change_id=? AND state IN ('SUBMITTED','UNKNOWN',"
                   "'OPERATOR_REQUIRED')",
                   (canon(body["receipt"]),cid))
    return {"decision":"CONFIRMED","changeId":cid,
            "attempts":row["attempts"],"replayed":False,
            "receiptVerified":True}


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--config",required=True)
    p.add_argument("--record-id",required=True)
    p.add_argument("--action",choices=("send","reconcile","inspect"),
                   required=True)
    a=p.parse_args()
    try:
        cfg=read_cfg(a.config)
        ensure(cfg["authorityDb"])
        if a.action=="send":
            result=new_send(cfg,a.record_id)
        elif a.action=="reconcile":
            result=reconcile(cfg,a.record_id)
        else:
            cmd=make_command(cfg["authorityDb"],a.record_id)
            result=job(cfg["authorityDb"],cmd["changeId"])
        print("P0B_EXTERNAL_DISPATCH|"+canon(result),flush=True)
    except (ExternalDenied,ValueError,sqlite3.Error) as exc:
        print("P0B_EXTERNAL_REJECT|"+getattr(
            exc,"code","EXTERNAL_SQL_OR_INPUT_INVALID"),flush=True)
        raise SystemExit(3) from None
