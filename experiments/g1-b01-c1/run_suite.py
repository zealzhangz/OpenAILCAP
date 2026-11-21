"""Emit independent C1-prefight observations; do not alter frozen W01-W24 status."""
import json
import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

import test_service


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


def main():
    tests = unittest.defaultTestLoader.loadTestsFromModule(test_service)
    ids = [case.id() for case in flatten(tests)]
    result = unittest.TextTestRunner(verbosity=2).run(tests)
    failures = {t.id(): msg for t, msg in result.failures}
    errors = {t.id(): msg for t, msg in result.errors}
    observations = {
        "stage": "S1",
        "scope": "C1_STANDALONE_RESEARCH_SERVICE_NOT_SALTCORN_NATIVE",
        "not_a_g1_w01_w24_result": True,
        "model_inference_executed": False,
        "github_sha": os.getenv("GITHUB_SHA"),
        "tested_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_count": result.testsRun,
        "pass_count": result.testsRun - len(failures) - len(errors)
                      - len(result.skipped),
        "fail_count": len(failures),
        "error_count": len(errors),
        "skip_count": len(result.skipped),
        "tests": [
            {"test": key,
             "status": "ERROR" if key in errors else
                       "FAIL" if key in failures else
                       "SKIP" if key in {test.id() for test, _ in result.skipped}
                       else "PASS"}
            for key in ids
        ],
    }
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("c1-observations.json")
    out.write_text(json.dumps(observations, indent=2, ensure_ascii=False) + "\n")
    print("C1_PREFLIGHT_RESULT", json.dumps(
        {k: observations[k] for k in
         ("scope", "run_count", "pass_count", "fail_count", "error_count")},
        sort_keys=True,
    ))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
