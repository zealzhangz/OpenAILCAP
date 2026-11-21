"""B13 narrow Unix IPC and read-time guard unit contracts (no mock E2E)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import native_ipc as ipc
import guard_router as guard


class B13Unit(unittest.TestCase):
    def setUp(self):
        self.broker=ipc.Broker("/tmp/nonexistent",1101,1102)
    def test_01_wrong_consumer_uid_denied(self):
        r=self.broker.execute("consumer",1103,{"op":"audit"})
        self.assertEqual(r["error"],"PEER_UID_FORBIDDEN")
    def test_02_wrong_guard_uid_denied(self):
        r=self.broker.execute("guard",1101,{"op":"snapshot"})
        self.assertEqual(r["error"],"PEER_UID_FORBIDDEN")
    def test_03_guard_cannot_apply(self):
        r=self.broker.execute("guard",1102,{"op":"apply","batch":{}})
        self.assertEqual(r["error"],"GUARD_READ_ONLY")
    def test_04_guard_cannot_checkpoint(self):
        r=self.broker.execute("guard",1102,{"op":"checkpoint"})
        self.assertEqual(r["error"],"GUARD_READ_ONLY")
    def test_05_consumer_cannot_guard_snapshot(self):
        r=self.broker.execute("consumer",1101,{"op":"snapshot"})
        self.assertEqual(r["error"],"CONSUMER_OP_FORBIDDEN")
    def test_06_consumer_unknown_operation_denied(self):
        r=self.broker.execute("consumer",1101,{"op":"exec"})
        self.assertEqual(r["error"],"CONSUMER_OP_FORBIDDEN")
    def test_07_extra_fields_denied(self):
        r=self.broker.execute("consumer",1101,{"op":"audit","shell":"id"})
        self.assertEqual(r["error"],"IPC_ARGUMENTS_INVALID")
    def test_08_apply_missing_batch_denied(self):
        r=self.broker.execute("consumer",1101,{"op":"apply"})
        self.assertEqual(r["error"],"IPC_ARGUMENTS_INVALID")
    def test_09_audit_with_batch_denied(self):
        r=self.broker.execute("consumer",1101,{"op":"audit","batch":{}})
        self.assertEqual(r["error"],"IPC_ARGUMENTS_INVALID")
    def test_10_invalid_type_denied(self):
        r=self.broker.execute("consumer",1101,["audit"])
        self.assertEqual(r["error"],"IPC_ARGUMENTS_INVALID")
    def test_11_guard_clean_snapshot_only(self):
        snap={"clean":True,"cursor":20,"rows":[],"receiptCount":20,
              "mappingCount":0}
        with patch.object(ipc,"native_snapshot",return_value=snap):
            r=self.broker.execute("guard",1102,{"op":"snapshot"})
        self.assertTrue(r["ok"])
        self.assertEqual(r["result"],snap)
    def test_12_consumer_audit_hides_rows(self):
        snap={"clean":True,"cursor":20,"rows":[{"title":"secret"}],
              "receiptCount":20,"mappingCount":1}
        with patch.object(ipc,"native_snapshot",return_value=snap):
            r=self.broker.execute("consumer",1101,{"op":"audit"})
        self.assertTrue(r["ok"])
        self.assertNotIn("rows",r["result"])
    def test_13_checkpoint_is_native_cursor(self):
        with patch.object(ipc,"native_snapshot",return_value={"cursor":9}):
            r=self.broker.execute("consumer",1101,{"op":"checkpoint"})
        self.assertEqual(r["result"]["lastSeq"],9)
    def test_14_native_apply_rejects_invalid_batch(self):
        r=self.broker.execute("consumer",1101,{"op":"apply","batch":{}})
        self.assertFalse(r["ok"])
    def test_15_native_snapshot_missing_db_denied(self):
        with self.assertRaises(Exception):
            ipc.native_snapshot("/tmp/nonexistent-B13.sqlite")
    def test_16_source_hash_canonical_stable(self):
        value={"b":1,"a":"合同"}
        self.assertEqual(guard.canon(value),'{"a":"合同","b":1}')
    def test_17_guard_native_missing_socket_failclosed(self):
        with self.assertRaises(guard.Refused) as e:
            guard.native_snapshot("/tmp/B13-missing.sock")
        self.assertEqual(e.exception.status,503)
    def test_18_guard_release_mismatch_failclosed(self):
        cfg={"kernelPort":9000,"kernelReadToken":"t"*36,
             "version":1,"manifestHash":"a"*64}
        with patch.object(guard,"query_current_release",
                          return_value={"version":2,"hash":"b"*64}):
            with self.assertRaises(guard.Refused) as e:
                guard.verify(cfg)
        self.assertEqual(e.exception.code,"GUARD_RELEASE_POINTER_MISMATCH")
    def test_19_guard_native_cursor_behind_source_denied(self):
        cfg={"kernelPort":9000,"kernelReadToken":"t"*36,
             "version":1,"manifestHash":"a"*64,"guardSocket":"/tmp/sock"}
        with patch.object(guard,"query_current_release",
                          return_value={"version":1,"hash":"a"*64}),patch.object(
            guard,"source_events",return_value=(2,{"A":{"title":"A"}})),patch.object(
            guard,"native_snapshot",return_value={"clean":True,"cursor":1,
            "rows":[],"receiptCount":1,"mappingCount":0}):
            with self.assertRaises(guard.Refused) as e:guard.verify(cfg)
        self.assertEqual(e.exception.code,"GUARD_NATIVE_BEHIND_OR_INCONSISTENT")
    def test_20_guard_source_native_cell_mismatch_denied(self):
        cfg={"kernelPort":9000,"kernelReadToken":"t"*36,
             "version":1,"manifestHash":"a"*64,"guardSocket":"/tmp/sock"}
        with patch.object(guard,"query_current_release",
                          return_value={"version":1,"hash":"a"*64}),patch.object(
            guard,"source_events",return_value=(1,{"A":{"contract_no":"A",
            "title":"trusted","amount_minor":1,"status":"Approved"}})),patch.object(
            guard,"native_snapshot",return_value={"clean":True,"cursor":1,
            "rows":[{"contract_no":"A","title":"tampered","amount_minor":1,
            "status":"Approved"}],"receiptCount":1,"mappingCount":1}):
            with self.assertRaises(guard.Refused) as e:guard.verify(cfg)
        self.assertEqual(e.exception.code,"GUARD_AUTHORITY_NATIVE_MISMATCH")
    def test_21_guard_duplicate_rows_denied(self):
        cfg={"kernelPort":9000,"kernelReadToken":"t"*36,
             "version":1,"manifestHash":"a"*64,"guardSocket":"/tmp/sock"}
        row={"contract_no":"A","title":"trusted",
             "amount_minor":1,"status":"Approved"}
        with patch.object(guard,"query_current_release",
                          return_value={"version":1,"hash":"a"*64}),patch.object(
            guard,"source_events",return_value=(2,{"A":row,"B":{}})),patch.object(
            guard,"native_snapshot",return_value={"clean":True,"cursor":2,
            "rows":[row,row],"receiptCount":2,"mappingCount":2}):
            with self.assertRaises(guard.Refused) as e:guard.verify(cfg)
        self.assertEqual(e.exception.code,"GUARD_NATIVE_ROW_INVALID")
    def test_22_guard_valid_exact_source_native_rows(self):
        cfg={"kernelPort":9000,"kernelReadToken":"t"*36,
             "version":1,"manifestHash":"a"*64,"guardSocket":"/tmp/sock"}
        row={"contract_no":"A","title":"trusted",
             "amount_minor":1,"status":"Approved"}
        with patch.object(guard,"query_current_release",
                          return_value={"version":1,"hash":"a"*64}),patch.object(
            guard,"source_events",return_value=(1,{"A":row})),patch.object(
            guard,"native_snapshot",return_value={"clean":True,"cursor":1,
            "rows":[row],"receiptCount":1,"mappingCount":1}):
            self.assertEqual(guard.verify(cfg),{"A":row})


if __name__=="__main__":
    unittest.main()
