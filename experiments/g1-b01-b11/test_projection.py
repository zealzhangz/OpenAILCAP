"""B11 unit-only source trigger and native transaction contracts.

Genuine Saltcorn + B2 + Chromium evidence is exclusively experiment.py CI.
"""
from __future__ import annotations

import copy
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from projection_source import (ProjectionRefused,install,pull,digest)
from apply_worker import Refused,apply,inspect


class B11OutboxContracts(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="b11unit-")
        self.db=Path(self.tmp.name)/"source.sqlite"
        self.native=Path(self.tmp.name)/"native.sqlite"
        with sqlite3.connect(self.db) as db:
            db.execute(
                "CREATE TABLE records("
                "app TEXT,model TEXT,record_id TEXT,"
                "version INTEGER,content TEXT)"
            )
        install(self.db)
        with sqlite3.connect(self.native) as db:
            db.execute("CREATE TABLE s1_contracts("
                       "contract_no TEXT,title TEXT,"
                       "amount_minor INTEGER,status TEXT)")
        self.cells={"contract_no":"HT-2026-000001","title":"B2 source",
                    "amount_minor":200000001,"status":"Draft"}
        self.rid="a"*18

    def tearDown(self):
        self.tmp.cleanup()

    def emit(self,version=1,cells=None,record_id=None,app="app-a"):
        with sqlite3.connect(self.db) as db:
            if version==1:
                db.execute("INSERT INTO records VALUES(?,?,?,?,?)",
                           (app,"model.contracts",record_id or self.rid,
                            version,json.dumps(cells or self.cells)))
            else:
                db.execute("UPDATE records SET version=?,content=? "
                           "WHERE app=? AND record_id=?",
                           (version,json.dumps(cells or self.cells),
                            app,record_id or self.rid))

    def events(self,after=0):
        return pull(self.db,"app-a",after,100)["events"]

    def batch(self,events=None,after=0):
        return {"app":"app-a","after":after,
                "events":self.events() if events is None else events}

    def reject(self,fn,code):
        with self.assertRaises(Refused) as e:fn()
        self.assertEqual(e.exception.code,code)

    def test_01_empty_head(self):
        self.assertEqual(pull(self.db,"app-a",0,100)["head"],0)

    def test_02_source_insert_creates_event_in_same_commit(self):
        self.emit()
        self.assertEqual(len(self.events()),1)

    def test_03_source_event_contains_actual_record_id(self):
        self.emit()
        self.assertEqual(self.events()[0]["recordId"],self.rid)

    def test_04_source_update_creates_second_version(self):
        self.emit()
        self.emit(2,{**self.cells,"status":"PendingLevel1"})
        self.assertEqual([x["version"] for x in self.events()],[1,2])

    def test_05_source_event_payload_is_event_time_immutable(self):
        self.emit()
        self.emit(2,{**self.cells,"status":"Approved"})
        self.assertEqual([x["cells"]["status"] for x in self.events()],
                         ["Draft","Approved"])

    def test_06_source_transaction_rollback_has_no_outbox_event(self):
        with sqlite3.connect(self.db,isolation_level=None) as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("INSERT INTO records VALUES (?,?,?,?,?)",
                       ("app-a","model.contracts",self.rid,1,
                        json.dumps(self.cells)))
            db.rollback()
        self.assertEqual(self.events(),[])

    def test_07_app_b_not_projected(self):
        self.emit(app="app-b")
        self.assertEqual(self.events(),[])

    def test_08_unknown_model_not_projected(self):
        with sqlite3.connect(self.db) as db:
            db.execute("INSERT INTO records VALUES(?,?,?,?,?)",
                       ("app-a","model.other",self.rid,1,
                        json.dumps(self.cells)))
        self.assertEqual(self.events(),[])

    def test_09_source_app_scope_rejected(self):
        with self.assertRaises(ProjectionRefused) as e:
            pull(self.db,"app-b",0,100)
        self.assertEqual(e.exception.code,"PROJECTION_APP_FORBIDDEN")

    def test_10_source_cursor_limit_rejected(self):
        with self.assertRaises(ProjectionRefused) as e:
            pull(self.db,"app-a",0,101)
        self.assertEqual(e.exception.code,"PROJECTION_CURSOR_INVALID")

    def test_11_source_event_hash_is_deterministic(self):
        self.emit()
        e=self.events()[0]
        self.assertEqual(e["eventHash"],digest({
            k:v for k,v in e.items() if k!="eventHash"
        }))

    def test_12_source_cursor_is_monotonic(self):
        self.emit()
        self.emit(2,{**self.cells,"status":"Approved"})
        self.assertEqual(self.events(after=1)[0]["seq"],2)

    def test_13_native_apply_one_actual_sql_row(self):
        self.emit()
        result=apply(self.native,self.batch())
        self.assertEqual(result["lastSeq"],1)
        self.assertEqual(inspect(self.native)["rows"][0]["title"],"B2 source")

    def test_14_native_replay_exactly_once(self):
        self.emit()
        apply(self.native,self.batch())
        r=apply(self.native,self.batch())
        self.assertEqual((r["applied"],r["replayed"]),(0,1))
        self.assertEqual(inspect(self.native)["mappings"],1)

    def test_15_native_replay_payload_conflict(self):
        self.emit()
        apply(self.native,self.batch())
        altered=copy.deepcopy(self.events())
        altered[0]["cells"]["title"]="FORGED"
        altered[0]["eventHash"]=digest({
            k:v for k,v in altered[0].items() if k!="eventHash"
        })
        self.reject(lambda:apply(self.native,self.batch(altered)),
                    "REPLAY_HASH_CONFLICT")

    def test_16_native_out_of_order_rejected(self):
        self.emit()
        self.emit(2,{**self.cells,"status":"Approved"})
        self.reject(lambda:apply(self.native,self.batch(self.events()[1:])),
                    "EVENT_SEQUENCE_GAP")

    def test_17_native_fail_before_commit_atomic(self):
        self.emit()
        self.reject(lambda:apply(self.native,self.batch(),True),
                    "INJECTED_BEFORE_COMMIT")
        state=inspect(self.native)
        self.assertEqual((state["lastSeq"],state["rows"],state["receipts"]),
                         (0,[],0))

    def test_18_native_retry_after_failure_succeeds(self):
        self.emit()
        try:apply(self.native,self.batch(),True)
        except Refused:pass
        self.assertEqual(apply(self.native,self.batch())["applied"],1)

    def test_19_native_source_update_changes_status(self):
        self.emit()
        apply(self.native,self.batch())
        self.emit(2,{**self.cells,"status":"Approved"})
        apply(self.native,self.batch(self.events(after=1),after=1))
        self.assertEqual(inspect(self.native)["rows"][0]["status"],"Approved")

    def test_20_native_derived_drift_blocks_update(self):
        self.emit()
        apply(self.native,self.batch())
        with sqlite3.connect(self.native) as db:
            db.execute("UPDATE s1_contracts SET title='HACKED'")
        self.emit(2,{**self.cells,"status":"Approved"})
        self.reject(lambda:apply(self.native,self.batch(
            self.events(after=1),after=1)),"NATIVE_DERIVED_ROW_DRIFT")
        self.assertEqual(inspect(self.native)["lastSeq"],1)

    def test_21_native_bad_hash_rejected(self):
        self.emit()
        e=self.events()
        e[0]["eventHash"]="0"*64
        self.reject(lambda:apply(self.native,self.batch(e)),
                    "EVENT_HASH_INVALID")

    def test_22_native_unknown_record_version_rejected(self):
        self.emit()
        e=self.events()
        e[0]["version"]=2
        e[0]["eventHash"]=digest({
            k:v for k,v in e[0].items() if k!="eventHash"
        })
        self.reject(lambda:apply(self.native,self.batch(e)),
                    "NEW_RECORD_VERSION_NOT_ONE")

    def test_23_native_foreign_app_rejected(self):
        self.emit()
        e=self.events()
        e[0]["app"]="app-b"
        e[0]["eventHash"]=digest({
            k:v for k,v in e[0].items() if k!="eventHash"
        })
        self.reject(lambda:apply(self.native,self.batch(e)),
                    "EVENT_SCOPE_OR_SHAPE_INVALID")

    def test_24_native_unowned_row_conflict(self):
        self.emit()
        with sqlite3.connect(self.native) as db:
            db.execute("INSERT INTO s1_contracts VALUES (?,?,?,?)",
                       ("HT-2026-000001","unowned",100,"Draft"))
        self.reject(lambda:apply(self.native,self.batch()),
                    "NATIVE_UNOWNED_CONTRACT_CONFLICT")

    def test_25_native_cursor_ahead_rejected(self):
        self.emit()
        self.reject(lambda:apply(self.native,self.batch(after=10)),
                    "CURSOR_AHEAD_OF_APPLIED")

    def test_26_native_empty_batch_no_changes(self):
        self.assertEqual(apply(self.native,self.batch([]))["lastSeq"],0)

    def test_27_native_incomplete_cells_rejected(self):
        self.emit()
        e=self.events()
        del e[0]["cells"]["title"]
        e[0]["eventHash"]=digest({
            k:v for k,v in e[0].items() if k!="eventHash"
        })
        self.reject(lambda:apply(self.native,self.batch(e)),
                    "EVENT_CELLS_INVALID")

    def test_28_native_duplicate_contract_numbers_rejected(self):
        self.emit()
        apply(self.native,self.batch())
        self.emit(1,{**self.cells,"title":"second"},record_id="b"*18)
        self.reject(lambda:apply(self.native,self.batch(
            self.events(after=1),after=1)),
                    "NATIVE_UNOWNED_CONTRACT_CONFLICT")


if __name__=="__main__":
    unittest.main()
