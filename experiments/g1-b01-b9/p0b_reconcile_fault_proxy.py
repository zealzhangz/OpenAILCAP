"""P0-B test-only real HTTP response-loss bridge; NOT a production proxy.

Only forwards the exact B2 publication.activate HTTP POST from the scoped
Publisher UID. Fault flag is written by trusted CI controller to this
ephemeral home; "after" forwards and receives actual committed B2 response
then holds it until Publisher HTTP times out, "before" never forwards and
holds, simulating unknown outcome WITHOUT actually committing. Reports
only the changeId/status, NEVER Authorization headers or secrets.
"""
from __future__ import annotations
import argparse
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request,urlopen

ROUTE="/v3/apps/app-a/tools/publication.activate"


def serve(target,flag,ready,events):
    flag=Path(flag);events=Path(events)
    seen=[]
    guard=threading.Lock()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*_):pass

        def do_POST(self):
            if self.path!=ROUTE:
                self.send_error(404)
                return
            size=int(self.headers.get("Content-Length","0"))
            if size<1 or size>4096:
                self.send_error(422)
                return
            raw=self.rfile.read(size)
            body=json.loads(raw)
            cid=body.get("changeId")
            with guard:
                mode=flag.read_text().strip() if flag.exists() else "normal"
                if flag.exists():flag.unlink()
            if mode=="before":
                self.register(cid,mode,None)
                time.sleep(2.7)
                return
            request=Request(
                target+ROUTE,method="POST",data=raw,
                headers={"Authorization":self.headers.get("Authorization",""),
                         "Content-Type":"application/json"})
            try:
                with urlopen(request,timeout=10) as response:
                    status,payload=response.status,response.read(4096)
            except HTTPError as exc:
                status,payload=exc.code,exc.read(4096)
            self.register(cid,mode,status)
            if mode=="after":
                # Actual B2 has ALREADY COMMITTED; do not send its reply.
                time.sleep(2.7)
                return
            try:
                self.send_response(status)
                self.send_header("Content-Type","application/json")
                self.send_header("Content-Length",str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            except (BrokenPipeError,ConnectionResetError):
                return

        def register(self,cid,mode,status):
            with guard:
                seen.append({"changeId":cid,"mode":mode,"kernelStatus":status})
                events.write_text(json.dumps(seen,sort_keys=True)+"\n")

        def do_GET(self):
            self.send_error(405)
        do_PUT=do_PATCH=do_DELETE=do_GET

    with ThreadingHTTPServer(("127.0.0.1",0),Handler) as server:
        Path(ready).write_text(json.dumps({"port":server.server_port}))
        Path(ready).chmod(0o644)
        server.serve_forever(poll_interval=.15)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--target",required=True)
    p.add_argument("--flag",required=True)
    p.add_argument("--ready",required=True)
    p.add_argument("--events",required=True)
    a=p.parse_args()
    if not a.target.startswith("http://127.0.0.1:"):
        raise SystemExit("PROXY_TARGET_LOOPBACK_ONLY")
    serve(a.target,a.flag,a.ready,a.events)
