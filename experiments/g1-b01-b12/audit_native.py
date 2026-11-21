"""B12 full mapped-row integrity audit, native SQLite owner UID.

Only reports whether the current derived table matches the B11 record-map
checkpoint; does not authenticate B2 or guard direct native HTTP access.
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"g1-b01-b11"))
from apply_worker import digest

def audit(db_path):
    with sqlite3.connect("file:"+str(db_path)+"?mode=ro",uri=True) as db:
        db.row_factory=sqlite3.Row
        db.execute("BEGIN")
        cursor=db.execute("SELECT last_seq FROM b11_projection_cursor "
                          "WHERE app='app-a'").fetchone()[0]
        receipts=db.execute(
            "SELECT seq FROM b11_projection_receipts "
            "WHERE app='app-a' ORDER BY seq").fetchall()
        mappings=db.execute(
            "SELECT contract_no,cells_hash FROM b11_record_map "
            "WHERE app='app-a'").fetchall()
        rows=db.execute(
            "SELECT contract_no,title,amount_minor,status "
            "FROM s1_contracts ORDER BY contract_no").fetchall()
        db.commit()
    receipts_ok=([r["seq"] for r in receipts]==list(range(1,cursor+1)))
    expected={r["contract_no"]:r["cells_hash"] for r in mappings}
    actual={r["contract_no"]:digest(dict(r)) for r in rows}
    clean=(receipts_ok and expected==actual and len(rows)==len(actual) and
           len(mappings)==len(expected))
    return {"clean":clean,"cursor":cursor,"mapped":len(expected),
            "actualRows":len(rows),"receipts":len(receipts),
            "receiptSequenceValid":receipts_ok}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--db",required=True)
    args=p.parse_args()
    if not args.db.startswith("/tmp/s1-b12-project-") or (
        "/runtime-private/projection-v1.sqlite" not in args.db
    ):
        raise SystemExit(3)
    try: result=audit(args.db)
    except sqlite3.Error:
        result={"clean":False,"reason":"NATIVE_SQL_UNAVAILABLE"}
    print("S1_B12_AUDIT|"+json.dumps(result),flush=True)

if __name__=="__main__":
    main()
