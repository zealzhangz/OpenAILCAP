#!/usr/bin/env python3
"""Independent deterministic typed Agent HTTP tool (no LLM or DB access)."""
import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

def call(base, method, path, token, body=None):
    headers={"Authorization":"Bearer "+token}
    data=None
    if body is not None:
        headers["Content-Type"]="application/json"
        data=json.dumps(body,ensure_ascii=False).encode()
    req=Request(base+path,headers=headers,data=data,method=method)
    try:
        with urlopen(req,timeout=10) as response:
            return response.status,json.loads(response.read())
    except HTTPError as exc:
        return exc.code,json.loads(exc.read())

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--base",required=True)
    parser.add_argument("--app",default="app-a")
    parser.add_argument("--operation",choices=("mutate","publish","rollback"),default="mutate")
    parser.add_argument("--resource")
    parser.add_argument("--spec-file",default=str(Path(__file__).with_name("contract_spec.json")))
    parser.add_argument("--delete",action="store_true")
    parser.add_argument("--change-id",required=True)
    parser.add_argument("--expected-app-revision",type=int)
    parser.add_argument("--target-version",type=int)
    parser.add_argument("--expected-published-version",type=int)
    args=parser.parse_args()
    token=os.environ.get("S1_B2_AGENT_TOKEN")
    if not token:
        raise SystemExit("AGENT_TOKEN_NOT_GRANTED")
    path="/v2/apps/"+args.app
    status,snapshot=call(args.base,"GET",path+"/draft",token)
    if status!=200:
        print(json.dumps({"http":status,"result":snapshot}))
        return 0
    if args.operation=="mutate":
        if not args.resource:
            raise SystemExit("RESOURCE_REQUIRED")
        entry=snapshot["resources"].get(args.resource)
        specs=json.loads(Path(args.spec_file).read_text(encoding="utf-8"))
        definition=None if args.delete else specs[args.resource]
        command={"changeId":args.change_id,"resourceId":args.resource,
                 "expectedAppRevision":snapshot["appRevision"] if
                     args.expected_app_revision is None else args.expected_app_revision,
                 "expectedRevision":entry["revision"] if entry else None,
                 "baseContentHash":entry["contentHash"] if entry else None,
                 "definition":definition}
        route="/commands"
    elif args.operation=="publish":
        command={"changeId":args.change_id,
                 "expectedAppRevision":snapshot["appRevision"] if
                     args.expected_app_revision is None else args.expected_app_revision,
                 "manifestHash":snapshot["manifestHash"]}
        route="/publish"
    else:
        command={"changeId":args.change_id,
                 "targetVersion":args.target_version,
                 "expectedPublishedVersion":snapshot["publishedVersion"] if
                   args.expected_published_version is None else args.expected_published_version}
        route="/rollback"
    status,result=call(args.base,"POST",path+route,token,command)
    print(json.dumps({"http":status,"result":result},ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
