"""TEST fixture only: copy four native fields into B15 schema, atomically.

No B2 signature/source verification; this is NOT the B15 trusted publisher.
"""
import argparse
import os
from pathlib import Path
import sqlite3
import tempfile
from snapshot_web import rows_digest


def write_snapshot(output, rows, head, manifest):
    output = Path(output)
    fd, name = tempfile.mkstemp(prefix=".b17-", suffix=".sqlite", dir=output.parent)
    os.close(fd)
    temp = Path(name)
    try:
        with sqlite3.connect(temp) as db:
            db.execute("CREATE TABLE published_contracts(contract_no TEXT PRIMARY KEY,"
                       "title TEXT NOT NULL,amount_minor INTEGER NOT NULL,status TEXT NOT NULL)")
            db.execute("CREATE TABLE published_state(head INTEGER NOT NULL,"
                       "rows_digest TEXT NOT NULL,manifest_hash TEXT NOT NULL)")
            db.executemany("INSERT INTO published_contracts VALUES(?,?,?,?)",
                           [(r['contract_no'], r['title'], r['amount_minor'], r['status']) for r in rows])
            db.execute("INSERT INTO published_state VALUES(?,?,?)", (head, rows_digest(rows), manifest))
        temp.chmod(0o640)
        with temp.open("rb") as stream:
            os.fsync(stream.fileno())
        os.replace(temp, output)
        fd = os.open(output.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        temp.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--native-db", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--head", type=int, required=True)
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()
    with sqlite3.connect("file:" + args.native_db + "?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        rows = [dict(r) for r in db.execute("SELECT contract_no,title,amount_minor,status FROM s1_contracts ORDER BY contract_no")]
    write_snapshot(args.output, rows, args.head, args.manifest)
    print("B17_FIXTURE_PUBLISHED", args.head, len(rows), flush=True)


if __name__ == "__main__":
    main()
