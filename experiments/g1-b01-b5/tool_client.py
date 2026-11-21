#!/usr/bin/env python3
"""External OS-process Agent/Plugin client of B5 typed v3 HTTP tools only.

No DB, workspace, Docker socket or publisher grants. The trusted broker
derives identity from its opaque token map, never from tool arguments.
"""
import argparse,json,os,sys
from urllib.request import Request,urlopen
from urllib.error import HTTPError

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--base",required=True)
    p.add_argument("--app",required=True)
    p.add_argument("--tool",required=True)
    p.add_argument("--args-json",required=True)
    a=p.parse_args()
    token=os.getenv("S1_B5_TOOL_TOKEN")
    if not token:raise SystemExit("S1_B5_NOT_AUTHORIZED")
    args=json.loads(a.args_json)
    data=json.dumps(args,ensure_ascii=False,separators=(",",":")).encode()
    url=a.base.rstrip("/")+"/v3/apps/"+a.app+"/tools/"+a.tool
    req=Request(url,data=data,method="POST",headers={
        "Authorization":"Bearer "+token,"Content-Type":"application/json"})
    try:
        with urlopen(req,timeout=60) as r:
            status,result=r.status,json.load(r)
    except HTTPError as e:
        status,result=e.code,json.loads(e.read())
    print("S1_B5_TOOL|"+json.dumps({"status":status,"tool":a.tool,
                                   "response":result},ensure_ascii=False))
    return 0

if __name__=="__main__":raise SystemExit(main())
