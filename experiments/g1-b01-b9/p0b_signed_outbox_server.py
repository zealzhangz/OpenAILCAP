"""G1 P0-B same-authority B14 signed B11 source with fixed restartable port.

Kernel UID only. Signs *only* events pulled from actual B2 transactional
b11_outbox, never caller-supplied JSON. Stable local port allows genuine
source outage/recovery while a distinct consumer UID stays alive.
Research-only localhost and ephemeral credentials; no TLS/HA/PKI.
"""
from __future__ import annotations
import argparse
from hmac import compare_digest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"g1-b01-b11"))
sys.path.insert(0,str(HERE.parent/"g1-b01-b14"))
from projection_source import pull,ProjectionRefused
from signed_projection import sign_event
from p0b_signed_release import sign_from_current_db

PATH="/v5/apps/app-a/projection/signed-pull"
PUBLISH_PATH="/v5/apps/app-a/projection/signed-release"


def serve(config,ready):
    conf=Path(config)
    if (conf.stat().st_uid!=os.getuid() or
        conf.stat().st_mode&0o077):
        raise RuntimeError("P0B_SOURCE_CONFIG_NOT_PRIVATE")
    cfg=json.loads(conf.read_text())
    if set(cfg)!={"db","key","token","port","publisherToken","template"} or (
        type(cfg["port"]) is not int or
        not 1024<=cfg["port"]<=65535 or
        not isinstance(cfg["token"],str) or len(cfg["token"])<32 or
        not isinstance(cfg["publisherToken"],str) or
        len(cfg["publisherToken"])<32 or
        cfg["token"]==cfg["publisherToken"] or
        not cfg["template"].startswith("/tmp/s1-b9-derive-") or
        not cfg["template"].endswith("/public-source/platform-saltcorn/contract-pack.json")):
        raise RuntimeError("P0B_SOURCE_CONFIG_INVALID")
    key=Path(cfg["key"])
    if key.stat().st_uid!=os.getuid() or key.stat().st_mode&0o077:
        raise RuntimeError("P0B_SIGNING_PRIVATE_KEY_EXPOSED")
    if not (cfg["db"].startswith("/tmp/s1-b9-derive-") and
            cfg["db"].endswith("/authority-private/authority.sqlite")):
        raise RuntimeError("P0B_SOURCE_AUTHORITY_PATH_INVALID")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*_):pass
        def answer(self,status,body):
            raw=json.dumps(body,separators=(",",":")).encode()
            self.send_response(status)
            self.send_header("Content-Type","application/json")
            self.send_header("Cache-Control","no-store")
            self.send_header("Content-Length",str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        def do_POST(self):
            route=urlsplit(self.path).path
            if route not in (PATH,PUBLISH_PATH):
                return self.answer(404,{"error":"SOURCE_ROUTE_NOT_EXPOSED"})
            token=self.headers.get("Authorization","")
            required=(cfg["token"] if route==PATH
                      else cfg["publisherToken"])
            if not (token.startswith("Bearer ") and
                    compare_digest(token[7:],required)):
                return self.answer(401,{"error":"SIGNED_SOURCE_TOKEN_REQUIRED"})
            try:
                size=int(self.headers.get("Content-Length","-1"))
                if size<2 or size>2048:
                    return self.answer(422,{"error":"SOURCE_FRAME_INVALID"})
                args=json.loads(self.rfile.read(size))
                if not isinstance(args,dict) or set(args)!={"after","limit"}:
                    return self.answer(422,{"error":"SOURCE_QUERY_INVALID"})
                if route==PUBLISH_PATH:
                    if args!={"after":0,"limit":0}:
                        return self.answer(422,{"error":"PUBLISH_SIGNED_RELEASE_QUERY_INVALID"})
                    signed=sign_from_current_db(cfg["db"],cfg["key"],cfg["template"])
                    if len(signed["signedEvents"])>1000:
                        return self.answer(422,{"error":"PUBLISH_SIGNED_EVENT_LIMIT"})
                    return self.answer(200,signed)
                data=pull(cfg["db"],"app-a",args["after"],args["limit"])
                data["events"]=[sign_event(e,cfg["key"]) for e in data["events"]]
                return self.answer(200,data)
            except ProjectionRefused as exc:
                return self.answer(exc.status,{"error":exc.code})
            except (ValueError,TypeError,KeyError):
                return self.answer(422,{"error":"SOURCE_INPUT_INVALID"})
        def do_GET(self):
            return self.answer(405,{"error":"ONLY_B14_SIGNED_PULL"})
        do_PUT=do_PATCH=do_DELETE=do_GET

    with ThreadingHTTPServer(("127.0.0.1",cfg["port"]),Handler) as server:
        out=Path(ready)
        out.write_text(json.dumps({
            "port":server.server_port,"uid":os.getuid(),"pid":os.getpid()
        }))
        out.chmod(0o644)
        print("P0B_SOURCE_READY|"+str(server.server_port),flush=True)
        server.serve_forever(poll_interval=.1)


if __name__=="__main__":
    pa=argparse.ArgumentParser()
    pa.add_argument("--config",required=True)
    pa.add_argument("--ready",required=True)
    args=pa.parse_args()
    serve(args.config,args.ready)
