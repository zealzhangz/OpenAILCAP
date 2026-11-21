#!/usr/bin/env python3
"""Generate a SAFE native CLI fixture runner from a validated model route list.

The model provides ENUMS only; code/Pack/fixtures are human-reviewed and fixed.
"""
import argparse
import json
from pathlib import Path
from predict import validate_choices

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--spec",required=True)
    p.add_argument("--prediction",required=True)
    p.add_argument("--template",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    spec=json.loads(Path(a.spec).read_text(encoding="utf-8"))
    prediction=json.loads(Path(a.prediction).read_text(encoding="utf-8"))
    if prediction.get("study_id")!=spec["id"]:
        raise ValueError("PREDICTION_SPEC_MISMATCH")
    validate_choices(spec,prediction)
    routes={c["id"]:c["mode"] for c in prediction["choices"]}
    fixtures=[{"id":case["id"],"mode":routes[case["id"]],
               "fixture":case["fixture"]} for case in spec["cases"]]
    body=Path(a.template).read_text(encoding="utf-8")
    sentinel="__FROZEN_EXECUTION_CASES_JSON__"
    if body.count(sentinel)!=1:
        raise ValueError("EXECUTOR_TEMPLATE_SENTINEL_COUNT")
    body=body.replace(sentinel,json.dumps(fixtures,ensure_ascii=True))
    Path(a.output).write_text(body,encoding="utf-8")
    print("S1_ROUTE_EXECUTOR_GENERATED|"+json.dumps({
      "case_count":len(fixtures),"selected_modes":routes,
      "model_generated_code":False,"safety":"allowlisted native adapters only"
    },ensure_ascii=False))

if __name__=="__main__":main()
