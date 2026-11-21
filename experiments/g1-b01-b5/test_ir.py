"""B5 representation parity/adversarial tests. No Docker and no LLM."""
import copy
import json
import sys
import unittest
from pathlib import Path
from schema_core import Rejected,sha
from ir_bridge import (EXTENSION,IDS,compare_representations,
                       from_ir,normalise_domain,to_ir)

SPEC=json.loads((Path(__file__).resolve().parent.parent/"g1-b01-b2"/
                 "contract_spec.json").read_text(encoding="utf-8"))
SPEC["view.contracts"]["columns"]=[
    "contract_no","title","amount_minor","status"]

class IRParity(unittest.TestCase):
    def setUp(self):
        self.direct=copy.deepcopy(SPEC)
        self.ir=to_ir(self.direct)
    def bad_ir(self,code,transform):
        proposal=copy.deepcopy(self.ir)
        transform(proposal)
        with self.assertRaises(Rejected) as c:from_ir(proposal)
        self.assertEqual(c.exception.code,code)
    def test_exact_domain_manifest(self):
        self.assertEqual(normalise_domain(self.direct),self.direct)
    def test_full_ir_roundtrip(self):
        self.assertEqual(from_ir(self.ir)["definitions"],self.direct)
    def test_ir_reconstructable(self):
        self.assertEqual(to_ir(from_ir(self.ir)["definitions"]),self.ir)
    def test_manifest_byte_canonical_equivalence(self):
        self.assertEqual(sha(self.direct),from_ir(self.ir)["manifestHash"])
    def test_representation_is_not_raw_nested_schema(self):
        self.assertIn("entity",self.ir)
        self.assertNotIn("model.contracts",self.ir)
        self.assertIn("attributes",self.ir["entity"])
        self.assertIn("interfaces",self.ir)
    def test_extension_reference_identical(self):
        self.assertEqual(self.ir["extensions"],[EXTENSION])
    def test_compare_two_real_serializations(self):
        x=compare_representations(self.direct)
        self.assertTrue(all(x[k] for k in (
            "identicalDefinitions","identicalManifest","irRoundtripStable")))
        self.assertNotEqual(x["domainAuthoringJsonBytes"],
                            x["irAuthoringJsonBytes"])
        self.assertEqual(x["materializedB2CommandsPerFullCreate"],4)
    def test_form_title_change_one_resource_only(self):
        copy_ir=copy.deepcopy(self.ir)
        copy_ir["interfaces"][0]["caption"]="人工更改的合同登记"
        defs=from_ir(copy_ir)["definitions"]
        changed=[k for k in IDS if defs[k]!=self.direct[k]]
        self.assertEqual(changed,["form.contracts"])
    def test_view_title_change_one_resource_only(self):
        copy_ir=copy.deepcopy(self.ir)
        copy_ir["interfaces"][1]["caption"]="AI 重新命名台账"
        defs=from_ir(copy_ir)["definitions"]
        self.assertEqual([k for k in IDS if defs[k]!=self.direct[k]],
                         ["view.contracts"])
    def test_ir_unknown_sibling_rejected(self):
        self.bad_ir("IR_ENVELOPE_INVALID",lambda x:x.update({"actor":"admin"}))
    def test_ir_version_bump_denied(self):
        self.bad_ir("IR_ENVELOPE_INVALID",lambda x:x.update({"irVersion":2}))
    def test_ir_second_process_rejected(self):
        self.bad_ir("IR_PROCESS_INVALID",lambda x:x["processes"].append(
            copy.deepcopy(x["processes"][0])))
    def test_ir_unknown_extension_denied(self):
        self.bad_ir("IR_EXTENSION_CONTRACT_INVALID",
                    lambda x:x["extensions"].append({"run":"shell"}))
    def test_ir_dangling_view_binding_denied(self):
        self.bad_ir("BROKEN_FIELD_REFERENCE",
                    lambda x:x["interfaces"][1]["bindings"].append("unknown"))
    def test_ir_dangling_entity_denied(self):
        self.bad_ir("IR_INTERFACE_REFERENCE_INVALID",
                    lambda x:x["interfaces"][0].update({"entity":"alien"}))
    def test_ir_duplicate_form_rejected(self):
        self.bad_ir("IR_INTERFACE_REFERENCE_INVALID",
                    lambda x:x["interfaces"][1].update({"type":"form"}))
    def test_ir_untrusted_extra_attribute_denied(self):
        self.bad_ir("IR_FIELD_INVALID",
                    lambda x:x["entity"]["attributes"][0].update({"sql":"DROP"}))
    def test_ir_workflow_wrong_amount_type_denied(self):
        self.bad_ir("BROKEN_WORKFLOW_FIELD_TYPE",
                    lambda x:x["entity"]["attributes"][2].update(
                        {"dataType":"string"}))
    def test_ir_workflow_threshold_preserved(self):
        self.assertEqual(from_ir(self.ir)["definitions"]["workflow.approval"]
                         ["thresholdMinor"],100000000)
    def test_ir_process_ref_swap_denied(self):
        self.bad_ir("DOMAIN_SEMANTICS_INVALID",
                    lambda x:x["processes"][0].update({"amount":"contract_no"}))
    def test_domain_missing_resource_denied(self):
        p=copy.deepcopy(self.direct);del p["workflow.approval"]
        with self.assertRaises(Rejected) as c:normalise_domain(p)
        self.assertEqual(c.exception.code,"DOMAIN_RESOURCE_SET_INVALID")

if __name__=="__main__":unittest.main()
