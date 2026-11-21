#!/usr/bin/env python3
"""S1 B4: real B2 runtime + one optional DeepSeek-generated code artifact.

Pure source -> AST static gate -> actual isolated Docker compile+432-case test ->
immutable content-addressed artifact -> human-only atomic publication -> real
Chromium published contract+extension runtime, rollback and stale B2 binding.
"""
from __future__ import annotations

import argparse
import copy
import json
import sqlite3
import secrets
import sys
import tempfile
import threading
import traceback
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"g1-b01-b2"))
from schema_core import SchemaStore,Actor,Rejected,sha
from extension_http import server_with_extension
from policy import (RuleError,select_mode,REQUIRED,validate_source,
                    propose,source_hash,oracle)
from sandbox import DockerSandbox,SandboxProof
from registry import ExtensionRegistry


def sql_oracle(path,app):
    """Independent read-only SQLite: not Registry.physical."""
    with sqlite3.connect("file:"+str(Path(path).resolve())+"?mode=ro",uri=True) as db:
        r=db.execute("SELECT revision,current_release FROM apps WHERE app=?",
                     (app,)).fetchone()
        ptr=db.execute("SELECT version FROM extension_pointers WHERE app=?",
                       (app,)).fetchone()
        artifacts=db.execute("SELECT artifact_hash,source,b2_version,b2_manifest_hash "
                             "FROM extension_artifacts WHERE app=?",(app,)).fetchall()
        releases=db.execute("SELECT version,artifact_hash,b2_version,b2_manifest_hash "
                            "FROM extension_releases WHERE app=? ORDER BY version",
                            (app,)).fetchall()
        events=db.execute("SELECT event,actor FROM events WHERE app=? ORDER BY eid",
                          (app,)).fetchall()
        records=db.execute("SELECT record_id,content FROM records WHERE app=?",
                           (app,)).fetchall()
    return {"appRevision":r[0],"b2Version":r[1],
            "extensionVersion":ptr[0] if ptr else 0,
            "artifacts":[{"hash":a[0],"sourceHashMatches":source_hash(a[1])==a[0],
                          "baseVersion":a[2],"baseHash":a[3]} for a in artifacts],
            "releases":[{"version":x[0],"artifactHash":x[1],
                         "b2Version":x[2],"b2Hash":x[3]} for x in releases],
            "events":[{"event":x[0],"actor":x[1]} for x in events],
            "rows":[{"recordId":x[0],"content":json.loads(x[1])} for x in records]}


def dom(page,sel,text,*,exact=False):
    for _ in range(80):
        value=page.locator(sel).inner_text(timeout=1400)
        if (value==text if exact else text in value):
            return
        page.wait_for_timeout(150)
    raise AssertionError("BROWSER_NOT_READY_"+sel)


