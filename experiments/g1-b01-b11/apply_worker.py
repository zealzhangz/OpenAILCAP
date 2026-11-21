"""B11 actual Saltcorn SQLite derived-table event apply, under Saltcorn OS UID.

The event transport is a trusted controller's stdin JSON; Saltcorn itself
NEVER receives the source token, Kernel config, DB or an HTTP write grant.
One transaction commits native row, source-record mapping, event receipt
and projection checkpoint. The applied native DB remains disposable.
This is a restricted demo for ONE model and ONE app, not general CDC.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

FIELDS=("contract_no","title","amount_minor","status")


class Refused(Exception):
    def __init__(self,code):
        self.code=code
        super().__init__(code)


def canon(x):
    return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(",",":"))


def digest(x):
    return hashlib.sha256(canon(x).encode()).hexdigest()


def ensure_tables(db):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS b11_projection_cursor(
          app TEXT PRIMARY KEY,
          last_seq INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS b11_projection_receipts(
          app TEXT NOT NULL,seq INTEGER NOT NULL,
          event_hash TEXT NOT NULL,
          PRIMARY KEY(app,seq)
        );
        CREATE TABLE IF NOT EXISTS b11_record_map(
          app TEXT NOT NULL,record_id TEXT NOT NULL,
          contract_no TEXT NOT NULL,version INTEGER NOT NULL,
          cells_hash TEXT NOT NULL,
          PRIMARY KEY(app,record_id),UNIQUE(app,contract_no)
        );
    """)
    db.execute(
        "INSERT OR IGNORE INTO b11_projection_cursor(app,last_seq) "
        "VALUES ('app-a',0)"
    )


def validate(e):
    if not isinstance(e,dict) or set(e)!={
        "app","seq","model","recordId","version","cells","eventHash"
    } or e["app"]!="app-a" or e["model"]!="model.contracts":
        raise Refused("EVENT_SCOPE_OR_SHAPE_INVALID")
    if type(e["seq"]) is not int or e["seq"]<1 or (
        type(e["version"]) is not int or e["version"]<1
    ) or not isinstance(e["recordId"],str) or not (
        len(e["recordId"])==18 and
        all(x in "0123456789abcdef" for x in e["recordId"])
    ):
        raise Refused("EVENT_IDENTITY_INVALID")
    cells=e["cells"]
    if not isinstance(cells,dict) or set(cells)!=set(FIELDS) or (
        any(not isinstance(cells[k],str) or not 1<=len(cells[k])<=256
            for k in ("contract_no","title","status"))
    ) or type(cells["amount_minor"]) is not int or not (
        0<=cells["amount_minor"]<=10**14
    ):
        raise Refused("EVENT_CELLS_INVALID")
    unsigned={k:e[k] for k in (
        "app","seq","model","recordId","version","cells"
    )}
    if not isinstance(e["eventHash"],str) or (
        digest(unsigned)!=e["eventHash"]
    ):
        raise Refused("EVENT_HASH_INVALID")


