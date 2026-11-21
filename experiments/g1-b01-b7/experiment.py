#!/usr/bin/env python3
"""B7: real Linux DAC -- core-only SQLite, untrusted native plugin and CLI.

CI supplies 3 distinct non-root Linux UIDs. The kernel service owns a private
mode-0700 directory and mode-0600 SQLite/config. The untrusted OS-native
clients actively try SQLite read/write and direct SQL mutation; they can edit
only through scoped v3 typed tools. No Docker, network namespaces or model
calls are needed for *this specific host-DAC boundary*.

CAUTION: test-controller is sudo-capable and remains privileged; tests show
root and SAME KERNEL UID can bypass the API. Not formal G1 acceptance.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import pwd
import secrets
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request,urlopen

from playwright.sync_api import sync_playwright

HERE=Path(__file__).resolve().parent
KERNEL="ailcapb7kern"
PLUGIN="ailcapb7plug"
AGENT="ailcapb7agen"


def run(cmd,*,input=None,timeout=25):
    result=subprocess.run(cmd,input=input,text=True,capture_output=True,
                          timeout=timeout,check=False)
    if result.returncode!=0:
        raise RuntimeError("SUBPROCESS_NONZERO "+
                           str(result.returncode)+" "+result.stderr[-450:])
    return result.stdout


def user_process(username,script,args=(),*,input=None):
    return run(["sudo","-n","runuser","-u",username,"--",
                sys.executable,str(HERE/script),*list(map(str,args))],
               input=input,timeout=25)


def prefixed(stdout,prefix):
    matches=[x.split("|",1)[1] for x in stdout.splitlines()
             if x.startswith(prefix+"|")]
    if len(matches)!=1:
        raise AssertionError("EXPECTED_SINGLE_JSON_RECORD_"+prefix)
    return json.loads(matches[0])


def http(base,path,token=None):
    req=Request(base+path,headers={
        "Authorization":"Bearer "+token
    } if token else {})
    try:
        with urlopen(req,timeout=8) as r:
            return r.status,json.loads(r.read())
    except HTTPError as e:
        return e.code,json.loads(e.read())


def mode_owner(path):
    raw=run(["sudo","-n","stat","-c","%a:%u:%g",str(path)]).strip()
    mode,uid,gid=map(int,raw.split(":"))
    return {"mode":mode,"uid":uid,"gid":gid}


def wait_browser(page,selector,expected):
    for _ in range(80):
        try:
            if expected in page.locator(selector).inner_text(timeout=900):return
        except Exception:
            pass
        page.wait_for_timeout(130)
    raise AssertionError("B7_BROWSER_TIMEOUT_"+selector)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True)
    a=p.parse_args()
    evidence={
        "experiment":"S1_B7_REAL_LINUX_OS_DAC_NATIVE_CLI_AND_PLUGIN",
        "modelCalls":0,
        "separateKernelUid":True,
        "sqliteOwnedOnlyByKernelUid":True,
        "browserAndApiShareTrustedKernel":True,
        "realSaltcornNativeEntrypointsTested":False,
        "cannotBlockRootOrSameUid":True,
        "formalG1Passed":False,
        "checks":[]
    }
    def check(key,condition,observed):
        item={"id":key,"status":"PASS" if condition else "FAIL",
              "observed":observed}
        evidence["checks"].append(item)
        print("B7 "+key+" "+item["status"]+" "+
              json.dumps(observed,ensure_ascii=False),flush=True)
        if not condition:raise AssertionError(key)

    uids={x:pwd.getpwnam(x).pw_uid for x in (KERNEL,PLUGIN,AGENT)}
    check("B7-01-three-real-different-nonroot-host-identities",
          len(set(uids.values()))==3 and all(v>0 for v in uids.values())
          and os.geteuid() not in uids.values(),
          {"kernelUid":uids[KERNEL],"pluginUid":uids[PLUGIN],
           "agentUid":uids[AGENT],"controllerUid":os.geteuid()})
    with tempfile.TemporaryDirectory(prefix="s1-b7-osdac-") as scratch:
        home=Path(scratch)
        home.chmod(0o755)
        private=home/"private"
        ready_dir=home/"readiness"
        private.mkdir(mode=0o700)
        ready_dir.mkdir(mode=0o755)
        dbfile=private/"authority.sqlite"
        cfgfile=private/"service-config.json"
        readyfile=ready_dir/"kernel-ready.json"
        log=home/"service.log"
        tokens={"agent":secrets.token_urlsafe(36),
                "plugin":secrets.token_urlsafe(36),
                "runtime":secrets.token_urlsafe(36)}
        password=secrets.token_urlsafe(35)
        cfg={
            "dbPath":str(dbfile),
            "password":password,
            "agentToken":tokens["agent"],
            "pluginToken":tokens["plugin"],
            "runtimeToken":tokens["runtime"]
        }
        cfgfile.write_text(json.dumps(cfg),encoding="utf-8")
        cfgfile.chmod(0o600)
        run(["sudo","-n","chown","-R",KERNEL+":"+KERNEL,
             str(private),str(ready_dir)])
        run(["sudo","-n","chmod","700",str(private)])
        run(["sudo","-n","chmod","755",str(ready_dir)])
        svc=None
        kernel_pid=None
        try:
            with log.open("w",encoding="utf-8") as stream:
                # Do NOT inject secrets through argv, env, log, or ready file.
                svc=subprocess.Popen([
                    "sudo","-n","runuser","-u",KERNEL,"--",
                    sys.executable,"-u",str(HERE/"kernel_service.py"),
                    "--config",str(cfgfile),"--ready",str(readyfile)
                ],stdout=stream,stderr=subprocess.STDOUT,
                  stdin=subprocess.DEVNULL)
                ready=None
                for _ in range(130):
                    if readyfile.exists():
                        ready=json.loads(readyfile.read_text(encoding="utf-8"))
                        break
                    if svc.poll() is not None:
                        raise RuntimeError("KERNEL_DIED: "+
                                           log.read_text()[-1200:])
                    time.sleep(.08)
                if ready is None:raise RuntimeError("KERNEL_NOT_READY")
                kernel_pid=ready["kernelPid"]
                base="http://127.0.0.1:"+str(ready["port"])
                check("B7-02-server-runs-as-dedicated-database-owner",
                      ready["kernelUid"]==uids[KERNEL] and
                      kernel_pid>0 and svc.poll() is None,
                      {"kernelUid":ready["kernelUid"],"pidExists":True})
                privstat=mode_owner(private)
                cfgstat=mode_owner(cfgfile)
                dbstat=mode_owner(dbfile)
                check("B7-03-real-DAC-private-directory-and-files",
                      privstat["mode"]==700 and
                      cfgstat["mode"]==dbstat["mode"]==600 and
                      all(x["uid"]==uids[KERNEL] for x in (
                          privstat,cfgstat,dbstat)),
                      {"directoryMode":700,"configMode":600,
                       "sqliteMode":600,"ownerUid":uids[KERNEL]})
                health=http(base,"/health")
                check("B7-04-live-domain-kernel-available-over-loopback",
                      health[0]==200 and health[1]["status"]=="OK",
                      {"status":health[0],"localOnly":True})
                # Independent physical inspection is itself run as the kernel
                # uid. Ordinary Python controller cannot traverse private dir.
                def physical():
                    return prefixed(user_process(
                        KERNEL,"physical_sql_oracle.py",(
                            "--db",dbfile)), "S1_B7_PHYSICAL")
                before=physical()
                check("B7-05-independent-real-SQL-shows-two-empty-apps",
                      before["app-a"]["revision"]==
                      before["app-b"]["revision"]==0 and
                      before["app-a"]["resources"]=={} and
                      before["app-b"]["resources"]=={},
                      {"appARevision":0,"appBRevision":0})
                def probes(name):
                    return prefixed(user_process(
                        name,"direct_probe.py",(
                            "--db",dbfile,"--config",cfgfile,
                            "--kernel-pid",kernel_pid)),
                            "S1_B7_DIRECT_PROBE")
                plugin_attack=probes(PLUGIN)
                agent_attack=probes(AGENT)
                blocked_keys=("dbOpenRead","dbOpenWrite","dbSqliteRead",
                              "dbSqliteDirectUpdate","configRead",
                              "kernelEnvironRead","kernelFdDirectoryRead")
                check("B7-06-real-native-plugin-direct-DB-SQL-CLI-blocked",
                      plugin_attack["uid"]==uids[PLUGIN] and
                      all(plugin_attack[k]=="DENIED" for k in blocked_keys),
                      plugin_attack)
                check("B7-07-real-native-Agent-direct-DB-SQL-CLI-blocked",
                      agent_attack["uid"]==uids[AGENT] and
                      all(agent_attack[k]=="DENIED" for k in blocked_keys),
                      agent_attack)
                post_attack=physical()
                check("B7-08-physical-DB-unmodified-by-direct-CLI-attacks",
                      post_attack==before,
                      {"identicalPhysicalSnapshot":True,
                       "noDirectSqlMutation":True})
                check("B7-09-public-ready-file-does-not-contain-token",
                      all(token not in readyfile.read_text()
                          for token in (*tokens.values(),password)) and
                      "dbPath" not in readyfile.read_text(),
                      {"publicMetadataOnly":True,"secretsInReady":False})
                def client(user,role,app,tool,args):
                    payload=json.dumps({
                        "base":base,"token":tokens[role],
                        "app":app,"tool":tool,"args":args
                    },ensure_ascii=False)+"\n"
                    raw=user_process(user,"native_client.py",(),input=payload)
                    return prefixed(raw,"S1_B7_TOOL")
                def ask(user,role,tool,args,app="app-a"):
                    return client(user,role,app,tool,args)
                def snapshot(role="agent",user=AGENT):
                    val=ask(user,role,"draft.read",{})
                    if val["status"]!=200:
                        raise AssertionError("B7_DRAFT_NOT_READABLE")
                    return val["result"]
                def command(snap,rid,definition,cid):
                    old=snap["resources"].get(rid)
                    return {
                        "changeId":cid,"resourceId":rid,
                        "expectedAppRevision":snap["appRevision"],
                        "expectedRevision":old["revision"] if old else None,
                        "baseContentHash":old["contentHash"] if old else None,
                        "definition":definition
                    }
                plugin_draft=ask(PLUGIN,"plugin","draft.read",{})
                check("B7-10-native-plugin-can-use-scoped-API-no-DB-grant",
                      plugin_draft["status"]==200 and
                      plugin_draft["result"]["appRevision"]==0 and
                      plugin_attack["dbOpenRead"]=="DENIED",
                      {"draftHTTP":200,"directSqliteRead":"DENIED"})
                unknown=ask(PLUGIN,"plugin","sql.admin",{
                    "query":"UPDATE apps SET revision=999"})
                direct_code=ask(PLUGIN,"plugin","code.publish",{
                    "artifactHash":"x","expectedExtensionVersion":0})
                check("B7-11-native-plugin-unknown-sql-and-code-tools-denied",
                      unknown["status"]==403 and
                      direct_code["status"]==403 and
                      physical()["app-a"]["revision"]==0,
                      {"sqlToolHttp":403,"publishToolHttp":403,
                       "unchangedRevision":0})
                forgery=ask(PLUGIN,"plugin","metadata.upsert",{
                    "command":{},"actorId":"administrator"})
                check("B7-12-native-plugin-role-forgery-rejected",
                      forgery["status"]==422 and
                      forgery["result"].get("error")=="TOOL_ARGUMENTS_INVALID",
                      {"http":422,"notTrustedActorId":True})
                other=client(PLUGIN,"plugin","app-b","draft.read",{})
                check("B7-13-real-cross-application-native-process-denied",
                      other["status"]==403 and
                      other["result"].get("error")=="CROSS_APP_FORBIDDEN",
                      {"http":403,"appBRevision":physical()["app-b"]["revision"]})
                raw_http=http(base,"/v2/apps/app-a/draft",tokens["plugin"])
                check("B7-14-untrusted-native-API-cannot-bypass-v3-with-v2",
                      raw_http==(401,{"error":"AUTH_REQUIRED"}),
                      {"http":401,"v2BearerNotGranted":True})
                specs=json.loads((HERE.parent/"g1-b01-b2"/
                                  "contract_spec.json").read_text(encoding="utf-8"))
                specs["view.contracts"]["columns"]=[
                    "contract_no","title","amount_minor","status"]
                model=ask(AGENT,"agent","metadata.upsert",{
                    "command":command(snapshot(),"model.contracts",
                                      specs["model.contracts"],
                                      "b7-agent-model-001")})
                check("B7-15-native-Agent-writes-Model-only-via-kernel",
                      model["status"]==200 and
                      physical()["app-a"]["revision"]==1 and
                      all(agent_attack[k]=="DENIED" for k in blocked_keys),
                      {"agentAuthorizedTool":200,"sqlDirectDenied":True})
                not_model=ask(PLUGIN,"plugin","metadata.upsert",{
                    "command":command(snapshot(),"model.contracts",
                                      specs["model.contracts"],
                                      "b7-plugin-model-unauth")})
                check("B7-16-native-plugin-view-kind-cannot-edit-model",
                      not_model["status"]==403 and
                      not_model["result"].get("error")=="KIND_FORBIDDEN",
                      {"http":403})
                view=ask(PLUGIN,"plugin","metadata.upsert",{
                    "command":command(snapshot("plugin",PLUGIN),"view.contracts",
                                      specs["view.contracts"],
                                      "b7-plugin-view-001")})
                check("B7-17-native-plugin-edits-View-via-service-without-DB-access",
                      view["status"]==200 and
                      view["result"]["appRevision"]==2 and
                      physical()["app-a"]["resources"]["view.contracts"]==
                      specs["view.contracts"],
                      {"viewHttp":200,"resourceRevision":1,
                       "dbNotDirectlyMapped":True})
                for i,rid in enumerate(("form.contracts","workflow.approval"),1):
                    result=ask(AGENT,"agent","metadata.upsert",{
                        "command":command(snapshot(),rid,specs[rid],
                                          "b7-agent-other-"+str(i))})
                    if result["status"]!=200:
                        raise AssertionError("B7_SEED_"+rid)
                complete=physical()
                check("B7-18-independent-SQL-confirms-four-typed-resources-and-audits",
                      complete["app-a"]["revision"]==4 and
                      set(complete["app-a"]["resources"])==set(specs) and
                      complete["app-a"]["resourceHashesValid"] and
                      complete["app-a"]["manifestMatches"] and
                      any(e["actor"]=="b7-native-plugin"
                          for e in complete["app-a"]["events"]) and
                      any(e["actor"]=="b7-agent"
                          for e in complete["app-a"]["events"]),
                      {"appRevision":4,"resources":list(specs),
                       "pluginAudited":True})
                stale=snapshot()
                # Real native plugin performs second View mutation while a
                # true Chromium browser has an old editor snapshot.
                with sync_playwright() as pw:
                    browser=pw.chromium.launch(headless=True,args=["--no-sandbox"])
                    ctx=browser.new_context()
                    try:
                        page=ctx.new_page()
                        page.goto(base+"/editor/app-a",wait_until="domcontentloaded")
                        check("B7-19-real-browser-requires-trusted-human-session",
                              page.url.endswith("/editor/login"),
                              {"unauthenticatedRedirect":True})
                        page.locator("#password").fill(password)
                        page.locator("#login").click()
                        page.wait_for_url("**/editor/app-a",timeout=16000)
                        wait_browser(page,"#revision","4")
                        page.locator("#resource-id").fill("view.contracts")
                        page.locator("#select").click()
                        old=json.loads(page.locator("#definition").input_value())
                        old["title"]="浏览器过时草稿的修改"
                        page.locator("#definition").fill(
                            json.dumps(old,ensure_ascii=False))
                        newview=copy.deepcopy(specs["view.contracts"])
                        newview["title"]="原生受限插件实际提交的 View"
                        accepted=ask(PLUGIN,"plugin","metadata.upsert",{
                            "command":command(snapshot("plugin",PLUGIN),
                                              "view.contracts",newview,
                                              "b7-plugin-view-002")})
                        page.locator("#save").click()
                        wait_browser(page,"#message","409")
                        check("B7-20-real-native-plugin-wins-and-Chromium-stale-409",
                              accepted["status"]==200 and
                              physical()["app-a"]["revision"]==5 and
                              physical()["app-a"]["resources"][
                                  "view.contracts"]["title"]==newview["title"] and
                              "409" in page.locator("#message").inner_text(),
                              {"browserHttp":409,"pluginMutation":200,
                               "correctViewRetained":True})
                        stale_cmd=command(stale,"form.contracts",
                                          specs["form.contracts"],
                                          "b7-stale-agent-edit")
                        rejected=ask(AGENT,"agent","metadata.upsert",{
                            "command":stale_cmd})
                        check("B7-21-old-Agent-version-cannot-override-plugin-or-human",
                              rejected["status"]==409 and
                              rejected["result"].get("error")=="APP_REVISION_CONFLICT",
                              {"agentStaleHttp":409,
                               "currentRevision":physical()["app-a"]["revision"]})
                        page.locator("#reload").click()
                        wait_browser(page,"#revision","5")
                        page.locator("#resource-id").fill("form.contracts")
                        page.locator("#select").click()
                        form=json.loads(page.locator("#definition").input_value())
                        form["title"]="人工继续编辑已隔离项目"
                        page.locator("#definition").fill(
                            json.dumps(form,ensure_ascii=False))
                        page.locator("#save").click()
                        wait_browser(page,"#revision","6")
                        check("B7-22-human-continues-safe-browser-edit-in-one-kernel",
                              physical()["app-a"]["revision"]==6 and
                              physical()["app-a"]["resources"][
                                  "form.contracts"]["title"]==form["title"],
                              {"humanDraftRevision":6})
                        # Native plugin may retry an identical changeId but
                        # cannot skip B2 idempotency receipts.
                        request=command(snapshot("plugin",PLUGIN),
                                        "view.contracts",newview,
                                        "b7-plugin-idempotency")
                        p1=ask(PLUGIN,"plugin","metadata.upsert",{"command":request})
                        before_replay=physical()
                        p2=ask(PLUGIN,"plugin","metadata.upsert",{"command":request})
                        after_replay=physical()
                        check("B7-23-real-native-replay-returns-existing-receipt",
                              p1["status"]==200 and
                              p2["status"]==200 and
                              p2["result"].get("replayed") is True and
                              after_replay["app-a"]["receipts"]==
                              before_replay["app-a"]["receipts"] and
                              len(after_replay["app-a"]["events"])==
                              len(before_replay["app-a"]["events"]),
                              {"replayed":True,"extraEvents":0,
                               "extraReceipts":0})
                        page.locator("#reload").click()
                        wait_browser(page,"#revision","7")
                        page.locator("#publish").click()
                        wait_browser(page,"#published-version","1")
                        pub=physical()
                        check("B7-24-trusted-human-publishes-immutable-B2-manifest",
                              pub["app-a"]["publishedVersion"]==1 and
                              pub["app-a"]["releaseHashesValid"] and
                              pub["app-a"]["releases"]==1,
                              {"publishedB2":1,"releaseVerified":True})
                        def runtime(tool_name,args0):
                            return ask(AGENT if False else PLUGIN,"plugin",
                                       tool_name,args0)
                        # Runtime identity may operate published application,
                        # but must never see or directly write the DB.
                        amount=client(AGENT,"runtime","app-a","form.submit",{
                            "formId":"form.contracts",
                            "values":{"contract_no":"B7-001",
                                      "title":"受控内核合同数据",
                                      "amount_minor":600000001}})
                        check("B7-25-published-contract-form-works-via-kernel",
                              amount["status"]==200 and
                              len(physical()["app-a"]["records"])==1,
                              {"formHttp":200,"records":1})
                        record_id=amount["result"]["recordId"]
                        states=[]
                        rev=1
                        for action in ("submit","approve","approve"):
                            result=client(AGENT,"runtime","app-a",
                                          "workflow.advance",{
                                              "workflowId":"workflow.approval",
                                              "recordId":record_id,
                                              "action":action,
                                              "expectedVersion":rev})
                            if result["status"]!=200:
                                raise AssertionError("WORKFLOW_FAILED")
                            states.append(result["result"]["status"])
                            rev=result["result"]["version"]
                        check("B7-26-real-threshold-workflow-unchanged-by-DAC",
                              states==["PendingLevel1",
                                       "PendingLevel2","Approved"],
                              {"workflowStates":states})
                        page.locator("#view").click()
                        wait_browser(page,"#runtime-output","受控内核合同数据")
                        visible=json.loads(
                            page.locator("#runtime-output").inner_text())
                        check("B7-27-real-browser-renders-published-typed-runtime",
                              visible["version"]==1 and
                              len(visible["rows"])==1 and
                              visible["title"]==newview["title"],
                              {"rows":1,"viewTitle":visible["title"]})
                    finally:
                        ctx.close()
                        browser.close()
                # Counterexample: a process with the SAME kernel OS UID can
                # perform raw SQLite without tools. This is essential: a uid
                # boundary alone doesn't secure arbitrary code running as uid.
                same_uid=probes(KERNEL)
                check("B7-28-same-kernel-uid-can-bypass-API-security-limitation",
                      same_uid["dbOpenRead"]=="ALLOWED" and
                      same_uid["dbSqliteDirectUpdate"]=="ALLOWED" and
                      same_uid["configRead"]=="ALLOWED",
                      {"negativeControl":"SAME_UID_CAN_WRITE_DIRECTLY",
                       "notProductionProof":True})
                before_root=physical()
                # Root will ALWAYS be able to change the physical DB. The
                # corrupting mutation deliberately leaves resource hash
                # unchanged so the kernel catches drift and quarantines.
                malicious=copy.deepcopy(
                    before_root["app-a"]["resources"]["view.contracts"])
                malicious["title"]="宿主 root 越权篡改资源"
                sql=("UPDATE definitions SET spec=? WHERE app='app-a' "
                     "AND rid='view.contracts'")
                script=("import sqlite3,sys;"
                        "c=sqlite3.connect(sys.argv[1]);"
                        "c.execute(sys.argv[2],(sys.argv[3],));"
                        "c.commit();c.close()")
                run(["sudo","-n",sys.executable,"-c",script,
                     str(dbfile),sql,
                     json.dumps(malicious,ensure_ascii=False)])
                after_root=physical()
                check("B7-29-privileged-root-bypass-still-physically-possible",
                      after_root["app-a"]["resources"][
                          "view.contracts"]["title"]==malicious["title"] and
                      not after_root["app-a"]["resourceHashesValid"],
                      {"rootCorruptionPhysicallySucceeded":True,
                       "noClaimThatRootWasBlocked":True})
                drift=ask(AGENT,"agent","draft.read",{})
                after_detect=physical()
                check("B7-30-kernel-detects-root-bypass-and-quarantines-draft",
                      drift["status"]==409 and
                      drift["result"].get("error")=="RESOURCE_DRIFT" and
                      after_detect["app-a"]["state"]=="QUARANTINED",
                      {"draftHttp":409,"appState":"QUARANTINED"})
                original_release=client(
                    AGENT,"runtime","app-a","release.read",{})
                check("B7-31-last-verified-release-retained-despite-draft-drift",
                      original_release["status"]==200 and
                      original_release["result"]["version"]==1 and
                      original_release["result"]["manifestHash"]==
                      before_root["app-a"]["manifestHash"],
                      {"lastGoodVersion":1,"releaseHashUnchanged":True})
                final=physical()
                check("B7-32-app-isolation-and-principal-audit-physical-oracle",
                      final["app-b"]["revision"]==0 and
                      final["app-b"]["resources"]=={} and
                      final["app-a"]["revision"]==7 and
                      any(e["actor"]=="b7-human-reviewer" for e in
                          final["app-a"]["events"]) and
                      any(e["actor"]=="b7-native-plugin" for e in
                          final["app-a"]["events"]) and
                      any(e["actor"]=="b7-agent" for e in
                          final["app-a"]["events"]),
                      {"appBRevision":0,"appARevision":7,
                       "kernelStoredActorAudit":True})
                evidence["finalPhysical"]={
                    "appARevision":final["app-a"]["revision"],
                    "appBRevision":final["app-b"]["revision"],
                    "publishedVersion":final["app-a"]["publishedVersion"],
                    "lastKnownGoodRelease":True,
                    "kernelUid":uids[KERNEL],
                    "directUnprivilegedSqliteDenied":True,
                    "privilegedRootSqliteDenied":False,
                    "kernelStateAfterRootAttack":final["app-a"]["state"]
                }
        finally:
            if kernel_pid is not None:
                subprocess.run(["sudo","-n","kill","-TERM",str(kernel_pid)],
                               text=True,capture_output=True,timeout=7,
                               check=False)
            if svc is not None:
                try:svc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    svc.terminate()
            evidence["summary"]={
                "passed":sum(x["status"]=="PASS" for x in evidence["checks"]),
                "attempted":len(evidence["checks"]),
                "expected":32,"modelCalls":0,"formalG1Passed":False
            }
            Path(a.output).write_text(json.dumps(evidence,ensure_ascii=False,
                                     indent=2)+"\n",encoding="utf-8")
            print("S1_B7_RESULT "+
                  json.dumps(evidence["summary"],ensure_ascii=False),
                  flush=True)
    return 0 if len(evidence["checks"])==32 and all(
        item["status"]=="PASS" for item in evidence["checks"]) else 1


if __name__=="__main__":
    raise SystemExit(main())
