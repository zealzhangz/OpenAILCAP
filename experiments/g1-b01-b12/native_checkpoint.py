"""Read B11 durable native SQLite checkpoint as the Saltcorn runtime UID."""
import argparse
import json
import sqlite3
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--db",required=True)
    args=p.parse_args()
    db=Path(args.db)
    if not str(db).startswith("/tmp/s1-b12-project-") or (
        "/runtime-private/projection-v1.sqlite" not in str(db)
    ):
        raise SystemExit(3)
    with sqlite3.connect("file:"+str(db)+"?mode=ro",uri=True) as c:
        cursor=c.execute("SELECT last_seq FROM b11_projection_cursor "
                         "WHERE app='app-a'").fetchone()[0]
    print("S1_B12_CHECKPOINT|"+json.dumps({"lastSeq":cursor}),flush=True)

if __name__=="__main__":
    main()
