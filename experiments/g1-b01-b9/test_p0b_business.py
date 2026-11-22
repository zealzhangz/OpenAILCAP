"""Fast B2 physical records vs B11 same-SQLite-trigger outbox regression.

Run together with the 83 real B9/Chromium/Official Saltcorn checks. This
does not independently grant G1 W17/W18/TC16 FULL PASS.
"""
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"g1-b01-b2"))
from schema_core import SchemaStore,canon
from p0b_authority_business import read_business,AuthorityDataRejected,install

RECORD1={"contract_no":"HT-2026-000001",
         "title":"S1 Platform Contract","amount_minor":100000001,
         "status":"Draft"}
RECORD2={"contract_no":"HT-2026-000002",
         "title":"S1 Authority Next Contract","amount_minor":200000002,
         "status":"Draft"}


class B11SameDbAuthority(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path=Path(self.folder.name)/"authority.sqlite"
        store=SchemaStore(self.path)
        store.init()
        store.seed_app_for_test("app-a")
        store.seed_app_for_test("app-b")
        install(self.path)

    def write(self,rid,version,content,app="app-a"):
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO records(app,model,record_id,version,content) "
                       "VALUES(?,?,?,?,?)",
                       (app,"model.contracts",rid,version,canon(content)))

    def change(self,rid,version,content):
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE records SET version=?,content=? "
                       "WHERE app='app-a' AND record_id=?",
                       (version,canon(content),rid))

    @staticmethod
    def assert_rejected(code,call):
        try:call()
        except AuthorityDataRejected as e:
            if e.code!=code:
                raise AssertionError((code,e.code))
        else:raise AssertionError("Expected "+code)

    def test_empty_source_is_not_fabricated(self):
        snap=read_business(self.path)
        self.assertEqual(snap["head"],0)
        self.assertEqual(snap["rows"],[])
        self.assertEqual(snap["events"],[])

    def test_transactionally_coupled_B2_record_insert(self):
        self.write("record-1",1,RECORD1)
        snap=read_business(self.path)
        self.assertEqual(snap["head"],1)
        self.assertEqual(snap["rows"],[RECORD1])
        self.assertEqual(snap["events"][0]["recordId"],"record-1")
        self.assertEqual(snap["events"][0]["cells"],RECORD1)

    def test_real_B2_update_appends_versioned_event(self):
        self.write("record-1",1,RECORD1)
        changed={**RECORD1,"status":"Submitted"}
        self.change("record-1",2,changed)
        snap=read_business(self.path)
        self.assertEqual([event["version"] for event in snap["events"]],[1,2])
        self.assertEqual(snap["rows"],[changed])
        self.assertEqual(snap["head"],2)

    def test_two_business_rows_stable_canonical_order(self):
        self.write("record-2",1,RECORD2)
        self.write("record-1",1,RECORD1)
        snap=read_business(self.path)
        self.assertEqual(snap["rows"],[RECORD1,RECORD2])
        self.assertEqual(snap["head"],2)

    def test_app_b_is_never_laundered_into_app_a(self):
        self.write("record-1",1,RECORD1)
        self.write("record-b",1,RECORD2,app="app-b")
        snap=read_business(self.path)
        self.assertEqual(snap["head"],1)
        self.assertEqual(snap["rows"],[RECORD1])

    def test_gap_in_B11_event_seq_is_denied(self):
        self.write("record-1",1,RECORD1)
        self.write("record-2",1,RECORD2)
        with sqlite3.connect(self.path) as db:
            db.execute("DELETE FROM b11_outbox WHERE seq=1")
        self.assert_rejected("AUTHORITY_OUTBOX_SEQ_OR_SCOPE_INVALID",
                             lambda:read_business(self.path))

    def test_out_of_band_record_content_is_not_authorized(self):
        self.write("record-1",1,RECORD1)
        with sqlite3.connect(self.path) as db:
            db.execute("DROP TRIGGER b11_record_update")
            db.execute("UPDATE records SET content=? WHERE record_id=?",
                       (canon({**RECORD1,"title":"BYPASS"}),"record-1"))
        self.assert_rejected("AUTHORITY_B2_OUTBOX_ROWS_DIVERGED",
                             lambda:read_business(self.path))

    def test_noncontiguous_B2_record_version_is_denied(self):
        self.write("record-1",1,RECORD1)
        self.change("record-1",3,RECORD1)
        self.assert_rejected("AUTHORITY_OUTBOX_VERSION_GAP",
                             lambda:read_business(self.path))

    def test_deleted_B2_record_with_outbox_left_is_denied(self):
        self.write("record-1",1,RECORD1)
        with sqlite3.connect(self.path) as db:
            db.execute("DELETE FROM records WHERE record_id='record-1'")
        self.assert_rejected("AUTHORITY_B2_OUTBOX_ROWS_DIVERGED",
                             lambda:read_business(self.path))

    def test_duplicate_contract_number_denied(self):
        self.write("record-1",1,RECORD1)
        self.write("record-2",1,{**RECORD2,"contract_no":"HT-2026-000001"})
        self.assert_rejected("AUTHORITY_DUPLICATE_CONTRACT_NO",
                             lambda:read_business(self.path))

if __name__=="__main__":
    unittest.main()