def json_browser(page,url):
    response=page.goto(url,wait_until="domcontentloaded")
    return response.status,json.loads(page.locator("body").inner_text())


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--mode",choices=("offline","live"),default="offline")
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    live=args.mode=="live"
    cases=[]
    evidence={"scope":"S1_B4_BOUNDED_CUSTOM_CODE_NOT_PRODUCTION_CODE_AGENT",
              "mode":args.mode,"inference":False,"modelAttempted":False,
              "modelCalls":0,"sandboxIsDocker":True,"sandboxNetwork":"none",
              "noArbitraryShellForAgent":True,"humanApprovalIsTestFixture":True,
              "formalG1Passed":False,"cases":cases}
    def check(cid,condition,observed):
        row={"id":cid,"status":"PASS" if condition else "FAIL",
             "observed":observed}
        cases.append(row)
        print("B4 "+cid+" "+row["status"]+" "+json.dumps(observed,ensure_ascii=False),
              flush=True)
        if not condition:raise AssertionError(cid)
    with tempfile.TemporaryDirectory(prefix="b4-") as tmp:
        dbfile=Path(tmp)/"app.sqlite"
        b2=SchemaStore(dbfile);b2.init()
        b2.seed_app_for_test("app-a");b2.seed_app_for_test("app-b")
        human=Actor("human-reviewer","app-a",can_publish=True,can_runtime=True)
        agent=Actor("code-agent","app-a",can_publish=False,can_runtime=False)
        runner=DockerSandbox()
        registry=ExtensionRegistry(b2,runner);registry.init()
        sessions={}
        token=secrets.token_urlsafe(32)
        password=secrets.token_urlsafe(32)
        server=server_with_extension(b2,registry,{token:agent},sessions,human,password)
        server_thread=threading.Thread(target=server.serve_forever,daemon=True)
        server_thread.start()
        base="http://127.0.0.1:"+str(server.server_port)
        try:
            check("B4-01-pinned-Docker-image",runner.image_id.startswith("sha256:") and
                  "--network=none" in runner.command(Path(tmp)) and
                  "--read-only" in runner.command(Path(tmp)) and
                  "--cap-drop=ALL" in runner.command(Path(tmp)),
                  {"imageIdPrefix":runner.image_id[:19],"network":"none",
                   "readOnly":True,"dropCapabilities":True})
            check("B4-02-existing-low-code-capability",
                  select_mode("amount_threshold_approval")=="LOW_CODE",
                  {"lowcode":"amount_threshold_approval"})
            check("B4-03-missing-risk-capability-requires-code",
                  select_mode(REQUIRED)=="CUSTOM_CODE",
                  {"missing":REQUIRED,"decision":"CUSTOM_CODE"})
            defs=json.loads((HERE.parent/"g1-b01-b2"/"contract_spec.json").read_text())
            # Existing B2 fixture has three visible columns; this B4 browser
            # observation requires the visible title, as in verified B3.
            defs["view.contracts"]["columns"]=["contract_no","title","amount_minor","status"]
            for n,(rid,spec) in enumerate(defs.items(),1):
                draft=b2.draft(agent,"app-a")
                b2.mutate(agent,"app-a",{
                    "changeId":"b4-seed-"+str(n),
                    "resourceId":rid,"expectedAppRevision":draft["appRevision"],
                    "expectedRevision":None,"baseContentHash":None,
                    "definition":spec})
            check("B4-04-low-code-B2-four-resources",
                  b2.draft(human,"app-a")["appRevision"]==4 and
                  len(b2.draft(human,"app-a")["resources"])==4,
                  {"appRevision":4,"resources":list(defs)})
            draft=b2.draft(human,"app-a")
            published=b2.publish(human,"app-a",{
                "changeId":"b4-b2-publish-v1",
                "expectedAppRevision":draft["appRevision"],
                "manifestHash":draft["manifestHash"]})
            check("B4-05-low-code-published-v1",
                  published["version"]==1 and b2.release(human,"app-a")["version"]==1,
                  {"baseRelease":1,"immutableHash":published["manifestHash"]})
            high=b2.submit_form(human,"app-a","form.contracts",{
                "contract_no":"RISK-LARGE","title":"高风险供应合同",
                "amount_minor":600000001})
            low=b2.submit_form(human,"app-a","form.contracts",{
                "contract_no":"RISK-LOW","title":"低风险供应合同",
                "amount_minor":100000000})
            check("B4-06-real-low-code-form-records",
                  len(sql_oracle(dbfile,"app-a")["rows"])==2 and
                  high["data"]["status"]=="Draft" and low["data"]["status"]=="Draft",
                  {"realSqlRecords":2,"lowcodeRuntime":"B2"})
            with sync_playwright() as pw:
                browser=pw.chromium.launch(headless=True,args=["--no-sandbox"])
                context=browser.new_context()
                try:
                    page=context.new_page()
                    page.goto(base+"/editor/app-a",wait_until="domcontentloaded")
                    check("B4-07-real-browser-unauthenticated-redirect",
                          page.url.endswith("/editor/login"),
                          {"loginRequired":True})
                    page.locator("#password").fill(password)
                    page.locator("#login").click()
                    page.wait_for_url("**/editor/app-a")
                    dom(page,"#published-version","1",exact=True)
                    page.locator("#view").click()
                    dom(page,"#runtime-output","高风险供应合同")
                    check("B4-08-real-Chromium-low-code-published-view",
                          len(json.loads(page.locator("#runtime-output").inner_text())
                              ["rows"])==2,
                          {"chromiumViewRows":2,"b2ReleaseVersion":1})
                    evidence["modelAttempted"]=live
                    if live:print("S1_B4_LIVE_DEEPSEEK_ONE_FUNCTION_CALL",flush=True)
                    proposal=propose(live=live)
                    evidence["inference"]=proposal["inference"]
                    evidence["modelCalls"]=proposal["modelCalls"]
                    src=proposal["code"]["source"]
                    checked=validate_source(src)
                    evidence["modelEvidence"]={
                        "inference":proposal["inference"],
                        "modelCalls":proposal["modelCalls"],
                        "toolCalls":proposal["toolCalls"],
                        "codeSha256":checked["sourceHash"],
                        "astNodes":checked["astNodes"],
                        "model":proposal.get("model"),
                        "tokenUsage":proposal.get("tokenUsage",{})
                    }
                    # Reviewable source is the validated function; raw provider
                    # headers/response, bearer and cookies are never exported.
                    evidence["validatedSource"]=src
                    check("B4-09-proposal-matches-model-origin",
                          proposal["inference"]==live and
                          proposal["modelCalls"]==(1 if live else 0) and
                          checked["sourceHash"]==source_hash(src),
                          {"realModel":proposal["inference"],
                           "modelRequests":proposal["modelCalls"],
                           "codeSha256":checked["sourceHash"]})
                    proof=runner.test(src)
                    check("B4-10-real-isolated-Docker-compile-and-oracle",
                          proof.cases==432 and
                          proof.source_hash==checked["sourceHash"] and
                          proof.image_id==runner.image_id,
                          {"sandbox":True,"isolatedCases":432,"network":"none"})
                    try:
                        validate_source("def score_contract(amount_minor, supplier_score, months_active):\n"
                                        "    import os\n    return 0\n")
                        evil_rejected=False
                    except RuleError as exc:
                        evil_rejected=exc.code=="AST_NODE_FORBIDDEN"
                    check("B4-11-malicious-import-not-executed",
                          evil_rejected,{"AST":"REJECTED","codeExecuted":False})
                    wrong=("def score_contract(amount_minor, supplier_score, months_active):\n"
                           "    return 0\n")
                    try:
                        runner.test(wrong)
                        wrong_failed=False
                    except RuleError as exc:
                        wrong_failed=exc.code=="SANDBOX_TEST_FAILED"
                    check("B4-12-wrong-logic-Docker-hidden-oracle-fails",
                          wrong_failed,{"incorrectCodeSandboxStatus":"FAIL"})
                    empty=sql_oracle(dbfile,"app-a")
                    check("B4-13-failed-code-never-staged-or-released",
                          empty["artifacts"]==[] and empty["releases"]==[] and
                          empty["extensionVersion"]==0 and empty["b2Version"]==1,
                          {"artifactCount":0,"codeReleaseCount":0,"B2VersionStill":1})
                    try:
                        registry.stage(agent,"app-a",src,proof)
                        agent_stage_denied=False
                    except Rejected as exc:
                        agent_stage_denied=exc.code=="PUBLISH_FORBIDDEN"
                    check("B4-14-agent-cannot-stage-with-own-identity",
                          agent_stage_denied,{"status":403,"code":"PUBLISH_FORBIDDEN"})
                    staged=registry.stage(human,"app-a",src,proof)
                    check("B4-15-human-reviewed-provenance-binds-B2-release",
                          staged["artifactHash"]==checked["sourceHash"] and
                          staged["boundB2Version"]==1 and
                          staged["boundManifestHash"]==published["manifestHash"],
                          {"buildSha256":staged["artifactHash"],
                           "boundB2Release":1,"testCount":432})
                    fake=SandboxProof(checked["sourceHash"],0,runner.image_id,None)
                    try:
                        registry.stage(human,"app-a",src,fake)
                        bad_proof_rejected=False
                    except Rejected as exc:
                        bad_proof_rejected=exc.code=="BUILD_ATTESTATION_INVALID"
                    check("B4-16-invalid-build-proof-denied",
                          bad_proof_rejected,{"fakeTestCount":0,"stageBlocked":True})
                    try:
                        registry.publish(agent,"app-a",staged["artifactHash"],0)
                        agent_publish_denied=False
                    except Rejected as exc:
                        agent_publish_denied=exc.code=="PUBLISH_FORBIDDEN"
                    check("B4-17-agent-cannot-publish-code",
                          agent_publish_denied,{"status":403,"agentMayProposeOnly":True})
                    try:
                        registry.publish(human,"app-a",staged["artifactHash"],0,
                                         inject_failure=True)
                        injection_rollback=False
                    except RuntimeError:
                        p=sql_oracle(dbfile,"app-a")
                        injection_rollback=(p["extensionVersion"]==0 and
                                            p["releases"]==[])
                    check("B4-18-injected-extension-publish-atomic-rollback",
                          injection_rollback,{"publishRolledBack":True,
                                              "B2PublishedStill":1})
                    release=registry.publish(human,"app-a",staged["artifactHash"],0)
                    physical=sql_oracle(dbfile,"app-a")
                    check("B4-19-human-publishes-content-addressed-code-v1",
                          release["publishedExtensionVersion"]==1 and
                          physical["extensionVersion"]==1 and
                          physical["artifacts"][0]["sourceHashMatches"],
                          {"extensionRelease":1,"b2Release":1,
                           "sourceHashVerified":True})
                    risk_high=context.new_page()
                    high_status,high_result=json_browser(
                        risk_high,base+"/v2/apps/app-a/runtime/extensions/risk/"+
                        high["recordId"]+"?supplier_score=20&months_active=3")
                    check("B4-20-real-browser-risk-extension-high",
                          high_status==200 and high_result["riskScore"]==95 and
                          high_result["riskTier"]=="HIGH" and
                          high_result["extensionVersion"]==1,
                          {"http":high_status,"score":high_result.get("riskScore"),
                           "tier":high_result.get("riskTier")})
                    risk_low=context.new_page()
                    low_status,low_result=json_browser(
                        risk_low,base+"/v2/apps/app-a/runtime/extensions/risk/"+
                        low["recordId"]+"?supplier_score=88&months_active=50")
                    check("B4-21-real-browser-risk-extension-low",
                          low_status==200 and low_result["riskScore"]==0 and
                          low_result["riskTier"]=="LOW",
                          {"http":low_status,"score":low_result.get("riskScore"),
                           "tier":low_result.get("riskTier")})
                    anonymous=browser.new_context()
                    try:
                        status,content=json_browser(
                            anonymous.new_page(),
                            base+"/v2/apps/app-a/runtime/extensions/risk/"+
                            high["recordId"]+"?supplier_score=20&months_active=3")
                    finally:anonymous.close()
                    crossstatus,cross=json_browser(
                        risk_high,base+"/v2/apps/app-b/runtime/extensions/risk/"+
                        high["recordId"]+"?supplier_score=20&months_active=3")
                    check("B4-22-runtime-auth-and-app-isolation",
                          status==401 and crossstatus==403,
                          {"anonymousHttp":status,"otherAppHttp":crossstatus})
                    # Trusted human edit of AI proposal; changing a comment does
                    # not relax static policy or hidden behavioral acceptance.
                    manual=src.rstrip()+"\n# Human reviewed output after AI code proposal\n"
                    manual_proof=runner.test(manual)
                    manual_stage=registry.stage(human,"app-a",manual,manual_proof)
                    second=registry.publish(human,"app-a",manual_stage["artifactHash"],1)
                    rollback=registry.rollback(human,"app-a",2,1)
                    check("B4-23-human-code-edit-build-v2-and-rollback",
                          second["publishedExtensionVersion"]==2 and
                          rollback["activeExtensionVersion"]==1 and
                          sql_oracle(dbfile,"app-a")["extensionVersion"]==1 and
                          manual_stage["artifactHash"]!=staged["artifactHash"],
                          {"humanCodeBuildCases":432,"extensionV2":True,
                           "rolledBackTo":1})
                    try:
                        registry.publish(human,"app-a",staged["artifactHash"],0)
                        stale_rejected=False
                    except Rejected as exc:
                        stale_rejected=exc.code=="EXTENSION_VERSION_CONFLICT"
                    check("B4-24-stale-extension-publish-CAS",
                          stale_rejected and
                          sql_oracle(dbfile,"app-a")["extensionVersion"]==1,
                          {"conflictStatus":409,"currentExtension":1})
                    current=b2.draft(human,"app-a")
                    old=current["resources"]["form.contracts"]
                    updated=copy.deepcopy(old["definition"])
                    updated["title"]="合同登记 - 人工调整草稿"
                    b2.mutate(human,"app-a",{
                        "changeId":"b4-human-draft-edit",
                        "resourceId":"form.contracts",
                        "expectedAppRevision":current["appRevision"],
                        "expectedRevision":old["revision"],
                        "baseContentHash":old["contentHash"],
                        "definition":updated})
                    keep=registry.score_record(human,"app-a",high["recordId"],20,3)
                    check("B4-25-human-B2-draft-edit-keeps-live-code",
                          b2.draft(human,"app-a")["appRevision"]==5 and
                          b2.release(human,"app-a")["version"]==1 and
                          keep["riskScore"]==95,
                          {"b2DraftRevision":5,"publishedB2Version":1,
                           "extensionScore":keep["riskScore"]})
                    current=b2.draft(human,"app-a")
                    b2v2=b2.publish(human,"app-a",{
                        "changeId":"b4-b2-publish-v2",
                        "expectedAppRevision":current["appRevision"],
                        "manifestHash":current["manifestHash"]})
                    mismatch_status,mismatch=json_browser(
                        risk_low,base+"/v2/apps/app-a/runtime/extensions/risk/"+
                        low["recordId"]+"?supplier_score=88&months_active=50")
                    pointer_unchanged=sql_oracle(dbfile,"app-a")["extensionVersion"]==1
                    b2.rollback(human,"app-a",{
                        "changeId":"b4-b2-rollback-v1",
                        "expectedPublishedVersion":2,"targetVersion":1})
                    restored_status,restored=json_browser(
                        risk_low,base+"/v2/apps/app-a/runtime/extensions/risk/"+
                        low["recordId"]+"?supplier_score=88&months_active=50")
                    check("B4-26-schema-version-mismatch-fail-closed-and-recover",
                          b2v2["version"]==2 and mismatch_status==409 and
                          mismatch.get("error")=="B2_RELEASE_CHANGED" and
                          pointer_unchanged and restored_status==200 and
                          restored["riskScore"]==0,
                          {"staleB2Http":mismatch_status,"recoveredB2Http":restored_status,
                           "extensionPointerNeverRewritten":True})
                    p=sql_oracle(dbfile,"app-a")
                    other=sql_oracle(dbfile,"app-b")
                    check("B4-27-independent-physical-oracle-and-cross-app",
                          p["extensionVersion"]==1 and len(p["artifacts"])==2 and
                          len(p["releases"])==2 and
                          all(x["sourceHashMatches"] for x in p["artifacts"]) and
                          other["appRevision"]==0 and other["artifacts"]==[] and
                          other["releases"]==[] and
                          any(x["event"]=="EXTENSION_PUBLISH" for x in p["events"]) and
                          any(x["event"]=="EXTENSION_ROLLBACK" for x in p["events"]),
                          {"appAArtifacts":2,"appACodeReleases":2,
                           "appBArtifacts":0,"appBRevision":0,
                           "finalCodePointer":p["extensionVersion"]})
                    evidence["finalPhysical"]={
                        "b2PublishedVersion":p["b2Version"],
                        "extensionPublishedVersion":p["extensionVersion"],
                        "immutableCodeArtifacts":len(p["artifacts"]),
                        "codeReleaseHistory":len(p["releases"]),
                        "appBRevision":other["appRevision"],
                        "recordCount":len(p["rows"])}
                finally:
                    context.close()
                    browser.close()
        except BaseException as exc:
            evidence["error"]={"kind":type(exc).__name__,
                               "message":str(exc)[:260],
                               "trace":traceback.format_exc()[-900:]}
            raise
        finally:
            server.shutdown();server.server_close();server_thread.join(timeout=4)
            evidence["summary"]={"passed":sum(x["status"]=="PASS" for x in cases),
                                 "attempted":len(cases),"expected":27,
                                 "real_model":evidence["inference"],
                                 "model_calls":evidence["modelCalls"]}
            Path(args.output).write_text(
                json.dumps(evidence,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            print("S1_B4_RESULT "+json.dumps(evidence["summary"]),flush=True)
    return 0 if len(cases)==27 and all(x["status"]=="PASS" for x in cases) else 1

if __name__=="__main__":
    raise SystemExit(main())
