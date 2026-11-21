"""No-network safety/unit checks for six frozen task route predictions."""
import json
import unittest
from pathlib import Path
from predict import validate_choices

SPEC=json.loads((Path(__file__).parent/"spec.json").read_text(encoding="utf-8"))

class RouteChoiceContract(unittest.TestCase):
    def test_six_fixed_cases_two_each(self):
        self.assertEqual(len(SPEC["cases"]),6)
        actual={x["expected_mode"] for x in SPEC["cases"]}
        self.assertEqual(actual,{"CONFIG","CODE","HYBRID"})
        self.assertEqual([x["expected_mode"] for x in SPEC["cases"]].count("CONFIG"),2)
        self.assertEqual([x["expected_mode"] for x in SPEC["cases"]].count("CODE"),2)
        self.assertEqual([x["expected_mode"] for x in SPEC["cases"]].count("HYBRID"),2)
    def test_no_duplicate_ids_and_bounded_once(self):
        ids=[c["id"] for c in SPEC["cases"]]
        self.assertEqual(len(set(ids)),6)
        self.assertEqual(SPEC["model_calls_budget"],1)
    def test_validated_full_routes(self):
        p={"choices":[{"id":c["id"],"mode":c["expected_mode"]} for c in SPEC["cases"]]}
        validate_choices(SPEC,p)
    def test_unknown_tool_route_rejected(self):
        p={"choices":[{"id":c["id"],"mode":"CONFIG"} for c in SPEC["cases"]]}
        p["choices"][0]["mode"]="SHELL"
        with self.assertRaises(ValueError):validate_choices(SPEC,p)
    def test_duplicate_task_rejected(self):
        p={"choices":[{"id":c["id"],"mode":"CONFIG"} for c in SPEC["cases"]]}
        p["choices"][1]["id"]=p["choices"][0]["id"]
        with self.assertRaises(ValueError):validate_choices(SPEC,p)
    def test_extra_parameter_rejected(self):
        p={"choices":[{"id":c["id"],"mode":"CONFIG"} for c in SPEC["cases"]]}
        p["choices"][0]["raw_js"]="process.exit()"
        with self.assertRaises(ValueError):validate_choices(SPEC,p)

if __name__=="__main__":unittest.main()
