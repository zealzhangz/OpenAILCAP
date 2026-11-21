"""Verify real Saltcorn native pack ingestion, SQLite metadata, REST, and HTML.

No claim about AI generation, approval workflow, or full contract TC01..TC18.
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

def get(url):
    try:
        with urlopen(url, timeout=12) as r:
            return r.status, r.read(2000000).decode("utf-8", "replace")
    except HTTPError as e:
        return e.code, e.read(10000).decode("utf-8", "replace")

def run(db_path, base_url):
    results=[]
    def record(i,ok,actual):
        results.append({"id":i,"status":"PASS" if ok else "FAIL","actual":actual})
    try:
        with sqlite3.connect(f"file:{Path(db_path).resolve()}?mode=ro",uri=True) as db:
            tables={r[0] for r in db.execute("SELECT name FROM _sc_tables")}
            record("PK01-native-tables", {"s1_contracts","s1_approvals"}.issubset(tables),
                   {"matched":sorted(tables & {"s1_contracts","s1_approvals"})})
            fields={r[0] for r in db.execute("SELECT name FROM _sc_fields WHERE table_id=(SELECT id FROM _sc_tables WHERE name='s1_contracts')")}
            record("PK02-contract-fields", {"contract_no","title","amount_minor","status"}.issubset(fields),
                   {"fields":sorted(fields)})
            relation=db.execute("SELECT name,reftable_name,type FROM _sc_fields WHERE table_id=(SELECT id FROM _sc_tables WHERE name='s1_approvals') AND name='contract_ref'").fetchone()
            record("PK03-key-reference", bool(relation and relation[1]=="s1_contracts"),
                   {"relation":relation})
            columns={r[1] for r in db.execute('PRAGMA table_info("s1_contracts")')}
            record("PK04-real-sql-columns", {"contract_no","amount_minor"}.issubset(columns),{"columns":sorted(columns)})
            row=db.execute('SELECT contract_no,title,amount_minor,status FROM "s1_contracts" WHERE contract_no=?',("HT-2026-000001",)).fetchone()
            record("PK05-real-sql-row", row==("HT-2026-000001","S1 Platform Contract",100000001,"Draft"),
                   {"matched":row==("HT-2026-000001","S1 Platform Contract",100000001,"Draft")})
            views={r[0] for r in db.execute("SELECT name FROM _sc_views")}
            record("PK06-lowcode-view", "s1_contract_list" in views,{"exists":"s1_contract_list" in views})
    except (sqlite3.Error,OSError) as e:
        record("PK-db-error",False,{"exception":str(e)})
    for name,url in [("PK07-real-rest","/api/s1_contracts/"),
                     ("PK08-real-render","/view/s1_contract_list"),
                     ("PK09-private-approval","/api/s1_approvals/")]:
        try:
            status,body=get(base_url+url)
            if name=="PK07-real-rest":
                decoded=json.loads(body)
                rows=decoded.get("success") if isinstance(decoded,dict) else None
                good=status==200 and isinstance(rows,list) and any(x.get("contract_no")=="HT-2026-000001" and x.get("amount_minor")==100000001 for x in rows)
                actual={"status":status,"matched_contract":good}
            elif name=="PK08-real-render":
                good=status==200 and "HT-2026-000001" in body
                actual={"status":status,"contains_contract":good}
            else:
                good=status==401
                actual={"status":status,"forbidden_to_anonymous":good}
            record(name,good,actual)
        except Exception as e:
            record(name,False,{"error":str(e)})
    return results

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--db",required=True)
    p.add_argument("--output",default="/tmp/s1-saltcorn-contract.json")
    p.add_argument("--base-url",default="http://127.0.0.1:3100")
    a=p.parse_args()
    results=run(a.db,a.base_url)
    data={"study":"Saltcorn real native contract Pack", "scope":"real platform configured via native Pack, NOT AI-generated and NOT approval flow",
          "checks":results,"summary":{"passed":sum(x["status"]=="PASS" for x in results),"total":len(results)},
          "openailcap_contract_tc_passed":0,
          "limitations":["amount_minor is integer cents, NOT decimal(12,2) field","Seed performed using privileged CLI for fixture, NOT normal user interface",
                         "No approval workflow implemented","No Agent", "No deployment/rollback verified"]}
    Path(a.output).write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for case in results:print(case["id"],case["status"],json.dumps(case["actual"],ensure_ascii=False))
    return 0 if len(results)==9 and all(x["status"]=="PASS" for x in results) else 1
if __name__=="__main__":
    sys.exit(main())
