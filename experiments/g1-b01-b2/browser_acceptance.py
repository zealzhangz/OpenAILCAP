#!/usr/bin/env python3
"""Actual Chromium human designer, independent Agent process, published runtime.

Independent read-only SQL oracles; all actual design writes through B2 /commands.
No external LLM; deterministic Agent tool exercises the real HTTP boundary.
"""
from __future__ import annotations

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
from schema_core import Actor, SchemaStore, sha
from schema_http import serve_local

HERE=Path(__file__).resolve().parent
SPECS=json.loads((HERE/"contract_spec.json").read_text(encoding="utf-8"))


def request(base, method, route, token=None, body=None, sid=None, csrf=None):
    headers={}
    if token:
        headers["Authorization"]="Bearer "+token
    if sid:
        headers["Cookie"]="sid="+sid
    if csrf:
        headers["X-CSRF-Token"]=csrf
    payload=None
    if body is not None:
        headers["Content-Type"]="application/json"
        payload=json.dumps(body,ensure_ascii=False).encode()
    req=Request(base+route,method=method,data=payload,headers=headers)
    try:
        with urlopen(req,timeout=15) as r:
            return r.status,json.loads(r.read())
    except HTTPError as e:
        return e.code,json.loads(e.read())


def run_tool(base,token,resource,change_id,spec_file=None,stale=None,delete=False,
             operation="mutate"):
    args=[sys.executable,str(HERE/"tool_client.py"),"--base",base,
          "--operation",operation,"--change-id",change_id]
    if resource:
        args+=["--resource",resource]
    if spec_file:
        args+=["--spec-file",str(spec_file)]
    if stale is not None:
        args+=["--expected-app-revision",str(stale)]
    if delete:
        args+=["--delete"]
    env={"PATH":os.environ.get("PATH",""),"S1_B2_AGENT_TOKEN":token}
    result=subprocess.run(args,env=env,text=True,capture_output=True,
                          timeout=15,check=False)
    if result.returncode:
        raise AssertionError("Agent process failed: "+result.stderr[:300])
    return json.loads(result.stdout)


def read_sql(dbfile,app):
    """Independent physically read-only SQLite connection, not SchemaStore API."""
    with sqlite3.connect("file:"+str(Path(dbfile).resolve())+"?mode=ro",uri=True) as db:
        app_row=db.execute("SELECT revision,manifest_hash,state,current_release "
                           "FROM apps WHERE app=?",(app,)).fetchone()
        resources=db.execute("SELECT rid,revision,hash FROM definitions WHERE app=?",
                             (app,)).fetchall()
        releases=db.execute("SELECT version,manifest,hash FROM releases WHERE app=? "
                            "ORDER BY version",(app,)).fetchall()
        receipts=db.execute("SELECT COUNT(*) FROM receipts WHERE app=?",(app,)).fetchone()[0]
        events=db.execute("SELECT event,actor FROM events WHERE app=? ORDER BY eid",
                          (app,)).fetchall()
        records=db.execute("SELECT record_id,version,content FROM records WHERE app=?",
                           (app,)).fetchall()
    return {"appRevision":app_row[0],"manifestHash":app_row[1],
            "state":app_row[2],"published":app_row[3],
            "resources":[{"rid":r[0],"rev":r[1],"hash":r[2]} for r in resources],
            "releases":[{"version":r[0],"manifest":json.loads(r[1]),"hash":r[2]}
                        for r in releases],
            "receiptCount":receipts,
            "events":[{"event":r[0],"actor":r[1]} for r in events],
            "records":[{"id":r[0],"version":r[1],"data":json.loads(r[2])}
                       for r in records]}


def dom(page,sel,expected,*,exact=False):
    """No eval/JS injection; strict CSP remains enabled."""
    for _ in range(85):
        actual=page.locator(sel).inner_text(timeout=1500)
        if (actual==expected if exact else expected in actual):
            return
        page.wait_for_timeout(140)
    raise AssertionError("Browser DOM did not reach "+sel+" "+expected+
                         "; observed "+actual[:140])


def edit_form_title(page,new_title):
    current=json.loads(page.locator("#definition").input_value())
    if current.get("kind")!="form":
        raise AssertionError("Expected selected form")
    current["title"]=new_title
    page.locator("#definition").fill(json.dumps(current,ensure_ascii=False,indent=2))
    page.locator("#save").click()


