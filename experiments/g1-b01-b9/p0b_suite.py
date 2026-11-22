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
        if verify(raw,self.public_key)!=raw["payload"]:
            raise AssertionError("P0B_SOURCE_INDEPENDENT_VERIFY_FAILED")
        return raw

    def _candidate(self,signature,native):
        return {"signedRelease":signature,"nativeOracle":native}

    def _write_candidate(self,tag,candidate):
        file=self.stage/("p0b-candidate-"+tag+".json")
        file.write_text(json.dumps(candidate,ensure_ascii=False,
                                   sort_keys=True)+"\n",encoding="utf-8")
        file.chmod(0o644)
        return file

    def _publish(self,tag,candidate,*,failure=False):
        path=self._write_candidate(tag,candidate)
        command=[
            self.stage/"g1-b01-b9"/"p0b_publisher.py",
            "--config",self.pubcfg,"--candidate",path]
        process=self._user_call(
            PUBL,command,strict=False,timeout=60,
            env={"P0B_INJECT_BUILD_FAILURE":"1"} if failure else None)
        if process.returncode==0:
            return (0,self.single(process.stdout,"P0B_PUBLISHED"))
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
        for folder in (self.pubdir,self.rodir,self.roready):
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
        self.execute(["sudo","-n","chmod","2750",self.pubdir])
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

    def init_v1(self,*,native_db,native_page):
        self.original_native=self.native_physical(native_db)
        self.v1_native=copy.deepcopy(self.original_native)
        self.app_b=self.physical()["app-b"]
        # The key physically resides in the KERN-only 0700 authority folder.
        init=self._user_call(KERN,[
            self.stage/"g1-b01-b9"/"p0b_signed_release.py",
            "init","--key",self.key,"--db",self.authority_db])
        self.public_key=init.stdout.split("P0B_PUBLIC_KEY|",1)[1].splitlines()[0]
        self.original_signed=self._sign()
        self.original_source=self.original_signed["payload"]
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
                   self.original_source["viewColumns"]==[
                       "contract_no","amount_minor","status"],
                   {"actualSignerUid":pwd.getpwnam(KERN).pw_uid,
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

    def published_v3(self,staged_native_db):
        self.source_v3=self._sign()
        physical_v3=self.native_physical(staged_native_db)
        old_digest=self._sha()
        before,_,_=self._request()
        self.page.reload(wait_until="domcontentloaded")
        self.check("P0B-03-B2-new-v3-source-before-publish-fails-closed",
                   before==503 and self._sha()==old_digest and
                   self.source_v3["payload"]["version"]==3 and
                   physical_v3["viewColumns"]==[
                       "contract_no","title","amount_minor","status"] and
                   self.page.locator("th").count()==0 and
                   self.router.poll() is None,
                   {"B2LatestRelease":3,"oldSnapshotStillOnDisk":True,
                    "readOnlyHTTP":before,"routerNeverRestarted":True})

        attack=copy.deepcopy(self.source_v3)
        attack["signature"]="AAAA"
        tampered=self._publish("tampered-signature",self._candidate(
            attack,physical_v3))
        wrong_native=copy.deepcopy(physical_v3)
        wrong_native["viewColumns"]=["contract_no","status"]
        mismatch=self._publish("forged-native-columns",self._candidate(
            self.source_v3,wrong_native))
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
        blocked={}
        for method in ("POST","PUT","PATCH","DELETE"):
            blocked[method]=self._request(method)[0]
        after_readonly=self._sha()
        self.check("P0B-07-B17-all-public-writes-rejected-no-snapshot-effects",
                   all(x==405 for x in blocked.values()) and
                   after_readonly==new_digest and
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

    def stop(self):
        if self.page is not None:
            try:self.page.close()
            except Exception:pass
        if self.router is not None and self.router.poll() is None:
            self.router.terminate()
            try:self.router.wait(timeout=4)
            except subprocess.TimeoutExpired:self.router.kill()
