"""B12 isolated consumer state-machine tests; real OS/SQL/HTTP in experiment.py."""
from __future__ import annotations
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import consumer_daemon as c

CFG={"sourceUrl":"http://127.0.0.1:9001/v4/apps/app-a/projection/pull",
     "token":"t"*36,"nativeUser":"ailcapb12salt",
     "nativeDb":"/tmp/s1-b12-project-fixture/runtime-private/projection-v1.sqlite",
     "sourceDir":"/tmp/stage/g1-b01-b12","intervalMs":180}


class ConsumerContracts(unittest.TestCase):
    def test_01_config_allowlisted(self):c.validate_config(CFG)
    def test_02_reject_native_wrong_user(self):
        with self.assertRaises(c.Failed):
            c.validate_config({**CFG,"nativeUser":"root"})
    def test_03_reject_public_source_url(self):
        with self.assertRaises(c.Failed):
            c.validate_config({**CFG,"sourceUrl":"https://example.invalid/x"})
    def test_04_reject_native_authority_db(self):
        with self.assertRaises(c.Failed):
            c.validate_config({**CFG,"nativeDb":"/tmp/authority.sqlite"})
    def test_05_reject_unbounded_poll_interval(self):
        with self.assertRaises(c.Failed):
            c.validate_config({**CFG,"intervalMs":1})
    def test_06_reject_config_unknown_key(self):
        with self.assertRaises(c.Failed):
            c.validate_config({**CFG,"adminToken":"abc"})
    def test_07_reject_short_token(self):
        with self.assertRaises(c.Failed):
            c.validate_config({**CFG,"token":"a"})
    def test_08_reject_wrong_worker_dir(self):
        with self.assertRaises(c.Failed):
            c.validate_config({**CFG,"sourceDir":"/tmp/unsafe"})
    def test_09_source_unavailable_is_fail_closed(self):
        with patch.object(c,"urlopen",side_effect=OSError("down")):
            with self.assertRaises(c.Failed) as e:c.pull(CFG,0)
        self.assertEqual(e.exception.code,"SOURCE_UNAVAILABLE")
    def test_10_source_wrong_app_refused(self):
        class Response:
            status=200
            def __enter__(self):return self
            def __exit__(self,*_):pass
            def read(self,_):return json.dumps(
                {"app":"app-b","after":0,"head":0,"events":[]}).encode()
        with patch.object(c,"urlopen",return_value=Response()):
            with self.assertRaises(c.Failed) as e:c.pull(CFG,0)
        self.assertEqual(e.exception.code,"SOURCE_RESPONSE_INVALID")
    def test_11_source_missing_events_refused(self):
        class Response:
            status=200
            def __enter__(self):return self
            def __exit__(self,*_):pass
            def read(self,_):return json.dumps(
                {"app":"app-a","after":0,"head":1,"events":[]}).encode()
        with patch.object(c,"urlopen",return_value=Response()):
            with self.assertRaises(c.Failed) as e:c.pull(CFG,0)
        self.assertEqual(e.exception.code,"SOURCE_MISSING_EVENTS")
    def test_12_source_head_behind_cursor_refused(self):
        class Response:
            status=200
            def __enter__(self):return self
            def __exit__(self,*_):pass
            def read(self,_):return json.dumps(
                {"app":"app-a","after":8,"head":7,"events":[]}).encode()
        with patch.object(c,"urlopen",return_value=Response()):
            with self.assertRaises(c.Failed) as e:c.pull(CFG,8)
        self.assertEqual(e.exception.code,"SOURCE_RESPONSE_INVALID")
    def test_13_step_audits_before_pull(self):
        calls=[]
        def native(_,script,**kw):
            calls.append(script)
            return {"clean":True} if script=="audit_native.py" else {
                "lastSeq":0}
        with patch.object(c,"run_native",side_effect=native),patch.object(
            c,"pull",return_value={"app":"app-a","after":0,
                                   "head":0,"events":[]}):
            self.assertEqual(c.step(CFG)["state"],"CAUGHT_UP")
        self.assertEqual(calls,["audit_native.py","native_checkpoint.py"])
    def test_14_step_drift_rejects_before_pull(self):
        with patch.object(c,"run_native",return_value={"clean":False}),patch.object(
            c,"pull") as fetch:
            with self.assertRaises(c.Failed) as e:c.step(CFG)
            fetch.assert_not_called()
        self.assertEqual(e.exception.code,"DERIVED_DRIFT")
    def test_15_step_uses_native_cursor_not_external_offset(self):
        calls=[]
        def native(_,script,**kw):
            calls.append(script)
            return {"clean":True} if script=="audit_native.py" else {
                "lastSeq":13}
        with patch.object(c,"run_native",side_effect=native),patch.object(
            c,"pull",return_value={"app":"app-a","after":13,
                                   "head":13,"events":[]}) as fetch:
            result=c.step(CFG)
        fetch.assert_called_once_with(CFG,13)
        self.assertEqual(result["cursor"],13)
    def test_16_step_applies_bounded_event_batch(self):
        def native(_,script,**kw):
            return {"clean":True} if script=="audit_native.py" else (
                {"lastSeq":4} if script=="native_checkpoint.py" else
                {"lastSeq":5,"applied":1})
        with patch.object(c,"run_native",side_effect=native),patch.object(
            c,"pull",return_value={"app":"app-a","after":4,"head":5,
                                   "events":[{"seq":5}]}):
            result=c.step(CFG)
        self.assertEqual((result["cursor"],result["applied"]),(5,1))
    def test_17_step_cursor_out_of_head_refused(self):
        def native(_,script,**kw):
            return {"clean":True} if script=="audit_native.py" else (
                {"lastSeq":4} if script=="native_checkpoint.py" else
                {"lastSeq":7,"applied":3})
        with patch.object(c,"run_native",side_effect=native),patch.object(
            c,"pull",return_value={"app":"app-a","after":4,"head":5,
                                   "events":[{"seq":5}]}):
            with self.assertRaises(c.Failed) as e:c.step(CFG)
        self.assertEqual(e.exception.code,"CONSUMER_CURSOR_INVALID")
    def test_18_status_contains_no_secret_or_native_path(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"status.json"
            c.write_status(path,{"state":"CAUGHT_UP","cursor":8,
                                 "head":8,"lag":0,"applied":0})
            raw=path.read_text()
            self.assertNotIn(CFG["token"],raw)
            self.assertNotIn(CFG["nativeDb"],raw)
            self.assertEqual(path.stat().st_mode&0o777,0o600)
    def test_19_status_atomic_replace(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"status.json"
            c.write_status(path,{"state":"STARTING"})
            c.write_status(path,{"state":"CAUGHT_UP","cursor":5})
            self.assertEqual(json.loads(path.read_text())["cursor"],5)
            self.assertFalse(path.with_suffix(".tmp").exists())
    def test_20_native_failure_does_not_advance_cursor(self):
        with patch.object(c,"run_native",side_effect=c.Failed(
            "NATIVE_WORKER_UNAVAILABLE")):
            with self.assertRaises(c.Failed):
                c.step(CFG)
    def test_21_status_does_not_expose_error(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"status.json"
            c.write_status(path,{"state":"SOURCE_UNAVAILABLE",
                                 "error":"secret-text","failures":2})
            self.assertNotIn("secret-text",path.read_text())
            self.assertEqual(json.loads(path.read_text())["failures"],2)
    def test_22_invalid_interval_boolean_refused(self):
        with self.assertRaises(c.Failed):
            c.validate_config({**CFG,"intervalMs":True})


if __name__=="__main__":
    unittest.main()
