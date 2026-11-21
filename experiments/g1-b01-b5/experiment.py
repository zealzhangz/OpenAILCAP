#!/usr/bin/env python3
"""S1 B5 controlled A/B representation experiment + v3 unified tool ingress.

Two independent test apps, identical B2 engine and B4 sandbox, distinct
authoring representations. Metrics compare only representation/control plane.
Browser edits app-a and compiled IR evolves app-b to identical new manifest.
Negative privileged SQLite bypass is deliberately preserved as an OPEN risk.
"""
from __future__ import annotations
import argparse,copy,json,os,secrets,sqlite3,subprocess,sys,tempfile,threading,time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request,urlopen

from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/"g1-b01-b2"))
sys.path.insert(0,str(ROOT.parent/"g1-b01-b4"))
from schema_core import Actor,SchemaStore,Rejected,sha
from registry import ExtensionRegistry
from sandbox import DockerSandbox
from policy import source_hash
from ir_bridge import IDS,compare_representations,to_ir,from_ir,EXTENSION
from tool_broker import ToolBroker,make_server


def req(base,path,body=None,token=None):
    headers={}
    if token:headers["Authorization"]="Bearer "+token
    if body is not None:headers["Content-Type"]="application/json"
    request=Request(base+path,method="POST" if body is not None else "GET",
                    data=None if body is None else
                         json.dumps(body,ensure_ascii=False).encode("utf-8"),
                    headers=headers)
    try:
        with urlopen(request,timeout=90) as r:
            return r.status,json.loads(r.read())
    except HTTPError as e:
        return e.code,json.loads(e.read())


def db_state(path,app):
    with sqlite3.connect("file:"+str(path.resolve())+"?mode=ro",uri=True) as db:
        h=db.execute("SELECT revision,manifest_hash,current_release FROM apps WHERE app=?",
                     (app,)).fetchone()
        defs=db.execute("SELECT rid,spec,hash,revision FROM definitions WHERE app=?",
                        (app,)).fetchall()
        releases=db.execute("SELECT version,manifest,hash FROM releases WHERE app=? "
                            "ORDER BY version",(app,)).fetchall()
        acts=db.execute("SELECT actor,event,rid FROM events WHERE app=? "
                        "ORDER BY eid",(app,)).fetchall()
        code_count=db.execute("SELECT COUNT(*) FROM extension_artifacts WHERE app=?",
                              (app,)).fetchone()[0]
        ptr=db.execute("SELECT version FROM extension_pointers WHERE app=?",
                       (app,)).fetchone()
        receipts=db.execute("SELECT COUNT(*) FROM receipts WHERE app=?",
                            (app,)).fetchone()[0]
        rows=db.execute("SELECT content FROM records WHERE app=? ORDER BY content",
                        (app,)).fetchall()
    result={"appRevision":h[0],"draftHash":h[1],"publishedVersion":h[2],
            "definitions":{r[0]:json.loads(r[1]) for r in defs},
            "allDefinitionHashesVerified":all(sha(json.loads(r[1]))==r[2] for r in defs),
            "releases":[{"version":r[0],"defs":json.loads(r[1]),"hash":r[2],
                         "verified":sha(json.loads(r[1]))==r[2]} for r in releases],
            "events":[{"actor":r[0],"event":r[1],"resource":r[2]} for r in acts],
            "codeArtifacts":code_count,"extensionVersion":ptr[0] if ptr else 0,
            "receiptCount":receipts,"businessRows":[json.loads(r[0]) for r in rows]}
    return result


