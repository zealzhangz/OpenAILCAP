"""Adversarial no-LLM checks for the strict B3 model proposal boundary."""
import copy
import json
import sys
import unittest
from pathlib import Path

from plan import (_decode_tool_call, check_plan, generate,
                  reviewed_offline_plan, sha)
from schema_core import Rejected

class B3Preflight(unittest.TestCase):
    def setUp(self):
        self.base=reviewed_offline_plan()

    def check_error(self,code,callable_):
        with self.assertRaises(Rejected) as exc:callable_()
        self.assertEqual(exc.exception.code,code)

    def test_reviewed_offline_baseline(self):
        result=check_plan(self.base)
        self.assertEqual(len(result["definitions"]),4)
        self.assertEqual(result["planHash"],sha(result["definitions"]))

    def test_offline_truthful_no_inference(self):
        result=generate(live=False)
        self.assertFalse(result["inference"])
        self.assertEqual(result["modelCalls"],0)
        self.assertEqual(result["toolCalls"],0)

    def test_extra_actor_field_rejected(self):
        p=copy.deepcopy(self.base)
        p["actorId"]="admin"
        self.check_error("PLAN_SHAPE_INVALID",lambda:check_plan(p))

    def test_extra_operation_fields_rejected(self):
        p=copy.deepcopy(self.base)
        p["operations"][0]["sql"]="DROP TABLE apps"
        self.check_error("PLAN_RESOURCE_ORDER_OR_ID_INVALID",lambda:check_plan(p))

    def test_missing_operation_rejected(self):
        p=copy.deepcopy(self.base)
        p["operations"].pop()
        self.check_error("PLAN_LENGTH_INVALID",lambda:check_plan(p))

    def test_duplicate_resource_id_rejected(self):
        p=copy.deepcopy(self.base)
        p["operations"][1]["resourceId"]="model.contracts"
        self.check_error("PLAN_RESOURCE_ORDER_OR_ID_INVALID",lambda:check_plan(p))

    def test_out_of_order_resource_rejected(self):
        p=copy.deepcopy(self.base)
        p["operations"][0],p["operations"][1]=p["operations"][1],p["operations"][0]
        self.check_error("PLAN_RESOURCE_ORDER_OR_ID_INVALID",lambda:check_plan(p))

    def test_undeclared_model_field_rejected(self):
        p=copy.deepcopy(self.base)
        p["operations"][0]["definition"]["fields"].append(
            {"name":"password","type":"string","required":False})
        self.check_error("SEMANTIC_MODEL_MISMATCH",lambda:check_plan(p))

    def test_wrong_model_type_rejected(self):
        p=copy.deepcopy(self.base)
        p["operations"][0]["definition"]["fields"][2]["type"]="string"
        self.check_error("SEMANTIC_MODEL_MISMATCH",lambda:check_plan(p))

    def test_wrong_minor_units_rejected(self):
        p=copy.deepcopy(self.base)
        p["operations"][3]["definition"]["thresholdMinor"]=1000000
        self.check_error("SEMANTIC_WORKFLOW_MISMATCH",lambda:check_plan(p))

    def test_missing_form_required_field_rejected(self):
        p=copy.deepcopy(self.base)
        p["operations"][1]["definition"]["fields"].remove("title")
        self.check_error("SEMANTIC_FORM_MISMATCH",lambda:check_plan(p))

    def test_missing_view_column_rejected(self):
        p=copy.deepcopy(self.base)
        p["operations"][2]["definition"]["columns"].remove("amount_minor")
        self.check_error("SEMANTIC_VIEW_MISMATCH",lambda:check_plan(p))

    def test_dangling_reference_rejected(self):
        p=copy.deepcopy(self.base)
        p["operations"][2]["definition"]["columns"][0]="never_exists"
        self.check_error("BROKEN_FIELD_REFERENCE",lambda:check_plan(p))

    def test_html_title_rejected(self):
        p=copy.deepcopy(self.base)
        p["operations"][1]["definition"]["title"]="<script>"
        self.check_error("UNSAFE_PRESENTATION_TITLE",lambda:check_plan(p))

    def test_unexpected_function_rejected(self):
        self.check_error("MODEL_TOOL_NAME_INVALID",
                         lambda:_decode_tool_call({"choices":[{
                             "message":{"tool_calls":[{"function":{
                                 "name":"execute_shell","arguments":"{}"}}]}}]}))

    def test_multiple_function_calls_rejected(self):
        tool={"function":{"name":"propose_application_plan",
                          "arguments":json.dumps(self.base)}}
        self.check_error("MODEL_TOOL_CALL_COUNT_INVALID",
                         lambda:_decode_tool_call({"choices":[{
                             "message":{"tool_calls":[tool,tool]}}]}))

    def test_non_json_function_arguments_rejected(self):
        self.check_error("MODEL_TOOL_JSON_INVALID",
                         lambda:_decode_tool_call({"choices":[{
                             "message":{"tool_calls":[{"function":{
                                 "name":"propose_application_plan",
                                 "arguments":"DROP TABLE apps"}}]}}]}))

    def test_valid_tool_parsing_only_proposes(self):
        tool={"function":{"name":"propose_application_plan",
                          "arguments":json.dumps(self.base)}}
        checked=_decode_tool_call({"choices":[{"message":{"tool_calls":[tool]}}]})
        self.assertEqual(len(checked["definitions"]),4)

if __name__=="__main__":
    unittest.main()
