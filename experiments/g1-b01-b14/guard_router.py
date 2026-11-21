"""B14 Ed25519 authenticated source + independent physical SQL auditor.

Separate least-privileged router Linux UID. Source token and release-read token
are never sent to Saltcorn. Guard-only Unix socket exposes only four public
contract fields and durable receipt state. Native auditor runs as a FIFTH Linux UID, distinct from Saltcorn;
Saltcorn UID cannot write auditor code/socket, but can mutate derived DB.
No proof of production linearizability, TLS, HA, multi-tenant ACL, or PII.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import socket
import time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError,URLError
from urllib.request import Request,urlopen
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"g1-b01-b10"))
from router import fetch_native,query_current_release,Refused,ROUTE
from signed_projection import verify_event,SignatureRefused

MAX_EVENTS=1000
FIELDS={"contract_no","title","amount_minor","status"}


def canon(x):
    return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(",",":"))


def native_snapshot(sockpath):
    try:
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as conn:
            conn.settimeout(3)
            conn.connect(sockpath)
            conn.sendall(b'{"op":"snapshot"}\n')
            with conn.makefile("rb") as stream:
                raw=stream.readline(131073)
        if len(raw)>131072 or not raw.endswith(b"\n"):
            raise Refused(503,"GUARD_NATIVE_RESPONSE_INVALID")
        response=json.loads(raw)
    except (OSError,ValueError,TimeoutError):
        raise Refused(503,"GUARD_NATIVE_UNAVAILABLE") from None
    if not isinstance(response,dict) or response.get("ok") is not True:
        raise Refused(503,"GUARD_NATIVE_DRIFT_OR_DENIED")
    result=response.get("result")
    if not isinstance(result,dict) or set(result)!={
        "clean","cursor","rows","receiptCount","mappingCount"
    } or result["clean"] is not True:
        raise Refused(503,"GUARD_NATIVE_DRIFT")
    return result


def source_events(config):
    after=0
    events=[]
    head=None
    while True:
        body=json.dumps({"after":after,"limit":100}).encode()
        req=Request(config["sourceUrl"],method="POST",data=body,
                    headers={"Authorization":"Bearer "+config["sourceToken"],
                             "Content-Type":"application/json"})
        try:
            with urlopen(req,timeout=3) as r:
                if r.status!=200:raise Refused(503,"GUARD_SOURCE_UNAVAILABLE")
                result=json.loads(r.read(131073))
        except (HTTPError,URLError,TimeoutError,OSError,ValueError):
            raise Refused(503,"GUARD_SOURCE_UNAVAILABLE") from None
        if not isinstance(result,dict) or result.get("app")!="app-a" or (
            result.get("after")!=after
        ) or type(result.get("head")) is not int or (
            result["head"]<after
        ) or not isinstance(result.get("events"),list) or (
            len(result["events"])>100
        ):
            raise Refused(503,"GUARD_SOURCE_INVALID")
        if head is None:head=result["head"]
        elif head!=result["head"]:
            # Avoid assembling an unversioned source across concurrent writes.
            raise Refused(503,"GUARD_SOURCE_MOVED_DURING_SCAN")
        for e in result["events"]:
            try:
                verified=verify_event(e,config["publicKeyHex"])
            except SignatureRefused:
                raise Refused(503,"GUARD_SOURCE_SIGNATURE_INVALID") from None
            if (verified["app"]!="app-a" or
                verified["model"]!="model.contracts" or
                type(verified["seq"]) is not int or
                verified["seq"]!=after+1 or
                not isinstance(verified["cells"],dict) or
                set(verified["cells"])!=FIELDS):
                raise Refused(503,"GUARD_SOURCE_EVENT_INVALID")
            unsigned={k:verified[k] for k in (
                "app","seq","model","recordId","version","cells"
            )}
            if hashlib.sha256(canon(unsigned).encode()).hexdigest()!=verified[
                "eventHash"
            ]:
                raise Refused(503,"GUARD_SOURCE_EVENT_HASH_MISMATCH")
            after=verified["seq"]
            events.append(verified)
            if len(events)>MAX_EVENTS:
                raise Refused(503,"GUARD_SOURCE_TOO_LARGE")
        if after==head:break
        if not result["events"]:
            raise Refused(503,"GUARD_SOURCE_GAP")
    latest={}
    for e in events:
        latest[e["cells"]["contract_no"]]=e["cells"]
    return head,latest


def verify(config):
    release=query_current_release(config["kernelPort"],
                                  config["kernelReadToken"])
    if release!={"version":config["version"],
                 "hash":config["manifestHash"]}:
        raise Refused(503,"GUARD_RELEASE_POINTER_MISMATCH")
    head,expected=source_events(config)
    snap=native_snapshot(config["guardSocket"])
    if (snap["cursor"]!=head or snap["receiptCount"]!=head or
        snap["mappingCount"]!=len(expected) or
        type(snap["rows"]) is not list or
        len(snap["rows"])!=len(expected)):
        raise Refused(503,"GUARD_NATIVE_BEHIND_OR_INCONSISTENT")
    actual={}
    for row in snap["rows"]:
        if not isinstance(row,dict) or set(row)!=FIELDS or (
            row["contract_no"] in actual
        ):
            raise Refused(503,"GUARD_NATIVE_ROW_INVALID")
        actual[row["contract_no"]]=row
    if actual!=expected:
        raise Refused(503,"GUARD_AUTHORITY_NATIVE_MISMATCH")
    return expected


def serve(config,ready):
    class Handler(BaseHTTPRequestHandler):
        protocol_version="HTTP/1.1"
        def log_message(self,*_):pass
        def reply(self,code,payload,media="application/json"):
            body=(json.dumps(payload,separators=(",",":")).encode()
                  if isinstance(payload,dict) else payload)
            self.send_response(code)
            self.send_header("Content-Type",media)
            self.send_header("Content-Length",str(len(body)))
            self.send_header("Cache-Control","no-store")
            self.send_header("X-Content-Type-Options","nosniff")
            self.end_headers()
            self.wfile.write(body)
        def do_GET(self):
            if self.path=="/_health":
                return self.reply(200,{"guard":"B14_ED25519_AND_INDEPENDENT_SQL",
                                       "activeVersion":config["version"]})
            if self.path!=ROUTE:
                return self.reply(404,{"error":"GUARD_ROUTE_NOT_EXPOSED"})
            try:
                expected=verify(config)
                body=fetch_native(config["nativePort"],config["marker"])
                # Recheck B2 + physical native rows after downstream HTTP read.
                again=verify(config)
                if expected!=again or any(
                    no.encode() not in body for no in expected
                ):
                    raise Refused(503,"GUARD_RENDERED_CONTENT_STALE")
                self.send_response(200)
                self.send_header("Content-Type","text/html; charset=utf-8")
                self.send_header("Content-Length",str(len(body)))
                self.send_header("Cache-Control","no-store")
                self.send_header("X-OpenAILCAP-Guard","B14-ED25519-SQL-VERIFIED")
                self.send_header("X-OpenAILCAP-Release",str(config["version"]))
                self.end_headers()
                self.wfile.write(body)
            except Refused as exc:
                self.reply(exc.status,{"error":exc.code})
            except (BrokenPipeError,ConnectionResetError):
                pass
        def do_POST(self):
            self.reply(405,{"error":"GUARD_PUBLIC_WRITE_DISABLED"})
        do_PUT=do_POST
        do_PATCH=do_POST
        do_DELETE=do_POST
    server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
    Path(ready).write_text(json.dumps({"port":server.server_port,
                                      "uid":os.getuid()}))
    Path(ready).chmod(0o644)
    print("S1_B13_GUARD_READY|"+json.dumps({"uid":os.getuid()}),flush=True)
    try:server.serve_forever(poll_interval=.1)
    finally:server.server_close()


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--config",required=True)
    p.add_argument("--ready",required=True)
    args=p.parse_args()
    cfgpath=Path(args.config)
    if cfgpath.stat().st_mode&0o077:
        raise SystemExit("GUARD_CONFIG_NOT_PRIVATE")
    cfg=json.loads(cfgpath.read_text())
    if set(cfg)!={"sourceUrl","sourceToken","kernelPort",
                 "kernelReadToken","guardSocket","nativePort",
                 "marker","version","manifestHash","publicKeyHex"} or (
        not cfg["sourceUrl"].startswith("http://127.0.0.1:")
    ) or not cfg["sourceUrl"].endswith(
        "/v5/apps/app-a/projection/signed-pull"
    ) or not cfg["guardSocket"].startswith(
        "/tmp/s1-b13-project-"
    ) or not cfg["guardSocket"].endswith("/b14-audit-ipc/guard.sock") or (
        any(len(cfg[k])<24 for k in ("sourceToken","kernelReadToken"))
    ):
        raise SystemExit("GUARD_CONFIG_INVALID")
    if len(bytes.fromhex(cfg["publicKeyHex"]))!=32:
        raise SystemExit("GUARD_PUBLIC_KEY_INVALID")
    serve(cfg,args.ready)


if __name__=="__main__":
    main()