def wait_dom(page,selector,expected):
    for _ in range(75):
        try:
            t=page.locator(selector).inner_text(timeout=1000)
            if expected in t:return t
        except Exception:
            pass
        page.wait_for_timeout(125)
    raise AssertionError("BROWSER_OBSERVATION_TIMEOUT_"+selector)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True)
    args=p.parse_args()
    evidence={"scope":"S1_B5_REPRESENTATION_AB_WITH_SHARED_ENGINE",
              "realModelCalls":0,"realDocker":True,
              "independentRuntimesCompared":False,
              "sharedB2AndB4Runtime":True,
              "productionPluginSandboxValidated":False,
              "directPrivilegedSQLiteBypassBlocked":False,
              "formalG1Passed":False,"checks":[]}
    def check(name,ok,value):
        item={"id":name,"status":"PASS" if ok else "FAIL","observed":value}
        evidence["checks"].append(item)
        print("B5 "+name+" "+item["status"]+" "+
              json.dumps(value,ensure_ascii=False),flush=True)
        if not ok:raise AssertionError(name)
    with tempfile.TemporaryDirectory(prefix="s1-b5-") as tmp:
        path=Path(tmp)/"applications.sqlite"
        store=SchemaStore(path)
        store.init()
        for app in ("app-a","app-b"):store.seed_app_for_test(app)
        runner=DockerSandbox()
        registry=ExtensionRegistry(store,runner);registry.init()
        broker=ToolBroker(store,registry)
        tokens={}
        actors={
          "h-a":Actor("reviewer-a","app-a",can_publish=True,can_runtime=True),
          "h-b":Actor("reviewer-b","app-b",can_publish=True,can_runtime=True),
          "a-a":Actor("agent-a","app-a",can_publish=False),
          "a-b":Actor("agent-b","app-b",can_publish=False),
          "p-a":Actor("plugin-a","app-a",kinds=("view",)),
          "p-b":Actor("plugin-b","app-b",kinds=("view",)),
          "r-a":Actor("runtime-a","app-a",can_runtime=True),
          "r-b":Actor("runtime-b","app-b",can_runtime=True)
        }
        for label,actor in actors.items():
            tok=secrets.token_urlsafe(32)
            if label.startswith("h-"):
                allowed={"metadata.upsert","draft.read","app.publish","app.rollback",
                         "code.verify","code.stage","code.publish","code.rollback",
                         "release.read","risk.score","form.submit","workflow.advance"}
            elif label.startswith("a-"):
                allowed={"metadata.upsert","draft.read","code.verify"}
            elif label.startswith("p-"):
                allowed={"metadata.upsert","draft.read"}
            else:
                allowed={"risk.score","form.submit","workflow.advance","release.read"}
            broker.grant(tok,actor,allowed)
            tokens[label]=tok
        sessions={}
        password=secrets.token_urlsafe(30)
        server=make_server(store,registry,broker,sessions,actors["h-a"],password)
        t=threading.Thread(target=server.serve_forever,daemon=True)
        t.start()
        base="http://127.0.0.1:"+str(server.server_port)
        def tool(label,app,name,kw=None):
            return req(base,"/v3/apps/"+app+"/tools/"+name,
                       kw if kw is not None else {},tokens[label])
        def read(label,app):
            status,data=tool(label,app,"draft.read")
            if status!=200:raise AssertionError("DRAFT_TOOL_FAILED")
            return data
        def put(label,app,rid,spec,cid,expected_app=None):
            snap=read(label,app)
            old=snap["resources"].get(rid)
            command={"changeId":cid,"resourceId":rid,
                     "expectedAppRevision":snap["appRevision"] if
                         expected_app is None else expected_app,
                     "expectedRevision":old["revision"] if old else None,
                     "baseContentHash":old["contentHash"] if old else None,
                     "definition":spec}
            return tool(label,app,"metadata.upsert",{"command":command})
        def external(label,app,name,kw):
            env={"PATH":os.getenv("PATH",""),
                 "S1_B5_TOOL_TOKEN":tokens[label]}
            run=subprocess.run([
                sys.executable,str(ROOT/"tool_client.py"),
                "--base",base,"--app",app,"--tool",name,
                "--args-json",json.dumps(kw,ensure_ascii=False)
            ],env=env,capture_output=True,text=True,timeout=75)
            if run.returncode!=0:
                raise AssertionError("SUBPROCESS_TOOL_DID_NOT_RETURN")
            line=next((l for l in run.stdout.splitlines()
                       if l.startswith("S1_B5_TOOL|")),None)
            if line is None:raise AssertionError("MISSING_PROCESS_TOOL_RECEIPT")
            out=json.loads(line.split("|",1)[1])
            return out["status"],out["response"]
        try:
            direct=json.loads((ROOT.parent/"g1-b01-b2"/"contract_spec.json").read_text())
            direct["view.contracts"]["columns"]=[
                "contract_no","title","amount_minor","status"]
            cmp=compare_representations(direct)
            evidence["representationMetrics"]={
                k:cmp[k] for k in
                ("domainAuthoringJsonBytes","irAuthoringJsonBytes",
                 "materializedB2CommandsPerFullCreate")}
            check("B5-01-IR-and-domain-lossless-semantic-roundtrip",
                  cmp["identicalDefinitions"] and cmp["identicalManifest"] and
                  cmp["irRoundtripStable"],
                  {"manifest":cmp["compiled"]["manifestHash"],
                   "sameRuntimeSchema":True})
            check("B5-02-observed-serialization-cost-not-claimed-benchmark",
                  cmp["domainAuthoringJsonBytes"]>0 and
                  cmp["irAuthoringJsonBytes"]>0 and
                  cmp["domainAuthoringJsonBytes"]!=cmp["irAuthoringJsonBytes"],
                  evidence["representationMetrics"])
            plugin_caps=req(base,"/v3/apps/app-a/capabilities",
                            token=tokens["p-a"])
            agent_caps=req(base,"/v3/apps/app-a/capabilities",
                           token=tokens["a-a"])
            check("B5-03-real-HTTP-tool-discovery-scoped-by-principal",
                  plugin_caps[0]==200 and agent_caps[0]==200 and
                  "code.verify" not in plugin_caps[1]["tools"] and
                  "code.verify" in agent_caps[1]["tools"] and
                  "app.publish" not in agent_caps[1]["tools"],
                  {"pluginTools":plugin_caps[1]["tools"],
                   "agentCanVerify":True,"agentCannotPublish":True})
            anon=tool("a-a","app-b","draft.read")
            check("B5-04-principal-cannot-discover-another-app",
                  anon==(403,{"error":"CROSS_APP_FORBIDDEN"}),
                  {"http":anon[0],"reason":anon[1].get("error")})
            for n,rid in enumerate(IDS,1):
                a=put("a-a","app-a",rid,direct[rid],"b5-domain-create-"+str(n))
                b=put("a-b","app-b",rid,cmp["compiled"]["definitions"][rid],
                      "b5-ir-create-"+str(n))
                if a[0]!=200 or b[0]!=200:raise AssertionError("CREATE_"+rid)
            s_a=db_state(path,"app-a")
            s_b=db_state(path,"app-b")
            check("B5-05-two-authored-apps-share-identical-draft-manifest",
                  s_a["draftHash"]==s_b["draftHash"]==
                  cmp["compiled"]["manifestHash"] and
                  s_a["definitions"]==s_b["definitions"] and
                  s_a["appRevision"]==s_b["appRevision"]==4,
                  {"aRevision":4,"bRevision":4,"manifest":s_a["draftHash"]})
            check("B5-06-physical-SQL-definition-hashes-and-receipts",
                  s_a["allDefinitionHashesVerified"] and
                  s_b["allDefinitionHashesVerified"] and
                  s_a["receiptCount"]==s_b["receiptCount"]==4,
                  {"aReceipts":4,"bReceipts":4,"resourceTypes":list(IDS)})
            ir_modified=copy.deepcopy(cmp["ir"])
            ir_modified["interfaces"][1]["caption"]="合同台账 · 插件审核"
            new_defs=from_ir(ir_modified)["definitions"]
            desc=copy.deepcopy(direct)
            desc["view.contracts"]["title"]="合同台账 · 插件审核"
            check("B5-07-IR-edit-compiles-to-exactly-one-B2-resource",
                  [x for x in IDS if new_defs[x]!=direct[x]]==["view.contracts"] and
                  new_defs==desc,
                  {"changed":["view.contracts"],"domainAndIRSame":True})
            pa=put("p-a","app-a","view.contracts",desc["view.contracts"],
                   "b5-plugin-a-view")
            pb=put("p-b","app-b","view.contracts",new_defs["view.contracts"],
                   "b5-plugin-b-view")
            check("B5-08-independent-plugin-HTTP-tool-modifies-only-view",
                  pa[0]==pb[0]==200 and
                  db_state(path,"app-a")["draftHash"]==
                  db_state(path,"app-b")["draftHash"] and
                  db_state(path,"app-a")["appRevision"]==5,
                  {"pluginWrites":2,"newAppRevision":5})
            bad_model=put("p-a","app-a","model.contracts",direct["model.contracts"],
                          "b5-plugin-model-denied")
            forbidden=external("p-a","app-a","code.stage",{"source":"hello"})
            check("B5-09-registered-plugin-cannot-write-model-or-stage-code",
                  bad_model==(403,{"error":"KIND_FORBIDDEN"}) and
                  forbidden==(403,{"error":"TOOL_NOT_GRANTED"}),
                  {"modelHTTP":403,"codeStageHTTP":403})
            forced=external("p-a","app-a","sql.admin",{"actorId":"admin"})
            check("B5-10-plugin-cannot-execute-undeclared-sql-or-mint-actor",
                  forced==(403,{"error":"TOOL_NOT_GRANTED"}),
                  {"http":403,"undeclaredToolDenied":True})
            # The same opaque token does not grant direct v2 B2 rights.
            direct_v2=req(base,"/v2/apps/app-a/draft",token=tokens["p-a"])
            check("B5-11-untrusted-Bearer-cannot-skip-v3-tools-to-v2",
                  direct_v2==(401,{"error":"AUTH_REQUIRED"}),
                  {"http":401,"toolIngressEnforced":True})
            # Application publication is a privileged tool on both tracks.
            pub={}
            for app,label in (("app-a","h-a"),("app-b","h-b")):
                snap=read(label,app)
                pub[app]=tool(label,app,"app.publish",{"command":{
                    "changeId":"b5-"+app+"-pub1",
                    "expectedAppRevision":snap["appRevision"],
                    "manifestHash":snap["manifestHash"]}})
            check("B5-12-both-approvals-publish-identical-immutable-B2-v1",
                  pub["app-a"][0]==pub["app-b"][0]==200 and
                  pub["app-a"][1]["version"]==pub["app-b"][1]["version"]==1 and
                  pub["app-a"][1]["manifestHash"]==
                  pub["app-b"][1]["manifestHash"],
                  {"publishedManifestHash":pub["app-a"][1]["manifestHash"]})
            records={}
            for app,label in (("app-a","r-a"),("app-b","r-b")):
                records[app]={}
                for rid,amount in (("high",600000001),("low",100000000)):
                    res=tool(label,app,"form.submit",{
                        "formId":"form.contracts",
                        "values":{"contract_no":"B5-"+rid,"title":"B5合同-"+rid,
                                  "amount_minor":amount}})
                    if res[0]!=200:raise AssertionError("FORM_SUBMIT_"+app)
                    records[app][rid]=res[1]
            check("B5-13-same-runtime-B2-contract-rows-and-SQL-isolation",
                  all(len(db_state(path,app)["businessRows"])==2 for app in
                      ("app-a","app-b")) and
                  db_state(path,"app-a")["businessRows"]==
                  db_state(path,"app-b")["businessRows"],
                  {"aRows":2,"bRows":2,"recordContentsEqual":True})
            transitions={}
            for app,label in (("app-a","r-a"),("app-b","r-b")):
                transitions[app]={}
                for tier in ("high","low"):
                    record=records[app][tier]
                    states=[]
                    rev=1
                    actions=("submit","approve","approve") if tier=="high" else (
                        "submit","approve")
                    for action in actions:
                        res=tool(label,app,"workflow.advance",{
                            "workflowId":"workflow.approval",
                            "recordId":record["recordId"],
                            "action":action,"expectedVersion":rev})
                        if res[0]!=200:raise AssertionError("WORKFLOW_"+app)
                        rev=res[1]["version"];states.append(res[1]["status"])
                    transitions[app][tier]=states
            check("B5-14-same-runtime-approval-semantic-oracle",
                  transitions["app-a"]==transitions["app-b"] and
                  transitions["app-a"]["high"]==[
                      "PendingLevel1","PendingLevel2","Approved"] and
                  transitions["app-a"]["low"]==["PendingLevel1","Approved"],
                  {"directAndIRStateTraces":transitions["app-a"]})
            source=(ROOT.parent/"g1-b01-b4"/"reviewed_rule.py").read_text()
            agent_verify=external("a-a","app-a","code.verify",{"source":source})
            check("B5-15-agent-can-verify-in-real-Docker-but-not-stage",
                  agent_verify[0]==200 and
                  agent_verify[1]["cases"]==432 and
                  not agent_verify[1]["stageAuthorized"] and
                  agent_verify[1]["sourceHash"]==source_hash(source),
                  {"dockerCases":432,"agentStagePermission":False})
            denied=external("a-a","app-a","code.publish",{
                "artifactHash":source_hash(source),"expectedExtensionVersion":0})
            check("B5-16-agent-cannot-publish-after-successful-build",
                  denied==(403,{"error":"TOOL_NOT_GRANTED"}),
                  {"http":403,"modelHasPublishPermission":False})
            staged={}
            for app,label in (("app-a","h-a"),("app-b","h-b")):
                staged[app]=tool(label,app,"code.stage",{"source":source})
            check("B5-17-trusted-human-rebuilds-and-binds-artifact-to-own-B2",
                  all(x[0]==200 and x[1]["testedCases"]==432 for x in
                      staged.values()) and
                  staged["app-a"][1]["artifactHash"]==
                  staged["app-b"][1]["artifactHash"]==
                  source_hash(source),
                  {"artifactHash":source_hash(source),
                   "twoIndependentDockerValidations":True})
            ex_published={}
            for app,label in (("app-a","h-a"),("app-b","h-b")):
                ex_published[app]=tool(label,app,"code.publish",{
                    "artifactHash":staged[app][1]["artifactHash"],
                    "expectedExtensionVersion":0})
            check("B5-18-both-publish-code-with-revision-and-manifest-binding",
                  all(res[0]==200 and
                      res[1]["publishedExtensionVersion"]==1 for res in
                      ex_published.values()) and
                  db_state(path,"app-a")["extensionVersion"]==
                  db_state(path,"app-b")["extensionVersion"]==1,
                  {"twoPublishedExtensions":2,"baseRelease":1})
            with sync_playwright() as pw:
                browser=pw.chromium.launch(headless=True,args=["--no-sandbox"])
                context=browser.new_context()
                try:
                    page=context.new_page()
                    page.goto(base+"/editor/app-a",wait_until="domcontentloaded")
                    check("B5-19-real-Chromium-login-required",
                          page.url.endswith("/editor/login"),
                          {"login":True})
                    page.locator("#password").fill(password)
                    page.locator("#login").click()
                    page.wait_for_url("**/editor/app-a",timeout=13000)
                    wait_dom(page,"#published-version","1")
                    page.locator("#view").click()
                    wait_dom(page,"#runtime-output","B5合同-high")
                    c=json.loads(page.locator("#runtime-output").inner_text())
                    check("B5-20-real-browser-published-domain-view",
                          c["version"]==1 and len(c["rows"])==2 and
                          "title" in c["columns"],
                          {"chromeRows":len(c["rows"]),"published":1})
                    browser_risk=context.new_page()
                    res=browser_risk.goto(
                        base+"/v2/apps/app-a/runtime/extensions/risk/"+
                        records["app-a"]["high"]["recordId"]+
                        "?supplier_score=20&months_active=3",
                        wait_until="domcontentloaded")
                    amount=json.loads(browser_risk.locator("body").inner_text())
                    ir_risk=tool("r-b","app-b","risk.score",{
                        "recordId":records["app-b"]["high"]["recordId"],
                        "supplierScore":20,"monthsActive":3})
                    check("B5-21-two-representations-have-identical-live-code-outcome",
                          res.status==200 and amount["riskScore"]==95 and
                          ir_risk[0]==200 and ir_risk[1]["riskScore"]==95 and
                          amount["riskTier"]==ir_risk[1]["riskTier"]=="HIGH",
                          {"domainBrowserRisk":95,"irBrokerRisk":95,
                           "sharedRuntime":True})
                    bad=tool("a-a","app-a","code.verify",{"source":
                        "def score_contract(amount_minor, supplier_score, months_active):\n"
                        "    return 0\n"})
                    a_ptr=db_state(path,"app-a")["extensionVersion"]
                    check("B5-22-bad-business-code-not-published",
                          bad==(422,{"error":"SANDBOX_TEST_FAILED"}) and
                          a_ptr==1,
                          {"badCodeHTTP":422,"activeCodeVersion":1})
                    # Human Chromium edits one published app's DRAFT; Agent
                    # old snapshot goes stale. IR track mirrors same semantic
                    # edit via one compiled resource command.
                    before=read("a-a","app-a")
                    page.locator("#reload").click()
                    wait_dom(page,"#revision","5")
                    page.locator("#resource-id").fill("form.contracts")
                    page.locator("#select").click()
                    form=json.loads(page.locator("#definition").input_value())
                    form["title"]="合同登记 · 人工修订"
                    page.locator("#definition").fill(json.dumps(form,ensure_ascii=False))
                    page.locator("#save").click()
                    wait_dom(page,"#revision","6")
                    agent_stale=put("a-a","app-a","view.contracts",
                                    desc["view.contracts"],"b5-agent-stale",
                                    expected_app=5)
                    ir_follow=copy.deepcopy(ir_modified)
                    ir_follow["interfaces"][0]["caption"]=form["title"]
                    new_ir=from_ir(ir_follow)["definitions"]
                    ir_save=put("a-b","app-b","form.contracts",
                                new_ir["form.contracts"],"b5-ir-apply-human-change")
                    check("B5-23-browser-human-edit-and-stale-agent-409",
                          agent_stale[0]==409 and ir_save[0]==200 and
                          db_state(path,"app-a")["draftHash"]==
                          db_state(path,"app-b")["draftHash"] and
                          db_state(path,"app-a")["appRevision"]==6,
                          {"humanBrowserRevision":6,"agentOldSnapshotHTTP":409,
                           "IRMirrorOps":1})
                    live=tool("r-b","app-b","risk.score",{
                        "recordId":records["app-b"]["low"]["recordId"],
                        "supplierScore":88,"monthsActive":50})
                    check("B5-24-draft-changes-do-not-alter-existing-releases",
                          live[0]==200 and live[1]["riskScore"]==0 and
                          db_state(path,"app-a")["publishedVersion"]==
                          db_state(path,"app-b")["publishedVersion"]==1,
                          {"lowRisk":0,"liveRelease":1,"draftRevision":6})
                    pub2={}
                    for app,label in (("app-a","h-a"),("app-b","h-b")):
                        snap=read(label,app)
                        pub2[app]=tool(label,app,"app.publish",{"command":{
                            "changeId":"b5-"+app+"-publish-v2",
                            "expectedAppRevision":snap["appRevision"],
                            "manifestHash":snap["manifestHash"]}})
                    drift=tool("r-b","app-b","risk.score",{
                        "recordId":records["app-b"]["high"]["recordId"],
                        "supplierScore":20,"monthsActive":3})
                    check("B5-25-B2-release-version-epoch-invalidates-bound-code",
                          all(v[0]==200 and v[1]["version"]==2
                              for v in pub2.values()) and
                          drift==(409,{"error":"B2_RELEASE_CHANGED"}) and
                          db_state(path,"app-a")["draftHash"]==
                          db_state(path,"app-b")["draftHash"],
                          {"newB2Version":2,"codeRunHTTP":409,
                           "manifestHashSame":True})
                    roll={}
                    for app,label in (("app-a","h-a"),("app-b","h-b")):
                        roll[app]=tool(label,app,"app.rollback",{"command":{
                            "changeId":"b5-"+app+"-rollback-v1",
                            "expectedPublishedVersion":2,"targetVersion":1}})
                    restored=tool("r-b","app-b","risk.score",{
                        "recordId":records["app-b"]["high"]["recordId"],
                        "supplierScore":20,"monthsActive":3})
                    check("B5-26-both-rollback-restore-original-working-extension",
                          all(v[0]==200 and v[1]["version"]==1 for v in roll.values()) and
                          restored[0]==200 and restored[1]["riskScore"]==95,
                          {"restoredB2":1,"restoredRisk":95})
                    broker.revoke(tokens["p-a"])
                    revoked=external("p-a","app-a","metadata.upsert",{
                        "command":{"actorId":"admin"}})
                    check("B5-27-plugin-token-revocation-is-immediate",
                          revoked==(401,{"error":"TOOL_GRANT_EXPIRED_OR_REVOKED"}),
                          {"afterRevokeHTTP":401})
                finally:
                    context.close()
                    browser.close()
            # NEGATIVE CONTROL: privileged DB process can still directly
            # modify B4 artifact; hash guard fails closed at runtime, but
            # broker/DB integration cannot PREVENT this bypass.
            with sqlite3.connect(path) as db:
                db.execute("UPDATE extension_artifacts SET source=? WHERE app=?",
                           ("def score_contract(amount_minor, supplier_score, months_active):\n"
                            "    return 0\n","app-b"))
                db.commit()
            quarantined=tool("r-b","app-b","risk.score",{
                "recordId":records["app-b"]["high"]["recordId"],
                "supplierScore":20,"monthsActive":3})
            healthy=tool("r-a","app-a","risk.score",{
                "recordId":records["app-a"]["high"]["recordId"],
                "supplierScore":20,"monthsActive":3})
            check("B5-28-privileged-DB-bypass-not-blocked-but-runtime-drift-detected",
                  quarantined==(409,{"error":"ARTIFACT_HASH_DRIFT"}) and
                  healthy[0]==200 and healthy[1]["riskScore"]==95,
                  {"negativeControl":"DIRECT_DB_BYPASS_REMAINS_POSSIBLE",
                   "modifiedAppHttp":409,"independentAppHttp":200})
            final_a=db_state(path,"app-a")
            final_b=db_state(path,"app-b")
            check("B5-29-independent-SQL-audit-two-app-isolation-and-no-LLM",
                  final_a["appRevision"]==final_b["appRevision"]==6 and
                  final_a["publishedVersion"]==final_b["publishedVersion"]==1 and
                  final_a["extensionVersion"]==final_b["extensionVersion"]==1 and
                  any(r["actor"]=="plugin-a" for r in final_a["events"]) and
                  any(r["actor"]=="reviewer-a" for r in final_a["events"]) and
                  any(r["actor"]=="agent-b" for r in final_b["events"]) and
                  final_a["allDefinitionHashesVerified"] and
                  final_b["allDefinitionHashesVerified"],
                  {"aRev":6,"bRev":6,"aAuditCount":len(final_a["events"]),
                   "bAuditCount":len(final_b["events"]),
                   "externalModelCalls":0})
            evidence["finalComparison"]={
                "sameB2ManifestAfterIndependentEdits":
                    final_a["draftHash"]==final_b["draftHash"],
                "sameReleaseHash":
                    final_a["releases"][0]["hash"]==
                    final_b["releases"][0]["hash"],
                "runtimeEngineIdentical":True,
                "strictIRRoundTrip":True,
                "separatePluginOSProcess":True,
                "nativeSaltcornWritePathsUnified":False,
                "privilegedDbWriteBypassPrevented":False,
                "externalModelCalls":0,
                "businessRowCountEach":2,
                "actualBrokerMetadataCommandsPerApp":6,
                "directVsIRRepresentationJsonBytes":evidence["representationMetrics"]
            }
        finally:
            server.shutdown()
            server.server_close()
            t.join(timeout=4)
            evidence["summary"]={
                "passed":sum(x["status"]=="PASS" for x in evidence["checks"]),
                "attempted":len(evidence["checks"]),"expected":29,
                "modelCalls":0,"independentRuntimeComparisons":0}
            Path(args.output).write_text(
                json.dumps(evidence,ensure_ascii=False,indent=2)+"\n",
                encoding="utf-8")
            print("S1_B5_RESULT "+
                  json.dumps(evidence["summary"],ensure_ascii=False),flush=True)
    return 0 if len(evidence["checks"])==29 and all(
        x["status"]=="PASS" for x in evidence["checks"]) else 1

if __name__=="__main__":
    raise SystemExit(main())
