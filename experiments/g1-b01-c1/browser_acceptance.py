#!/usr/bin/env python3
"""B1 independent real-browser + Agent-process + plugin-process acceptance.

The UI is an OWNED OpenAILCAP B1 research editor, not Saltcorn native UI.
All three writers enter exactly the same C1 Store.apply authoritative path.
No DeepSeek request or model-dependent action is performed.
"""
from __future__ import annotations

import argparse
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

from service import Principal, Store, change_from
from web_editor import serve_b1

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "plugin_manifest.json"


def http_call(base, method, path, *, token=None, cookie=None, body=None, csrf=None):
    headers = {}
    if token:
        headers["Authorization"] = "Bearer " + token
    if cookie:
        headers["Cookie"] = "sid=" + cookie
    if csrf:
        headers["X-CSRF-Token"] = csrf
    payload = None
    if body is not None:
        payload = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(base + path, method=method, data=payload, headers=headers)
    try:
        with urlopen(request, timeout=12) as response:
            return response.status, json.load(response)
    except HTTPError as exc:
        return exc.code, json.loads(exc.read())


def raw_db(db_file, app="app-a"):
    """Second, read-only database connection: not Store's returned value."""
    with sqlite3.connect("file:" + str(Path(db_file).resolve()) + "?mode=ro",
                         uri=True) as db:
        row = db.execute(
            "SELECT revision,doc,state FROM resources WHERE app_id=? "
            "AND resource_id='field.title'", (app,)
        ).fetchone()
        audits = db.execute("SELECT principal FROM audit WHERE app_id=? "
                            "ORDER BY event_id", (app,)).fetchall()
        receipts = db.execute("SELECT COUNT(*) FROM receipts WHERE app_id=?",
                              (app,)).fetchone()[0]
    if not row:
        raise AssertionError("Missing physical resource")
    return {"revision": row[0], "content": json.loads(row[1]), "state": row[2],
            "principals": [x[0] for x in audits], "audits": len(audits),
            "receipts": receipts}


def process_command(base, kind, token, value, change_id, field="status",
                    app="app-a", base_snapshot=None, check=True):
    args = [sys.executable, str(HERE / "tool_client.py"),
            "--caller", kind, "--base", base, "--app", app,
            "--field", field, "--value", value, "--change-id", change_id]
    if base_snapshot:
        args += ["--base-revision", str(base_snapshot["revision"]),
                 "--base-hash", base_snapshot["contentHash"]]
    env = {"PATH": os.environ.get("PATH", ""),
           "B1_AGENT_TOKEN" if kind == "agent" else "B1_PLUGIN_TOKEN": token}
    result = subprocess.run(args, text=True, capture_output=True, timeout=16,
                            env=env, check=False)
    if check and result.returncode != 0:
        raise AssertionError(kind + " subprocess error: " +
                             (result.stderr or result.stdout)[:300])
    return result


def parse_command(result):
    return json.loads(result.stdout.strip())


def save_label(page, value, field="label"):
    page.locator("#field").select_option(field)
    page.locator("#value").fill(value)
    page.locator("#save").click()


