"""Build stale automation's full Pack from a PRE-HUMAN baseline.

The program's intention is ONLY to remove the amount column from a view.
It carries an unrelated old "title.label" attribute because it submits a full
snapshot. Tests reveal whether native Pack restore treats this as an overwrite.
"""
from __future__ import annotations
import argparse
import copy
import json
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    original=json.loads(Path(args.source).read_text(encoding="utf-8"))
    data=copy.deepcopy(original)
    assert any(field["name"]=="title" and field["label"]=="Title"
               for table in data["tables"] if table["name"]=="s1_contracts"
               for field in table["fields"]), "Unexpected baseline"
    target=next(v for v in data["views"] if v["name"]=="s1_contract_list")
    before=[col["field_name"] for col in target["configuration"]["columns"]]
    assert "amount_minor" in before
    target["configuration"]["columns"]=[
        item for item in target["configuration"]["columns"]
        if item["field_name"]!="amount_minor"]
    assert len(before)-len(target["configuration"]["columns"])==1
    Path(args.output).write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"intent":"view-only","removed_view_column":"amount_minor",
                      "carried_stale_title_label":"Title",
                      "payload_type":"full-admin-Pack-snapshot"},ensure_ascii=False))

if __name__=="__main__":
    main()
