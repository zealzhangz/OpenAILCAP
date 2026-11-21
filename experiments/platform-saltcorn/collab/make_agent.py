#!/usr/bin/env python3
"""Compile only validated JSON patch data into a fixed, human-reviewed CLI.

The model cannot generate JavaScript, pick table names, or change actor ids.
"""
import argparse
import json
from pathlib import Path
from propose import validate_patch

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--proposal",required=True)
    p.add_argument("--template",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    result=json.loads(Path(a.proposal).read_text(encoding="utf-8"))
    snapshot={
      "title_label":result["original_native_snapshot"]["title"],
      "status_label":result["original_native_snapshot"]["status"]
    }
    patch=validate_patch(result["patch"],snapshot)
    if result["research_scope"]["model_has_write_tools"] is not False:
        raise ValueError("UNSAFE_MODEL_WRITE_TOOL_EXPOSURE")
    code=Path(a.template).read_text(encoding="utf-8")
    sentinel="__VERIFIED_LABEL_PATCH_JSON__"
    if code.count(sentinel)!=1:
        raise ValueError("TEMPLATE_REPLACEMENT_NOT_UNIQUE")
    code=code.replace(sentinel,json.dumps(patch,ensure_ascii=True))
    Path(a.output).write_text(code,encoding="utf-8")
    print("S1_COLLAB_AGENT_SCRIPT|"+json.dumps({
      "model_supplied_source_code":False,
      "approved_fields":["status"],
      "requires_guard_for_all_observed_fields":True
    }))

if __name__=="__main__":
    main()
