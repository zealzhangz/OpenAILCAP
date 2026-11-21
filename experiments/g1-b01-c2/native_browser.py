#!/usr/bin/env python3
"""Real Chromium/native Saltcorn edit wizard after disposable compiled-route patch.

Instruments only the /field route; this is NOT a production-safe CAS implementation.
"""
import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "platform-saltcorn" / "browser"))
# Import via explicit repo root instead (this file lives experiments/g1-b01-c2)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "platform-saltcorn" / "browser"))
from browser_roundtrip import db_value, field_id, save_wizard

EMAIL="s1-research-admin@example.invalid"


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--db",required=True)
    ap.add_argument("--output",required=True)
    ap.add_argument("--base",default="http://127.0.0.1:3100")
    args=ap.parse_args()
    password=os.environ["S1_ADMIN_PASSWORD"]
    before=db_value(args.db)
    if before!="Title":
        raise AssertionError(f"Wrong fixture field label {before}")
    fid=field_id(args.db)
    cases=[]
    def record(name,ok,detail):
        cases.append({"test":name,"status":"PASS" if ok else "FAIL","observed":detail})
        print(f"S1_C2 {name} {'PASS' if ok else 'FAIL'} {json.dumps(detail)}",flush=True)
        if not ok:
            raise AssertionError(name)

    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,args=["--no-sandbox"])
        ctx=browser.new_context()
        try:
            login=ctx.new_page()
            login.goto(args.base+"/auth/login",wait_until="domcontentloaded")
            login.locator('input[name="email"]').fill(EMAIL)
            login.locator('input[name="password"]').fill(password)
            login.locator('form[action="/auth/login"] button[type="submit"], form[action="/auth/login"] input[type="submit"]').last.click()
            login.wait_for_load_state("domcontentloaded")
            tab_a=ctx.new_page()
            tab_b=ctx.new_page()
            tab_a.goto(args.base+f"/field/{fid}",wait_until="domcontentloaded")
            tab_b.goto(args.base+f"/field/{fid}",wait_until="domcontentloaded")
            initial_a=tab_a.locator('input[name="label"]').input_value()
            initial_b=tab_b.locator('input[name="label"]').input_value()
            record("C2-01-two-native-tabs",initial_a=="Title" and initial_b=="Title",
                   {"a":initial_a,"b":initial_b})
            record("C2-02-signed-baseline-in-original-form",
                   "contextEnc" in tab_a.content() and "_csrf" in tab_a.content(),
                   {"workflow_context":True,"csrf":True})
            trace=[]
            native_post=[]
            def monitor(response):
                if response.request.method=="POST" and response.url.split("?")[0].rstrip("/").endswith("/field"):
                    native_post.append({"http":response.status,"path":"/field"})
            tab_a.on("response",monitor)
            tab_b.on("response",monitor)
            save_wizard(tab_b,"Browser B Protected",trace)
            record("C2-03-native-B-field-update",db_value(args.db)=="Browser B Protected",
                   {"label":db_value(args.db),"b_post_count":len(native_post)})
            tab_a.locator('input[name="label"]').fill("Browser A Stale Attack")
            stale_rejected=False
            for attempt in range(9):
                forms=tab_a.locator('form').filter(
                    has=tab_a.locator('input[name="contextEnc"]'))
                if forms.count()!=1:
                    break
                buttons=forms.first.locator('button[type="submit"], input[type="submit"]')
                if not buttons.count():
                    break
                buttons.last.click()
                tab_a.wait_for_load_state("domcontentloaded",timeout=25000)
                if any(x["http"]==409 for x in native_post):
                    stale_rejected=True
                    break
                if "/table/" in tab_a.url and "/field" not in tab_a.url:
                    break
            record("C2-04-native-stale-response-409",stale_rejected,
                   {"post_statuses":[x["http"] for x in native_post],
                    "stale_attempted":True})
            record("C2-05-preserve-B-physical-label",
                   db_value(args.db)=="Browser B Protected",
                   {"label":db_value(args.db)})
            newest=ctx.new_page()
            newest.goto(args.base+f"/field/{fid}",wait_until="domcontentloaded")
            actual=newest.locator('input[name="label"]').input_value()
            record("C2-06-new-native-view-current-label",
                   actual=="Browser B Protected",{"browser_label":actual})
            # Try a fresh native browser edit to check the patch is not a blanket denial.
            save_wizard(newest,"Browser C Fresh Edit",trace)
            record("C2-07-native-fresh-form-works",
                   db_value(args.db)=="Browser C Fresh Edit",
                   {"label":db_value(args.db)})
            record("C2-08-native-post-chain",
                   len(native_post)>=2 and any(x["http"]==409 for x in native_post),
                   {"tracked_posts":native_post})
        finally:
            ctx.close()
            browser.close()
    result={"scope":"C2_UNOFFICIAL_SALTCORN_COMPILED_ROUTE_PATCH",
            "source_package":"@saltcorn/cli@1.7.0-beta.5",
            "real_chromium":True, "native_saltcorn_web":True,
            "atomic_cas":False,"real_plugin_tested":False,
            "no_external_llm":True,"cases":cases,
            "summary":{"passed":len(cases),"total":len(cases)}}
    Path(args.output).write_text(json.dumps(result,indent=2)+"\n")
    print("S1_C2_BROWSER_SUMMARY",json.dumps(result["summary"]))

if __name__=="__main__":
    main()
