#!/usr/bin/env python3
"""Saltcorn real browser login + native REST + native Validate/Insert triggers.

This is a security regression experiment on an ephemeral Saltcorn platform.
Login session comes from Saltcorn itself; actor_role/actor_id are untrusted
client fields, compared by the native Trigger with authenticated req.user.
This does NOT use a custom approval gateway or a real LLM Agent.
"""
from __future__ import annotations
import argparse
import json
import os
import sqlite3
import traceback
from pathlib import Path
from playwright.sync_api import sync_playwright

IDENTITIES={
 "creator":("s1-creator@example.invalid","S1_CREATOR_PASSWORD"),
 "approver1":("s1-approver1@example.invalid","S1_APPROVER1_PASSWORD"),
 "approver2":("s1-approver2@example.invalid","S1_APPROVER2_PASSWORD"),
 "viewer":("s1-viewer@example.invalid","S1_VIEWER_PASSWORD")
}

def dbread(path,sql,params=()):
    with sqlite3.connect(f"file:{Path(path).resolve()}?mode=ro",uri=True) as db:
        db.row_factory=sqlite3.Row
        return [dict(row) for row in db.execute(sql,params)]

def contract(path,number):
    matches=dbread(path,"SELECT id,number,amount_minor,status FROM s1_bench_contracts WHERE number=?",(number,))
    if len(matches)!=1:raise AssertionError("contract fixture missing "+number)
    return matches[0]

def approvals(path,contract_id):
    return dbread(path,"SELECT approver_id,actor_role,action FROM s1_bench_approvals WHERE contract_ref=? ORDER BY id",(contract_id,))

def requests(path,contract_id):
    return dbread(path,"SELECT request_id,actor_id,actor_role,action FROM s1_bench_action_requests WHERE contract_ref=? ORDER BY id",(contract_id,))

def http_post(ctx,base,path,body):
    response=ctx.request.post(base+path,data=json.dumps(body),
                              headers={"Content-Type":"application/json"},timeout=20000)
    content=response.text()
    # Scrubbed diagnostics: never print Cookie, Authorization, CSRF or raw HTML.
    kind="unknown"
    err=None
    keys=[]
    try:
        obj=json.loads(content)
        kind="json"
        if isinstance(obj,dict):
            keys=list(obj.keys())[:10]
            err=str(obj.get("error",""))[:180] if "error" in obj else None
    except ValueError:
        kind="html" if "<html" in content.lower() or "<!doctype" in content.lower() else "non-json"
    print("S1_NATIVE_HTTP_DIAGNOSTIC|"+json.dumps({
        "path":path,"http":response.status,
        "final_path":response.url.replace(base,""),
        "content_type":response.headers.get("content-type",""),
        "response_kind":kind,"json_keys":keys,"error_code":err
    }),flush=True)
    return response.status,content[:600]

