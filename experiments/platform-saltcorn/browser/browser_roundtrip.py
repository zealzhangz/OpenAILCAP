#!/usr/bin/env python3
"""Actual Chromium browser-session and Saltcorn field wizard stale-page probe.

All browser interactions use Playwright DOM controls and regular CSRF-protected
web pages. No direct programmatic SQL writes are made by this script.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import traceback

from playwright.sync_api import sync_playwright

def db_value(dbpath: str, field: str = "title"):
    with sqlite3.connect(f"file:{Path(dbpath).resolve()}?mode=ro", uri=True) as db:
        row = db.execute(
            "SELECT label FROM _sc_fields WHERE table_id="
            "(SELECT id FROM _sc_tables WHERE name='s1_contracts') AND name=?",
            (field,)).fetchone()
        if not row:
            raise AssertionError(f"missing real Saltcorn field: {field}")
        return row[0]

def field_id(dbpath: str):
    with sqlite3.connect(f"file:{Path(dbpath).resolve()}?mode=ro", uri=True) as db:
        row = db.execute(
            "SELECT id FROM _sc_fields WHERE table_id="
            "(SELECT id FROM _sc_tables WHERE name='s1_contracts') AND name='title'"
        ).fetchone()
        if not row:
            raise AssertionError("missing title field")
        return row[0]

def save_wizard(page, new_label, trace):
    """Save via the actual web form, completing all wizard steps via DOM clicks."""
    inputs = page.locator('input[name="label"]')
    if inputs.count() != 1:
        raise AssertionError(f"Expected exactly one editable label input, saw {inputs.count()} at {page.url}")
    inputs.fill(new_label)
    for i in range(9):
        if "/table/" in page.url and "/field" not in page.url:
            return
        forms = page.locator('form').filter(has=page.locator('input[name="contextEnc"]'))
        if forms.count() != 1:
            raise AssertionError(f"Expected one real wizard form, got {forms.count()} at {page.url}")
        form = forms.first
        step = form.locator('input[name="stepName"]').input_value() if form.locator('input[name="stepName"]').count() else "unknown"
        action = form.get_attribute("action")
        buttons = form.locator('button[type="submit"], input[type="submit"]')
        names = []
        for j in range(buttons.count()):
            el = buttons.nth(j)
            names.append({"value":el.get_attribute("value") or "",
                          "text":el.inner_text() if el.evaluate("(e)=>e.tagName.toLowerCase()") == "button" else ""})
        if buttons.count() == 0:
            raise AssertionError(f"No actual wizard submit button, step={step}")
        buttons.last.click()
        page.wait_for_load_state("domcontentloaded",timeout=25000)
        trace.append({"step":step,"form_action":action,"button_labels":names,"after_url_path":page.url.split("3100")[-1][:150]})
        if "/table/" in page.url and "/field" not in page.url:
            return
    raise AssertionError("Field editing wizard exceeded 9 steps; possible validation loop")

def test(args):
    evidence={"study":"S1 actual Chromium human UI stale Saltcorn field edit",
              "mode":"real browser admin login + actual HTTP form/csrf/redirect",
              "source_platform":"@saltcorn/cli@1.7.0-beta.5",
              "is_real_agent":False,"is_real_ai":False,
              "is_real_browser":True,"cases":[],"requests":[],"wizard_trace":[]}
    def note(cid,ok,observed):
        evidence["cases"].append({"id":cid,"status":"PASS" if ok else "FAIL",
                                  "observed":observed})
        print(cid,"PASS" if ok else "FAIL",json.dumps(observed,ensure_ascii=False),flush=True)
    original=db_value(args.db)
    note("UI01-initial-field",original=="Title",{"field_label":original})
    fid=field_id(args.db)
    base=f"http://127.0.0.1:{args.port}"
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
        ctx=browser.new_context(ignore_https_errors=False)
        admin=ctx.new_page()
        admin.goto(base+"/auth/login",wait_until="domcontentloaded")
        admin.locator('input[name="email"]').fill("s1-research-admin@example.invalid")
        admin.locator('input[name="password"]').fill(args.password)
        admin.locator('form[action="/auth/login"] button[type="submit"], form[action="/auth/login"] input[type="submit"]').last.click()
        admin.wait_for_load_state("domcontentloaded")
        a=ctx.new_page()
        a.goto(base+f"/field/{fid}",wait_until="domcontentloaded")
        logged_in=a.locator('input[name="label"]').count()==1
        note("UI02-authenticated-editor",logged_in,{"editor_path":a.url.split("3100")[-1],
             "has_label_input":logged_in})
        if not logged_in:
            raise AssertionError("Authenticated admin browser could not open field editor")
        htmlform=a.locator("form").filter(has=a.locator('input[name="contextEnc"]')).first
        raw_fields=htmlform.locator("input").evaluate_all("(els)=>els.map(e=>e.name)")
        note("UI03-actual-form-context-and-csrf",
             "contextEnc" in raw_fields and "_csrf" in raw_fields,
             {"form_field_names":sorted(set(raw_fields))})
        b=ctx.new_page()
        b.goto(base+f"/field/{fid}",wait_until="domcontentloaded")
        note("UI04-two-stale-pages",a.locator('input[name="label"]').input_value()=="Title" and
             b.locator('input[name="label"]').input_value()=="Title",
             {"initial_a":a.locator('input[name="label"]').input_value(),
              "initial_b":b.locator('input[name="label"]').input_value()})
        def monitor_request(req):
            if req.method=="POST" and req.url.split("?")[0].rstrip("/").endswith("/field"):
                evidence["requests"].append({"method":"POST","path":"/field","route":"normal_browser",
                    "has_contextEnc":"contextEnc=" in (req.post_data or ""),
                    "has_csrf":"_csrf=" in (req.post_data or "")})
        a.on("request",monitor_request)
        b.on("request",monitor_request)
        save_wizard(b,"Browser B Saved",evidence["wizard_trace"])
        after_b=db_value(args.db)
        note("UI05-browser-B-saved-db",after_b=="Browser B Saved",{"db_label":after_b})
        save_wizard(a,"Browser A Stale Save",evidence["wizard_trace"])
        after_a=db_value(args.db)
        # This explicitly tests native UI behavior, including an UNSAFE overwrite.
        note("UI06-stale-browser-overwrites-B",after_a=="Browser A Stale Save",
             {"db_label":after_a,"previous_browser_label":"Browser B Saved",
              "unsafe_lost_update":after_a=="Browser A Stale Save"})
        fresh=ctx.new_page()
        fresh.goto(base+f"/field/{fid}",wait_until="domcontentloaded")
        ui_label=fresh.locator('input[name="label"]').input_value()
        note("UI07-server-reopen-shows-new-field",ui_label=="Browser A Stale Save",
             {"field_label":ui_label})
        guest=browser.new_context()
        guest_page=guest.new_page()
        guest_page.goto(base+f"/field/{fid}",wait_until="domcontentloaded")
        guest_denied=guest_page.url.endswith("/auth/login") or "/auth/login" in guest_page.url
        note("UI08-no-cookie-cannot-edit",guest_denied,{"redirect_path":guest_page.url.split("3100")[-1]})
        note("UI09-normal-forms-really-posted",len(evidence["requests"])>=2 and all(
            x["has_contextEnc"] and x["has_csrf"] for x in evidence["requests"]),
            {"post_count":len(evidence["requests"]),"request_summaries":evidence["requests"]})
        guest.close()
        browser.close()
    evidence["summary"]={"passed":sum(x["status"]=="PASS" for x in evidence["cases"]),
                         "total":len(evidence["cases"])}
    return evidence

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--db",required=True)
    p.add_argument("--port",type=int,default=3100)
    p.add_argument("--output",required=True)
    p.add_argument("--password",default=os.getenv("S1_ADMIN_PASSWORD"))
    args=p.parse_args()
    if not args.password: raise SystemExit("S1_ADMIN_PASSWORD missing")
    out=Path(args.output)
    try:
        result=test(args)
    except Exception as e:
        result={"study":"S1 actual Chromium human field editor",
                "status":"ERROR_NOT_VERIFIED",
                "error_type":type(e).__name__,
                "error":str(e)[:1200],
                "traceback":traceback.format_exc()[-2500:],
                "scope":"Test stopped; no success claimed"}
        print("ACTUAL_BROWSER_TEST_ERROR",str(e),file=sys.stderr)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if result.get("summary",{}).get("passed")==9 and result["summary"]["total"]==9:
        return 0
    return 1

if __name__=="__main__":
    raise SystemExit(main())
