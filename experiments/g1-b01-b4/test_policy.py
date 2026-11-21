"""S1 B4 static policy / model-tool adversarial tests: no Docker/LLM required."""
import json
import unittest
from pathlib import Path

from policy import (CAPABILITIES,REQUIRED,RuleError,oracle,parse_proposal,
                    propose,select_mode,source_hash,validate_source)


BASE="def score_contract(amount_minor, supplier_score, months_active):\n    return 42\n"


class PolicyTests(unittest.TestCase):
    def bad(self,code,src):
        with self.assertRaises(RuleError) as exc:
            validate_source(src)
        self.assertEqual(exc.exception.code,code)

    def test_reviewed_code_statically_compiles(self):
        self.assertTrue(validate_source(propose(live=False)["code"]["source"])
                        ["sourceHash"])

    def test_real_inference_not_faked_offline(self):
        self.assertEqual(propose(live=False)["modelCalls"],0)
        self.assertFalse(propose(live=False)["inference"])

    def test_capability_lowcode(self):
        self.assertEqual(select_mode("amount_threshold_approval"),"LOW_CODE")

    def test_capability_custom_code_needed(self):
        self.assertEqual(select_mode(REQUIRED),"CUSTOM_CODE")

    def test_capability_unknown_denied(self):
        with self.assertRaises(RuleError) as e:select_mode("run_unapproved_shell")
        self.assertEqual(e.exception.code,"CAPABILITY_UNKNOWN")

    def test_wrong_signature_rejected(self):
        self.bad("SIGNATURE_FORBIDDEN",
                 "def score_contract(x,y,z):\n    return 0\n")

    def test_multiple_functions_rejected(self):
        self.bad("ONE_FUNCTION_REQUIRED",BASE+
                 "\ndef more():\n    return 0\n")

    def test_import_rejected(self):
        self.bad("AST_NODE_FORBIDDEN",BASE.replace(
            "    return 42","    import os\n    return 42"))

    def test_exec_rejected(self):
        self.bad("EXPRESSION_FORBIDDEN",BASE.replace(
            "    return 42","    exec('print(1)')\n    return 42"))

    def test_network_call_rejected(self):
        self.bad("EXPRESSION_FORBIDDEN",BASE.replace(
            "    return 42","    socket(1)\n    return 42"))

    def test_attribute_traversal_rejected(self):
        self.bad("AST_NODE_FORBIDDEN",BASE.replace(
            "    return 42","    return amount_minor.real"))

    def test_subscript_rejected(self):
        self.bad("AST_NODE_FORBIDDEN",BASE.replace(
            "    return 42","    return x[0]"))

    def test_loop_rejected(self):
        self.bad("AST_NODE_FORBIDDEN",BASE.replace(
            "    return 42","    while True:\n        pass\n    return 42"))

    def test_list_and_comprehension_rejected(self):
        self.bad("AST_NODE_FORBIDDEN",BASE.replace(
            "    return 42","    return [x for x in range(10)]"))

    def test_lambda_rejected(self):
        self.bad("AST_NODE_FORBIDDEN",BASE.replace(
            "    return 42","    x = lambda a: a\n    return 42"))

    def test_dunder_identifier_rejected(self):
        self.bad("IDENTIFIER_FORBIDDEN",BASE.replace(
            "    return 42","    __class__ = 1\n    return __class__"))

    def test_type_annotation_rejected(self):
        self.bad("SIGNATURE_FORBIDDEN",
                 "def score_contract(amount_minor: int, supplier_score, months_active):\n"
                 "    return 42\n")

    def test_assignment_cannot_target_index(self):
        self.bad("ASSIGNMENT_FORBIDDEN",BASE.replace(
            "    return 42","    a[0] = 1\n    return 42"))

    def test_safe_min_max_allowed(self):
        v=validate_source(BASE.replace(
            "    return 42","    return min(100,max(0,42))"))
        self.assertEqual(len(v["sourceHash"]),64)

    def test_min_max_kwargs_denied(self):
        self.bad("FUNCTION_CALL_FORBIDDEN",BASE.replace(
            "    return 42","    return max(1, key=2)"))

    def test_shell_tool_name_rejected(self):
        tool={"function":{"name":"run_shell","arguments":"{}"}}
        with self.assertRaises(RuleError) as e:
            parse_proposal({"choices":[{"message":{"tool_calls":[tool]}}]})
        self.assertEqual(e.exception.code,"MODEL_TOOL_NAME_INVALID")

    def test_multiple_model_calls_rejected(self):
        tool={"function":{"name":"submit_python_rule",
                          "arguments":json.dumps({"source":BASE})}}
        with self.assertRaises(RuleError) as e:
            parse_proposal({"choices":[{"message":{"tool_calls":[tool,tool]}}]})
        self.assertEqual(e.exception.code,"MODEL_TOOL_COUNT_INVALID")

    def test_extra_authorization_field_rejected(self):
        tool={"function":{"name":"submit_python_rule",
                          "arguments":json.dumps({"source":BASE,"publish":True})}}
        with self.assertRaises(RuleError) as e:
            parse_proposal({"choices":[{"message":{"tool_calls":[tool]}}]})
        self.assertEqual(e.exception.code,"MODEL_FIELDS_FORBIDDEN")

    def test_valid_function_response_returns_only_source(self):
        tool={"function":{"name":"submit_python_rule",
                          "arguments":json.dumps({"source":BASE})}}
        v=parse_proposal({"choices":[{"message":{"tool_calls":[tool]}}]})
        self.assertEqual(v["sourceHash"],source_hash(BASE))

    def test_oracle_threshold_boundaries(self):
        self.assertEqual(oracle(100000000,60,24),0)
        self.assertEqual(oracle(100000001,60,24),20)
        self.assertEqual(oracle(200000000,44,24),40)
        self.assertEqual(oracle(200000001,44,24),90)
        self.assertEqual(oracle(500000000,60,24),20)
        self.assertEqual(oracle(500000001,60,24),35)
        self.assertEqual(oracle(10**12,0,0),95)

    def test_oracle_invalid_type(self):
        with self.assertRaises(RuleError) as e:oracle(100,True,3)
        self.assertEqual(e.exception.code,"INPUT_TYPE_INVALID")

    def test_oracle_invalid_range(self):
        with self.assertRaises(RuleError) as e:oracle(100,-1,3)
        self.assertEqual(e.exception.code,"INPUT_RANGE_INVALID")

if __name__=="__main__":
    unittest.main()
