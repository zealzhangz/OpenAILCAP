#!/usr/bin/env python3
"""Build an actual native Saltcorn Pack for three pre-reviewed capability paths.

All code and schema are human-authored. AI route decisions DO NOT write Pack
metadata, SQL, code or policy. A fresh ephemeral Saltcorn DB is required.
"""
import argparse
import json
from pathlib import Path

def field(name, typ="String", *, ref=None):
    o={"name":name,"label":name,"type":typ,"required":True,"attributes":{}}
    if ref:
        o["reftable_name"]=ref
        o["attributes"]["summary_field"]="number"
    return o

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--original-pack",required=True)
    p.add_argument("--source-dir",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    pack=json.loads(Path(a.original_pack).read_text(encoding="utf-8"))
    tables=[
      {"name":"s1_route_cfg","min_role_read":100,"min_role_write":1,
       "fields":[field("case_id"),field("number"),field("review_note"),field("status")]},
      {"name":"s1_route_code","min_role_read":100,"min_role_write":1,
       "fields":[field("case_id"),field("number")]},
      {"name":"s1_route_hybrid","min_role_read":100,"min_role_write":1,
       "fields":[field("case_id"),field("number"),field("amount_minor","Integer"),
                 field("approval_note")]},
      {"name":"s1_route_hybrid_audit","min_role_read":100,"min_role_write":1,
       "fields":[field("contract_ref","Key",ref="s1_route_hybrid"),field("outcome"),
                 field("approval_note_snapshot")]}
    ]
    pack["tables"]+=tables
    pack["views"].append({
      "name":"s1_route_cfg_view","table":"s1_route_cfg","viewtemplate":"List",
      "min_role":100,"configuration":{"columns":[
        {"type":"Field","field_name":n,"state_field":"on"}
        for n in ("case_id","number","review_note","status")]}})
    pack["views"].append({
      "name":"s1_route_hybrid_view","table":"s1_route_hybrid","viewtemplate":"List",
      "min_role":100,"configuration":{"columns":[
        {"type":"Field","field_name":n,"state_field":"on"}
        for n in ("case_id","number","amount_minor","approval_note")]}})
    for name,table,when,filename in [
        ("S1 Route Choice Code Validate","s1_route_code","Validate","code_validate.js"),
        ("S1 Route Choice Hybrid Audit","s1_route_hybrid","Insert","hybrid_insert.js")
    ]:
        body=(Path(a.source_dir)/filename).read_text(encoding="utf-8")
        pack["triggers"].append({"name":name,"table_name":table,
                                "when_trigger":when,"action":"run_js_code",
                                "min_role":1,
                                "configuration":{"code":body,"run_where":"Server"}})
    Path(a.output).write_text(json.dumps(pack,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"created_models":len(tables),"created_native_views":2,
                      "created_native_code_triggers":2,
                      "ai_wrote_code":False}))

if __name__=="__main__":
    main()
