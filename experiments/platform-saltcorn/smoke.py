#!/usr/bin/env python3
"""Independent Saltcorn runtime smoke, NOT a contract benchmark."""
import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

def fetch(url):
    try:
        with urlopen(url, timeout=8) as r:
            return r.status, r.read(2000000).decode("utf-8", "replace")
    except HTTPError as e:
        return e.code, e.read(2000).decode("utf-8", "replace")

def run(dbpath, base):
    cases = []
    def check(cid, good, observed):
        cases.append({"id": cid, "status": "PASS" if good else "FAIL", "observed": observed})
    try:
        with sqlite3.connect(f"file:{Path(dbpath).resolve()}?mode=ro", uri=True) as db:
            names = {a[0] for a in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            check("SC01-schema", {"_sc_tables", "_sc_fields", "_sc_views"}.issubset(names),
                  {"schema_objects_exist": {"_sc_tables", "_sc_fields", "_sc_views"}.issubset(names)})
            tables = {a[0] for a in db.execute("SELECT name FROM _sc_tables")}
            check("SC02-tables", {"books", "patients"}.issubset(tables), {"fixtures_present": sorted(tables & {"books", "patients"})})
            fields = {a[0] for a in db.execute("SELECT name FROM _sc_fields WHERE table_id=(SELECT id FROM _sc_tables WHERE name='books')")}
            check("SC03-fields", "author" in fields, {"author_exists": "author" in fields})
            views = {a[0] for a in db.execute("SELECT name FROM _sc_views")}
            check("SC04-views", "authorlist" in views, {"authorlist_exists": "authorlist" in views})
    except (sqlite3.DatabaseError, OSError) as e:
        check("SC01-SC04-storage-error", False, {"error": str(e)})
    for case_id, endpoint in [("SC05-rest", "/api/books/"), ("SC06-render", "/view/authorlist"), ("SC07-auth", "/api/patients/")]:
        try:
            status, body = fetch(base + endpoint)
            if case_id == "SC05-rest":
                data = json.loads(body).get("success")
                good = status == 200 and isinstance(data, list) and any(
                    x.get("author") == "Herman Melville" for x in data)
                observed = {"status": status, "fixture_data": good}
            elif case_id == "SC06-render":
                good = status == 200 and "Tolstoy" in body
                observed = {"status": status, "rendered_text_present": "Tolstoy" in body}
            else:
                good = status == 401
                observed = {"status": status, "unauthenticated_denied": good}
            check(case_id, good, observed)
        except Exception as e:
            check(case_id, False, {"error": str(e)})
    return cases

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db", required=True)
    p.add_argument("--base-url", default="http://127.0.0.1:3100")
    p.add_argument("--output", default="/tmp/s1-saltcorn-results.json")
    a = p.parse_args()
    result = run(a.db, a.base_url)
    obj = {
        "study": "OpenAILCAP S1 Saltcorn real runtime smoke",
        "upstream_sha_inspected": "515254bee5a98df70530cc59846b1df02d5db350",
        "date_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Actual third-party fixtures/models/views/REST, NOT OpenAILCAP contract",
        "checks": result,
        "summary": {"passed": sum(x["status"] == "PASS" for x in result), "total": len(result)},
        "contract_platform_tasks_passed": 0,
        "limitations": ["No custom contract application", "No AI development",
                        "No human/AI multi-round edit", "No plugin installation or deployment"],
    }
    Path(a.output).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for case in result:
        print(case["id"], case["status"], json.dumps(case["observed"], ensure_ascii=False))
    return 0 if len(result) == 7 and all(x["status"] == "PASS" for x in result) else 1

if __name__ == "__main__":
    sys.exit(main())
