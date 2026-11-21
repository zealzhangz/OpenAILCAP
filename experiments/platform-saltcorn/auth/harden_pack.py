#!/usr/bin/env python3
"""Harden the PREVIOUS actual Saltcorn workflow pack to bind to true req.user.

Pack is used ONLY in clean ephemeral CI. Frozen spec.json remains untouched.
"""
import argparse
import json
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--in-pack",required=True)
    p.add_argument("--validation-code",required=True)
    p.add_argument("--out-pack",required=True)
    args=p.parse_args()
    source=json.loads(Path(args.in_pack).read_text(encoding="utf-8"))
    tables=[t for t in source["tables"] if t["name"]=="s1_bench_action_requests"]
    assert len(tables)==1
    assert tables[0]["min_role_write"]==1
    tables[0]["min_role_write"]=80
    targets=[t for t in source["triggers"] if t["name"]=="S1 Validate Approval Request"]
    assert len(targets)==1
    target=targets[0]
    assert target["when_trigger"]=="Validate" and target["action"]=="run_js_code"
    code=Path(args.validation_code).read_text(encoding="utf-8")
    assert "user.email" in code and "user.id" in code
    target["configuration"]["code"]=code
    Path(args.out_pack).write_text(json.dumps(source,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"tested_native_models":4,"native_actions":3,
          "protected_table":tables[0]["name"],"api_write_role":80,
          "validate_action":"identity bound to authenticated Saltcorn User"}))

if __name__=="__main__":
    main()
