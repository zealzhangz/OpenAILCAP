"""Real untrusted OS-user v3 tool client. Grant arrives over stdin only.

The trusted test harness injects a token only to the explicitly authorized
process. It never writes the token into argv, command-line options, files,
stdout, error text or the kernel's public ready marker.
"""
import json
import sys
from urllib.error import HTTPError
from urllib.request import Request,urlopen


def main():
    req=json.loads(sys.stdin.buffer.readline(32769))
    if not isinstance(req,dict) or set(req)!={
        "base","token","app","tool","args"
    }:
        raise SystemExit("CLIENT_ENVELOPE_INVALID")
    if not req["base"].startswith("http://127.0.0.1:"):
        raise SystemExit("CLIENT_WRONG_ORIGIN")
    body=json.dumps(req["args"],ensure_ascii=False).encode("utf-8")
    call=Request(req["base"]+"/v3/apps/"+req["app"]+"/tools/"+req["tool"],
                 method="POST",data=body,headers={
                     "Content-Type":"application/json",
                     "Authorization":"Bearer "+req["token"]})
    try:
        with urlopen(call,timeout=10) as r:
            status=r.status
            result=json.loads(r.read())
    except HTTPError as e:
        status=e.code
        result=json.loads(e.read())
    print("S1_B7_TOOL|"+json.dumps({
        "status":status,"tool":req["tool"],"result":result
    },ensure_ascii=False,sort_keys=True))


if __name__=="__main__":main()
