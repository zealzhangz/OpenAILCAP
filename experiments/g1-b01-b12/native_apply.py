"""Run B11 real atomic native SQLite apply under Saltcorn UID, stdin only."""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"g1-b01-b11"))
from apply_worker import apply,Refused

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--db",required=True)
    p.add_argument("--fail-before-commit",action="store_true")
    args=p.parse_args()
    if not args.db.startswith("/tmp/s1-b12-project-") or (
        "/runtime-private/projection-v1.sqlite" not in args.db
    ):
        raise SystemExit(3)
    raw=sys.stdin.buffer.read(128*1024+1)
    if len(raw)>128*1024:
        raise SystemExit(3)
    try:
        result=apply(args.db,json.loads(raw),args.fail_before_commit)
        print("S1_B12_APPLY|"+json.dumps(result),flush=True)
    except (Refused,ValueError,sqlite3.Error) as exc:
        print("S1_B12_REJECT|"+json.dumps({
            "error":getattr(exc,"code","INVALID_BATCH_OR_SQL")}),flush=True)
        raise SystemExit(3) from None

if __name__=="__main__":
    main()
