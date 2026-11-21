#!/usr/bin/env python3
"""Independent oracle: native Saltcorn SQLite/UI + sealed route labels.

Never imports the model predictor or its decision policy. The three modes
execute previously human-reviewed adapters; this is a routing feasibility
pilot, NOT AI-generated schema, code, plugins, or autonomous development.
"""
import argparse
import json
from pathlib import Path
import sqlite3
from urllib.request import urlopen

MODES=("CONFIG","CODE","HYBRID")

def main():
    p=argparse.ArgumentParser()
    for name in ("spec","prediction","database","log","output"):
        p.add_argument("--"+name,required=True)
    p.add_argument("--base",default="http://127.0.0.1:3100")
    p.add_argument("--live-model",action="store_true")
    a=p.parse_args()
    spec=json.loads(Path(a.spec).read_text(encoding="utf-8"))
    prediction=json.loads(Path(a.prediction).read_text(encoding="utf-8"))
    lines=Path(a.log).read_text(encoding="utf-8",errors="replace").splitlines()
    logs={key:{} for key in ("S1_ROUTE_EXEC","S1_ROUTE_NEGATIVE")}
    complete=None
    for line in lines:
        for key in logs:
            tag=key+"|"
            if line.startswith(tag):
                row=json.loads(line[len(tag):])
                cid=row["case_id"]
                if cid in logs[key]:raise ValueError("DUPLICATE_CLI_LOG_"+cid)
                logs[key][cid]=row
        if line.startswith("S1_ROUTE_EXEC_COMPLETE|"):
            complete=json.loads(line.partition("|")[2])
    cases=spec["cases"]
    selected={r["id"]:r["mode"] for r in prediction["choices"]}
    checks=[]
    def record(cid,condition,details):
        good=bool(condition)
        checks.append({"id":cid,"status":"PASS" if good else "FAIL","observed":details})
        print(cid,"PASS" if good else "FAIL",json.dumps(details,ensure_ascii=False),flush=True)

    real_model=bool(prediction.get("model_inference_executed"))
    record("ROUTE00-inference-source",
           real_model==a.live_model and
           (not a.live_model or
            prediction.get("model_id")=="deepseek-flash" and
            prediction.get("tool_calls_returned")==1),
           {"live_requested":a.live_model,"actual_model":real_model,
            "model_id":prediction.get("model_id"),
            "selected_count":len(selected),
            "tool_calls_returned":prediction.get("tool_calls_returned")})
    record("ROUTE01-real-native-driver-ran",
           complete=={"route_count":len(cases),"runtime_native_table_api":True,
                      "ai_generated_code":False},
           {"driver":complete})

    with sqlite3.connect("file:"+str(Path(a.database).resolve())+"?mode=ro",uri=True) as db:
        db.row_factory=sqlite3.Row
        tables={x["name"] for x in db.execute(
            "SELECT name FROM _sc_tables WHERE name LIKE 's1_route_%'")}
        wanted={"s1_route_cfg","s1_route_code","s1_route_hybrid",
                "s1_route_hybrid_audit"}
        record("ROUTE02-platform-native-tables",wanted.issubset(tables),
               {"tables":sorted(tables)})
        fields={x["name"] for x in db.execute(
            'PRAGMA table_info("s1_route_cfg")')}
        hybrid_fields={x["name"] for x in db.execute(
            'PRAGMA table_info("s1_route_hybrid")')}
        record("ROUTE03-native-field-metadata",
               {"review_note","status","number"}<=fields and
               {"approval_note","amount_minor","case_id"}<=hybrid_fields,
               {"config_fields":sorted(fields),"hybrid_fields":sorted(hybrid_fields)})
        triggers={tuple(row) for row in db.execute(
            "SELECT name,action,when_trigger FROM _sc_triggers "
            "WHERE name LIKE 'S1 Route Choice %'")}
        expected_triggers={
            ("S1 Route Choice Code Validate","run_js_code","Validate"),
            ("S1 Route Choice Hybrid Audit","run_js_code","Insert")
        }
        record("ROUTE04-native-code-actions",
               expected_triggers<=triggers,
               {"registered":[list(x) for x in sorted(triggers)]})
        views={r["name"] for r in db.execute(
            "SELECT name FROM _sc_views WHERE name LIKE 's1_route_%'")}
        record("ROUTE05-native-listviews",
               {"s1_route_cfg_view","s1_route_hybrid_view"}<=views,
               {"views":sorted(views)})
        for case in cases:
            cid=case["id"];expected=case["expected_mode"];mode=selected.get(cid)
            record("CHOOSE-"+cid,mode==expected,
                   {"predicted":mode,"expected":expected})
            exec_record=logs["S1_ROUTE_EXEC"].get(cid,{})
            present={}
            for name in ("s1_route_cfg","s1_route_code","s1_route_hybrid"):
                present[name]=[dict(r) for r in db.execute(
                    'SELECT * FROM "'+name+'" WHERE case_id=?',(cid,))]
            expected_table={"CONFIG":"s1_route_cfg","CODE":"s1_route_code",
                            "HYBRID":"s1_route_hybrid"}[expected]
            selected_valid=(mode==expected and exec_record.get("selected_mode")==expected
                            and len(present[expected_table])==1
                            and all(not rows for name,rows in present.items()
                                    if name!=expected_table))
            fixture=case["fixture"]
            extra={}
            if expected=="CONFIG":
                row=present[expected_table][0] if present[expected_table] else {}
                selected_valid=selected_valid and \
                    row.get("review_note")==fixture["note"] and \
                    row.get("number")==fixture["number"] and \
                    row.get("status")==fixture["status"]
                extra={"physical_note":row.get("review_note"),
                       "physical_status":row.get("status")}
            elif expected=="CODE":
                row=present[expected_table][0] if present[expected_table] else {}
                selected_valid=selected_valid and row.get("number")==fixture["number"]
                neg=logs["S1_ROUTE_NEGATIVE"].get(cid,{})
                neg_rows=list(db.execute(
                    'SELECT case_id FROM "s1_route_code" WHERE case_id=?',
                    ("NEG-"+cid,)))
                selected_valid=selected_valid and \
                    "CHECKSUM_MISMATCH" in str(neg.get("error") or "") and \
                    not neg_rows and neg.get("inserted_id") is None
                extra={"valid_number":row.get("number"),
                       "negative_error":neg.get("error"),
                       "invalid_inserted_rows":len(neg_rows)}
            elif expected=="HYBRID":
                row=present[expected_table][0] if present[expected_table] else {}
                audits=[dict(x) for x in db.execute(
                    "SELECT contract_ref,outcome,approval_note_snapshot "
                    "FROM s1_route_hybrid_audit WHERE contract_ref=?",
                    (row.get("id",-1),))]
                selected_valid=selected_valid and \
                    row.get("number")==fixture["number"] and \
                    row.get("approval_note")==fixture["note"] and \
                    row.get("amount_minor")==fixture["amount_minor"] and \
                    len(audits)==1 and \
                    audits[0]["outcome"]==fixture["outcome"] and \
                    audits[0]["approval_note_snapshot"]==fixture["note"]
                extra={"amount_cents":row.get("amount_minor"),
                       "physical_audit":audits}
            record("NATIVE-"+cid,selected_valid,
                   {"selected_mode":mode,"physical_table":expected_table,
                    "native_record":exec_record,"validation":extra})

    for path,should_contain in [
        ("/view/s1_route_cfg_view","CFG-01"),
        ("/view/s1_route_hybrid_view","HYB-05")
    ]:
        try:
            with urlopen(a.base+path,timeout=15) as response:
                page=response.read(250000).decode("utf-8","replace")
                condition=response.status==200 and should_contain in page
                detail={"http":response.status,"expected_text_present":should_contain in page}
        except Exception as exc:
            condition=False;detail={"error_type":type(exc).__name__}
        record("HTTP-"+path,condition,detail)

    accuracy=sum(selected.get(c["id"])==c["expected_mode"] for c in cases)
    baseline=sum(c["expected_mode"]=="CONFIG" for c in cases)
    result={
      "study_id":spec["id"],"date":"2026-11-21",
      "model_inference_executed":real_model,
      "model_id":prediction.get("model_id"),
      "model_budget_actual_calls":1 if real_model else 0,
      "sample_size":len(cases),
      "routing_accuracy":{"correct":accuracy,"total":len(cases)},
      "trivial_baseline_all_config":{"correct":baseline,"total":len(cases)},
      "usage_tokens":prediction.get("usage_tokens",{}),
      "checks":checks,
      "summary":{"passed":sum(x["status"]=="PASS" for x in checks),
                 "total":len(checks)},
      "scope":{
        "model_chose_paths":real_model,
        "model_generated_saltcorn_code":False,
        "code_and_configuration_preinstalled_by_researcher":True,
        "native_tables_triggers_and_http_tested":True,
        "human_ai_roundtrip_tested":False,
        "full_contract_benchmark_tasks_claimed_passed":0,
        "G1":"NOT_PASSED"
      }
    }
    Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",
                              encoding="utf-8")
    print("S1_ROUTE_RESULT|"+json.dumps({
        "model_inference_executed":real_model,
        "correct":accuracy,"cases":len(cases),
        "baseline":baseline,"passed":result["summary"]["passed"],
        "total":result["summary"]["total"]}),flush=True)
    # 2 runtime framing + 4 metadata + 6 choices + 6 physical + 2 HTTP = 20.
    return 0 if len(checks)==20 and all(x["status"]=="PASS" for x in checks) else 1

if __name__=="__main__":
    raise SystemExit(main())