def apply(db_path,batch,fail_before_commit=False):
    if not isinstance(batch,dict) or set(batch)!={
        "app","after","events"
    } or batch["app"]!="app-a" or type(batch["after"]) is not int or (
        batch["after"]<0
    ) or not isinstance(batch["events"],list) or (
        len(batch["events"])>100
    ):
        raise Refused("BATCH_INVALID")
    # trusted native process owns this derived DB, never the authority DB.
    with sqlite3.connect(db_path,timeout=10,isolation_level=None) as db:
        db.row_factory=sqlite3.Row
        ensure_tables(db)
        try:
            db.execute("BEGIN IMMEDIATE")
            cursor=db.execute(
                "SELECT last_seq FROM b11_projection_cursor "
                "WHERE app='app-a'"
            ).fetchone()[0]
            if batch["after"]>cursor:
                raise Refused("CURSOR_AHEAD_OF_APPLIED")
            applied=0
            replayed=0
            for event in batch["events"]:
                validate(event)
                seq=event["seq"]
                h=event["eventHash"]
                if seq<=cursor:
                    prior=db.execute(
                        "SELECT event_hash FROM b11_projection_receipts "
                        "WHERE app='app-a' AND seq=?",(seq,)
                    ).fetchone()
                    if prior is None or prior["event_hash"]!=h:
                        raise Refused("REPLAY_HASH_CONFLICT")
                    replayed+=1
                    continue
                if seq!=cursor+1:
                    raise Refused("EVENT_SEQUENCE_GAP")
                cells=event["cells"]
                record_id=event["recordId"]
                old=db.execute(
                    "SELECT * FROM b11_record_map "
                    "WHERE app='app-a' AND record_id=?",(record_id,)
                ).fetchone()
                if old is None:
                    if event["version"]!=1:
                        raise Refused("NEW_RECORD_VERSION_NOT_ONE")
                    if db.execute(
                        "SELECT COUNT(*) FROM s1_contracts WHERE contract_no=?",
                        (cells["contract_no"],)
                    ).fetchone()[0]:
                        raise Refused("NATIVE_UNOWNED_CONTRACT_CONFLICT")
                    db.execute(
                        "INSERT INTO s1_contracts "
                        "(contract_no,title,amount_minor,status) "
                        "VALUES (?,?,?,?)",
                        tuple(cells[k] for k in FIELDS)
                    )
                    db.execute(
                        "INSERT INTO b11_record_map VALUES (?,?,?,?,?)",
                        ("app-a",record_id,cells["contract_no"],
                         event["version"],digest(cells))
                    )
                else:
                    if event["version"]!=old["version"]+1 or (
                        cells["contract_no"]!=old["contract_no"]
                    ):
                        raise Refused("SOURCE_RECORD_VERSION_CONFLICT")
                    current=db.execute(
                        "SELECT contract_no,title,amount_minor,status "
                        "FROM s1_contracts WHERE contract_no=?",
                        (old["contract_no"],)
                    ).fetchall()
                    if len(current)!=1 or digest(dict(current[0]))!=(
                        old["cells_hash"]
                    ):
                        raise Refused("NATIVE_DERIVED_ROW_DRIFT")
                    result=db.execute(
                        "UPDATE s1_contracts SET title=?,amount_minor=?,"
                        "status=? WHERE contract_no=?",
                        (cells["title"],cells["amount_minor"],
                         cells["status"],cells["contract_no"])
                    )
                    if result.rowcount!=1:
                        raise Refused("NATIVE_ROW_LOST")
                    db.execute(
                        "UPDATE b11_record_map SET version=?,cells_hash=? "
                        "WHERE app='app-a' AND record_id=?",
                        (event["version"],digest(cells),record_id)
                    )
                db.execute(
                    "INSERT INTO b11_projection_receipts VALUES (?,?,?)",
                    ("app-a",seq,h)
                )
                cursor=seq
                applied+=1
            db.execute(
                "UPDATE b11_projection_cursor SET last_seq=? "
                "WHERE app='app-a'",(cursor,)
            )
            if fail_before_commit:
                raise Refused("INJECTED_BEFORE_COMMIT")
            db.commit()
            return {"lastSeq":cursor,"applied":applied,
                    "replayed":replayed}
        except BaseException:
            if db.in_transaction:db.rollback()
            raise


def inspect(db_path):
    with sqlite3.connect(
        "file:"+str(db_path)+"?mode=ro",uri=True
    ) as db:
        db.row_factory=sqlite3.Row
        cursor=db.execute(
            "SELECT last_seq FROM b11_projection_cursor "
            "WHERE app='app-a'"
        ).fetchone()
        rows=db.execute(
            "SELECT contract_no,title,amount_minor,status "
            "FROM s1_contracts ORDER BY contract_no"
        ).fetchall()
        return {"lastSeq":cursor["last_seq"] if cursor else None,
                "rows":[dict(r) for r in rows],
                "receipts":db.execute(
                    "SELECT COUNT(*) FROM b11_projection_receipts"
                ).fetchone()[0],
                "mappings":db.execute(
                    "SELECT COUNT(*) FROM b11_record_map"
                ).fetchone()[0]}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--db",required=True)
    p.add_argument("--inspect",action="store_true")
    p.add_argument("--fail-before-commit",action="store_true")
    args=p.parse_args()
    path=Path(args.db)
    if not path.is_absolute() or not str(path).startswith(
        "/tmp/s1-b11-project-"
    ) or "/runtime-private/projection-" not in str(path) or (
        path.suffix!=".sqlite"
    ):
        raise SystemExit("B11_DERIVED_DB_PATH_REQUIRED")
    try:
        if args.inspect:
            result=inspect(path)
        else:
            raw=sys.stdin.buffer.read(256*1024+1)
            if len(raw)>256*1024:
                raise Refused("BATCH_TOO_LARGE")
            result=apply(path,json.loads(raw),
                         args.fail_before_commit)
        print("S1_B11_NATIVE_APPLY|"+canon(result),flush=True)
    except (Refused,ValueError,sqlite3.Error) as exc:
        code=exc.code if isinstance(exc,Refused) else (
            "INVALID_BATCH_OR_NATIVE_SQL"
        )
        print("S1_B11_NATIVE_REJECT|"+canon({"error":code}),flush=True)
        raise SystemExit(3) from None


if __name__=="__main__":
    main()
