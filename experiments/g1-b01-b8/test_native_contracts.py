"""B8 offline controls: provenance, exact native scripts and artifact oracle.

No mock tests are counted as verification of real Saltcorn OS or browser
behavior. That evidence comes only from experiment.py in GitHub CI.
"""
from __future__ import annotations

import ast
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
sys.path.insert(0,str(ROOT/"platform-saltcorn"/"governed"))
sys.path.insert(0,str(HERE))
from gateway import Storage,Rejected
from experiment import uid_probe
from physical_native_oracle import read
from gateway_service import serve


class B8Contracts(unittest.TestCase):
    def test_real_native_js_field_update_present(self):
        t=(ROOT/"platform-saltcorn"/"governed"/
           "native-out-of-band.js").read_text()
        self.assertIn("field.update({label:",t)
    def test_native_js_does_not_use_gateway(self):
        t=(ROOT/"platform-saltcorn"/"governed"/
           "native-out-of-band.js").read_text()
        self.assertNotIn("http://",t)
        self.assertNotIn("fetch(",t)
    def test_real_contract_pack_has_actual_native_field(self):
        j=json.loads((ROOT/"platform-saltcorn"/"contract-pack.json").read_text())
        f=next(x["fields"] for x in j["tables"]
               if x["name"]=="s1_contracts")
        self.assertIn("title",[x["name"] for x in f])
    def test_real_pack_has_native_publishing_entities(self):
        j=json.loads((ROOT/"platform-saltcorn"/"contract-pack.json").read_text())
        self.assertTrue(j["views"])
    def test_real_seed_uses_native_table_model(self):
        t=(ROOT/"platform-saltcorn"/"seed-contract.js").read_text()
        self.assertIn("Table.findOne",t)
        self.assertIn("insertRow",t)
    def test_governed_storage_contains_drift_guard(self):
        import inspect
        s=inspect.getsource(Storage.read)
        self.assertIn("OUT_OF_BAND_DRIFT",s)
    def test_governed_writer_requires_atomic_sql_begin(self):
        import inspect
        s=inspect.getsource(Storage.update)
        self.assertIn("BEGIN IMMEDIATE",s)
        self.assertIn("base_revision",s)
    def test_governed_writer_receipt_and_audit_in_one_transaction(self):
        import inspect
        s=inspect.getsource(Storage.update)
        self.assertIn("_openailcap_s1_http_changes",s)
        self.assertIn("_openailcap_s1_http_audit",s)
        self.assertIn("COMMIT",s)
    def test_governed_actor_from_bearer_not_client_json(self):
        import inspect
        from gateway import Handler
        s=inspect.getsource(Handler.bearer)
        self.assertIn("self.server.agent_token",s)
        self.assertIn("self.server.read_token",s)
    def test_server_requires_private_config(self):
        import inspect
        s=inspect.getsource(serve)
        self.assertIn("B8_GATEWAY_CONFIG_MODE_UNSAFE",s)
    def test_server_rejects_world_readable_config_before_load(self):
        with tempfile.TemporaryDirectory() as root:
            c=Path(root)/"config.json";c.write_text("{}")
            c.chmod(0o644)
            with self.assertRaisesRegex(RuntimeError,"CONFIG_MODE_UNSAFE"):
                serve(c,Path(root)/"ready.json")
    def test_native_os_probe_contains_real_sql_update(self):
        code=uid_probe("/db/private","/db/config")
        self.assertIn("UPDATE _sc_fields SET label=label",code)
        ast.parse(code)
    def test_native_os_probe_does_not_create_db(self):
        code=uid_probe("/db/private","/db/config")
        self.assertIn("mode=rw",code)
    def test_real_native_browser_wizard_is_reused(self):
        import inspect
        from experiment import save_wizard
        s=inspect.getsource(save_wizard)
        self.assertIn("button",s)
        self.assertIn("contextEnc",s)
    def test_physical_oracle_is_separate_sqlite_read(self):
        import inspect
        s=inspect.getsource(read)
        self.assertIn("sqlite3.connect",s)
        self.assertIn("_sc_fields",s)
        self.assertIn("_openailcap_s1_http_guard",s)


if __name__=="__main__":
    unittest.main()
