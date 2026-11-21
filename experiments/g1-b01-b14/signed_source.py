"""B14 Kernel-UID-only signing sidecar over the existing B2 atomic outbox."""
from __future__ import annotations
import argparse
import json
import os
import secrets
import sys
from pathlib import Path
from hmac import compare_digest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"g1-b01-b11"))
from projection_source import pull,ProjectionRefused
from signed_projection import make_keypair,sign_event

PATH="/v5/apps/app-a/projection/signed-pull"


def serve(config,ready):
    cfg_path=Path(config)
    if cfg_path.stat().st_mode&0o077:
        raise RuntimeError("SOURCE_CONFIG_NOT_PRIVATE")
    cfg=json.loads(cfg_path.read_text())
    if set(cfg)!={"db","privateKey","token"} or len(cfg["token"])<24:
        raise RuntimeError("SOURCE_CONFIG_INVALID")
    if Path(cfg["privateKey"]).stat().st_mode&0o077:
        raise RuntimeError("PRIVATE_SIGNING_KEY_EXPOSED")
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*_):pass
        def reply(self,status,body):
            raw=json.dumps(body,separators=(",",":")).encode()
            self.send_response(status)
            self.send_header("Content-Type","application/json")
            self.send_header("Content-Length",str(len(raw)))
            self.send_header("Cache-Control","no-store")
            self.end_headers()
            self.wfile.write(raw)
        def do_POST(self):
            if urlsplit(self.path).path!=PATH:
                return self.reply(404,{"error":"SOURCE_ROUTE_NOT_EXPOSED"})
            token=self.headers.get("Authorization","")
            if not (token.startswith("Bearer ") and
                    compare_digest(token[7:],cfg["token"])):
                return self.reply(401,{"error":"SIGNED_SOURCE_TOKEN_REQUIRED"})
            try:
                n=int(self.headers.get("Content-Length","-1"))
                if n<0 or n>2048:
                    return self.reply(422,{"error":"SIGNED_SOURCE_FRAME_INVALID"})
                request=json.loads(self.rfile.read(n))
                if not isinstance(request,dict) or set(request)!={"after","limit"}:
                    return self.reply(422,{"error":"SIGNED_SOURCE_ARGUMENTS_INVALID"})
                result=pull(cfg["db"],"app-a",request["after"],request["limit"])
                result["events"]=[sign_event(e,cfg["privateKey"])
                                  for e in result["events"]]
                return self.reply(200,result)
            except (ProjectionRefused,) as exc:
                return self.reply(exc.status,{"error":exc.code})
            except (ValueError,TypeError,KeyError):
                return self.reply(422,{"error":"SIGNED_SOURCE_INVALID_JSON"})
        def do_GET(self):
            self.reply(405,{"error":"SIGNED_SOURCE_READ_REQUIRES_POST"})
    server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
    Path(ready).write_text(json.dumps({"port":server.server_port,
                                      "uid":os.getuid()}))
    Path(ready).chmod(0o644)
    print("S1_B14_SIGNED_SOURCE_READY|"+str(server.server_port),flush=True)
    try:server.serve_forever(poll_interval=.1)
    finally:server.server_close()


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--generate-key",default=None)
    p.add_argument("--config")
    p.add_argument("--ready")
    args=p.parse_args()
    if args.generate_key:
        print("S1_B14_PUBLIC_KEY|"+make_keypair(args.generate_key),flush=True)
    elif args.config and args.ready:
        serve(args.config,args.ready)
    else:raise SystemExit("SOURCE_ARGUMENTS_INVALID")


if __name__=="__main__":
    main()
