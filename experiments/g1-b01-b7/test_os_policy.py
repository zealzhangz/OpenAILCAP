"""B7 trusted service configuration and native OS access policy unit tests.

Real Linux DAC boundary and user identities are tested separately under
sudo/runuser in experiment.py; these pure tests cannot substitute for it.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"g1-b01-b2"))
sys.path.insert(0,str(HERE.parent/"g1-b01-b4"))
sys.path.insert(0,str(HERE.parent/"g1-b01-b5"))
from kernel_service import NoBuildAccess,load_config
from direct_probe import file_probe,sqlite_probe
from physical_sql_oracle import digest


def good():
    return {
        "dbPath":"/tmp/private/domain.sqlite",
        "password":"a"*36,
        "agentToken":"b"*36,
        "pluginToken":"c"*36,
        "runtimeToken":"d"*36
    }


class SecurityContract(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.config=Path(self.tmp.name)/"config.json"
        self.save(good(),0o600)

    def tearDown(self):
        self.tmp.cleanup()

    def save(self,obj,mode):
        self.config.write_text(json.dumps(obj))
        self.config.chmod(mode)

    def denied(self,phrase):
        with self.assertRaises(RuntimeError) as exc:
            load_config(self.config)
        self.assertIn(phrase,str(exc.exception))

    def test_private_config_accepted(self):
        self.assertEqual(load_config(self.config),good())

    def test_secret_config_world_readable_refused(self):
        self.save(good(),0o644)
        self.denied("KERNEL_CONFIG_NOT_PRIVATE")

    def test_secret_config_group_readable_refused(self):
        self.save(good(),0o640)
        self.denied("KERNEL_CONFIG_NOT_PRIVATE")

    def test_secret_config_other_writable_refused(self):
        self.save(good(),0o602)
        self.denied("KERNEL_CONFIG_NOT_PRIVATE")

    def test_untrusted_actor_input_field_refused(self):
        obj=good();obj["actorId"]="root"
        self.save(obj,0o600)
        self.denied("CONFIG_SHAPE_INVALID")

    def test_missing_grant_refused(self):
        obj=good();del obj["pluginToken"]
        self.save(obj,0o600)
        self.denied("CONFIG_SHAPE_INVALID")

    def test_missing_password_refused(self):
        obj=good();obj["password"]=""
        self.save(obj,0o600)
        self.denied("CREDENTIALS_NOT_SET")

    def test_short_agent_secret_refused(self):
        obj=good();obj["agentToken"]="x"
        self.save(obj,0o600)
        self.denied("CREDENTIALS_NOT_SET")

    def test_no_docker_build_privilege_on_kernel(self):
        with self.assertRaisesRegex(
                RuntimeError,"BUILD_EXECUTION_NOT_GRANTED_TO_KERNEL"):
            NoBuildAccess().test("arbitrary code")

    def test_canonical_digest_order_independence(self):
        self.assertEqual(digest({"x":1,"y":2}),digest({"y":2,"x":1}))

    def test_canonical_digest_modified_resource_differs(self):
        self.assertNotEqual(digest({"title":"old"}),digest({"title":"new"}))

    def test_file_read_positive_same_trusted_user(self):
        self.assertEqual(file_probe(self.config,os.O_RDONLY),"ALLOWED")

    def test_file_write_positive_same_trusted_user(self):
        self.assertEqual(file_probe(self.config,os.O_RDWR),"ALLOWED")

    def test_file_missing_fails_instead_of_creation(self):
        self.assertEqual(file_probe(self.config.with_suffix(".missing"),os.O_RDONLY),
                         "DENIED")

    def test_sqlite_native_read_and_update_are_real(self):
        path=Path(self.tmp.name)/"db.sqlite"
        with sqlite3.connect(path) as db:
            db.execute("CREATE TABLE apps(app TEXT, revision INTEGER)")
            db.execute("INSERT INTO apps VALUES('app-a',1)")
        self.assertEqual(sqlite_probe(path,"ro"),"ALLOWED")
        self.assertEqual(sqlite_probe(path,"rw",write=True),"ALLOWED")

    def test_sqlite_nonexistent_uri_does_not_create_database(self):
        path=Path(self.tmp.name)/"not-created.sqlite"
        self.assertEqual(sqlite_probe(path,"rw",write=True),"DENIED")
        self.assertFalse(path.exists())


if __name__=="__main__":unittest.main()