def run(a,record):
    base=a.base
    people={}
    for role,(email,_) in IDENTITIES.items():
        rows=dbread(a.db,"SELECT id,email,role_id FROM users WHERE email=?",(email,))
        people[role]=rows[0] if len(rows)==1 else {}
    record("AUTH01-four-native-users",all(p.get("role_id")==80 for p in people.values()),
           {"observed":{k:{"present":bool(v),"role_id":v.get("role_id")} for k,v in people.items()}})
    for name in ("S1-AUTH-HIGH-1","S1-AUTH-NORMAL-1","S1-AUTH-HIGH-REJECT","S1-AUTH-HIGH-FORGED"):
        c=contract(a.db,name)
        record("AUTH02-"+name,c["status"]=="Draft",{"contract_no":name,"status":c["status"]})
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
        contexts={}
        for role,(email,pwvar) in IDENTITIES.items():
            ctx=browser.new_context()
            page=ctx.new_page()
            page.goto(base+"/auth/login",wait_until="domcontentloaded")
            loginform=page.locator('form[action="/auth/login"]')
            has_csrf=loginform.locator('input[name="_csrf"]').count()==1
            page.locator('input[name="email"]').fill(email)
            page.locator('input[name="password"]').fill(os.environ[pwvar])
            loginform.locator('button[type="submit"],input[type="submit"]').last.click()
            page.wait_for_load_state("domcontentloaded")
            success=not page.url.endswith("/auth/login") and "/auth/login?" not in page.url
            record("AUTH03-login-"+role,success and has_csrf,
                   {"login_redirect_path":page.url.replace(base,""),"csrf_present":has_csrf})
            contexts[role]=ctx

        bad=browser.new_context()
        code,body=http_post(bad,base,"/api/s1_bench_action_requests/",{
            "request_id":"s1-anon-forbidden","contract_ref":contract(a.db,"S1-AUTH-HIGH-1")["id"],
            "action":"submit","actor_role":"creator","actor_id":str(people["creator"]["id"])
        })
        record("AUTH04-anonymous-native-api-denied",code==401,
               {"http":code,"physical_request_count":len(requests(a.db,contract(a.db,"S1-AUTH-HIGH-1")["id"]))})
        bad.close()
        count=0
        def send(role,number,action,*,claimed_role=None,actor_id=None,request_id=None):
            nonlocal count
            count+=1
            obj=contract(a.db,number)
            jsonbody={
                "request_id":request_id or f"s1-auth-{count:04}",
                "contract_ref":obj["id"],
                "action":action,
                "actor_role":claimed_role or role,
                "actor_id":str(people[role]["id"]) if actor_id is None else str(actor_id),
                "occurred_at":"2026-11-21T00:00:00Z",
                "reason":"authenticated native Saltcorn research"
            }
            return http_post(contexts[role],base,"/api/s1_bench_action_requests/",jsonbody)

        high="S1-AUTH-HIGH-1"
        normal="S1-AUTH-NORMAL-1"
        denied="S1-AUTH-HIGH-FORGED"
        rejection="S1-AUTH-HIGH-REJECT"
        approver1=people["approver1"]["id"]
        approver2=people["approver2"]["id"]
        code,body=send("viewer",denied,"approve",claimed_role="approver1",actor_id=approver1)
        record("AUTH05-forged-role-and-identity-rejected",
               code==400 and "IDENTITY_MISMATCH" in body and contract(a.db,denied)["status"]=="Draft",
               {"http":code,"error":"IDENTITY_MISMATCH" in body,"status":contract(a.db,denied)["status"]})
        code,body=send("creator",denied,"submit",actor_id=approver1)
        record("AUTH06-forged-actor-id-rejected",
               code==400 and "IDENTITY_MISMATCH" in body and not requests(a.db,contract(a.db,denied)["id"]),
               {"http":code,"error":"IDENTITY_MISMATCH" in body})
        code,body=send("creator",normal,"submit")
        record("AUTH07-native-creator-normal-submit",
               code==200 and contract(a.db,normal)["status"]=="Submitted",
               {"http":code,"actual_status":contract(a.db,normal)["status"]})
        code,body=send("approver2",normal,"approve")
        record("AUTH08-wrong-authenticated-approver-normal",
               code==400 and "FORBIDDEN" in body and contract(a.db,normal)["status"]=="Submitted",
               {"http":code,"business_error":"FORBIDDEN" in body})
        code,body=send("approver1",normal,"approve")
        record("AUTH09-authenticated-approver1-finishes-normal",
               code==200 and contract(a.db,normal)["status"]=="Approved" and
               len(approvals(a.db,contract(a.db,normal)["id"]))==1,
               {"http":code,"actual_status":contract(a.db,normal)["status"],
                "approval_count":len(approvals(a.db,contract(a.db,normal)["id"]))})
        code,body=send("creator",high,"submit")
        record("AUTH10-authenticated-creator-high-submit",
               code==200 and contract(a.db,high)["status"]=="Submitted",
               {"http":code,"actual_status":contract(a.db,high)["status"]})
        code,body=send("viewer",high,"approve")
        record("AUTH11-authenticated-viewer-rejected-high",
               code==400 and "FORBIDDEN" in body and contract(a.db,high)["status"]=="Submitted",
               {"http":code,"business_error":"FORBIDDEN" in body})
        code,body=send("approver1",high,"approve")
        record("AUTH12-first-high-approval",
               code==200 and contract(a.db,high)["status"]=="Level1Approved",
               {"http":code,"actual_status":contract(a.db,high)["status"]})
        code,body=send("approver1",high,"approve")
        record("AUTH13-first-approver-cannot-finalize",
               code==400 and "FORBIDDEN" in body and contract(a.db,high)["status"]=="Level1Approved",
               {"http":code,"business_error":"FORBIDDEN" in body})
        code,body=send("approver2",high,"approve")
        observed_ap=approvals(a.db,contract(a.db,high)["id"])
        record("AUTH14-second-high-approval-final",
               code==200 and contract(a.db,high)["status"]=="Approved" and
               [x["approver_id"] for x in observed_ap]==[str(approver1),str(approver2)],
               {"http":code,"actual_status":contract(a.db,high)["status"],
                "approval_roles":[x["actor_role"] for x in observed_ap],
                "db_actor_ids_match_authenticated_users":[x["approver_id"] for x in observed_ap]==[str(approver1),str(approver2)]})
        code,body=send("creator",rejection,"submit")
        record("AUTH15-creator-reject-sequence-start",
               code==200 and contract(a.db,rejection)["status"]=="Submitted",
               {"http":code,"actual_status":contract(a.db,rejection)["status"]})
        code,body=send("approver1",rejection,"reject")
        record("AUTH16-authenticated-rejection",
               code==200 and contract(a.db,rejection)["status"]=="Rejected" and
               len(approvals(a.db,contract(a.db,rejection)["id"]))==1,
               {"http":code,"actual_status":contract(a.db,rejection)["status"]})
        direct_code,direct_response=http_post(
            contexts["viewer"],base,
            f"/api/s1_bench_contracts/{contract(a.db,high)['id']}",
            {"status":"Approved"})
        record("AUTH17-viewer-direct-business-table-update-denied",
               direct_code==401 and contract(a.db,high)["status"]=="Approved",
               {"http":direct_code,"actual_status":contract(a.db,high)["status"]})
        code,body=http_post(contexts["creator"],base,"/api/s1_bench_approvals/",{
            "contract_ref":contract(a.db,high)["id"],"approver_id":"forged",
            "actor_role":"approver2","action":"approve","occurred_at":"2026-11-21T00:00:00Z"})
        record("AUTH18-native-approval-table-direct-insert-denied",
               code==401 and len(approvals(a.db,contract(a.db,high)["id"]))==2,
               {"http":code,"approval_count":len(approvals(a.db,contract(a.db,high)["id"]))})
        code,body=send("creator",high,"approve",claimed_role="approver2",actor_id=approver2)
        record("AUTH19-replay-business-identity-spoof-denied",
               code==400 and "IDENTITY_MISMATCH" in body and
               len(approvals(a.db,contract(a.db,high)["id"]))==2,
               {"http":code,"error":"IDENTITY_MISMATCH" in body})
        for role,ctx in contexts.items():
            ctx.close()
        browser.close()

    good_requests=[
        ("S1-AUTH-NORMAL-1",2,1),("S1-AUTH-HIGH-1",3,2),
        ("S1-AUTH-HIGH-REJECT",2,1),("S1-AUTH-HIGH-FORGED",0,0)
    ]
    for number,nrequests,napprovals in good_requests:
        c=contract(a.db,number)
        reqs=requests(a.db,c["id"])
        aps=approvals(a.db,c["id"])
        record("AUTH20-db-"+number,len(reqs)==nrequests and len(aps)==napprovals,
               {"actual_request_count":len(reqs),"actual_approval_count":len(aps),
                "expected_request_count":nrequests,"expected_approval_count":napprovals})
    triggers=dbread(a.db,"SELECT name,action,when_trigger FROM _sc_triggers WHERE name LIKE 'S1 %'")
    record("AUTH21-authentication-bound-native-validate-trigger",
           len(triggers)==3 and any(t["name"]=="S1 Validate Approval Request" and t["action"]=="run_js_code" for t in triggers),
           {"trigger_names":[t["name"] for t in triggers]})
    meta=dbread(a.db,"SELECT min_role_write FROM _sc_tables WHERE name='s1_bench_action_requests'")
    record("AUTH22-table-access-native-role-boundary",
           len(meta)==1 and meta[0]["min_role_write"]==80,
           {"native_min_role_write":meta[0]["min_role_write"]})
    return True

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--db",required=True)
    ap.add_argument("--base",default="http://127.0.0.1:3100")
    ap.add_argument("--output",required=True)
    a=ap.parse_args()
    evidence={"study":"Real Saltcorn passport browser login and native REST approval via native Validate/Insert Trigger",
              "real_browser_login":True,
              "real_saltcorn_api":True,
              "auth_user_from_saltcorn_session":True,
              "not_full_approval_browser_UI":True,
              "no_llm_agent":True,
              "cases":[]}
    def record(cid,ok,observation):
        evidence["cases"].append({"id":cid,"status":"PASS" if ok else "FAIL","observed":observation})
        print(cid,"PASS" if ok else "FAIL",json.dumps(observation,ensure_ascii=False),flush=True)
    try:
        run(a,record)
    except Exception as exc:
        evidence["error"]={"type":type(exc).__name__,"detail":str(exc)[:900],
                           "traceback_tail":traceback.format_exc()[-2000:]}
        print("AUTH_ACCEPTANCE_ERROR",type(exc).__name__,str(exc),flush=True)
    evidence["summary"]={"total":len(evidence["cases"]),
                         "passed":sum(x["status"]=="PASS" for x in evidence["cases"])}
    Path(a.output).write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    # 1 + 4 fixtures + 4 logins + AUTH04 through AUTH19 (16) + 4 SQL rows + 2 = 27.
    return 0 if len(evidence["cases"])==27 and all(x["status"]=="PASS" for x in evidence["cases"]) else 1

if __name__=="__main__":
    raise SystemExit(main())