def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True)
    args=p.parse_args()
    cases=[]
    evidence={"study":"S1 B2 typed DataModel Form View Workflow Manifest and immutable release",
              "scope":"OWNED_MINIMAL_ENGINE_NOT_PLATFORM_OR_SALTCORN_NATIVE",
              "real_chromium":True,"real_external_agent_process":True,
              "model_inference_executed":False,"real_plugin_sandbox":False,
              "full_G1_pass":False,"cases":cases}
    def check(name,condition,observed):
        entry={"id":name,"status":"PASS" if condition else "FAIL","observed":observed}
        cases.append(entry)
        print("B2 "+name+" "+entry["status"]+" "+json.dumps(observed,ensure_ascii=False),
              flush=True)
        if not condition:
            raise AssertionError(name)

    with tempfile.TemporaryDirectory() as tmp:
        dbfile=Path(tmp)/"b2.sqlite"
        store=SchemaStore(dbfile)
        store.init()
        store.seed_app_for_test("app-a")
        store.seed_app_for_test("app-b")
        human=Actor("human-designer","app-a",can_publish=True,can_runtime=True)
        agent=Actor("agent-tool","app-a")
        plugin=Actor("plugin-view-only","app-a",kinds=("view",))
        token=secrets.token_urlsafe(30)
        plugin_token=secrets.token_urlsafe(30)
        password=secrets.token_urlsafe(30)
        sessions={}
        server=serve_local(store,{token:agent,plugin_token:plugin},sessions,human,password)
        host="http://127.0.0.1:"+str(server.server_port)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        evidence["environment"]={"bind":"127.0.0.1","database":"ephemeral SQLite",
                                 "agent":"independent Python subprocess via Bearer HTTP"}
        try:
            check("B2-01-local-host-ready",
                  request(host,"GET","/health")[0]==200,
                  {"http":200,"database_file_exists":dbfile.exists()})
            for num,rid in enumerate(SPECS,1):
                result=run_tool(host,token,rid,f"seed-agent-{num:02}")
                check(f"B2-{num+1:02}-agent-create-{rid}",
                      result["http"]==200 and
                      result["result"]["appRevision"]==num,
                      {"http":result["http"],"appRevision":result["result"].get("appRevision")})
            initial=request(host,"GET","/v2/apps/app-a/draft",token=token)
            check("B2-06-typed-manifest-physical-hash",
                  initial[0]==200 and initial[1]["manifestHash"]==sha(SPECS) and
                  read_sql(dbfile,"app-a")["appRevision"]==4,
                  {"model_kind_count":4,"revision":initial[1]["appRevision"],
                   "manifest_hash_matches":initial[1]["manifestHash"]==sha(SPECS)})
            with sync_playwright() as pw:
                browser=pw.chromium.launch(headless=True,args=["--no-sandbox"])
                context=browser.new_context()
                try:
                    login=context.new_page()
                    login.goto(host+"/editor/app-a",wait_until="domcontentloaded")
                    check("B2-07-unauthenticated-editor-redirect",
                          login.url.endswith("/editor/login"),
                          {"redirect":"/editor/login"})
                    login.locator("#password").fill(password)
                    login.locator("#login").click()
                    login.wait_for_url("**/editor/app-a")
                    dom(login,"#revision","4",exact=True)
                    check("B2-08-real-login-editor-renders-4-resources",
                          "form.contracts" in login.locator("#resources").inner_text() and
                          login.locator("#published-version").inner_text()=="未发布",
                          {"real_chromium":True,"form_in_resources":True})
                    a=context.new_page();b=context.new_page()
                    a.goto(host+"/editor/app-a",wait_until="domcontentloaded")
                    b.goto(host+"/editor/app-a",wait_until="domcontentloaded")
                    dom(a,"#revision","4",exact=True)
                    dom(b,"#revision","4",exact=True)
                    check("B2-09-two-tabs-same-draft-baseline",
                          json.loads(a.locator("#definition").input_value())["title"]=="合同登记" and
                          json.loads(b.locator("#definition").input_value())["title"]=="合同登记",
                          {"a_revision":4,"b_revision":4})
                    edit_form_title(a,"合同登记 · 人工维护")
                    dom(a,"#message","保存成功")
                    check("B2-10-human-change-form-via-typed-HTTP",
                          read_sql(dbfile,"app-a")["appRevision"]==5 and
                          store.draft(human,"app-a")["resources"]["form.contracts"]["definition"]["title"]==
                          "合同登记 · 人工维护",
                          {"revision":5,"human_edit_preserved":True})
                    new_specs=copy.deepcopy(SPECS)
                    new_specs["view.contracts"]["columns"].insert(1,"title")
                    altered=Path(tmp)/"agent-new-view.json"
                    altered.write_text(json.dumps(new_specs,ensure_ascii=False),encoding="utf-8")
                    stale=run_tool(host,token,"view.contracts","agent-view-stale-01",
                                   spec_file=altered,stale=4)
                    check("B2-11-agent-older-app-revision-rejected",
                          stale["http"]==409 and
                          stale["result"].get("error")=="APP_REVISION_CONFLICT" and
                          read_sql(dbfile,"app-a")["appRevision"]==5,
                          {"agent_http":stale["http"],"error":stale["result"].get("error")})
                    current=run_tool(host,token,"view.contracts","agent-view-fresh-02",
                                     spec_file=altered)
                    check("B2-12-agent-rebase-preserves-human-change",
                          current["http"]==200 and
                          read_sql(dbfile,"app-a")["appRevision"]==6 and
                          store.draft(human,"app-a")["resources"]["form.contracts"]["definition"]["title"]==
                          "合同登记 · 人工维护",
                          {"agent_http":current["http"],"revision":6})
                    edit_form_title(b,"stale overwrite")
                    dom(b,"#message","409 APP_REVISION_CONFLICT")
                    check("B2-13-old-browser-form-no-silent-overwrite",
                          store.draft(human,"app-a")["resources"]["form.contracts"]["definition"]["title"]==
                          "合同登记 · 人工维护",
                          {"browser_conflict":409,"current_revision":6})
                    b.locator("#reload").click()
                    dom(b,"#revision","6",exact=True)
                    b.locator("#resource-id").fill("view.contracts")
                    b.locator("#select").click()
                    view_b=json.loads(b.locator("#definition").input_value())
                    check("B2-14-human-sees-agent-view-after-reload",
                          "title" in view_b["columns"] and
                          "合同登记 · 人工维护"==store.draft(
                              human,"app-a")["resources"]["form.contracts"]["definition"]["title"],
                          {"view_columns":view_b["columns"]})
                    no_publish=request(host,"POST","/v2/apps/app-a/publish",token=token,
                                       body={"changeId":"agent-publish-denied-01",
                                             "expectedAppRevision":6,
                                             "manifestHash":store.draft(
                                                 human,"app-a")["manifestHash"]})
                    check("B2-15-agent-cannot-publish",
                          no_publish[0]==403 and
                          read_sql(dbfile,"app-a")["published"] is None,
                          {"http":no_publish[0],"error":no_publish[1]["error"]})
                    b.locator("#publish").click()
                    dom(b,"#published-version","1",exact=True)
                    release1=request(host,"GET","/v2/apps/app-a/releases/current",token=token)
                    physical1=read_sql(dbfile,"app-a")
                    check("B2-16-human-publishes-immutable-snapshot",
                          release1[0]==200 and release1[1]["version"]==1 and
                          physical1["releases"][0]["hash"]==
                          sha(physical1["releases"][0]["manifest"]) and
                          physical1["published"]==1,
                          {"release":1,"hash_matches":True})
                    sid=next(c["value"] for c in context.cookies() if c["name"]=="sid")
                    csrf=sessions[sid][1]
                    def web_post(path,body):
                        return request(host,"POST","/v2/apps/app-a"+path,
                                       sid=sid,csrf=csrf,body=body)
                    invalid=web_post("/runtime/forms/form.contracts/records",
                                     {"contract_no":"C-001","title":"错误金额",
                                      "amount_minor":"100000001"})
                    check("B2-17-runtime-types-are-enforced",
                          invalid[0]==422 and
                          invalid[1].get("error")=="TYPE_MISMATCH",
                          {"http":invalid[0],"error":invalid[1].get("error")})
                    large=web_post("/runtime/forms/form.contracts/records",
                                   {"contract_no":"CT-LARGE","title":"大额合同",
                                    "amount_minor":100000001})
                    small=web_post("/runtime/forms/form.contracts/records",
                                   {"contract_no":"CT-EXACT","title":"边界合同",
                                    "amount_minor":100000000})
                    check("B2-18-real-form-creates-typed-rows",
                          large[0]==200 and small[0]==200 and
                          len(read_sql(dbfile,"app-a")["records"])==2 and
                          large[1]["data"]["status"]=="Draft",
                          {"http_statuses":[large[0],small[0]],
                           "rows":2,"state":"Draft"})
                    def advance(row,action,version):
                        return web_post(
                            "/runtime/workflows/workflow.approval/records/"+
                            row["recordId"]+"/advance",
                            {"action":action,"expectedVersion":version})
                    high1=advance(large[1],"submit",1)
                    high2=advance(large[1],"approve",2)
                    high3=advance(large[1],"approve",3)
                    low1=advance(small[1],"submit",1)
                    low2=advance(small[1],"approve",2)
                    badagain=advance(large[1],"approve",4)
                    check("B2-19-threshold-workflow-state-machine",
                          all(r[0]==200 for r in (high1,high2,high3,low1,low2)) and
                          [r[1]["status"] for r in (high1,high2,high3)]==
                          ["PendingLevel1","PendingLevel2","Approved"] and
                          low2[1]["status"]=="Approved" and
                          badagain[0]==409,
                          {"high_path":[r[1].get("status") for r in (high1,high2,high3)],
                           "exact_threshold_path":[low1[1].get("status"),low2[1].get("status")],
                           "invalid_repeat_http":badagain[0]})
                    b.locator("#view").click()
                    dom(b,"#runtime-output","大额合同")
                    viewed=json.loads(b.locator("#runtime-output").inner_text())
                    check("B2-20-real-chromium-published-view",
                          viewed["version"]==1 and
                          viewed["columns"]==new_specs["view.contracts"]["columns"] and
                          len(viewed["rows"])==2 and
                          all(row["cells"]["status"]=="Approved" for row in viewed["rows"]),
                          {"release":viewed["version"],"rows":len(viewed["rows"]),
                           "columns":viewed["columns"]})
                    deletion=run_tool(host,token,"model.contracts",
                                      "agent-delete-model-01",delete=True)
                    check("B2-21-cannot-delete-referenced-model",
                          deletion["http"]==422 and
                          deletion["result"].get("error")=="BROKEN_MODEL_REFERENCE" and
                          read_sql(dbfile,"app-a")["appRevision"]==6,
                          {"http":deletion["http"],"error":deletion["result"].get("error")})
                    malicious=copy.deepcopy(new_specs)
                    malicious["view.contracts"]["columns"].append("ghost")
                    badspec=Path(tmp)/"bad-spec.json"
                    badspec.write_text(json.dumps(malicious,ensure_ascii=False))
                    broken=run_tool(host,token,"view.contracts",
                                    "agent-broken-ref-02",spec_file=badspec)
                    check("B2-22-dangling-field-reference-rejected",
                          broken["http"]==422 and
                          broken["result"].get("error")=="BROKEN_FIELD_REFERENCE" and
                          read_sql(dbfile,"app-a")["appRevision"]==6,
                          {"http":broken["http"],"error":broken["result"].get("error")})
                    b.locator("#resource-id").fill("form.contracts")
                    b.locator("#select").click()
                    edit_form_title(b,"合同登记 · 草稿第二版")
                    dom(b,"#revision","7",exact=True)
                    current_release=request(host,"GET","/v2/apps/app-a/releases/current",
                                            token=token)
                    check("B2-23-draft-cannot-alter-live-release",
                          current_release[1]["version"]==1 and
                          current_release[1]["definitions"]["form.contracts"]["title"]==
                          "合同登记 · 人工维护",
                          {"draft_revision":7,"live_version":1,
                           "live_form_title_unchanged":True})
                    stale_publish=web_post("/publish",{
                        "changeId":"web-stale-publish-01","expectedAppRevision":6,
                        "manifestHash":current_release[1]["manifestHash"]})
                    check("B2-24-stale-release-attempt-fails-closed",
                          stale_publish[0]==409 and
                          read_sql(dbfile,"app-a")["published"]==1,
                          {"http":stale_publish[0],
                           "error":stale_publish[1].get("error")})
                    b.locator("#publish").click()
                    dom(b,"#published-version","2",exact=True)
                    current_release=request(host,"GET","/v2/apps/app-a/releases/current",
                                            token=token)
                    rollback=web_post("/rollback",{
                        "changeId":"human-rollback-01","expectedPublishedVersion":2,
                        "targetVersion":1})
                    after_rollback=request(host,"GET","/v2/apps/app-a/releases/current",
                                           token=token)
                    check("B2-25-publish-v2-and-rollback-pointer-v1",
                          current_release[1]["version"]==2 and
                          current_release[1]["definitions"]["form.contracts"]["title"]==
                          "合同登记 · 草稿第二版" and
                          rollback[0]==200 and after_rollback[1]["version"]==1 and
                          read_sql(dbfile,"app-a")["published"]==1,
                          {"v2_published":True,"rollback_http":rollback[0],
                           "active_release":1})
                    with sqlite3.connect(dbfile) as conn:
                        conn.execute("UPDATE definitions SET spec=? "
                                     "WHERE app='app-a' AND rid='view.contracts'",
                                     ('{"kind":"view","title":"UNSAFE","model":"model.contracts",'
                                      '"columns":["contract_no"]}',))
                    drift=request(host,"GET","/v2/apps/app-a/draft",token=token)
                    invalid_publish=web_post("/publish",{
                        "changeId":"after-drift-denied",
                        "expectedAppRevision":7,
                        "manifestHash":read_sql(dbfile,"app-a")["manifestHash"]})
                    live=request(host,"GET","/v2/apps/app-a/runtime/views/view.contracts",
                                 sid=sid)
                    check("B2-26-out-of-band-draft-quarantine-last-release-still-works",
                          drift[0]==409 and
                          drift[1].get("error")=="RESOURCE_DRIFT" and
                          invalid_publish[0]==423 and
                          read_sql(dbfile,"app-a")["state"]=="QUARANTINED" and
                          live[0]==200 and live[1]["version"]==1,
                          {"drift_http":drift[0],"publish_http":invalid_publish[0],
                           "live_http":live[0],"live_version":live[1].get("version")})
                    other=read_sql(dbfile,"app-b")
                    final=read_sql(dbfile,"app-a")
                    check("B2-27-cross-app-and-independent-oracle",
                          other["appRevision"]==0 and other["resources"]==[] and
                          len(final["releases"])==2 and len(final["records"])==2 and
                          any(e["actor"]=="agent-tool" for e in final["events"]) and
                          any(e["actor"]=="human-designer" for e in final["events"]),
                          {"other_app_revision":other["appRevision"],
                           "versions":[r["version"] for r in final["releases"]],
                           "runtime_record_count":len(final["records"])})
                    evidence["independent_sql_summary"]={
                        "applicationRevision":final["appRevision"],
                        "publishedVersion":final["published"],
                        "releaseCount":len(final["releases"]),
                        "resourceCount":len(final["resources"]),
                        "recordCount":len(final["records"]),
                        "appBRevision":other["appRevision"],
                        "state":final["state"],
                        "auditEventTypes":[e["event"] for e in final["events"]],
                    }
                finally:
                    context.close()
                    browser.close()
        except Exception as exc:
            evidence["error"]={"class":type(exc).__name__,
                               "message":str(exc)[:1000],
                               "trace":traceback.format_exc()[-1700:]}
            raise
        finally:
            server.shutdown();server.server_close();thread.join(timeout=4)
            evidence["summary"]={"passed":sum(c["status"]=="PASS" for c in cases),
                                 "attempted":len(cases),"expected":27}
            Path(args.output).write_text(
                json.dumps(evidence,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            print("S1_B2_RESULT "+json.dumps(evidence["summary"]),flush=True)
    return 0 if len(cases)==27 and all(c["status"]=="PASS" for c in cases) else 1

if __name__=="__main__":
    raise SystemExit(main())
