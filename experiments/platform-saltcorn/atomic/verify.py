"""Independent SQLite assertions AND separate-process CLI outcome checks."""
from __future__ import annotations
import argparse
import json
import sqlite3
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

WINNERS = {"Writer Alpha", "Writer Beta"}

def read_marker(log_file: str):
    lines = Path(log_file).read_text(encoding="utf-8", errors="replace").splitlines()
    events = []
    for line in lines:
        if line.startswith("S1_ATOMIC_") and "|" in line:
            label, payload = line.split("|", 1)
            events.append((label.removeprefix("S1_ATOMIC_"), json.loads(payload)))
    if len(events) != 1:
        raise AssertionError(f"Expected one real CLI outcome in {log_file}; found {len(events)}")
    return events[0]

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--phase", required=True, choices=["wrapper", "disjoint", "collision",
                                                     "injected", "bypass-human", "bypass-agent", "http"])
    p.add_argument("--db", required=True)
    p.add_argument("--log-dir", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--base-url", default="http://127.0.0.1:3100")
    args = p.parse_args()
    checks=[]
    def add(name, good, detail):
        checks.append({"name":name,"passed":bool(good),"observed":detail})
    with sqlite3.connect(f"file:{Path(args.db).resolve()}?mode=ro", uri=True) as db:
        sql = "SELECT name,label FROM _sc_fields WHERE table_id=(SELECT id FROM _sc_tables WHERE name='s1_contracts') AND name IN ('title','status')"
        labels = dict(db.execute(sql))
        ledgers = {}
        if args.phase != "wrapper":
            ledgers = dict(db.execute("SELECT resource_id,revision FROM _openailcap_s1_guard"))
        row = db.execute("SELECT contract_no,amount_minor FROM s1_contracts WHERE contract_no='HT-2026-000001'").fetchone()
        add("physical-platform-business-row",row == ("HT-2026-000001",100000001),
            {"row_preserved":row == ("HT-2026-000001",100000001)})
        phase = args.phase
        if phase=="wrapper":
            add("native-transaction-wrapper-unsafe-write-survived",labels.get("title")=="Unrolled Back Label",
                {"title_label":labels.get("title"),"unsafe_behavior":True})
        if phase=="disjoint":
            add("separate-process-title",labels.get("title")=="Human Checked",{"value":labels.get("title")})
            add("separate-process-status",labels.get("status")=="Automation Checked",{"value":labels.get("status")})
            add("scoped-revisions",ledgers=={"title":1,"status":1},{"revisions":ledgers})
            for log in ("d-title","d-status"):
                result,payload = read_marker(str(Path(args.log_dir)/(log+".log")))
                add("disjoint-"+log,result=="APPLIED" and payload["id"]==log,
                    {"result":result,"id":payload["id"]})
        if phase in ("collision","injected","bypass-human","bypass-agent","http"):
            add("same-resource-version",ledgers.get("title")==2,
                {"title_revision":ledgers.get("title")})
            add("winner-survives",labels.get("title") in WINNERS,{"value":labels.get("title")})
        if phase=="collision":
            statuses=[]
            for log in ("c-alpha","c-beta"):
                status,payload = read_marker(str(Path(args.log_dir)/(log+".log")))
                statuses.append(status)
            add("one-applied-one-rejected",sorted(statuses)==["APPLIED","STALE"],{"outcomes":statuses})
            add("status-unchanged",labels.get("status")=="Automation Checked",{"value":labels.get("status")})
        if phase=="injected":
            status,payload=read_marker(str(Path(args.log_dir)/"f-title.log"))
            add("injected-error-rollback-observed",status=="ROLLED_BACK",{"outcome":status})
            add("injected-wrong-value-absent",labels.get("title")!="INJECTED_INVALID",
                {"title_label":labels.get("title")})
        if phase=="bypass-human":
            add("unguarded-manual-write",labels.get("status")=="Ungoverned Human",
                {"value":labels.get("status")})
            add("ledger-did-not-observe-manual-write",ledgers.get("status")==1,{"revision":ledgers.get("status"),
                "unsafe_out_of_band":True})
        if phase in ("bypass-agent","http"):
            add("blind-cas-lost-unguarded-edit",labels.get("status")=="Unaware Agent",
                {"value":labels.get("status"),"unsafe_loss":True})
            add("guard-version-after-blind-write",ledgers.get("status")==2,{"revision":ledgers.get("status")})
        if phase=="bypass-agent":
            status,payload=read_marker(str(Path(args.log_dir)/"b-status.log"))
            add("cas-misleadingly-applied",status=="APPLIED",{"outcome":status,"unsafe_loss":True})
    if args.phase=="http":
        for path,term in [("/api/s1_contracts/","HT-2026-000001"),
                          ("/view/s1_contract_list","HT-2026-000001")]:
            try:
                with urlopen(args.base_url+path,timeout=10) as r:
                    body=r.read(2000000).decode("utf-8","replace")
                    add("real-http-"+path, r.status==200 and term in body,
                        {"status":r.status,"contract_present":term in body})
            except (HTTPError, OSError) as exc:
                add("real-http-"+path,False,{"error":str(exc)})
    result={"study":"OpenAILCAP H03 actual Saltcorn native field and SQLite transaction probe",
            "phase":args.phase,
            "checks":checks,
            "summary":{"passed":sum(c["passed"] for c in checks),"total":len(checks)},
            "real_platform":True,
            "real_llm_agent":False,
            "real_browser_editor":False,
            "production_ready_cas":False,
            "important":"PASS of wrapper or bypass means unsafe loss was reproduced, NOT safety proven"}
    Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for c in checks: print(c["name"],"PASS" if c["passed"] else "FAIL",json.dumps(c["observed"],ensure_ascii=False))
    return 0 if len(checks)>1 and all(c["passed"] for c in checks) else 1

if __name__=="__main__":
    sys.exit(main())
