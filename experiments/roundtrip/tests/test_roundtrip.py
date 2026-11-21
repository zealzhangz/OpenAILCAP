"""Unittest wrapper around locked independent test scenarios + extra guards."""
import sys
from pathlib import Path
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cases import CASES, rejected
from engine import Store, naive_full_replace_loss, operation_set as setval, operation_delete as delete


class RoundTripTests(unittest.TestCase):
    pass


def make_test(design, case_name, fn):
    def test(self):
        store = Store(design)
        fn(store)
        self.assertGreater(store.serialized_bytes(), 0)
    test.__name__ = f"test_{design.replace('-', '_')}_{case_name.split('-')[0]}"
    return test


for design in ("A-unified-ir", "B-domain-manifest"):
    for case_name, fn in CASES.items():
        setattr(RoundTripTests, f"test_{design.replace('-', '_')}_{case_name.split('-')[0]}",
                make_test(design, case_name, fn))


class DefensiveTests(unittest.TestCase):
    def test_negative_control_is_expected_to_lose_human_style(self):
        self.assertTrue(naive_full_replace_loss())

    def test_untrusted_base_is_rejected(self):
        for design in ("A-unified-ir", "B-domain-manifest"):
            store = Store(design)
            base = store.snapshot()
            base.resources["button-submit"]["data"]["label"] = "forged"  # immutable revision claim
            rejected("UNTRUSTED_BASELINE", lambda: store.apply(actor="ai", change_id="forged", base=base,
                     operations=[setval("button-submit", "data.label", "evil")]))

    def test_delete_referenced_resource_is_rejected(self):
        for design in ("A-unified-ir", "B-domain-manifest"):
            store = Store(design)
            baseline = store.snapshot()
            rejected("BROKEN_REFERENCE", lambda: store.apply(actor="ai", change_id="delete-page", base=baseline,
                     operations=[delete("page-contract-form")]))
            self.assertEqual(store.snapshot(), baseline)

    def test_immutable_id_field_is_rejected(self):
        for design in ("A-unified-ir", "B-domain-manifest"):
            store = Store(design)
            baseline = store.snapshot()
            rejected("IMMUTABLE_FIELD", lambda: store.apply(actor="ai", change_id="id-write", base=baseline,
                     operations=[setval("button-submit", "id", "other")]))
            self.assertEqual(store.snapshot(), baseline)

    def test_manifest_hash_detects_raw_corruption(self):
        store = Store("B-domain-manifest")
        store._raw["domains"]["ui"]["button-submit"]["data"]["label"] = "corrupted"
        rejected("MANIFEST_MISMATCH", lambda: store.snapshot())

    def test_parallel_disjoint_writes_preserved(self):
        for design in ("A-unified-ir", "B-domain-manifest"):
            store = Store(design)
            base = store.snapshot()
            barrier = Barrier(2)
            def worker(index):
                barrier.wait(timeout=5)
                return store.apply(actor=f"human-{index}", change_id=f"parallel-{index[0]}", base=base,
                                   operations=[setval("button-submit", index[0], index[1])])
            with ThreadPoolExecutor(max_workers=2) as pool:
                rows = list(pool.map(worker, [ ("data.label", "并发完成"), ("data.style.background", "gray") ]))
            self.assertEqual(len(rows), 2)
            now = store.resources()["button-submit"]["data"]
            self.assertEqual(now["label"], "并发完成")
            self.assertEqual(now["style"]["background"], "gray")

    def test_parallel_same_field_conflict(self):
        for design in ("A-unified-ir", "B-domain-manifest"):
            store = Store(design)
            base = store.snapshot()
            barrier = Barrier(2)
            def worker(index):
                barrier.wait(timeout=5)
                try:
                    store.apply(actor=f"human-{index}", change_id=f"parallel-conflict-{index}", base=base,
                                operations=[setval("button-submit", "data.label", f"choice-{index}")])
                    return "APPLIED"
                except Exception as exc:
                    return getattr(exc, "code", type(exc).__name__)
            with ThreadPoolExecutor(max_workers=2) as pool:
                outcomes = list(pool.map(worker, range(2)))
            self.assertCountEqual(outcomes, ["APPLIED", "WRITE_CONFLICT"])

    def test_rollback_revision_is_monotonic(self):
        for design in ("A-unified-ir", "B-domain-manifest"):
            store = Store(design)
            baseline = store.snapshot()
            store.apply(actor="human", change_id="rev1", base=baseline,
                        operations=[setval("button-submit", "data.label", "updated")])
            restored = store.rollback(0)
            self.assertEqual(restored.revision, 2)
            self.assertEqual(store.snapshot().fingerprint, baseline.fingerprint)

if __name__ == "__main__":
    unittest.main()
