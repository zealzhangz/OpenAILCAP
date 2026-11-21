#!/usr/bin/env python3
"""B8: real Saltcorn native Field.update / Pack / Web route vs Linux DAC.

This is a *negative control study* of Saltcorn @saltcorn/cli@1.7.0-beta.5.
A dedicated Saltcorn DB-owner Linux UID prevents separate unprivileged CLI
processes from opening that database. However an authentic Saltcorn web
editor and native Field.update/Pack run under THE OWNER UID can still write
the database without the research CAS gateway, so this C2 approach does NOT
close G1-B01. No pretending patched web paths have full coverage.

All operations run on an isolated disposable SQLite and test-only admin.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import pwd
import secrets
import shutil
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
ROOT=HERE.parent
sys.path.insert(0,str(ROOT/"platform-saltcorn"/"browser"))
from browser_roundtrip import save_wizard

KERNEL="ailcapb8core"
PLUGIN="ailcapb8plug"
SOURCE="S1_B8_PLAIN_SALTCORN_NATIVE_ENTRIES_REAL_DAC"


def subprocess_run(argv,cwd,env,timeout=100):
    return subprocess.run(argv,cwd=str(cwd),env=env,text=True,
                          capture_output=True,check=False,timeout=timeout)


def command(user,argv,cwd,env,timeout=110):
    # Arguments are native Saltcorn CLI commands, not mocks.
    # OS umask is applied inside the actual owner/guest user process.
    args=["sudo","-n","runuser","-u",user,"--",
          "/bin/bash","-c",'umask 077; exec "$@"',"s1-b8",*argv]
    return subprocess_run(args,cwd,env,timeout=timeout)


def cli_observation(result):
    # Never print command args, tokens, admin password, or raw CLI exception.
    # The raw stderr may contain secrets; only publish limited classification.
    t=(result.stderr+"\n"+result.stdout).lower()
    return {"returnCode":result.returncode,
            "permissionError":("permission denied" in t or "eacces" in t or
                               "sqlite_cantopen" in t or
                               "unable to open database file" in t),
            "nativeCliInvoked":True}


def single_json(text,prefix):
    lines=[x.partition("|")[2] for x in text.splitlines()
           if x.startswith(prefix+"|")]
    if len(lines)!=1:raise AssertionError("EXPECTED_ONE_"+prefix)
    return json.loads(lines[0])


def get_http(base,path,token=None,body=None):
    headers={"Content-Type":"application/json"} if body is not None else {}
    if token:headers["Authorization"]="Bearer "+token
    req=Request(base+path,method="POST" if body is not None else "GET",
                headers=headers,
                data=None if body is None else json.dumps(body).encode())
    try:
        with urlopen(req,timeout=20) as r:
            return r.status,json.loads(r.read(32768))
    except HTTPError as e:
        return e.code,json.loads(e.read(32768))


def wait_port(base,path,timeout=60):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        try:
            with urlopen(base+path,timeout=2) as r:
                if r.status==200:return True
        except Exception:pass
        time.sleep(.2)
    return False


def uid_probe(db,config):
    # OS-level checks run with genuine untrusted Plugin Linux uid.
    snippet=("import os,sqlite3,json,sys;"
             "p=sys.argv[1];c=sys.argv[2];"
             "defx=lambda f: f;" # a simple no-op for deterministic interpreter
             "\n"
             "def access(path,flags):\n"
             " try:\n"
             "  fd=os.open(path,flags);os.close(fd);return 'OPENED'\n"
             " except OSError:return 'DENIED'\n"
             "\n"
             "def sql(path):\n"
             " try:\n"
             "  conn=sqlite3.connect('file:'+path+'?mode=rw',uri=True,timeout=.2)\n"
             "  conn.execute('UPDATE _sc_fields SET label=label');conn.commit()\n"
             "  conn.close();return 'UPDATED'\n"
             " except (sqlite3.Error,OSError):return 'DENIED'\n"
             "\n"
             "print('S1_B8_OS|'+json.dumps({'uid':os.getuid(),"
             "'dbRead':access(p,os.O_RDONLY),"
             "'dbWrite':access(p,os.O_RDWR),"
             "'configRead':access(c,os.O_RDONLY),"
             "'actualNativeSQLiteUpdate':sql(p)}))")
    # string only, no privileged reference/token shared into process.
    return snippet


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",required=True)
    options=parser.parse_args()
    result={
        "name":SOURCE,"platform":"@saltcorn/cli@1.7.0-beta.5",
        "realSaltcornBrowser":True,"realNativeFieldUpdate":True,
        "realPackImport":True,"modelCalls":0,
        "allNativeSaltcornPathsForcedThroughDomainKernel":False,
        "g1Passed":False,"checks":[]}
    def check(name,ok,value):
        record={"id":name,"status":"PASS" if ok else "FAIL","observed":value}
        result["checks"].append(record)
        print("B8 "+name+" "+record["status"]+" "+
              json.dumps(value,ensure_ascii=False),flush=True)
        if not ok:raise AssertionError(name)

    uid0=pwd.getpwnam(KERNEL).pw_uid
    uid1=pwd.getpwnam(PLUGIN).pw_uid
    check("B8-01-distinct-real-nonroot-Saltcorn-owner-and-native-CLI-users",
          uid0>0 and uid1>0 and uid0!=uid1 and os.geteuid()!=uid0,
          {"ownerUid":uid0,"nativePluginUid":uid1})
    with tempfile.TemporaryDirectory(prefix="s1-b8-saltcorn-") as rootstr:
        root=Path(rootstr);root.chmod(0o755)
        stage=root/"source";stage.mkdir(mode=0o755)
        private=root/"private";private.mkdir(mode=0o700)
        ready=root/"ready";ready.mkdir(mode=0o755)
        db=private/"native-saltcorn.sqlite"
        config=private/"gateway-config.json"
        gateway_ready=ready/"gateway-ready.json"
        gateway_log=root/"gateway.log"
        salt_log=root/"saltcorn.log"
        source={
            "gateway.py":ROOT/"platform-saltcorn"/"governed"/"gateway.py",
            "native-out-of-band.js":ROOT/"platform-saltcorn"/"governed"/"native-out-of-band.js",
            "contract-pack.json":ROOT/"platform-saltcorn"/"contract-pack.json",
            "seed-contract.js":ROOT/"platform-saltcorn"/"seed-contract.js",
            "gateway_service.py":HERE/"gateway_service.py",
            "native_http_client.py":HERE/"native_http_client.py",
            "physical_native_oracle.py":HERE/"physical_native_oracle.py"
        }
        for name,path in source.items():
            path2=stage/name;shutil.copyfile(path,path2);path2.chmod(0o644)
        salt_secret=secrets.token_urlsafe(44)
        admin_password=secrets.token_urlsafe(34)
        agent_token=secrets.token_urlsafe(44)
        readonly_token=secrets.token_urlsafe(44)
        human_password=secrets.token_urlsafe(44)
        config.write_text(json.dumps({
            "db":str(db),"humanPassword":human_password,
            "agentToken":agent_token,"readToken":readonly_token
        }),encoding="utf-8")
        config.chmod(0o600)
        setup=subprocess_run(["sudo","-n","chown","-R",
                             KERNEL+":"+KERNEL,str(private),str(ready)],
                            root,os.environ.copy())
        if setup.returncode:raise AssertionError("CHOWN_OWNER_FAILED")
        pathenv=os.environ.copy()
        pathenv.update({"SQLITE_FILEPATH":str(db),
                        "SALTCORN_SESSION_SECRET":salt_secret,
                        "SALTCORN_NWORKERS":"1","HOME":str(private)})
        pluginenv=os.environ.copy()
        pluginenv.update({"SQLITE_FILEPATH":str(db),
                          # Even with Saltcorn auth secret known, actual DAC
                          # must deny native CLI direct SQLite access.
                          "SALTCORN_SESSION_SECRET":salt_secret,
                          "SALTCORN_NWORKERS":"1","HOME":str(root)})
        owner_srv=None;gateway_srv=None
        try:
            def owner_native(args,timeout=110):
                return command(KERNEL,args,stage,pathenv,timeout)
            def plugin_native(args,timeout=80):
                return command(PLUGIN,args,stage,pluginenv,timeout)
            def physical():
                r=command(KERNEL,[
                    sys.executable,str(stage/"physical_native_oracle.py"),
                    "--db",str(db)],stage,pathenv,timeout=12)
                if r.returncode:raise RuntimeError("PHYSICAL_SQL_READ_FAILED")
                return single_json(r.stdout,"S1_B8_PHYSICAL")
            def native_tool(token,method,path,payload=None):
                args={"base":gateway_base,"token":token,
                      "method":method,"path":path,"body":payload}
                r=command(PLUGIN,[sys.executable,
                          str(stage/"native_http_client.py")],
                          stage,pluginenv,timeout=15) if False else None
                # Run a genuinely distinct process as untrusted plugin UID.
                proc=subprocess_run([
                    "sudo","-n","runuser","-u",PLUGIN,"--",
                    sys.executable,str(stage/"native_http_client.py")
                ],stage,pluginenv,timeout=15) if False else None
                proc=subprocess.run([
                    "sudo","-n","runuser","-u",PLUGIN,"--",
                    sys.executable,str(stage/"native_http_client.py")
                ],input=json.dumps(args,ensure_ascii=False)+"\n",
                  cwd=str(stage),env=pluginenv,text=True,
                  capture_output=True,timeout=15,check=False)
                if proc.returncode:
                    raise RuntimeError("NATIVE_TOOL_PROCESS_FAILED")
                return single_json(proc.stdout,"S1_B8_TOOL")
            # FIXTURE: the real Saltcorn package with genuine native SQLite.
            reset=owner_native(["saltcorn","reset-schema","-f"],timeout=150)
            check("B8-02-real-Saltcorn-owner-reset-schema-native",
                  reset.returncode==0 and db.exists(),
                  {"officialCliExit":reset.returncode,"actualSqlite":db.exists()})
            pack=owner_native(["saltcorn","install-pack","-f",
                               str(stage/"contract-pack.json")],timeout=150)
            seed=owner_native(["saltcorn","run-js","-f",
                               str(stage/"seed-contract.js")],timeout=110)
            original=physical()
            check("B8-03-owner-native-Pack-and-Table-insert-really-run",
                  pack.returncode==0 and seed.returncode==0 and
                  original["fieldLabel"]=="Title" and
                  original["nativeRowCount"]==1,
                  {"packExit":pack.returncode,"seedExit":seed.returncode,
                   "label":original["fieldLabel"],"contractRows":1})
            mode=subprocess_run(["sudo","-n","stat","-c","%a:%u",
                                str(private)],stage,os.environ.copy())
            priv_mode=mode.stdout.strip()
            check("B8-04-real-private-directory-owner-0700",
                  priv_mode==("700:"+str(uid0)),
                  {"privateDir":priv_mode,"databaseInside":True})
            probe=subprocess_run(["sudo","-n","runuser","-u",PLUGIN,"--",
                                  sys.executable,"-c",uid_probe(db,config),
                                  str(db),str(config)],stage,pluginenv)
            attempted=single_json(probe.stdout,"S1_B8_OS")
            check("B8-05-untrusted-native-Plugin-real-OS-direct-SQL-denied",
                  probe.returncode==0 and attempted["uid"]==uid1 and
                  all(attempted[k]=="DENIED" for k in (
                      "dbRead","dbWrite","configRead",
                      "actualNativeSQLiteUpdate")),
                  attempted)
            native_bypass=plugin_native([
                "saltcorn","run-js","-f",
                str(stage/"native-out-of-band.js")])
            after_direct=physical()
            check("B8-06-actual-Saltcorn-Field-update-CLI-denied-by-OS",
                  native_bypass.returncode!=0 and
                  after_direct["fieldLabel"]=="Title" and
                  after_direct["nativeRowCount"]==1,
                  {"cli":cli_observation(native_bypass),
                   "physicalLabel":after_direct["fieldLabel"]})
            attempted_pack=plugin_native([
                "saltcorn","install-pack","-f",
                str(stage/"contract-pack.json")])
            after_pack=physical()
            check("B8-07-actual-Saltcorn-install-Pack-denied-by-OS",
                  attempted_pack.returncode!=0 and
                  after_pack==after_direct,
                  {"cli":cli_observation(attempted_pack),
                   "nativeFieldUnchanged":True})
            check("B8-08-real-Saltcorn-DB-unchanged-by-native-CLI-attacks",
                  original==after_pack,
                  {"physicalSnapshotsEqual":True,"contractRows":1})
            # Trusted gateway is a separate OS process WITH THE SAME
            # Saltcorn DB-owner UID. Its own research write contract is
            # atomic, but the native Saltcorn web route remains uncovered.
            with gateway_log.open("w") as output:
                gateway_srv=subprocess.Popen([
                    "sudo","-n","runuser","-u",KERNEL,"--",
                    sys.executable,"-u",str(stage/"gateway_service.py"),
                    "--config",str(config),"--ready",str(gateway_ready)
                ],cwd=str(stage),env=pathenv,stdout=output,
                  stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL)
            for _ in range(130):
                if gateway_ready.is_file():break
                if gateway_srv.poll() is not None:
                    raise RuntimeError("GATEWAY_DIED "+
                                       gateway_log.read_text()[-700:])
                time.sleep(.08)
            if not gateway_ready.exists():raise RuntimeError("GATEWAY_NOT_READY")
            metadata=json.loads(gateway_ready.read_text())
            gateway_base="http://127.0.0.1:"+str(metadata["port"])
            check("B8-09-real-governed-Saltcorn-gateway-runs-under-owner-UID",
                  metadata["uid"]==uid0 and
                  wait_port(gateway_base,"/health",timeout=12),
                  {"gatewayOwnerUid":metadata["uid"],
                   "host":"127.0.0.1"})
            resource="/api/apps/s1-contract/resources/title"
            unauth=get_http(gateway_base,resource)
            check("B8-10-unauthenticated-tool-gateway-rejects",
                  unauth==(401,{"error":"AUTH_REQUIRED"}),
                  {"http":unauth[0]})
            state=native_tool(agent_token,"GET",resource)
            check("B8-11-different-host-UID-can-read-scoped-governed-tool",
                  state["http"]==200 and
                  state["data"]["revision"]==0 and
                  state["data"]["label"]=="Title",
                  {"http":state["http"],"revision":0,
                   "differentHostUid":True})
            read_only=native_tool(readonly_token,"POST",resource,{
                "change_id":"b8_readonly-denied",
                "label":"SHOULD NOT BE WRITTEN",
                "base_revision":0,
                "base_fingerprint":state["data"]["fingerprint"]})
            check("B8-12-readonly-token-cannot-write-real-Saltcorn-metadata",
                  read_only["http"]==403 and
                  read_only["data"].get("error")=="READ_ONLY" and
                  physical()["fieldLabel"]=="Title",
                  {"http":403,"unchangedLabel":True})
            cross=native_tool(agent_token,"GET",
                               "/api/apps/other-app/resources/title")
            check("B8-13-native-Plugin-bearer-cannot-cross-app",
                  cross["http"]==403 and
                  cross["data"].get("error")=="APP_FORBIDDEN",
                  {"http":403})
            correct={
                "change_id":"b8-authorized-plugin-edit-0001",
                "label":"Governed by Native Client",
                "base_revision":0,
                "base_fingerprint":state["data"]["fingerprint"]
            }
            accepted=native_tool(agent_token,"POST",resource,correct)
            accepted_db=physical()
            check("B8-14-unprivileged-Plugin-edits-native-Field-via-governed-API",
                  accepted["http"]==200 and
                  accepted_db["fieldLabel"]=="Governed by Native Client" and
                  accepted_db["revision"]==1 and
                  accepted_db["changes"]==1 and
                  accepted_db["nativeRowCount"]==1,
                  {"http":200,"physicalLabel":accepted_db["fieldLabel"],
                   "version":1,"successfulChanges":1})
            stale=dict(correct)
            stale["change_id"]="b8-stale-unauthorized-agent-0001"
            stale["label"]="Stale Value Must Not Win"
            stale_attempt=native_tool(agent_token,"POST",resource,stale)
            check("B8-15-old-native-Agent-CAS-conflict-409-with-no-write",
                  stale_attempt["http"]==409 and
                  physical()["fieldLabel"]==accepted_db["fieldLabel"],
                  {"http":409,"governedLabelKept":True})
            again=native_tool(agent_token,"POST",resource,correct)
            check("B8-16-identical-Plugin-replay-does-not-add-receipts",
                  again["http"]==200 and
                  again["data"].get("replayed") is True and
                  physical()["changes"]==1,
                  {"http":200,"replayed":True,"receiptCount":1})
            # CRITICAL: launching actual Saltcorn native WEB under owner UID
            # still permits Field.update via /field/:id without the Gateway.
            admin=owner_native([
                "saltcorn","create-user","--admin",
                "--email","s1-research-admin@example.invalid",
                "--password",admin_password],timeout=90)
            check("B8-17-real-native-Saltcorn-admin-created-for-browser",
                  admin.returncode==0 and
                  physical()["fieldLabel"]==accepted_db["fieldLabel"],
                  {"saltcornCreateUserExit":admin.returncode,
                   "noDatabaseLabelChange":True})
            salt_base="http://127.0.0.1:3108"
            with salt_log.open("w") as output:
                owner_srv=subprocess.Popen([
                    "sudo","-n","runuser","-u",KERNEL,"--",
                    "saltcorn","serve","--port","3108","--noscheduler"
                ],cwd=str(stage),env=pathenv,stdout=output,
                  stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL)
            if not wait_port(salt_base,"/auth/login",timeout=100):
                raise RuntimeError("REAL_SALTCORN_SERVER_NOT_READY "+
                                   salt_log.read_text()[-800:])
            check("B8-18-native-Saltcorn-Web-starts-with-protected-DB-owner",
                  owner_srv.poll() is None and
                  physical()["fieldLabel"]==accepted_db["fieldLabel"],
                  {"nativeWebHttp":200,"ownerUid":uid0})
            with sync_playwright() as pw:
                browser=pw.chromium.launch(headless=True,
                                            args=["--no-sandbox"])
                ctx=browser.new_context()
                try:
                    page=ctx.new_page()
                    page.goto(salt_base+"/auth/login",
                              wait_until="domcontentloaded")
                    page.locator('input[name="email"]').fill(
                        "s1-research-admin@example.invalid")
                    page.locator('input[name="password"]').fill(admin_password)
                    page.locator('form[action="/auth/login"] button[type="submit"], form[action="/auth/login"] input[type="submit"]').last.click()
                    page.wait_for_load_state("domcontentloaded")
                    fid=physical()["fieldId"]
                    edit=ctx.new_page()
                    edit.goto(salt_base+"/field/"+str(fid),
                              wait_until="domcontentloaded")
                    seen=edit.locator('input[name="label"]').input_value()
                    check("B8-19-real-Chromium-Saltcorn-native-Field-edit-form",
                          seen=="Governed by Native Client" and
                          edit.locator('input[name="contextEnc"]').count()>0,
                          {"nativeEditorField":seen,"nativeWizard":True})
                    trace=[]
                    save_wizard(edit,"Native Web Outside Gateway",trace)
                    native_saved=physical()
                    check("B8-20-critical-native-Web-Field-update-bypasses-CAS",
                          native_saved["fieldLabel"]==
                          "Native Web Outside Gateway" and
                          native_saved["revision"]==1 and
                          native_saved["changes"]==1 and
                          len(trace)>0,
                          {"dangerousNativeWebWriteSucceeded":True,
                           "realGatewayRevisionStill":1,
                           "actualBrowserWizardSteps":len(trace)})
                finally:
                    ctx.close()
                    browser.close()
            drift=native_tool(agent_token,"GET",resource)
            check("B8-21-gateway-detects-native-Web-out-of-band-drift",
                  drift["http"]==409 and
                  drift["data"].get("error")=="OUT_OF_BAND_DRIFT",
                  {"http":409,"type":"OUT_OF_BAND_DRIFT"})
            attempted_gov=native_tool(agent_token,"POST",resource,{
                "change_id":"b8-after-native-web-drift",
                "label":"Cannot Overwrite Native Web",
                "base_revision":1,
                "base_fingerprint":accepted["data"]["fingerprint"]})
            frozen=physical()
            check("B8-22-Agent-tool-write-fails-closed-after-native-Web-drift",
                  attempted_gov["http"]==409 and
                  frozen["fieldLabel"]=="Native Web Outside Gateway" and
                  frozen["revision"]==1 and frozen["changes"]==1,
                  {"governedWriteRejected":409,"ledgerNotFalselyAdvanced":True})
            # Real official CLI with SAME owner UID: explicit native bypass
            # shows why Linux DAC cannot substitute for native entry gating.
            owner_bypass=owner_native([
                "saltcorn","run-js","-f",
                str(stage/"native-out-of-band.js")],timeout=100)
            after_owner=physical()
            check("B8-23-owner-native-Field-update-still-bypasses-all-HTTP-policy",
                  owner_bypass.returncode==0 and
                  after_owner["fieldLabel"]=="Native Outside Gateway" and
                  after_owner["revision"]==1 and
                  after_owner["changes"]==1,
                  {"ownerNativeFieldUpdateExit":owner_bypass.returncode,
                   "physicalWriteSucceeded":True,"CASLedgerUnchanged":True})
            final_drift=native_tool(agent_token,"GET",resource)
            check("B8-24-final-real-API-fail-closed-and-data-retained",
                  final_drift["http"]==409 and
                  final_drift["data"].get("error")=="OUT_OF_BAND_DRIFT" and
                  physical()["nativeRowCount"]==1 and
                  physical()["fieldLabel"]=="Native Outside Gateway",
                  {"http":409,"nativeContractsRemain":1,
                   "nativeWriteEntrypointsStillOpen":["web.field","cli.Field.update"],
                   "formalW11_W16Passed":False})
            result["finalFinding"]={
                "nativePluginCliDifferentUidBlocked":True,
                "nativeInstallPackDifferentUidBlocked":True,
                "saltcornNativeWebSameUidBypassesGuard":True,
                "saltcornNativeCliSameUidBypassesGuard":True,
                "outOfBandDriftDetected":True,
                "g1B01StillOpen":True
            }
        finally:
            # Trusted CI controller; NEVER grant sudo to native plugin/Agent.
            subprocess.run(["sudo","-n","pkill","-TERM","-u",KERNEL],
                           text=True,capture_output=True,timeout=7,check=False)
            for proc in (owner_srv,gateway_srv):
                if proc:
                    try:proc.wait(timeout=4)
                    except subprocess.TimeoutExpired:proc.terminate()
            subprocess.run(["sudo","-n","chown","-R",
                            str(os.getuid())+":"+str(os.getgid()),
                            str(private),str(ready)],
                           text=True,capture_output=True,timeout=10,check=False)
            result["summary"]={
                "passed":sum(x["status"]=="PASS" for x in result["checks"]),
                "attempted":len(result["checks"]),
                "expected":24,"modelCalls":0,"formalG1Passed":False
            }
            Path(options.output).write_text(
                json.dumps(result,ensure_ascii=False,indent=2)+"\n",
                encoding="utf-8")
            print("S1_B8_RESULT "+json.dumps(result["summary"]),flush=True)
    return 0 if len(result["checks"])==24 and all(
        x["status"]=="PASS" for x in result["checks"]) else 1


if __name__=="__main__":
    raise SystemExit(main())
