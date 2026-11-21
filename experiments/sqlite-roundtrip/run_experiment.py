"""Run independent acceptance tests and emit machine-readable S1 evidence."""
from __future__ import annotations

import argparse
import io
import json
import os
import platform
import sqlite3
import sys
import time
import unittest
from pathlib import Path


class RecordingResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records: list[dict] = []
        self._started: dict[str, float] = {}

    def startTest(self, test):
        self._started[test.id()] = time.perf_counter()
        super().startTest(test)

    def _record(self, test, status, message=None):
        self.records.append({"test_id": test.id(), "status": status,
                             "duration_ms": round((time.perf_counter() - self._started[test.id()]) * 1000, 3),
                             "error": message})

    def addSuccess(self, test):
        super().addSuccess(test)
        self._record(test, "PASS")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._record(test, "FAIL", self._exc_info_to_string(err, test))

    def addError(self, test, err):
        super().addError(test, err)
        self._record(test, "ERROR", self._exc_info_to_string(err, test))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._record(test, "SKIP", reason)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="results.json")
    args = parser.parse_args()
    suite = unittest.defaultTestLoader.discover("tests", pattern="test_*.py")
    stream = io.StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=RecordingResult)
    started = time.perf_counter()
    result = runner.run(suite)
    log = stream.getvalue()
    print(log, end="")
    data = {
        "experiment": "OpenAILCAP S1 H01/H03 persistent SQLite governed-edit spike",
        "scope": "SQLite file-backed application resource model, NOT a real low-code platform",
        "environment": {"python": platform.python_version(), "sqlite": sqlite3.sqlite_version,
                        "platform": platform.platform(), "github_sha": os.getenv("GITHUB_SHA")},
        "summary": {"total": result.testsRun, "passed": len([r for r in result.records if r["status"] == "PASS"]),
                    "failures": len(result.failures), "errors": len(result.errors),
                    "skipped": len(result.skipped), "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                    "status": "PASS" if result.wasSuccessful() else "FAIL"},
        "tests": result.records,
        "limitations": ["No API gateway authentication; actor is supplied by trusted caller",
                        "No actual low-code editor / server deployment",
                        "No actual AI model or untrusted code execution",
                        "SQLite process-transaction durability only; no distributed transactions",
                        "No production workload or performance benchmark"],
    }
    Path(args.output).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
