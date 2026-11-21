"""P0-A extension: genuine Chromium human editor vs B5 Agent + OS plugin.

The suite runs AFTER B9 native tamper/rebuild/rollback on the SAME
existing Kernel process, authority.sqlite and live Saltcorn projection.
All full G1 W/TC acceptance statuses remain NOT_RUN. Only partial oracles.
"""
from __future__ import annotations

import copy
import json


def run_suite(*, context, base, token_agent, plugin_tool, http, physical,
              make_mutation, check, native_page, native_physical, native_db,
              expected_native_columns):
    def agent(tool, args):
        return http(base, "app-a", tool, token_agent, args)

    def draft():
        status, body = agent("draft.read", {})
        if status != 200:
            raise AssertionError("P0A_AGENT_DRAFT_NOT_READABLE")
        return body

    def human_page():
        page = context.new_page()  # inherits real authenticated HttpOnly sid
        page.goto(base + "/editor/app-a", wait_until="domcontentloaded")
        page.locator("#revision").wait_for(timeout=10000)
        if page.url.endswith("/editor/login"):
            raise AssertionError("P0A_HUMAN_SESSION_MISSING")
        # Wait for async fetch to complete, rather than assuming DOMContentLoaded.
        page.locator("#message").get_by_text("已加载草稿", exact=False).wait_for(
            timeout=12000)
        page.locator("#resource-id").fill("view.contracts")
        page.locator("#select").click()
        return page

    def revision(page, expected):
        page.wait_for_function(
            "n => document.getElementById('revision').textContent === String(n)",
            expected, timeout=12000)

    def refresh(page, expected):
        page.locator("#reload").click()
        revision(page, expected)
        page.locator("#select").click()

    def save_view(page, field, value, status_expected):
        definition = json.loads(page.locator("#definition").input_value())
        definition[field] = value
        page.locator("#definition").fill(json.dumps(
            definition, ensure_ascii=False, sort_keys=True))
        with page.expect_response(
            lambda r: r.request.method == "POST" and
                      r.url.endswith("/v2/apps/app-a/commands"),
            timeout=15000
        ) as observed:
            page.locator("#save").click()
        response = observed.value
        result = response.json()
        if response.status != status_expected:
            raise AssertionError(
                "P0A_HUMAN_HTTP_"+str(response.status)+
                "_EXPECTED_"+str(status_expected))
        if status_expected == 200:
            page.get_by_role("status").get_by_text(
                "保存成功", exact=False).wait_for(timeout=12000)
        else:
            page.get_by_role("status").get_by_text(
                "409", exact=False).wait_for(timeout=12000)
        return response.status, result

    def app():
        return physical()["app-a"]

    initial = physical()
    first = initial["app-a"]
    if first["revision"] != 6 or first["publishedVersion"] != 1:
        raise AssertionError("P0A_PREEXISTING_AUTHORITY_BASELINE_MOVED")
    a = human_page()
    b = human_page()
    try:
        revision(a, 6)
        revision(b, 6)
        # A: two ACTUAL human Chromium tabs holding the same old View snapshot.
        pre = app()
        b_success = save_view(b, "title", "P0A-Browser-B-Winner", 200)
        a_stale = save_view(a, "title", "P0A-Browser-A-Stale", 409)
        current = app()
        check("P0A-07-two-real-human-tabs-stale-CAS-409",
              b_success[0] == 200 and
              a_stale[1].get("error") == "APP_REVISION_CONFLICT" and
              current["revision"] == pre["revision"]+1 and
              current["resources"]["view.contracts"]["title"] ==
                "P0A-Browser-B-Winner" and
              current["receipts"] == pre["receipts"]+1 and
              len(current["events"]) == len(pre["events"])+1,
              {"realTabs":2, "winner":200, "stale":409,
               "physicalRevision":current["revision"], "oneReceipt":True})
        # H first, stale A after H. Agent does not get to silently overwrite.
        snap_agent = draft()
        before = app()
        web = save_view(b, "title", "P0A-Human-First", 200)
        agent_def = copy.deepcopy(snap_agent["resources"][
            "view.contracts"]["definition"])
        agent_def["title"] = "P0A-Agent-Stale"
        stale = agent("metadata.upsert", {"command":make_mutation(
            snap_agent, "view.contracts", agent_def, "p0a-agent-after-web")})
        current = app()
        check("P0A-08-human-before-stale-Agent-does-not-lose-title",
              web[0] == 200 and stale[0] == 409 and
              stale[1].get("error") == "APP_REVISION_CONFLICT" and
              current["resources"]["view.contracts"]["title"] ==
                "P0A-Human-First" and
              current["receipts"] == before["receipts"]+1,
              {"realBrowserHTTP":200, "staleAgentHTTP":409,
               "humanTitleRetained":True})
        # A first, stale H after A. The very same browser page is held.
        refresh(a, current["revision"])
        snap_agent = draft()
        before = app()
        new_agent = copy.deepcopy(snap_agent["resources"][
            "view.contracts"]["definition"])
        new_agent["title"] = "P0A-Agent-First"
        agent_status, agent_result = agent("metadata.upsert", {
            "command":make_mutation(
                snap_agent, "view.contracts", new_agent,
                "p0a-agent-before-web")})
        human_stale = save_view(a, "title", "P0A-Human-Stale", 409)
        current = app()
        check("P0A-09-Agent-before-stale-human-does-not-lose-title",
              agent_status == 200 and human_stale[0] == 409 and
              human_stale[1].get("error") == "APP_REVISION_CONFLICT" and
              current["resources"]["view.contracts"]["title"] ==
                "P0A-Agent-First" and
              current["receipts"] == before["receipts"]+1,
              {"agentHTTP":agent_status, "staleHumanHTTP":409,
               "agentTitleRetained":True})
        # Non-overlap: no auto-merging stale JSON. Explicit re-read and
        # reviewed merge on different View keys retains both changes.
        refresh(b, current["revision"])
        stale_snapshot = draft()
        human = save_view(b, "title", "P0A-Human-Merged-Title", 200)
        edit_columns = copy.deepcopy(stale_snapshot["resources"][
            "view.contracts"]["definition"])
        edit_columns["columns"] = ["contract_no", "amount_minor", "status"]
        stale_code, stale_body = agent("metadata.upsert", {
            "command":make_mutation(
                stale_snapshot,"view.contracts",edit_columns,
                "p0a-non-overlap-stale-must-rebase")})
        reread = draft()
        merged = copy.deepcopy(reread["resources"][
            "view.contracts"]["definition"])
        merged["columns"] = edit_columns["columns"]
        merged_code, merged_body = agent("metadata.upsert", {
            "command":make_mutation(
                reread,"view.contracts",merged,
                "p0a-explicit-reviewed-rebase")})
        current = app()
        check("P0A-10-explicit-reload-merge-preserves-both-fields",
              human[0] == 200 and stale_code == 409 and
              stale_body.get("error") == "APP_REVISION_CONFLICT" and
              merged_code == 200 and
              current["resources"]["view.contracts"]["title"] ==
                "P0A-Human-Merged-Title" and
              current["resources"]["view.contracts"]["columns"] ==
                ["contract_no","amount_minor","status"] and
              current["manifestMatches"] and current["resourceHashesValid"],
              {"staleAgent":409, "reviewedRebase":200,
               "humanTitleRetained":True,"agentColumnsRetained":True})
        # Human designer succeeds while external model use is disabled.
        refresh(b, current["revision"])
        before = app()
        code, result = save_view(
            b, "title", "P0A-Manual-Without-Model", 200)
        current = app()
        check("P0A-11-human-browser-writes-without-model",
              code == 200 and current["revision"] == before["revision"]+1
              and current["resources"]["view.contracts"]["title"] ==
                "P0A-Manual-Without-Model" and
              current["receipts"] == before["receipts"]+1,
              {"realChromiumHTTP":code,"modelCalls":0,
               "independentSQLReadback":True})
        # Replay of a successful Agent change even AFTER a later Human write.
        before_replay = physical()
        receipt_again = agent("metadata.upsert", {
            "command":make_mutation(
                reread, "view.contracts", merged,
                "p0a-explicit-reviewed-rebase")})
        forged = plugin_tool("app-a", "metadata.upsert", {
            "command":make_mutation(
                reread, "view.contracts", merged,
                "p0a-explicit-reviewed-rebase")})
        changed_cmd = make_mutation(
            reread, "view.contracts", merged,
            "p0a-explicit-reviewed-rebase")
        changed_cmd["definition"]["title"] = "FORGED-REQUEST-DIGEST"
        digest_reuse = agent("metadata.upsert",{"command":changed_cmd})
        after_replay = physical()
        check("P0A-12-replay-after-newer-writer-and-cid-abuse-refused",
              receipt_again[0] == 200 and
              receipt_again[1].get("replayed") is True and
              receipt_again[1]["appRevision"] == merged_body["appRevision"]
              and forged["status"] == 409 and
              forged["body"].get("error") == "CHANGE_ID_REUSED" and
              digest_reuse[0] == 409 and
              digest_reuse[1].get("error") == "CHANGE_ID_REUSED" and
              before_replay == after_replay,
              {"sameAgentReplay":200,"otherActorReplay":409,
               "alteredDigestReplay":409,"physicalUnchanged":True})
        # Real authenticated browser attempting cross-site writes without
        # its CSRF header MUST receive JSON 403 rather than HTML redirect.
        before = physical()
        payload = make_mutation(
            draft(), "view.contracts", current["resources"][
                "view.contracts"], "p0a-csrf-unauthorized")
        csrf_missing = b.evaluate("""async body => {
          const r=await fetch('/v2/apps/app-a/commands', {
            method:'POST',credentials:'same-origin',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify(body)});
          return {status:r.status,contentType:r.headers.get('content-type'),
                  result:await r.json()}; }""", payload)
        csrf_invalid = b.evaluate("""async body => {
          const r=await fetch('/v2/apps/app-a/commands', {
            method:'POST',credentials:'same-origin',
            headers:{'Content-Type':'application/json','X-CSRF-Token':'bad'},
            body:JSON.stringify(body)});
          return {status:r.status,contentType:r.headers.get('content-type'),
                  result:await r.json()}; }""", payload)
        check("P0A-13-real-session-CSRF-negative-no-side-effects",
              all(x["status"]==403 and
                  x["result"].get("error")=="CSRF_REQUIRED" and
                  x["contentType"].startswith("application/json") for x in (
                  csrf_missing,csrf_invalid)) and physical()==before,
              {"noCSRF":csrf_missing["status"],"badCSRF":csrf_invalid["status"],
               "notHTMLRedirect":True,"physicalUnchanged":True})
        # Invalid untrusted tool identity / actor / role passed inside args.
        injected = plugin_tool("app-a","metadata.upsert",{
            "command":make_mutation(
                draft(),"view.contracts",current["resources"][
                    "view.contracts"],"p0a-plugin-role-injected"),
            "actorId":"admin","role":"administrator","appId":"app-b"})
        check("P0A-14-plugin-tool-identity-injection-rejected",
              injected["status"] == 422 and
              injected["body"].get("error")=="TOOL_ARGUMENTS_INVALID" and
              physical()==before,
              {"toolHTTP":injected["status"],"principalNotTrusted":True,
               "physicalUnchanged":True})
        # Native v1 remains a published, disposable view, not a draft cache.
        native_page.reload(wait_until="domcontentloaded")
        native_state = native_physical(native_db)
        after_all=physical()
        check("P0A-15-independent-physical-total-and-native-v1-no-leak",
              after_all["app-a"]["revision"] == first["revision"]+6 and
              after_all["app-a"]["receipts"] == first["receipts"]+6 and
              len(after_all["app-a"]["events"]) ==
                len(first["events"])+6 and
              after_all["app-a"]["publishedVersion"]==1 and
              after_all["app-a"]["releases"]==2 and
              native_state["viewColumns"]==expected_native_columns and
              "HT-2026-000001" in native_page.content() and
              after_all["app-b"]==initial["app-b"] and
              after_all["app-a"]["manifestMatches"] and
              after_all["app-a"]["resourceHashesValid"] and
              after_all["app-a"]["releaseHashesValid"],
              {"authorizedChanges":6,"physicalRevision":after_all[
                   "app-a"]["revision"],"publishedVersion":1,
               "NativeHasOnlyOldPublishedRelease":True,
               "otherAppUnchanged":True})
        return {"observedHumanTabs":2,"successfulHumanAndAgentWrites":6,
                "checks":9,"realBrowser":True,"independentSQL":True,
                "nativeStillOldPublishedV1":True,
                "fullFrozenWOrTC":False,"modelCalls":0}
    finally:
        b.close()
        a.close()
