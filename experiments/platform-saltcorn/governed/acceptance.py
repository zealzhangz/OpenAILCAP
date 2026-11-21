#!/usr/bin/env python3
"""Independent acceptance for a *lab-owned* gateway over real Saltcorn metadata.

Actual Chromium human session uses the research gateway HTML, not Saltcorn's
native /field route. Automation uses raw bearer HTTP, never an LLM.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import sqlite3
import sys
import traceback
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

from playwright.sync_api import sync_playwright


def request(base, method, path, token=None, payload=None, headers=None):
    headers = dict(headers or {})
    if token:
        headers["Authorization"] = "Bearer " + token
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload, ensure_ascii=False).encode()
    req = Request(base + path, data=body, method=method, headers=headers)
    try:
        with urlopen(req, timeout=25) as res:
            status, content = res.status, res.read().decode()
    except HTTPError as exc:
        status, content = exc.code, exc.read().decode()
    try:
        data = json.loads(content)
    except ValueError:
        data = {"_not_json": content[:100]}
    return status, data


def native_label(db_path, resource):
    with sqlite3.connect(f"file:{Path(db_path).resolve()}?mode=ro", uri=True) as db:
        row = db.execute("SELECT f.label FROM _sc_fields f JOIN _sc_tables t "
                         "ON f.table_id=t.id WHERE t.name=? AND f.name=?",
                         ("s1_contracts", resource)).fetchone()
        return row[0]


def ledgers(db_path):
    with sqlite3.connect(f"file:{Path(db_path).resolve()}?mode=ro", uri=True) as db:
        revisions = dict(db.execute("SELECT resource_id,revision FROM _openailcap_s1_http_guard"))
        audit = list(db.execute(
            "SELECT actor,resource_id,outcome,change_id FROM _openailcap_s1_http_audit ORDER BY id"))
        change_ids = set(x[0] for x in db.execute("SELECT change_id FROM _openailcap_s1_http_changes"))
    return revisions, audit, change_ids


def run_main(args, record):
    base = args.base
    app = "/api/apps/s1-contract/resources/"
    agent, readonly = os.environ["S1_AGENT_TOKEN"], os.environ["S1_READ_TOKEN"]
    pw = os.environ["S1_HUMAN_PASSWORD"]

    status, data = request(base, "GET", "/health")
    record("G01-real-gateway-health", status == 200 and data.get("status") == "OK",
           {"status": status})
    status, data = request(base, "GET", app+"title")
    record("G02-unauthenticated-API-rejected", status == 401,
           {"status": status, "error": data.get("error")})
    status, data = request(base, "GET", app+"title", token=readonly)
    record("G03-readonly-can-read", status == 200 and data.get("revision") == 0,
           {"status": status, "revision": data.get("revision")})
    base_title = data
    status, data = request(base, "POST", app+"title", token=readonly,
                           payload={"change_id":uuid4().hex, "label":"Forbidden",
                                    "base_revision":0,"base_fingerprint":base_title["fingerprint"]})
    record("G04-readonly-cannot-write", status == 403 and data.get("error") == "READ_ONLY",
           {"status": status, "error": data.get("error")})
    status, data = request(base, "GET", "/api/apps/another-app/resources/title",token=agent)
    record("G05-cross-app-rejected", status == 403 and data.get("error") == "APP_FORBIDDEN",
           {"status": status, "error": data.get("error")})
    status, data = request(base, "POST", app+"title",token=agent,
                           payload={"change_id":uuid4().hex,"label":"",
                                    "base_revision":0,"base_fingerprint":base_title["fingerprint"]})
    record("G06-invalid-input-422", status == 422 and data.get("error") == "INVALID_LABEL",
           {"status": status, "error": data.get("error")})

    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
        ctx=browser.new_context()
        no_session=browser.new_context()
        anon=no_session.new_page()
        anon.goto(base+"/edit/title")
        record("G07-unauthenticated-browser-redirect",
               anon.url.endswith("/login"), {"path":anon.url.split(":3200")[-1]})
        page=ctx.new_page()
        page.goto(base+"/login")
        page.locator('input[name="password"]').fill(pw)
        page.get_by_role("button",name="Log in").click()
        record("G08-real-browser-human-login",
               page.url.endswith("/edit/title") and
               page.locator('input[name="label"]').count()==1,
               {"path":page.url.split(":3200")[-1]})
        a=ctx.new_page()
        b=ctx.new_page()
        a.goto(base+"/edit/title")
        b.goto(base+"/edit/title")
        same=(a.locator('input[name="label"]').input_value()=="Title" and
              b.locator('input[name="label"]').input_value()=="Title")
        record("G09-two-browser-tabs-same-base",same,{"both_initial":"Title" if same else "DIFFERENT"})
        b.locator('input[name="label"]').fill("Browser Governed Title")
        with b.expect_response(lambda r:r.request.method=="POST" and "/edit/title" in r.url) as ev:
            b.get_by_role("button",name="Save").click()
        first_code=ev.value.status
        record("G10-real-browser-atomic-save",
               first_code==200 and native_label(args.db,"title")=="Browser Governed Title",
               {"http_status":first_code,"native_label":native_label(args.db,"title")})
        a.locator('input[name="label"]').fill("Old Tab Cannot Overwrite")
        with a.expect_response(lambda r:r.request.method=="POST" and "/edit/title" in r.url) as ev:
            a.get_by_role("button",name="Save").click()
        stale_code=ev.value.status
        record("G11-stale-web-form-gets-409",
               stale_code==409 and native_label(args.db,"title")=="Browser Governed Title",
               {"http_status":stale_code,"native_label":native_label(args.db,"title")})
        csrf_request=ctx.request.post(
            base+"/edit/title", data=urlencode({
                "label":"Malicious Form", "base_revision":"1",
                "base_fingerprint":base_title["fingerprint"],"change_id":uuid4().hex
            }),headers={"Content-Type":"application/x-www-form-urlencoded"})
        record("G12-real-session-without-csrf-rejected",
               csrf_request.status==403 and native_label(args.db,"title")=="Browser Governed Title",
               {"http_status":csrf_request.status})
        no_session.close()
        browser.close()

    status, current_title = request(base,"GET",app+"title",token=agent)
    record("G13-agent-sees-browser-revision",
           status==200 and current_title.get("revision")==1 and
           current_title.get("label")=="Browser Governed Title",
           {"status":status,"revision":current_title.get("revision")})
    status, data = request(base,"POST",app+"title",token=agent,payload={
        "label":"Blind Agent Change","base_revision":0,
        "base_fingerprint":base_title["fingerprint"],"change_id":uuid4().hex})
    record("G14-agent-stale-base-rejected",
           status==409 and data.get("error")=="VERSION_CONFLICT",
           {"status":status,"error":data.get("error")})

    st, current_status = request(base,"GET",app+"status",token=agent)
    assert st==200
    first_change={"label":"Automated Status","base_revision":current_status["revision"],
                 "base_fingerprint":current_status["fingerprint"],"change_id":uuid4().hex}
    st, receipt = request(base,"POST",app+"status",token=agent,payload=first_change)
    record("G15-agent-nonoverlap-preserves-browser",
           st==200 and native_label(args.db,"title")=="Browser Governed Title"
           and native_label(args.db,"status")=="Automated Status",
           {"status":st,"title":native_label(args.db,"title"),"status_label":native_label(args.db,"status")})
    st, replay = request(base,"POST",app+"status",token=agent,payload=first_change)
    record("G16-idempotent-retry",
           st==200 and replay.get("replayed") is True and replay.get("revision")==1,
           {"status":st,"replayed":replay.get("replayed")})
    changed={**first_change,"label":"Changed But Same Id"}
    st, data=request(base,"POST",app+"status",token=agent,payload=changed)
    record("G17-idempotency-key-conflict",
           st==409 and data.get("error")=="CHANGE_ID_REUSED",
           {"status":st,"error":data.get("error")})

    st, concurrent_status=request(base,"GET",app+"status",token=agent)
    assert st==200 and concurrent_status["revision"]==1
    def compete(i):
        payload={"label":f"Concurrent {i}","base_revision":1,
                 "base_fingerprint":concurrent_status["fingerprint"],"change_id":uuid4().hex}
        return request(base,"POST",app+"status",token=agent,payload=payload)
    with ThreadPoolExecutor(max_workers=2) as pool:
        future1=pool.submit(compete,"A")
        future2=pool.submit(compete,"B")
        responses=[future1.result(),future2.result()]
    record("G18-two-independent-http-requests-one-wins",
           sorted(status for status,_ in responses)==[200,409],
           {"http_statuses":[x[0] for x in responses]})
    st, state=request(base,"GET",app+"status",token=agent)
    record("G19-real-resource-version-increments-once",
           st==200 and state.get("revision")==2 and
           native_label(args.db,"status") in ("Concurrent A","Concurrent B"),
           {"status":st,"revision":state.get("revision")})

    st,before=request(base,"GET",app+"title",token=agent)
    assert st==200
    injected_id=uuid4().hex
    st,data=request(base,"POST",app+"title",token=agent,
        payload={"label":"Injected Must Roll Back","base_revision":before["revision"],
                 "base_fingerprint":before["fingerprint"],"change_id":injected_id},
        headers={"X-S1-Inject-Failure":"after-write"})
    st2,after=request(base,"GET",app+"title",token=agent)
    revisions,audit,changes=ledgers(args.db)
    record("G20-physical-transaction-rollback",
           st==500 and data.get("error")=="INJECTED_ROLLBACK" and
           st2==200 and after==before and injected_id not in changes,
           {"http_status":st,"after_revision":after.get("revision"),
            "after_label":after.get("label"),"injected_event_absent":injected_id not in changes})

    valid_id=uuid4().hex
    st,receipt=request(base,"POST",app+"title",token=agent,
        payload={"label":"Agent After Verified Refresh","base_revision":before["revision"],
                 "base_fingerprint":before["fingerprint"],"change_id":valid_id})
    record("G21-agent-can-edit-after-refresh",st==200 and receipt.get("revision")==2,
           {"http_status":st,"revision":receipt.get("revision")})
    revisions,audit,changes=ledgers(args.db)
    accepted=[x for x in audit if x[2]=="APPLIED"]
    rejected=[x for x in audit if x[2]=="VERSION_CONFLICT"]
    record("G22-audit-who-and-change-id",
           any(x[0]=="human" for x in accepted) and
           any(x[0]=="agent" for x in accepted) and
           len(rejected)>=2 and valid_id in changes,
           {"accepted_count":len(accepted),"version_conflicts":len(rejected),
            "has_human_and_agent":set(x[0] for x in accepted)>={"human","agent"}})
    return {"concurrency_statuses":[x[0] for x in responses]}


def run_drift(args, record):
    app="/api/apps/s1-contract/resources/title"
    agent=os.environ["S1_AGENT_TOKEN"]
    with sqlite3.connect(f"file:{Path(args.db).resolve()}?mode=ro",uri=True) as db:
        guard=db.execute("SELECT revision,fingerprint FROM _openailcap_s1_http_guard "
                         "WHERE resource_id='title'").fetchone()
    label=native_label(args.db,"title")
    record("D01-real-native-out-of-band-write-observed",label=="Native Outside Gateway",
           {"native_label":label})
    st,data=request(args.base,"GET",app,token=agent)
    record("D02-gateway-read-fails-closed-on-drift",
           st==409 and data.get("error")=="OUT_OF_BAND_DRIFT",
           {"status":st,"error":data.get("error")})
    change_id=uuid4().hex
    st,data=request(args.base,"POST",app,token=agent,payload={
        "label":"Must Not Overwrite Native Change","base_revision":guard[0],
        "base_fingerprint":guard[1],"change_id":change_id})
    revisions,audit,changes=ledgers(args.db)
    record("D03-agent-write-denied-on-native-drift",
           st==409 and data.get("error")=="OUT_OF_BAND_DRIFT" and
           native_label(args.db,"title")=="Native Outside Gateway",
           {"status":st,"error":data.get("error")})
    record("D04-ledger-and-events-not-falsely-advanced",
           revisions.get("title")==guard[0] and change_id not in changes,
           {"revision":revisions.get("title"),"change_id_committed":change_id in changes})


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--phase",choices=["main","drift"],required=True)
    p.add_argument("--db",required=True)
    p.add_argument("--base",default="http://127.0.0.1:3200")
    p.add_argument("--output",required=True)
    args=p.parse_args()
    cases=[]
    def record(name,ok,observed):
        cases.append({"id":name,"passed":bool(ok),"observed":observed})
        print(name,"PASS" if ok else "FAIL",json.dumps(observed,ensure_ascii=False),flush=True)
    result={"study":"OpenAILCAP S1 shared governed HTTP resource editing research",
            "phase":args.phase,"real_saltcorn_sqlite":True,
            "browser_is_lab_gateway_not_native_saltcorn_editor":True,
            "real_llm_agent":False,"production_gateway":False,"cases":cases}
    try:
        if args.phase=="main":
            run_main(args,record)
        else:
            run_drift(args,record)
    except Exception as exc:
        result["unhandled_error"]={"type":type(exc).__name__,"message":str(exc)[:800],
                                   "traceback_tail":traceback.format_exc()[-1800:]}
        print("ACCEPTANCE_ERROR",str(exc),file=sys.stderr)
    result["summary"]={"total":len(cases),"passed":sum(x["passed"] for x in cases)}
    Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return 0 if len(cases)==(22 if args.phase=="main" else 4) and all(x["passed"] for x in cases) else 1


if __name__=="__main__":
    raise SystemExit(main())
