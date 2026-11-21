"""B9 independent Saltcorn native SQLite projection oracle.

No projector.py, broker or SchemaStore import. Verify real generated _sc_*,
contract rows, view configuration and field labels after native attacks.
"""
import argparse
import hashlib
import json
import sqlite3


def inspect(db_path):
    with sqlite3.connect("file:"+db_path+"?mode=ro",uri=True) as c:
        c.row_factory=sqlite3.Row
        fields=c.execute(
            "SELECT f.name,f.label FROM _sc_fields f JOIN _sc_tables t "
            "ON f.table_id=t.id WHERE t.name='s1_contracts' ORDER BY f.name"
        ).fetchall()
        view=c.execute(
            "SELECT name,configuration FROM _sc_views "
            "WHERE name='s1_contract_list'"
        ).fetchone()
        if not fields or not view:
            raise ValueError("SALT_CORRELATION_PROJECTION_NOT_MATERIALIZED")
        conf=json.loads(view["configuration"])
        cols=[x.get("field_name") for x in conf.get("columns",[])
              if x.get("type")=="Field"]
        rows=c.execute(
            "SELECT contract_no,title,amount_minor,status "
            "FROM s1_contracts ORDER BY contract_no"
        ).fetchall()
        counts={
            "tables":c.execute(
                "SELECT COUNT(*) FROM _sc_tables").fetchone()[0],
            "views":c.execute(
                "SELECT COUNT(*) FROM _sc_views").fetchone()[0]
        }
        return {
            "fieldLabels":{r["name"]:r["label"] for r in fields},
            "viewColumns":cols,
            "viewConfiguration":conf,
            "businessRows":[dict(r) for r in rows],
            "counts":counts,
            "rawSqlViewHash":hashlib.sha256(
                view["configuration"].encode()
                if isinstance(view["configuration"],str)
                else view["configuration"]
            ).hexdigest()
        }


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--db",required=True)
    args=p.parse_args()
    print("S1_B9_NATIVE_ORACLE|"+json.dumps(
        inspect(args.db),ensure_ascii=False,separators=(",",":")),flush=True)
