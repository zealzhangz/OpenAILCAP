#!/usr/bin/env python3
"""Audit the G1 convergence ledger against the frozen acceptance definitions."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
W = ROOT / "docs/01-research/g1-b01-acceptance-cases.json"
TC = ROOT / "experiments/contract-benchmark/spec.json"
LEDGER = ROOT / "docs/01-research/g1-convergence-ledger.json"
PACKAGES = {"P0-A", "P0-B", "P1-C", "P1-D", "P1-E"}


def main():
    w = json.loads(W.read_text())
    tc = json.loads(TC.read_text())
    ledger = json.loads(LEDGER.read_text())
    expected = {case["id"]: case for case in w["cases"] + tc["acceptance_tasks"]}
    assert len(w["cases"]) == 24 and len(tc["acceptance_tasks"]) == 18
    assert len(expected) == 42, "duplicate frozen IDs"
    actual = ledger["cases"]
    assert set(actual) == set(expected), f"missing={set(expected)-set(actual)}, extra={set(actual)-set(expected)}"
    assert ledger["gate"] == "NOT_PASSED"
    for case_id, entry in actual.items():
        frozen = expected[case_id]
        frozen_status = frozen.get("status", frozen.get("result"))
        assert entry["status"] == frozen_status == "NOT_RUN", case_id
        assert entry["package"] in PACKAGES, case_id
        assert len(entry["missing_full_acceptance"].strip()) > 9, case_id
        assert entry["partial_evidence"], case_id
        for path in entry["partial_evidence"]:
            assert path.startswith("docs/01-research/") and (ROOT / path).is_file(), (case_id, path)
    assert w["counts"] == {"total": 24, "passed": 0, "failed": 0, "not_run": 24}
    print("G1 NOT_PASSED: frozen W 0/24, TC 0/18 FULL PASS; 42/42 gaps and evidence paths checked")


if __name__ == "__main__":
    main()
