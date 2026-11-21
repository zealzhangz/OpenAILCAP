"""Independent read-only physical SQLite oracle, run under Saltcorn owner UID.

Does not import Saltcorn Node models nor the Python research gateway. Reads
actual _sc_fields, rows, and guard receipt/audit ledger at each boundary.
"""
import argparse,json,hashlib,sqlite3


def read(path):
    with sqlite3.connect("file:"+path+"?mode=ro",uri=True) as db:
        labelrow=db.execute(
            "SELECT f.label, f.id FROM _sc_fields f "
            "JOIN _sc_tables t ON f.table_id=t.id "
            "WHERE t.name='s1_contracts' AND f.name='title'").fetchone()
        if not labelrow:raise RuntimeError("REAL_SALTCORN_FIELD_MISSING")
        count=db.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' "
            "AND name='_openailcap_s1_http_guard'").fetchone()[0]
        out={"fieldLabel":labelrow[0],"fieldId":labelrow[1],
             "rawFieldDigest":hashlib.sha256(labelrow[0].encode()).hexdigest(),
             "hasGuard":bool(count)}
        if count:
            ledger=db.execute(
                "SELECT revision,fingerprint FROM _openailcap_s1_http_guard "
                "WHERE app_id='s1-contract' AND resource_id='title'").fetchone()
            out["revision"]=ledger[0] if ledger else None
            out["fingerprint"]=ledger[1] if ledger else None
            out["changes"]=db.execute(
                "SELECT COUNT(*) FROM _openailcap_s1_http_changes").fetchone()[0]
            out["audit"]=db.execute(
                "SELECT actor,resource_id,outcome FROM _openailcap_s1_http_audit "
                "ORDER BY id").fetchall()
        else:
            out.update({"revision":None,"fingerprint":None,
                        "changes":0,"audit":[]})
        out["nativeRowCount"]=db.execute(
            "SELECT COUNT(*) FROM s1_contracts").fetchone()[0]
        return out


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--db",required=True)
    a=p.parse_args()
    print("S1_B8_PHYSICAL|"+json.dumps(
        read(a.db),ensure_ascii=False,separators=(",",":")))
