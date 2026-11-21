#!/usr/bin/env python3
"""B10 true traffic cutover with 2 live, independent native Saltcorn servers.

B2 trusted Domain Kernel owns authority and real business workflow; router
runs as its own non-root Linux UID and gets ONLY B2 release.read; Saltcorn
runs as another UID with derived DBs and no kernel token. Controller holds
reversible release/route grants. Test-only hold header checks in-flight route
pinning; this is not proof of production zero downtime/long-lived connections.
"""
from __future__ import annotations

import copy
import json
import os
import pwd
import secrets
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from urllib.error import HTTPError,URLError
from urllib.request import Request,urlopen

from playwright.sync_api import sync_playwright

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
sys.path.insert(0,str(ROOT/"g1-b01-b2"))
sys.path.insert(0,str(ROOT/"g1-b01-b9"))
from schema_core import sha
from projector import compile_release,check_compiled
from router import ROUTE

KERNEL="ailcapb10kern"
SALT="ailcapb10salt"
ROUTER="ailcapb10route"
EMAIL="s1-research-admin@example.invalid"
MARKER="HT-2026-000001"


def run(argv,*,cwd=None,env=None,stdin=None,timeout=120,ok=True):
    r=subprocess.run(list(map(str,argv)),cwd=str(cwd) if cwd else None,
                     env=env,input=stdin,text=True,capture_output=True,
                     check=False,timeout=timeout)
    if ok and r.returncode:
        raise RuntimeError("SUBPROCESS_FAILED "+str(r.returncode)+
                           " "+str(argv[0])+" "+r.stderr[-260:])
    return r


def one(line,tag):
    values=[x.partition("|")[2] for x in line.splitlines()
            if x.startswith(tag+"|")]
    if len(values)!=1:raise AssertionError("EXPECTED_ONE_"+tag)
    return json.loads(values[0])


def tool(base,app,name,token,args):
    return web_call(base+"/v3/apps/"+app+"/tools/"+name,
                    method="POST",body=args,bearer=token)


def web_call(url,method="GET",body=None,bearer=None,headers=None,timeout=12):
    h={} if headers is None else dict(headers)
    if bearer is not None:h["Authorization"]="Bearer "+bearer
    raw=None
    if body is not None:
        raw=json.dumps(body,ensure_ascii=False).encode()
        h["Content-Type"]="application/json"
    req=Request(url,method=method,data=raw,headers=h)
    try:
        with urlopen(req,timeout=timeout) as r:
            return r.status,dict(r.headers),r.read(2*1024*1024+1024)
    except HTTPError as e:
        return e.code,dict(e.headers),e.read(2*1024*1024+1024)


def api_json(url,method="GET",body=None,bearer=None):
    code,headers,payload=web_call(url,method,body,bearer)
    return code,json.loads(payload)


def wait_page(url,max_wait=65):
    deadline=time.monotonic()+max_wait
    while time.monotonic()<deadline:
        try:
            if web_call(url,timeout=2)[0]==200:return True
        except (OSError,TimeoutError,URLError):pass
        time.sleep(.16)
    return False


def wait_text(page,selector,text0):
    for _ in range(80):
        try:
            if text0 in page.locator(selector).inner_text(timeout=700):return
        except Exception:pass
        page.wait_for_timeout(120)
    raise AssertionError("WAIT_TEXT_"+selector)


