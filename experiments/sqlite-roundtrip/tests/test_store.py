"""Independent acceptance assertions; executed against SQLite with new connections."""
from __future__ import annotations

import json
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from store import Store, Rejected, set_field, create, delete


class PersistentStoreTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix="openailcap-s1-sqlite-")
        self.db = Path(self.folder.name) / "apps.sqlite"
        self.store = Store(self.db)
        self.store.bootstrap_app("A", "owner")
        self.store.bootstrap_app("B", "owner")
        self.store.grant_for_fixture("A", "human", "write")
        self.store.grant_for_fixture("A", "agent", "write")
        self.store.grant_for_fixture("B", "other-agent", "write")
        self.store.grant_for_fixture("A", "auditor", "read")

    def tearDown(self):
        self.folder.cleanup()

    def do(self, actor, cid, base, operations, app="A", **kwargs):
        return self.store.apply(app, actor=actor, change_id=cid, base=base,
                                operations=operations, **kwargs)

    def denied(self, expected, operation):
        with self.assertRaises(Rejected) as caught:
            operation()
        self.assertEqual(caught.exception.code, expected)

    def test_01_manual_ai_nonoverlap_same_resource(self):
        base = self.store.snapshot("A")
        self.do("human", "human1", base, [set_field("submit-btn", "data.style.background", "gray")])
        receipt = self.do("agent", "ai1", base, [set_field("submit-btn", "data.label", "送审")])
        self.assertTrue(receipt["merged"])
        data = self.store.snapshot("A").resources["submit-btn"]["data"]
        self.assertEqual((data["style"]["background"], data["label"]), ("gray", "送审"))

    def test_02_manual_ai_overlap_refused(self):
        base = self.store.snapshot("A")
        self.do("human", "human2", base, [set_field("submit-btn", "data.label", "保存")])
        self.denied("WRITE_CONFLICT", lambda: self.do("agent", "ai2", base,
                    [set_field("submit-btn", "data.label", "送审")]))
        self.assertEqual(self.store.snapshot("A").resources["submit-btn"]["data"]["label"], "保存")

    def test_03_persists_after_reopening_database(self):
        base = self.store.snapshot("A")
        self.do("human", "reopen", base, [set_field("approval", "data.threshold", 2000000)])
        from_disk = Store(self.db).snapshot("A", actor="human")
        self.assertEqual(from_disk.revision, 1)
        self.assertEqual(from_disk.resources["approval"]["data"]["threshold"], 2000000)

    def test_04_same_revision_content_drift_is_refused(self):
        base = self.store.snapshot("A")
        with closing(sqlite3.connect(self.db)) as conn:
            row = conn.execute("SELECT body FROM resources WHERE app_id='A' AND resource_id='submit-btn'").fetchone()
            data = json.loads(row[0]); data["data"]["label"] = "hidden edit"
            conn.execute("UPDATE resources SET body=? WHERE app_id='A' AND resource_id='submit-btn'", (json.dumps(data),))
            conn.commit()
        self.denied("SNAPSHOT_DRIFT", lambda: self.store.snapshot("A"))
        self.denied("SNAPSHOT_DRIFT", lambda: self.do("agent", "drift", base,
                    [set_field("approval", "data.threshold", 9)]))

    def test_05_bad_ref_delete_is_atomic(self):
        before = self.store.snapshot("A")
        self.denied("BROKEN_REF", lambda: self.do("agent", "dangling", before, [delete("submit-btn")]))
        self.assertEqual(self.store.snapshot("A"), before)

    def test_06_failure_injection_undoes_sql_writes(self):
        before = self.store.snapshot("A")
        self.denied("INJECTED_FAILURE", lambda: self.do("agent", "inject", before,
                    [set_field("approval", "data.threshold", 7)], fail_after_write=True))
        self.assertEqual(Store(self.db).snapshot("A"), before)

    def test_07_rollback_creates_new_monotonic_revision(self):
        before = self.store.snapshot("A")
        self.do("agent", "change1", before, [set_field("approval", "data.threshold", 5)])
        receipt = self.store.rollback("A", actor="human", to_revision=0)
        self.assertEqual(receipt["revision"], 2)
        self.assertEqual(Store(self.db).snapshot("A").fingerprint, before.fingerprint)

    def test_08_idempotent_retry_after_reopen(self):
        before = self.store.snapshot("A")
        ops = [set_field("submit-btn", "data.label", "确定")]
        one = self.do("agent", "same-key", before, ops)
        second = Store(self.db).apply("A", actor="agent", change_id="same-key", base=before, operations=ops)
        self.assertEqual(one, second)
        self.assertEqual(Store(self.db).snapshot("A").revision, 1)
        self.denied("IDEMPOTENCY_REUSE", lambda: self.do("agent", "same-key", before,
                    [set_field("submit-btn", "data.label", "malicious")]))

    def test_09_untrusted_base_rejected(self):
        base = self.store.snapshot("A")
        base.resources["submit-btn"]["data"]["label"] = "fabricated"
        self.denied("UNTRUSTED_BASE", lambda: self.do("agent", "forged", base,
                    [set_field("submit-btn", "data.label", "xx")]))

    def test_10_readonly_cannot_write(self):
        base = self.store.snapshot("A", actor="auditor")
        self.denied("FORBIDDEN", lambda: self.do("auditor", "readonly", base,
                    [set_field("submit-btn", "data.label", "xx")]))

    def test_11_cross_app_read_refused(self):
        self.denied("FORBIDDEN", lambda: self.store.snapshot("B", actor="agent"))
        self.denied("FORBIDDEN", lambda: self.store.snapshot("A", actor="other-agent"))

    def test_12_cross_app_write_refused(self):
        base = self.store.snapshot("A", actor="agent")
        self.denied("FORBIDDEN", lambda: self.do("agent", "to-B", base,
                    [set_field("submit-btn", "data.label", "xx")], app="B"))
        self.assertEqual(self.store.snapshot("B").revision, 0)

    def test_13_cross_app_base_rejected_even_owner(self):
        base_a = self.store.snapshot("A")
        self.denied("CROSS_APP_BASE", lambda: self.do("owner", "base-other", base_a,
                    [set_field("submit-btn", "data.label", "xx")], app="B"))

    def test_14_both_apps_same_resource_id_independent(self):
        a = self.store.snapshot("A")
        self.do("agent", "a-only", a, [set_field("submit-btn", "data.label", "A")])
        self.assertEqual(self.store.snapshot("A").resources["submit-btn"]["data"]["label"], "A")
        self.assertEqual(self.store.snapshot("B").resources["submit-btn"]["data"]["label"], "提交")

    def test_15_parallel_disjoint_updates_separate_connections(self):
        base = self.store.snapshot("A")
        barrier = threading.Barrier(2)
        def perform(i):
            barrier.wait(timeout=5)
            target, value = [("data.label", "已提交"), ("data.style.background", "gray")][i]
            return Store(self.db).apply("A", actor="agent", change_id=f"parallel-{i}", base=base,
                                        operations=[set_field("submit-btn", target, value)])
        with ThreadPoolExecutor(max_workers=2) as pool:
            rows = list(pool.map(perform, (0, 1)))
        self.assertEqual(len(rows), 2)
        state = self.store.snapshot("A").resources["submit-btn"]["data"]
        self.assertEqual((state["label"], state["style"]["background"]), ("已提交", "gray"))
        self.assertEqual(self.store.snapshot("A").revision, 2)

    def test_16_parallel_overlap_one_rejected(self):
        base = self.store.snapshot("A")
        barrier = threading.Barrier(2)
        def perform(i):
            barrier.wait(timeout=5)
            try:
                Store(self.db).apply("A", actor="agent", change_id=f"overlap-{i}", base=base,
                                     operations=[set_field("submit-btn", "data.label", str(i))])
                return "APPLIED"
            except Rejected as e:
                return e.code
        with ThreadPoolExecutor(max_workers=2) as pool:
            result = list(pool.map(perform, (0, 1)))
        self.assertCountEqual(result, ["APPLIED", "WRITE_CONFLICT"])

    def test_17_unknown_plugin_extension_is_preserved(self):
        base = self.store.snapshot("A")
        self.do("agent", "label-only", base, [set_field("submit-btn", "data.label", "已提交")])
        self.assertEqual(self.store.snapshot("A").resources["plugin"]["data"]["config"]["unknown_field"], {"v": 17})

    def test_18_manual_code_survives_ai_edit(self):
        base = self.store.snapshot("A")
        self.do("human", "manual-code", base, [set_field("custom-code", "data.source", "return prefix + str(seq)")])
        self.do("agent", "ai-page", base, [set_field("contract-page", "data.title", "合同登记")])
        self.assertEqual(self.store.snapshot("A").resources["custom-code"]["data"]["source"], "return prefix + str(seq)")

    def test_19_unknown_ref_create_rejected(self):
        base = self.store.snapshot("A")
        self.denied("BROKEN_REF", lambda: self.do("agent", "new-bad", base,
                    [create("new", {"domain": "ui", "data": {}, "refs": ["unknown"]})]))

    def test_20_combined_delete_and_rewire_allowed(self):
        base = self.store.snapshot("A")
        self.do("agent", "rewire", base, [set_field("submit-event", "refs", ["approval"]), delete("submit-btn")])
        self.assertNotIn("submit-btn", self.store.snapshot("A").resources)

    def test_21_crashed_process_uncommitted_sql_rolls_back(self):
        before = self.store.snapshot("A")
        script = '''import os,sqlite3,sys
c=sqlite3.connect(sys.argv[1],isolation_level=None)
c.execute("BEGIN IMMEDIATE")
c.execute("UPDATE resources SET body=? WHERE app_id='A' AND resource_id='submit-btn'", ('{}',))
os._exit(71)
'''
        completed = subprocess.run([sys.executable, "-c", script, str(self.db)], capture_output=True, timeout=8)
        self.assertEqual(completed.returncode, 71)
        self.assertEqual(Store(self.db).snapshot("A"), before)

    def test_22_manual_updates_work_without_llm(self):
        base = self.store.snapshot("A")
        self.do("human", "manual", base, [set_field("approval", "data.threshold", 500000)])
        self.assertEqual(self.store.snapshot("A", actor="human").resources["approval"]["data"]["threshold"], 500000)

if __name__ == "__main__":
    unittest.main()

# Keep late-added regression in the discoverable class (before any runner's main()).
def _test_23_idempotent_replay_must_fail_on_db_drift(self):
    base = self.store.snapshot("A")
    ops = [set_field("submit-btn", "data.label", "hello")]
    self.do("agent", "replay-on-corrupt", base, ops)
    with closing(sqlite3.connect(self.db)) as conn:
        conn.execute("UPDATE resources SET body=? WHERE app_id='A' AND resource_id='submit-btn'", ('{}',))
        conn.commit()
    self.denied("SNAPSHOT_DRIFT", lambda: self.do("agent", "replay-on-corrupt", base, ops))
PersistentStoreTests.test_23_idempotent_replay_must_fail_on_db_drift = _test_23_idempotent_replay_must_fail_on_db_drift
