"""Trusted read-only physical SQLite inspector, run as dedicated kernel UID.

This inspector does not import or call SchemaStore or ToolBroker. It derives
manifest/data hashes independently and reads the actual database file, not
cached HTTP response objects.
"""
import argparse
import hashlib
import json
import sqlite3


def digest(value):
    return hashlib.sha256(json.dumps(
        value,ensure_ascii=False,sort_keys=True,separators=(",",":")
    ).encode()).hexdigest()


def read(dbfile):
    uri="file:"+dbfile+"?mode=ro"
    with sqlite3.connect(uri,uri=True,timeout=2) as db:
        db.row_factory=sqlite3.Row
        output={}
        for app in ("app-a","app-b"):
            head=db.execute(
                "SELECT revision,manifest_hash,current_release,state "
                "FROM apps WHERE app=?",(app,)).fetchone()
            defs=db.execute(
                "SELECT rid,spec,hash FROM definitions WHERE app=? "
                "ORDER BY rid",(app,)).fetchall()
            receipts=db.execute(
                "SELECT actor,cid FROM receipts WHERE app=?",(app,)).fetchall()
            events=db.execute(
                "SELECT actor,event,rid FROM events WHERE app=? ORDER BY eid",
                (app,)).fetchall()
            releases=db.execute(
                "SELECT version,manifest,hash FROM releases WHERE app=?",
                (app,)).fetchall()
            rows=db.execute(
                "SELECT record_id,content,version FROM records WHERE app=?",
                (app,)).fetchall()
            defs_map={r["rid"]:json.loads(r["spec"]) for r in defs}
            output[app]={
                "revision":head["revision"],
                "publishedVersion":head["current_release"],
                "state":head["state"],
                "manifestHash":head["manifest_hash"],
                "manifestMatches":digest(defs_map)==head["manifest_hash"],
                "resources":defs_map,
                "resourceHashesValid":all(
                    digest(json.loads(d["spec"]))==d["hash"] for d in defs),
                "receipts":len(receipts),
                "events":[dict(e) for e in events],
                "releases":len(releases),
                "releaseHashesValid":all(
                    digest(json.loads(r["manifest"]))==r["hash"] for r in releases),
                "records":[{"id":r["record_id"],
                            "value":json.loads(r["content"]),
                            "version":r["version"]} for r in rows]
            }
        return output


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--db",required=True)
    a=p.parse_args()
    print("S1_B7_PHYSICAL|"+json.dumps(read(a.db),ensure_ascii=False))
