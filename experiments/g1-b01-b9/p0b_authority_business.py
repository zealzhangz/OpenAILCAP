"""G1 P0-B: independent B11 outbox / B2 RECORDS consistency oracle.

Runs ONLY in the B9 trusted Domain Kernel UID, against the same private
authority.sqlite that serves human/Agent/Plugin requests. B11 AFTER triggers
are transactionally coupled to B2 record inserts/updates. Verify contiguous
event-time history AND match every event's latest record/version against
the actual B2 records table using one read transaction. No made-up Native
seed rows may be treated as authoritative data. Returns a digest/head, not
any authority SQLite handle to Publisher/Reader.

Bounded app-a/model.contracts research case; not general CDC or HA.
"""
from __future__ import annotations
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"g1-b01-b11"))
from projection_source import install,event_of,ProjectionRefused

FIELDS={"contract_no","title","amount_minor","status"}
MAX_EVENTS=1000
MAX_ROWS=256


class AuthorityDataRejected(Exception):
    def __init__(self,code):
        super().__init__(code)
        self.code=code


def canon(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,
                      separators=(",",":"))


def rows_digest(rows):
    return hashlib.sha256(canon(sorted(
        rows,key=lambda r:r["contract_no"])).encode("utf-8")).hexdigest()


def read_business(dbpath):
    # A single B2 SQLite snapshot protects event head/records consistency.
    with sqlite3.connect("file:"+str(dbpath)+"?mode=ro",
                         uri=True,timeout=10) as db:
        db.row_factory=sqlite3.Row
        db.execute("BEGIN")
        try:
            event_rows=db.execute(
                "SELECT app,seq,model,record_id,version,content "
                "FROM b11_outbox WHERE app=? ORDER BY seq",("app-a",)
            ).fetchall()
            record_rows=db.execute(
                "SELECT record_id,version,content FROM records "
                "WHERE app=? AND model=? ORDER BY record_id",
                ("app-a","model.contracts")
            ).fetchall()
            db.commit()
        except sqlite3.Error:
            db.rollback()
            raise AuthorityDataRejected("AUTHORITY_OUTBOX_UNAVAILABLE") from None
    if len(event_rows)>MAX_EVENTS or len(record_rows)>MAX_ROWS:
        raise AuthorityDataRejected("AUTHORITY_DATA_LIMIT")
    events=[]
    latest={}
    for idx,source in enumerate(event_rows,1):
        try:
            item=event_of(source)
        except (ProjectionRefused,ValueError,TypeError,KeyError):
            raise AuthorityDataRejected("AUTHORITY_OUTBOX_PAYLOAD_INVALID") from None
        if (item["seq"]!=idx or item["app"]!="app-a" or
            item["model"]!="model.contracts" or
            type(item["version"]) is not int or item["version"]<1):
            raise AuthorityDataRejected("AUTHORITY_OUTBOX_SEQ_OR_SCOPE_INVALID")
        old=latest.get(item["recordId"])
        if old is not None and item["version"]!=old["version"]+1:
            raise AuthorityDataRejected("AUTHORITY_OUTBOX_VERSION_GAP")
        if old is None and item["version"]!=1:
            raise AuthorityDataRejected("AUTHORITY_OUTBOX_INITIAL_VERSION")
        latest[item["recordId"]]={
            "version":item["version"],"cells":item["cells"]}
        events.append(item)
    actual={}
    for row in record_rows:
        try:cells=json.loads(row["content"])
        except (ValueError,TypeError):
            raise AuthorityDataRejected("AUTHORITY_B2_RECORD_BAD_JSON") from None
        if (not isinstance(cells,dict) or set(cells)!=FIELDS or
            type(row["version"]) is not int or row["version"]<1):
            raise AuthorityDataRejected("AUTHORITY_B2_RECORD_SHAPE_INVALID")
        if row["record_id"] in actual:
            raise AuthorityDataRejected("AUTHORITY_B2_DUPLICATE_RECORD")
        actual[row["record_id"]]={"version":row["version"],"cells":cells}
    if actual!=latest:
        raise AuthorityDataRejected("AUTHORITY_B2_OUTBOX_ROWS_DIVERGED")
    result_rows=[entry["cells"] for entry in actual.values()]
    if len({row["contract_no"] for row in result_rows})!=len(result_rows):
        raise AuthorityDataRejected("AUTHORITY_DUPLICATE_CONTRACT_NO")
    return {
        "head":len(events),
        "rows":sorted(result_rows,key=lambda r:r["contract_no"]),
        "rowsDigest":rows_digest(result_rows),
        "events":events
    }
