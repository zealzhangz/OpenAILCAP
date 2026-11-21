"""Independent physical SQLite check after real browser sessions and blind CAS."""
import argparse
import json
import sqlite3
from pathlib import Path
from urllib.request import urlopen

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--db",required=True);p.add_argument("--output",required=True)
    p.add_argument("--base-url",default="http://127.0.0.1:3100")
    args=p.parse_args()
    with sqlite3.connect(f"file:{Path(args.db).resolve()}?mode=ro",uri=True) as db:
        row=db.execute("SELECT label FROM _sc_fields WHERE table_id=(SELECT id FROM _sc_tables WHERE name='s1_contracts') AND name='title'").fetchone()
        rev=db.execute("SELECT revision FROM _openailcap_s1_browser_ledger WHERE resource_id='title'").fetchone()
        contract=db.execute("SELECT contract_no,amount_minor FROM s1_contracts WHERE contract_no='HT-2026-000001'").fetchone()
    checks=[
      {"id":"U10-browser-change-was-overwritten","passed":row==("Agent Overwrites Browser",),
       "actual_label":row[0] if row else None,"semantic":"NEGATIVE_PRODUCT_BEHAVIOR_REPRODUCED"},
      {"id":"U11-agent-advanced-only-its-own-ledger","passed":rev==(1,),
       "revision":rev[0] if rev else None,"semantic":"NEGATIVE_BYPASS"},
      {"id":"U12-existing-contract-row-remains","passed":contract==("HT-2026-000001",100000001),
       "actual_matches":contract==("HT-2026-000001",100000001)}
    ]
    for suffix in ("/api/s1_contracts/","/view/s1_contract_list"):
        with urlopen(args.base_url+suffix,timeout=10) as r:
            content=r.read(1000000).decode("utf-8","replace")
            checks.append({"id":"U13-http-"+suffix,"passed":r.status==200 and "HT-2026-000001" in content,
                           "http_status":r.status})
    data={"study":"Real browser editor vs separate agent-only ledger on actual Saltcorn",
          "scope":"Actual Chromium UI authenticated session vs simulated trusted CLI, NOT real Agent",
          "negative_result":"A sidecar CAS used only by Agent does not protect browser edits",
          "cases":checks,"summary":{"passed":sum(x["passed"] for x in checks),"total":len(checks)}}
    Path(args.output).write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for case in checks:print(case["id"],"PASS" if case["passed"] else "FAIL")
    return 0 if all(c["passed"] for c in checks) else 1
if __name__=="__main__":
    raise SystemExit(main())
