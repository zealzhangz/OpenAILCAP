"""B11 authoritative, transactionally coupled append-only projection outbox.

SQLite AFTER INSERT/UPDATE triggers run in EXACTLY the same transaction as
the existing B2 SchemaStore.submit_form/advance record changes. No change
to B2 core, no polling "latest" and pretending it is CDC. Projection is
limited to app-a/model.contracts and a fixed public-column allowlist. The
outbox records immutable event-time payload (not the latest current row).
A compromised kernel UID/root can still bypass these assumptions.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3

FIELDS=("contract_no","title","amount_minor","status")


class ProjectionRefused(Exception):
    def __init__(self,status,code):
        self.status=status
        self.code=code
        super().__init__(code)


def canon(x):
    return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(",",":"))


def digest(x):
    return hashlib.sha256(canon(x).encode()).hexdigest()


def install(db_path):
    with sqlite3.connect(db_path,timeout=10) as c:
        c.executescript("""
          CREATE TABLE IF NOT EXISTS b11_outbox(
            app TEXT NOT NULL,
            seq INTEGER NOT NULL,
            model TEXT NOT NULL,
            record_id TEXT NOT NULL,
            version INTEGER NOT NULL,
            content TEXT NOT NULL,
            PRIMARY KEY(app,seq)
          );
          CREATE TRIGGER IF NOT EXISTS b11_record_insert
          AFTER INSERT ON records
          WHEN NEW.app='app-a' AND NEW.model='model.contracts'
          BEGIN
            INSERT INTO b11_outbox(app,seq,model,record_id,version,content)
            VALUES(
              NEW.app,
              (SELECT COALESCE(MAX(seq),0)+1 FROM b11_outbox
               WHERE app=NEW.app),
              NEW.model,NEW.record_id,NEW.version,NEW.content
            );
          END;
          CREATE TRIGGER IF NOT EXISTS b11_record_update
          AFTER UPDATE OF content,version ON records
          WHEN NEW.app='app-a' AND NEW.model='model.contracts'
          BEGIN
            INSERT INTO b11_outbox(app,seq,model,record_id,version,content)
            VALUES(
              NEW.app,
              (SELECT COALESCE(MAX(seq),0)+1 FROM b11_outbox
               WHERE app=NEW.app),
              NEW.model,NEW.record_id,NEW.version,NEW.content
            );
          END;
        """)


def event_of(row):
    content=json.loads(row["content"])
    if not isinstance(content,dict) or set(content)!=set(FIELDS):
        raise ProjectionRefused(503,"SOURCE_PAYLOAD_SCHEMA_DRIFT")
    if not (isinstance(content["contract_no"],str) and
            isinstance(content["title"],str) and
            isinstance(content["status"],str) and
            type(content["amount_minor"]) is int):
        raise ProjectionRefused(503,"SOURCE_PAYLOAD_TYPE_DRIFT")
    event={"app":row["app"],"seq":row["seq"],"model":row["model"],
           "recordId":row["record_id"],"version":row["version"],
           "cells":{key:content[key] for key in FIELDS}}
    return {**event,"eventHash":digest(event)}


def pull(db_path,app,after,limit):
    if app!="app-a":
        raise ProjectionRefused(403,"PROJECTION_APP_FORBIDDEN")
    if type(after) is not int or after<0 or after>10**12 or (
        type(limit) is not int or not 1<=limit<=100
    ):
        raise ProjectionRefused(422,"PROJECTION_CURSOR_INVALID")
    with sqlite3.connect(
        "file:"+str(db_path)+"?mode=ro",uri=True,timeout=10
    ) as c:
        c.row_factory=sqlite3.Row
        c.execute("BEGIN")
        head=c.execute(
            "SELECT COALESCE(MAX(seq),0) FROM b11_outbox WHERE app=?",
            (app,)
        ).fetchone()[0]
        rows=c.execute(
            "SELECT app,seq,model,record_id,version,content "
            "FROM b11_outbox WHERE app=? AND seq>? ORDER BY seq LIMIT ?",
            (app,after,limit)
        ).fetchall()
        c.commit()
    events=[event_of(row) for row in rows]
    if any(event["seq"]!=after+i+1 for i,event in enumerate(events)):
        raise ProjectionRefused(503,"SOURCE_OUTBOX_SEQUENCE_GAP")
    return {"app":app,"after":after,"head":head,
            "events":events,
            "hasMore":bool(events and events[-1]["seq"]<head)}
