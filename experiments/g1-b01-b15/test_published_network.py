"""B15 published-only business snapshot and IPv4/IPv6 firewall contracts."""
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from publish_snapshot import (publish,read_published,rows_digest,Refused,
                              SNAP_TABLES)
from network_policy import rules,apply

EXPECTED={"HT-2026-000001":{"contract_no":"HT-2026-000001",
          "title":"B2 source only","amount_minor":42,"status":"Approved"}}


class B15Unit(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="s1-b15-project-")
        self.folder=Path(self.temp.name)/"published-private"
        self.folder.mkdir()
        self.output=self.folder/"published.sqlite"
        self.config={"output":str(self.output),
                     "nativeDb":str(Path(self.temp.name)/
                         "runtime-private"/"projection-v1.sqlite"),
                     "manifestHash":"a"*64}
    def tearDown(self):self.temp.cleanup()
    def write(self,expected=None):
        x=EXPECTED if expected is None else expected
        with patch("publish_snapshot.compare_source_native",
                   return_value=(4,x)):
            return publish(self.config)
    def read(self):
        return read_published(self.output,os.getuid(),"a"*64)
    def test_01_public_rows_digest_deterministic(self):
        self.assertEqual(rows_digest(list(EXPECTED.values())),
                         rows_digest(list(reversed(list(EXPECTED.values())))))
    def test_02_snapshot_single_file(self):
        self.write()
        self.assertTrue(self.output.exists())
    def test_03_snapshot_only_public_business_schema(self):
        self.write()
        with sqlite3.connect(self.output) as db:
            tables={x[0] for x in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertEqual(tables,SNAP_TABLES)
        self.assertNotIn("users",tables)
    def test_04_snapshot_cursor(self):
        self.write()
        self.assertEqual(self.read()["head"],4)
    def test_05_snapshot_business_row(self):
        self.write()
        self.assertEqual(self.read()["rows"],list(EXPECTED.values()))
    def test_06_snapshot_digest(self):
        self.write()
        self.assertEqual(self.read()["digest"],
                         rows_digest(list(EXPECTED.values())))
    def test_07_snapshot_file_0640(self):
        self.write()
        self.assertEqual(self.output.stat().st_mode&0o777,0o640)
    def test_08_wrong_manifest_fails(self):
        self.write()
        with self.assertRaises(Refused):
            read_published(self.output,os.getuid(),"b"*64)
    def test_09_wrong_owner_fails(self):
        self.write()
        with self.assertRaises(Refused):
            read_published(self.output,os.getuid()+1,"a"*64)
    def test_10_group_writable_fails(self):
        self.write()
        self.output.chmod(0o660)
        with self.assertRaises(Refused):self.read()
    def test_11_missing_snapshot_fails_closed(self):
        with self.assertRaises(Refused):self.read()
    def test_12_corrupted_row_fails_digest(self):
        self.write()
        with sqlite3.connect(self.output) as db:
            db.execute("UPDATE published_contracts SET title='tampered'")
        with self.assertRaises(Refused):self.read()
    def test_13_atomic_replace_changes_rows(self):
        self.write()
        changed={**EXPECTED,"HT-2026-000002":{
            "contract_no":"HT-2026-000002","title":"next",
            "amount_minor":43,"status":"Draft"}}
        self.write(changed)
        self.assertEqual(len(self.read()["rows"]),2)
    def test_14_publish_rejects_unverified_source(self):
        with patch("publish_snapshot.compare_source_native",
                   side_effect=Refused(503,"PUBLISH_SOURCE_NATIVE_MISMATCH")):
            with self.assertRaises(Refused):publish(self.config)
        self.assertFalse(self.output.exists())
    def test_15_concurrent_change_preserves_previous_snapshot(self):
        self.write()
        before=self.output.read_bytes()
        with patch("publish_snapshot.compare_source_native",
                   side_effect=[(5,EXPECTED),
                                Refused(503,"PUBLISH_SOURCE_MOVED")]):
            with self.assertRaises(Refused):publish(self.config)
        self.assertEqual(self.output.read_bytes(),before)
        self.assertEqual(len(list(self.folder.glob(".staging*"))),0)
    def test_16_snapshot_symlink_wrong_owner_rejected(self):
        self.write()
        other=self.folder/"another.sqlite"
        other.symlink_to(self.output)
        with self.assertRaises(Refused):
            read_published(other,os.getuid()+1,"a"*64)
    def test_17_network_policy_four_rules(self):
        self.assertEqual(len(rules(3158,995)),4)
    def test_18_network_policy_owner_exception_ipv4_ipv6(self):
        rs=rules(3158,995)
        self.assertIn("127.0.0.1",rs[0][2])
        self.assertIn("::1",rs[2][2])
        self.assertIn("--uid-owner",rs[0][2])
        self.assertIn("--uid-owner",rs[2][2])
    def test_19_network_policy_nonloopback_ingress_rejected(self):
        rs=rules(3158,995)
        self.assertIn("INPUT",rs[1])
        self.assertIn("INPUT",rs[3])
        self.assertIn("REJECT",rs[1][2])
    def test_20_network_policy_requires_root(self):
        with patch("network_policy.os.geteuid",return_value=1000):
            with self.assertRaises(RuntimeError):
                apply("enable",3158,995)
    def test_21_network_policy_rejects_low_ports(self):
        with patch("network_policy.os.geteuid",return_value=0):
            with self.assertRaises(RuntimeError):
                apply("enable",80,995)
    def test_22_snapshot_outside_scoped_path_rejected(self):
        self.config["output"]="/tmp/snapshot-untrusted.sqlite"
        with self.assertRaises(Refused):publish(self.config)


if __name__=="__main__":unittest.main()
