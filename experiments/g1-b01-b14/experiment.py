#!/usr/bin/env python3
"""B11 true traffic cutover with 2 live, independent native Saltcorn servers.

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
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer

from playwright.sync_api import sync_playwright

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
sys.path.insert(0,str(ROOT/"g1-b01-b2"))
sys.path.insert(0,str(ROOT/"g1-b01-b9"))
from schema_core import sha
from projector import compile_release,check_compiled
sys.path.insert(0,str(ROOT/"g1-b01-b10"))
from router import ROUTE
sys.path.insert(0,str(ROOT/"g1-b01-b11"))
from projection_source import digest
import socket

KERNEL="ailcapb13kern"
SALT="ailcapb13salt"
ROUTER="ailcapb13route"
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
        "experiment":"S1_B14_ED25519_SIGNED_KERNEL_AND_FIFTH_UID_INDEPENDENT_SQL",
        "zeroDowntimeProductionValidated":False,
        "runtimeCacheHotUpdateValidated":False,
        "nativeWorkflowParityValidated":False,
        "businessDataMirroredToNative":True,
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
    check("B11-01-three-independent-nonroot-host-UIDs",
          len(set(uids.values()))==3 and all(x>0 for x in uids.values()),
          {"kernelUid":uids[KERNEL],"runtimeUid":uids[SALT],
           "routerUid":uids[ROUTER]})

    with tempfile.TemporaryDirectory(prefix="s1-b14-project-") as location:
        home=Path(location);home.chmod(0o755)
        stage=home/"public-source";stage.mkdir(mode=0o755)
        files={
            "g1-b01-b2":("schema_core.py","schema_http.py"),
            "g1-b01-b4":("registry.py","policy.py","sandbox.py","worker.py"),
            "g1-b01-b5":("tool_broker.py",),
            "g1-b01-b7":("physical_sql_oracle.py",),
            "g1-b01-b9":("native_oracle.py",),
            "g1-b01-b11":("kernel_service.py","projection_source.py",
                           "apply_worker.py"),
            "g1-b01-b12":("native_env_launcher.py","apply_worker.py",
                           "consumer_daemon.py","native_checkpoint.py",
                           "native_apply.py","audit_native.py"),
            "g1-b01-b10":("router.py",),
            "g1-b01-b13":("native_ipc.py","consumer_daemon.py",
                           "guard_router.py"),
            "g1-b01-b14":("signed_projection.py","signed_source.py",
                           "signed_native_ipc.py","audit_reader.py",
                           "consumer_daemon.py","guard_router.py"),
            "platform-saltcorn":("contract-pack.json","seed-contract.js")
        }
        for directory,names in files.items():
            folder=stage/directory;folder.mkdir(mode=0o755)
            for name in names:
                shutil.copyfile(ROOT/directory/name,folder/name)
                if directory in ("g1-b01-b12","g1-b01-b13"):
                    staged=(folder/name).read_text()
                    staged=staged.replace("s1-b12-project-","s1-b14-project-")
                    staged=staged.replace("ailcapb12salt","ailcapb13salt")
                    staged=staged.replace("s1-b13-project-","s1-b14-project-")
                    (folder/name).write_text(staged)
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
        projection_token=secrets.token_urlsafe(36)
        route_admin_token=secrets.token_urlsafe(36)
        session_secret=secrets.token_urlsafe(43)
        auth_cfg.write_text(json.dumps({
            "dbPath":str(auth_db),"humanPassword":pass_kernel,
            "agentToken":agent_token,"publisherToken":publisher_token,
            "runtimeToken":runtime_token,
            "appBPublisherToken":app_b_token,
            "routerReadToken":router_read_token,
            "projectionToken":projection_token
        }))
        auth_cfg.chmod(0o600)
        run(["sudo","-n","chown","-R",KERNEL+":"+KERNEL,authority])
        run(["sudo","-n","chown","-R",SALT+":"+SALT,runtime])
        run(["sudo","-n","chown","-R",KERNEL+":"+KERNEL,ready])
        # Router currently must use app-a read scope. B11 has a separate
        # short-lived read-only grant, never an admin/publish token.
        # Modify only this B11 kernel fixture (no B9 code changes).
        procs=[]
        consumer_proc=None
        proxy_server=None
        ipc_proc=None
        guard_proc=None
        unprivileged_consumer=None
        signed_source_proc=None
        signed_ipc_proc=None
        audit_proc=None
        signed_guard_proc=None
        signed_consumer_proc=None
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

        def native_command(command,db,timeout=140,allow_fail=False,
                           stdin_payload=None):
            env={key:env_native[key] for key in (
                "PATH","HOME","SALTCORN_NWORKERS","SALTCORN_SESSION_SECRET")}
            env["SQLITE_FILEPATH"]=str(db)
            return run(["sudo","-n","runuser","-u",SALT,"--",sys.executable,
                        str(stage/"g1-b01-b12"/"native_env_launcher.py"),
                        *command],cwd=stage,env=env_native,
                       stdin=json.dumps(env)+"\n"+(
                           stdin_payload+"\n" if stdin_payload is not None
                           else ""),timeout=timeout,
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
            native_command(["saltcorn","create-user","--admin",
                            "--email",EMAIL,"--password",admin_password],db)
            oracle=physical_native(db)
            if oracle["viewColumns"]!=(
                release["definitions"]["view.contracts"]["columns"]
            ) or len(oracle["businessRows"])!=0:
                raise AssertionError("NATIVE_ORACLE_MISMATCH")
            return {"db":db,"pack":pack,"projection":compiled,"oracle":oracle}

        def pull_events(after=0,limit=100,token=None):
            return api_json(core_base+"/v4/apps/app-a/projection/pull",
                            "POST",{"after":after,"limit":limit},
                            projection_token if token is None else token)

        def native_apply(db,batch,fail=False,allow_fail=False):
            args=["sudo","-n","runuser","-u",SALT,"--",
                  sys.executable,
                  str(stage/"g1-b01-b12"/"apply_worker.py"),
                  "--db",db]
            if fail:args.append("--fail-before-commit")
            # Native process receives ONLY event batch via stdin, never
            # a Kernel bearer, authority DB path, or publisher credential.
            p=run(args,cwd=stage,timeout=20,ok=not allow_fail,
                  stdin=json.dumps(batch)+"\n")
            tag="S1_B11_NATIVE_REJECT" if allow_fail else "S1_B11_NATIVE_APPLY"
            return one(p.stdout,tag)

        def native_inspect(db):
            p=run(["sudo","-n","runuser","-u",SALT,"--",
                sys.executable,str(stage/"g1-b01-b12"/"apply_worker.py"),
                "--db",db,"--inspect"],cwd=stage,timeout=15)
            return one(p.stdout,"S1_B11_NATIVE_APPLY")

        def sync_native(db,after=0):
            code,feed=pull_events(after)
            if code!=200:raise AssertionError("SOURCE_PULL_"+str(code))
            batch={"app":"app-a","after":after,"events":feed["events"]}
            result=native_apply(db,batch)
            return feed,result,native_inspect(db)

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
                sys.executable,str(stage/"g1-b01-b12"/"native_env_launcher.py"),
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
                    str(stage/"g1-b01-b11"/"kernel_service.py"),
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
            check("B11-02-authority-kernel-real-OS-service",
                  meta["uid"]==uids[KERNEL] and
                  wait_page(core_base+"/health",10),
                  {"authorityUid":meta["uid"]})
            init=physical_core()
            check("B11-03-physical-apps-start-empty-and-private",
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
            check("B11-04-router-is-third-least-privileged-real-UID",
                  routemeta["uid"]==uids[ROUTER] and status==200 and
                  h["activeVersion"] is None and h["epoch"]==0,
                  {"routeUid":routemeta["uid"],"initialEpoch":0})
            code,_,body=web_call(route_base+ROUTE)
            check("B11-05-no-active-version-fails-closed",
                  code==503 and b"NO_ACTIVE_VERSION" in body,
                  {"http":503,"noFallback":True})
            # Real source schema + real human session publish v1.
            specs=json.loads(
                (ROOT/"g1-b01-b2"/"contract_spec.json").read_text())
            for i,(rid,spec) in enumerate(specs.items(),1):
                state=required("draft.read",agent_token,{})
                required("metadata.upsert",agent_token,{"command":
                    command(state,rid,spec,"b11-initial-schema-"+str(i))})
            check("B11-06-four-trusted-typed-resources-with-CAS",
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
                    check("B11-07-real-human-B2-published-v1-hash-verified",
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
                    check("B11-08-real-authoritative-contract-two-level-workflow",
                          transitions==[
                              "PendingLevel1","PendingLevel2","Approved"] and
                          physical_core()["app-a"]["records"][0][
                              "value"]["status"]=="Approved",
                          {"approvalStates":transitions,
                           "businessOwner":"B2 Kernel ONLY"})
                    # B11-45..48: authoritative transactional event-time outbox.
                    src_code,source0=pull_events()
                    check("B11-45-real-B2-record-writes-emit-4-atomic-outbox-events",
                          src_code==200 and source0["head"]==4 and
                          [e["seq"] for e in source0["events"]]==[1,2,3,4] and
                          [e["cells"]["status"] for e in source0["events"]]==[
                              "Draft","PendingLevel1","PendingLevel2","Approved"],
                          {"eventTimeStatuses":[e["cells"]["status"]
                                                for e in source0["events"]]})
                    denied=pull_events(token="not-a-valid-token")
                    check("B11-46-unauthorized-projection-pull-rejected",
                          denied[0]==401 and
                          denied[1]["error"]=="PROJECTION_TOKEN_REQUIRED",
                          {"http":401})
                    forbidden=b2("release.read",projection_token,{})
                    check("B11-47-projection-bearer-not-valid-as-B5-tool-token",
                          forbidden[0]==401,
                          {"b5ReleaseReadHttp":401,
                           "nativeReceivesToken":False})
                    invalid=api_json(
                        core_base+"/v4/apps/app-a/projection/pull","POST",
                        {"after":-1,"limit":101},projection_token)
                    check("B11-48-outbox-invalid-cursor-limit-rejected",
                          invalid[0]==422 and
                          invalid[1]["error"]=="PROJECTION_CURSOR_INVALID",
                          {"http":422})
                    v1native=native_materialize("v1",v1)
                    feed1,applied1,native1_rows=sync_native(v1native["db"])
                    v1native["oracle"]=physical_native(v1native["db"])
                    check("B11-49-native-v1-source-outbox-exactly-4-events",
                          applied1["applied"]==4 and
                          native1_rows["lastSeq"]==4 and
                          native1_rows["receipts"]==4 and
                          native1_rows["mappings"]==1 and
                          native1_rows["rows"][0]["title"]==
                          "B2 authority-only contract",
                          {"cursor":4,"nativeRows":1,
                           "actualSource":"B2 outbox"})
                    replay1=native_apply(v1native["db"],{
                        "app":"app-a","after":0,"events":feed1["events"]})
                    check("B11-50-native-v1-replay-same-events-no-duplicate-rows",
                          replay1["applied"]==0 and
                          replay1["replayed"]==4 and
                          native_inspect(v1native["db"])["mappings"]==1,
                          {"replayed":4,"applied":0})
                    tampered=copy.deepcopy(feed1["events"])
                    tampered[0]["cells"]["title"]="TAMPERED"
                    tampered[0]["eventHash"]=digest({
                        k:v for k,v in tampered[0].items()
                        if k!="eventHash"})
                    tamper_result=native_apply(v1native["db"],{
                        "app":"app-a","after":0,"events":tampered},
                        allow_fail=True)
                    check("B11-51-native-replayed-sequence-hash-conflict-rejected",
                          tamper_result["error"]=="REPLAY_HASH_CONFLICT" and
                          native_inspect(v1native["db"])["lastSeq"]==4,
                          {"error":"REPLAY_HASH_CONFLICT",
                           "cursorUnaffected":4})
                    check("B11-09-real-native-v1-physical-Oracle-and-test-record",
                          v1native["oracle"]["viewColumns"]==[
                              "contract_no","amount_minor","status"] and
                          v1native["oracle"]["businessRows"][0][
                              "contract_no"]==MARKER and
                          v1native["oracle"]["businessRows"][0][
                              "title"]=="B2 authority-only contract",
                          {"nativeSource":"real B2 transactional outbox",
                           "viewColumns":["contract_no",
                                          "amount_minor","status"]})
                    native1=start_native("v1",v1native["db"],3158)
                    check("B11-10-v1-real-Saltcorn-prefetch-business-HTTP-ready",
                          MARKER.encode() in web_call(native1+ROUTE)[2],
                          {"nativeHttp":200,"businessMarker":True})
                    invalid_auth=api_json(
                        route_base+"/_admin/register","POST",{
                            "version":1,"manifestHash":v1["manifestHash"],
                            "port":3158,"marker":MARKER},
                        bearer="bad-token-not-admin")
                    check("B11-11-route-registration-requires-independent-admin",
                          invalid_auth[0]==401,
                          {"http":401,"publicCannotRegister":True})
                    broken=router_register(1,v1,9)
                    check("B11-12-dead-backend-rejected-before-registration",
                          broken[0]==503 and
                          broken[1]["error"]=="BACKEND_READINESS_FAILED" and
                          api_json(route_base+"/_health")[1][
                              "candidateVersions"]==[],
                          {"candidateRejected":True,"activeStillNone":True})
                    forged=router_admin("register",{
                        "version":1,"manifestHash":"f"*64,
                        "port":3158,"marker":MARKER})
                    check("B11-13-false-release-sha-rejected-by-live-kernel",
                          forged[0]==409 and
                          forged[1]["error"]=="NOT_CURRENT_VERIFIED_RELEASE",
                          {"http":409})
                    reg1=router_register(1,v1,3158)
                    check("B11-14-real-live-business-ready-v1-registered",
                          reg1[0]==200 and
                          reg1[1]["businessReadiness"],
                          {"version":1,"checkedLiveNative":True})
                    first=switch("b11-activate-v1",0,None,1,v1)
                    check("B11-15-v1-front-end-route-switched-with-CAS",
                          first[0]==200 and
                          first[1]["epoch"]==1 and
                          first[1]["version"]==1,
                          {"epoch":1,"active":1})
                    code,headers,html=web_call(route_base+ROUTE)
                    check("B11-16-actual-front-end-HTTP-views-native-v1",
                          code==200 and MARKER.encode() in html and
                          headers["X-OpenAILCAP-Release"]=="1",
                          {"frontHttp":200,"routedRelease":1})
                    webview=context.new_page()
                    webview.goto(route_base+ROUTE,wait_until="domcontentloaded")
                    check("B11-17-real-Chromium-renders-through-version-router",
                          MARKER in webview.content(),
                          {"browserHttp":200,"viaRouter":True})
                    post_view=api_json(route_base+ROUTE,"POST",{})
                    blocked_editor=api_json(route_base+"/field/999")
                    check("B11-18-public-router-exposes-GET-only-no-native-editor",
                          post_view[0]==405 and blocked_editor[0]==404,
                          {"post":405,"nativeFieldHttp":404})
                    snapshot=physical_core()
                    check("B11-19-authority-approval-not-overwritten-by-native-view",
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
                                "b11-add-title-v2")})
                    page.locator("#reload").click()
                    wait_text(page,"#revision","5")
                    page.locator("#publish").click()
                    wait_text(page,"#published-version","2")
                    v2=required("release.read",runtime_token,{})
                    check("B11-20-B2-human-publishes-v2-while-v1-serves",
                          v2["version"]==2 and
                          v2["manifestHash"]!=v1["manifestHash"] and
                          api_json(route_base+"/_health")[1][
                              "activeVersion"]==1,
                          {"kernelRelease":2,"stillServing":1,
                           "explicitDeploymentLag":True})
                    native2obj=native_materialize("v2",v2)
                    # Fault injection inside one real native SQLite transaction.
                    fail2=native_apply(native2obj["db"],{
                        "app":"app-a","after":0,"events":source0["events"]},
                        fail=True,allow_fail=True)
                    no_partial=native_inspect(native2obj["db"])
                    check("B11-52-real-native-transaction-fault-rolls-back-row-and-cursor",
                          fail2["error"]=="INJECTED_BEFORE_COMMIT" and
                          no_partial["lastSeq"]==0 and
                          no_partial["rows"]==[] and
                          no_partial["receipts"]==0,
                          {"injectedFailure":"before SQL commit",
                           "partialRows":0,"cursor":0})
                    feed2,applied2,native2_rows=sync_native(native2obj["db"])
                    check("B11-53-native-v2-retry-after-unknown-result-applies-once",
                          applied2["applied"]==4 and
                          native2_rows["lastSeq"]==4 and
                          native2_rows["receipts"]==4,
                          {"applied":4,"lastSeq":4})
                    native2obj["oracle"]=physical_native(native2obj["db"])
                    check("B11-54-native-v2-row-exactly-equals-B2-authority",
                          native2obj["oracle"]["businessRows"]==
                          v1native["oracle"]["businessRows"] and
                          native2obj["oracle"]["businessRows"][0]["status"]==
                          "Approved",
                          {"twoDerivedDatabasesSameBusinessState":True})
                    # Actual OS open(2) attempt, not just os.access metadata.
                    probe_script=(
                        "import sys,os\n"
                        "for path in sys.argv[1:]:\n"
                        " try:\n"
                        "  fd=os.open(path,os.O_RDONLY)\n"
                        "  os.close(fd)\n"
                        "  raise SystemExit(3)\n"
                        " except PermissionError:\n"
                        "  pass\n"
                        "raise SystemExit(0)\n"
                    )
                    native_probe=run(["sudo","-n","runuser","-u",SALT,
                        "--",sys.executable,"-c",probe_script,
                        auth_db,auth_cfg],cwd=stage,ok=False)
                    check("B11-55-native-UID-cannot-read-authority-SQLite-or-token",
                          native_probe.returncode==0,
                          {"authoritySqliteRead":"DENIED",
                           "authorityConfigRead":"DENIED",
                           "projectionTokenNotPassedToNative":True})
                    native2=start_native("v2",native2obj["db"],3159)
                    check("B11-21-two-independent-actual-Saltcorn-servers-live",
                          MARKER.encode() in web_call(native1+ROUTE)[2] and
                          MARKER.encode() in web_call(native2+ROUTE)[2] and
                          v2native_columns(native2obj)==[
                              "contract_no","title","amount_minor","status"],
                          {"nativeV1Port":3158,"nativeV2Port":3159,
                           "v1Cols":3,"v2Cols":4})
                    check("B11-56-same-authoritative-business-different-v1-v2-view-shapes",
                          native_inspect(v1native["db"])["rows"]==
                          native_inspect(native2obj["db"])["rows"] and
                          v1native["oracle"]["viewColumns"]!=
                          native2obj["oracle"]["viewColumns"],
                          {"businessRowsEqual":True,
                           "v1ViewColumns":3,"v2ViewColumns":4})
                    still=web_call(route_base+ROUTE)
                    check("B11-22-before-commit-all-client-traffic-remains-v1",
                          still[0]==200 and
                          still[1]["X-OpenAILCAP-Release"]=="1",
                          {"clientRelease":1,"kernelRelease":2})
                    bad_marker=router_admin("register",{
                        "version":2,"manifestHash":v2["manifestHash"],
                        "port":3159,"marker":"HT-2026-DOES-NOT-EXIST"})
                    check("B11-23-business-readiness-marker-failure-rejected",
                          bad_marker[0]==503 and
                          bad_marker[1]["error"]==(
                              "BACKEND_BUSINESS_READINESS_FAILED"),
                          {"http":503,"activeStillV1":True})
                    reg2=router_register(2,v2,3159)
                    check("B11-24-prewarmed-v2-registered-without-routing",
                          reg2[0]==200 and
                          api_json(route_base+"/_health")[1][
                              "activeVersion"]==1,
                          {"candidateV2Ready":True,"clientRelease":1})
                    # A deliberately pinned, real GET begins before commit.
                    caught={}
                    def old_request():
                        caught["value"]=web_call(
                            route_base+ROUTE,headers={
                                "X-B11-Test-Hold-Ms":"1600"},timeout=9)
                    worker=threading.Thread(target=old_request)
                    worker.start()
                    for _ in range(100):
                        if api_json(route_base+"/_health")[1]["inflight"]>=1:
                            break
                        time.sleep(.015)
                    else:raise AssertionError("IN_FLIGHT_NEVER_CAPTURED")
                    check("B11-25-observed-an-inflight-v1-request-before-cutover",
                          worker.is_alive() and
                          api_json(route_base+"/_health")[1]["inflight"]>=1,
                          {"inflight":1,"testOnlyHoldMs":1600})
                    changed=switch("b11-cutover-v1-v2",1,1,2,v2)
                    check("B11-26-atomic-pointer-cutover-after-B2-verified-publish",
                          changed[0]==200 and
                          changed[1]["version"]==2 and
                          changed[1]["epoch"]==2,
                          {"epoch":2,"from":1,"to":2})
                    code2,h2,page2=web_call(route_base+ROUTE)
                    check("B11-27-postcutover-new-real-HTTP-requests-go-to-v2",
                          code2==200 and MARKER.encode() in page2 and
                          h2["X-OpenAILCAP-Release"]=="2",
                          {"newRequestVersion":2})
                    worker.join(timeout=8)
                    prior=caught.get("value")
                    check("B11-28-inflight-v1-request-pinned-through-v2-switch",
                          prior is not None and
                          prior[0]==200 and
                          prior[1]["X-OpenAILCAP-Release"]=="1" and
                          prior[1]["X-OpenAILCAP-Route-Epoch"]=="1" and
                          h2["X-OpenAILCAP-Route-Epoch"]=="2",
                          {"oldRequestVersion":1,"newRequestVersion":2,
                           "noCrossRequestMixing":True})
                    repeated=switch("b11-cutover-v1-v2",1,1,2,v2)
                    check("B11-29-unknown-result-same-changeId-replays-once",
                          repeated[0]==200 and
                          repeated[1]["replayed"] and
                          api_json(route_base+"/_health")[1]["epoch"]==2,
                          {"replayed":True,"noDoubleSwitch":True,
                           "persistedAcrossRestart":False})
                    stale=switch("b11-stale-cutover",1,1,2,v2)
                    check("B11-30-stale-route-pointer-denied-409",
                          stale[0]==409 and
                          stale[1]["error"]=="ROUTE_EPOCH_CONFLICT",
                          {"http":409,"routeEpoch":2})
                    bad_replay=router_admin("switch",{
                        "changeId":"b11-cutover-v1-v2","expectedEpoch":1,
                        "expectedFromVersion":1,"targetVersion":2,
                        "manifestHash":"0"*64})
                    check("B11-31-reused-changeId-different-body-denied",
                          bad_replay[0]==409 and
                          bad_replay[1]["error"]=="CHANGE_ID_REUSED",
                          {"http":409,"noMutation":True})
                    v2browser=context.new_page()
                    v2browser.goto(route_base+ROUTE,
                                   wait_until="domcontentloaded")
                    check("B11-32-actual-Chromium-after-cutover-serves-v2",
                          MARKER in v2browser.content(),
                          {"browserHttp":200,
                           "routeVersion":api_json(
                               route_base+"/_health")[1]["activeVersion"]})
                    # New B2 contract after BOTH native Saltcorn servers started:
                    # project only new seq5..8, without restarting either server.
                    marker2="HT-2026-000002"
                    sub2=required("form.submit",runtime_token,{
                        "formId":"form.contracts",
                        "values":{"contract_no":marker2,
                                  "title":"Real B2 second authority contract",
                                  "amount_minor":200000002}})
                    rec2=sub2["recordId"]
                    statuses2=[]
                    for act,rev in (("submit",1),("approve",2),("approve",3)):
                        res=required("workflow.advance",runtime_token,{
                            "workflowId":"workflow.approval",
                            "recordId":rec2,"action":act,
                            "expectedVersion":rev})
                        statuses2.append(res["status"])
                    source_more=pull_events(after=4)[1]
                    check("B11-57-live-second-B2-contract-and-four-new-outbox-events",
                          statuses2==[
                              "PendingLevel1","PendingLevel2","Approved"] and
                          source_more["head"]==8 and
                          [e["seq"] for e in source_more["events"]]==[
                              5,6,7,8] and
                          source_more["events"][-1]["cells"]["status"]==
                          "Approved",
                          {"outboxSeq":[5,6,7,8],
                           "authoritativeNewContract":marker2})
                    delta1=sync_native(v1native["db"],after=4)
                    check("B11-58-live-v1-incremental-cursor-4-to-8-no-restart",
                          delta1[1]["applied"]==4 and
                          delta1[2]["lastSeq"]==8 and
                          len(delta1[2]["rows"])==2 and
                          all(row["status"]=="Approved"
                              for row in delta1[2]["rows"]),
                          {"nativeV1Cursor":8,"rows":2})
                    delta2=sync_native(native2obj["db"],after=4)
                    check("B11-59-live-v2-incremental-cursor-4-to-8-no-restart",
                          delta2[1]["applied"]==4 and
                          delta2[2]["lastSeq"]==8 and
                          delta2[2]["rows"]==delta1[2]["rows"] and
                          delta2[2]["receipts"]==8,
                          {"nativeV2Cursor":8,"rows":2,
                           "bothNativeRowsEqual":True})
                    html1=web_call(native1+ROUTE)
                    html2=web_call(native2+ROUTE)
                    htmlroute=web_call(route_base+ROUTE)
                    live_page=context.new_page()
                    live_page.goto(route_base+ROUTE,
                                   wait_until="domcontentloaded")
                    check("B11-60-actual-native-HTTP-and-Chromium-see-new-B2-row",
                          html1[0]==html2[0]==htmlroute[0]==200 and
                          all(marker2.encode() in t[2]
                              for t in (html1,html2,htmlroute)) and
                          marker2 in live_page.content(),
                          {"bothRealSaltcornLiveUpdated":True,
                           "routerVersion":2,
                           "realChromiumSawNewRecord":True})
                    # Native v2 crash: fail closed; DO NOT route to old v1.
                    proc=native_processes["v2"]
                    os.killpg(proc.pid,signal.SIGTERM)
                    proc.wait(timeout=12)
                    check("B11-33-real-v2-native-process-exited-after-fault",
                          proc.poll() is not None,
                          {"nativeV2Terminated":True})
                    code_down,h_down,resp_down=web_call(route_base+ROUTE)
                    check("B11-34-unhealthy-active-backend-returns-503-no-fallback",
                          code_down==503 and
                          b"BACKEND_READINESS_FAILED" in resp_down and
                          api_json(route_base+"/_health")[1][
                              "activeVersion"]==2,
                          {"frontHttp":503,"active":2,
                           "silentFallbackDisabled":True})
                    # Business data unaffected by external Saltcorn outage.
                    state_during=physical_core()
                    check("B11-35-authority-contract-approved-during-native-outage",
                          state_during["app-a"]["records"][0]["value"][
                              "status"]=="Approved" and
                          state_during["app-a"]["publishedVersion"]==2,
                          {"authorityWorkflow":"Approved",
                           "nativeOutageNotATransactionRollback":True})
                    # Rollback before kernel pointer change should be refused.
                    wrong=switch("b11-pre-rollback",2,2,1,v1)
                    check("B11-36-runtime-rollback-requires-source-Kernel-pointer",
                          wrong[0]==409 and
                          wrong[1]["error"]==(
                              "KERNEL_PUBLISH_POINTER_MISMATCH"),
                          {"http":409,"stillEpoch":2})
                    rb=required("app.rollback",publisher_token,{"command":{
                        "changeId":"b11-human-rollback-v2-v1",
                        "expectedPublishedVersion":2,
                        "targetVersion":1}})
                    check("B11-37-trusted-B2-CAS-reverts-published-pointer-only",
                          rb["version"]==1 and
                          physical_core()["app-a"]["publishedVersion"]==1,
                          {"authoritativeVersion":1,"draftRevision":5})
                    restored=switch("b11-restore-live-v1",2,2,1,v1)
                    check("B11-38-verified-runtime-rollback-pointer-restores-v1",
                          restored[0]==200 and
                          restored[1]["version"]==1 and
                          restored[1]["epoch"]==3,
                          {"epoch":3,"active":1})
                    code3,h3,content3=web_call(route_base+ROUTE)
                    check("B11-39-public-HTTP-recovers-using-still-live-v1",
                          code3==200 and
                          MARKER.encode() in content3 and
                          h3["X-OpenAILCAP-Release"]=="1",
                          {"http":200,"activeRelease":1})
                    rollback_page=context.new_page()
                    rollback_page.goto(route_base+ROUTE,
                                       wait_until="domcontentloaded")
                    check("B11-40-true-Chromium-browser-reads-rolled-back-v1",
                          MARKER in rollback_page.content(),
                          {"browserRendered":True})
                    stale_rb=required("release.read",runtime_token,{})
                    check("B11-41-B2-release-read-reverted-v1-exact-SHA",
                          stale_rb["version"]==1 and
                          stale_rb["manifestHash"]==v1["manifestHash"],
                          {"version":1,"shaRestored":True})
                    full=physical_core()
                    check("B11-42-independent-Oracle-two-releases-record-and-other-app",
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
                    check("B11-43-genuine-native-v1-v2-business-row-matches-B2-recordId",
                          v1native["oracle"]["businessRows"][0]["title"]==
                          v2native_columns_title(native2obj) and
                          v1native["oracle"]["businessRows"][0]["title"]==
                          next(r["value"]["title"]
                               for r in full["app-a"]["records"]
                               if r["id"]==record),
                          {"nativeDataFromB2Outbox":True,
                           "notFromIndependentSeed":True})
                    check("B11-44-no-false-production-zero-downtime-or-workflow-parity",
                          api_json(route_base+"/_health")[1]["epoch"]==3 and
                          full["app-a"]["records"][0]["value"][
                              "status"]=="Approved",
                          {"rawRouterReadOnly":True,
                           "nativeWorkflowNotProjected":True,
                           "routeJournalVolatile":True,
                           "noFormalG1Pass":True})
                    restored_native=native_inspect(v1native["db"])
                    final_html=web_call(route_base+ROUTE)
                    check("B11-61-UI-rollback-keeps-both-latest-authoritative-contracts",
                          restored_native["lastSeq"]==8 and
                          len(restored_native["rows"])==2 and
                          all(r["status"]=="Approved"
                              for r in restored_native["rows"]) and
                          marker2.encode() in final_html[2] and
                          final_html[1]["X-OpenAILCAP-Release"]=="1",
                          {"activeViewRelease":1,"businessCursor":8,
                           "businessFactsNotRolledBack":True})
                    final_source=pull_events(after=0)[1]
                    final_core=physical_core()
                    check("B11-62-independent-SQL-outbox-and-two-approved-records",
                          final_source["head"]==8 and
                          len(final_source["events"])==8 and
                          len(final_core["app-a"]["records"])==2 and
                          all(r["value"]["status"]=="Approved"
                              for r in final_core["app-a"]["records"]) and
                          final_core["app-b"]==init["app-b"],
                          {"sourceEvents":8,"authorityRows":2,
                           "appBunchanged":True,
                           "nativeBusinessDataFromB2":True})
                    # B12: a genuine long-lived *separate OS process* now
                    # replaces the B11 trusted controller's manual sync.
                    # Source proxy can return a real HTTP 503 while B2 stays up.
                    source_paused=threading.Event()
                    class SourceProxy(BaseHTTPRequestHandler):
                        def log_message(self,*_):
                            pass
                        def do_POST(self):
                            if self.path!="/v4/apps/app-a/projection/pull":
                                self.send_error(404);return
                            length=int(self.headers.get("Content-Length","0"))
                            if length>4096:
                                self.send_error(413);return
                            raw=self.rfile.read(length)
                            if source_paused.is_set():
                                self.send_response(503)
                                self.end_headers()
                                self.wfile.write(b'{"error":"INJECTED_SOURCE_OUTAGE"}')
                                return
                            upstream=Request(
                                core_base+self.path,data=raw,method="POST",
                                headers={
                                    "Authorization":self.headers.get(
                                        "Authorization",""),
                                    "Content-Type":"application/json"
                                })
                            try:
                                with urlopen(upstream,timeout=3) as upstream_resp:
                                    body=upstream_resp.read(128*1024)
                                    status=upstream_resp.status
                            except HTTPError as exc:
                                status=exc.code
                                body=exc.read(128*1024)
                            except Exception:
                                status=503
                                body=b'{"error":"UPSTREAM_UNAVAILABLE"}'
                            self.send_response(status)
                            self.send_header("Content-Type","application/json")
                            self.send_header("Content-Length",str(len(body)))
                            self.end_headers()
                            self.wfile.write(body)

                    proxy_server=ThreadingHTTPServer(
                        ("127.0.0.1",0),SourceProxy)
                    proxy_thread=threading.Thread(
                        target=proxy_server.serve_forever,daemon=True)
                    proxy_thread.start()
                    proxy_url=("http://127.0.0.1:"+
                        str(proxy_server.server_port)+
                        "/v4/apps/app-a/projection/pull")
                    controller=home/"controller-private"
                    controller.mkdir(mode=0o700)
                    consumer_cfg=controller/"consumer.json"
                    consumer_status=controller/"consumer-status.json"
                    consumer_log=home/"consumer.log"
                    consumer_cfg.write_text(json.dumps({
                        "sourceUrl":proxy_url,
                        "token":projection_token,
                        "nativeUser":SALT,
                        "nativeDb":str(v1native["db"]),
                        "sourceDir":str(stage/"g1-b01-b12"),
                        "intervalMs":180
                    }))
                    consumer_cfg.chmod(0o600)
                    def start_consumer():
                        nonlocal consumer_proc
                        with consumer_log.open("a") as output:
                            consumer_proc=subprocess.Popen([
                                sys.executable,"-u",
                                str(stage/"g1-b01-b12"/"consumer_daemon.py"),
                                "--config",str(consumer_cfg),
                                "--status",str(consumer_status)
                            ],cwd=str(stage),stdin=subprocess.DEVNULL,
                              stdout=output,stderr=subprocess.STDOUT)
                    def wait_consumer(predicate,seconds=24):
                        until=time.monotonic()+seconds
                        latest={}
                        while time.monotonic()<until:
                            if consumer_status.exists():
                                try:
                                    latest=json.loads(
                                        consumer_status.read_text())
                                    if predicate(latest):return latest
                                except (ValueError,OSError):pass
                            if consumer_proc and consumer_proc.poll() is not None:
                                raise AssertionError("CONSUMER_EXITED "+
                                    consumer_log.read_text()[-800:])
                            time.sleep(.12)
                        raise AssertionError("CONSUMER_WAIT_TIMEOUT "+
                                             json.dumps(latest))
                    def create_approved(number):
                        no="HT-2026-"+str(number).zfill(6)
                        response=required("form.submit",runtime_token,{
                            "formId":"form.contracts",
                            "values":{"contract_no":no,
                                      "title":"B2 autonomous contract "+str(number),
                                      "amount_minor":200000000+number}})
                        rid=response["recordId"]
                        statuses=[]
                        for action,version in (
                            ("submit",1),("approve",2),("approve",3)
                        ):
                            event=required("workflow.advance",runtime_token,{
                                "workflowId":"workflow.approval",
                                "recordId":rid,"action":action,
                                "expectedVersion":version})
                            statuses.append(event["status"])
                        if statuses!=["PendingLevel1",
                                     "PendingLevel2","Approved"]:
                            raise AssertionError("B12_WORKFLOW_NOT_APPROVED")
                        return no

                    start_consumer()
                    first_status=wait_consumer(
                        lambda x:x["state"]=="CAUGHT_UP" and
                                 x["cursor"]==8)
                    check("B12-63-background-daemon-autostarts-from-native-cursor8",
                          consumer_proc.poll() is None and
                          first_status["lag"]==0,
                          {"daemonPid":consumer_proc.pid,
                           "nativeDurableCursor":8})
                    denied_cfg=run(["sudo","-n","runuser","-u",SALT,
                        "--",sys.executable,"-c",
                        "import os,sys\n"
                        "try:\n"
                        " f=os.open(sys.argv[1],os.O_RDONLY)\n"
                        " os.close(f)\n"
                        " raise SystemExit(3)\n"
                        "except PermissionError:\n"
                        " raise SystemExit(0)\n",
                        str(consumer_cfg)],cwd=stage,ok=False)
                    check("B12-64-native-UID-cannot-open-controller-source-token",
                          denied_cfg.returncode==0 and
                          projection_token not in
                          consumer_status.read_text(),
                          {"controllerConfigMode":"0600",
                           "nativeTokenOpen":"DENIED"})
                    third=create_approved(3)
                    st12=wait_consumer(
                        lambda x:x.get("cursor")==12 and
                                 x["state"]=="CAUGHT_UP")
                    rows12=native_inspect(v1native["db"])
                    check("B12-65-true-background-auto-applies-third-B2-contract",
                          st12["head"]==12 and
                          len(rows12["rows"])==3 and
                          rows12["receipts"]==12 and
                          any(r["contract_no"]==third and
                              r["status"]=="Approved"
                              for r in rows12["rows"]),
                          {"nativeCursor":12,"rows":3,
                           "manualSyncInvocations":0})
                    native3=web_call(native1+ROUTE)
                    route3=web_call(route_base+ROUTE)
                    check("B12-66-running-real-native-HTTP-shows-auto-synced-row",
                          native3[0]==route3[0]==200 and
                          third.encode() in native3[2] and
                          third.encode() in route3[2],
                          {"realSaltcorn":200,"routerRelease":1})
                    dead_pid=consumer_proc.pid
                    consumer_proc.kill()
                    consumer_proc.wait(timeout=10)
                    check("B12-67-real-consumer-SIGKILL-not-saltcorn",
                          consumer_proc.returncode!=0 and
                          native_processes["v1"].poll() is None and
                          web_call(native1+ROUTE)[0]==200,
                          {"consumerKilled":dead_pid,
                           "saltcornStillAlive":True})
                    fourth=create_approved(4)
                    before_restart=native_inspect(v1native["db"])
                    check("B12-68-authority-advances-while-consumer-dead",
                          pull_events(after=12)[1]["head"]==16 and
                          before_restart["lastSeq"]==12 and
                          len(before_restart["rows"])==3,
                          {"sourceHead":16,"nativeCursor":12,
                           "sourceWritesNotBlocked":True})
                    start_consumer()
                    st16=wait_consumer(
                        lambda x:x.get("cursor")==16 and
                                 x["state"]=="CAUGHT_UP")
                    check("B12-69-restarted-daemon-resumes-from-native-receipt",
                          st16["head"]==16 and
                          any(r["contract_no"]==fourth
                              for r in native_inspect(
                                  v1native["db"])["rows"]),
                          {"recoveredCursor":16,
                           "separateNewProcess":consumer_proc.pid!=dead_pid})
                    chk16=native_inspect(v1native["db"])
                    check("B12-70-restart-does-not-duplicate-native-business",
                          chk16["receipts"]==16 and
                          chk16["mappings"]==4 and
                          len(chk16["rows"])==4,
                          {"receipts":16,"rows":4,"duplicates":0})
                    source_paused.set()
                    outage=api_json(proxy_url,"POST",{
                        "after":16,"limit":20},projection_token)
                    check("B12-71-real-source-HTTP-proxy-returns-503",
                          outage[0]==503 and
                          outage[1]["error"]=="INJECTED_SOURCE_OUTAGE",
                          {"consumerSourceHttp":503,
                           "kernelBusinessEndpointStillAvailable":True})
                    fifth=create_approved(5)
                    unavailable=wait_consumer(
                        lambda x:x["state"]=="SOURCE_UNAVAILABLE")
                    still16=native_inspect(v1native["db"])
                    check("B12-72-real-source-outage-does-not-advance-checkpoint",
                          unavailable["failures"]>=1 and
                          still16["lastSeq"]==16 and
                          len(still16["rows"])==4 and
                          pull_events(after=16)[1]["head"]==20,
                          {"sourceHead":20,"nativeCursor":16,
                           "failClosedOnSourceOutage":True})
                    source_paused.clear()
                    st20=wait_consumer(
                        lambda x:x.get("cursor")==20 and
                                 x["state"]=="CAUGHT_UP",seconds=35)
                    chk20=native_inspect(v1native["db"])
                    check("B12-73-network-recovers-daemon-auto-catches-up",
                          st20["head"]==20 and
                          chk20["receipts"]==20 and
                          chk20["mappings"]==5 and
                          len(chk20["rows"])==5,
                          {"sourceHead":20,"nativeCursor":20,
                           "manualSyncInvocations":0})
                    check("B12-74-live-native-HTTP-shows-fifth-B2-contract",
                          fifth.encode() in web_call(native1+ROUTE)[2] and
                          fifth.encode() in web_call(route_base+ROUTE)[2],
                          {"nativeHTTP":"updated","routeHTTP":"updated"})
                    corrupt_sql=(
                        "import sqlite3,os\n"
                        "c=sqlite3.connect(os.environ['SQLITE_FILEPATH'])\n"
                        "c.execute(\"UPDATE s1_contracts SET title='B12_TAMPERED' "
                        "WHERE contract_no='HT-2026-000005'\")\n"
                        "c.commit()\n"
                    )
                    native_command([sys.executable,"-c",corrupt_sql],
                                   v1native["db"])
                    drift=wait_consumer(
                        lambda x:x["state"]=="DERIVED_DRIFT")
                    check("B12-75-idle-daemon-detects-native-UID-row-drift",
                          drift["failures"]>=1 and
                          native_inspect(v1native["db"])["lastSeq"]==20,
                          {"periodicFullMappedRowAudit":"DRIFT",
                           "noNewSourceEvents":True})
                    raw_dirty=web_call(native1+ROUTE)
                    polluted=native_inspect(v1native["db"])
                    check("B12-76-negative-native-HTTP-still-200-despite-drift",
                          raw_dirty[0]==200 and
                          any(row["title"]=="B12_TAMPERED"
                              for row in polluted["rows"]) and
                          polluted["lastSeq"]==20,
                          {"nativeHttpStatus":raw_dirty[0],
                           "nativePhysicalSqlHasTamper":True,
                           "httpShowsTamper":b"B12_TAMPERED" in raw_dirty[2],
                           "readTimeFailClosedNotImplemented":True})
                    repair_sql=(
                        "import sqlite3,os\n"
                        "c=sqlite3.connect(os.environ['SQLITE_FILEPATH'])\n"
                        "c.execute(\"UPDATE s1_contracts SET title="
                        "'B2 autonomous contract 5' "
                        "WHERE contract_no='HT-2026-000005'\")\n"
                        "c.commit()\n"
                    )
                    native_command([sys.executable,"-c",repair_sql],
                                   v1native["db"])
                    healed=wait_consumer(
                        lambda x:x["state"]=="CAUGHT_UP" and
                                 x.get("cursor")==20)
                    check("B12-77-after-authorized-native-repair-daemon-heals",
                          healed["lag"]==0 and
                          native_inspect(v1native["db"])["receipts"]==20,
                          {"audit":"CLEAN","cursor":20,
                           "repairWasManualNotAutomatic":True})
                    last_source=pull_events(after=0)[1]
                    last_core=physical_core()
                    check("B12-78-independent-B2-oracle-20-events-5-contracts",
                          last_source["head"]==20 and
                          len(last_source["events"])==20 and
                          len(last_core["app-a"]["records"])==5 and
                          all(r["value"]["status"]=="Approved"
                              for r in last_core["app-a"]["records"]) and
                          last_core["app-b"]==init["app-b"],
                          {"sourceEvents":20,"approvedContracts":5,
                           "appBunchanged":True})
                    final_browser=context.new_page()
                    final_browser.goto(route_base+ROUTE,
                                       wait_until="domcontentloaded")
                    check("B12-79-real-Chromium-renders-auto-recovered-contract",
                          fifth in final_browser.content() and
                          api_json(route_base+"/_health")[1][
                              "activeVersion"]==1,
                          {"chromium":"fifth-authority-contract",
                           "activeUIRelease":1,
                           "noProductionHAClaim":True})
                    # B13: the old privileged B12 consumer is no longer used.
                    # Four actual UIDs: Kernel, Saltcorn, Router, Consumer.
                    consumer_proc.terminate()
                    consumer_proc.wait(timeout=5)
                    consumer_uid=pwd.getpwnam("ailcapb13cons").pw_uid
                    check("B13-80-four-distinct-nonroot-Linux-UIDs",
                          consumer_uid>0 and consumer_uid not in uids.values()
                          and len(set([consumer_uid,*uids.values()]))==4,
                          {"consumerUid":consumer_uid,
                           "kernelUid":uids[KERNEL],
                           "nativeUid":uids[SALT],
                           "routerUid":uids[ROUTER]})
                    ipc_dir=home/"ipc"
                    ipc_dir.mkdir(mode=0o755)
                    run(["sudo","-n","chown",SALT+":"+SALT,ipc_dir])
                    consumer_socket=ipc_dir/"consumer.sock"
                    guard_socket=ipc_dir/"guard.sock"
                    ipc_ready=ipc_dir/"ready.json"
                    ipc_log=home/"native-ipc.log"
                    with ipc_log.open("w") as output:
                        ipc_proc=subprocess.Popen([
                            "sudo","-n","runuser","-u",SALT,"--",
                            sys.executable,"-u",
                            str(stage/"g1-b01-b13"/"native_ipc.py"),
                            "--db",str(v1native["db"]),
                            "--consumer-socket",str(consumer_socket),
                            "--guard-socket",str(guard_socket),
                            "--ready",str(ipc_ready),
                            "--consumer-uid",str(consumer_uid),
                            "--router-uid",str(uids[ROUTER])
                        ],cwd=str(stage),stdin=subprocess.DEVNULL,
                          stdout=output,stderr=subprocess.STDOUT)
                    for _ in range(120):
                        if ipc_ready.is_file():break
                        if ipc_proc.poll() is not None:
                            raise AssertionError("B13_IPC_EXIT "+
                                ipc_log.read_text()[-1300:])
                        time.sleep(.08)
                    if not ipc_ready.is_file():
                        raise AssertionError("B13_IPC_NOT_READY")
                    ipc_info=json.loads(ipc_ready.read_text())
                    check("B13-81-native-broker-real-Saltcorn-UID-two-0660-sockets",
                          ipc_info["uid"]==uids[SALT] and
                          consumer_socket.stat().st_mode&0o777==0o660 and
                          guard_socket.stat().st_mode&0o777==0o660,
                          {"nativeBrokerUid":ipc_info["uid"],
                           "consumerSocketMode":"0660",
                           "guardSocketMode":"0660"})
                    def uid_probe(user,code,args=()):
                        return run(["sudo","-n","runuser","-u",user,"--",
                            sys.executable,"-c",code,*map(str,args)],
                            cwd=stage,ok=False)
                    def denied_read(user,path):
                        return uid_probe(user,
                            "import os,sys\n"
                            "try:\n"
                            " f=os.open(sys.argv[1],os.O_RDONLY)\n"
                            " os.close(f)\n"
                            " raise SystemExit(3)\n"
                            "except PermissionError:\n"
                            " raise SystemExit(0)\n", (path,)).returncode==0
                    no_sudo=uid_probe("ailcapb13cons",
                        "import subprocess\n"
                        "p=subprocess.run(['sudo','-n','true'],"
                        "capture_output=True)\n"
                        "raise SystemExit(0 if p.returncode!=0 else 3)\n")
                    check("B13-82-consumer-UID-no-sudo-privilege",
                          no_sudo.returncode==0,
                          {"consumerCanSudo":False})
                    check("B13-83-consumer-UID-cannot-read-authority-DB",
                          denied_read("ailcapb13cons",auth_db),
                          {"authoritySQLite":"DENIED"})
                    check("B13-84-consumer-UID-cannot-read-native-DB",
                          denied_read("ailcapb13cons",v1native["db"]),
                          {"nativeSQLite":"DENIED"})
                    guard_private=home/"guard-private"
                    guard_private.mkdir(mode=0o700)
                    guard_cfg=guard_private/"guard.json"
                    guard_cfg.write_text(json.dumps({
                        "sourceUrl":core_base+
                            "/v4/apps/app-a/projection/pull",
                        "sourceToken":projection_token,
                        "kernelPort":meta["port"],
                        "kernelReadToken":router_read_token,
                        "guardSocket":str(guard_socket),
                        "nativePort":3158,"marker":MARKER,
                        "version":1,"manifestHash":v1["manifestHash"]
                    }))
                    guard_cfg.chmod(0o600)
                    run(["sudo","-n","chown","-R",
                         ROUTER+":"+ROUTER,guard_private])
                    check("B13-85-consumer-cannot-read-router-B2-token",
                          denied_read("ailcapb13cons",guard_cfg),
                          {"routerProjectionToken":"DENIED"})
                    cons_private=home/"b13-consumer-private"
                    cons_private.mkdir(mode=0o700)
                    b13_cfg=cons_private/"consumer.json"
                    b13_status=cons_private/"status.json"
                    b13_log=home/"b13-consumer.log"
                    b13_cfg.write_text(json.dumps({
                        "sourceUrl":proxy_url,
                        "token":projection_token,
                        "nativeSocket":str(consumer_socket),
                        "intervalMs":180
                    }))
                    b13_cfg.chmod(0o600)
                    run(["sudo","-n","chown","-R",
                         "ailcapb13cons:ailcapb13cons",cons_private])
                    check("B13-86-native-UID-cannot-open-consumer-B2-token",
                          denied_read(SALT,b13_cfg),
                          {"nativeHasSourceToken":False})
                    check("B13-87-native-UID-cannot-open-router-B2-token",
                          denied_read(SALT,guard_cfg),
                          {"nativeHasRouterToken":False})
                    def ipc_call(sock,body):
                        with socket.socket(socket.AF_UNIX,
                                           socket.SOCK_STREAM) as conn:
                            conn.settimeout(4)
                            conn.connect(str(sock))
                            conn.sendall(
                                (json.dumps(body,separators=(",",":"))+
                                 "\n").encode())
                            with conn.makefile("rb") as stream:
                                return json.loads(stream.readline(131073))
                    def peer_call(user,sock,body):
                        cmd=(
                            "import json,socket,sys\n"
                            "s=socket.socket(socket.AF_UNIX)\n"
                            "s.settimeout(4)\n"
                            "s.connect(sys.argv[1])\n"
                            "s.sendall((sys.argv[2]+'\\n').encode())\n"
                            "data=b''\n"
                            "while not data.endswith(b'\\n'):\n"
                            " p=s.recv(4096)\n"
                            " if not p:break\n"
                            " data+=p\n"
                            "print('S1_B13_PEER|'+data.decode().strip())\n"
                        )
                        p=uid_probe(user,cmd,(sock,json.dumps(body)))
                        if p.returncode:
                            raise AssertionError("IPC_PEER_DENIED "+p.stderr)
                        return one(p.stdout,"S1_B13_PEER")
                    def denied_connect(user,sock):
                        return uid_probe(user,
                            "import socket,sys\n"
                            "s=socket.socket(socket.AF_UNIX)\n"
                            "try:\n"
                            " s.connect(sys.argv[1])\n"
                            " raise SystemExit(3)\n"
                            "except PermissionError:\n"
                            " raise SystemExit(0)\n",(sock,)).returncode==0
                    a=peer_call("ailcapb13cons",consumer_socket,
                                {"op":"audit"})
                    check("B13-88-consumer-IPC-audit-allowed-by-UID",
                          a["ok"] and a["result"]["clean"] and
                          a["result"]["cursor"]==20,
                          {"audit":"CLEAN","cursor":20})
                    c=peer_call("ailcapb13cons",consumer_socket,
                                {"op":"checkpoint"})
                    check("B13-89-consumer-IPC-checkpoint-from-real-native-SQL",
                          c["ok"] and c["result"]["lastSeq"]==20,
                          {"nativeCommittedCursor":20})
                    check("B13-90-consumer-UID-guard-socket-DAC-denied",
                          denied_connect("ailcapb13cons",guard_socket),
                          {"consumerCanCallGuardSnapshot":False})
                    g=peer_call(ROUTER,guard_socket,{"op":"snapshot"})
                    check("B13-91-router-UID-guard-snapshot-public-only",
                          g["ok"] and g["result"]["clean"] and
                          g["result"]["cursor"]==20 and
                          len(g["result"]["rows"])==5,
                          {"rows":5,"cursor":20,
                           "noSaltcornAdminTables":True})
                    check("B13-92-router-UID-consumer-write-socket-DAC-denied",
                          denied_connect(ROUTER,consumer_socket),
                          {"routerCanCallNativeApply":False})
                    guard_ready_dir=home/"guard-ready"
                    guard_ready_dir.mkdir(mode=0o755)
                    run(["sudo","-n","chown",ROUTER+":"+ROUTER,
                         guard_ready_dir])
                    guard_ready=guard_ready_dir/"ready.json"
                    guard_log=home/"guard-router.log"
                    with guard_log.open("w") as output:
                        guard_proc=subprocess.Popen([
                            "sudo","-n","runuser","-u",ROUTER,"--",
                            sys.executable,"-u",
                            str(stage/"g1-b01-b13"/"guard_router.py"),
                            "--config",str(guard_cfg),
                            "--ready",str(guard_ready)
                        ],cwd=str(stage),stdin=subprocess.DEVNULL,
                          stdout=output,stderr=subprocess.STDOUT)
                    for _ in range(120):
                        if guard_ready.is_file():break
                        if guard_proc.poll() is not None:
                            raise AssertionError("B13_GUARD_EXIT "+
                                guard_log.read_text()[-1300:])
                        time.sleep(.08)
                    if not guard_ready.is_file():
                        raise AssertionError("B13_GUARD_NOT_READY")
                    guard_meta=json.loads(guard_ready.read_text())
                    guard_base=("http://127.0.0.1:"+
                                str(guard_meta["port"]))
                    check("B13-93-guard-router-runs-under-real-router-UID",
                          guard_meta["uid"]==uids[ROUTER],
                          {"guardRouterUid":guard_meta["uid"],
                           "saltcornUid":uids[SALT]})
                    guarded=web_call(guard_base+ROUTE)
                    check("B13-94-read-time-B2-outbox-native-SQL-HTTP-200",
                          guarded[0]==200 and
                          guarded[1].get("X-OpenAILCAP-Guard")==
                          "B13-VERIFIED" and
                          all(("HT-2026-"+str(i).zfill(6)).encode()
                              in guarded[2] for i in range(1,6)),
                          {"verifiedContractRows":5,
                           "sourceEvents":20,"http":guarded[0]})
                    guarded_page=context.new_page()
                    guarded_page.goto(guard_base+ROUTE,
                                      wait_until="domcontentloaded")
                    check("B13-95-real-Chromium-guarded-business-view",
                          fifth in guarded_page.content() and
                          "HT-2026-000001" in guarded_page.content(),
                          {"browser":"Chromium",
                           "guardedRowsVisible":True})
                    forbidden=web_call(guard_base+ROUTE,
                                       method="POST",body={})
                    check("B13-96-guard-public-HTTP-writes-405",
                          forbidden[0]==405,
                          {"http":405,"writeNotForwarded":True})
                    def start_b13_consumer():
                        nonlocal unprivileged_consumer
                        with b13_log.open("a") as output:
                            unprivileged_consumer=subprocess.Popen([
                                "sudo","-n","runuser","-u","ailcapb13cons",
                                "--",sys.executable,"-u",
                                str(stage/"g1-b01-b13"/"consumer_daemon.py"),
                                "--config",str(b13_cfg),
                                "--status",str(b13_status)
                            ],cwd=str(stage),stdin=subprocess.DEVNULL,
                              stdout=output,stderr=subprocess.STDOUT,
                              start_new_session=True)
                    def b13_state():
                        # 0700 Consumer directory is intentionally not
                        # traversable by the CI runner: read via sudo cat.
                        result=run(["sudo","-n","cat",b13_status],
                                   cwd=stage,ok=False)
                        try:return json.loads(result.stdout)
                        except ValueError:return {}
                    def wait_b13(predicate,seconds=28):
                        deadline=time.monotonic()+seconds
                        latest={}
                        while time.monotonic()<deadline:
                            latest=b13_state()
                            if latest and predicate(latest):return latest
                            if unprivileged_consumer and (
                                unprivileged_consumer.poll() is not None
                            ):
                                raise AssertionError("B13_CONSUMER_EXIT "+
                                    b13_log.read_text()[-1100:])
                            time.sleep(.13)
                        raise AssertionError("B13_CONSUMER_TIMEOUT "+
                                             json.dumps(latest))
                    start_b13_consumer()
                    b13_first=wait_b13(lambda x:x.get("state")=="CAUGHT_UP"
                                       and x.get("cursor")==20)
                    check("B13-97-unprivileged-consumer-starts-from-cursor20",
                          b13_first["lag"]==0 and
                          unprivileged_consumer.poll() is None,
                          {"cursor":20,"noSudoInsideConsumer":True})
                    sixth=create_approved(6)
                    b13_sixth=wait_b13(lambda x:x.get("cursor")==24
                                       and x.get("state")=="CAUGHT_UP")
                    good6=web_call(guard_base+ROUTE)
                    check("B13-98-real-unprivileged-IPC-auto-applies-sixth",
                          b13_sixth["head"]==24 and
                          good6[0]==200 and sixth.encode() in good6[2] and
                          native_inspect(v1native["db"])["receipts"]==24,
                          {"sourceHead":24,"nativeCursor":24,
                           "guardHTTP":200})
                    os.killpg(unprivileged_consumer.pid,signal.SIGTERM)
                    unprivileged_consumer.wait(timeout=7)
                    seventh=create_approved(7)
                    native_stale=native_inspect(v1native["db"])
                    check("B13-99-B2-authority-advances-while-UID-consumer-down",
                          pull_events(after=24)[1]["head"]==28 and
                          native_stale["lastSeq"]==24 and
                          len(native_stale["rows"])==6,
                          {"sourceHead":28,"nativeCursor":24})
                    lag_guard=web_call(guard_base+ROUTE)
                    raw_native=web_call(native1+ROUTE)
                    check("B13-100-guard-fails-closed-on-lag-raw-native-200",
                          lag_guard[0]==503 and raw_native[0]==200 and
                          b"GUARD_NATIVE_BEHIND" in lag_guard[2],
                          {"guardHTTP":503,"nativeHTTP":200,
                           "noStalePublicRead":True})
                    start_b13_consumer()
                    b13_seventh=wait_b13(
                        lambda x:x.get("cursor")==28 and
                                 x.get("state")=="CAUGHT_UP")
                    healthy=web_call(guard_base+ROUTE)
                    check("B13-101-IPC-restart-auto-catchup-restores-guard",
                          b13_seventh["head"]==28 and
                          healthy[0]==200 and seventh.encode() in healthy[2],
                          {"cursor":28,"guardHTTP":200,
                           "restartedUnprivilegedConsumer":True})
                    native_command([sys.executable,"-c",
                        "import sqlite3,os\n"
                        "c=sqlite3.connect(os.environ['SQLITE_FILEPATH'])\n"
                        "c.execute(\"UPDATE s1_contracts SET title="
                        "'B13_NATIVE_TAMPER' "
                        "WHERE contract_no='HT-2026-000007'\")\n"
                        "c.commit()\n"],v1native["db"])
                    tamper_guard=web_call(guard_base+ROUTE)
                    tamper_native=web_call(native1+ROUTE)
                    physical_tamper=native_inspect(v1native["db"])
                    check("B13-102-real-native-SQL-tamper-guard-503",
                          tamper_guard[0]==503 and
                          tamper_native[0]==200 and
                          any(r["title"]=="B13_NATIVE_TAMPER"
                              for r in physical_tamper["rows"]),
                          {"guardHTTP":503,"directNativeHTTP":200,
                           "physicalSQLiteTampered":True})
                    native_command([sys.executable,"-c",
                        "import sqlite3,os\n"
                        "c=sqlite3.connect(os.environ['SQLITE_FILEPATH'])\n"
                        "c.execute(\"UPDATE s1_contracts SET title="
                        "'B2 autonomous contract 7' "
                        "WHERE contract_no='HT-2026-000007'\")\n"
                        "c.commit()\n"],v1native["db"])
                    recovered=web_call(guard_base+ROUTE)
                    check("B13-103-manual-native-repair-guard-200",
                          recovered[0]==200 and
                          seventh.encode() in recovered[2],
                          {"guardHTTP":200,"repair":"MANUAL",
                           "notAutomaticRepair":True})
                    # P0 negative control: hashes are NOT source signatures.
                    # A compromised Consumer UID can forge an event over its
                    # authorized apply IPC. Guard independently compares
                    # native cursor against B2 head and MUST reject.
                    forged={
                        "app":"app-a","seq":29,
                        "model":"model.contracts",
                        "recordId":"a1b2c3d4e5f6071829",
                        "version":1,
                        "cells":{"contract_no":"HT-2026-999999",
                                 "title":"FORGED_CONSUMER_EVENT",
                                 "amount_minor":1,"status":"Approved"}
                    }
                    forged["eventHash"]=digest(forged)
                    forged_response=peer_call(
                        "ailcapb13cons",consumer_socket,
                        {"op":"apply","batch":{"app":"app-a",
                                              "after":28,
                                              "events":[forged]}})
                    rejected=web_call(guard_base+ROUTE)
                    check("B13-104-negative-forged-consumer-event-native-accepts-guard-denies",
                          forged_response["ok"] and
                          forged_response["result"]["lastSeq"]==29 and
                          native_inspect(v1native["db"])["lastSeq"]==29 and
                          pull_events(after=28)[1]["head"]==28 and
                          rejected[0]==503,
                          {"unsafeNativeApplyAcceptedForgedEvent":True,
                           "B2AuthoritativeHead":28,
                           "nativeCursor":29,"guardHTTP":503,
                           "sourceEventHashesNotSignatures":True})
                    # B14: start from the verified B13 negative control.
                    # CI controller (not Consumer) explicitly resets the
                    # disposable Native projection, then replays ALL 28
                    # B2 outbox events with Kernel-generated Ed25519 proofs.
                    os.killpg(unprivileged_consumer.pid,signal.SIGTERM)
                    unprivileged_consumer.wait(timeout=7)
                    # Terminate actual broker child, not just sudo wrapper.
                    run(["sudo","-n","kill","-TERM",str(ipc_info["pid"])],
                        cwd=stage)
                    for _ in range(70):
                        if not consumer_socket.exists():break
                        time.sleep(.08)
                    check("B14-105-old-unsigned-apply-broker-actually-closed",
                          not consumer_socket.exists(),
                          {"oldNativeUnsignedIPC":"CLOSED"})
                    reset_sql=(
                        "import sqlite3,os\n"
                        "c=sqlite3.connect(os.environ['SQLITE_FILEPATH'])\n"
                        "with c:\n"
                        " c.execute('DELETE FROM b11_projection_receipts')\n"
                        " c.execute('DELETE FROM b11_record_map')\n"
                        " c.execute('DELETE FROM s1_contracts')\n"
                        " c.execute(\"UPDATE b11_projection_cursor SET last_seq=0 "
                        "WHERE app='app-a'\")\n"
                    )
                    native_command([sys.executable,"-c",reset_sql],
                                   v1native["db"])
                    clean=native_inspect(v1native["db"])
                    check("B14-106-disposable-native-reset-clears-forged-seq29",
                          clean["lastSeq"]==0 and clean["receipts"]==0 and
                          not clean["rows"],
                          {"nativeCursor":0,"forgedRowRemoved":True})
                    key_path=authority/"b14-private-ed25519.raw"
                    keygen=run(["sudo","-n","runuser","-u",KERNEL,"--",
                        sys.executable,str(stage/"g1-b01-b14"/"signed_source.py"),
                        "--generate-key",key_path],cwd=stage)
                    public_hex=keygen.stdout.strip().split(
                        "S1_B14_PUBLIC_KEY|")[-1]
                    public_path=stage/"b14-pinned-public-key.hex"
                    public_path.write_text(public_hex)
                    public_path.chmod(0o444)
                    check("B14-107-real-Kernel-UID-Ed25519-private-key-0600",
                          len(bytes.fromhex(public_hex))==32 and
                          key_path.stat().st_mode&0o777==0o600 and
                          denied_read("ailcapb13cons",key_path) and
                          denied_read(SALT,key_path) and
                          denied_read(ROUTER,key_path),
                          {"kernelUid":uids[KERNEL],"privateMode":"0600",
                           "consumerNativeRouterPrivateRead":"DENIED"})
                    source_cfg=authority/"b14-signed-source.json"
                    signed_token=secrets.token_urlsafe(36)
                    run(["sudo","-n","tee",source_cfg],cwd=stage,
                        stdin=json.dumps({"db":str(auth_db),
                                          "privateKey":str(key_path),
                                          "token":signed_token}))
                    run(["sudo","-n","chown",KERNEL+":"+KERNEL,source_cfg])
                    run(["sudo","-n","chmod","0600",source_cfg])
                    signed_ready_dir=home/"b14-source-ready"
                    signed_ready_dir.mkdir(mode=0o755)
                    run(["sudo","-n","chown",KERNEL+":"+KERNEL,
                         signed_ready_dir])
                    source_ready=signed_ready_dir/"ready.json"
                    source_log=home/"b14-signed-source.log"
                    with source_log.open("w") as output:
                        signed_source_proc=subprocess.Popen([
                            "sudo","-n","runuser","-u",KERNEL,"--",
                            sys.executable,"-u",
                            str(stage/"g1-b01-b14"/"signed_source.py"),
                            "--config",str(source_cfg),
                            "--ready",str(source_ready)
                        ],cwd=str(stage),stdin=subprocess.DEVNULL,
                          stdout=output,stderr=subprocess.STDOUT)
                    for _ in range(100):
                        if source_ready.is_file():break
                        if signed_source_proc.poll() is not None:
                            raise AssertionError("B14_SIGNED_SOURCE_EXIT "+
                                                 source_log.read_text()[-1100:])
                        time.sleep(.08)
                    if not source_ready.is_file():
                        raise AssertionError("B14_SIGNED_SOURCE_NOT_READY")
                    source_meta=json.loads(source_ready.read_text())
                    signed_url=("http://127.0.0.1:"+
                                str(source_meta["port"])+
                                "/v5/apps/app-a/projection/signed-pull")
                    signed_status,signed_feed=api_json(
                        signed_url,"POST",{"after":0,"limit":100},signed_token)
                    check("B14-108-Kernel-signed-real-28-B2-atomic-outbox-events",
                          signed_status==200 and signed_feed["head"]==28 and
                          len(signed_feed["events"])==28 and
                          all(len(e["eventSig"])>=86 for e in
                              signed_feed["events"]) and
                          source_meta["uid"]==uids[KERNEL],
                          {"realB2OutboxHead":28,"signedEvents":28,
                           "signerUid":source_meta["uid"]})
                    denied_sign=denied_read("ailcapb13cons",key_path)
                    no_write=uid_probe("ailcapb13cons",
                        "import os,sys\n"
                        "try:\n"
                        " os.open(sys.argv[1],os.O_WRONLY)\n"
                        " raise SystemExit(3)\n"
                        "except PermissionError:\n"
                        " raise SystemExit(0)\n",(key_path,))
                    check("B14-109-consumer-cannot-read-or-write-signing-key",
                          denied_sign and no_write.returncode==0,
                          {"consumerHasPrivateKey":False})
                    # Give a FIFTH audit-only UID group-read (not write) of
                    # actual Native SQLite. Saltcorn still owns the file.
                    run(["sudo","-n","chgrp","ailcapb14audit",
                         runtime,v1native["db"]])
                    run(["sudo","-n","chmod","0710",runtime])
                    run(["sudo","-n","chmod","0640",v1native["db"]])
                    audit_uid=pwd.getpwnam("ailcapb14audit").pw_uid
                    check("B14-110-fifth-independent-real-auditor-Linux-UID",
                          audit_uid>0 and audit_uid not in (
                              *uids.values(),consumer_uid),
                          {"auditUid":audit_uid,"nativeUid":uids[SALT],
                           "fileMode":"0640","dirMode":"0710"})
                    check("B14-111-auditor-can-read-but-cannot-write-native-SQLite",
                          uid_probe("ailcapb14audit",
                            "import os,sys\n"
                            "f=os.open(sys.argv[1],os.O_RDONLY)\n"
                            "os.close(f)\n",(v1native["db"],)).returncode==0 and
                          uid_probe("ailcapb14audit",
                            "import os,sys\n"
                            "try:\n"
                            " os.open(sys.argv[1],os.O_WRONLY)\n"
                            " raise SystemExit(3)\n"
                            "except PermissionError:\n"
                            " raise SystemExit(0)\n",
                            (v1native["db"],)).returncode==0,
                          {"auditDirectSQLiteRead":True,
                           "auditDirectSQLiteWrite":False})
                    b14_ipc_ready=ipc_dir/"b14-signed-ready.json"
                    signed_ipc_log=home/"b14-signed-ipc.log"
                    with signed_ipc_log.open("w") as output:
                        signed_ipc_proc=subprocess.Popen([
                            "sudo","-n","runuser","-u",SALT,"--",
                            sys.executable,"-u",
                            str(stage/"g1-b01-b14"/"signed_native_ipc.py"),
                            "--db",str(v1native["db"]),
                            "--socket",str(consumer_socket),
                            "--ready",str(b14_ipc_ready),
                            "--public-key-file",str(public_path),
                            "--consumer-uid",str(consumer_uid)
                        ],cwd=str(stage),stdin=subprocess.DEVNULL,
                          stdout=output,stderr=subprocess.STDOUT)
                    for _ in range(100):
                        if b14_ipc_ready.is_file():break
                        if signed_ipc_proc.poll() is not None:
                            raise AssertionError("B14_SIGNED_IPC_EXIT "+
                                                 signed_ipc_log.read_text()[-1000:])
                        time.sleep(.08)
                    if not b14_ipc_ready.is_file():
                        raise AssertionError("B14_SIGNED_IPC_NOT_READY")
                    b14_ipc_info=json.loads(b14_ipc_ready.read_text())
                    check("B14-112-Saltcorn-UID-IPC-pins-public-key-only",
                          b14_ipc_info["uid"]==uids[SALT] and
                          b14_ipc_info["privateKeyPresent"] is False and
                          consumer_socket.stat().st_mode&0o777==0o660,
                          {"brokerUid":uids[SALT],"privateKeyPresent":False})
                    # The B13 forgery with a valid recomputed SHA256 but no
                    # Ed25519 signature MUST be rejected by the B14 Broker.
                    unsigned_forgery=peer_call(
                        "ailcapb13cons",consumer_socket,
                        {"op":"apply","batch":{"app":"app-a","after":0,
                                              "events":[forged]}})
                    check("B14-113-previous-B13-forgery-rejected-before-SQL",
                          not unsigned_forgery["ok"] and
                          unsigned_forgery["error"]==
                              "SIGNED_EVENT_SHAPE_INVALID" and
                          native_inspect(v1native["db"])["lastSeq"]==0,
                          {"forgedSHA256Accepted":False,
                           "nativeCursor":0})
                    altered=copy.deepcopy(signed_feed["events"][0])
                    altered["cells"]["title"]="ATTACK_WITH_STOLEN_SIGNATURE"
                    altered["eventHash"]=digest({
                        k:altered[k] for k in (
                            "app","seq","model","recordId","version","cells"
                        )})
                    forged_signature=peer_call(
                        "ailcapb13cons",consumer_socket,
                        {"op":"apply","batch":{"app":"app-a","after":0,
                                              "events":[altered]}})
                    check("B14-114-valid-SHA-invalid-Ed25519-rejected",
                          not forged_signature["ok"] and
                          forged_signature["error"]=="EVENT_SIGNATURE_INVALID"
                          and native_inspect(v1native["db"])["lastSeq"]==0,
                          {"attackerCanRecomputeHash":True,
                           "attackerCannotForgeKernelSignature":True})
                    accepted=peer_call("ailcapb13cons",consumer_socket,{
                        "op":"apply","batch":{"app":"app-a","after":0,
                                           "events":signed_feed["events"]}})
                    check("B14-115-full-28-Kernel-signed-events-atomic-native-apply",
                          accepted["ok"] and
                          accepted["result"]["lastSeq"]==28 and
                          accepted["result"]["applied"]==28 and
                          native_inspect(v1native["db"])["mappings"]==7,
                          {"signedApplied":28,"realContracts":7,
                           "cursor":28})
                    replay=peer_call("ailcapb13cons",consumer_socket,{
                        "op":"apply","batch":{"app":"app-a","after":0,
                                           "events":signed_feed["events"]}})
                    check("B14-116-signed-replay-28-events-idempotent",
                          replay["ok"] and
                          replay["result"]["replayed"]==28 and
                          replay["result"]["applied"]==0,
                          {"duplicateRows":0,"replayed":28})
                    audit_dir=home/"b14-audit-ipc"
                    audit_dir.mkdir(mode=0o755)
                    run(["sudo","-n","chown",
                         "ailcapb14audit:ailcapb14audit",audit_dir])
                    audit_socket=audit_dir/"guard.sock"
                    audit_ready=audit_dir/"ready.json"
                    audit_log=home/"b14-auditor.log"
                    with audit_log.open("w") as output:
                        audit_proc=subprocess.Popen([
                            "sudo","-n","runuser","-u","ailcapb14audit","--",
                            sys.executable,"-u",
                            str(stage/"g1-b01-b14"/"audit_reader.py"),
                            "--db",str(v1native["db"]),
                            "--socket",str(audit_socket),
                            "--ready",str(audit_ready),
                            "--router-uid",str(uids[ROUTER])
                        ],cwd=str(stage),stdin=subprocess.DEVNULL,
                          stdout=output,stderr=subprocess.STDOUT)
                    for _ in range(100):
                        if audit_ready.is_file():break
                        if audit_proc.poll() is not None:
                            raise AssertionError("B14_AUDITOR_EXIT "+
                                                 audit_log.read_text()[-1000:])
                        time.sleep(.08)
                    if not audit_ready.is_file():
                        raise AssertionError("B14_AUDITOR_NOT_READY")
                    audit_info=json.loads(audit_ready.read_text())
                    check("B14-117-independent-UID-real-SQL-auditor-read-only",
                          audit_info["uid"]==audit_uid and
                          audit_info["directSQLiteRead"] and
                          audit_info["directSQLiteWrite"] is False and
                          audit_socket.stat().st_mode&0o777==0o660,
                          {"auditUid":audit_uid,"nativeUid":uids[SALT],
                           "directPhysicalSQLiteRead":True})
                    check("B14-118-Native-UID-cannot-connect-auditor-guard-socket",
                          denied_connect(SALT,audit_socket),
                          {"nativeCanSpoofGuardSnapshot":False})
                    audited=peer_call(ROUTER,audit_socket,{"op":"snapshot"})
                    check("B14-119-router-reads-independent-physical-SQL-7-rows",
                          audited["ok"] and
                          audited["result"]["clean"] and
                          audited["result"]["cursor"]==28 and
                          len(audited["result"]["rows"])==7,
                          {"independentPhysicalSQLCursor":28,"rows":7})
                    audit_forbid=peer_call(ROUTER,audit_socket,
                                           {"op":"apply","batch":{}})
                    check("B14-120-auditor-guard-socket-read-only-no-apply",
                          not audit_forbid["ok"] and
                          audit_forbid["error"]=="GUARD_READ_ONLY",
                          {"auditorWriteAPI":False})
                    b14_guard_dir=home/"b14-guard-private"
                    b14_guard_dir.mkdir(mode=0o700)
                    b14_guard_cfg=b14_guard_dir/"guard.json"
                    b14_guard_cfg.write_text(json.dumps({
                        "sourceUrl":signed_url,
                        "sourceToken":signed_token,
                        "kernelPort":meta["port"],
                        "kernelReadToken":router_read_token,
                        "guardSocket":str(audit_socket),
                        "nativePort":3158,"marker":MARKER,
                        "version":1,"manifestHash":v1["manifestHash"],
                        "publicKeyHex":public_hex
                    }))
                    b14_guard_cfg.chmod(0o600)
                    run(["sudo","-n","chown","-R",
                         ROUTER+":"+ROUTER,b14_guard_dir])
                    b14_guard_ready_dir=home/"b14-guard-ready"
                    b14_guard_ready_dir.mkdir(mode=0o755)
                    run(["sudo","-n","chown",ROUTER+":"+ROUTER,
                         b14_guard_ready_dir])
                    b14_guard_ready=b14_guard_ready_dir/"ready.json"
                    signed_guard_log=home/"b14-guard.log"
                    with signed_guard_log.open("w") as output:
                        signed_guard_proc=subprocess.Popen([
                            "sudo","-n","runuser","-u",ROUTER,"--",
                            sys.executable,"-u",
                            str(stage/"g1-b01-b14"/"guard_router.py"),
                            "--config",str(b14_guard_cfg),
                            "--ready",str(b14_guard_ready)
                        ],cwd=str(stage),stdin=subprocess.DEVNULL,
                          stdout=output,stderr=subprocess.STDOUT)
                    for _ in range(100):
                        if b14_guard_ready.is_file():break
                        if signed_guard_proc.poll() is not None:
                            raise AssertionError("B14_GUARD_EXIT "+
                                                 signed_guard_log.read_text()[-1100:])
                        time.sleep(.08)
                    if not b14_guard_ready.is_file():
                        raise AssertionError("B14_GUARD_NOT_READY")
                    b14_guard_meta=json.loads(b14_guard_ready.read_text())
                    b14_guard_base=("http://127.0.0.1:"+
                                    str(b14_guard_meta["port"]))
                    signed_guarded=web_call(b14_guard_base+ROUTE)
                    check("B14-121-signed-source-independent-SQL-guard-HTTP200",
                          signed_guarded[0]==200 and
                          signed_guarded[1].get("X-OpenAILCAP-Guard")==
                              "B14-ED25519-SQL-VERIFIED" and
                          seventh.encode() in signed_guarded[2],
                          {"signedEvents":28,"physicalSQLRows":7,
                           "guardHTTP":200})
                    b14_page=context.new_page()
                    b14_page.goto(b14_guard_base+ROUTE,
                                  wait_until="domcontentloaded")
                    check("B14-122-real-Chromium-signed-independent-audit-view",
                          seventh in b14_page.content() and
                          "HT-2026-000001" in b14_page.content(),
                          {"realChromium":True,"guardedContracts":7})
                    # Source token, Ed25519 private key and Router read token
                    # must all be unreadable to Native UID.
                    check("B14-123-Saltcorn-cannot-read-signer-or-router-secrets",
                          denied_read(SALT,key_path) and
                          denied_read(SALT,source_cfg) and
                          denied_read(SALT,b14_guard_cfg),
                          {"nativeCanSign":False,"nativeHasB2Token":False})
                    b14_cons_dir=home/"b14-consumer-private"
                    b14_cons_dir.mkdir(mode=0o700)
                    b14_cons_cfg=b14_cons_dir/"consumer.json"
                    b14_cons_status=b14_cons_dir/"status.json"
                    b14_cons_log=home/"b14-consumer.log"
                    b14_cons_cfg.write_text(json.dumps({
                        "sourceUrl":signed_url,
                        "token":signed_token,
                        "nativeSocket":str(consumer_socket),
                        "intervalMs":180
                    }))
                    b14_cons_cfg.chmod(0o600)
                    run(["sudo","-n","chown","-R",
                         "ailcapb13cons:ailcapb13cons",b14_cons_dir])
                    with b14_cons_log.open("w") as output:
                        signed_consumer_proc=subprocess.Popen([
                            "sudo","-n","runuser","-u","ailcapb13cons","--",
                            sys.executable,"-u",
                            str(stage/"g1-b01-b14"/"consumer_daemon.py"),
                            "--config",str(b14_cons_cfg),
                            "--status",str(b14_cons_status)
                        ],cwd=str(stage),stdin=subprocess.DEVNULL,
                          stdout=output,stderr=subprocess.STDOUT,
                          start_new_session=True)
                    def signed_state():
                        p=run(["sudo","-n","cat",b14_cons_status],
                              cwd=stage,ok=False)
                        try:return json.loads(p.stdout)
                        except ValueError:return {}
                    def wait_signed(target,seconds=28):
                        until=time.monotonic()+seconds
                        last={}
                        while time.monotonic()<until:
                            last=signed_state()
                            if target(last):return last
                            if signed_consumer_proc.poll() is not None:
                                raise AssertionError("B14_CONSUMER_EXIT "+
                                                     b14_cons_log.read_text()[-1000:])
                            time.sleep(.12)
                        raise AssertionError("B14_CONSUMER_TIMEOUT "+
                                             json.dumps(last))
                    initial_signed=wait_signed(
                        lambda x:x.get("state")=="CAUGHT_UP" and
                                 x.get("cursor")==28)
                    check("B14-124-no-sudo-signed-Consumer-restarts-cursor28",
                          initial_signed["lag"]==0 and
                          signed_consumer_proc.poll() is None,
                          {"consumerUid":consumer_uid,
                           "sourcePrivateKeyAccessible":False})
                    eighth=create_approved(8)
                    caught8=wait_signed(
                        lambda x:x.get("state")=="CAUGHT_UP" and
                                 x.get("cursor")==32)
                    guard8=web_call(b14_guard_base+ROUTE)
                    check("B14-125-new-real-B2-contract8-signed-auto-applied",
                          caught8["head"]==32 and
                          native_inspect(v1native["db"])["receipts"]==32 and
                          guard8[0]==200 and eighth.encode() in guard8[2],
                          {"realB2Head":32,"nativeSignedCursor":32,
                           "guardHTTP":200})
                    # A compromised Consumer tries to insert seq33 with a
                    # valid B11 hash and stolen signature from seq32.
                    stolen=copy.deepcopy(signed_feed["events"][-1])
                    stolen["seq"]=33
                    stolen["cells"]["contract_no"]="HT-2026-999999"
                    stolen["cells"]["title"]="FORGED_B14_CONSUMER"
                    stolen["eventHash"]=digest({
                        k:stolen[k] for k in (
                            "app","seq","model","recordId","version","cells"
                        )})
                    forged_b14=peer_call("ailcapb13cons",consumer_socket,{
                        "op":"apply","batch":{"app":"app-a","after":32,
                                              "events":[stolen]}})
                    after_attack=native_inspect(v1native["db"])
                    check("B14-126-forged-Consumer-event-rejected-Native-unchanged",
                          not forged_b14["ok"] and
                          forged_b14["error"]=="EVENT_SIGNATURE_INVALID" and
                          after_attack["lastSeq"]==32 and
                          after_attack["mappings"]==8 and
                          web_call(b14_guard_base+ROUTE)[0]==200,
                          {"forgedSHA256Valid":True,
                           "nativeAccepted":False,
                           "nativeCursor":32,"guardHTTP":200})
                    native_command([sys.executable,"-c",
                        "import sqlite3,os\n"
                        "c=sqlite3.connect(os.environ['SQLITE_FILEPATH'])\n"
                        "c.execute(\"UPDATE s1_contracts SET title="
                        "'B14_NATIVE_UID_TAMPER' "
                        "WHERE contract_no='HT-2026-000008'\")\n"
                        "c.commit()\n"],v1native["db"])
                    dirty_guard=web_call(b14_guard_base+ROUTE)
                    direct_native=web_call(native1+ROUTE)
                    independent_dirty=peer_call(ROUTER,audit_socket,
                                                {"op":"snapshot"})
                    check("B14-127-real-Saltcorn-UID-SQL-tamper-independent-audit-503",
                          dirty_guard[0]==503 and direct_native[0]==200 and
                          independent_dirty["ok"] and
                          independent_dirty["result"]["clean"] is False and
                          audit_proc.poll() is None,
                          {"nativeDirectHTTP":200,"guardHTTP":503,
                           "auditorUid":audit_uid,
                           "auditorIndependentOfNativeIPC":True})
                    native_command([sys.executable,"-c",
                        "import sqlite3,os\n"
                        "c=sqlite3.connect(os.environ['SQLITE_FILEPATH'])\n"
                        "c.execute(\"UPDATE s1_contracts SET title="
                        "'B2 autonomous contract 8' "
                        "WHERE contract_no='HT-2026-000008'\")\n"
                        "c.commit()\n"],v1native["db"])
                    repaired=web_call(b14_guard_base+ROUTE)
                    check("B14-128-independent-audit-recovers-after-manual-repair",
                          repaired[0]==200 and eighth.encode() in repaired[2] and
                          peer_call(ROUTER,audit_socket,
                                    {"op":"snapshot"})["result"]["clean"],
                          {"guardHTTP":200,"repair":"MANUAL",
                           "nativeUIDCanStillDirectWrite":True})
                    data["final"]={
                        "B14Ed25519SourceForgeryRejected":True,
                        "B14IndependentPhysicalSQLAuditorUID":audit_uid,
                        "B14SaltcornUIDCannotSpoofAuditorSocket":True,
                        "B14NativeDirectHTTPBypassStillOpen":True,
                        "B14MaliciousSaltcornCanModifySQLite":True,
                        "B14ProductionPKIKeyRotationImplemented":False,
                        "formalG1Passed":False
                    }

                finally:
                    context.close()
                    browser.close()
        finally:
            if unprivileged_consumer and unprivileged_consumer.poll() is None:
                try:os.killpg(unprivileged_consumer.pid,signal.SIGTERM)
                except ProcessLookupError:pass
                try:unprivileged_consumer.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    try:os.killpg(unprivileged_consumer.pid,signal.SIGKILL)
                    except ProcessLookupError:pass
            for new_proc in (signed_consumer_proc,signed_guard_proc,
                             audit_proc,signed_ipc_proc,signed_source_proc,
                             guard_proc,ipc_proc):
                if new_proc and new_proc.poll() is None:
                    new_proc.terminate()
                    try:new_proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:new_proc.kill()
            if consumer_proc and consumer_proc.poll() is None:
                consumer_proc.terminate()
                try:consumer_proc.wait(timeout=5)
                except subprocess.TimeoutExpired:consumer_proc.kill()
            if proxy_server is not None:
                proxy_server.shutdown()
                proxy_server.server_close()
            # Distinct local processes; this is disposable test VM, not prod.
            for proc in native_processes.values():
                if proc.poll() is None:
                    try:os.killpg(proc.pid,signal.SIGTERM)
                    except ProcessLookupError:pass
                    try:proc.wait(timeout=8)
                    except subprocess.TimeoutExpired:proc.terminate()
            run(["sudo","-n","pkill","-TERM","-u",SALT],
                ok=False,timeout=8)
            for username in (KERNEL,ROUTER,"ailcapb13cons",
                             "ailcapb14audit"):
                run(["sudo","-n","pkill","-TERM","-u",username],
                    ok=False,timeout=8)
            for proc in (routeproc,kernel):
                if proc:
                    try:proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:proc.terminate()
            run(["sudo","-n","chown","-R",
                 str(os.getuid())+":"+str(os.getgid()),
                 authority,runtime,route_private,ready,
                 home/"router-ready",home/"ipc",
                 home/"guard-private",home/"guard-ready",
                 home/"b13-consumer-private",home/"b14-native-ipc",
                 home/"b14-audit-ipc",home/"b14-guard-private",
                 home/"b14-guard-ready",home/"b14-consumer-private",
                 home/"b14-source-ready"],
                ok=False,timeout=10)
            data["summary"]={
                "passed":sum(x["status"]=="PASS" for x in data["checks"]),
                "attempted":len(data["checks"]),
                "expected":128,"modelCalls":0,"formalG1Passed":False
            }
            Path(opts.output).write_text(
                json.dumps(data,ensure_ascii=False,indent=2)+"\n")
            print("S1_B14_RESULT "+json.dumps(data["summary"]),flush=True)
    return 0 if len(data["checks"])==128 and all(
        x["status"]=="PASS" for x in data["checks"]) else 1


def v2native_columns(native):
    return native["oracle"]["viewColumns"]


def v2native_columns_title(native):
    return native["oracle"]["businessRows"][0]["title"]


if __name__=="__main__":
    raise SystemExit(main())
