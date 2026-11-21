"""S1 B10: a scoped, live, read-only traffic router over REAL Saltcorn servers.

This is a research-only ThreadingHTTPServer, not a production reverse proxy.
Its ONLY public business route is GET /view/s1_contract_list. Backend
instances are immutable-by-convention, but Saltcorn itself can be edited
by its OS owner; this router never forwards /field, /admin, POST, cookies or
the B2 Domain Kernel's credentials. The trusted deployment controller has
a separate one-use admin bearer. A release.read-only Kernel token allows
route SWITCH only to the currently published and verified B2 release.

In-flight GET captures one immutable (version, backend) routing tuple before
a pointer switch. It never mixes v1/v2 in a request. No persistent switch
journal, no crash failover, no cross-process HA; do not claim W17/W24 PASS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError,URLError
from urllib.parse import urlsplit
from urllib.request import Request,build_opener,HTTPRedirectHandler


MAX_BYTES=2*1024*1024
ROUTE="/view/s1_contract_list"
CHANGE=re.compile(r"^[a-zA-Z0-9_-]{4,96}$")
HASH=re.compile(r"^[0-9a-f]{64}$")


class Refused(Exception):
    def __init__(self,status,code):
        self.status=status
        self.code=code
        super().__init__(code)


def canon(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),
                      ensure_ascii=False)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        return None


def fetch_native(port,marker):
    if type(port) is not int or not 1<=port<=65535:
        raise Refused(422,"BACKEND_PORT_INVALID")
    if not isinstance(marker,str) or not 6<=len(marker)<=80 or not (
        marker.startswith("HT-2026-")
    ):
        raise Refused(422,"MARKER_INVALID")
    request=Request("http://127.0.0.1:"+str(port)+ROUTE,
                    headers={"Accept":"text/html"},
                    method="GET")
    try:
        with build_opener(NoRedirect()).open(request,timeout=6) as res:
            code=res.status
            media=res.headers.get("Content-Type","")
            data=res.read(MAX_BYTES+1)
    except (HTTPError,URLError,TimeoutError,OSError,ValueError) as exc:
        raise Refused(503,"BACKEND_READINESS_FAILED") from None
    if code!=200 or "text/html" not in media.lower() or (
        len(data)>MAX_BYTES or marker.encode("utf-8") not in data
    ):
        raise Refused(503,"BACKEND_BUSINESS_READINESS_FAILED")
    return data


def query_current_release(kernel_port,token):
    if type(kernel_port) is not int or not 1<=kernel_port<=65535:
        raise Refused(500,"KERNEL_CONFIGURATION_BAD")
    req=Request(
        "http://127.0.0.1:"+str(kernel_port)+
        "/v3/apps/app-a/tools/release.read",
        data=b"{}",
        method="POST",
        headers={"Authorization":"Bearer "+token,
                 "Content-Type":"application/json"})
    try:
        with build_opener(NoRedirect()).open(req,timeout=5) as res:
            data=json.loads(res.read(131072))
    except (HTTPError,URLError,TimeoutError,OSError,ValueError,
            json.JSONDecodeError):
        raise Refused(503,"KERNEL_RELEASE_NOT_VERIFIABLE") from None
    if not isinstance(data,dict) or set(data)!={
        "version","manifestHash","draftRevision","definitions"
    }:
        raise Refused(503,"KERNEL_RELEASE_SHAPE_BAD")
    if type(data["version"]) is not int or not HASH.fullmatch(
        str(data["manifestHash"])
    ):
        raise Refused(503,"KERNEL_RELEASE_INVALID")
    manifest=hashlib.sha256(canon(data["definitions"]).encode()).hexdigest()
    if manifest!=data["manifestHash"]:
        raise Refused(503,"KERNEL_RELEASE_HASH_MISMATCH")
    return {"version":data["version"],"hash":data["manifestHash"]}


@dataclass(frozen=True)
class Candidate:
    version:int
    manifest_hash:str
    port:int
    marker:str


class Router:
    def __init__(self,kernel_port,kernel_read_token,admin_token):
        if not all(isinstance(t,str) and len(t)>=32 for t in
                   (kernel_read_token,admin_token)):
            raise ValueError("B10_EPHEMERAL_CREDENTIAL_TOO_SHORT")
        self.kernel_port=kernel_port
        self.kernel_token=kernel_read_token
        self.admin_token=admin_token
        self.lock=threading.RLock()
        self.candidates={}
        self.active=None
        self.epoch=0
        self.receipts={}
        self.inflight=0

    def snapshot(self):
        with self.lock:
            return {"epoch":self.epoch,
                    "activeVersion":self.active.version if self.active else None,
                    "activeManifestHash":(
                        self.active.manifest_hash if self.active else None),
                    "inflight":self.inflight,"candidateVersions":
                    sorted(self.candidates)}
    @staticmethod
    def shape(args,keys):
        if not isinstance(args,dict) or set(args)!=set(keys):
            raise Refused(422,"ARGUMENTS_INVALID")

    def authorize(self,header):
        from hmac import compare_digest
        if not isinstance(header,str) or not (
                header.startswith("Bearer ") and
                compare_digest(header[7:],self.admin_token)):
            raise Refused(401,"ADMIN_AUTH_REQUIRED")

    def register(self,body):
        self.shape(body,("version","manifestHash","port","marker"))
        version=body["version"]
        manifest=body["manifestHash"]
        if type(version) is not int or version<1 or not isinstance(
            manifest,str
        ) or not HASH.fullmatch(manifest):
            raise Refused(422,"CANDIDATE_INVALID")
        candidate=Candidate(version,manifest,body["port"],body["marker"])
        with self.lock:
            current=query_current_release(
                self.kernel_port,self.kernel_token)
            if current!={"version":version,"hash":manifest}:
                raise Refused(409,"NOT_CURRENT_VERIFIED_RELEASE")
            fetch_native(candidate.port,candidate.marker)
            old=self.candidates.get(version)
            if old is not None and old!=candidate:
                raise Refused(409,"VERSION_ALREADY_REGISTERED")
            self.candidates[version]=candidate
            return {"registered":True,"version":version,
                    "manifestHash":manifest,"businessReadiness":True,
                    "alreadyRegistered":old is not None}

    def switch(self,body):
        self.shape(body,("changeId","expectedEpoch","expectedFromVersion",
                         "targetVersion","manifestHash"))
        cid=body["changeId"]
        if not isinstance(cid,str) or not CHANGE.fullmatch(cid):
            raise Refused(422,"CHANGE_ID_INVALID")
        if type(body["expectedEpoch"]) is not int or (
            body["expectedFromVersion"] is not None and
            type(body["expectedFromVersion"]) is not int
        ) or type(body["targetVersion"]) is not int or not isinstance(
            body["manifestHash"],str
        ) or not HASH.fullmatch(body["manifestHash"]):
            raise Refused(422,"SWITCH_COMMAND_INVALID")
        fingerprint=hashlib.sha256(canon(body).encode()).hexdigest()
        with self.lock:
            old=self.receipts.get(cid)
            if old is not None:
                if old["fingerprint"]!=fingerprint:
                    raise Refused(409,"CHANGE_ID_REUSED")
                return {**old["result"],"replayed":True}
            if body["expectedEpoch"]!=self.epoch or (
                body["expectedFromVersion"]!=(
                    self.active.version if self.active else None)
            ):
                raise Refused(409,"ROUTE_EPOCH_CONFLICT")
            candidate=self.candidates.get(body["targetVersion"])
            if candidate is None:
                raise Refused(404,"CANDIDATE_NOT_REGISTERED")
            if candidate.manifest_hash!=body["manifestHash"]:
                raise Refused(409,"CANDIDATE_HASH_CONFLICT")
            release=query_current_release(self.kernel_port,self.kernel_token)
            if release!={"version":candidate.version,
                         "hash":candidate.manifest_hash}:
                raise Refused(409,"KERNEL_PUBLISH_POINTER_MISMATCH")
            fetch_native(candidate.port,candidate.marker)
            self.epoch+=1
            self.active=candidate
            result={"decision":"SWITCHED","version":candidate.version,
                    "epoch":self.epoch,"manifestHash":candidate.manifest_hash,
                    "replayed":False}
            self.receipts[cid]={"fingerprint":fingerprint,"result":result}
            return result

    def capture(self):
        with self.lock:
            if self.active is None:
                raise Refused(503,"NO_ACTIVE_VERSION")
            self.inflight+=1
            return self.active,self.epoch

    def finish(self):
        with self.lock:self.inflight-=1


def serve(state,ready):
    class Handler(BaseHTTPRequestHandler):
        protocol_version="HTTP/1.1"

        def log_message(self,*_):pass

        def reply(self,status,body,media="application/json"):
            if isinstance(body,dict):
                payload=canon(body).encode()
            else:payload=body
            self.send_response(status)
            self.send_header("Content-Type",media)
            self.send_header("Content-Length",str(len(payload)))
            self.send_header("Cache-Control","no-store")
            self.send_header("X-Content-Type-Options","nosniff")
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            if self.path=="/_health":
                return self.reply(200,state.snapshot())
            if self.path!=ROUTE:
                return self.reply(404,{"error":"PUBLIC_PATH_NOT_EXPOSED"})
            try:
                candidate,epoch=state.capture()
            except Refused as e:
                return self.reply(e.status,{"error":e.code})
            try:
                # Test-only deterministic in-flight interval: route tuple
                # captured BEFORE sleep, so an atomic switch cannot redirect
                # this request into a newer backend.
                wait=self.headers.get("X-B10-Test-Hold-Ms","0")
                if not wait.isascii() or not wait.isdigit() or int(wait)>2500:
                    raise Refused(422,"HOLD_HEADER_INVALID")
                if int(wait):time.sleep(int(wait)/1000)
                body=fetch_native(candidate.port,candidate.marker)
                # The label on the response is the EXACT captured tuple.
                self.send_response(200)
                self.send_header("Content-Type","text/html; charset=utf-8")
                self.send_header("Content-Length",str(len(body)))
                self.send_header("Cache-Control","no-store")
                self.send_header("X-OpenAILCAP-Release",str(candidate.version))
                self.send_header("X-OpenAILCAP-Route-Epoch",str(epoch))
                self.send_header("X-Content-Type-Options","nosniff")
                self.end_headers()
                self.wfile.write(body)
            except Refused as e:
                self.reply(e.status,{"error":e.code})
            except (BrokenPipeError,ConnectionResetError):
                pass
            finally:state.finish()

        def do_POST(self):
            if self.path not in ("/_admin/register","/_admin/switch"):
                return self.reply(405,{"error":"PUBLIC_WRITE_DISABLED"})
            try:
                state.authorize(self.headers.get("Authorization",""))
                if self.headers.get("Content-Type","").split(";")[0]!=(
                    "application/json"
                ):
                    raise Refused(415,"JSON_REQUIRED")
                size=int(self.headers.get("Content-Length","0"))
                if size<2 or size>8192:
                    raise Refused(413,"BODY_SIZE_INVALID")
                body=json.loads(self.rfile.read(size))
                result=(state.register(body) if self.path.endswith(
                    "/register") else state.switch(body))
                return self.reply(200,result)
            except Refused as e:
                return self.reply(e.status,{"error":e.code})
            except (ValueError,json.JSONDecodeError):
                return self.reply(422,{"error":"INVALID_JSON"})

        def do_PUT(self):
            self.reply(405,{"error":"PUBLIC_WRITE_DISABLED"})
        def do_DELETE(self):
            self.reply(405,{"error":"PUBLIC_WRITE_DISABLED"})

    server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
    PathReady=__import__("pathlib").Path
    PathReady(ready).write_text(canon({
        "port":server.server_port,"uid":os.getuid(),
        "scope":"S1_B10_EPHEMERAL_ROUTE_CONTROL"
    }))
    PathReady(ready).chmod(0o644)
    print("S1_B10_ROUTER_READY|"+canon({"uid":os.getuid()}),flush=True)
    try:server.serve_forever(poll_interval=.1)
    finally:server.server_close()


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--config",required=True)
    p.add_argument("--ready",required=True)
    args=p.parse_args()
    path=__import__("pathlib").Path(args.config)
    if path.stat().st_mode & 0o077:
        raise SystemExit("ROUTER_CONFIG_WORLD_READABLE")
    cfg=json.loads(path.read_text())
    if set(cfg)!={"kernelPort","kernelReadToken","adminToken"}:
        raise SystemExit("ROUTER_CONFIG_SHAPE")
    serve(Router(cfg["kernelPort"],cfg["kernelReadToken"],
                 cfg["adminToken"]),args.ready)
