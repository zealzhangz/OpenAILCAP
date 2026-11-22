#!/usr/bin/env python3
"""B9 REAL B2 Kernel -> derived actual Saltcorn Pack/SQLite/Chromium.

CI: 3 distinct non-root OS UIDs, genuine B2 release tool, Saltcorn @1.7.0-beta.5
official CLI, native Web /field, physical SQLite read-only oracles for BOTH
trust domains, tamper/rebuild, v1->v2->v1 rollback. No external model.
LIMITS: Only model+view subset; workflow and B4 code remain on B2 kernel,
not equivalent to Saltcorn; runtime switch uses sequential local processes.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import copy
import json
import os
import pwd
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request,urlopen

from playwright.sync_api import sync_playwright

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
sys.path.insert(0,str(ROOT/"g1-b01-b2"))
sys.path.insert(0,str(ROOT/"platform-saltcorn"/"browser"))
from schema_core import sha
from projector import compile_release,check_compiled,ProjectionRejected
from p0a_browser_suite import run_suite
from p0a_docker_suite import run_suite as run_docker_suite

KERN="ailcapb9kern"
RUNT="ailcapb9run"
PLUG="ailcapb9plug"


def execute(args,cwd=None,env=None,stdin=None,timeout=125,strict=True):
    p=subprocess.run(
        list(map(str,args)),cwd=str(cwd) if cwd else None,env=env,
        input=stdin,text=True,capture_output=True,timeout=timeout,check=False)
    if strict and p.returncode:
        raise RuntimeError("RUN_FAILURE status="+str(p.returncode)+
                           " cmd="+str(args[0])+
                           " stderr_tail="+p.stderr[-300:])
    return p


def single(output,header):
    rows=[r.split("|",1)[1] for r in output.splitlines()
          if r.startswith(header+"|")]
    if len(rows)!=1:raise AssertionError("B9_BAD_ORACLE_"+header)
    return json.loads(rows[0])


def http(base,app,tool,token,args):
    req=Request(
        base+"/v3/apps/"+app+"/tools/"+tool,
        data=json.dumps(args,ensure_ascii=False).encode(),
        headers=({"Authorization":"Bearer "+token}
                 if token is not None else {}) | {
                    "Content-Type":"application/json"},
        method="POST")
    try:
        with urlopen(req,timeout=20) as resp:
            return resp.status,json.loads(resp.read())
    except HTTPError as e:
        return e.code,json.loads(e.read())


def wait_page(base,path,limit=65):
    until=time.monotonic()+limit
    while time.monotonic()<until:
        try:
            with urlopen(base+path,timeout=3) as r:
                if r.status==200:return True
        except Exception:
            pass
        time.sleep(.18)
    return False


def wait_text(page,selector,expected):
    for _ in range(90):
        if expected in page.locator(selector).inner_text(timeout=1000):
            return
        page.wait_for_timeout(.12*1000)
    raise AssertionError("B9_EXPECTED_BROWSER_TEXT_"+selector)


def login_kernel(page,base,password):
    page.goto(base+"/editor/app-a",wait_until="domcontentloaded")
    if not page.url.endswith("/editor/login"):
        raise AssertionError("B9_AUTH_REQUIRED")
    page.locator("#password").fill(password)
    page.locator("#login").click()
    page.wait_for_url("**/editor/app-a",timeout=14000)


def login_native(page,base,password):
    page.goto(base+"/auth/login",wait_until="domcontentloaded")
    page.locator('input[name="email"]').fill("s1-research-admin@example.invalid")
    page.locator('input[name="password"]').fill(password)
    page.locator('form[action="/auth/login"] button[type="submit"], form[action="/auth/login"] input[type="submit"]').last.click()
    page.wait_for_load_state("domcontentloaded")


def main():
    pa=argparse.ArgumentParser()
    pa.add_argument("--output",required=True)
    args=pa.parse_args()
    evidence={
        "experiment":"B9_TRUE_AUTHORITATIVE_B2_KERNEL_DERIVED_REAL_SALTCORN",
        "modelCalls":0,
        "nativeRuntimeUsesAuthoritySQLite":False,
        "sameUidAsAuthority":False,
        "runtimeCanModifyItsDisposableProjection":True,
        "workflowActuallyProjectedToSaltcorn":False,
        "codeActuallyProjectedToSaltcorn":False,
        "zeroDowntimeCutoverValidated":False,
        "g1Passed":False,"checks":[]
    }
    def check(cid,ok,observed):
        row={"id":cid,"status":"PASS" if ok else "FAIL","observed":observed}
        evidence["checks"].append(row)
        print(cid+" "+row["status"]+" "+
              json.dumps(observed,ensure_ascii=False),flush=True)
        if not ok:raise AssertionError(cid)

    uids=[pwd.getpwnam(x).pw_uid for x in (KERN,RUNT,PLUG)]
    check("B9-01-distinct-real-Linux-OS-owners",
          len(set(uids))==3 and all(u>0 for u in uids)
          and os.geteuid() not in uids,
          {"kernelUid":uids[0],"saltcornUid":uids[1],
           "pluginUid":uids[2]})
    with tempfile.TemporaryDirectory(prefix="s1-b9-derive-") as tmp:
        home=Path(tmp);home.chmod(0o755)
        stage=home/"public-source";stage.mkdir(mode=0o755)
        for directory,names in {
            "g1-b01-b2":("schema_core.py","schema_http.py"),
            "g1-b01-b4":("registry.py","policy.py","sandbox.py","worker.py"),
            "g1-b01-b5":("tool_broker.py",),
            "g1-b01-b7":("physical_sql_oracle.py",),
            "g1-b01-b8":(),
            "g1-b01-b9":("kernel_service.py","native_oracle.py",
                         "native_env_launcher.py","plugin_client.py"),
            "platform-saltcorn":("contract-pack.json","seed-contract.js")
        }.items():
            dst=stage/directory;dst.mkdir(mode=0o755)
            for name in names:
                shutil.copyfile(ROOT/directory/name,dst/name)
                (dst/name).chmod(0o644)
        native_attack=ROOT/"platform-saltcorn"/"governed"/"native-out-of-band.js"
        shutil.copyfile(native_attack,stage/"native-out-of-band.js")
        (stage/"native-out-of-band.js").chmod(0o644)

        authority=home/"authority-private"
        runtime=home/"runtime-private"
        ready=home/"ready"
        for path in (authority,runtime):
            path.mkdir(mode=0o700)
        ready.mkdir(mode=0o755)
        # Create private config under the CI controller first, then chown
        # to the kernel UID. A 0700 kernel-owned directory cannot be
        # traversed by the test controller (that is the safety property).
        db=authority/"authority.sqlite"
        config=authority/"kernel-config.json"
        readyfile=ready/"kernel-ready.json"
        kernel_log=home/"kernel.log"
        salt_log=home/"saltcorn.log"

        password=secrets.token_urlsafe(38)
        token_agent=secrets.token_urlsafe(38)
        token_plugin=secrets.token_urlsafe(38)
        token_publisher=secrets.token_urlsafe(38)
        token_runtime=secrets.token_urlsafe(38)
        token_appb=secrets.token_urlsafe(38)
        config.write_text(json.dumps({
            "dbPath":str(db),"humanPassword":password,
            "agentToken":token_agent,"pluginToken":token_plugin,
            "publisherToken":token_publisher,
            "runtimeToken":token_runtime,"appBPublisherToken":token_appb
        }),encoding="utf-8")
        config.chmod(0o600)
        execute(["sudo","-n","chown","-R",KERN+":"+KERN,authority])
        execute(["sudo","-n","chown","-R",RUNT+":"+RUNT,runtime])
        execute(["sudo","-n","chown","-R",KERN+":"+KERN,ready])
        salt_session=secrets.token_urlsafe(45)
        admin_password=secrets.token_urlsafe(33)
        salt_env=os.environ.copy()
        salt_env.update({
            "PATH":os.environ.get("PATH","/usr/bin:/bin"),
            "HOME":str(runtime),
            "SALTCORN_SESSION_SECRET":salt_session,
            "SALTCORN_NWORKERS":"1",
            "SQLITE_FILEPATH":str(runtime/"not-selected.sqlite")
        })
        procs=[]
        def kernel_physical():
            out=execute([
                "sudo","-n","runuser","-u",KERN,"--",
                sys.executable,str(stage/"g1-b01-b7"/"physical_sql_oracle.py"),
                "--db",db],cwd=stage)
            return single(out.stdout,"S1_B7_PHYSICAL")

        def native_cmd(argv,dbfile,timeout=150,strict=True):
            env={key:salt_env[key] for key in (
                "PATH","HOME","SALTCORN_SESSION_SECRET","SALTCORN_NWORKERS")}
            env["SQLITE_FILEPATH"]=str(dbfile)
            out=execute([
                "sudo","-n","runuser","-u",RUNT,"--",
                sys.executable,str(stage/"g1-b01-b9"/"native_env_launcher.py"),
                *argv
            ],cwd=stage,env=salt_env,stdin=json.dumps(env)+"\n",
              strict=False,timeout=timeout)
            if strict and out.returncode:
                raise RuntimeError("SALT_NATIVE_FAIL: "+str(out.returncode)+
                                   " "+out.stderr[-300:])
            return out

        def native_physical(dbfile):
            response=native_cmd([
                sys.executable,str(stage/"g1-b01-b9"/"native_oracle.py"),
                "--db",dbfile
            ],dbfile,timeout=20)
            return single(response.stdout,"S1_B9_NATIVE_ORACLE")

        def compiled_file(tag,release):
            projection=compile_release(release,template)
            check_compiled(projection)
            path=stage/("projection-"+tag+".json")
            path.write_text(json.dumps(
                projection["projectionPack"],ensure_ascii=False,indent=2),
                encoding="utf-8")
            path.chmod(0o444)
            return projection,path

        def create_native(tag,release):
            projection,packfile=compiled_file(tag,release)
            dbpath=runtime/("projection-"+tag+".sqlite")
            reset=native_cmd(["saltcorn","reset-schema","-f"],dbpath)
            install=native_cmd(["saltcorn","install-pack","-f",packfile],dbpath)
            seed=native_cmd(["saltcorn","run-js","-f",
                             stage/"platform-saltcorn"/"seed-contract.js"],dbpath)
            admin=native_cmd(["saltcorn","create-user","--admin",
                              "--email","s1-research-admin@example.invalid",
                              "--password",admin_password],dbpath)
            obs=native_physical(dbpath)
            if not all(x.returncode==0 for x in (reset,install,seed,admin)):
                raise AssertionError("NATIVE_SETUP_FAILED")
            if obs["viewColumns"]!=release["definitions"]["view.contracts"]["columns"]:
                raise AssertionError("NATIVE_VIEW_PROJECTION_MISMATCH")
            return {"db":dbpath,"compiled":projection,"pack":packfile,
                    "physical":obs}

        def start_saltcorn(dbpath,port):
            env=salt_env.copy()
            config={key:env[key] for key in (
                "PATH","HOME","SALTCORN_SESSION_SECRET","SALTCORN_NWORKERS")}
            config["SQLITE_FILEPATH"]=str(dbpath)
            output=salt_log.open("w",encoding="utf-8")
            proc=subprocess.Popen([
                "sudo","-n","runuser","-u",RUNT,"--",
                sys.executable,str(stage/"g1-b01-b9"/"native_env_launcher.py"),
                "saltcorn","serve","--port",str(port),"--noscheduler"
            ],cwd=str(stage),env=env,stdin=subprocess.PIPE,
              stdout=output,stderr=subprocess.STDOUT,text=True)
            proc.stdin.write(json.dumps(config)+"\n")
            proc.stdin.flush()
            proc.stdin.close()
            procs.append(proc)
            base="http://127.0.0.1:"+str(port)
            if not wait_page(base,"/auth/login",70):
                # CI diagnosis without leaking the ephemeral Saltcorn or
                # Kernel secrets; the server output only belongs to fixture.
                diagnostic=salt_log.read_text(errors="replace")[-2400:]
                for private_value in (
                    salt_session,admin_password,password,
                    token_agent,token_plugin,token_runtime,token_publisher,token_appb
                ):
                    diagnostic=diagnostic.replace(
                        private_value,"[REDACTED]")
                raise RuntimeError(
                    "ACTUAL_SALTCORN_SERVER_NOT_READY status="+
                    str(proc.poll())+" excerpt="+diagnostic)
            return base

        def stop_runtime():
            # Only the untrusted Saltcorn user's processes; never kill kernel.
            execute(["sudo","-n","pkill","-TERM","-u",RUNT],
                    strict=False,timeout=8)
            for p in procs:
                try:p.wait(timeout=7)
                except subprocess.TimeoutExpired:p.terminate()
            procs.clear()

        def broker(app,tool,token,payload,expect=200):
            res=http(base,app,tool,token,payload)
            if res[0]!=expect:
                raise AssertionError("TOOL_"+tool+"_HTTP_"+str(res[0])+
                                     "_EXPECTED_"+str(expect)+
                                     "_BODY_"+str(res[1])[:350])
            return res[1]

        def plugin(payload):
            """One low-privilege OS process per call; grant passed on stdin."""
            p=execute([
                "sudo","-n","runuser","-u",PLUG,"--",sys.executable,
                str(stage/"g1-b01-b9"/"plugin_client.py")
            ],cwd=stage,stdin=json.dumps(payload,ensure_ascii=False)+"\n",
              timeout=25)
            out=single(p.stdout,"S1_P0A_PLUGIN")
            if out["uid"]!=uids[2]:
                raise AssertionError("PLUGIN_UID_NOT_SEPARATE")
            return out

        def plugin_tool(app,tool,payload):
            return plugin({"kind":"tool","base":base,"token":token_plugin,
                           "app":app,"tool":tool,"args":payload})

        def make_mutation(snap,rid,definition,cid):
            old=snap["resources"].get(rid)
            return {"changeId":cid,"resourceId":rid,
                    "expectedAppRevision":snap["appRevision"],
                    "expectedRevision":old["revision"] if old else None,
                    "baseContentHash":old["contentHash"] if old else None,
                    "definition":definition}

        template=json.loads((stage/"platform-saltcorn"/
                             "contract-pack.json").read_text())
        kernelproc=None
        try:
            with kernel_log.open("w",encoding="utf-8") as output:
                kernelproc=subprocess.Popen([
                    "sudo","-n","runuser","-u",KERN,"--",
                    sys.executable,"-u",str(stage/"g1-b01-b9"/"kernel_service.py"),
                    "--config",str(config),"--ready",str(readyfile)
                ],cwd=str(stage),env=os.environ.copy(),
                  stdin=subprocess.DEVNULL,stdout=output,
                  stderr=subprocess.STDOUT)
            for _ in range(120):
                if readyfile.is_file():break
                if kernelproc.poll() is not None:
                    raise RuntimeError("KERNEL_PROCESS_EXITED")
                time.sleep(.09)
            if not readyfile.exists():
                raise RuntimeError("KERNEL_START_TIMEOUT")
            metadata=json.loads(readyfile.read_text())
            base="http://127.0.0.1:"+str(metadata["port"])
            check("B9-02-trusted-Domain-Kernel-runs-as-nonroot-private-UID",
                  metadata["uid"]==uids[0] and
                  wait_page(base,"/health",10),
                  {"authorityOwnerUid":metadata["uid"],"loopbackOnly":True})
            def mode(path):
                v=execute(["sudo","-n","stat","-c","%a:%u",path]).stdout.strip()
                return v
            check("B9-03-authority-db-and-config-are-private-OS-objects",
                  mode(authority)=="700:"+str(uids[0]) and
                  mode(db)=="600:"+str(uids[0]) and
                  mode(config)=="600:"+str(uids[0]),
                  {"privateDir":"0700","db":"0600","config":"0600"})
            start=kernel_physical()
            check("B9-04-two-tenant-authority-apps-initially-empty",
                  start["app-a"]["revision"]==0 and
                  start["app-b"]["revision"]==0,
                  {"appA":0,"appB":0})
            attack=execute([
                "sudo","-n","runuser","-u",RUNT,"--",
                sys.executable,"-c",
                "import os,sqlite3,json,sys\n"
                "p=sys.argv[1]\n"
                "def access(mode):\n"
                " try:\n"
                "  fd=os.open(p,mode);os.close(fd);return 'OPENED'\n"
                " except OSError:return 'DENIED'\n"
                "def sql():\n"
                " try:\n"
                "  c=sqlite3.connect('file:'+p+'?mode=rw',uri=True)\n"
                "  c.execute(\"UPDATE apps SET revision=revision\")\n"
                "  c.commit();return 'UPDATED'\n"
                " except sqlite3.Error:return 'DENIED'\n"
                "print('S1_B9_DAC|'+json.dumps({'uid':os.getuid(),"
                "'r':access(os.O_RDONLY),'w':access(os.O_RDWR),"
                "'sql':sql()}))",
                db],cwd=stage)
            direct=single(attack.stdout,"S1_B9_DAC")
            check("B9-05-real-Saltcorn-runtime-UID-cannot-touch-authority-DB",
                  direct=={"uid":uids[1],"r":"DENIED","w":"DENIED",
                           "sql":"DENIED"},
                  direct)
            unauthorized=http(base,"app-a","release.read",None,{})
            cross=http(base,"app-b","release.read",token_runtime,{})
            check("B9-06-native-runtime-no-kernel-grants-and-cross-app-forbidden",
                  unauthorized[0]==401 and cross[0]==403,
                  {"missingToken":401,"crossAppToken":403})
            check("B9-07-runtime-process-not-given-kernel-publisher-credentials",
                  all(x not in salt_env.values() for x in (
                      token_agent,token_plugin,token_runtime,token_publisher,password,
                      token_appb)) and
                  all(v not in str(stage) for v in (
                      token_agent,token_plugin,token_runtime,token_publisher)),
                  {"separateUid":True,"noAuthorityCredentialsInRuntimeEnv":True})
            specs=json.loads(
                (ROOT/"g1-b01-b2"/"contract_spec.json").read_text())
            for i,rid in enumerate(specs,1):
                current=broker("app-a","draft.read",token_agent,{})
                cmd=make_mutation(current,rid,specs[rid],"b9-v1-resource-"+str(i))
                broker("app-a","metadata.upsert",token_agent,{"command":cmd})
            draft1=broker("app-a","draft.read",token_agent,{})
            check("B9-08-four-real-typed-B2-resources-with-v1-view-columns",
                  draft1["appRevision"]==4 and
                  set(draft1["resources"])==set(specs) and
                  draft1["resources"]["view.contracts"]["definition"][
                      "columns"]==["contract_no","amount_minor","status"],
                  {"revision":4,"viewColumns":["contract_no",
                                              "amount_minor","status"]})
            with sync_playwright() as pw:
                browser=pw.chromium.launch(headless=True,args=["--no-sandbox"])
                context=browser.new_context()
                try:
                    page=context.new_page()
                    login_kernel(page,base,password)
                    wait_text(page,"#revision","4")
                    check("B9-09-real-human-browser-session-on-kernel",
                          page.locator("#revision").inner_text()=="4",
                          {"sessionAuthenticated":True})
                    page.locator("#publish").click()
                    wait_text(page,"#published-version","1")
                    pub1=broker("app-a","release.read",token_runtime,{})
                    check("B9-10-true-immutable-B2-v1-human-browser-published",
                          pub1["version"]==1 and
                          pub1["manifestHash"]==sha(pub1["definitions"]),
                          {"v1":1,"manifestSha":pub1["manifestHash"]})
                    pack1,packfile1=compiled_file("v1-preview",pub1)
                    check("B9-11-v1-Pack-compiled-only-from-hash-checked-release",
                          pack1["manifestHash"]==pub1["manifestHash"] and
                          pack1["projectionPack"]["views"][0]["configuration"][
                              "columns"]==[
                                  {"type":"Field","field_name":x,"state_field":"on"}
                                  for x in specs["view.contracts"]["columns"]],
                          {"projectionSha":pack1["projectionPackHash"],
                           "onlyModelView":pack1["projections"]})
                    corrupted=copy.deepcopy(pub1)
                    corrupted["definitions"]["view.contracts"]["title"]="EVIL"
                    try:
                        compile_release(corrupted,template)
                        tamper=False
                    except ProjectionRejected as e:
                        tamper=e.code=="RELEASE_HASH_DRIFT"
                    check("B9-12-fake-current-release-hash-mismatch-refused",
                          tamper,{"tamperRejected":True})
                    first=create_native("v1",pub1)
                    check("B9-13-real-Saltcorn-CLI-materialized-v1-view-and-table",
                          first["physical"]["viewColumns"]==specs[
                              "view.contracts"]["columns"] and
                          len(first["physical"]["businessRows"])==1 and
                          first["physical"]["businessRows"][0][
                              "contract_no"]=="HT-2026-000001",
                          {"nativeDbVersion":1,
                           "nativeView":first["physical"]["viewColumns"],
                           "rows":1})
                    check("B9-14-authority-DB-and-native-Saltcorn-DB-separate-owners",
                          mode(runtime)=="700:"+str(uids[1]) and
                          mode(first["db"])=="600:"+str(uids[1]) and
                          kernel_physical()["app-a"]["publishedVersion"]==1,
                          {"separateAuthorityDirUid":uids[0],
                           "separateSaltcornDirUid":uids[1]})
                    before_native=kernel_physical()
                    salt_base=start_saltcorn(first["db"],3139)
                    native_page=context.new_page()
                    login_native(native_page,salt_base,admin_password)
                    view_page=context.new_page()
                    view_page.goto(salt_base+"/view/s1_contract_list",
                                   wait_until="domcontentloaded")
                    rendered=view_page.content()
                    check("B9-15-genuine-Saltcorn-native-HTML-renders-v1-rows",
                          "HT-2026-000001" in rendered and
                          "s1_contract_list" in view_page.url,
                          {"httpHtml":200,"realNativeContract":True})
                    edit=context.new_page()
                    fid=first["physical"]["fieldLabels"]
                    fieldid=execute([
                        "sudo","-n","runuser","-u",RUNT,"--",
                        sys.executable,"-c",
                        "import sqlite3,sys;"
                        "c=sqlite3.connect('file:'+sys.argv[1]+'?mode=ro',uri=True);"
                        "print(c.execute(\"SELECT f.id FROM _sc_fields f JOIN "
                        "_sc_tables t ON f.table_id=t.id WHERE "
                        "t.name='s1_contracts' AND f.name='title'\").fetchone()[0])",
                        first["db"]],cwd=stage).stdout.strip()
                    edit.goto(salt_base+"/field/"+fieldid,wait_until="domcontentloaded")
                    check("B9-16-native-browser-editor-runs-only-on-derived-copy",
                          edit.locator('input[name="label"]').input_value()=="Title",
                          {"nativeFieldWizard":True,
                           "authorityHasNoSaltcornTables":True})
                    from_native=edit.locator('input[name="label"]')
                    from_native.fill("POLLUTED NATIVE RUNTIME FIELD")
                    # Complete real Saltcorn multi-step native wizard; helper
                    # is from the previously verified C2 research.
                    from browser_roundtrip import save_wizard
                    trace=[]
                    save_wizard(edit,"POLLUTED NATIVE RUNTIME FIELD",trace)
                    dirt=native_physical(first["db"])
                    check("B9-17-native-Chromium-Field-update-corrupts-only-projection",
                          dirt["fieldLabels"]["title"]==
                          "POLLUTED NATIVE RUNTIME FIELD" and len(trace)>0,
                          {"runtimeFieldCorrupted":True,
                           "nativeWizardSteps":len(trace)})
                    afterweb=kernel_physical()
                    check("B9-18-actual-authority-Manifest-Receipt-Audit-unmodified",
                          afterweb==before_native and
                          afterweb["app-a"]["revision"]==4 and
                          afterweb["app-a"]["publishedVersion"]==1 and
                          afterweb["app-b"]==start["app-b"],
                          {"authoritativeManifestUnaffected":True,
                           "runtimeWriteOnlyProjection":True})
                    # Second official dangerous native CLI mutation, without
                    # any Kernel grant; show no reverse write bridge exists.
                    cmd=native_cmd(["saltcorn","run-js","-f",
                                    stage/"native-out-of-band.js"],first["db"])
                    nativecli=native_physical(first["db"])
                    check("B9-19-real-Saltcorn-run-js-Field-update-alters-derived-only",
                          cmd.returncode==0 and
                          nativecli["fieldLabels"]["title"]=="Native Outside Gateway",
                          {"nativeCliExit":0,
                           "actualDerivedFieldChanged":True})
                    aftercli=kernel_physical()
                    check("B9-20-runtime-native-Web-and-CLI-do-not-enter-core-Audits",
                          aftercli==afterweb and
                          aftercli["app-a"]["resourceHashesValid"] and
                          aftercli["app-a"]["releaseHashesValid"],
                          {"b2AuthoritySamePhysicalSnapshot":True,
                           "sourceReleaseStillVerified":True})
                    # Probe Pack import as a native command, on a disposable
                    # version. Whether Saltcorn overwrites or rejects is
                    # measured; it must never alter authority.
                    salt_pack=native_cmd(["saltcorn","install-pack","-f",
                                          packfile1],first["db"],
                                         strict=False,timeout=150)
                    afterpack=kernel_physical()
                    check("B9-21-native-Pack-actions-have-no-authority-side-effect",
                          afterpack==aftercli,
                          {"nativePackExit":salt_pack.returncode,
                           "authorityUnaffected":True,
                           "doNotClaimPackSucceeded":salt_pack.returncode!=0})
                    stop_runtime()
                    # Rebuild an unpoisoned clean copy from immutable v1.
                    clean=create_native("v1rebuild",pub1)
                    check("B9-22-deleting-attacked-runtime-allows-deterministic-rebuild",
                          clean["compiled"]["projectionPackHash"]==
                          first["compiled"]["projectionPackHash"] and
                          clean["physical"]["fieldLabels"]["title"]=="Title" and
                          clean["physical"]["viewColumns"]==
                          first["physical"]["viewColumns"],
                          {"projectionHashIdentical":True,
                           "nativeCorruptionRemoved":True})
                    native_cmd(["/usr/bin/rm","-f",first["db"]],first["db"])
                    gone=native_cmd(["/usr/bin/test","!","-e",first["db"]],
                                    clean["db"])
                    check("B9-23-actual-tainted-Saltcorn-database-disposable",
                          gone.returncode==0 and
                          kernel_physical()==aftercli,
                          {"taintedDatabaseRemoved":True,
                           "authorityStillPresent":True})
                    # Publish v2: a real B2 view definition change changes
                    # the deployed native Saltcorn *column config*.
                    snap2=broker("app-a","draft.read",token_agent,{})
                    newview=copy.deepcopy(
                        snap2["resources"]["view.contracts"]["definition"])
                    newview["columns"]=[
                        "contract_no","title","amount_minor","status"]
                    change=make_mutation(snap2,"view.contracts",newview,
                                         "b9-v2-view-column-change")
                    updated=broker("app-a","metadata.upsert",token_agent,
                                   {"command":change})
                    check("B9-24-governed-Agent-v2-View-CAS-writes-only-authority",
                          updated["appRevision"]==5 and
                          kernel_physical()["app-a"]["revision"]==5,
                          {"appRevision":5})
                    page.locator("#reload").click()
                    wait_text(page,"#revision","5")
                    page.locator("#publish").click()
                    wait_text(page,"#published-version","2")
                    pub2=broker("app-a","release.read",token_runtime,{})
                    check("B9-25-human-approved-v2-immutable-release-is-distinct",
                          pub2["version"]==2 and
                          pub2["manifestHash"]!=pub1["manifestHash"] and
                          pub2["definitions"]["view.contracts"]["columns"]==
                          newview["columns"],
                          {"v2Manifest":pub2["manifestHash"],
                           "changedFields":newview["columns"]})
                    second=create_native("v2",pub2)
                    check("B9-26-real-v2-Saltcorn-physical-View-columns-changed",
                          second["physical"]["viewColumns"]==
                          newview["columns"] and
                          second["compiled"]["projectionPackHash"]!=
                          first["compiled"]["projectionPackHash"],
                          {"v1Columns":first["physical"]["viewColumns"],
                           "v2Columns":second["physical"]["viewColumns"]})
                    v2base=start_saltcorn(second["db"],3139)
                    v2page=context.new_page()
                    v2page.goto(v2base+"/view/s1_contract_list",
                                wait_until="domcontentloaded")
                    v2html=v2page.content()
                    check("B9-27-native-v2-browser-real-contract-present",
                          "HT-2026-000001" in v2html and
                          second["physical"]["businessRows"][0][
                              "title"]=="S1 Platform Contract",
                          {"nativeViewRows":1,"actualV2Columns":True})
                    stop_runtime()
                    rollback=broker("app-a","app.rollback",token_publisher,{
                        "command":{"changeId":"b9-human-rollback-v2-to-v1",
                                   "expectedPublishedVersion":2,
                                   "targetVersion":1}})
                    check("B9-28-trusted-Kernel-CAS-rolls-back-authority-pointer",
                          rollback["decision"]=="ROLLED_BACK" and
                          rollback["version"]==1 and
                          kernel_physical()["app-a"]["publishedVersion"]==1,
                          {"restoredVersion":1})
                    replay=broker("app-a","release.read",token_runtime,{})
                    check("B9-29-verified-release-read-after-rollback-matches-v1",
                          replay["manifestHash"]==pub1["manifestHash"] and
                          replay["definitions"]==pub1["definitions"],
                          {"sourceShaRestored":pub1["manifestHash"]})
                    restored=create_native("rollback-v1",replay)
                    check("B9-30-real-Saltcorn-rebuilt-v1-view-after-rollback",
                          restored["compiled"]["projectionPackHash"]==
                          first["compiled"]["projectionPackHash"] and
                          restored["physical"]["viewColumns"]==
                          first["physical"]["viewColumns"] and
                          restored["physical"]["fieldLabels"]["title"]=="Title",
                          {"rollbackNativeColumns":
                           restored["physical"]["viewColumns"],
                           "nativeCorruptionAbsent":True})
                    v1again=start_saltcorn(restored["db"],3139)
                    page_again=context.new_page()
                    page_again.goto(v1again+"/view/s1_contract_list",
                                    wait_until="domcontentloaded")
                    check("B9-31-actual-Saltcorn-browser-renders-rolled-back-v1",
                          "HT-2026-000001" in page_again.content(),
                          {"realBrowserOnRollback":True,"http":200})
                    rejected=broker("app-a","app.rollback",token_publisher,{
                        "command":{"changeId":"b9-rollback-stale-pointer",
                                   "expectedPublishedVersion":2,
                                   "targetVersion":1}},expect=409)
                    check("B9-32-stale-rollback-CAS-denied-no-pointer-change",
                          rejected["error"]=="PUBLISH_POINTER_CONFLICT" and
                          kernel_physical()["app-a"]["publishedVersion"]==1,
                          {"http":409,"verifiedPointerStill":1})
                    bcheck=kernel_physical()
                    check("B9-33-other-application-has-zero-cross-app-effects",
                          bcheck["app-b"]==start["app-b"] and
                          bcheck["app-b"]["releases"]==0,
                          {"otherAppEmpty":True,
                           "independentAuthority":True})
                    check("B9-34-release-v1-and-v2-preserved-immutable-after-rollback",
                          bcheck["app-a"]["releases"]==2 and
                          bcheck["app-a"]["releaseHashesValid"] and
                          bcheck["app-a"]["resourceHashesValid"],
                          {"verifiedReleaseCount":2,
                           "activeVersion":1})
                    check("B9-35-published-View-only-no-false-workflow-code-parity",
                          first["compiled"]["notProjected"]==[
                              "form.contracts","workflow.approval","B4 code"] and
                          restored["compiled"]["projections"]==[
                              "model.contracts","view.contracts"],
                          {"scope":"native Model/View only",
                           "excluded":["form","workflow","code"]})
                    check("B9-36-kernel-is-sole-authority-runtime-no-reverse-sync",
                          bcheck["app-a"]["publishedVersion"]==1 and
                          restored["db"]!=db and
                          restored["compiled"]["manifestHash"]==
                          pub1["manifestHash"] and
                          bcheck["app-a"]["revision"]==5,
                          {"authorityRevision":5,
                           "activeSourceReleaseVersion":1,
                           "disposableRuntime":True})
                    # P0-A: all probes use the very same live B9 authority
                    # and Saltcorn v1; no independent service or test reset.
                    plugin_probe=plugin({
                        "kind":"probe","authorityDb":str(db),
                        "authorityConfig":str(config)})
                    check("P0A-01-plugin-UID-physical-DAC-denial",
                          all(plugin_probe[k]=="DENIED" for k in (
                              "authorityRead","authorityWrite",
                              "authoritySQLWrite","authorityConfigRead")),
                          plugin_probe)
                    before_three=kernel_physical()
                    plugin_draft=plugin_tool("app-a","draft.read",{})
                    check("P0A-02-plugin-reads-same-authority",
                          plugin_draft["status"]==200 and
                          plugin_draft["body"]["appRevision"]==5 and
                          plugin_draft["body"]["publishedVersion"]==1,
                          {"readHTTP":plugin_draft["status"],"revision":5})
                    denied_model=plugin_tool("app-a","metadata.upsert",{
                        "command":make_mutation(
                            plugin_draft["body"],"model.contracts",
                            plugin_draft["body"]["resources"][
                                "model.contracts"]["definition"],
                            "p0a-plugin-should-not-edit-model")})
                    denied_publish=plugin_tool("app-a","app.publish",{
                        "command":{}})
                    denied_cross=plugin_tool("app-b","draft.read",{})
                    check("P0A-03-plugin-least-privilege-and-cross-app",
                          denied_model["status"]==403 and
                          denied_publish["status"]==403 and
                          denied_cross["status"]==403 and
                          kernel_physical()==before_three,
                          {"modelWrite":denied_model["status"],
                           "publish":denied_publish["status"],
                           "crossApp":denied_cross["status"],
                           "noSqlEffects":True})
                    concurrent=broker("app-a","draft.read",token_agent,{})
                    agent_def=copy.deepcopy(concurrent["resources"][
                        "view.contracts"]["definition"])
                    plugin_def=copy.deepcopy(agent_def)
                    agent_def["title"]="P0A Agent Revision"
                    plugin_def["title"]="P0A Plugin Revision"
                    agent_change=make_mutation(
                        concurrent,"view.contracts",agent_def,
                        "p0a-agent-view-race")
                    plugin_change=make_mutation(
                        concurrent,"view.contracts",plugin_def,
                        "p0a-plugin-view-race")
                    with ThreadPoolExecutor(max_workers=2) as pool:
                        future_agent=pool.submit(
                            http,base,"app-a","metadata.upsert",
                            token_agent,{"command":agent_change})
                        future_plugin=pool.submit(
                            plugin_tool,"app-a","metadata.upsert",
                            {"command":plugin_change})
                        agent_result=future_agent.result()
                        plugin_result=future_plugin.result()
                    statuses=sorted([agent_result[0],plugin_result["status"]])
                    winner=(agent_def if agent_result[0]==200 else plugin_def)
                    after_three=kernel_physical()
                    check("P0A-04-agent-plugin-race-one-CAS-winner",
                          statuses==[200,409] and
                          after_three["app-a"]["resources"][
                              "view.contracts"]["title"]==winner["title"],
                          {"agentHTTP":agent_result[0],
                           "pluginHTTP":plugin_result["status"],
                           "oneWinner":statuses==[200,409]})
                    check("P0A-05-physical-one-receipt-release-unchanged",
                          after_three["app-a"]["revision"]==6 and
                          after_three["app-a"]["receipts"]==
                              before_three["app-a"]["receipts"]+1 and
                          len(after_three["app-a"]["events"])==
                              len(before_three["app-a"]["events"])+1 and
                          after_three["app-a"]["publishedVersion"]==1 and
                          after_three["app-a"]["releases"]==2 and
                          after_three["app-a"]["resourceHashesValid"] and
                          after_three["app-a"]["releaseHashesValid"] and
                          after_three["app-a"]["manifestMatches"] and
                          after_three["app-b"]==before_three["app-b"],
                          {"revision":after_three["app-a"]["revision"],
                           "receiptDelta":after_three["app-a"]["receipts"]-
                               before_three["app-a"]["receipts"],
                           "publishedVersion":1,"appBUnchanged":True})
                    if agent_result[0]==200:
                        replay_http,replay_body=http(
                            base,"app-a","metadata.upsert",token_agent,
                            {"command":agent_change})
                    else:
                        replay=plugin_tool("app-a","metadata.upsert",
                                           {"command":plugin_change})
                        replay_http,replay_body=replay["status"],replay["body"]
                    page_again.reload(wait_until="domcontentloaded")
                    check("P0A-06-idempotent-replay-native-still-old-release",
                          replay_http==200 and replay_body.get("replayed") is True
                          and kernel_physical()==after_three and
                          native_physical(restored["db"])["viewColumns"]==
                              first["physical"]["viewColumns"] and
                          "HT-2026-000001" in page_again.content(),
                          {"replayHTTP":replay_http,
                           "noAdditionalReceipt":True,
                           "nativeStillPublishedV1":True})
                    next_round = run_suite(
                        context=context, base=base, token_agent=token_agent,
                        plugin_tool=plugin_tool, http=http,
                        physical=kernel_physical,
                        make_mutation=make_mutation, check=check,
                        native_page=page_again,
                        native_physical=native_physical,
                        native_db=restored["db"],
                        expected_native_columns=first["physical"]["viewColumns"])
                    evidence["p0a_web"]=next_round
                    docker_round = run_docker_suite(
                        context=context, base=base,
                        token_plugin=token_plugin, token_agent=token_agent,
                        authority_db=db, authority_config=config,
                        native_db=restored["db"], native_page=page_again,
                        native_physical=native_physical, physical=kernel_physical,
                        http=http, make_mutation=make_mutation, check=check)
                    evidence["p0a_docker"]=docker_round
                    evidence["p0a"]={
                        "scope":"same B9 kernel, plugin UID, Agent and Native",
                        "originalB9Checks":36,"additionalChecks":24,
                        "pluginDockerSandboxValidated":True,
                        "pluginInstallerOrRevocationValidated":False,
                        "nativePackFullDiffApprovalValidated":False,
                        "formalWOrTCFullPass":False}
                    evidence["final"]={
                        "v1ManifestHash":pub1["manifestHash"],
                        "v2ManifestHash":pub2["manifestHash"],
                        "v1ProjectionHash":first["compiled"]["projectionPackHash"],
                        "v2ProjectionHash":second["compiled"]["projectionPackHash"],
                        "activeRelease":1,
                        "authorityAppARevision":kernel_physical()["app-a"]["revision"],
                        "authorityAppBRevision":0,
                        "physicalSaltcornNativeWebBypassContained":True,
                        "physicalSaltcornNativeCliBypassContained":True,
                        "codeWorkflowParityValidated":False,
                        "externalEffectsRollbackValidated":False
                    }
                finally:
                    context.close()
                    browser.close()
        finally:
            stop_runtime()
            execute(["sudo","-n","pkill","-TERM","-u",KERN],
                    strict=False,timeout=8)
            if kernelproc:
                try:kernelproc.wait(timeout=7)
                except subprocess.TimeoutExpired:kernelproc.terminate()
            # The trusted CI orchestrator cleans each OS-owned private dir,
            # not Agent or Saltcorn user with access to Kernel private DB.
            execute(["sudo","-n","chown","-R",
                     str(os.getuid())+":"+str(os.getgid()),
                     authority,runtime,ready],strict=False,timeout=12)
            evidence["summary"]={
                "passed":sum(x["status"]=="PASS" for x in evidence["checks"]),
                "attempted":len(evidence["checks"]),
                "expected":60,
                "modelCalls":0,"g1Passed":False
            }
            Path(args.output).write_text(json.dumps(
                evidence,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            print("S1_B9_RESULT "+
                  json.dumps(evidence["summary"],ensure_ascii=False),
                  flush=True)
    return 0 if len(evidence["checks"])==60 and all(
        x["status"]=="PASS" for x in evidence["checks"]) else 1


if __name__=="__main__":
    raise SystemExit(main())
