#!/usr/bin/env python3
"""B3 separate OS process: execute checked model PLAN via B2 trusted HTTP only.

No access to SQLite, publisher role, credentials other than one token.
Do not retry unknown POST outcomes under a new changeId.
"""
import argparse
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from plan import check_plan
from schema_core import sha

def call(method,url,token,payload=None):
    headers={"Authorization":"Bearer "+token}
    data=None
    if payload is not None:
        headers["Content-Type"]="application/json"
        data=json.dumps(payload,ensure_ascii=False).encode()
    req=Request(url,headers=headers,data=data,method=method)
    try:
        with urlopen(req,timeout=12) as resp:
            return resp.status,json.loads(resp.read())
    except HTTPError as exc:
        return exc.code,json.loads(exc.read())


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--base",required=True)
    p.add_argument("--plan",required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    token=os.environ.get("S1_B3_AGENT_TOKEN")
    if not token:
        raise SystemExit("AGENT_NOT_AUTHORIZED")
    data=json.loads(Path(args.plan).read_text(encoding="utf-8"))
    if set(data)!={"operations","planHash"}:
        raise SystemExit("UNEXPECTED_PLAN_ENVELOPE")
    validated=check_plan({"operations":data["operations"]})
    if validated["planHash"]!=data["planHash"]:
        raise SystemExit("UNTRUSTED_PLAN_DIGEST_CHANGED")
    base=args.base.rstrip("/")+"/v2/apps/app-a"
    status,snapshot=call("GET",base+"/draft",token)
    if status!=200 or snapshot["appRevision"]!=0 or snapshot["resources"]!={}:
        raise SystemExit("EXPECTED_EMPTY_ISOLATED_APP")
    events=[]
    try:
        for idx,op in enumerate(validated["operations"],1):
            rid=op["resourceId"]
            cmd={"changeId":"b3-agent-create-"+str(idx).zfill(2),
                 "resourceId":rid,"expectedAppRevision":snapshot["appRevision"],
                 "expectedRevision":None,"baseContentHash":None,
                 "definition":op["definition"]}
            status,result=call("POST",base+"/commands",token,cmd)
            if status!=200 or result.get("decision")!="APPLIED":
                raise RuntimeError("TOOL_MUTATION_FAILED_"+str(idx)+"_HTTP_"+str(status))
            events.append({"resource":rid,"status":status,"appRevision":result["appRevision"],
                           "changeId":result["changeId"]})
            status,snapshot=call("GET",base+"/draft",token)
            if status!=200 or snapshot["appRevision"]!=idx:
                raise RuntimeError("TOOL_POST_WRITE_READBACK_FAILED_"+str(idx))
        computed={k:v["definition"] for k,v in snapshot["resources"].items()}
        if sha(computed)!=validated["planHash"] or len(events)!=4:
            raise RuntimeError("TOOL_FINAL_MANIFEST_DIVERGENCE")
        result={"status":"APPLIED","operations":events,
                "manifestHash":snapshot["manifestHash"],
                "appRevision":snapshot["appRevision"],
                "agent_has_publish_permission":False,
                "direct_sql_access":False}
        Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",
                                     encoding="utf-8")
        print("S1_B3_APPLY|"+json.dumps({
            "outcome":"APPLIED","resources":[e["resource"] for e in events],
            "appRevision":snapshot["appRevision"],"manifestHashMatches":True
        },ensure_ascii=False),flush=True)
    except Exception:
        # Partial DRAFT is possible; no publish occurs if anything fails.
        raise

if __name__=="__main__":
    main()
