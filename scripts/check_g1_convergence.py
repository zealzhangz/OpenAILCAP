#!/usr/bin/env python3
"""Strict G1 ledger audit against immutable frozen W/TC registration.

Frozen specs are historic NOT_RUN registrations, NOT the live results.
Live statuses can advance ONLY if a *specifically registered* independent
verdict + real CI provenance exists. This deliberately recognizes formal
W20 only; new cases require a new independent judge AND reviewer change,
not a status rename or local count inflation.
"""
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
W=ROOT/"docs/01-research/g1-b01-acceptance-cases.json"
TC=ROOT/"experiments/contract-benchmark/spec.json"
LEDGER=ROOT/"docs/01-research/g1-convergence-ledger.json"
PACKAGES={"P0-A","P0-B","P1-C","P1-D","P1-E"}
# NO catch-all policy: each formally accepted case needs independently
# reviewed, exactly frozen-oracle-specific judgement criteria.
REGISTERED_FORMAL={
    "W20":{
        "verdict":"docs/01-research/g1-w20-formal-verdict.json",
        "validator":"scripts/verify_g1_w20.py",
        "report":"docs/01-research/61-g1-w20-real-external-unknown-formal-acceptance.md",
        "required_oracles":{
            "B2AuthenticatedChromiumWorkflow",
            "B2AuthorityPhysicalSQLAndKernelJournal",
            "B11NativePhysicalCursorAndReceipts",
            "seventhExternalOSUidPhysicalBusinessSQL",
            "actualExternalHTTPRequestTimedOutAfterCommit",
            "externalReceiptHTTPAndPhysicalSQLCrossChecked",
            "sameChangeIdNoExtraPost",
            "negativeCredentialAndPayloadReplay"
        }
    }
}


def verify_formal(case_id,entry):
    if case_id not in REGISTERED_FORMAL:
        raise AssertionError(
            "UNREVIEWED_FORMAL_STATUS_"+case_id)
    fixed=REGISTERED_FORMAL[case_id]
    data=entry.get("full_acceptance")
    if not isinstance(data,dict) or set(data)!={
        "verdict","validator","report","ci_run_url",
        "artifact_id","source_commit"}:
        raise AssertionError("FULL_EVIDENCE_SCHEMA_"+case_id)
    for key in ("verdict","validator","report"):
        if data[key]!=fixed[key] or not (ROOT/data[key]).is_file():
            raise AssertionError("FORMAL_EVIDENCE_PATH_"+case_id)
    if (not isinstance(data["artifact_id"],int) or
        data["artifact_id"]<1 or
        not isinstance(data["source_commit"],str) or
        not re.fullmatch(r"[0-9a-f]{40}",data["source_commit"]) or
        not isinstance(data["ci_run_url"],str) or
        not re.fullmatch(
            r"https://github\.com/zealzhangz/OpenAILCAP/actions/runs/[0-9]+",
            data["ci_run_url"])):
        raise AssertionError("FORMAL_CI_PROVENANCE_"+case_id)
    verdict=json.loads((ROOT/fixed["verdict"]).read_text())
    if (verdict.get("test_id")!=case_id or
        verdict.get("status")!="PASS" or
        verdict.get("G1Passed") is not False or
        verdict.get("W01_24AllPass") is not False or
        verdict.get("source_code_commit")!=data["source_commit"] or
        verdict.get("ci_run_url")!=data["ci_run_url"] or
        verdict.get("artifact_id")!=data["artifact_id"] or
        verdict.get("verifier")!=fixed["validator"] or
        not re.fullmatch(r"p0bnotify_[a-f0-9]{40}",
                         verdict.get("external_effect_change_id",""))):
        raise AssertionError("FORMAL_VERDICT_PROVENANCE_"+case_id)
    got=verdict.get("independent_real_oracles")
    if not isinstance(got,dict) or set(got)!=fixed["required_oracles"]:
        raise AssertionError("FORMAL_ORACLES_MISSING_"+case_id)
    if any(v is not True for k,v in got.items()
           if k!="seventhExternalOSUidPhysicalBusinessSQL") or (
        type(got["seventhExternalOSUidPhysicalBusinessSQL"]) is not int or
        got["seventhExternalOSUidPhysicalBusinessSQL"]<=0):
        raise AssertionError("FORMAL_ORACLES_NOT_PROVEN_"+case_id)
    if fixed["report"] not in entry.get("partial_evidence",[]):
        raise AssertionError("FORMAL_REPORT_NOT_LINKED_"+case_id)


def main():
    w=json.loads(W.read_text())
    tc=json.loads(TC.read_text())
    ledger=json.loads(LEDGER.read_text())
    expected={case["id"]:case for case in w["cases"]+tc["acceptance_tasks"]}
    assert len(w["cases"])==24 and len(tc["acceptance_tasks"])==18
    assert len(expected)==42,"duplicate frozen case IDs"
    actual=ledger["cases"]
    assert set(actual)==set(expected),(
        f"missing={set(expected)-set(actual)}, extra={set(actual)-set(expected)}")
    assert ledger["basis"]==[
        "docs/01-research/g1-b01-acceptance-cases.json",
        "experiments/contract-benchmark/spec.json"
    ]
    assert ledger["gate"]=="NOT_PASSED" # G1 cannot yet pass, 41 cases unrun.
    passed=[]
    for case_id,entry in actual.items():
        frozen=expected[case_id]
        # The ORIGINAL preregistered definition stays immutable.
        assert frozen.get("status",frozen.get("result"))=="NOT_RUN",case_id
        assert entry["package"] in PACKAGES,case_id
        assert entry["partial_evidence"],case_id
        for path in entry["partial_evidence"]:
            assert path.startswith("docs/01-research/"),(case_id,path)
            assert (ROOT/path).is_file(),(case_id,path)
        status=entry["status"]
        if status=="NOT_RUN":
            assert len(entry["missing_full_acceptance"].strip())>9,case_id
            assert "full_acceptance" not in entry,case_id
        elif status=="PASS":
            verify_formal(case_id,entry)
            passed.append(case_id)
            assert not entry["missing_full_acceptance"],case_id
        else:
            raise AssertionError("UNREVIEWED_STATUS_"+case_id+":"+str(status))
    # Original W registration counts stay fixed historical evidence.
    assert w["counts"]=={"total":24,"passed":0,"failed":0,"not_run":24}
    assert passed==["W20"],f"unexpected formal pass list {passed}"
    assert sum(1 for x in actual if x.startswith("TC") and
               actual[x]["status"]=="PASS")==0
    print("G1 NOT_PASSED: frozen registrations W24/TC18 unchanged; "
          "formal accepted W 1/24 (W20), TC 0/18; "
          "41 NOT_RUN with independent W20 provenance validated")


if __name__=="__main__":
    main()
