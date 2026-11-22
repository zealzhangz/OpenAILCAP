#!/usr/bin/env python3
"""Independent strict G1 W20 external-UNKNOWN evidence judge.

Does not import B2 SchemaStore, the external effect service, dispatcher,
P0-B runtime implementation, or rely on G1 partial integration counts.
Consumes a *real same-process* CI artifact emitted by actual Chromium,
two OS-owned SQLite databases, B11/NATIVE and HTTP external receipt oracles.
This judges precisely frozen W20, NOT TC16 or overall G1.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

IDS=[
    "P0B-44-independent-external-business-DB-and-least-privilege",
    "P0B-45-real-B2-Chromium-workflow-update-B11-Native-publication",
    "P0B-46-real-external-SQL-effect-committed-before-HTTP-timeout",
    "P0B-47-external-receipt-exact-changeId-confirms-UNKNOWN-once",
    "P0B-48-W20-independent-B2-B11-external-oracles-no-side-effect-replay",
]


def judge(document):
    checks=document.get("checks")
    if not isinstance(checks,list):
        raise AssertionError("W20_CHECKS_MISSING")
    relevant=[c for c in checks if c.get("id") in IDS]
    if (len(relevant)!=5 or
        [c["id"] for c in relevant]!=IDS or
        any(c.get("status")!="PASS" for c in relevant)):
        raise AssertionError("W20_FIVE_REAL_TESTS_NOT_PASS")
    a,b,c,d,e=[x["observed"] for x in relevant]
    if (type(a.get("externalUid")) is not int or
        a["externalUid"]<=0 or
        a.get("physicalInitialEffects")!=0 or
        set(a.get("KernelPublisherConsumerPluginDenied",{}).values())!={"DENIED"} or
        a.get("externalNoDomainWriteGrant") is not True):
        raise AssertionError("W20_INDEPENDENT_BUSINESS_OWNER_UNPROVED")
    if (b.get("authenticatedB2WorkflowHTTP")!=200 or
        b.get("workflowRecordVersion")!=2 or
        b.get("workflowStatus")!="PendingLevel1" or
        b.get("trueB11OutboxHead")!=b.get("durableNativeCursor") or
        b.get("autoPublisherActivationEpoch")!=7 or
        b.get("sameB17BrowserRows")!=8):
        raise AssertionError("W20_NOT_SAME_REAL_BUSINESS_WORKFLOW")
    cid=c.get("originalChangeId")
    if (not isinstance(cid,str) or
        not re.fullmatch(r"p0bnotify_[0-9a-f]{40}",cid) or
        c.get("actualExternalHTTPClient")!="Kernel UID" or
        c.get("clientObserved")!="UNKNOWN_AFTER_TIMEOUT" or
        c.get("physicallyCommittedExternalBusinessEffects")!=1 or
        c.get("physicallyCommittedExternalReceipts")!=1 or
        c.get("B2Journal")!="UNKNOWN" or
        c.get("distinctExternalHTTPResult")!=200):
        raise AssertionError("W20_REAL_EXTERNAL_UNKNOWN_EFFECT_UNPROVED")
    if (d.get("B2Reconciliation")!="CONFIRMED" or
        d.get("outboundAttempts")!=1 or
        d.get("externalEffectCountAfterRetry")!=1 or
        d.get("externalReceiptCountAfterRetry")!=1 or
        d.get("unauthorizedReceiptHTTP")!=401 or
        d.get("changedPayloadSameChangeIdHTTP")!=409 or
        d.get("noOtherAppEffect") is not True):
        raise AssertionError("W20_CHANGE_ID_OR_REPLAY_UNVERIFIED")
    if (e.get("originalB2RecordVersion")!=2 or
        e.get("originalB2WorkflowStatus")!="PendingLevel1" or
        e.get("B11NativeReceiptCursor")!=9 or
        e.get("externalCommittedBusinessId")!=cid or
        e.get("externalResponseWasTimeout") is not True or
        e.get("B2OriginalChangeIdReceipt")!="CONFIRMED" or
        e.get("autoRetryCount")!=0):
        raise AssertionError("W20_INDEPENDENT_RECONCILIATION_INCOMPLETE")
    return {"test_id":"W20","status":"PASS",
            "frozen_expected":"remote execution timeout UNKNOWN; query actual "
                              "side effect and receipt by original changeId, "
                              "no new-ID blind replay",
            "external_effect_change_id":cid,
            "independent_real_oracles":{
                "B2AuthenticatedChromiumWorkflow":True,
                "B2AuthorityPhysicalSQLAndKernelJournal":True,
                "B11NativePhysicalCursorAndReceipts":True,
                "seventhExternalOSUidPhysicalBusinessSQL":a["externalUid"],
                "actualExternalHTTPRequestTimedOutAfterCommit":True,
                "externalReceiptHTTPAndPhysicalSQLCrossChecked":True,
                "sameChangeIdNoExtraPost":True,
                "negativeCredentialAndPayloadReplay":True},
            "G1Passed":False,
            "W01_24AllPass":False}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--evidence",required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    result=judge(json.loads(Path(args.evidence).read_text()))
    Path(args.output).write_text(json.dumps(result,indent=2)+"\n")
    print("G1_W20_FORMAL|"+json.dumps(result,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
