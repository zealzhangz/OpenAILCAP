#!/usr/bin/env python3
"""Actual authenticated Chromium / Saltcorn native field-wizard editing.

Phase first: human changes title field in real browser, then freeze a PHYSICAL
SQLite snapshot for one read-only LLM proposal. No browser CSRF/cookie exported.
Phase second: human changes title AGAIN after the Agent safely changed status.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sqlite3
import sys

from playwright.sync_api import sync_playwright

sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"browser"))
from browser_roundtrip import save_wizard

EMAIL="s1-research-admin@example.invalid"
FIRST="Human First Saved"
SECOND="Human Second Saved"
TARGET="AI Reviewed Status"

def state(dbpath):
    with sqlite3.connect("file:"+str(Path(dbpath).resolve())+"?mode=ro",uri=True) as db:
        db.row_factory=sqlite3.Row
        rows=list(db.execute(
            "SELECT f.id,f.name,f.label FROM _sc_fields f "
            "JOIN _sc_tables t ON f.table_id=t.id "
            "WHERE t.name='s1_contracts' AND f.name IN ('title','status')"))
    if {r["name"] for r in rows}!={"title","status"}:
        raise AssertionError("Missing real Saltcorn title/status fields")
    return {r["name"]:{"id":r["id"],"label":r["label"]} for r in rows}

def open_page(page,url):
    for attempt in range(3):
        try:
            page.goto(url,wait_until="domcontentloaded",timeout=18000)
            return
        except Exception:
            if attempt==2:raise
            page.wait_for_timeout(400)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--phase",choices=["first","second"],required=True)
    p.add_argument("--db",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--password",default=os.getenv("S1_ADMIN_PASSWORD"))
    p.add_argument("--base",default="http://127.0.0.1:3100")
    args=p.parse_args()
    if not args.password:raise RuntimeError("NO_ADMIN_PASSWORD")
    before=state(args.db)
    if args.phase=="first":
        if before["title"]["label"]!="Title" or before["status"]["label"]!="Status":
            raise AssertionError("INITIAL_NATIVE_FIELD_LABELS_MISMATCH")
    else:
        if before["title"]["label"]!=FIRST or before["status"]["label"]!=TARGET:
            raise AssertionError("AI_PATCH_NOT_VISIBLE_BEFORE_SECOND_HUMAN_EDIT")
    new_label=FIRST if args.phase=="first" else SECOND
    trace=[]
    monitor=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,args=["--no-sandbox"])
        try:
            ctx=browser.new_context()
            login=ctx.new_page()
            open_page(login,args.base+"/auth/login")
            login.locator('input[name="email"]').fill(EMAIL)
            login.locator('input[name="password"]').fill(args.password)
            login.locator('form[action="/auth/login"] button[type="submit"], form[action="/auth/login"] input[type="submit"]').last.click()
            login.wait_for_load_state("domcontentloaded")
            edit=ctx.new_page()
            open_page(edit,args.base+"/field/"+str(before["title"]["id"]))
            if edit.locator('input[name="label"]').count()!=1:
                raise AssertionError("NATIVE_BROWSER_FIELD_EDITOR_NOT_AUTHENTICATED")
            value=edit.locator('input[name="label"]').input_value()
            if value != before["title"]["label"]:
                raise AssertionError("NATIVE_BROWSER_STALE_INITIAL_LABEL")
            def monitor_req(req):
                if req.method=="POST" and req.url.split("?")[0].rstrip("/").endswith("/field"):
                    body=req.post_data or ""
                    monitor.append({"method":"POST","path":"/field",
                                    "csrf_present":"_csrf=" in body,
                                    "context_present":"contextEnc=" in body})
            edit.on("request",monitor_req)
            save_wizard(edit,new_label,trace)
            after=state(args.db)
            if after["title"]["label"]!=new_label:
                raise AssertionError("HUMAN_NATIVE_BROWSER_SAVE_NOT_PERSISTED")
            if after["status"]["label"]!=before["status"]["label"]:
                raise AssertionError("BROWSER_TITLE_SAVE_CHANGED_OTHER_FIELD")
            if not monitor or not all(x["csrf_present"] and x["context_present"] for x in monitor):
                raise AssertionError("NATIVE_BROWSER_POST_NOT_VERIFIED")
            if args.phase=="second":
                verify=ctx.new_page()
                open_page(verify,args.base+"/field/"+str(after["status"]["id"]))
                ui_status=verify.locator('input[name="label"]').input_value()
                if ui_status!=TARGET:
                    raise AssertionError("AI_PATCH_NOT_VISIBLE_IN_REAL_BROWSER")
            else:
                ui_status=None
            ctx.close()
        finally:
            browser.close()
    evidence={
      "study":"S1 actual Saltcorn Chromium authenticated field editing around AI proposal",
      "phase":args.phase,
      "real_chromium":True,
      "real_native_saltcorn_ui":True,
      "actual_field_wizard_post_count":len(monitor),
      "actual_csrf_and_context":True,
      "before":{"title":before["title"]["label"],"status":before["status"]["label"]},
      "after":{"title":after["title"]["label"],"status":after["status"]["label"]},
      "status_visible_in_real_browser_after_agent":ui_status==TARGET if args.phase=="second" else None,
      "snapshot":{"title_label":after["title"]["label"],
                  "status_label":after["status"]["label"],
                  "title_field_id":after["title"]["id"],
                  "status_field_id":after["status"]["id"]},
      "result":"PASS"}
    Path(args.output).write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("S1_COLLAB_HUMAN|"+json.dumps({
       "phase":args.phase,"title":after["title"]["label"],
       "status":after["status"]["label"],
       "native_post_count":len(monitor),
       "ai_status_visible":evidence["status_visible_in_real_browser_after_agent"]
    },ensure_ascii=False),flush=True)

if __name__=="__main__":
    main()