def wait_message(page, needle):
    page.locator("#message").get_by_text(needle, exact=False).wait_for(timeout=12000)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    cases = []
    artifact = {
        "study": "S1 B1 real own-web editor and Agent/Plugin separate processes",
        "scope": "OWNED_MINIMAL_EDITOR_NOT_SALTCORN_NATIVE",
        "real_chromium": True,
        "real_agent_model": False,
        "real_plugin_process": True,
        "plugin_sandbox": False,
        "same_authoritative_sqlite": True,
        "g1_b01_closed": False,
        "frozen_w01_w24_full_pass_unchanged": True,
        "cases": cases,
    }

    def record(label, condition, observed):
        case = {"id": label, "status": "PASS" if condition else "FAIL",
                "observed": observed}
        cases.append(case)
        print("B1 " + label + " " + case["status"] + " " +
              json.dumps(observed, ensure_ascii=False), flush=True)
        if not condition:
            raise AssertionError(label)

    with tempfile.TemporaryDirectory() as tmp:
        dbfile = Path(tmp) / "b1-research.sqlite"
        store = Store(dbfile)
        store.initialize()
        store.bootstrap_for_test("app-a", "field.title",
                                 {"label": "Title", "status": "Draft"})
        store.bootstrap_for_test("app-b", "field.title",
                                 {"label": "Other App", "status": "Draft"})
        manifest = json.loads(MANIFEST.read_text())
        if manifest["appId"] != "app-a" or manifest["fields"] != ["status"]:
            raise AssertionError("unexpected plugin manifest")
        human = Principal("human-b1", "app-a", "browser")
        agent = Principal("agent-tool", "app-a", "agent")
        plugin = Principal(manifest["name"], manifest["appId"], "plugin",
                           resources=tuple(manifest["resources"]),
                           fields=tuple(manifest["fields"]))
        agent_token = secrets.token_urlsafe(32)
        plugin_token = secrets.token_urlsafe(32)
        password = secrets.token_urlsafe(32)
        tokens = {agent_token: agent, plugin_token: plugin}
        sessions = {}
        server = serve_b1(store, tokens, sessions, human, password, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = "http://127.0.0.1:" + str(server.server_port)
        artifact["environment"] = {
            "server_bind": "127.0.0.1 (ephemeral port)",
            "db_file_isolated": True,
            "plugin_manifest": "status-helper: app-a/field.title/status",
        }
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    headless=True, args=["--no-sandbox"]
                )
                context = browser.new_context()
                try:
                    login = context.new_page()
                    login.goto(base + "/editor/app-a/field.title",
                               wait_until="domcontentloaded")
                    record("B1-01-anonymous-editor-requires-login",
                           login.url.endswith("/editor/login") and
                           login.locator("#password").count() == 1,
                           {"anonymous_redirect_path": "/editor/login"})
                    login.locator("#password").fill(password)
                    login.locator("#login").click()
                    login.wait_for_url("**/editor/app-a/field.title",
                                       timeout=12000)
                    login.wait_for_function("document.getElementById('revision').textContent === '0'", timeout=12000)
                    record("B1-02-real-session-login",
                           login.locator("#label-current").inner_text() == "Title",
                           {"login": "real-form", "current_label": "Title"})
                    tab_a = context.new_page()
                    tab_b = context.new_page()
                    tab_a.goto(base + "/editor/app-a/field.title",
                               wait_until="domcontentloaded")
                    tab_b.goto(base + "/editor/app-a/field.title",
                               wait_until="domcontentloaded")
                    tab_a.wait_for_function("document.getElementById('revision').textContent === '0'", timeout=12000)
                    tab_b.wait_for_function("document.getElementById('revision').textContent === '0'", timeout=12000)
                    record("B1-03-two-independent-browser-snapshots",
                           tab_a.locator("#label-current").inner_text() == "Title" and
                           tab_b.locator("#label-current").inner_text() == "Title",
                           {"a_revision": 0, "b_revision": 0})
                    posted = []
                    tab_a.on("response", lambda r: posted.append(
                        {"tab": "A", "status": r.status, "path": "/changes"}
                    ) if r.request.method == "POST" and
                    r.url.endswith("/v1/apps/app-a/changes") else None)
                    tab_b.on("response", lambda r: posted.append(
                        {"tab": "B", "status": r.status, "path": "/changes"}
                    ) if r.request.method == "POST" and
                    r.url.endswith("/v1/apps/app-a/changes") else None)
                    save_label(tab_b, "Browser B Saved")
                    tab_b.locator("#message").get_by_text("保存成功").wait_for(
                        timeout=12000)
                    after_b = raw_db(dbfile)
                    record("B1-04-actual-B-browser-saves-via-command",
                           after_b["revision"] == 1 and
                           after_b["content"]["label"] == "Browser B Saved",
                           {"db_revision": after_b["revision"],
                            "db_label": after_b["content"]["label"]})
                    save_label(tab_a, "Browser A Stale")
                    tab_a.wait_for_function("document.getElementById('message').textContent.includes('409 VERSION_CONFLICT')", timeout=12000)
                    after_a = raw_db(dbfile)
                    record("B1-05-stale-browser-409-no-loss",
                           after_a["content"]["label"] == "Browser B Saved" and
                           after_a["revision"] == 1 and
                           any(x["status"] == 409 for x in posted),
                           {"db_revision": after_a["revision"],
                            "response_409": True,
                            "browser_message": "409 VERSION_CONFLICT"})
                    agent_result = parse_command(process_command(
                        base, "agent", agent_token, "AI Reviewed",
                        "agent-step-0001", field="status"))
                    after_agent = raw_db(dbfile)
                    record("B1-06-external-agent-typed-HTTP-tool",
                           agent_result["status"] == 200 and
                           after_agent["revision"] == 2 and
                           after_agent["content"]["status"] == "AI Reviewed" and
                           after_agent["content"]["label"] == "Browser B Saved",
                           {"agent_http": agent_result["status"],
                            "db_revision": after_agent["revision"]})
                    save_label(tab_b, "Overwrites Agent", field="status")
                    tab_b.wait_for_function("document.getElementById('message').textContent.includes('409 VERSION_CONFLICT')", timeout=12000)
                    record("B1-07-stale-human-after-agent-409",
                           raw_db(dbfile)["content"]["status"] == "AI Reviewed",
                           {"browser_http": 409, "agent_status_preserved": True})
                    tab_a.locator("#reload").click()
                    tab_a.wait_for_function("document.getElementById('revision').textContent === '2'", timeout=12000)
                    record("B1-08-human-explicit-refresh-after-agent",
                           tab_a.locator("#status-current").inner_text() ==
                           "AI Reviewed",
                           {"browser_revision": 2, "visible_agent_status": True})
                    save_label(tab_a, "Human After AI")
                    tab_a.locator("#message").get_by_text("保存成功").wait_for(
                        timeout=12000)
                    after_human = raw_db(dbfile)
                    record("B1-09-human-resumes-with-agent-change-preserved",
                           after_human["revision"] == 3 and
                           after_human["content"] == {
                               "label": "Human After AI", "status": "AI Reviewed"
                           },
                           {"db_revision": 3, "nonoverlapping_data_retained": True})
                    before_plugin = http_call(
                        base, "GET", "/v1/apps/app-a/resources/field.title",
                        token=agent_token
                    )[1]
                    plugin_result = parse_command(process_command(
                        base, "plugin", plugin_token, "Plugin Reviewed",
                        "plugin-step-0001"))
                    after_plugin = raw_db(dbfile)
                    record("B1-10-separate-plugin-process-shared-commit",
                           plugin_result["status"] == 200 and
                           after_plugin["revision"] == 4 and
                           after_plugin["content"]["label"] == "Human After AI" and
                           after_plugin["content"]["status"] == "Plugin Reviewed" and
                           after_plugin["principals"][-1] == "status-helper",
                           {"plugin_http": plugin_result["status"],
                            "db_revision": after_plugin["revision"],
                            "audit_principal": after_plugin["principals"][-1]})
                    before = http_call(
                        base, "GET", "/v1/apps/app-a/resources/field.title",
                        token=plugin_token
                    )[1]
                    denied = http_call(
                        base, "POST", "/v1/apps/app-a/changes",
                        token=plugin_token,
                        body=change_from(before, "plugin-denied-001",
                                         "label", "Unauthorized Label"))
                    record("B1-11-server-enforces-plugin-field-scope",
                           denied == (403, {"error": "FIELD_FORBIDDEN"}) and
                           raw_db(dbfile)["revision"] == 4,
                           {"plugin_unmanaged_direct_http": denied[0],
                            "error": denied[1].get("error")})
                    outside = http_call(
                        base, "GET", "/v1/apps/app-b/resources/field.title",
                        token=plugin_token
                    )
                    rejected_plugin = process_command(
                        base, "plugin", plugin_token, "Wrong",
                        "plugin-denied-002", field="label", check=False)
                    record("B1-12-plugin-manifest-and-cross-app-isolation",
                           outside[0] == 403 and
                           rejected_plugin.returncode != 0 and
                           "PLUGIN_MANIFEST_DENIED" in rejected_plugin.stderr and
                           raw_db(dbfile, "app-b")["revision"] == 0,
                           {"cross_app_http": outside[0],
                            "manifest_denial": True,
                            "other_app_revision": 0})
                    stale_agent = parse_command(process_command(
                        base, "agent", agent_token, "AI Outdated",
                        "agent-stale-0002", base_snapshot=before_plugin))
                    record("B1-13-previous-agent-snapshot-stale-409",
                           stale_agent["status"] == 409 and
                           raw_db(dbfile)["revision"] == 4,
                           {"stale_agent_http": stale_agent["status"],
                            "code": stale_agent["result"].get("error")})
                    noauth = http_call(
                        base, "POST", "/v1/apps/app-a/changes",
                        body=change_from(before, "noauth-0003", "label", "Nope"))
                    record("B1-14-anonymous-mutation-rejected",
                           noauth[0] == 401 and raw_db(dbfile)["revision"] == 4,
                           {"anonymous_http": noauth[0]})
                    cookies = context.cookies()
                    sid = next((c["value"] for c in cookies
                                if c["name"] == "sid"), None)
                    if not sid:
                        raise AssertionError("actual Chromium session cookie missing")
                    csrf_free = http_call(
                        base, "POST", "/v1/apps/app-a/changes", cookie=sid,
                        body=change_from(before, "no-csrf-0004",
                                         "label", "Nope"))
                    record("B1-15-real-browser-cookie-without-csrf-403",
                           csrf_free[0] == 403 and
                           csrf_free[1].get("error") == "CSRF_REQUIRED",
                           {"cookie_from_actual_chromium": True,
                            "no_csrf_http": csrf_free[0]})
                    race_snapshot = http_call(
                        base, "GET", "/v1/apps/app-a/resources/field.title",
                        token=agent_token
                    )[1]
                    # Two distinct OS processes on the same pre-read revision.
                    env = {"PATH": os.environ.get("PATH", "")}
                    commands = []
                    for kind, token, value, change_id in (
                        ("agent", agent_token, "Race Agent", "race-agent-01"),
                        ("plugin", plugin_token, "Race Plugin", "race-plugin-01"),
                    ):
                        argv = [sys.executable, str(HERE / "tool_client.py"),
                                "--caller", kind, "--base", base,
                                "--field", "status", "--value", value,
                                "--change-id", change_id,
                                "--base-revision", str(race_snapshot["revision"]),
                                "--base-hash", race_snapshot["contentHash"]]
                        local_env = dict(env)
                        local_env["B1_AGENT_TOKEN" if kind == "agent"
                                  else "B1_PLUGIN_TOKEN"] = token
                        commands.append(subprocess.Popen(
                            argv, env=local_env, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE
                        ))
                    results = []
                    for child in commands:
                        stdout, stderr = child.communicate(timeout=16)
                        if child.returncode != 0:
                            raise AssertionError("race client error " + stderr[:250])
                        results.append(json.loads(stdout.strip()))
                    after_race = raw_db(dbfile)
                    record("B1-16-actual-two-process-agent-plugin-race",
                           sorted(x["status"] for x in results) == [200, 409] and
                           after_race["revision"] == 5 and
                           after_race["audits"] == 5 and
                           after_race["receipts"] == 5 and
                           after_race["content"]["label"] == "Human After AI",
                           {"http_statuses": sorted(x["status"] for x in results),
                            "db_revision": after_race["revision"],
                            "audit_count": after_race["audits"]})
                    tokens.pop(plugin_token)
                    revoked = http_call(
                        base, "GET", "/v1/apps/app-a/resources/field.title",
                        token=plugin_token
                    )
                    record("B1-17-revoked-plugin-token-cannot-read",
                           revoked == (401, {"error": "AUTH_REQUIRED"}),
                           {"revoked_token_http": revoked[0]})
                    final_db = raw_db(dbfile)
                    final_b = raw_db(dbfile, "app-b")
                    tab_a.locator("#reload").click()
                    tab_a.wait_for_function("document.getElementById('revision').textContent === '5'", timeout=12000)
                    record("B1-18-independent-db-and-live-browser-consistent",
                           tab_a.locator("#label-current").inner_text() ==
                           final_db["content"]["label"] and
                           tab_a.locator("#status-current").inner_text() ==
                           final_db["content"]["status"] and
                           final_b["revision"] == 0 and
                           final_db["state"] == "ACTIVE",
                           {"db_revision": final_db["revision"],
                            "browser_revision": 5,
                            "app_b_unchanged": final_b["revision"] == 0})
                    artifact["final_independent_physical_state"] = {
                        "app_a_revision": final_db["revision"],
                        "audit_count": final_db["audits"],
                        "receipt_count": final_db["receipts"],
                        "principal_sequence": final_db["principals"],
                        "app_b_revision": final_b["revision"],
                        "content": final_db["content"],
                    }
                finally:
                    context.close()
                    browser.close()
        except Exception as exc:
            artifact["error"] = {"type": type(exc).__name__,
                                 "message": str(exc)[:1000],
                                 "traceback": traceback.format_exc()[-1700:]}
            raise
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
            artifact["summary"] = {
                "passed": sum(x["status"] == "PASS" for x in cases),
                "total_attempted": len(cases),
                "expected_total": 18,
            }
            Path(args.output).write_text(
                json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8"
            )
            print("S1_B1_RESULT " + json.dumps(artifact["summary"]), flush=True)
    return 0 if len(cases) == 18 and all(x["status"] == "PASS" for x in cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
