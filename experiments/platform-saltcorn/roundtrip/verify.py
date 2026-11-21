"""Independent SQLite + HTTP readback of real Saltcorn editing experiments.

Expected unsafe overwrite is detected and recorded as a *negative* security/
correctness result. A CI green check DOES NOT mean the product is safe.
"""
from __future__ import annotations
import argparse
import json
import sqlite3
import sys
from pathlib import Path
from urllib.request import urlopen
from urllib.error import HTTPError

EXPECTED={
    "A": {"title":"Human Reviewed Title","status":"Automated Status","amount_visible":True},
    "B": {"title":"Title","status":"Status","amount_visible":False},
    "C": {"title":"Human Reviewed Title","status":"Status","amount_visible":False},
}

def inspect(dbfile,phase):
    expected=EXPECTED[phase]
    records=[]
    def check(cid,ok,observed):
        records.append({"id":cid,"passed":bool(ok),"observed":observed})
    with sqlite3.connect(f"file:{Path(dbfile).resolve()}?mode=ro",uri=True) as db:
        rows=db.execute("""
        SELECT name,label FROM _sc_fields
        WHERE table_id=(SELECT id FROM _sc_tables WHERE name='s1_contracts')
          AND name IN ('title','status')
        """).fetchall()
        labels=dict(rows)
        views=db.execute(
            "SELECT configuration FROM _sc_views WHERE name='s1_contract_list'").fetchone()
        cols=None
        if views:
            config=json.loads(views[0]) if isinstance(views[0],str) else views[0]
            cols=[x.get("field_name") for x in config.get("columns",[])]
        check(f"{phase}1-title-field",labels.get("title")==expected["title"],{"actual":labels.get("title"),"expected":expected["title"]})
        check(f"{phase}2-status-field",labels.get("status")==expected["status"],{"actual":labels.get("status"),"expected":expected["status"]})
        check(f"{phase}3-amount-column",bool(cols is not None and ("amount_minor" in cols)==expected["amount_visible"]),
              {"column_names":cols,"expected_amount_visible":expected["amount_visible"]})
        row=db.execute("SELECT contract_no,amount_minor FROM s1_contracts WHERE contract_no=?",("HT-2026-000001",)).fetchone()
        check(f"{phase}4-business-row",row==("HT-2026-000001",100000001),{"row_preserved":row==("HT-2026-000001",100000001)})
    return records

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--phase",choices=list(EXPECTED),required=True)
    p.add_argument("--db",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--base-url",default="")
    args=p.parse_args()
    records=inspect(args.db,args.phase)
    if args.base_url:
        for path,marker,id_ in [
          ("/api/s1_contracts/","HT-2026-000001",f"{args.phase}5-rest"),
          ("/view/s1_contract_list","HT-2026-000001",f"{args.phase}6-html")]:
            try:
                with urlopen(args.base_url+path,timeout=15) as resp:
                    body=resp.read(2000000).decode("utf-8","replace")
                    records.append({"id":id_,"passed":resp.status==200 and marker in body,
                                    "observed":{"status":resp.status,"contains_contract":marker in body}})
            except (OSError,HTTPError) as e:
                records.append({"id":id_,"passed":False,"observed":{"error":str(e)}})
    verdict={
       "phase":args.phase,
       "method":{"A":"native narrowly scoped Field.update after manual update",
                 "B":"stale full Pack import after manual update",
                 "C":"guarded narrow update, expected stale-base rejection after human saved edit"}[args.phase],
       "criteria":"Observed behavior against preregistered phase oracle; PASS may indicate an unsafe overwrite!",
       "checks":records,
       "summary":{"passed":sum(bool(x["passed"]) for x in records),"total":len(records)},
       "is_real_ai_agent":False,
       "is_visual_editor_session":False,
    }
    Path(args.output).write_text(json.dumps(verdict,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for x in records:
        print(x["id"],"PASS" if x["passed"] else "FAIL",json.dumps(x["observed"],ensure_ascii=False))
    return 0 if all(x["passed"] for x in records) else 1

if __name__=="__main__":
    sys.exit(main())
