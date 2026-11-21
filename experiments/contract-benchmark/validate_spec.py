"""Independent preregistered contract acceptance oracle; NOT a platform test."""
from __future__ import annotations
import json
import re
import sys
import unittest
from decimal import Decimal
from pathlib import Path

SPEC_PATH = Path(__file__).with_name("spec.json")
AMOUNT_RE = re.compile(r"^[0-9]{1,10}(?:\.[0-9]{1,2})?$")
THRESHOLD = Decimal("1000000.00")


def read_spec() -> dict:
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def amount_class(amount: str) -> str:
    if not isinstance(amount, str) or AMOUNT_RE.fullmatch(amount) is None:
        return "INVALID"
    value = Decimal(amount)
    return "HIGH" if value > THRESHOLD else "NORMAL"


def advance(before: str, action: str, role: str, level: str) -> str:
    if before in {"Approved", "Rejected"}:
        return "INVALID_STATE"
    if action == "submit":
        if before != "Draft":
            return "INVALID_STATE"
        return "Submitted" if role == "creator" else "FORBIDDEN"
    if before not in {"Submitted", "Level1Approved"}:
        return "INVALID_STATE"
    required = "approver1" if before == "Submitted" else "approver2"
    if role != required:
        return "FORBIDDEN"
    if action == "reject":
        return "Rejected"
    if action != "approve":
        return "INVALID_ACTION"
    if before == "Level1Approved":
        return "Approved"
    return "Level1Approved" if level == "HIGH" else "Approved"


class ContractSpecificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = read_spec()

    def test_01_threshold_is_strictly_greater_than_million(self):
        self.assertEqual(self.spec["threshold_op"], ">")
        self.assertEqual(Decimal(self.spec["threshold"]), THRESHOLD)

    def test_02_amount_boundary_oracles(self):
        self.assertGreaterEqual(len(self.spec["amount_cases"]), 12)
        for case in self.spec["amount_cases"]:
            with self.subTest(case=case["id"]):
                self.assertEqual(amount_class(case["amount"]), case["expected"])

    def test_03_state_machine_oracles(self):
        self.assertGreaterEqual(len(self.spec["transition_cases"]), 12)
        for case in self.spec["transition_cases"]:
            with self.subTest(case=case["id"]):
                self.assertEqual(advance(case["from"], case["action"],
                                         case["role"], case["level"]), case["expected"])

    def test_04_all_cases_have_unique_ids(self):
        all_cases = self.spec["amount_cases"] + self.spec["transition_cases"] + self.spec["acceptance_tasks"]
        ids = [case["id"] for case in all_cases]
        self.assertEqual(len(ids), len(set(ids)))

    def test_05_platform_tasks_are_not_falsely_marked_success(self):
        self.assertGreaterEqual(len(self.spec["acceptance_tasks"]), 18)
        self.assertTrue(all(task["result"] == "NOT_RUN" for task in self.spec["acceptance_tasks"]))
        self.assertTrue(all(task.get("oracle") and task.get("evidence_required")
                            for task in self.spec["acceptance_tasks"]))

    def test_06_required_platform_experiments_covered(self):
        categories = {task["category"] for task in self.spec["acceptance_tasks"]}
        self.assertTrue({"data", "workflow", "ai-config", "ai-route", "ai-code",
                         "manual-ai", "plugin", "isolation", "release", "security",
                         "independence"}.issubset(categories))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--summary":
        spec = read_spec()
        print(json.dumps({"spec_id": spec["id"],
                          "amount_oracles": len(spec["amount_cases"]),
                          "transition_oracles": len(spec["transition_cases"]),
                          "platform_acceptance_tasks": len(spec["acceptance_tasks"]),
                          "platform_tasks_completed": sum(c["result"] == "PASS" for c in spec["acceptance_tasks"])},
                         ensure_ascii=False, indent=2))
    else:
        unittest.main()
