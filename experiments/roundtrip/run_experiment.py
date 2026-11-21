"""Generate deterministic, machine-readable evidence from independent scenarios."""
from __future__ import annotations
import argparse
import json
import platform
import time
from pathlib import Path
from cases import CASES
from engine import Store, naive_full_replace_loss


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", default="results.json", help="Path to report")
    args = p.parse_args()
    rows = []
    for design in ("A-unified-ir", "B-domain-manifest"):
        for name, case in CASES.items():
            store = Store(design)
            start = time.perf_counter_ns()
            try:
                case(store)
            except Exception as exc:
                status, error = "FAIL", f"{type(exc).__name__}: {exc}"
            else:
                status, error = "PASS", None
            rows.append({"design": design, "case": name, "status": status, "error": error,
                         "elapsed_ns": time.perf_counter_ns() - start,
                         "resource_count": len(store.resources()),
                         "final_revision": store.snapshot().revision,
                         "serialized_bytes": store.serialized_bytes()})
    negative = {"name": "stale-full-replace-loses-human-edit", "failure_reproduced": naive_full_replace_loss()}
    summary = {design: {"pass": sum(r["status"] == "PASS" for r in rows if r["design"] == design),
                        "total": sum(r["design"] == design for r in rows)}
               for design in ("A-unified-ir", "B-domain-manifest")}
    report = {"experiment": "OpenAILCAP H01/H03 model-only roundtrip spike",
              "scope": "in-memory deterministic simulator, NOT a real low-code runtime",
              "python": platform.python_version(),
              "platform": platform.platform(),
              "cases": rows, "summary": summary, "negative_control": negative,
              "limitations": ["No persisted database or crash recovery", "No application editor or runtime",
                              "No authentication boundary or real multi-user access", "No AI model was called",
                              "Shared merge algorithm; A/B compares representation, not full architectures"]}
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"summary": summary, "negative_control": negative,
                      "output": str(Path(args.output).resolve())}, ensure_ascii=False))
    return 0 if all(v["pass"] == v["total"] for v in summary.values()) and negative["failure_reproduced"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
