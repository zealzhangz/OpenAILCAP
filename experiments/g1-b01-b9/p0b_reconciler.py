"""G1 P0-B single-instance Publisher-only autonomous deployment reconciler.

No root/sudo, Kernel key, Native SQLite or Docker socket. B14 publisher
scoped signed-release + Unix peer-UID read-only Saltcorn oracle -> B15
content-addressed prepare -> B2 single-TX activation. A durable Publisher
journal persists exact changeId and request BEFORE network POST; if response
is lost, query B2 publication.receipt (no blind new ID/replay). Single-machine
research coordinator, not cross-DB XA/production HA or external 2PC.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import sqlite3
import sys
import time
from urllib.error import HTTPError,URLError
from urllib.request import Request,urlopen

from p0b_publisher import publish,PublishRejected
from p0b_readonly_web import load_snapshot,SnapshotDenied
from p0b_signed_release import verify,ReleaseSignatureRejected

KEYS={"kernelBase","kernelReadToken","kernelActivateToken","sourceUrl",
      "sourceToken","nativeSocket","output","publicKeyHex","packTemplate",
      "intervalMs","journal","status"}
SOURCE=("version","manifestHash","draftRevision","outboxHead","rowsDigest")


class Pending(Exception):
    def __init__(self,code,block=False):
        super().__init__(code)
        self.code,self.block=code,block


def canon(x):
    return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(",",":"))


def config(path):
    p=Path(path)
    if p.stat().st_uid!=os.getuid() or p.stat().st_mode&0o077:
        raise RuntimeError("RECONCILER_CONFIG_PRIVATE")
    c=json.loads(p.read_text())
    if (not isinstance(c,dict) or set(c)!=KEYS or
        not all(isinstance(c[k],str) and len(c[k])>24 for k in
                ("kernelReadToken","kernelActivateToken","sourceToken")) or
        not c["kernelBase"].startswith("http://127.0.0.1:") or
        not c["sourceUrl"].startswith("http://127.0.0.1:") or
        not c["sourceUrl"].endswith("/v5/apps/app-a/projection/signed-release") or
        not c["nativeSocket"].startswith("/tmp/s1-b9-derive-") or
        not c["nativeSocket"].endswith("/publisher-ipc/oracle.sock") or
        not c["output"].endswith("/published-private/published.sqlite") or
        not c["journal"].endswith("/published-private/deploy-journal.sqlite") or
        not c["status"].endswith("/published-private/deploy-status.json") or
        not c["packTemplate"].endswith(
            "/public-source/platform-saltcorn/contract-pack.json") or
        len(c["publicKeyHex"])!=64 or
        type(c["intervalMs"]) is not int or
        not 50<=c["intervalMs"]<=2000):
        raise RuntimeError("RECONCILER_CONFIG_INVALID")
    for item in ("output","journal","status"):
        f=Path(c[item])
        if (not str(f).startswith("/tmp/s1-b9-derive-") or
            f.parent.stat().st_uid!=os.getuid() or
            f.parent.stat().st_mode&0o027):
            raise RuntimeError("RECONCILER_OWNER_INVALID")
    return c


def post(url,token,data,timeout=4):
    request=Request(url,data=canon(data).encode(),method="POST",
                    headers={"Authorization":"Bearer "+token,
                             "Content-Type":"application/json"})
    try:
        with urlopen(request,timeout=timeout) as result:
            raw=result.read(131073)
            if len(raw)>131072:raise Pending("HTTP_TOO_LARGE",True)
            return result.status,json.loads(raw)
    except HTTPError as e:
        return e.code,json.loads(e.read(4096))
    except (OSError,URLError,TimeoutError,ValueError):
        raise Pending("HTTP_REPLY_UNKNOWN")


def tool(c,operation,args,high=False):
    return post(c["kernelBase"]+"/v3/apps/app-a/tools/"+operation,
                c["kernelActivateToken"] if high else c["kernelReadToken"],args)


def oracle(c):
    try:
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:
            s.settimeout(3);s.connect(c["nativeSocket"])
            s.sendall(b'{"op":"oracle"}\n')
            with s.makefile("rb") as f:raw=f.readline(131073)
        if len(raw)>131072 or not raw.endswith(b"\n"):
            raise Pending("NATIVE_ORACLE_FRAME_INVALID")
        response=json.loads(raw)
        if not response.get("ok") or not isinstance(response.get("result"),dict):
            raise Pending("NATIVE_ORACLE_REFUSED")
        return response["result"]
    except (OSError,TimeoutError,ValueError):
        raise Pending("NATIVE_ORACLE_UNAVAILABLE")


def init(c):
    with sqlite3.connect(c["journal"]) as db:
        db.execute("CREATE TABLE IF NOT EXISTS deploy("
                   "cid TEXT PRIMARY KEY, command TEXT NOT NULL,"
                   "source_hash TEXT NOT NULL, state TEXT NOT NULL,"
                   "result TEXT,attempts INTEGER NOT NULL DEFAULT 0)")


def jobs(c,states):
    with sqlite3.connect(c["journal"]) as db:
        placeholders=",".join("?" for _ in states)
        return db.execute("SELECT cid,command,state FROM deploy "
                          "WHERE state IN ("+placeholders+") "
                          "ORDER BY cid",tuple(states)).fetchall()


def put(c,cid,cmd,source_hash):
    with sqlite3.connect(c["journal"],timeout=8) as db:
        db.execute("INSERT OR IGNORE INTO deploy "
                   "(cid,command,source_hash,state) VALUES (?,?,?,'PREPARED')",
                   (cid,canon(cmd),source_hash))
        row=db.execute("SELECT command,source_hash,state,result,attempts "
                       "FROM deploy WHERE cid=?",(cid,)).fetchone()
        if row[0]!=canon(cmd) or row[1]!=source_hash:
            raise Pending("JOURNAL_CHANGE_ID_CONFLICT",True)
        return {"state":row[2],"result":json.loads(row[3]) if row[3] else None,
                "attempts":row[4]}


def mark(c,cid,state,result=None,send=False):
    with sqlite3.connect(c["journal"],timeout=8) as db:
        db.execute("UPDATE deploy SET state=?,result=?,"
                   "attempts=attempts+? WHERE cid=?",
                   (state,canon(result) if result is not None else None,
                    1 if send else 0,cid))


def receipt(c,cid,cmd):
    try:
        status,body=tool(c,"publication.receipt",{"changeId":cid},True)
    except Pending:
        mark(c,cid,"UNKNOWN")
        raise Pending("RECEIPT_QUERY_UNKNOWN")
    if status!=200 or body.get("status") not in ("COMMITTED","NOT_FOUND"):
        mark(c,cid,"OPERATOR_REQUIRED",body)
        raise Pending("RECEIPT_UNVERIFIABLE",True)
    if body["status"]=="NOT_FOUND":
        mark(c,cid,"OPERATOR_REQUIRED")
        # Absence of Kernel receipt is not proof of any external effect.
        raise Pending("UNKNOWN_NOT_AUTOMATICALLY_REISSUED",True)
    r=body["result"]
    if (not isinstance(r,dict) or r.get("changeId")!=cid or
        r.get("decision")!="ACTIVATED" or
        r.get("epoch")!=cmd["expectedEpoch"]+1 or
        not isinstance(r.get("active"),dict) or
        r["active"].get("snapshotSha256")!=cmd["candidateSha256"] or
        r["active"].get("outboxHead")!=cmd["expectedOutboxHead"]):
        mark(c,cid,"OPERATOR_REQUIRED",r)
        raise Pending("RECEIPT_MISMATCH",True)
    mark(c,cid,"COMMITTED",r)
    return r


def activate(c,cmd,source_hash):
    cid=cmd["changeId"]
    old=put(c,cid,cmd,source_hash)
    if old["state"]=="COMMITTED":
        return old["result"]
    if old["state"] in ("SUBMITTED","UNKNOWN","OPERATOR_REQUIRED"):
        return receipt(c,cid,cmd)
    if old["state"]!="PREPARED":
        raise Pending("JOURNAL_STATE_INVALID",True)
    mark(c,cid,"SUBMITTED",send=True)
    try:status,result=tool(c,"publication.activate",cmd,True)
    except Pending:
        mark(c,cid,"UNKNOWN")
        raise Pending("ACTIVATION_REPLY_UNKNOWN")
    if status==200 and result.get("decision")=="ACTIVATED":
        mark(c,cid,"COMMITTED",result)
        return result
    if status==409:
        mark(c,cid,"STALE",result)
        raise Pending("ACTIVATION_CAS_STALE")
    mark(c,cid,"OPERATOR_REQUIRED",result)
    raise Pending("ACTIVATION_REJECTED",True)


def step(c):
    status,current=tool(c,"publication.read",{})
    if (status!=200 or not isinstance(current,dict) or
        set(current)!={"app","epoch","active","source"} or
        current["app"]!="app-a" or
        type(current["epoch"]) is not int or
        not isinstance(current["source"],dict) or
        set(current["source"])!=set(SOURCE)):
        raise Pending("B2_SOURCE_NOT_VERIFIABLE")
    source=current["source"]
    active=current["active"]
    if isinstance(active,dict) and {
        k:active[k] for k in SOURCE}==source:
        try:
            candidate=Path(c["output"]).parent/"candidates"/(
                active["snapshotSha256"]+".sqlite")
            snap=load_snapshot(candidate,os.getuid(),c["publicKeyHex"])
            if (snap["artifactSha256"]==active["snapshotSha256"] and
                {k:snap["payload"][k] for k in SOURCE}==source):
                return {"state":"CAUGHT_UP","head":source["outboxHead"],
                        "epoch":current["epoch"]}
        except (OSError,SnapshotDenied,ValueError,KeyError):
            pass
    unknown=jobs(c,("SUBMITTED","UNKNOWN","OPERATOR_REQUIRED"))
    if unknown:
        cid,original,_=unknown[0]
        r=receipt(c,cid,json.loads(original))
        return {"state":"RECONCILED_AFTER_UNKNOWN","epoch":r["epoch"],
                "head":r["active"]["outboxHead"],"changeId":cid}
    physical=oracle(c)
    if physical["cursor"]!=source["outboxHead"]:
        return {"state":"WAIT_NATIVE_CURSOR","head":source["outboxHead"],
                "nativeCursor":physical["cursor"]}
    code,signed=post(c["sourceUrl"],c["sourceToken"],{"after":0,"limit":0})
    if code!=200 or not isinstance(signed,dict) or set(signed)!={
        "signedRelease","signedEvents"}:
        raise Pending("SIGNED_SOURCE_UNAVAILABLE")
    try:payload=verify(signed["signedRelease"],c["publicKeyHex"])
    except ReleaseSignatureRejected:
        raise Pending("SIGNED_SOURCE_INVALID",True)
    if {k:payload[k] for k in SOURCE}!=source:
        raise Pending("SIGNED_SOURCE_MOVED")
    config_pub={k:c[k] for k in (
        "output","kernelBase","kernelReadToken","publicKeyHex","packTemplate")}
    try:
        prepared=publish(config_pub,{**signed,
            "nativeOracle":physical["nativeOracle"]},prepare_only=True)
    except PublishRejected as err:
        raise Pending("B15_PREPARE_"+err.code)
    sha=prepared["snapshotSha256"]
    cmd={"changeId":"p0bauto_"+hashlib.sha256(canon({
             "source":source,"epoch":current["epoch"],"sha":sha
         }).encode()).hexdigest()[:48],
         "expectedEpoch":current["epoch"],
         "candidateSha256":sha,
         "expectedVersion":source["version"],
         "expectedOutboxHead":source["outboxHead"]}
    result=activate(c,cmd,hashlib.sha256(canon(source).encode()).hexdigest())
    return {"state":"ACTIVATED","head":source["outboxHead"],
            "epoch":result["epoch"],"changeId":cmd["changeId"]}


def status(c,row,error=None):
    body={k:row.get(k) for k in (
        "state","head","epoch","nativeCursor","changeId")}
    body.update({"failure":error,"pid":os.getpid()})
    t=Path(c["status"]+".tmp")
    t.write_text(canon(body)+"\n")
    t.chmod(0o600)
    os.replace(t,c["status"])


def loop(c):
    stop=False
    def halt(*_):
        nonlocal stop
        stop=True
    signal.signal(signal.SIGTERM,halt)
    signal.signal(signal.SIGINT,halt)
    status(c,{"state":"STARTING"})
    while not stop:
        try:status(c,step(c))
        except Pending as err:
            status(c,{"state":"OPERATOR_REQUIRED" if err.block else
                       "RETRYING"},err.code)
        time.sleep(c["intervalMs"]/1000)
    status(c,{"state":"STOPPED"})


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--config",required=True)
    p.add_argument("--once",action="store_true")
    args=p.parse_args()
    conf=config(args.config)
    init(conf)
    if args.once:
        try:print("P0B_RECONCILER|"+canon(step(conf)),flush=True)
        except Pending as e:
            print("P0B_RECONCILER|"+canon({
                "state":"OPERATOR_REQUIRED" if e.block else "RETRYING",
                "error":e.code}),flush=True)
    else:loop(conf)
