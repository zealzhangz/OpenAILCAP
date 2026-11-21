#!/usr/bin/env python3
"""Independent physical DB confirmation of native Saltcorn CLI bypass after C2 UI patch."""
import argparse
import json
import sqlite3
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument("--db",required=True)
p.add_argument("--output",required=True)
args=p.parse_args()
with sqlite3.connect("file:"+str(Path(args.db).resolve())+"?mode=ro",uri=True) as db:
    row=db.execute(
        "SELECT f.label FROM _sc_fields f JOIN _sc_tables t ON f.table_id=t.id "
        "WHERE t.name='s1_contracts' AND f.name='title'").fetchone()
label=row[0] if row else None
passed=label=="Native Outside Gateway"
result={
    "id":"C2-09-native-Field.update-bypass-still-possible",
    "expected_negative_control":True,
    "status":"PASS" if passed else "FAIL",
    "physical_sql_label":label,
    "risk":"unpatched Field.update via CLI bypasses guarded web route",
    "g1_b01_closed":False
}
Path(args.output).write_text(json.dumps(result,indent=2)+"\n")
print("S1_C2_BYPASS",json.dumps(result))
if not passed: raise SystemExit(1)
