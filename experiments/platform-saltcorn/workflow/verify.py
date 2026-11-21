#!/usr/bin/env python3
"""Independent frozen-contract oracle on an actual Saltcorn runtime database.

Does not import the business JS. Uses the previously frozen spec.json, raw
native CLI logs, physical SQL rows and (optional) live Saltcorn HTTP readback.
"""
from __future__ import annotations
import argparse
from decimal import Decimal, InvalidOperation
import json
import re
import sqlite3
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

MONEY=re.compile(r"^[0-9]{1,10}(?:\.[0-9]{1,2})?$")
THRESHOLD=Decimal("1000000.00")
MAXIMUM=Decimal("9999999999.99")
EXPECTED_PATHS={
    "normal":(["Submitted","Approved"],"Approved",1),
    "high":(["Submitted","Level1Approved","Approved"],"Approved",2),
    "reject":(["Submitted","Rejected"],"Rejected",1)
}

def parse_amount(value):
    if not isinstance(value,str) or not MONEY.fullmatch(value):
        return None
    try:
        val=Decimal(value)
        if not val.is_finite() or val<0 or val>MAXIMUM:
            return None
        return val
    except InvalidOperation:
        return None

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--spec",required=True)
    p.add_argument("--db",required=True)
    p.add_argument("--log",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--base-url",default="")
    a=p.parse_args()
    spec=json.loads(Path(a.spec).read_text(encoding="utf-8"))
    text=Path(a.log).read_text(encoding="utf-8",errors="replace")
    logs={"S1_AMOUNT":{},"S1_STATE":{},"S1_SEQUENCE":{}}
    driver_complete=None
    for line in text.splitlines():
        for key in logs:
            k=key+"|"
            if line.startswith(k):
                record=json.loads(line[len(k):])
                if record["id"] in logs[key]:
                    raise AssertionError("duplicate runtime log for "+key+" "+record["id"])
                logs[key][record["id"]]=record
        if line.startswith("S1_DRIVER_COMPLETE|"):
            driver_complete=json.loads(line.partition("|")[2])
    checks=[]
    def check(cid,ok,obs):
        checks.append({"id":cid,"status":"PASS" if ok else "FAIL","observed":obs})
        print(cid,"PASS" if ok else "FAIL",json.dumps(obs,ensure_ascii=False),flush=True)
    with sqlite3.connect(f"file:{Path(a.db).resolve()}?mode=ro",uri=True) as db:
        db.row_factory=sqlite3.Row
        tables={x["name"] for x in db.execute(
            "SELECT name FROM _sc_tables WHERE name LIKE 's1_bench_%'")}
        check("WF00-native-table-metadata",{
            "s1_bench_contracts","s1_bench_routes","s1_bench_action_requests",
            "s1_bench_approvals"
        }.issubset(tables),{"native_tables":sorted(tables)})
        trigger_rows=list(db.execute(
            "SELECT t.name,t.action,t.when_trigger,tab.name AS table_name "
            "FROM _sc_triggers t LEFT JOIN _sc_tables tab ON tab.id=t.table_id "
            "WHERE t.name LIKE 'S1 %'"))
        observed={(x["name"],x["action"],x["when_trigger"],x["table_name"])
                  for x in trigger_rows}
        expected={
          ("S1 Route On Contract Insert","run_js_code","Insert","s1_bench_contracts"),
          ("S1 Validate Approval Request","run_js_code","Validate","s1_bench_action_requests"),
          ("S1 Apply Approval Request","run_js_code","Insert","s1_bench_action_requests")
        }
        check("WF01-native-triggers-installed",expected.issubset(observed),
              {"installed":[list(x) for x in sorted(observed)]})
        field_columns={x["name"] for x in db.execute(
            'PRAGMA table_info("s1_bench_contracts")')}
        check("WF02-physical-business-columns",
              {"number","amount_decimal","amount_minor","status","owner_id"} <= field_columns,
              {"physical_columns":sorted(field_columns)})
        amount_count=0
        for case in spec["amount_cases"]:
            cid=case["id"]
            record=logs["S1_AMOUNT"].get(cid,{})
            parsed=parse_amount(case["amount"])
            expect_level=("INVALID" if parsed is None else
                "HIGH" if parsed>THRESHOLD else "NORMAL")
            num="AM-"+cid
            rows=list(db.execute('SELECT * FROM "s1_bench_contracts" WHERE number=?',(num,)))
            if parsed is None:
                good=(expect_level==case["expected"] and
                      record.get("inserted") is False and
                      record.get("actual_error")=="INVALID_AMOUNT" and len(rows)==0)
                detail={"expected":"INVALID","native_row_count":len(rows),
                        "reported_error":record.get("actual_error")}
            else:
                amount_count+=1
                minor=int(parsed*100)
                contract=rows[0] if len(rows)==1 else None
                routes=list(db.execute(
                    'SELECT route,stage FROM "s1_bench_routes" WHERE contract_ref=?',
                    (contract["id"] if contract else -1,)))
                canonical=f"{parsed:.2f}"
                good=(expect_level==case["expected"] and record.get("inserted") is True
                    and len(rows)==1 and record.get("derived_minor")==minor
                    and record.get("derived_level")==expect_level
                    and contract["amount_minor"]==minor
                    and contract["amount_decimal"]==canonical
                    and len(routes)==1 and routes[0]["route"]==expect_level)
                detail={"expected_route":expect_level,"real_cents":contract["amount_minor"] if contract else None,
                        "canonical_amount":contract["amount_decimal"] if contract else None,
                        "native_inserted_routes":[r["route"] for r in routes]}
            check("AM-"+cid,good,detail)
        for case in spec["transition_cases"]:
            cid=case["id"]
            record=logs["S1_STATE"].get(cid,{})
            num="ST-"+cid
            row=db.execute('SELECT * FROM "s1_bench_contracts" WHERE number=?',(num,)).fetchone()
            if row is None:
                check("ST-"+cid,False,{"error":"native_contract_absent"})
                continue
            requests=list(db.execute(
                'SELECT * FROM "s1_bench_action_requests" WHERE contract_ref=?',(row["id"],)))
            approvals=list(db.execute(
                'SELECT * FROM "s1_bench_approvals" WHERE contract_ref=?',(row["id"],)))
            exp=case["expected"]
            is_error=exp in ("INVALID_STATE","FORBIDDEN","INVALID_ACTION")
            expected_status=case["from"] if is_error else exp
            expected_requests=0 if is_error else 1
            expected_approvals=0 if is_error or case["action"]=="submit" else 1
            good=(row["status"]==expected_status and record.get("actual_status")==expected_status
                  and len(requests)==expected_requests and
                  len(approvals)==expected_approvals and
                  record.get("native_request_count")==expected_requests and
                  record.get("native_approval_count")==expected_approvals and
                  record.get("accepted")== (not is_error) and
                  (record.get("actual_error")==exp if is_error else
                   record.get("actual_error") is None))
            check("ST-"+cid,good,{"expected":exp,"real_status":row["status"],
                  "reported_error":record.get("actual_error"),
                  "real_requests":len(requests),"real_approvals":len(approvals)})
        for cid,(steps,expected_final,apcount) in EXPECTED_PATHS.items():
            log=logs["S1_SEQUENCE"].get(cid,{})
            row=db.execute('SELECT * FROM "s1_bench_contracts" WHERE number=?',
                           ("SEQ-"+cid,)).fetchone()
            actual_status=row["status"] if row else None
            approvals=(list(db.execute(
              'SELECT action,actor_role FROM "s1_bench_approvals" WHERE contract_ref=? ORDER BY id',
              (row["id"],))) if row else [])
            expected_roles=(["approver1","approver2"] if cid=="high" else ["approver1"])
            good=(log.get("actual_steps")==steps and
                  actual_status==expected_final and
                  log.get("error") is None and
                  len(approvals)==apcount and
                  [x["actor_role"] for x in approvals]==expected_roles)
            check("SEQ-"+cid,good,{"observed_steps":log.get("actual_steps"),
                  "db_status":actual_status,
                  "approval_actors":[x["actor_role"] for x in approvals]})
        check("WF03-run-complete",
              driver_complete=={"amount_case_count":12,"transition_case_count":12,
                               "sequence_count":3,"all_executed_via_native_table_api":True},
              {"runtime_summary":driver_complete})
        views={x[0] for x in db.execute("SELECT name FROM _sc_views")}
        check("WF04-native-view", "s1_bench_contract_list" in views,
              {"native_view_registered":"s1_bench_contract_list" in views})
        # Physical TEXT currency storage, not decimal(12,2): cannot mark TC02 fully passed.
        types={r["name"]:r["type"] for r in db.execute(
            'PRAGMA table_info("s1_bench_contracts")')}
        check("WF05-currency-type-limitation-detected",
              "TEXT" in types.get("amount_decimal","").upper(),
              {"real_sql_type":types.get("amount_decimal"),
               "frozen_required":"decimal(12,2)","limitation":"NOT_EQUAL"})
    if a.base_url:
        base=a.base_url
        for path,term in [("/api/s1_bench_contracts/","ST-ST03"),
                          ("/view/s1_bench_contract_list","SEQ-high")]:
            try:
                with urlopen(base+path,timeout=15) as r:
                    body=r.read(2000000).decode("utf-8","replace")
                    good=r.status==200 and term in body
                    check("HTTP-"+path,good,{"status":r.status,"contains":term in body})
            except (HTTPError,OSError) as exc:
                check("HTTP-"+path,False,{"error":str(exc)})
    result={
        "study":"S1 Saltcorn real built-in Trigger + run_js_code Action, benchmark workflow",
        "frozen_spec":spec["id"],
        "scope":"Real native model/trigger execution through privileged Saltcorn CLI; NOT authenticated actor access or visual workflow",
        "checks":checks,
        "summary":{"passed":sum(x["status"]=="PASS" for x in checks),"total":len(checks)},
        "original_benchmark_tasks_claimed_passed":0,
        "limitations":[
            "Saltcorn actor_role is user-provided test string, not authenticated principal",
            "Numeric amount stored as canonical TEXT + Integer cents, not native decimal(12,2)",
            "JS prevalidation runs before native data creation; invalid monetary values are not passed to Saltcorn directly",
            "JS triggers and CLI are privileged; no HTTP business approval endpoint or 403 verified",
            "Explicit CLI transaction wraps action; no proof native Saltcorn SQLite trigger execution alone is atomic",
            "Not AI-written code, no LLM, no plugin discovery, no cross-app isolation",
            "No claim complete TC01/TC02/TC03/TC04/TC05 acceptance"
        ]
    }
    Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return 0 if len(checks)==(1+1+1+12+12+3+1+1+1+(2 if a.base_url else 0)) and all(x["status"]=="PASS" for x in checks) else 1

if __name__=="__main__":
    raise SystemExit(main())
