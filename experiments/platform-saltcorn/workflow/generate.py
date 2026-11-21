#!/usr/bin/env python3
"""Prepare a native Saltcorn Pack with native built-in code actions and frozen cases.

Use ONLY clean CI test databases. The frozen spec is loaded but never modified.
"""
import argparse
import json
from pathlib import Path

def make_field(name, typ, *, label=None, required=True, unique=False, reftable=None):
    field={"name":name,"label":label or name,"type":typ,"required":required,
           "attributes":{}}
    if unique:
        field["is_unique"]=True
    if reftable:
        field["reftable_name"]=reftable
        field["attributes"]["summary_field"]="number"
    return field

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--base-pack",required=True)
    p.add_argument("--benchmark",required=True)
    p.add_argument("--trigger-dir",required=True)
    p.add_argument("--driver-template",required=True)
    p.add_argument("--pack-out",required=True)
    p.add_argument("--driver-out",required=True)
    a=p.parse_args()
    pack=json.loads(Path(a.base_pack).read_text(encoding="utf-8"))
    spec=json.loads(Path(a.benchmark).read_text(encoding="utf-8"))
    assert len(spec["amount_cases"])==12 and len(spec["transition_cases"])==12
    root="s1_bench_contracts"
    tables=[
        {"name":root,"description":"S1 real Saltcorn trigger workflow, lab fixture",
         "min_role_read":100,"min_role_write":1,
         "fields":[
            make_field("number","String",unique=True),
            make_field("title","String"),
            make_field("amount_decimal","String",label="Canonical CNY decimal text"),
            make_field("amount_minor","Integer",label="Exact CNY cents"),
            make_field("owner_id","String"),
            make_field("status","String")]},
        {"name":"s1_bench_routes","min_role_read":1,"min_role_write":1,
         "fields":[make_field("contract_ref","Key",reftable=root),
                   make_field("route","String"),make_field("stage","String")]},
        {"name":"s1_bench_action_requests","min_role_read":1,"min_role_write":1,
         "fields":[make_field("request_id","String",unique=True),
                   make_field("contract_ref","Key",reftable=root),
                   make_field("action","String"),make_field("actor_role","String"),
                   make_field("actor_id","String"),
                   make_field("occurred_at","String",required=False),
                   make_field("reason","String",required=False)]},
        {"name":"s1_bench_approvals","min_role_read":1,"min_role_write":1,
         "fields":[make_field("contract_ref","Key",reftable=root),
                   make_field("approver_id","String"),make_field("actor_role","String"),
                   make_field("action","String"),make_field("occurred_at","String"),
                   make_field("reason","String",required=False)]}
    ]
    pack["tables"]+=tables
    pack["views"].append({
      "name":"s1_bench_contract_list","table":root,"viewtemplate":"List","min_role":100,
      "configuration":{"columns":[
        {"type":"Field","field_name":name,"state_field":"on"}
        for name in ("number","title","amount_decimal","status")
      ]}})
    triggers=[]
    for name,table,when,filename in [
       ("S1 Route On Contract Insert",root,"Insert","route_on_insert.js"),
       ("S1 Validate Approval Request","s1_bench_action_requests","Validate","validate_action.js"),
       ("S1 Apply Approval Request","s1_bench_action_requests","Insert","apply_action.js")
    ]:
        code=(Path(a.trigger_dir)/filename).read_text(encoding="utf-8")
        assert "Table.findOne" in code
        triggers.append({"name":name,"table_name":table,"when_trigger":when,
                         "action":"run_js_code","min_role":1,
                         "configuration":{"code":code,"run_where":"Server"}})
    pack["triggers"]+=triggers
    Path(a.pack_out).write_text(json.dumps(pack,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    template=Path(a.driver_template).read_text(encoding="utf-8")
    assert template.count("__FROZEN_CASES__")==1
    case_data={"amount_cases":spec["amount_cases"],
               "transition_cases":spec["transition_cases"]}
    script=template.replace("__FROZEN_CASES__",json.dumps(case_data,ensure_ascii=False))
    Path(a.driver_out).write_text(script,encoding="utf-8")
    print(json.dumps({"native_trigger_count":len(triggers),
                      "real_tables":len(tables),"amount_cases":12,
                      "transition_cases":12,"source_spec_unchanged":True}))

if __name__=="__main__":
    main()
