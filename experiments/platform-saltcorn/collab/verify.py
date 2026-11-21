#!/usr/bin/env python3
"""Independent physical DB + native HTTP oracle for browser↔real LLM↔browser.

An expected stale conflict is a successful *negative-control observation*, not
evidence of globally safe native Saltcorn browser editing.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sqlite3
from urllib.request import urlopen

FIRST="Human First Saved"
SECOND="Human Second Saved"
TARGET="AI Reviewed Status"

def event(path):
    found=[]
    for line in Path(path).read_text(encoding="utf-8",errors="replace").splitlines():
        marker="S1_COLLAB_NATIVE_CAS|"
        # Saltcorn CLI also echoes JavaScript source that contains the marker.
        # Accept only actual emitted JSON events, not source-code snippets.
        if line.startswith(marker):
            found.append(json.loads(line[len(marker):]))
    if len(found)!=1:
        raise RuntimeError("NATIVE_CAS_LOG_EVENT_COUNT_NOT_ONE")
    return found[0]

def main():
    p=argparse.ArgumentParser()
    for x in ("db","first-human","proposal","applied-log","second-human","stale-log","output"):
        p.add_argument("--"+x,required=True)
    p.add_argument("--base",default="http://127.0.0.1:3100")
    p.add_argument("--live-model",action="store_true")
    a=p.parse_args()
    first=json.loads(Path(a.first_human).read_text(encoding="utf-8"))
    proposal=json.loads(Path(a.proposal).read_text(encoding="utf-8"))
    second=json.loads(Path(a.second_human).read_text(encoding="utf-8"))
    applied=event(a.applied_log)
    stale=event(a.stale_log)
    patch=proposal["patch"]
    checks=[]
    def check(i,ok,details):
        checks.append({"id":i,"status":"PASS" if ok else "FAIL","observed":details})
        print(i,"PASS" if ok else "FAIL",json.dumps(details,ensure_ascii=False),flush=True)
    with sqlite3.connect("file:"+str(Path(a.db).resolve())+"?mode=ro",uri=True) as db:
        rows=list(db.execute(
           "SELECT f.name,f.label FROM _sc_fields f "
           "JOIN _sc_tables t ON f.table_id=t.id "
           "WHERE t.name='s1_contracts' AND f.name IN ('title','status')"))
        final=dict(rows)
        contract=db.execute(
          "SELECT contract_no,amount_minor,status FROM s1_contracts "
          "WHERE contract_no='HT-2026-000001'").fetchone()
    check("COL01-real-first-human-browser",
          first.get("real_chromium") is True and first.get("result")=="PASS" and
          first.get("phase")=="first" and
          first.get("actual_csrf_and_context") is True and
          first.get("actual_field_wizard_post_count",0)>=1,
          {"native_post_count":first.get("actual_field_wizard_post_count"),
           "browser":first.get("real_chromium")})
    check("COL02-initial-physical-browser-state",
          first.get("before")=={"title":"Title","status":"Status"} and
          first.get("after")=={"title":FIRST,"status":"Status"},
          {"before":first.get("before"),"after":first.get("after")})
    check("COL03-real-model-source",
          proposal.get("model_inference_executed") is a.live_model and
          (not a.live_model or
            proposal.get("model")=="deepseek-flash" and
            proposal.get("model_calls")==1 and
            proposal.get("function_calls")==1),
          {"real_model":proposal.get("model_inference_executed"),
           "model_id":proposal.get("model"),
           "number_of_model_calls":proposal.get("model_calls")})
    check("COL04-model-reflected-current-human-title",
          patch.get("expected_title")==FIRST and
          patch.get("expected_status")=="Status",
          {"human_title_in_model_patch":patch.get("expected_title"),
           "target_initial_status":patch.get("expected_status")})
    check("COL05-strictly-scoped-model-patch",
          set(patch)=={"field","expected_title","expected_status","new_label"} and
          patch["field"]=="status" and patch["new_label"]==TARGET and
          proposal.get("research_scope",{}).get("model_has_write_tools") is False,
          {"patch_target":patch.get("field"),"new_label":patch.get("new_label"),
           "model_did_not_get_write_tools":True})
    check("COL06-first-agent-native-CAS-applied",
          applied.get("decision")=="APPLIED" and
          applied.get("native_write_attempted") is True and
          applied.get("title_observed")==FIRST and
          applied.get("status_observed")==TARGET,
          {"native_decision":applied})
    check("COL07-real-second-human-browser",
          second.get("real_chromium") is True and second.get("result")=="PASS" and
          second.get("phase")=="second" and
          second.get("actual_field_wizard_post_count",0)>=1,
          {"native_post_count":second.get("actual_field_wizard_post_count")})
    check("COL08-browser-did-not-lose-AI-modification",
          second.get("before")=={"title":FIRST,"status":TARGET} and
          second.get("after")=={"title":SECOND,"status":TARGET} and
          second.get("status_visible_in_real_browser_after_agent") is True,
          {"before":second.get("before"),"after":second.get("after"),
           "AI_label_visible_in_original_editor":
                second.get("status_visible_in_real_browser_after_agent")})
    check("COL09-stale-model-patch-blocked",
          stale.get("decision")=="STALE_REJECTED" and
          stale.get("native_write_attempted") is False,
          {"stale_decision":stale})
    check("COL10-stale-patch-observed-latest-human",
          stale.get("title_observed")==SECOND and
          stale.get("status_observed")==TARGET,
          {"latest_title":stale.get("title_observed"),
           "latest_target":stale.get("status_observed")})
    check("COL11-final-physical-human-label-preserved",
          final.get("title")==SECOND,{"final_title":final.get("title")})
    check("COL12-final-physical-AI-label-preserved",
          final.get("status")==TARGET,{"final_status":final.get("status")})
    check("COL13-existing-business-record-preserved",
          contract is not None and
          contract[0]=="HT-2026-000001" and contract[1]==100000001,
          {"record_present":contract is not None,"amount_minor":contract[1] if contract else None})
    for suffix in ("/api/s1_contracts/","/view/s1_contract_list"):
        try:
            with urlopen(a.base+suffix,timeout=12) as response:
                data=response.read(500000).decode("utf-8","replace")
                ok=response.status==200 and "HT-2026-000001" in data
                details={"http":response.status,"contract_no_present":"HT-2026-000001" in data}
        except Exception as e:
            ok=False;details={"error_type":type(e).__name__}
        check("COL14-runtime-"+suffix,ok,details)
    check("COL16-model-supplied-no-source-code",
          proposal.get("research_scope",{}).get("AI_generated_code") is False and
          proposal.get("research_scope",{}).get("native_editor_side_CAS_added") is False,
          {"AI_generated_code":False,"native_editor_still_unprotected":True})
    summary={"total":len(checks),"passed":sum(x["status"]=="PASS" for x in checks)}
    out={"study":"S1 real Chromium human edit → optional DeepSeek read-only patch → guarded native Field.update → Chromium second human edit",
         "platform":"actual Saltcorn CLI 1.7.0-beta.5 / real Chromium / SQLite",
         "model_inference_executed":proposal.get("model_inference_executed"),
         "model_id":proposal.get("model"),
         "model_calls":proposal.get("model_calls",0),
         "tokens":proposal.get("usage_tokens",{}),
         "native_CAS_security_scope":"AGENT_SIDE_ONLY; native browser editor remains bypass",
         "positive_roundtrip_supported":summary["passed"]==16,
         "cases":checks,"summary":summary,
         "G1":"NOT_PASSED",
         "frozen_contract_benchmark_full_pass":0}
    Path(a.output).write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("S1_COLLAB_RESULT|"+json.dumps({
        "real_model":out["model_inference_executed"],
        "passed":summary["passed"],"total":summary["total"],
        "native_editor_side_protected":False
    }),flush=True)
    return 0 if summary["total"]==16 and summary["passed"]==16 else 1

if __name__=="__main__":
    raise SystemExit(main())
