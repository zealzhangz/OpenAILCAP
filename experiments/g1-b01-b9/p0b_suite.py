"""P0-B real end-to-end B2→B14→B15→B17 on the SAME B9 live instance.

No new Kernel/database. Genuine Kernel UID signs live SQLite pointer; the
independent Publisher atomically replaces ONE snapshot file; different
read-only Linux UID serves same-port HTTP/Chromium without restart. Source
pointer advances temporarily fail closed until published snapshot catches up.
Only B9 Model/View and the seeded disposable Native contract data are proved.
"""
from __future__ import annotations
import copy
import hashlib
import json
import os
from pathlib import Path
import pwd
import secrets
import subprocess
import sys
import time
from urllib.error import HTTPError
from urllib.request import Request,urlopen

from p0b_signed_release import verify,ReleaseSignatureRejected
from p0b_consumer_suite import ConsumerRound
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"g1-b01-b14"))
from signed_projection import verify_event,SignatureRefused

KERN="ailcapb9kern"
RUNT="ailcapb9run"
PLUG="ailcapb9plug"
PUBL="ailcapb9pub"
READ="ailcapb9ro"
PUBGRP="ailcapb9public"

class SignedRuntimeSuite:
    def __init__(self,*,home,stage,authority_db,authority_dir,
                 kernel_base,kernel_token,publisher_token,
                 template,native_physical,physical,execute,single,
                 wait_page,context,check):
        self.home=home
        self.stage=stage
        self.authority_db=authority_db
        self.authority_dir=authority_dir
        self.base=kernel_base
        self.token=kernel_token
        self.publisher_token=publisher_token
        self.template=template
        self.native_physical=native_physical
        self.physical=physical
        self.execute=execute
        self.single=single
        self.wait_page=wait_page
        self.context=context
        self.check=check
        self.key=authority_dir/"p0b-release-ed25519.key"
        self.pubdir=home/"published-private"
        self.rodir=home/"readonly-private"
        self.roready=home/"readonly-ready"
        self.pubcfg=self.pubdir/"publisher-config.json"
        self.rocfg=self.rodir/"router-config.json"
        self.snapshot=self.pubdir/"published.sqlite"
        self.public_key=None
        self.router=None
        self.router_log=None
        self.router_base=None
        self.page=None
        self.original_native=None
        self.original_source=None
        self.original_signed=None
        self.source_v3=None
        self.v1_native=None
        self.app_b=None
        self.runtime_pid=None

    def _user_call(self,owner,argv,*,strict=True,env=None,timeout=90):
        args=["sudo","-n","runuser","-u",owner,"--"]
        if env:
            args+=["/usr/bin/env",*[
                key+"="+str(val) for key,val in env.items()]]
        args += [sys.executable,*map(str,argv)]
        return self.execute(args,cwd=self.stage,strict=strict,timeout=timeout)

    def _sign(self):
        result=self._user_call(KERN,[
            self.stage/"g1-b01-b9"/"p0b_signed_release.py",
            "sign","--key",self.key,"--db",self.authority_db,
            "--template",self.stage/"platform-saltcorn"/"contract-pack.json"])
        raw=self.single(result.stdout,"P0B_SOURCE")
        if (not isinstance(raw,dict) or
            set(raw)!={"signedRelease","signedEvents"} or
            verify(raw["signedRelease"],self.public_key)!=
                raw["signedRelease"]["payload"]):
            raise AssertionError("P0B_SOURCE_INDEPENDENT_VERIFY_FAILED")
        for event in raw["signedEvents"]:
            verify_event(event,self.public_key)
        return raw

    def _candidate(self,signature,native):
        return {**copy.deepcopy(signature),"nativeOracle":native}

    def _write_candidate(self,tag,candidate):
        file=self.stage/("p0b-candidate-"+tag+".json")
        file.write_text(json.dumps(candidate,ensure_ascii=False,
                                   sort_keys=True)+"\n",encoding="utf-8")
        file.chmod(0o644)
        return file

    def _publish(self,tag,candidate,*,failure=False,prepare=False):
        path=self._write_candidate(tag,candidate)
        command=[
            self.stage/"g1-b01-b9"/"p0b_publisher.py",
            "--config",self.pubcfg,"--candidate",path]
        if prepare:
            command.append("--prepare")
        process=self._user_call(
            PUBL,command,strict=False,timeout=60,
            env={"P0B_INJECT_BUILD_FAILURE":"1"} if failure else None)
        if process.returncode==0:
            return (0,self.single(process.stdout,
                         "P0B_PREPARED" if prepare else "P0B_PUBLISHED"))
        errors=[line.split("|",1)[1] for line in process.stdout.splitlines()
                if line.startswith("P0B_PUBLISH_REJECT|")]
        if not errors:
            raise AssertionError("P0B_PUBLISHER_CRASHED_"+
                                 process.stderr[-230:])
        return process.returncode,errors[0]

    def _request(self,method="GET",path="/view/s1_contract_list"):
        req=Request(self.router_base+path,method=method)
        try:
            with urlopen(req,timeout=6) as resp:
                return resp.status,dict(resp.headers),resp.read(1048577)
        except HTTPError as exc:
            return exc.code,dict(exc.headers),exc.read(1048577)

    def _sha(self):
        # Publisher-private directory is 2750, inaccessible to runner UID.
        # Ask the actual owner to inspect the atomic snapshot bytes.
        script = ("import hashlib,sys,pathlib\n"
                  "p=pathlib.Path(sys.argv[1 ])\n"
                  "print(hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else 'MISSING')")
        proof=self._user_call(PUBL,["-c",script,self.snapshot],
                              strict=True,timeout=10)
        digest=proof.stdout.strip()
        return None if digest=="MISSING" else digest

    def _make_dirs(self):
        for folder in (self.pubdir,self.rodir,self.roready,
                       self.pubdir/"candidates"):
            folder.mkdir(mode=0o700)
        self.pubcfg.write_text(json.dumps({
            "output":str(self.snapshot),"kernelBase":self.base,
            "kernelReadToken":self.token,"publicKeyHex":self.public_key,
            "packTemplate":self.template
        },ensure_ascii=False),encoding="utf-8")
        self.rocfg.write_text(json.dumps({
            "kernelBase":self.base,"kernelReadToken":self.token,
            "publicKeyHex":self.public_key,"snapshot":str(self.snapshot),
            "publisherUid":pwd.getpwnam(PUBL).pw_uid
        }),encoding="utf-8")
        self.pubcfg.chmod(0o600)
        self.rocfg.chmod(0o600)
        self.execute(["sudo","-n","chown","-R",PUBL+":"+PUBGRP,
                      self.pubdir])
        self.execute(["sudo","-n","chmod","2750",self.pubdir,
                      self.pubdir/"candidates"])
        self.execute(["sudo","-n","chown","-R",READ+":"+READ,self.rodir,
                      self.roready])
        self.execute(["sudo","-n","chmod","0700",self.rodir])
        self.execute(["sudo","-n","chmod","0755",self.roready])

    def _start_router(self):
        log=self.home/"p0b-router.log"
        self.router_log=log
        self.router=subprocess.Popen([
            "sudo","-n","runuser","-u",READ,"--",sys.executable,"-u",
            str(self.stage/"g1-b01-b9"/"p0b_readonly_web.py"),
            "--config",str(self.rocfg),
            "--ready",str(self.roready/"router-ready.json")
        ],cwd=str(self.stage),stdout=log.open("w"),
          stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL)
        ready=self.roready/"router-ready.json"
        for _ in range(100):
            if ready.exists():
                break
            if self.router.poll() is not None:
                raise AssertionError("P0B_ROUTER_LAUNCH_ERROR "+
                                     log.read_text()[-900:])
            time.sleep(.1)
        if not ready.exists():
            raise AssertionError("P0B_ROUTER_READY_TIMEOUT "+
                                 log.read_text()[-900:])
        meta=json.loads(ready.read_text())
        self.router_base="http://127.0.0.1:"+str(meta["port"])
        self.runtime_pid=meta["port"]
        if not self.wait_page(self.router_base,
                              "/view/s1_contract_list",10):
            raise AssertionError("P0B_SIGNED_ROUTER_NOT_READY")
        return meta

    def init_v1(self,*,native_db,native_page,human_page):
        self.original_native=self.native_physical(native_db)
        self.v1_native=copy.deepcopy(self.original_native)
        self.app_b=self.physical()["app-b"]
        # Real authenticated B2 HUMAN + CSRF form submission; B11 AFTER
        # trigger records event-time data in the same authority SQLite TX.
        posted=human_page.evaluate("""async () => {
            const r=await fetch("/v2/apps/app-a/runtime/forms/form.contracts/records",{
              method:"POST",credentials:"same-origin",
              headers:{"Content-Type":"application/json","X-CSRF-Token":csrf},
              body:JSON.stringify({contract_no:"HT-2026-000001",
                title:"S1 Platform Contract",amount_minor:100000001})
            });
            return {status:r.status,body:await r.json()};
        }""")
        if (posted["status"]!=200 or
            posted["body"].get("data",{}).get("status")!="Draft"):
            raise AssertionError("P0B_B2_HUMAN_FORM_SUBMIT_FAILED_"+str(posted))
        self.b2_human_first=posted
        # The key physically resides in the KERN-only 0700 authority folder.
        init=self._user_call(KERN,[
            self.stage/"g1-b01-b9"/"p0b_signed_release.py",
            "init","--key",self.key,"--db",self.authority_db])
        self.public_key=init.stdout.split("P0B_PUBLIC_KEY|",1)[1].splitlines()[0]
        self.original_signed=self._sign()
        self.original_source=self.original_signed["signedRelease"]["payload"]
        denied={}
        for u in (RUNT,PLUG,PUBL,READ):
            read=self._user_call(u,["-c","import os,sys\n"
                "p=sys.argv[1]\n"
                "try:\n fd=os.open(p,os.O_RDONLY);os.close(fd);print('OPENED')\n"
                "except OSError:print('DENIED')",self.key],
                strict=False)
            # Passing "-c" through sys.executable is supported by _user_call.
            denied[u]=read.stdout.strip()
        self.check("P0B-01-actual-B14-Ed25519-Kernel-UID-key-only",
                   len(self.public_key)==64 and
                   all(x=="DENIED" for x in denied.values()) and
                   self.original_source["version"]==1 and
                   self.original_source["outboxHead"]==1 and
                   len(self.original_signed["signedEvents"])==1 and
                   self.original_source["viewColumns"]==[
                       "contract_no","amount_minor","status"],
                   {"actualSignerUid":pwd.getpwnam(KERN).pw_uid,
                    "b2HumanFormHTTP":posted["status"],
                    "signedB11EventCount":1,
                    "deniedUids":denied,"keyNotExported":True,
                    "signedVersion":1})
        self._make_dirs()
        status,result=self._publish("verified-v1",self._candidate(
            self.original_signed,self.v1_native))
        meta=self._start_router()
        self.page=self.context.new_page()
        self.page.goto(self.router_base+"/view/s1_contract_list",
                       wait_until="domcontentloaded")
        document=self.page.content()
        headings=self.page.locator("th").all_inner_texts()
        first_status,headers,_=self._request()
        self.check("P0B-02-different-Uids-atomic-v1-B17-browser-readonly",
                   status==0 and result["version"]==1 and
                   meta["uid"]==pwd.getpwnam(READ).pw_uid and
                   meta["uid"]!=result["ownerUid"] and
                   first_status==200 and
                   headers.get("X-OpenAILCAP-Release")=="1" and
                   len(headings)==3 and
                   headings==["Contract Number","Amount in CNY cents",
                              "Status"] and
                   "HT-2026-000001" in document and
                   self.physical()["app-b"]==self.app_b,
                   {"published":result,"routerUid":meta["uid"],
                    "browserColumns":headings,
                    "actualReadOnlyRoute":self.router_base,
                    "noWorkerRestart":True})
        true_row=self.v1_native["businessRows"][0]
        actual_row=self.physical()["app-a"]["records"][0]["value"]
        event=self.original_signed["signedEvents"][0]
        head=self._business_head()
        self.check("P0B-10-real-B2-human-record-B11-Ed25519-equals-Native",
                   actual_row==true_row==event["cells"] and
                   head["head"]==1 and
                   head["rowsDigest"]==self.original_source["rowsDigest"] and
                   self.b2_human_first["body"]["recordId"]==
                      self.physical()["app-a"]["records"][0]["id"] and
                   self.original_source["outboxHead"]==1,
                   {"B2ActualRecord":actual_row,"realHumanPOST":200,
                    "nativeSQLMatches":True,"actualB11Head":1,
                    "signedEventVerified":True})

    def published_v3(self,staged_native_db):
        self.source_v3=self._sign()
        physical_v3=self.native_physical(staged_native_db)
        old_digest=self._sha()
        before,_,_=self._request()
        self.page.reload(wait_until="domcontentloaded")
        self.check("P0B-03-B2-new-v3-source-before-publish-fails-closed",
                   before==503 and self._sha()==old_digest and
                   self.source_v3["signedRelease"]["payload"]["version"]==3 and
                   physical_v3["viewColumns"]==[
                       "contract_no","title","amount_minor","status"] and
                   self.page.locator("th").count()==0 and
                   self.router.poll() is None,
                   {"B2LatestRelease":3,"oldSnapshotStillOnDisk":True,
                    "readOnlyHTTP":before,"routerNeverRestarted":True})

        attack=copy.deepcopy(self.source_v3)
        attack["signedRelease"]["signature"]="AAAA"
        tampered=self._publish("tampered-signature",self._candidate(
            attack,physical_v3))
        wrong_native=copy.deepcopy(physical_v3)
        wrong_native["viewColumns"]=["contract_no","status"]
        mismatch=self._publish("forged-native-columns",self._candidate(
            self.source_v3,wrong_native))
        native_forgery=copy.deepcopy(physical_v3)
        native_forgery["businessRows"][0]["title"]="UNTRUSTED_NATIVE_TITLE"
        forged_rows=self._publish(
            "forged-same-view-native-row",self._candidate(
                self.source_v3,native_forgery))
        forged_event=copy.deepcopy(self.source_v3)
        forged_event["signedEvents"][0]["cells"]["title"]="ATTACK_FROM_PLUGIN"
        forged_payload=self._publish(
            "forged-b11-signed-event",self._candidate(
                forged_event,physical_v3))
        self.check("P0B-11-native-row-same-view-fabrication-denied",
                   forged_rows==(2,"PUBLISH_NATIVE_ROWS_NOT_B2_SIGNED") and
                   self._sha()==old_digest,
                   {"sameViewColumns":True,"nativeCellForged":True,
                    "publishDecision":forged_rows[1],
                    "oldSnapshotBytesUntouched":True})
        self.check("P0B-12-tampered-B14-business-event-rejected",
                   forged_payload==(2,"PUBLISH_B11_EVENT_SIGNATURE_INVALID") and
                   self._sha()==old_digest,
                   {"signedEventTamper":forged_payload[1],
                    "realB2RecordUnmodified":True})
        self.check("P0B-04-B14-signature-and-SQL-projection-forgery-denied",
                   tampered==(2,"PUBLISH_SOURCE_SIGNATURE_REJECTED") and
                   mismatch==(2,"PUBLISH_NATIVE_VIEW_MISMATCH") and
                   self._sha()==old_digest,
                   {"tamperedSignature":tampered[1],
                    "nativeViewMismatch":mismatch[1],
                    "oldVerifiedSnapshotBytesUnchanged":True})
        injected=self._publish("injected-build-failure",
                               self._candidate(self.source_v3,physical_v3),
                               failure=True)
        self.check("P0B-05-B15-build-failure-preserves-old-file",
                   injected==(2,"PUBLISH_BUILD_FAILURE_INJECTED") and
                   self._sha()==old_digest and
                   self._request()[0]==503,
                   {"failure":injected[1],
                    "atomicSnapshotOldHashPreserved":True,
                    "noUnverifiedStaleHTML":True})
        good_status,good=self._publish("verified-v3",self._candidate(
            self.source_v3,physical_v3))
        new_digest=self._sha()
        self.page.reload(wait_until="domcontentloaded")
        head=self.page.locator("th").all_inner_texts()
        response,headers,raw=self._request()
        self.check("P0B-06-B15-atomic-v3-to-same-B17-browser-without-restart",
                   good_status==0 and good["version"]==3 and
                   good["singleFileAtomicSwap"] and
                   new_digest!=old_digest and response==200 and
                   headers.get("X-OpenAILCAP-Release")=="3" and
                   len(head)==4 and head==[
                       "Contract Number","Title",
                       "Amount in CNY cents","Status"] and
                   self.page.locator("body").get_attribute("data-release")=="3" and
                   "HT-2026-000001" in raw.decode("utf-8") and
                   self.router.poll() is None and
                   self.native_physical(staged_native_db)==physical_v3,
                   {"fromVersion":1,"toVersion":3,
                    "realChromiumColumns":head,"browserReloadNoRestart":True,
                    "atomicFileHashChanged":True,"published":good})
        authority_before=self.physical()
        blocked={}
        for method in ("POST","PUT","PATCH","DELETE"):
            blocked[method]=self._request(method)[0]
        after_readonly=self._sha()
        self.check("P0B-07-B17-all-public-writes-rejected-no-snapshot-effects",
                   all(x==405 for x in blocked.values()) and
                   after_readonly==new_digest and
                   self.physical()==authority_before and
                   self.router.poll() is None,
                   {"methods":blocked,"sameAtomicSnapshot":True,
                    "noKernelMutations":True})

    def rolled_back(self,*,native_live_db):
        before_sha=self._sha()
        before,_,_=self._request()
        self.page.reload(wait_until="domcontentloaded")
        self.check("P0B-08-rollback-pointer-before-publisher-fails-closed",
                   before==503 and self.page.locator("th").count()==0 and
                   self._sha()==before_sha and
                   self.physical()["app-a"]["publishedVersion"]==1 and
                   self.router.poll() is None,
                   {"B2Pointer":1,"staleVersion3NotServed":True,
                    "unchangedLastPublishedAtomicBytes":True})
        signature_v1=self._sign()
        current_native=self.native_physical(native_live_db)
        res,published=self._publish("verified-rollback-v1",
                                   self._candidate(signature_v1,current_native))
        self.page.reload(wait_until="domcontentloaded")
        col=self.page.locator("th").all_inner_texts()
        resp,headers,body=self._request()
        self.check("P0B-09-B14-B15-B17-verified-rollback-same-browser-port",
                   res==0 and published["version"]==1 and
                   resp==200 and
                   headers.get("X-OpenAILCAP-Release")=="1" and
                   col==["Contract Number","Amount in CNY cents","Status"] and
                   self.page.locator("body").get_attribute("data-release")=="1" and
                   "HT-2026-000001" in body.decode("utf-8") and
                   self._sha()!=before_sha and
                   self.router.poll() is None and
                   current_native==self.original_native and
                   self.physical()["app-b"]==self.app_b,
                   {"version":1,"browserColumns":col,
                    "sameReadOnlyUrl":self.router_base,
                    "Ed25519Verified":True,"atomicallyReplaced":True,
                    "noBrowserOrRouterRestart":True})
        return {"checks":9,"signedByLiveKernelUid":True,
                "independentPublisherAndRendererUid":True,
                "samePublicRouterAcrossV1V3Rollback":True,
                "stalePointerFailClosed":True,
                "failedBuildOldSnapshotPhysicallyPreserved":True,
                "modelCalls":0,"g1Passed":False,
                "codeWorkflowFormParity":False,
                "productionAtomicAcrossB2AndPublisher":False}

    def _business_head(self):
        req=Request(self.base+"/v3/apps/app-a/tools/business.head",
                    method="POST",data=b"{}",
                    headers={"Content-Type":"application/json",
                             "Authorization":"Bearer "+self.token})
        with urlopen(req,timeout=5) as response:
            if response.status!=200:
                raise AssertionError("B2_BUSINESS_HEAD_UNAVAILABLE")
            return json.loads(response.read())

    def business_row_advance(self,*,human_page,native_live_db,native_cmd):
        """Same published version: business transaction advances B11 head.

        Prove B17 freshness also watches authoritative DATA, not just the
        B2 RELEASE metadata. A trusted test controller runs real Native CLI
        to catch up; this is NOT an autonomous production B11 consumer.
        """
        prior=self._sha()
        prior_head=self._business_head()
        if prior_head["head"]!=1:
            raise AssertionError("P0B_BUSINESS_BASELINE_HEAD_NOT_ONE")
        posted=human_page.evaluate("""async () => {
            const r=await fetch("/v2/apps/app-a/runtime/forms/form.contracts/records",{
              method:"POST",credentials:"same-origin",
              headers:{"Content-Type":"application/json","X-CSRF-Token":csrf},
              body:JSON.stringify({contract_no:"HT-2026-000002",
                title:"S1 Authority Next Contract",amount_minor:200000002})
            });
            return {status:r.status,body:await r.json()};
        }""")
        advanced=self._business_head()
        stale,_,body=self._request()
        self.page.reload(wait_until="domcontentloaded")
        kernel_rows=self.physical()["app-a"]["records"]
        self.check("P0B-13-B2-record-commit-outbox-moves-without-release",
                   posted["status"]==200 and
                   posted["body"].get("data",{}).get("status")=="Draft" and
                   advanced["head"]==2 and
                   advanced["rowsDigest"]!=prior_head["rowsDigest"] and
                   self.physical()["app-a"]["publishedVersion"]==1 and
                   stale==503 and self.page.locator("th").count()==0 and
                   self._sha()==prior and len(kernel_rows)==2 and
                   self.router.poll() is None,
                   {"realHumanPOST":posted["status"],
                    "outboxHeadBefore":1,"outboxHeadAfter":2,
                    "publishedVersionStill":1,"browserHTTP":stale,
                    "oldVerifiedSnapshotBytesUnchanged":True})

        # Same old one-row Native must NOT be promoted despite a valid signed
        # B2 release: its business data lags one committed source event.
        re_signed=self._sign()
        stale_native=self.native_physical(native_live_db)
        status_before,reason=self._publish(
            "same-release-but-outbox-stale",
            self._candidate(re_signed,stale_native))
        self.check("P0B-14-native-lags-B11-signed-business-denied",
                   status_before==2 and
                   reason=="PUBLISH_NATIVE_ROWS_NOT_B2_SIGNED" and
                   self._sha()==prior and self._request()[0]==503,
                   {"laggingNativeRows":len(stale_native["businessRows"]),
                    "realB2Records":len(kernel_rows),"denied":reason,
                    "snapshotProtected":True})

        # This is a manual trusted same-instance synchronization, not a new
        # source of truth. We reuse the existing Native owner and its
        # launcher path restrictions for the actual official Saltcorn CLI.
        updated=native_cmd(
            ["saltcorn","run-js","-f",
             self.stage/"platform-saltcorn"/"p0b-seed-second-contract.js"],
            native_live_db)
        native_now=self.native_physical(native_live_db)
        synced_status,result=self._publish(
            "same-release-matched-b2-outbox",
            self._candidate(re_signed,native_now))
        self.page.reload(wait_until="domcontentloaded")
        latest_status,headers,html=self._request()
        content=html.decode("utf-8")
        after=self._business_head()
        self.check("P0B-15-authority-signed-second-row-reaches-live-browser",
                   updated.returncode==0 and synced_status==0 and
                   result["version"]==1 and result["rows"]==2 and
                   after["head"]==2 and
                   len(native_now["businessRows"])==2 and
                   native_now["businessRows"]==[
                       record["value"] for record in sorted(
                           kernel_rows,key=lambda r:r["value"]["contract_no"])] and
                   self._sha()!=prior and latest_status==200 and
                   headers.get("X-OpenAILCAP-Release")=="1" and
                   "HT-2026-000001" in content and
                   "HT-2026-000002" in content and
                   self.page.locator("tbody tr").count()==2 and
                   self.router.poll() is None and
                   self.physical()["app-b"]==self.app_b,
                   {"realB2Records":2,"signedB11Events":2,
                    "saltcornNativeRows":2,"publicBrowserRows":2,
                    "sameB2ReleaseVersion":1,
                    "sameB17RouterNoRestart":True,
                    "signerDigest":re_signed["signedRelease"]["payload"]["rowsDigest"]})
        return {"newSignedEvents":1,"businessRows":2,
                "sameReleaseDataFreshnessValidated":True,
                "manualNativeCatchupRequired":True}

    def durable_consumer_round(self,*,native_cmd,native_runtime,human_page):
        """Actual asynchronous B14 signed IPC consumer over this SAME B2."""
        roundtrip=ConsumerRound(self,native_cmd=native_cmd,
                                native_runtime=native_runtime,
                                human_page=human_page)
        return roundtrip.run()

    def stop(self):
        if self.page is not None:
            try:self.page.close()
            except Exception:pass
        if self.router is not None and self.router.poll() is None:
            self.router.terminate()
            try:self.router.wait(timeout=4)
            except subprocess.TimeoutExpired:self.router.kill()
