"""Untrusted UID native client of the existing Saltcorn governed field gateway.

Bearer supplied only via an isolated one-use stdin JSON. No SQLite path,
operating-system user name or identity field is interpreted as authorization.
"""
from __future__ import annotations
import json,sys
from urllib.error import HTTPError
from urllib.request import Request,urlopen


def main():
    raw=sys.stdin.buffer.readline(32769)
    if len(raw)>32768:
        raise SystemExit("CLIENT_TOO_LARGE")
    req=json.loads(raw)
    if not isinstance(req,dict) or set(req)!={"base","token","method","path","body"}:
        raise SystemExit("CLIENT_BAD_ENVELOPE")
    base,path,method=req["base"],req["path"],req["method"]
    if not isinstance(base,str) or not base.startswith("http://127.0.0.1:"):
        raise SystemExit("CLIENT_ORIGIN_REFUSED")
    if not isinstance(path,str) or not path.startswith("/") or "//" in path:
        raise SystemExit("CLIENT_PATH_REFUSED")
    if method not in ("GET","POST"):
        raise SystemExit("CLIENT_METHOD_REFUSED")
    body=None if req["body"] is None else json.dumps(
        req["body"],ensure_ascii=False,separators=(",",":")).encode()
    headers={"Authorization":"Bearer "+req["token"]}
    if body is not None:headers["Content-Type"]="application/json"
    call=Request(base+path,data=body,method=method,headers=headers)
    try:
        with urlopen(call,timeout=15) as res:
            status,data=res.status,json.loads(res.read(32769))
    except HTTPError as error:
        status,data=error.code,json.loads(error.read(32769))
    print("S1_B8_TOOL|"+json.dumps(
        {"http":status,"data":data},ensure_ascii=False,separators=(",",":")))


if __name__=="__main__":main()
