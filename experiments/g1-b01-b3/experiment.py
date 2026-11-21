#!/usr/bin/env python3
"""B3 real human Chromium + one optional live model function call + real B2 runtime.

No secret or model raw HTTP response in artifacts. Preflight uses *reviewed*
static metadata and clearly marks inference=False. The live path can never
substitute its static baseline on a model failure.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import secrets
import sqlite3
import subprocess
import sys
import tempfile
import threading
import traceback
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from playwright.sync_api import sync_playwright
from plan import generate, redact_observation, sha
from schema_core import Actor, SchemaStore
from schema_http import serve_local

HERE=Path(__file__).resolve().parent


def http(base, method, route, *, token=None, body=None, sid=None, csrf=None):
    headers={}
    if token:
        headers["Authorization"]="Bearer "+token
    if sid:
        headers["Cookie"]="sid="+sid
    if csrf:
        headers["X-CSRF-Token"]=csrf
    data=None
    if body is not None:
        data=json.dumps(body,ensure_ascii=False).encode()
        headers["Content-Type"]="application/json"
    req=Request(base+route,method=method,headers=headers,data=data)
    try:
        with urlopen(req,timeout=15) as r:
            return r.status,json.loads(r.read())
    except HTTPError as e:
        return e.code,json.loads(e.read())


def verify_db(path,app):
    """Independent physical SQLite read-only oracle; not via SchemaStore."""
    with sqlite3.connect("file:"+str(Path(path).resolve())+"?mode=ro",uri=True) as db:
        a=db.execute("SELECT revision,manifest_hash,state,current_release FROM apps "
                     "WHERE app=?",(app,)).fetchone()
        defs=db.execute("SELECT rid,revision,spec,hash FROM definitions WHERE app=? "
                        "ORDER BY rid",(app,)).fetchall()
        events=db.execute("SELECT actor,event,rid FROM events WHERE app=? "
                          "ORDER BY eid",(app,)).fetchall()
        receipts=db.execute("SELECT COUNT(*) FROM receipts WHERE app=?",(app,)).fetchone()[0]
        rows=db.execute("SELECT record_id,version,content FROM records WHERE app=?",
                        (app,)).fetchall()
        releases=db.execute("SELECT version,manifest,hash FROM releases WHERE app=? "
                            "ORDER BY version",(app,)).fetchall()
    return {"appRevision":a[0],"manifestHash":a[1],"state":a[2],
            "currentRelease":a[3],
            "defs":{r[0]:{"revision":r[1],"definition":json.loads(r[2]),"hash":r[3]}
                    for r in defs},
            "events":[{"actor":r[0],"event":r[1],"resource":r[2]} for r in events],
            "receiptCount":receipts,
            "records":[{"id":r[0],"revision":r[1],"data":json.loads(r[2])} for r in rows],
            "releases":[{"version":r[0],"definitions":json.loads(r[1]),"hash":r[2]}
                        for r in releases]}


def dom(page,selector,value,exact=False):
    """CSP-safe DOM polling (no string-JS eval)."""
    for _ in range(90):
        text=page.locator(selector).inner_text(timeout=1500)
        if (text==value if exact else value in text):
            return
        page.wait_for_timeout(160)
    raise AssertionError("DOM assertion timed out: "+selector+" expected "+value)


def change_form_title(page,new):
    page.locator("#resource-id").fill("form.contracts")
    page.locator("#select").click()
    definition=json.loads(page.locator("#definition").input_value())
    if definition.get("kind")!="form":
        raise AssertionError("unexpected browser current form")
    definition["title"]=new
    page.locator("#definition").fill(json.dumps(definition,ensure_ascii=False,indent=2))
    page.locator("#save").click()


def subprocess_apply(base,token,plan,path):
    plan_path=path/"validated-plan.json"
    output=path/"tool-execution.json"
    plan_path.write_text(json.dumps({
        "operations":plan["operations"],"planHash":plan["planHash"]
    },ensure_ascii=False),encoding="utf-8")
    env={"PATH":os.getenv("PATH",""),"S1_B3_AGENT_TOKEN":token}
    args=[sys.executable,str(HERE/"apply_plan.py"),"--base",base,
          "--plan",str(plan_path),"--output",str(output)]
    done=subprocess.run(args,env=env,text=True,capture_output=True,timeout=70)
    if done.returncode!=0:
        raise AssertionError("AGENT_TOOL_FAILED:"+done.stderr[-500:])
    result=json.loads(output.read_text(encoding="utf-8"))
    if result["status"]!="APPLIED":
        raise AssertionError("AGENT_TOOL_NOT_APPLIED")
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--mode",choices=("offline","live"),default="offline")
    p.add_argument("--output",required=True)
    args=p.parse_args()
    live=(args.mode=="live")
    cases=[]
    evidence={
        "scope":"S1_B3_MODEL_TYPED_TOOL_NARROW_CONTRACT_DEMO",
        "mode":args.mode,"inference":False,"model_attempted":False,
        "not_poc_a_full":True,"not_a_w01_w24_result":True,
        "source_is_not_saltcorn_native":True,
        "real_chromium":True,"external_agent_process":True,
        "model_has_db_or_publish_access":False,"cases":cases
    }
    def check(name,condition,observed):
        entry={"id":name,"status":"PASS" if condition else "FAIL","observed":observed}
        cases.append(entry)
        print("B3 "+name+" "+entry["status"]+" "+json.dumps(observed,ensure_ascii=False),
              flush=True)
        if not condition:
            raise AssertionError(name)
    with tempfile.TemporaryDirectory() as temp:
        tmp=Path(temp)
        dbfile=tmp/"b3.sqlite"
        store=SchemaStore(dbfile)
        store.init()
        store.seed_app_for_test("app-a")
        store.seed_app_for_test("app-b")
        human=Actor("human-approved","app-a",can_publish=True,can_runtime=True)
        agent=Actor("deepseek-proposal-executor","app-a",can_publish=False)
        token=secrets.token_urlsafe(30)
        password=secrets.token_urlsafe(30)
        sessions={}
        server=serve_local(store,{token:agent},sessions,human,password)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        base="http://127.0.0.1:"+str(server.server_port)
        try:
            check("B3-01-loopback-real-HTTP-ready",
                  http(base,"GET","/health")[0]==200,
                  {"http":200,"app_revision":0})
            with sync_playwright() as pw:
                browser=pw.chromium.launch(headless=True,args=["--no-sandbox"])
                context=browser.new_context()
                try:
                    human_tab=context.new_page()
                    human_tab.goto(base+"/editor/app-a",wait_until="domcontentloaded")
                    check("B3-02-anonymous-human-redirect",
                          human_tab.url.endswith("/editor/login"),
                          {"login_required":True})
                    human_tab.locator("#password").fill(password)
                    human_tab.locator("#login").click()
                    human_tab.wait_for_url("**/editor/app-a",timeout=13000)
                    dom(human_tab,"#revision","0",exact=True)
                    check("B3-03-real-human-empty-editor",
                          human_tab.locator("#resources").inner_text()=="已注册: " and
                          verify_db(dbfile,"app-a")["appRevision"]==0,
                          {"real_chromium":True,"draft_revision":0})
                    # This is the ONLY place an external model call is allowed.
                    evidence["model_attempted"]=live
                    if live:
                        print("S1_B3_LIVE_DEEPSEEK_SINGLE_REQUEST",flush=True)
                    result=generate(live=live)
                    evidence["inference"]=result["inference"]
                    evidence["proposal"]=redact_observation(result)
                    plan=result["plan"]
                    evidence["validated_model_generated_plan"]=plan["definitions"]
                    check("B3-04-plan-transport-and-independent-schema-gate",
                          bool(result["inference"])==live and
                          result["modelCalls"]==(1 if live else 0) and
                          len(plan["definitions"])==4,
                          {"inference":result["inference"],
                           "actual_model_requests":result["modelCalls"],
                           "validated_resources":list(plan["definitions"])})
                    initial=http(base,"GET","/v2/apps/app-a/draft",token=token)
                    check("B3-05-agent-pre-write-authoritative-snapshot",
                          initial[0]==200 and initial[1]["appRevision"]==0 and
                          initial[1]["resources"]=={},
                          {"appRevision":0,"trusted_principal":"agent"})
                    executed=subprocess_apply(base,token,plan,tmp)
                    db=verify_db(dbfile,"app-a")
                    defs={rid:row["definition"] for rid,row in db["defs"].items()}
                    check("B3-06-model-plan-applied-by-real-tool-process",
                          executed["appRevision"]==4 and len(executed["operations"])==4 and
                          db["appRevision"]==4 and set(defs)==set(plan["definitions"]) and
                          all(e["actor"]=="deepseek-proposal-executor"
                              for e in db["events"]),
                          {"actual_cli_http_commands":4,"physical_sql_app_revision":4,
                           "audit_agent_writes":len(db["events"])})
                    check("B3-07-model-manifest-content-and-hash-oracle",
                          sha(defs)==plan["planHash"] and
                          db["manifestHash"]==plan["planHash"] and
                          all(sha(e["definition"])==e["hash"]
                              for e in db["defs"].values()),
                          {"manifest_hash":db["manifestHash"],
                           "independent_sql_digest_match":True})
                    human_tab.locator("#reload").click()
                    dom(human_tab,"#revision","4",exact=True)
                    check("B3-08-browser-displays-model-created-resources",
                          all(rid in human_tab.locator("#resources").inner_text()
                              for rid in plan["definitions"]),
                          {"ui_resource_count":4,"browser_revision":4})
                    tab_a=context.new_page()
                    tab_b=context.new_page()
                    tab_a.goto(base+"/editor/app-a",wait_until="domcontentloaded")
                    tab_b.goto(base+"/editor/app-a",wait_until="domcontentloaded")
                    dom(tab_a,"#revision","4",exact=True)
                    dom(tab_b,"#revision","4",exact=True)
                    check("B3-09-two-real-browser-snapshots",
                          tab_a.locator("#definition").input_value()!="" and
                          tab_b.locator("#definition").input_value()!="",
                          {"browser_tabs":2,"stale_baseline_revision":4})
                    model_form_title=plan["definitions"]["form.contracts"]["title"]
                    human_title=model_form_title+" · 人工审核"
                    change_form_title(tab_a,human_title)
                    dom(tab_a,"#revision","5",exact=True)
                    after_human=verify_db(dbfile,"app-a")
                    check("B3-10-human-maintains-model-form",
                          after_human["defs"]["form.contracts"]["definition"]["title"]==
                          human_title and after_human["appRevision"]==5,
                          {"revision":5,"human_title":human_title})
                    model_view=copy.deepcopy(plan["definitions"]["view.contracts"])
                    model_view["title"]=model_view["title"]+" · Agent 后续维护"
                    # The second follow-up change is deterministic policy-driven:
                    # NOT an additional LLM inference. Same guarded tool interface.
                    stale_cmd={
                        "changeId":"b3-agent-stale-01",
                        "resourceId":"view.contracts",
                        "expectedAppRevision":4,
                        "expectedRevision":1,
                        "baseContentHash":sha(plan["definitions"]["view.contracts"]),
                        "definition":model_view
                    }
                    stale=http(base,"POST","/v2/apps/app-a/commands",
                               token=token,body=stale_cmd)
                    check("B3-11-previous-agent-snapshot-rejected",
                          stale[0]==409 and
                          stale[1].get("error")=="APP_REVISION_CONFLICT" and
                          verify_db(dbfile,"app-a")["appRevision"]==5,
                          {"http":409,"error":stale[1].get("error")})
                    fresh=http(base,"GET","/v2/apps/app-a/draft",token=token)[1]
                    fresh_cmd=dict(stale_cmd,changeId="b3-agent-rebased-02",
                                   expectedAppRevision=fresh["appRevision"],
                                   expectedRevision=fresh["resources"]["view.contracts"]["revision"],
                                   baseContentHash=fresh["resources"]["view.contracts"]["contentHash"])
                    fresh_response=http(base,"POST","/v2/apps/app-a/commands",
                                        token=token,body=fresh_cmd)
                    check("B3-12-rebased-agent-preserves-human-edit",
                          fresh_response[0]==200 and
                          verify_db(dbfile,"app-a")["appRevision"]==6 and
                          verify_db(dbfile,"app-a")["defs"]["form.contracts"]["definition"]["title"]==
                          human_title,
                          {"http":200,"new_revision":6,"human_title_retained":True})
                    change_form_title(tab_b,"旧页面不应覆盖")
                    dom(tab_b,"#message","409 APP_REVISION_CONFLICT")
                    check("B3-13-browser-stale-form-is-rejected",
                          verify_db(dbfile,"app-a")["defs"]["form.contracts"]["definition"]["title"]==
                          human_title,
                          {"stale_browser_status":409,"human_first_edit_preserved":True})
                    tab_b.locator("#reload").click()
                    dom(tab_b,"#revision","6",exact=True)
                    tab_b.locator("#resource-id").fill("view.contracts")
                    tab_b.locator("#select").click()
                    latest_view=json.loads(tab_b.locator("#definition").input_value())
                    check("B3-14-human-sees-agent-followup-change",
                          latest_view["title"]==model_view["title"],
                          {"model_plan_view_extended":True,"browser_revision":6})
                    reject_agent_publish=http(base,"POST","/v2/apps/app-a/publish",
                        token=token,body={
                            "changeId":"b3-agent-forbidden-pub-01",
                            "expectedAppRevision":6,
                            "manifestHash":verify_db(dbfile,"app-a")["manifestHash"]})
                    check("B3-15-agent-not-authorized-to-publish",
                          reject_agent_publish==(403,{"error":"PUBLISH_FORBIDDEN"}) and
                          verify_db(dbfile,"app-a")["currentRelease"] is None,
                          {"http":reject_agent_publish[0],"release":None})
                    tab_b.locator("#publish").click()
                    dom(tab_b,"#published-version","1",exact=True)
                    released=http(base,"GET","/v2/apps/app-a/releases/current",
                                  token=token)
                    physical=verify_db(dbfile,"app-a")
                    check("B3-16-human-approval-publishes-verified-release",
                          released[0]==200 and released[1]["version"]==1 and
                          physical["currentRelease"]==1 and len(physical["releases"])==1 and
                          sha(physical["releases"][0]["definitions"])==
                          physical["releases"][0]["hash"],
                          {"human_approved_version":1,"immutable_hash_verified":True})
                    sid=next(x["value"] for x in context.cookies() if x["name"]=="sid")
                    csrf=sessions[sid][1]
                    def browser_post(route,body):
                        return http(base,"POST","/v2/apps/app-a"+route,
                                    sid=sid,csrf=csrf,body=body)
                    bad_row=browser_post("/runtime/forms/form.contracts/records",{
                        "contract_no":"INVALID-1","title":"Invalid","amount_minor":"100000001"})
                    check("B3-17-published-form-rejects-string-amount",
                          bad_row==(422,{"error":"TYPE_MISMATCH"}),
                          {"http":bad_row[0]})
                    large=browser_post("/runtime/forms/form.contracts/records",{
                        "contract_no":"LLM-2026-1","title":"大额合同","amount_minor":100000001})
                    equal=browser_post("/runtime/forms/form.contracts/records",{
                        "contract_no":"LLM-2026-2","title":"边界合同","amount_minor":100000000})
                    check("B3-18-real-contract-rows-from-model-definitions",
                          large[0]==200 and equal[0]==200 and
                          len(verify_db(dbfile,"app-a")["records"])==2,
                          {"created_records":2,"release":1})
                    def advance(row,action,version):
                        return browser_post(
                            "/runtime/workflows/workflow.approval/records/"+
                            row["recordId"]+"/advance",
                            {"action":action,"expectedVersion":version})
                    h1=advance(large[1],"submit",1)
                    h2=advance(large[1],"approve",2)
                    h3=advance(large[1],"approve",3)
                    l1=advance(equal[1],"submit",1)
                    l2=advance(equal[1],"approve",2)
                    check("B3-19-model-workflow-executes-1m-threshold",
                          all(x[0]==200 for x in (h1,h2,h3,l1,l2)) and
                          [x[1]["status"] for x in (h1,h2,h3)]==
                          ["PendingLevel1","PendingLevel2","Approved"] and
                          [x[1]["status"] for x in (l1,l2)]==
                          ["PendingLevel1","Approved"],
                          {"above_1m_states":[x[1].get("status") for x in (h1,h2,h3)],
                           "equal_1m_states":[x[1].get("status") for x in (l1,l2)]})
                    tab_b.locator("#view").click()
                    dom(tab_b,"#runtime-output","大额合同")
                    rendered=json.loads(tab_b.locator("#runtime-output").inner_text())
                    check("B3-20-actual-chromium-displays-generated-view",
                          rendered["version"]==1 and len(rendered["rows"])==2 and
                          set(rendered["columns"])==
                          {"contract_no","title","amount_minor","status"},
                          {"browser_rows":len(rendered["rows"]),
                           "browser_columns":rendered["columns"]})
                    spec=store.draft(human,"app-a")
                    old_model=spec["resources"]["model.contracts"]
                    unsafe={
                        "changeId":"b3-agent-delete-model-01","resourceId":"model.contracts",
                        "expectedAppRevision":spec["appRevision"],
                        "expectedRevision":old_model["revision"],
                        "baseContentHash":old_model["contentHash"],
                        "definition":None
                    }
                    deletion=http(base,"POST","/v2/apps/app-a/commands",token=token,
                                  body=unsafe)
                    check("B3-21-live-referenced-model-cannot-be-deleted",
                          deletion==(422,{"error":"BROKEN_MODEL_REFERENCE"}),
                          {"http":deletion[0],"release_still":1})
                    no_csrf=browser_post("/runtime/forms/form.contracts/records",{
                        "contract_no":"INTERNAL","title":"Unexpected","amount_minor":1})
                    cookies_rejected=http(base,"POST",
                        "/v2/apps/app-a/runtime/forms/form.contracts/records",
                        sid=sid,body={"contract_no":"NO-CSRF","title":"NO-CSRF",
                                      "amount_minor":1})
                    check("B3-22-real-session-CSRF-enforced",
                          no_csrf[0]==200 and cookies_rejected[0]==403,
                          {"with_csrf":no_csrf[0],"without_csrf":cookies_rejected[0]})
                    # One extra legitimate row above is expected; it is not part
                    # of the workflow and won't be tested as approved.
                    other=verify_db(dbfile,"app-b")
                    final=verify_db(dbfile,"app-a")
                    check("B3-23-physical-SQL-audit-and-app-isolation",
                          other["appRevision"]==0 and other["defs"]=={} and
                          final["appRevision"]==6 and
                          final["receiptCount"]==7 and
                          final["currentRelease"]==1 and
                          any(e["actor"]=="human-approved" for e in final["events"]),
                          {"other_app_revision":0,"draft_revision":6,
                           "receipt_count":final["receiptCount"],
                           "release":1})
                    check("B3-24-inference-label-never-faked",
                          evidence["proposal"]["inference"]==live and
                          evidence["proposal"]["model_calls"]==(1 if live else 0) and
                          evidence["proposal"]["plan_hash"]==plan["planHash"],
                          {"mode":args.mode,"actual_external_model_calls":
                           evidence["proposal"]["model_calls"],
                           "plan_has_independent_runtime_oracle":True})
                    evidence["final_physical_sql_summary"]={
                        "appRevision":final["appRevision"],"currentRelease":final["currentRelease"],
                        "receipts":final["receiptCount"],"recordCount":len(final["records"]),
                        "otherAppRevision":other["appRevision"],"releaseHashMatches":
                        sha(final["releases"][0]["definitions"])==final["releases"][0]["hash"],
                        "auditActors":[e["actor"] for e in final["events"]]
                    }
                finally:
                    context.close()
                    browser.close()
        except Exception as exc:
            # Do not write model raw output/credentials to artifact or terminal.
            evidence["error"]={"kind":type(exc).__name__,
                               "message":str(exc)[:300],
                               "trace":traceback.format_exc()[-1200:]}
            raise
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=4)
            evidence["summary"]={"passed":sum(x["status"]=="PASS" for x in cases),
                                 "attempted":len(cases),"expected":24,
                                 "real_model":evidence["inference"]}
            Path(args.output).write_text(
                json.dumps(evidence,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            print("S1_B3_RESULT "+json.dumps(evidence["summary"]),flush=True)
    return 0 if len(cases)==24 and all(x["status"]=="PASS" for x in cases) else 1

if __name__=="__main__":
    raise SystemExit(main())
