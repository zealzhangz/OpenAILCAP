import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

from fixture_snapshot import write_snapshot
from snapshot_web import load_snapshot, render, SnapshotRejected, MAX_BYTES
from patch_native import patched

ROWS = [{"contract_no": "HT-2026-000001", "title": "Contract", "amount_minor": 100000001, "status": "Approved"}]
MANIFEST = "a" * 64


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.path = self.folder / "published.sqlite"
        self.publish()

    def tearDown(self):
        self.temp.cleanup()

    def publish(self, rows=ROWS, head=4, manifest=MANIFEST):
        write_snapshot(self.path, rows, head, manifest)

    def read(self):
        return load_snapshot(self.path, os.getuid(), MANIFEST)

    def sql(self, query):
        with sqlite3.connect(self.path) as db:
            db.execute(query)

    def test_b15_reader_accepts_same_snapshot(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "g1-b01-b15"))
        from publish_snapshot import read_published
        previous = read_published(self.path, os.getuid(), MANIFEST)
        self.assertEqual(previous["rows"], self.read()["rows"])
        self.assertEqual(previous["head"], self.read()["head"])

    def test_corrupt_digest_rejected(self):
        self.sql("UPDATE published_contracts SET title='tampered'")
        with self.assertRaises(SnapshotRejected):
            self.read()

    def test_wrong_release_rejected(self):
        self.publish(manifest="b" * 64)
        with self.assertRaises(SnapshotRejected):
            self.read()

    def test_extra_private_table_rejected(self):
        self.sql("CREATE TABLE users(password TEXT)")
        with self.assertRaises(SnapshotRejected):
            self.read()

    def test_extra_column_rejected(self):
        self.sql("ALTER TABLE published_contracts ADD COLUMN secret TEXT")
        with self.assertRaises(SnapshotRejected):
            self.read()

    def test_duplicate_state_rejected(self):
        self.sql("INSERT INTO published_state SELECT * FROM published_state")
        with self.assertRaises(SnapshotRejected):
            self.read()

    def test_wrong_owner_and_writable_parent_rejected(self):
        with self.assertRaises(SnapshotRejected):
            load_snapshot(self.path, os.getuid() + 1, MANIFEST)
        self.folder.chmod(0o770)
        with self.assertRaises(SnapshotRejected):
            self.read()

    def test_writable_file_rejected(self):
        self.path.chmod(0o660)
        with self.assertRaises(SnapshotRejected):
            self.read()

    def test_symlink_and_hardlink_rejected(self):
        alias = self.folder / "alias.sqlite"
        alias.symlink_to(self.path)
        with self.assertRaises(SnapshotRejected):
            load_snapshot(alias, os.getuid(), MANIFEST)
        os.link(self.path, self.folder / "hard.sqlite")
        with self.assertRaises(SnapshotRejected):
            self.read()

    def test_missing_corrupt_oversize_rejected(self):
        self.path.unlink()
        for data in (None, b"broken", b"x" * (MAX_BYTES + 1)):
            if data is not None:
                self.path.write_bytes(data)
            with self.assertRaises(SnapshotRejected):
                self.read()

    def test_limits_and_types_rejected(self):
        for rows in ([{**ROWS[0], "amount_minor": -1}],
                     [{**ROWS[0], "title": "x" * 4097}],
                     [{**ROWS[0], "contract_no": str(i)} for i in range(257)]):
            self.publish(rows)
            with self.assertRaises(SnapshotRejected):
                self.read()

    def test_html_escaped_and_integer_preserved(self):
        title = '<img src=x onerror="window.__b17_xss=1">'
        self.publish([{**ROWS[0], "title": title}])
        body = render(self.read()).decode()
        self.assertNotIn("<img", body)
        self.assertIn("&lt;img", body)
        self.assertIn("100000001", body)

    def test_open_descriptor_pins_old_generation_across_replace(self):
        original_open = os.open
        swapped = False

        def open_then_replace(path, flags, *args, **kwargs):
            nonlocal swapped
            fd = original_open(path, flags, *args, **kwargs)
            if Path(path) == self.path and not swapped:
                swapped = True
                self.publish([{**ROWS[0], "title": "Next generation"}], head=8)
            return fd

        with patch("snapshot_web.os.open", side_effect=open_then_replace):
            snapshot = self.read()
        self.assertEqual(snapshot, {"head": 4, "rows": ROWS})
        self.assertEqual(self.read()["head"], 8)

    def test_patch_refuses_unknown_upstream(self):
        with self.assertRaisesRegex(ValueError, "UPSTREAM_SOURCE_DRIFT"):
            patched(b"    await initOfflineStoreCfg();")


if __name__ == "__main__":
    unittest.main()
