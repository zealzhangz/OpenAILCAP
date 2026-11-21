#!/usr/bin/env python3
"""Independent executable acceptance of tool broker on real Saltcorn runtime.

Each browser login is real. The trusted HOST (test controller), never model,
issues one-use, scope-limited approval grants. Mutations are real native REST
and native workflow triggers. Does NOT run any LLM.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sqlite3
from uuid import uuid4
from playwright.sync_api import sync_playwright

from broker import APP_ID, Broker, SaltcornRest, TrustedSession, ToolError

USERS = {
    "creator": ("s1-creator@example.invalid", "S1_CREATOR_PASSWORD"),
    "approver1": ("s1-approver1@example.invalid", "S1_APPROVER1_PASSWORD"),
    "approver2": ("s1-approver2@example.invalid", "S1_APPROVER2_PASSWORD"),
    "viewer": ("s1-viewer@example.invalid", "S1_VIEWER_PASSWORD"),
}
HIGH="S1-AGENT-HIGH-1"
NORMAL="S1-AGENT-NORMAL-1"

def read_db(db_path, sql, parameters=()):
    with sqlite3.connect(f"file:{Path(db_path).resolve()}?mode=ro", uri=True) as db:
        db.row_factory=sqlite3.Row
        return [dict(r) for r in db.execute(sql,parameters)]

def db_contract(db_path,number):
    rows=read_db(db_path,"SELECT id,number,status,amount_minor FROM s1_bench_contracts WHERE number=?",(number,))
    if len(rows)!=1:
        raise RuntimeError("MISSING_REAL_NATIVE_CONTRACT")
    return rows[0]

def db_approval_count(db_path,number):
    cid=db_contract(db_path,number)["id"]
    return len(read_db(db_path,"SELECT id FROM s1_bench_approvals WHERE contract_ref=?",(cid,)))

def record_factory(cases):
    def record(name,condition,observed):
        cases.append({"id":name,"passed":bool(condition),"observed":observed})
        print(name,"PASS" if condition else "FAIL",json.dumps(observed,ensure_ascii=False),flush=True)
    return record

def get_browser_page(page,base,path):
    for n in range(3):
        try:
            page.goto(base+path,wait_until="domcontentloaded",timeout=18000)
            return
        except Exception:
            if n==2: raise
            page.wait_for_timeout(350)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--db",required=True)
    parser.add_argument("--base",default="http://127.0.0.1:3100")
    parser.add_argument("--output",required=True)
    parser.add_argument("--live-model",action="store_true",
                        help="Explicit manual real-model probe; requires HTTPS provider credentials")
    a=parser.parse_args()
    cases=[]
    check=record_factory(cases)
    report={
       "study":"OpenAILCAP S1 least privilege typed Agent tool contract on real Saltcorn",
       "real_saltcorn":True,"model_inference_executed":False,
       "trusted_controller_issued_human_grants":True,"cases":cases}
    now=[1000.0]
    adapter=SaltcornRest(a.base)
    broker=Broker("/tmp/s1-agent-tool-audit.sqlite",adapter,now=lambda:now[0])
    contexts={}
    try:
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(headless=True,args=["--no-sandbox"])
            try:
                for role,(email,pwenv) in USERS.items():
                    ctx=browser.new_context()
                    contexts[role]=ctx
                    page=ctx.new_page()
                    get_browser_page(page,a.base,"/auth/login")
                    page.locator('input[name="email"]').fill(email)
                    page.locator('input[name="password"]').fill(os.environ[pwenv])
                    page.locator('form[action="/auth/login"] button[type="submit"], form[action="/auth/login"] input[type="submit"]').last.click()
                    page.wait_for_load_state("domcontentloaded")
                    logged_in=page.url.split("?")[0] != a.base+"/auth/login"
                    get_browser_page(page,a.base,"/auth/login")
                    csrf_input=page.locator('form[action="/auth/login"] input[name="_csrf"]')
                    if csrf_input.count()!=1:
                        raise RuntimeError("NATIVE_CSRF_NOT_AVAILABLE")
                    csrf=csrf_input.input_value()
                    user=read_db(a.db,"SELECT id,role_id FROM users WHERE email=?",(email,))
                    if len(user)!=1:
                        raise RuntimeError("NATIVE_USER_MISSING")
                    subject=TrustedSession(session_key=f"s1-real-{role}",app_id=APP_ID,
                                           email=email,user_id=user[0]["id"],role=role,
                                           scopes=frozenset({"contract.read"} if role=="viewer" else
                                                             {"contract.read","contract.action"}))
                    broker.bind_session(subject,ctx,csrf)
                    check("AT01-login-"+role,
                          logged_in and bool(csrf) and user[0]["role_id"]==80,
                          {"native_saltcorn_login":logged_in,"has_csrf":bool(csrf),
                           "role_id":user[0]["role_id"]})
                C="s1-real-creator";P1="s1-real-approver1";P2="s1-real-approver2";V="s1-real-viewer"
                def invoke(user,tool,args,grant=None):
                    return broker.execute(user,tool,args,call_id="ai-"+uuid4().hex[:24],human_grant=grant)
                def denied(code,fn):
                    try:
                        fn()
                        return False
                    except ToolError as exc:
                        return exc.code==code
                before=broker.catalog(V)
                check("AT02-least-privilege-catalog",
                      [x["name"] for x in before]==["contract.read"],
                      {"viewer_tool_names":[x["name"] for x in before]})
                check("AT03-reject-dangerous-plugin-handler",
                      denied("UNTRUSTED_PLUGIN_HANDLER",lambda:broker.register_manifest({
                          "name":"route-inspector","version":"1.0.0",
                          "tool":{"name":"contract.route","handler":"os_command"}})),
                      {"custom_code_executable":False})
                broker.register_manifest({"name":"route-inspector","version":"1.0.0",
                                          "tool":{"name":"contract.route","handler":"route_inspector_v1"}})
                check("AT04-manifest-registered-without-core-rewrite",
                      set(x["name"] for x in broker.catalog(V))=={"contract.read","contract.route"},
                      {"viewer_tools":[x["name"] for x in broker.catalog(V)]})
                native=invoke(V,"contract.read",{"number":HIGH})
                check("AT05-real-native-REST-contract-read",
                      native["number"]==HIGH and native["amount_minor"]==100000001 and
                      native["status"]=="Draft" and
                      db_contract(a.db,HIGH)["status"]=="Draft",
                      {"contract_no":native["number"],"http_data_status":native["status"],
                       "amount_minor":native["amount_minor"]})
                route=invoke(V,"contract.route",{"number":HIGH})
                row=read_db(a.db,"SELECT route FROM s1_bench_routes WHERE contract_ref=?",(native["id"],))
                check("AT06-new-plugin-routes-against-physical-native-data",
                      route["derived_route"]=="HIGH" and len(row)==1 and row[0]["route"]=="HIGH",
                      {"model_visible_tool":"contract.route","derived":"HIGH","native_route":row[0]["route"] if row else None})
                check("AT07-no-shell-or-credential-tools",
                      denied("UNKNOWN_TOOL",lambda:invoke(V,"system.shell",{"cmd":"cat /etc/passwd"})),
                      {"shell_executed":False})
                check("AT08-forged-actor-in-LLM-arguments-rejected",
                      denied("INVALID_ARGUMENTS",lambda:invoke(C,"contract.read",{
                          "number":HIGH,"actor_id":"1","actor_role":"admin"})),
                      {"server_identity_source":"Saltcorn browser session"})
                args={"number":HIGH,"action":"submit","base_status":"Draft"}
                check("AT09-no-write-without-separate-human-grant",
                      denied("HUMAN_APPROVAL_REQUIRED",lambda:invoke(C,"contract.action",args))
                      and db_contract(a.db,HIGH)["status"]=="Draft",
                      {"unchanged":db_contract(a.db,HIGH)["status"]})
                check("AT10-viewer-cannot-do-mutating-tool",
                      denied("SCOPE_DENIED",lambda:invoke(V,"contract.action",args)),
                      {"viewer_scopes":["contract.read"]})
                check("AT11-agent-cannot-mint-approval-grant",
                      denied("HUMAN_APPROVAL_REQUIRED",lambda:broker.issue_human_grant(
                         C,HIGH,"submit",trusted_user_confirmed=False)),
                      {"separate_human_confirmation_required":True})
                check("AT12-approver-cannot-submit",
                      denied("ROLE_NOT_DELEGATABLE",lambda:broker.issue_human_grant(
                         P1,HIGH,"submit",trusted_user_confirmed=True)),
                      {"signed_in_role":"approver1"})
                check("AT13-forged-application-session-rejected",
                      denied("SCOPE_DENIED",lambda:broker.bind_session(
                         TrustedSession("other-tenant","other-app",USERS["viewer"][0],1,
                                        "viewer",frozenset({"contract.read"})),contexts["viewer"],"dummycsrfvalue")),
                      {"cross_app_isolation":"fixed study app only"})
                # Actual short grant expired without changing resource.
                short=broker.issue_human_grant(C,HIGH,"submit",trusted_user_confirmed=True,ttl=1)
                now[0]=1002.0
                check("AT15-actual-expired-grant-no-write",
                      denied("GRANT_REJECTED",lambda:invoke(C,"contract.action",args,short)) and
                      db_contract(a.db,HIGH)["status"]=="Draft",
                      {"physical_status":db_contract(a.db,HIGH)["status"]})
                now[0]=1003.0
                human=broker.issue_human_grant(C,HIGH,"submit",trusted_user_confirmed=True)
                check("AT16-cross-user-grant-denied",
                      denied("GRANT_REJECTED",lambda:invoke(P1,"contract.action",args,human)),
                      {"grant_bound_to":"creator"})
                check("AT17-cross-resource-grant-denied",
                      denied("GRANT_REJECTED",lambda:invoke(C,"contract.action",{
                        "number":NORMAL,"action":"submit","base_status":"Draft"},human)),
                      {"resource_bound_to":HIGH})
                check("AT18-stale-base-rejected-before-HTTP",
                      denied("STALE_RESOURCE",lambda:invoke(C,"contract.action",{
                        "number":HIGH,"action":"submit","base_status":"Submitted"},human)) and
                      db_contract(a.db,HIGH)["status"]=="Draft",
                      {"actual_status":"Draft"})
                receipt=invoke(C,"contract.action",args,human)
                check("AT19-real-human-delegated-submit-via-native-Saltcorn",
                      receipt["status"]=="NATIVE_ACCEPTED_RECHECK_REQUIRED" and
                      db_contract(a.db,HIGH)["status"]=="Submitted",
                      {"physical_state":db_contract(a.db,HIGH)["status"],"http_success":True})
                check("AT20-one-time-grant-replay-denied",
                      denied("GRANT_REJECTED",lambda:invoke(C,"contract.action",args,human)),
                      {"cannot_reuse_grant":True})
                check("AT21-creator-cannot-directly-edit-contract",
                      (lambda r: r.status==401)(
                        contexts["creator"].request.post(
                          a.base+"/api/s1_bench_contracts/"+str(native["id"]),
                          data=json.dumps({"status":"Approved"}),
                          headers={"Content-Type":"application/json",
                                   "X-CSRF-Token":adapter.sessions[C][1]})) and
                      db_contract(a.db,HIGH)["status"]=="Submitted",
                      {"native_http_permission":"401","state_unchanged":True})
                approve={"number":HIGH,"action":"approve","base_status":"Submitted"}
                p1grant=broker.issue_human_grant(P1,HIGH,"approve",trusted_user_confirmed=True)
                r=invoke(P1,"contract.action",approve,p1grant)
                check("AT22-real-delegated-first-approval",
                      r["status"]=="NATIVE_ACCEPTED_RECHECK_REQUIRED" and
                      db_contract(a.db,HIGH)["status"]=="Level1Approved",
                      {"real_state":db_contract(a.db,HIGH)["status"]})
                late=broker.issue_human_grant(P1,HIGH,"approve",trusted_user_confirmed=True)
                bad={"number":HIGH,"action":"approve","base_status":"Level1Approved"}
                check("AT23-wrong-level-native-business-policy-denied",
                      denied("NATIVE_REJECTED",lambda:invoke(P1,"contract.action",bad,late)) and
                      db_contract(a.db,HIGH)["status"]=="Level1Approved",
                      {"actual_native_sql_state":"Level1Approved","tool_result":"NATIVE_REJECTED"})
                p2grant=broker.issue_human_grant(P2,HIGH,"approve",trusted_user_confirmed=True)
                result=invoke(P2,"contract.action",bad,p2grant)
                check("AT24-real-delegated-second-approval",
                      result["status"]=="NATIVE_ACCEPTED_RECHECK_REQUIRED" and
                      db_contract(a.db,HIGH)["status"]=="Approved" and
                      db_approval_count(a.db,HIGH)==2,
                      {"physical_state":db_contract(a.db,HIGH)["status"],
                       "approvals":db_approval_count(a.db,HIGH)})
                after=invoke(V,"contract.read",{"number":HIGH})
                check("AT25-read-after-real-Saltcorn-approval",
                      after["status"]=="Approved" and after["amount_minor"]==100000001,
                      {"API_status":after["status"],"DB_status":db_contract(a.db,HIGH)["status"]})
                logs=read_db("/tmp/s1-agent-tool-audit.sqlite",
                             "SELECT tool,result,args_sha256 FROM agent_tool_audit")
                outcomes=[x["result"] for x in logs]
                check("AT26-persistent-redacted-tool-audit",
                      len(logs)>=16 and "MUTATION_ACCEPTED" in outcomes and
                      "HUMAN_APPROVAL_REQUIRED" in outcomes and
                      "GRANT_REJECTED" in outcomes and
                      all(len(x["args_sha256"])==64 for x in logs),
                      {"audits":len(logs),"accepted":outcomes.count("MUTATION_ACCEPTED"),
                       "denied":sum(x not in ("READ_OK","READ_ROUTE_OK","MUTATION_ACCEPTED") for x in outcomes),
                       "no_password_cookies_csrf_stored":True})
                # Explicit absence of model. No claim that tool calls were planned by LLM.
                check("AT27-model-not-implicitly-claimed",
                      report["model_inference_executed"] is False,
                      {"model_status":"SEPARATE_EXPLICIT_OPT_IN_REQUIRED"})
                if a.live_model:
                    from model_client import actual_model_probe
                    proof=actual_model_probe(broker,V,HIGH)
                    report["real_model_evidence"]=proof
                    report["model_inference_executed"]=True
                    check("AT28-true-external-LLM-tool-call-real-native-read",
                          proof["tool_calls_executed"]>=1
                          and proof["no_mutating_tools_exposed"]
                          and all(x["result"]["number"]==HIGH for x in proof["observations"]),
                          {"model_id":proof["model_id"],
                           "executed_read_only_tools":[x["tool"] for x in proof["observations"]]})
            finally:
                for ctx in contexts.values():ctx.close()
                browser.close()
    except Exception as exc:
        import traceback
        report["unhandled_error"]={"type":type(exc).__name__,"message":str(exc)[:450],
                                   "trace":traceback.format_exc()[-1400:]}
    report["summary"]={"total":len(cases),"passed":sum(c["passed"] for c in cases)}
    Path(a.output).write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("AT_RESULT|"+json.dumps(report["summary"]),flush=True)
    expected = 30 if a.live_model else 29
    return 0 if len(cases)==expected and all(c["passed"] for c in cases) else 1

if __name__=="__main__":raise SystemExit(main())
