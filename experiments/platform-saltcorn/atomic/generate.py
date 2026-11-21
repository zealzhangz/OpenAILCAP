"""Generate parameterized real Saltcorn CLI workers from trusted fixed scenarios."""
import argparse
import json
from pathlib import Path

SCENARIOS = {
    "d-title": ("title", 0, "Human Checked", False),
    "d-status": ("status", 0, "Automation Checked", False),
    "c-alpha": ("title", 1, "Writer Alpha", False),
    "c-beta": ("title", 1, "Writer Beta", False),
    "f-title": ("title", 2, "INJECTED_INVALID", True),
    "b-status": ("status", 1, "Unaware Agent", False),
}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", required=True)
    a = p.parse_args()
    dest = Path(a.output_dir)
    dest.mkdir(parents=True, exist_ok=True)
    template = Path(__file__).with_name("work-template.js").read_text(encoding="utf-8")
    assert template.count("__CFG__") == 2 or template.count("__CFG__") == 1
    for name, (field, expected, value, inject) in SCENARIOS.items():
        cfg = dict(id=name, field=field, expected_revision=expected, value=value,
                   fail_after_model_write=inject)
        # Only use the exact substitution on the JS assignment line, not the comment.
        source = template.replace("const cfg = __CFG__;",
                                  "const cfg = " + json.dumps(cfg, ensure_ascii=False) + ";")
        assert "const cfg = __CFG__;" not in source
        (dest / (name + ".js")).write_text(source, encoding="utf-8")
    print(json.dumps({"scenario_count": len(SCENARIOS),
                      "names": list(SCENARIOS.keys())}, ensure_ascii=False))

if __name__ == "__main__":
    main()
