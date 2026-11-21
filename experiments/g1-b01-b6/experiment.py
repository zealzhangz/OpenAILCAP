#!/usr/bin/env python3
"""B6 real untrusted Docker plugin attempts DB/socket/network bypass.

No LLM calls. Every B6 check observes real Docker processes + trusted B5
v3 HTTP broker + B2 browser/SQL; the plugin doesn't receive bearer secrets.
Formal W11/W16 remain NOT_FULL_PASS; privileged host remains a counterexample.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import secrets
import sqlite3
import sys
import tempfile
import threading
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request,urlopen

from playwright.sync_api import sync_playwright

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"g1-b01-b2"))
sys.path.insert(0,str(HERE.parent/"g1-b01-b4"))
sys.path.insert(0,str(HERE.parent/"g1-b01-b5"))
from schema_core import Actor,SchemaStore,sha,Rejected
from registry import ExtensionRegistry
from sandbox import DockerSandbox
from policy import source_hash
from tool_broker import ToolBroker,make_server
from plugin_isolation import DockerPlugin,IsolationFailure,complete_isolation


def http(base,path,token=None,body=None):
    headers={}
    if token is not None:
        headers["Authorization"]="Bearer "+token
    if body is not None:
        headers["Content-Type"]="application/json"
    req=Request(base+path,data=None if body is None else
                json.dumps(body,ensure_ascii=False).encode("utf-8"),
                method="GET" if body is None else "POST",headers=headers)
    try:
        with urlopen(req,timeout=60) as res:
            return res.status,json.loads(res.read())
    except HTTPError as e:
        return e.code,json.loads(e.read())


def physical(path,app):
    """Independent read-only SQL oracle; no writes through broker internals."""
    with sqlite3.connect("file:"+str(path.resolve())+"?mode=ro",uri=True) as db:
        db.row_factory=sqlite3.Row
        head=db.execute("SELECT revision,manifest_hash,current_release,state "
                        "FROM apps WHERE app=?",(app,)).fetchone()
        defs=db.execute("SELECT rid,spec,hash,revision FROM definitions "
                        "WHERE app=? ORDER BY rid",(app,)).fetchall()
        audits=db.execute("SELECT actor,event,rid,app_revision FROM events "
                          "WHERE app=? ORDER BY eid",(app,)).fetchall()
        receipts=db.execute("SELECT actor,cid,request_hash,response FROM receipts "
                            "WHERE app=? ORDER BY cid",(app,)).fetchall()
        rows=db.execute("SELECT record_id,content,version FROM records "
                        "WHERE app=? ORDER BY rowid",(app,)).fetchall()
        releases=db.execute("SELECT version,hash,manifest FROM releases "
                            "WHERE app=? ORDER BY version",(app,)).fetchall()
        code=db.execute("SELECT artifact_hash,source FROM extension_artifacts "
                        "WHERE app=?",(app,)).fetchall()
        ext=db.execute("SELECT version FROM extension_pointers WHERE app=?",
                       (app,)).fetchone()
    defs=[dict(x) for x in defs]
    return {
        "appRevision":head["revision"],
        "manifestHash":head["manifest_hash"],
        "currentRelease":head["current_release"],
        "appState":head["state"],
        "definitions":{
            x["rid"]:json.loads(x["spec"]) for x in defs
        },
        "definitionsHashesValid":all(
            sha(json.loads(x["spec"]))==x["hash"] for x in defs
        ),
        "events":[dict(x) for x in audits],
        "receiptCount":len(receipts),
        "receipts":[dict(x) for x in receipts],
        "records":[{"recordId":r["record_id"],
                    "data":json.loads(r["content"]),
                    "version":r["version"]} for r in rows],
        "releaseHashesValid":all(
            sha(json.loads(x["manifest"]))==x["hash"] for x in releases
        ),
        "releaseCount":len(releases),
        "codeArtifacts":len(code),
        "codeHashesValid":all(
            source_hash(x["source"])==x["artifact_hash"] for x in code
        ),
        "extensionVersion":ext["version"] if ext else 0
    }


def browser_wait(page,css,expected):
    for _ in range(80):
        if expected in page.locator(css).inner_text(timeout=1000):
            return
        page.wait_for_timeout(130)
    raise AssertionError("BROWSER_OBSERVATION_TIMEOUT_"+css)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    evidence={
        "experiment":"S1_B6_REAL_DOCKER_PLUGIN_STDINLESS_HOST_RELAY",
        "callsToExternalModels":0,
        "realOsContainer":True,
        "pluginReceivesApiToken":False,
        "pluginHasNetwork":False,
        "pluginHasHostDbMount":False,
        "hostPrivilegedDbBypassEliminated":False,
        "realThirdPartySaltcornPluginTested":False,
        "formalG1Passed":False,
        "checks":[]
    }
    def check(cid,predicate,observed):
        row={"id":cid,"status":"PASS" if predicate else "FAIL",
             "observed":observed}
        evidence["checks"].append(row)
        print("B6 "+cid+" "+row["status"]+" "+
              json.dumps(observed,ensure_ascii=False),flush=True)
        if not predicate:
            raise AssertionError(cid)
    with tempfile.TemporaryDirectory(prefix="s1-b6-host-") as temp:
        host=Path(temp)
        dbfile=host/"authority.sqlite"
        sentinel=host/"host-only-secret.txt"
        sentinel.write_text(secrets.token_urlsafe(38),encoding="utf-8")
        sentinel.chmod(0o644) # even WORLD READABLE on host must be absent
        secret_name="S1_B6_HOST_SENTINEL"
        original=os.environ.get(secret_name)
        os.environ[secret_name]=secrets.token_urlsafe(45)
        store=SchemaStore(dbfile)
        store.init()
        for a in ("app-a","app-b"):
            store.seed_app_for_test(a)
        image_id=os.environ["S1_B4_IMAGE_ID"]
        real_code_runner=DockerSandbox(image_id)
        registry=ExtensionRegistry(store,real_code_runner)
        registry.init()
        broker=ToolBroker(store,registry)
        identity={
            "human":Actor("trusted-reviewer","app-a",can_publish=True,
                          can_runtime=True),
            "agent":Actor("trusted-agent","app-a"),
            "plugin":Actor("sandboxed-view-plugin","app-a",kinds=("view",)),
            "runtime":Actor("runtime-user","app-a",can_runtime=True)
        }
        grants={
            "human":{"draft.read","release.read","metadata.upsert",
                     "app.publish","app.rollback","code.stage","code.publish",
                     "code.rollback","code.verify","form.submit","risk.score",
                     "workflow.advance"},
            "agent":{"draft.read","metadata.upsert","code.verify"},
            "plugin":{"draft.read","metadata.upsert"},
            "runtime":{"form.submit","risk.score","workflow.advance",
                       "release.read"}
        }
        tokens={}
        for role in identity:
            tokens[role]=secrets.token_urlsafe(32)
            broker.grant(tokens[role],identity[role],grants[role])
        sessions={}
        password=secrets.token_urlsafe(33)
        srv=make_server(store,registry,broker,sessions,identity["human"],password)
        thread=threading.Thread(target=srv.serve_forever,daemon=True)
        thread.start()
        base="http://127.0.0.1:"+str(srv.server_port)
        plugin=DockerPlugin(image_id,base,tokens["plugin"],"app-a",
                            "sandboxed-view-plugin")
        def tool(role,op,args0,app="app-a"):
            return http(base,"/v3/apps/"+app+"/tools/"+op,
                        tokens[role],args0)
        def run_plugin(request):
            observed=plugin.run(request,dbfile,sentinel)
            assert complete_isolation(observed.probes), "CONTAINER_ISOLATION_REGRESSION"
            return observed
        def draft(role):
            status,data=tool(role,"draft.read",{})
            if status!=200:raise AssertionError("BROKER_DRAFT_FAILED")
            return data
        def cmd(snap,rid,spec,cid):
            old=snap["resources"].get(rid)
            return {"changeId":cid,"resourceId":rid,
                    "expectedAppRevision":snap["appRevision"],
                    "expectedRevision":old["revision"] if old else None,
                    "baseContentHash":old["contentHash"] if old else None,
                    "definition":spec}
        def plug(app,op,args0):
            return run_plugin({"app":app,"tool":op,"args":args0})
        try:
            command=plugin.docker_argv(host)
            check("B6-01-real-Docker-isolation-command-pinned",
                  command.count("--mount")==1 and
                  "--network=none" in command and
                  "--read-only" in command and
                  "--cap-drop=ALL" in command and
                  "--user=65534:65534" in command and
                  "--security-opt=no-new-privileges" in command and
                  "--privileged" not in command and
                  image_id in command,
                  {"pinnedImagePrefix":image_id[:23],
                   "mountCount":1,"network":"none",
                   "user":"65534:65534","privileged":False})
            with sqlite3.connect(dbfile) as db:
                host_has_sql=bool(db.execute(
                    "SELECT 1 FROM apps WHERE app='app-a'").fetchone())
            check("B6-02-host-SQL-and-world-readable-sentinel-exist",
                  host_has_sql and len(sentinel.read_text())>20 and
                  sentinel.stat().st_mode & 0o004 != 0,
                  {"trustedHostDBAccessible":True,
                   "sentinelWorldReadable":True,
                   "containerWillNotMountEither":True})
            sample=plug("app-a","draft.read",{})
            check("B6-03-actual-untrusted-container-all-OS-probes-denied",
                  complete_isolation(sample.probes),
                  {k:v for k,v in sample.probes.items()
                   if k!="containerHasDatabaseLibrary"})
            check("B6-04-restricted-plugin-can-request-valid-host-tool",
                  sample.http_status==200 and
                  sample.result["applicationId"]=="app-a" and
                  sample.result["appRevision"]==0,
                  {"http":sample.http_status,"draftRevision":0,
                   "mediatedTool":sample.tool})
            check("B6-05-plugin-has-no-secret-or-token-in-mounted-command",
                  sample.probes["hostSecretInherited"] is False and
                  not any(tokens["plugin"] in x or
                          os.environ[secret_name] in x for x in command),
                  {"hostTokenOnly":True,"secretInherited":False})
            initial=physical(dbfile,"app-a")
            sql_ask=plug("app-a","sql.admin",{"query":"UPDATE apps SET revision=999"})
            check("B6-06-sandbox-plugin-unknown-SQL-tool-403-no-write",
                  sql_ask.http_status==403 and
                  sql_ask.result.get("error")=="TOOL_NOT_GRANTED" and
                  physical(dbfile,"app-a")["appRevision"]==0,
                  {"http":403,"databaseRevision":0})
            code_stage=plug("app-a","code.stage",{
                "source":"def score_contract(amount_minor, supplier_score, months_active):\n"
                         "    return 0\n"})
            check("B6-07-plugin-cannot-stage-arbitrary-code",
                  code_stage.http_status==403 and
                  physical(dbfile,"app-a")["codeArtifacts"]==0,
                  {"http":403,"codeArtifacts":0})
            pub=plug("app-a","app.publish",{"command":{}})
            check("B6-08-plugin-cannot-publish-B2",
                  pub.http_status==403 and
                  physical(dbfile,"app-a")["currentRelease"] is None,
                  {"http":403,"publishedRelease":None})
            cross=plug("app-b","draft.read",{})
            check("B6-09-plugin-forged-app-is-rejected-before-relay",
                  cross.http_status==403 and
                  cross.result.get("error")=="PLUGIN_CROSS_APP_FORBIDDEN" and
                  physical(dbfile,"app-b")["appRevision"]==0,
                  {"http":403,"untouchedOtherApp":True})
            injected=plug("app-a","metadata.upsert",{
                "command":{},"actorId":"administrator"})
            check("B6-10-actor-spoof-in-tool-args-422",
                  injected.http_status==422 and
                  injected.result.get("error")=="TOOL_ARGUMENTS_INVALID",
                  {"http":422,"forgedActorRejected":True})
            try:
                plugin.run({"app":"app-a","tool":"draft.read","args":{},
                            "actorId":"admin"},dbfile,sentinel)
                envelope_rejected=False
            except IsolationFailure as e:
                envelope_rejected=e.code=="PLUGIN_REQUEST_INVALID"
            check("B6-11-protocol-envelope-actor-forgery-fails-closed",
                  envelope_rejected and
                  physical(dbfile,"app-a")["appRevision"]==0,
                  {"extraActor":False,"databaseRevision":0})
            # Create B2's typed model under an independently granted agent.
            specs=json.loads((HERE.parent/"g1-b01-b2"/
                              "contract_spec.json").read_text())
            specs["view.contracts"]["columns"]=[
                "contract_no","title","amount_minor","status"]
            model=cmd(draft("agent"),"model.contracts",
                      specs["model.contracts"],"b6-agent-model-1")
            created=tool("agent","metadata.upsert",{"command":model})
            check("B6-12-agent-uses-same-governed-model-ingress",
                  created[0]==200 and
                  physical(dbfile,"app-a")["appRevision"]==1,
                  {"http":200,"revision":1})
            blocked_model=plug("app-a","metadata.upsert",{
                "command":cmd(draft("agent"),"model.contracts",
                              specs["model.contracts"],"b6-plugin-forbid-model")})
            check("B6-13-plugin-allowed-view-not-model-kind",
                  blocked_model.http_status==403 and
                  blocked_model.result.get("error")=="KIND_FORBIDDEN" and
                  physical(dbfile,"app-a")["appRevision"]==1,
                  {"http":403,"modelRevisionStill":1})
            original_view=copy.deepcopy(specs["view.contracts"])
            first_view=cmd(draft("plugin"),"view.contracts",
                           original_view,"b6-plugin-create-view")
            first=plug("app-a","metadata.upsert",{"command":first_view})
            check("B6-14-real-Docker-plugin-creates-B2-view-via-Broker",
                  first.http_status==200 and
                  first.result["appRevision"]==2 and
                  physical(dbfile,"app-a")["definitions"]["view.contracts"]==
                  original_view,
                  {"http":200,"viewRevision":1,"appRevision":2})
            afterfirst=physical(dbfile,"app-a")
            replay=plug("app-a","metadata.upsert",{"command":first_view})
            afterreplay=physical(dbfile,"app-a")
            check("B6-15-plugin-same-changeId-exact-replay-no-extra-effects",
                  replay.http_status==200 and
                  replay.result["replayed"] is True and
                  afterfirst["receiptCount"]==afterreplay["receiptCount"] and
                  len(afterfirst["events"])==len(afterreplay["events"]) and
                  afterreplay["appRevision"]==2,
                  {"replayed":True,"newAuditEvents":0,
                   "newReceipts":0})
            rest={}
            for n,rid in enumerate(("form.contracts","workflow.approval"),1):
                snap=draft("agent")
                rest[rid]=tool("agent","metadata.upsert",{
                    "command":cmd(snap,rid,specs[rid],"b6-agent-rest-"+str(n))})
            current=physical(dbfile,"app-a")
            check("B6-16-schema-created-through-agent-and-container-plugin",
                  all(x[0]==200 for x in rest.values()) and
                  current["appRevision"]==4 and
                  set(current["definitions"])==set(specs) and
                  current["definitionsHashesValid"],
                  {"appRevision":4,"resources":list(current["definitions"]),
                   "allSourceHashVerified":True})
            check("B6-17-other-app-remains-physically-empty",
                  physical(dbfile,"app-b")["definitions"]=={} and
                  physical(dbfile,"app-b")["receiptCount"]==0 and
                  physical(dbfile,"app-b")["events"]==[],
                  {"appBRevision":0,"appBAudits":0})
            with sync_playwright() as pw:
                browser=pw.chromium.launch(headless=True,args=["--no-sandbox"])
                context=browser.new_context()
                try:
                    page=context.new_page()
                    page.goto(base+"/editor/app-a",wait_until="domcontentloaded")
                    check("B6-18-real-browser-unauthenticated-redirect",
                          page.url.endswith("/editor/login"),
                          {"loginRequired":True})
                    page.locator("#password").fill(password)
                    page.locator("#login").click()
                    page.wait_for_url("**/editor/app-a",timeout=15000)
                    browser_wait(page,"#revision","4")
                    page.locator("#resource-id").fill("view.contracts")
                    page.locator("#select").click()
                    old_view=json.loads(page.locator("#definition").input_value())
                    old_view["title"]="Chrome 用户过期 View 标题"
                    page.locator("#definition").fill(
                        json.dumps(old_view,ensure_ascii=False))
                    check("B6-19-real-human-Chromium-opens-stale-view-snapshot",
                          page.locator("#revision").inner_text()=="4",
                          {"humanSnapshotRevision":4})
                    plugin_view=copy.deepcopy(specs["view.contracts"])
                    plugin_view["title"]="隔离插件成功修改台账"
                    snap=draft("plugin")
                    plugin_change=cmd(snap,"view.contracts",plugin_view,
                                      "b6-plugin-concurrent-view")
                    applied=plug("app-a","metadata.upsert",
                                 {"command":plugin_change})
                    page.locator("#save").click()
                    browser_wait(page,"#message","409")
                    check("B6-20-isolated-plugin-wins-stale-browser-rejected-409",
                          applied.http_status==200 and
                          physical(dbfile,"app-a")["appRevision"]==5 and
                          physical(dbfile,"app-a")["definitions"][
                              "view.contracts"]["title"]==plugin_view["title"] and
                          "409" in page.locator("#message").inner_text(),
                          {"pluginApplied":True,"browserStale":409,
                           "pluginTitleKept":plugin_view["title"]})
                    page.locator("#reload").click()
                    browser_wait(page,"#revision","5")
                    page.locator("#resource-id").fill("form.contracts")
                    page.locator("#select").click()
                    old_form=json.loads(page.locator("#definition").input_value())
                    old_form["title"]="用户核验后的合同登记"
                    page.locator("#definition").fill(
                        json.dumps(old_form,ensure_ascii=False))
                    page.locator("#save").click()
                    browser_wait(page,"#revision","6")
                    check("B6-21-human-can-still-edit-through-governed-browser",
                          physical(dbfile,"app-a")["appRevision"]==6 and
                          physical(dbfile,"app-a")["definitions"][
                              "form.contracts"]["title"]==old_form["title"] and
                          any(x["actor"]=="trusted-reviewer"
                              for x in physical(dbfile,"app-a")["events"]),
                          {"humanAppRevision":6,"browserSave":True})
                    # Simulate unknown external delivery: intentionally do not
                    # consult first response and replay with same changeId.
                    # The host owns the token, so unknown is confined to one
                    # exact command, not a new mutation ID.
                    snap=draft("plugin")
                    v=copy.deepcopy(snap["resources"][
                        "view.contracts"]["definition"])
                    v["title"]="插件写入结果未知后按 changeId 对账"
                    unknown_cmd=cmd(snap,"view.contracts",v,
                                    "b6-unknown-response-same-change-id")
                    ignored=plug("app-a","metadata.upsert",
                                 {"command":unknown_cmd})
                    before_recon=physical(dbfile,"app-a")
                    retry=plug("app-a","metadata.upsert",
                                {"command":unknown_cmd})
                    after_recon=physical(dbfile,"app-a")
                    check("B6-22-lost-reply-reconciled-with-same-changeId-no-new-write",
                          ignored.http_status==retry.http_status==200 and
                          retry.result["replayed"] is True and
                          before_recon["receiptCount"]==
                          after_recon["receiptCount"] and
                          len(before_recon["events"])==
                          len(after_recon["events"]) and
                          after_recon["appRevision"]==7 and
                          after_recon["definitions"]["view.contracts"]["title"]==
                          v["title"],
                          {"firstResponseDiscardedByTest":True,
                           "reconcileSameChangeId":True,
                           "newMutations":0,"revision":7})
                    page.locator("#reload").click()
                    browser_wait(page,"#revision","7")
                    page.locator("#publish").click()
                    browser_wait(page,"#published-version","1")
                    check("B6-23-human-approved-full-typed-manifest-publication",
                          physical(dbfile,"app-a")["currentRelease"]==1 and
                          physical(dbfile,"app-a")["releaseCount"]==1 and
                          physical(dbfile,"app-a")["releaseHashesValid"],
                          {"publishedVersion":1,"schemaResources":4})
                    high=tool("runtime","form.submit",{"formId":"form.contracts",
                        "values":{"contract_no":"B6-H",
                                  "title":"安全隔离高风险合同",
                                  "amount_minor":600000001}})
                    low=tool("runtime","form.submit",{"formId":"form.contracts",
                        "values":{"contract_no":"B6-L",
                                  "title":"安全隔离低风险合同",
                                  "amount_minor":100000000}})
                    check("B6-24-real-published-form-inserts-actual-SQL-records",
                          high[0]==low[0]==200 and
                          len(physical(dbfile,"app-a")["records"])==2 and
                          len(physical(dbfile,"app-b")["records"])==0,
                          {"appARows":2,"appBRows":0})
                    statuses=[]
                    rev=1
                    for action in ("submit","approve","approve"):
                        response=tool("runtime","workflow.advance",{
                            "workflowId":"workflow.approval",
                            "recordId":high[1]["recordId"],
                            "action":action,"expectedVersion":rev})
                        if response[0]!=200:raise AssertionError("APPROVAL_NOT_APPLIED")
                        statuses.append(response[1]["status"])
                        rev=response[1]["version"]
                    check("B6-25-low-code-workflow-runtime-still-works-after-plugin",
                          statuses==["PendingLevel1","PendingLevel2","Approved"],
                          {"highContractApprovalStates":statuses})
                    page.locator("#view").click()
                    browser_wait(page,"#runtime-output","安全隔离高风险合同")
                    shown=json.loads(page.locator("#runtime-output").inner_text())
                    check("B6-26-real-browser-sees-published-plugin-View-and-rows",
                          shown["version"]==1 and
                          len(shown["rows"])==2 and
                          shown["title"]==v["title"],
                          {"rows":2,"viewTitle":shown["title"],
                           "publishedVersion":1})
                    rule=(HERE.parent/"g1-b01-b4"/
                          "reviewed_rule.py").read_text()
                    refused=plug("app-a","code.stage",{"source":rule})
                    human_stage=tool("human","code.stage",{"source":rule})
                    check("B6-27-only-trusted-human-can-stage-tested-code",
                          refused.http_status==403 and
                          human_stage[0]==200 and
                          human_stage[1]["testedCases"]==432 and
                          physical(dbfile,"app-a")["codeArtifacts"]==1,
                          {"pluginStage":403,"independentDockerOracle":432})
                    human_publish=tool("human","code.publish",{
                        "artifactHash":human_stage[1]["artifactHash"],
                        "expectedExtensionVersion":0})
                    high_risk=tool("runtime","risk.score",{
                        "recordId":high[1]["recordId"],
                        "supplierScore":20,"monthsActive":3})
                    check("B6-28-code-extension-deployed-with-plugin-still-isolated",
                          human_publish[0]==200 and
                          high_risk[0]==200 and
                          high_risk[1]["riskScore"]==95 and
                          physical(dbfile,"app-a")["extensionVersion"]==1,
                          {"risk":95,"extensionRelease":1})
                    broker.revoke(tokens["plugin"])
                    revoked=plug("app-a","draft.read",{})
                    check("B6-29-plugin-token-revocation-immediate",
                          revoked.http_status==401 and
                          revoked.result["error"]==
                          "TOOL_GRANT_EXPIRED_OR_REVOKED",
                          {"revokedHttp":401})
                    independent=tool("runtime","risk.score",{
                        "recordId":high[1]["recordId"],
                        "supplierScore":20,"monthsActive":3})
                    check("B6-30-authorized-runtime-survives-plugin-revocation",
                          independent[0]==200 and
                          independent[1]["riskScore"]==95 and
                          physical(dbfile,"app-b")["appRevision"]==0,
                          {"runtimeHttp":200,"risk":95,"otherAppStillEmpty":True})
                finally:
                    context.close()
                    browser.close()
            final=physical(dbfile,"app-a")
            check("B6-31-physical-SQL-plugin-attribution-no-unauthorized-writes",
                  final["appRevision"]==7 and
                  final["definitionsHashesValid"] and
                  final["releaseHashesValid"] and
                  final["codeHashesValid"] and
                  any(e["actor"]=="sandboxed-view-plugin" and
                      e["event"]=="UPSERT"
                      for e in final["events"]) and
                  not any(e["actor"]=="administrator"
                          for e in final["events"]) and
                  physical(dbfile,"app-b")["appRevision"]==0,
                  {"appRevision":7,"pluginAudited":True,
                   "unknownPrivilegesNotRecorded":True,
                   "otherAppRevision":0})
            # Positive host-control confirms the OS boundary: trusted host
            # still has direct SQLite write permission. No privileged host/
            # Saltcorn process is magically restricted by Docker isolation.
            with sqlite3.connect(dbfile) as con:
                con.execute("UPDATE extension_artifacts SET source=? "
                            "WHERE app=?",
                            ("def score_contract(amount_minor, supplier_score, months_active):\n"
                             "    return 0\n","app-a"))
                con.commit()
            drift=tool("runtime","risk.score",{
                "recordId":high[1]["recordId"],
                "supplierScore":20,"monthsActive":3})
            check("B6-32-privileged-host-bypass-still-possible-but-detected",
                  drift==(409,{"error":"ARTIFACT_HASH_DRIFT"}) and
                  not physical(dbfile,"app-a")["codeHashesValid"] and
                  physical(dbfile,"app-a")["currentRelease"]==1,
                  {"hostPrivilegedWriteSucceeded":True,
                   "runtimeRejectedDriftHttp":409,
                   "formalW11_W16Passed":False})
            evidence["lastState"]={
                "appARevision":physical(dbfile,"app-a")["appRevision"],
                "appBRevision":physical(dbfile,"app-b")["appRevision"],
                "appARelease":physical(dbfile,"app-a")["currentRelease"],
                "pluginOSNoDb":True,
                "privilegedHostCanStillBypass":True,
                "runWithDeepSeek":False
            }
        finally:
            srv.shutdown()
            srv.server_close()
            thread.join(timeout=3)
            if original is None:
                os.environ.pop(secret_name,None)
            else:
                os.environ[secret_name]=original
            evidence["summary"]={
                "passed":sum(x["status"]=="PASS" for x in evidence["checks"]),
                "attempted":len(evidence["checks"]),
                "expected":32,"modelCalls":0,"formalG1Passed":False
            }
            Path(args.output).write_text(json.dumps(evidence,ensure_ascii=False,
                                     indent=2)+"\n",encoding="utf-8")
            print("S1_B6_RESULT "+json.dumps(evidence["summary"]),flush=True)
    return 0 if len(evidence["checks"])==32 and all(
        x["status"]=="PASS" for x in evidence["checks"]) else 1


if __name__=="__main__":
    raise SystemExit(main())
