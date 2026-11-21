"""B9 deterministic projection compiler rejection and scope regression units."""
import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
sys.path.insert(0,str(ROOT/"g1-b01-b2"))
from schema_core import sha
from projector import (compile_release,check_compiled,ProjectionRejected,
                       hash_pack,canon,assert_no_import_from_runtime)
from native_env_launcher import ALLOWED as LAUNCH_KEYS


def setup():
    defs=json.loads((ROOT/"g1-b01-b2"/"contract_spec.json").read_text())
    pack=json.loads((ROOT/"platform-saltcorn"/"contract-pack.json").read_text())
    release={"version":1,"manifestHash":sha(defs),
             "draftRevision":4,"definitions":defs}
    return release,pack


class ProjectedRelease(unittest.TestCase):
    def good(self):
        rel,pack=setup()
        return compile_release(rel,pack)
    def deny(self,code,rel=None,pack=None):
        a,b=setup()
        with self.assertRaises(ProjectionRejected) as x:
            compile_release(a if rel is None else rel,
                            b if pack is None else pack)
        self.assertEqual(x.exception.code,code)

    def test_v1_pack_hash_and_manifest_retained(self):
        r=self.good()
        self.assertEqual(r["manifestHash"],setup()[0]["manifestHash"])
    def test_release_v1_is_validated(self):
        self.assertTrue(check_compiled(self.good()))
    def test_pack_has_one_derived_table(self):
        self.assertEqual([x["name"] for x in self.good()[
            "projectionPack"]["tables"]],["s1_contracts"])
    def test_pack_has_one_derived_view(self):
        self.assertEqual([x["name"] for x in self.good()[
            "projectionPack"]["views"]],["s1_contract_list"])
    def test_v1_columns_are_source_view_columns(self):
        r=self.good()
        self.assertEqual([
            x["field_name"] for x in r["projectionPack"]["views"][0][
                "configuration"]["columns"]],
            ["contract_no","amount_minor","status"])
    def test_v2_columns_produce_new_pack_sha(self):
        rel,pack=setup()
        rel["definitions"]["view.contracts"]["columns"]=[
            "contract_no","title","amount_minor","status"]
        rel["version"]=2
        rel["manifestHash"]=sha(rel["definitions"])
        v2=compile_release(rel,pack)
        self.assertNotEqual(v2["projectionPackHash"],
                            self.good()["projectionPackHash"])
    def test_compilation_deterministic(self):
        self.assertEqual(self.good(),self.good())
    def test_original_native_pack_not_mutated(self):
        rel,pack=setup()
        before=copy.deepcopy(pack)
        compile_release(rel,pack)
        self.assertEqual(before,pack)
    def test_code_and_workflow_not_claimed_as_projected(self):
        self.assertEqual(self.good()["notProjected"],[
            "form.contracts","workflow.approval","B4 code"])
    def test_trigger_and_plugin_never_emitted(self):
        _,pack=setup()
        pack["plugins"]=[{"name":"malicious plugin"}]
        pack["triggers"]=[{"name":"malicious trigger"}]
        r=compile_release(setup()[0],pack)
        self.assertEqual(r["projectionPack"]["plugins"],[])
        self.assertEqual(r["projectionPack"]["triggers"],[])
    def test_reject_tampered_manifest_definitions(self):
        rel,_=setup()
        rel["definitions"]["view.contracts"]["title"]="EVIL"
        self.deny("RELEASE_HASH_DRIFT",rel=rel)
    def test_reject_laundered_extra_definitions(self):
        rel,_=setup()
        rel["definitions"]["plugin.hidden"]={"kind":"plugin"}
        rel["manifestHash"]=sha(rel["definitions"])
        self.deny("UNSUPPORTED_DEFINITION_SET",rel=rel)
    def test_reject_broken_reference_even_with_valid_hash(self):
        rel,_=setup()
        rel["definitions"]["view.contracts"]["model"]="model.missing"
        rel["manifestHash"]=sha(rel["definitions"])
        with self.assertRaises(ProjectionRejected) as x:
            compile_release(rel,setup()[1])
        self.assertIn("RELEASE_INVALID_",x.exception.code)
    def test_reject_unsupported_model_name(self):
        rel,_=setup()
        rel["definitions"]["model.contracts"]["table"]="other"
        rel["manifestHash"]=sha(rel["definitions"])
        self.deny("UNSUPPORTED_MODEL_TABLE",rel=rel)
    def test_reject_model_extra_field(self):
        rel,_=setup()
        rel["definitions"]["model.contracts"]["fields"].append({
            "name":"user_secret","type":"string","required":False})
        rel["manifestHash"]=sha(rel["definitions"])
        self.deny("UNSUPPORTED_MODEL_FIELDS",rel=rel)
    def test_reject_unsupported_view_duplicate(self):
        rel,_=setup()
        rel["definitions"]["view.contracts"]["columns"]=[
            "contract_no","contract_no"]
        rel["manifestHash"]=sha(rel["definitions"])
        with self.assertRaises(ProjectionRejected) as x:
            compile_release(rel,setup()[1])
        self.assertTrue(x.exception.code.startswith("RELEASE_INVALID_") or
                        x.exception.code=="UNSUPPORTED_VIEW_COLUMNS")
    def test_reject_projection_pack_tampered(self):
        r=self.good()
        r["projectionPack"]["tables"][0]["fields"][0]["label"]="Injected"
        with self.assertRaises(ProjectionRejected) as x:
            check_compiled(r)
        self.assertEqual(x.exception.code,"PROJECTION_TAMPERED")
    def test_reject_invalid_release_version(self):
        rel,_=setup()
        rel["version"]=False
        self.deny("INVALID_RELEASE_VERSION",rel=rel)
    def test_reject_invalid_release_envelope(self):
        rel,_=setup()
        rel["runtimeAdmin"]="true"
        self.deny("RELEASE_SHAPE_INVALID",rel=rel)
    def test_no_reverse_sync_capability(self):
        with self.assertRaises(ProjectionRejected):
            assert_no_import_from_runtime({"reverseSync":"yes"})
    def test_manifest_hash_is_not_runtime_field_hash(self):
        r=self.good()
        self.assertNotEqual(r["projectionPackHash"],r["manifestHash"])
    def test_compiler_does_not_take_form_or_workflow_as_native_policy(self):
        r=self.good()
        self.assertTrue(r["notProjected"])
    def test_no_authority_environment_in_native_launcher(self):
        self.assertEqual(LAUNCH_KEYS,{
            "PATH","HOME","SQLITE_FILEPATH",
            "SALTCORN_SESSION_SECRET","SALTCORN_NWORKERS"})
    def test_runtime_default_has_no_sql_direct_access_token(self):
        r=self.good()
        self.assertNotIn("publisherToken",canon(r["projectionPack"]))
    def test_reject_template_wrong_type(self):
        rel,pack=setup()
        pack["tables"][0]["fields"][0]["type"]="Trigger"
        self.deny("PACK_TEMPLATE_TYPE_DRIFT",pack=pack)


if __name__=="__main__":unittest.main()