def main():
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",required=True)
    opts=ap.parse_args()
    data={
        "experiment":"S1_B10_TWO_REAL_SALTCORN_INSTANCES_TRAFFIC_CAS",
        "zeroDowntimeProductionValidated":False,
        "runtimeCacheHotUpdateValidated":False,
        "nativeWorkflowParityValidated":False,
        "businessDataMirroredToNative":False,
        "persistedRouterJournalValidated":False,
        "formalG1Passed":False,
        "modelCalls":0,
        "checks":[]
    }
    def check(name,passed,observed):
        item={"id":name,"status":"PASS" if passed else "FAIL",
              "observed":observed}
        data["checks"].append(item)
        print(name+" "+item["status"]+" "+
              json.dumps(observed,ensure_ascii=False),flush=True)
        if not passed:raise AssertionError(name)

    uids={u:pwd.getpwnam(u).pw_uid for u in (KERNEL,SALT,ROUTER)}
    check("B10-01-three-independent-nonroot-host-UIDs",
          len(set(uids.values()))==3 and all(x>0 for x in uids.values()),
          {"kernelUid":uids[KERNEL],"runtimeUid":uids[SALT],
           "routerUid":uids[ROUTER]})

    with tempfile.TemporaryDirectory(prefix="s1-b10-traffic-") as location:
        home=Path(location);home.chmod(0o755)
        stage=home/"public-source";stage.mkdir(mode=0o755)
        files={
            "g1-b01-b2":("schema_core.py","schema_http.py"),
            "g1-b01-b4":("registry.py","policy.py","sandbox.py","worker.py"),
            "g1-b01-b5":("tool_broker.py",),
            "g1-b01-b7":("physical_sql_oracle.py",),
            "g1-b01-b9":("native_oracle.py",),
            "g1-b01-b10":("kernel_service.py","native_env_launcher.py",
                           "router.py"),
            "platform-saltcorn":("contract-pack.json","seed-contract.js")
        }
        for directory,names in files.items():
            folder=stage/directory;folder.mkdir(mode=0o755)
            for name in names:
                shutil.copyfile(ROOT/directory/name,folder/name)
                (folder/name).chmod(0o644)
        authority=home/"authority-private"
        runtime=home/"runtime-private"
        route_private=home/"route-private"
        ready=home/"ready"
        for directory in (authority,runtime,route_private):
            directory.mkdir(mode=0o700)
        ready.mkdir(mode=0o755)
        auth_db=authority/"authority.sqlite"
        auth_cfg=authority/"config.json"
        route_cfg=route_private/"router.json"
        kernel_ready=ready/"kernel-ready.json"
        router_ready=ready/"router-ready.json"
        kerlog=home/"kernel.log"
        routelog=home/"router.log"
        admin_password=secrets.token_urlsafe(34)
        pass_kernel=secrets.token_urlsafe(34)
        agent_token=secrets.token_urlsafe(36)
        publisher_token=secrets.token_urlsafe(36)
        runtime_token=secrets.token_urlsafe(36)
        router_read_token=secrets.token_urlsafe(36)
        app_b_token=secrets.token_urlsafe(36)
        route_admin_token=secrets.token_urlsafe(36)
        session_secret=secrets.token_urlsafe(43)
        auth_cfg.write_text(json.dumps({
            "dbPath":str(auth_db),"humanPassword":pass_kernel,
            "agentToken":agent_token,"publisherToken":publisher_token,
            "runtimeToken":runtime_token,
            "appBPublisherToken":app_b_token,
            "routerReadToken":router_read_token
        }))
        auth_cfg.chmod(0o600)
        run(["sudo","-n","chown","-R",KERNEL+":"+KERNEL,authority])
        run(["sudo","-n","chown","-R",SALT+":"+SALT,runtime])
        run(["sudo","-n","chown","-R",KERNEL+":"+KERNEL,ready])
        # Router currently must use app-a read scope. B10 has a separate
        # short-lived read-only grant, never an admin/publish token.
        # Modify only this B10 kernel fixture (no B9 code changes).
        procs=[]
        kernel=None
        routeproc=None
        native_processes={}
        native_logs={}
        env_native=os.environ.copy()
        env_native.update({
            "PATH":os.environ.get("PATH","/usr/bin:/bin"),
            "HOME":str(runtime),"SALTCORN_NWORKERS":"1",
            "SALTCORN_SESSION_SECRET":session_secret,
            "SQLITE_FILEPATH":str(runtime/"projection-invalid.sqlite")
        })

        def physical_core():
            p=run(["sudo","-n","runuser","-u",KERNEL,"--",
                   sys.executable,
                   str(stage/"g1-b01-b7"/"physical_sql_oracle.py"),
                   "--db",auth_db],cwd=stage)
            return one(p.stdout,"S1_B7_PHYSICAL")

        def native_command(command,db,timeout=140,allow_fail=False):
            env={key:env_native[key] for key in (
                "PATH","HOME","SALTCORN_NWORKERS","SALTCORN_SESSION_SECRET")}
            env["SQLITE_FILEPATH"]=str(db)
            return run(["sudo","-n","runuser","-u",SALT,"--",sys.executable,
                        str(stage/"g1-b01-b10"/"native_env_launcher.py"),
                        *command],cwd=stage,env=env_native,
                       stdin=json.dumps(env)+"\n",timeout=timeout,
                       ok=not allow_fail)

        def physical_native(db):
            p=native_command([
                sys.executable,str(stage/"g1-b01-b9"/"native_oracle.py"),
                "--db",db],db,timeout=15)
            return one(p.stdout,"S1_B9_NATIVE_ORACLE")

        def native_materialize(tag,release):
            compiled=compile_release(release,template)
            check_compiled(compiled)
            pack=stage/("approved-"+tag+".json")
            pack.write_text(json.dumps(
                compiled["projectionPack"],ensure_ascii=False))
            pack.chmod(0o444)
            db=runtime/("projection-"+tag+".sqlite")
            native_command(["saltcorn","reset-schema","-f"],db)
            native_command(["saltcorn","install-pack","-f",pack],db)
            native_command(["saltcorn","run-js","-f",
                            stage/"platform-saltcorn"/"seed-contract.js"],db)
            native_command(["saltcorn","create-user","--admin",
                            "--email",EMAIL,"--password",admin_password],db)
            oracle=physical_native(db)
            if oracle["viewColumns"]!=(
                release["definitions"]["view.contracts"]["columns"]
            ) or len(oracle["businessRows"])!=1:
                raise AssertionError("NATIVE_ORACLE_MISMATCH")
            return {"db":db,"pack":pack,"projection":compiled,"oracle":oracle}

        def start_native(tag,db,port):
            entry=env_native.copy()
            cfg={key:entry[key] for key in (
                "PATH","HOME","SALTCORN_NWORKERS","SALTCORN_SESSION_SECRET")}
            cfg["SQLITE_FILEPATH"]=str(db)
            logfile=home/("saltcorn-"+tag+".log")
            native_logs[tag]=logfile
            stream=logfile.open("w")
            p=subprocess.Popen([
                "sudo","-n","runuser","-u",SALT,"--",
                sys.executable,str(stage/"g1-b01-b10"/"native_env_launcher.py"),
                "saltcorn","serve","--port",str(port),"--noscheduler"
            ],cwd=str(stage),env=entry,stdin=subprocess.PIPE,
              stdout=stream,stderr=subprocess.STDOUT,text=True,
              start_new_session=True)
            stream.close()
            p.stdin.write(json.dumps(cfg)+"\n")
            p.stdin.flush()
            p.stdin.close()
            native_processes[tag]=p
            url="http://127.0.0.1:"+str(port)
            if not wait_page(url+"/auth/login",80):
                trace=logfile.read_text(errors="replace")[-800:]
                for val in (admin_password,session_secret):
                    trace=trace.replace(val,"[REDACTED]")
                raise RuntimeError("NATIVE_NOT_READY "+tag+" "+trace)
            return url

        def router_admin(endpoint,payload,token=None):
            return api_json(route_base+"/_admin/"+endpoint,"POST",payload,
                            route_admin_token if token is None else token)

        def router_register(version,release,port):
            return router_admin("register",{
                "version":version,"manifestHash":release["manifestHash"],
                "port":port,"marker":MARKER
            })
        def switch(change_id,expected_epoch,from_version,to_version,release):
            return router_admin("switch",{
                "changeId":change_id,"expectedEpoch":expected_epoch,
                "expectedFromVersion":from_version,
                "targetVersion":to_version,
                "manifestHash":release["manifestHash"]
            })
        def b2(toolname,token,args,app="app-a"):
            st,_,raw=tool(core_base,app,toolname,token,args)
            try:d=json.loads(raw)
            except ValueError:d={}
            return st,d
        def required(toolname,token,args,app="app-a"):
            status,data0=b2(toolname,token,args,app)
            if status!=200:
                raise AssertionError("BAD_TOOL_"+toolname+"_"+str(status)+
                                     "_"+str(data0)[:180])
            return data0
        def command(snapshot,rid,definition,cid):
            old=snapshot["resources"].get(rid)
            return {
                "changeId":cid,"resourceId":rid,
                "expectedAppRevision":snapshot["appRevision"],
                "expectedRevision":old["revision"] if old else None,
                "baseContentHash":old["contentHash"] if old else None,
                "definition":definition
            }
        template=json.loads(
            (stage/"platform-saltcorn"/"contract-pack.json").read_text())
        try:
            with kerlog.open("w") as out:
                kernel=subprocess.Popen([
                    "sudo","-n","runuser","-u",KERNEL,"--",
                    sys.executable,"-u",
                    str(stage/"g1-b01-b10"/"kernel_service.py"),
                    "--config",str(auth_cfg),"--ready",str(kernel_ready)
                ],cwd=str(stage),stdin=subprocess.DEVNULL,stdout=out,
                  stderr=subprocess.STDOUT)
            for _ in range(140):
                if kernel_ready.is_file():break
                if kernel.poll() is not None:raise RuntimeError(
                    "KERNEL_DIED "+kerlog.read_text(errors="replace")[-900:])
                time.sleep(.08)
            if not kernel_ready.is_file():
                raise RuntimeError("KERNEL_NOT_READY")
            meta=json.loads(kernel_ready.read_text())
            core_base="http://127.0.0.1:"+str(meta["port"])
            check("B10-02-authority-kernel-real-OS-service",
                  meta["uid"]==uids[KERNEL] and
                  wait_page(core_base+"/health",10),
                  {"authorityUid":meta["uid"]})
            init=physical_core()
            check("B10-03-physical-apps-start-empty-and-private",
                  init["app-a"]["revision"]==init["app-b"]["revision"]==0 and
                  run(["sudo","-n","stat","-c","%a",authority]).stdout.strip()=="700",
                  {"appARev":0,"appBRev":0,"privateDirectory":700})
            # The router only gets the read-only runtime-token from kernel.
            # Route config is built by the trusted controller before chown.
            route_cfg.write_text(json.dumps({
                "kernelPort":meta["port"],
                "kernelReadToken":router_read_token,
                "adminToken":route_admin_token
            }))
            route_cfg.chmod(0o600)
            run(["sudo","-n","chown","-R",ROUTER+":"+ROUTER,route_private])
            # ready is owner KERNEL; router needs its own readable subdir
            router_out=home/"router-ready"
            router_out.mkdir(mode=0o755)
            run(["sudo","-n","chown",ROUTER+":"+ROUTER,router_out])
            router_ready=router_out/"ready.json"
            with routelog.open("w") as output:
                routeproc=subprocess.Popen([
                    "sudo","-n","runuser","-u",ROUTER,"--",
                    sys.executable,"-u",str(stage/"g1-b01-b10"/"router.py"),
                    "--config",str(route_cfg),"--ready",str(router_ready)
                ],cwd=str(stage),stdin=subprocess.DEVNULL,stdout=output,
                  stderr=subprocess.STDOUT)
            for _ in range(140):
                if router_ready.is_file():break
                if routeproc.poll() is not None:raise RuntimeError(
                    "ROUTER_DIED "+routelog.read_text(errors="replace")[-900:])
                time.sleep(.08)
            if not router_ready.is_file():raise RuntimeError("ROUTER_NOT_READY")
            routemeta=json.loads(router_ready.read_text())
            route_base="http://127.0.0.1:"+str(routemeta["port"])
            status,h=api_json(route_base+"/_health")
            check("B10-04-router-is-third-least-privileged-real-UID",
                  routemeta["uid"]==uids[ROUTER] and status==200 and
                  h["activeVersion"] is None and h["epoch"]==0,
                  {"routeUid":routemeta["uid"],"initialEpoch":0})
            code,_,body=web_call(route_base+ROUTE)
            check("B10-05-no-active-version-fails-closed",
                  code==503 and b"NO_ACTIVE_VERSION" in body,
                  {"http":503,"noFallback":True})
            # Real source schema + real human session publish v1.
            specs=json.loads(
                (ROOT/"g1-b01-b2"/"contract_spec.json").read_text())
            for i,(rid,spec) in enumerate(specs.items(),1):
                state=required("draft.read",agent_token,{})
                required("metadata.upsert",agent_token,{"command":
                    command(state,rid,spec,"b10-initial-schema-"+str(i))})
            check("B10-06-four-trusted-typed-resources-with-CAS",
                  physical_core()["app-a"]["revision"]==4,
                  {"appRevision":4})
            with sync_playwright() as pw:
                browser=pw.chromium.launch(headless=True,args=["--no-sandbox"])
                context=browser.new_context()
                try:
                    page=context.new_page()
                    page.goto(core_base+"/editor/app-a",
                              wait_until="domcontentloaded")
                    page.locator("#password").fill(pass_kernel)
                    page.locator("#login").click()
                    page.wait_for_url("**/editor/app-a",timeout=14000)
                    wait_text(page,"#revision","4")
                    page.locator("#publish").click()
                    wait_text(page,"#published-version","1")
                    v1=required("release.read",runtime_token,{})
                    check("B10-07-real-human-B2-published-v1-hash-verified",
                          v1["version"]==1 and
                          sha(v1["definitions"])==v1["manifestHash"],
                          {"version":1,"manifestHash":v1["manifestHash"]})
                    # Exercise authority BUSINESS state instead of inferring
                    # business correctness from a native HTML view.
                    sub=required("form.submit",runtime_token,{
                        "formId":"form.contracts",
                        "values":{"contract_no":MARKER,
                                  "title":"B2 authority-only contract",
                                  "amount_minor":200000001}})
                    record=sub["recordId"]
                    transitions=[]
                    for act,rev in (("submit",1),("approve",2),("approve",3)):
                        res=required("workflow.advance",runtime_token,{
                            "workflowId":"workflow.approval",
                            "recordId":record,"action":act,
                            "expectedVersion":rev})
                        transitions.append(res["status"])
                    check("B10-08-real-authoritative-contract-two-level-workflow",
                          transitions==[
                              "PendingLevel1","PendingLevel2","Approved"] and
                          physical_core()["app-a"]["records"][0][
                              "value"]["status"]=="Approved",
                          {"approvalStates":transitions,
                           "businessOwner":"B2 Kernel ONLY"})
                    v1native=native_materialize("v1",v1)
                    check("B10-09-real-native-v1-physical-Oracle-and-test-record",
                          v1native["oracle"]["viewColumns"]==[
                              "contract_no","amount_minor","status"] and
                          v1native["oracle"]["businessRows"][0][
                              "contract_no"]==MARKER and
                          v1native["oracle"]["businessRows"][0][
                              "title"]!="B2 authority-only contract",
                          {"nativeSource":"independent fixture; NOT data sync",
                           "viewColumns":["contract_no",
                                          "amount_minor","status"]})
                    native1=start_native("v1",v1native["db"],3158)
                    check("B10-10-v1-real-Saltcorn-prefetch-business-HTTP-ready",
                          MARKER.encode() in web_call(native1+ROUTE)[2],
                          {"nativeHttp":200,"businessMarker":True})
                    invalid_auth=api_json(
                        route_base+"/_admin/register","POST",{
                            "version":1,"manifestHash":v1["manifestHash"],
                            "port":3158,"marker":MARKER},
                        bearer="bad-token-not-admin")
                    check("B10-11-route-registration-requires-independent-admin",
                          invalid_auth[0]==401,
                          {"http":401,"publicCannotRegister":True})
                    broken=router_register(1,v1,9)
                    check("B10-12-dead-backend-rejected-before-registration",
                          broken[0]==503 and
                          broken[1]["error"]=="BACKEND_READINESS_FAILED" and
                          api_json(route_base+"/_health")[1][
                              "candidateVersions"]==[],
                          {"candidateRejected":True,"activeStillNone":True})
                    forged=router_admin("register",{
                        "version":1,"manifestHash":"f"*64,
                        "port":3158,"marker":MARKER})
                    check("B10-13-false-release-sha-rejected-by-live-kernel",
                          forged[0]==409 and
                          forged[1]["error"]=="NOT_CURRENT_VERIFIED_RELEASE",
                          {"http":409})
                    reg1=router_register(1,v1,3158)
                    check("B10-14-real-live-business-ready-v1-registered",
                          reg1[0]==200 and
                          reg1[1]["businessReadiness"],
                          {"version":1,"checkedLiveNative":True})
                    first=switch("b10-activate-v1",0,None,1,v1)
                    check("B10-15-v1-front-end-route-switched-with-CAS",
                          first[0]==200 and
                          first[1]["epoch"]==1 and
                          first[1]["version"]==1,
                          {"epoch":1,"active":1})
                    code,headers,html=web_call(route_base+ROUTE)
                    check("B10-16-actual-front-end-HTTP-views-native-v1",
                          code==200 and MARKER.encode() in html and
                          headers["X-OpenAILCAP-Release"]=="1",
                          {"frontHttp":200,"routedRelease":1})
                    webview=context.new_page()
                    webview.goto(route_base+ROUTE,wait_until="domcontentloaded")
                    check("B10-17-real-Chromium-renders-through-version-router",
                          MARKER in webview.content(),
                          {"browserHttp":200,"viaRouter":True})
                    post_view=api_json(route_base+ROUTE,"POST",{})
                    blocked_editor=api_json(route_base+"/field/999")
                    check("B10-18-public-router-exposes-GET-only-no-native-editor",
                          post_view[0]==405 and blocked_editor[0]==404,
                          {"post":405,"nativeFieldHttp":404})
                    snapshot=physical_core()
                    check("B10-19-authority-approval-not-overwritten-by-native-view",
                          snapshot["app-a"]["records"][0]["value"][
                              "status"]=="Approved" and
                          snapshot["app-a"]["publishedVersion"]==1,
                          {"businessState":"Approved",
                           "nativeDataNotMistakenForAuthority":True})
                    # A newer B2 publish happens while old runtime still
                    # serves traffic. This is a deployment lag, explicitly.
                    draft=required("draft.read",agent_token,{})
                    v2view=copy.deepcopy(
                        draft["resources"]["view.contracts"]["definition"])
                    v2view["columns"]=[
                        "contract_no","title","amount_minor","status"]
                    required("metadata.upsert",agent_token,{"command":
                        command(draft,"view.contracts",v2view,
                                "b10-add-title-v2")})
                    page.locator("#reload").click()
                    wait_text(page,"#revision","5")
                    page.locator("#publish").click()
                    wait_text(page,"#published-version","2")
                    v2=required("release.read",runtime_token,{})
                    check("B10-20-B2-human-publishes-v2-while-v1-serves",
                          v2["version"]==2 and
                          v2["manifestHash"]!=v1["manifestHash"] and
                          api_json(route_base+"/_health")[1][
                              "activeVersion"]==1,
                          {"kernelRelease":2,"stillServing":1,
                           "explicitDeploymentLag":True})
                    native2obj=native_materialize("v2",v2)
                    native2=start_native("v2",native2obj["db"],3159)
                    check("B10-21-two-independent-actual-Saltcorn-servers-live",
                          MARKER.encode() in web_call(native1+ROUTE)[2] and
                          MARKER.encode() in web_call(native2+ROUTE)[2] and
                          v2native_columns(native2obj)==[
                              "contract_no","title","amount_minor","status"],
                          {"nativeV1Port":3158,"nativeV2Port":3159,
                           "v1Cols":3,"v2Cols":4})
                    still=web_call(route_base+ROUTE)
                    check("B10-22-before-commit-all-client-traffic-remains-v1",
                          still[0]==200 and
                          still[1]["X-OpenAILCAP-Release"]=="1",
                          {"clientRelease":1,"kernelRelease":2})
                    bad_marker=router_admin("register",{
                        "version":2,"manifestHash":v2["manifestHash"],
                        "port":3159,"marker":"HT-2026-DOES-NOT-EXIST"})
                    check("B10-23-business-readiness-marker-failure-rejected",
                          bad_marker[0]==503 and
                          bad_marker[1]["error"]==(
                              "BACKEND_BUSINESS_READINESS_FAILED"),
                          {"http":503,"activeStillV1":True})
                    reg2=router_register(2,v2,3159)
                    check("B10-24-prewarmed-v2-registered-without-routing",
                          reg2[0]==200 and
                          api_json(route_base+"/_health")[1][
                              "activeVersion"]==1,
                          {"candidateV2Ready":True,"clientRelease":1})
                    # A deliberately pinned, real GET begins before commit.
                    caught={}
                    def old_request():
                        caught["value"]=web_call(
                            route_base+ROUTE,headers={
                                "X-B10-Test-Hold-Ms":"1600"},timeout=9)
                    worker=threading.Thread(target=old_request)
                    worker.start()
                    for _ in range(100):
                        if api_json(route_base+"/_health")[1]["inflight"]>=1:
                            break
                        time.sleep(.015)
                    else:raise AssertionError("IN_FLIGHT_NEVER_CAPTURED")
                    check("B10-25-observed-an-inflight-v1-request-before-cutover",
                          worker.is_alive() and
                          api_json(route_base+"/_health")[1]["inflight"]>=1,
                          {"inflight":1,"testOnlyHoldMs":1600})
                    changed=switch("b10-cutover-v1-v2",1,1,2,v2)
                    check("B10-26-atomic-pointer-cutover-after-B2-verified-publish",
                          changed[0]==200 and
                          changed[1]["version"]==2 and
                          changed[1]["epoch"]==2,
                          {"epoch":2,"from":1,"to":2})
                    code2,h2,page2=web_call(route_base+ROUTE)
                    check("B10-27-postcutover-new-real-HTTP-requests-go-to-v2",
                          code2==200 and MARKER.encode() in page2 and
                          h2["X-OpenAILCAP-Release"]=="2",
                          {"newRequestVersion":2})
                    worker.join(timeout=8)
                    prior=caught.get("value")
                    check("B10-28-inflight-v1-request-pinned-through-v2-switch",
                          prior is not None and
                          prior[0]==200 and
                          prior[1]["X-OpenAILCAP-Release"]=="1" and
                          prior[1]["X-OpenAILCAP-Route-Epoch"]=="1" and
                          h2["X-OpenAILCAP-Route-Epoch"]=="2",
                          {"oldRequestVersion":1,"newRequestVersion":2,
                           "noCrossRequestMixing":True})
                    repeated=switch("b10-cutover-v1-v2",1,1,2,v2)
                    check("B10-29-unknown-result-same-changeId-replays-once",
                          repeated[0]==200 and
                          repeated[1]["replayed"] and
                          api_json(route_base+"/_health")[1]["epoch"]==2,
                          {"replayed":True,"noDoubleSwitch":True,
                           "persistedAcrossRestart":False})
                    stale=switch("b10-stale-cutover",1,1,2,v2)
                    check("B10-30-stale-route-pointer-denied-409",
                          stale[0]==409 and
                          stale[1]["error"]=="ROUTE_EPOCH_CONFLICT",
                          {"http":409,"routeEpoch":2})
                    bad_replay=router_admin("switch",{
                        "changeId":"b10-cutover-v1-v2","expectedEpoch":1,
                        "expectedFromVersion":1,"targetVersion":2,
                        "manifestHash":"0"*64})
                    check("B10-31-reused-changeId-different-body-denied",
                          bad_replay[0]==409 and
                          bad_replay[1]["error"]=="CHANGE_ID_REUSED",
                          {"http":409,"noMutation":True})
                    v2browser=context.new_page()
                    v2browser.goto(route_base+ROUTE,
                                   wait_until="domcontentloaded")
                    check("B10-32-actual-Chromium-after-cutover-serves-v2",
                          MARKER in v2browser.content(),
                          {"browserHttp":200,
                           "routeVersion":api_json(
                               route_base+"/_health")[1]["activeVersion"]})
                    # Native v2 crash: fail closed; DO NOT route to old v1.
                    proc=native_processes["v2"]
                    os.killpg(proc.pid,signal.SIGTERM)
                    proc.wait(timeout=12)
                    check("B10-33-real-v2-native-process-exited-after-fault",
                          proc.poll() is not None,
                          {"nativeV2Terminated":True})
                    code_down,h_down,resp_down=web_call(route_base+ROUTE)
                    check("B10-34-unhealthy-active-backend-returns-503-no-fallback",
                          code_down==503 and
                          b"BACKEND_READINESS_FAILED" in resp_down and
                          api_json(route_base+"/_health")[1][
                              "activeVersion"]==2,
                          {"frontHttp":503,"active":2,
                           "silentFallbackDisabled":True})
                    # Business data unaffected by external Saltcorn outage.
                    state_during=physical_core()
                    check("B10-35-authority-contract-approved-during-native-outage",
                          state_during["app-a"]["records"][0]["value"][
                              "status"]=="Approved" and
                          state_during["app-a"]["publishedVersion"]==2,
                          {"authorityWorkflow":"Approved",
                           "nativeOutageNotATransactionRollback":True})
                    # Rollback before kernel pointer change should be refused.
                    wrong=switch("b10-pre-rollback",2,2,1,v1)
                    check("B10-36-runtime-rollback-requires-source-Kernel-pointer",
                          wrong[0]==409 and
                          wrong[1]["error"]==(
                              "KERNEL_PUBLISH_POINTER_MISMATCH"),
                          {"http":409,"stillEpoch":2})
                    rb=required("app.rollback",publisher_token,{"command":{
                        "changeId":"b10-human-rollback-v2-v1",
                        "expectedPublishedVersion":2,
                        "targetVersion":1}})
                    check("B10-37-trusted-B2-CAS-reverts-published-pointer-only",
                          rb["version"]==1 and
                          physical_core()["app-a"]["publishedVersion"]==1,
                          {"authoritativeVersion":1,"draftRevision":5})
                    restored=switch("b10-restore-live-v1",2,2,1,v1)
                    check("B10-38-verified-runtime-rollback-pointer-restores-v1",
                          restored[0]==200 and
                          restored[1]["version"]==1 and
                          restored[1]["epoch"]==3,
                          {"epoch":3,"active":1})
                    code3,h3,content3=web_call(route_base+ROUTE)
                    check("B10-39-public-HTTP-recovers-using-still-live-v1",
                          code3==200 and
                          MARKER.encode() in content3 and
                          h3["X-OpenAILCAP-Release"]=="1",
                          {"http":200,"activeRelease":1})
                    rollback_page=context.new_page()
                    rollback_page.goto(route_base+ROUTE,
                                       wait_until="domcontentloaded")
                    check("B10-40-true-Chromium-browser-reads-rolled-back-v1",
                          MARKER in rollback_page.content(),
                          {"browserRendered":True})
                    stale_rb=required("release.read",runtime_token,{})
                    check("B10-41-B2-release-read-reverted-v1-exact-SHA",
                          stale_rb["version"]==1 and
                          stale_rb["manifestHash"]==v1["manifestHash"],
                          {"version":1,"shaRestored":True})
                    full=physical_core()
                    check("B10-42-independent-Oracle-two-releases-record-and-other-app",
                          full["app-a"]["releases"]==2 and
                          full["app-a"]["resourceHashesValid"] and
                          full["app-a"]["releaseHashesValid"] and
                          full["app-a"]["revision"]==5 and
                          full["app-a"]["records"][0]["value"][
                              "status"]=="Approved" and
                          full["app-b"]==init["app-b"],
                          {"releases":2,"latestDraft":5,"published":1,
                           "authorityContractStatus":"Approved",
                           "appBunchanged":True})
                    check("B10-43-genuine-native-v1-v2-database-business-rows-are-fixtures",
                          v1native["oracle"]["businessRows"][0]["title"]==
                          v2native_columns_title(native2obj) and
                          v1native["oracle"]["businessRows"][0]["title"]!=
                          full["app-a"]["records"][0]["value"]["title"],
                          {"nativeFixtureOwnedByRuntime":True,
                           "notSyncedFromAuthoritativeB2":True})
                    check("B10-44-no-false-production-zero-downtime-or-workflow-parity",
                          api_json(route_base+"/_health")[1]["epoch"]==3 and
                          full["app-a"]["records"][0]["value"][
                              "status"]=="Approved",
                          {"rawRouterReadOnly":True,
                           "nativeWorkflowNotProjected":True,
                           "routeJournalVolatile":True,
                           "noFormalG1Pass":True})
                    data["final"]={
                        "v1Manifest":v1["manifestHash"],
                        "v2Manifest":v2["manifestHash"],
                        "routerEpoch":3,
                        "activeVersion":1,
                        "actualNativeV2Crashed":True,
                        "authoritativeWorkflowStatus":"Approved",
                        "businessDataNotMirroredToNative":True,
                        "w17W24FullPass":False
                    }
                finally:
                    context.close()
                    browser.close()
        finally:
            # Distinct local processes; this is disposable test VM, not prod.
            for proc in native_processes.values():
                if proc.poll() is None:
                    try:os.killpg(proc.pid,signal.SIGTERM)
                    except ProcessLookupError:pass
                    try:proc.wait(timeout=8)
                    except subprocess.TimeoutExpired:proc.terminate()
            run(["sudo","-n","pkill","-TERM","-u",SALT],
                ok=False,timeout=8)
            for username in (KERNEL,ROUTER):
                run(["sudo","-n","pkill","-TERM","-u",username],
                    ok=False,timeout=8)
            for proc in (routeproc,kernel):
                if proc:
                    try:proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:proc.terminate()
            run(["sudo","-n","chown","-R",
                 str(os.getuid())+":"+str(os.getgid()),
                 authority,runtime,route_private,ready],
                ok=False,timeout=10)
            data["summary"]={
                "passed":sum(x["status"]=="PASS" for x in data["checks"]),
                "attempted":len(data["checks"]),
                "expected":44,"modelCalls":0,"formalG1Passed":False
            }
            Path(opts.output).write_text(
                json.dumps(data,ensure_ascii=False,indent=2)+"\n")
            print("S1_B10_RESULT "+json.dumps(data["summary"]),flush=True)
    return 0 if len(data["checks"])==44 and all(
        x["status"]=="PASS" for x in data["checks"]) else 1


def v2native_columns(native):
    return native["oracle"]["viewColumns"]


def v2native_columns_title(native):
    return native["oracle"]["businessRows"][0]["title"]


if __name__=="__main__":
    raise SystemExit(main())
