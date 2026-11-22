"""Frozen G1 W20 real external business side-effect UNKNOWN evidence.

This is NOT a mock side effect and not an activation HTTP timeout:
- same logged-in B2 Chromium real form.contracts record -> workflow.advance
- original B11 AFTER UPDATE event and independent Native SQL version/receipt
- seventh independent Linux UID runs an actual HTTP external API with separate
  SQLite business effect AND response receipt committed before HTTP timeout
- separate original B2 Kernel UID persists exact changeId before one outbound
  POST, sees UNKNOWN; GET receipt plus external physical DB oracle reconciles.
Manual/Plugin/Consumer must not read the external DB or impersonate the sender.
This tests W20's entire specific scope as a real research candidate.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import os
import pwd
import secrets
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError
from urllib.request import Request,urlopen

EXT="ailcapb9external"
KERN="ailcapb9kern"
PUBL="ailcapb9pub"
CONS="ailcapb9cons"
PLUG="ailcapb9plug"


class RealExternalUnknownRound:
    def __init__(self,suite,consumer,publisher):
        self.s=suite
        self.cons=consumer
        self.pub=publisher
        self.home=suite.home
        self.stage=suite.stage
        self.private=self.home/"external-private"
        self.readydir=self.home/"external-ready"
        self.db=self.private/"effects.sqlite"
        self.extcfg=self.private/"config.json"
        self.kcfg=suite.authority_dir/"p0b-external-dispatch.json"
        self.ready=self.readydir/"external-ready.json"
        self.external=None
        self.port=None
        self.token_send=secrets.token_urlsafe(42)
        self.token_query=secrets.token_urlsafe(42)
        self.record_id=suite.b2_human_first["body"]["recordId"]

    def _call(self,owner,argv,strict=True):
        return self.s._user_call(owner,argv,timeout=30,strict=strict)

    def _sql(self):
        r=self._call(EXT,[self.stage/"g1-b01-b9"/"p0b_external_effect.py",
                          "--inspect",self.db])
        return self.s.single(r.stdout,"P0B_EXTERNAL_SQL")

    def _dispatch(self,action):
        r=self._call(KERN,[
            self.stage/"g1-b01-b9"/"p0b_external_dispatch.py",
            "--config",self.kcfg,
            "--record-id",self.record_id,"--action",action])
        return self.s.single(r.stdout,"P0B_EXTERNAL_DISPATCH")

    def _get(self,token,cid):
        r=Request(
            "http://127.0.0.1:"+str(self.port)+
            "/v1/contract-effects/receipts/"+cid,
            method="GET",headers={"Authorization":"Bearer "+token})
        try:
            with urlopen(r,timeout=6) as resp:
                return resp.status,json.loads(resp.read())
        except HTTPError as exc:
            return exc.code,json.loads(exc.read())

    def _post(self,token,payload):
        r=Request(
            "http://127.0.0.1:"+str(self.port)+"/v1/contract-effects",
            method="POST",data=json.dumps(payload).encode(),
            headers={"Authorization":"Bearer "+token,
                     "Content-Type":"application/json"})
        try:
            with urlopen(r,timeout=6) as resp:
                return resp.status,json.loads(resp.read())
        except HTTPError as exc:
            return exc.code,json.loads(exc.read())

    def _setup(self):
        self.private.mkdir(mode=0o700)
        self.readydir.mkdir(mode=0o755)
        self.s.execute(["sudo","-n","chown","-R",
                        EXT+":"+EXT,self.private,self.readydir])
        # Runtime UID is not part of B2 Kernel's credential group.
        with socket.socket() as probe:
            probe.bind(("127.0.0.1",0))
            self.port=probe.getsockname()[1]
        seed=self.home/"external-config-seed.json"
        seed.write_text(json.dumps({
            "db":str(self.db),"sendToken":self.token_send,
            "queryToken":self.token_query,"delayFirstMs":1250,
            "port":self.port}))
        seed.chmod(0o600)
        self.s.execute(["sudo","-n","install","-m","0600",
                        "-o",EXT,"-g",EXT,seed,self.extcfg])
        seed.unlink()
        seed=self.home/"kernel-external-config-seed.json"
        seed.write_text(json.dumps({
            "authorityDb":str(self.s.authority_db),
            "externalBase":"http://127.0.0.1:"+str(self.port),
            "sendToken":self.token_send,"queryToken":self.token_query,
            "timeoutMs":165}))
        seed.chmod(0o600)
        self.s.execute(["sudo","-n","install","-m","0600",
                        "-o",KERN,"-g",KERN,seed,self.kcfg])
        seed.unlink()
        log=self.home/"external-side-effect.log"
        self.external=subprocess.Popen([
            "sudo","-n","runuser","-u",EXT,"--",sys.executable,"-u",
            str(self.stage/"g1-b01-b9"/"p0b_external_effect.py"),
            "--config",str(self.extcfg),"--ready",str(self.ready)
        ],cwd=str(self.stage),stdin=subprocess.DEVNULL,
           stdout=log.open("w"),stderr=subprocess.STDOUT)
        for _ in range(100):
            if self.ready.is_file():break
            if self.external.poll() is not None:
                raise AssertionError(
                    "W20_EXTERNAL_SERVICE_DIED_"+log.read_text()[-1000:])
            time.sleep(.08)
        if not self.ready.is_file():
            raise AssertionError("W20_EXTERNAL_READY_TIMEOUT")
        ready=json.loads(self.ready.read_text())
        if (ready["uid"]!=pwd.getpwnam(EXT).pw_uid or
            ready["port"]!=self.port):
            raise AssertionError("W20_EXTERNAL_UID_OR_PORT_MISMATCH")

    def run(self):
        try:return self._run()
        finally:self.stop()

    def _run(self):
        s=self.s
        baseline=self.pub._api("publication.read",s.token,{})[1]
        if (baseline["source"]["outboxHead"]!=8 or
            baseline["epoch"]!=6 or
            self.cons._inspect()["cursor"]!=8):
            raise AssertionError("W20_NOT_SAME_PUBLISHED_KERNEL_RECORDS")
        self._setup()
        empty=self._sql()
        app_b=s.physical()["app-b"]
        uid=pwd.getpwnam(EXT).pw_uid
        for person in (KERN,PUBL,CONS,PLUG):
            if uid==pwd.getpwnam(person).pw_uid:
                raise AssertionError("W20_EXTERNAL_DB_OWNER_NOT_INDEPENDENT")
        script=("import os,sys\n"
                "try:\n"
                " fd=os.open(sys.argv[1],os.O_RDONLY)\n"
                " os.close(fd);print('OPENED')\n"
                "except OSError:print('DENIED')\n")
        no_direct={k:self._call(k,["-c",script,self.db],strict=False
                         ).stdout.strip() for k in (KERN,PUBL,CONS,PLUG)}
        s.check("P0B-44-independent-external-business-DB-and-least-privilege",
                empty["effects"]==empty["receipts"]==[] and
                empty["uid"]==uid and
                all(x=="DENIED" for x in no_direct.values()) and
                self.external.poll() is None,
                {"externalUid":uid,"independentBusinessSQLite":str(self.db),
                 "physicalInitialEffects":0,"KernelPublisherConsumerPluginDenied":
                     no_direct,"externalNoDomainWriteGrant":True})

        # Real logged-in Chromium calls the original B2 workflow engine.
        # B11 AFTER UPDATE must emit event seq9, not a made-up workflow row.
        posted=self.cons.human_page.evaluate("""async recordId => {
          const r=await fetch(
            "/v2/apps/app-a/runtime/workflows/workflow.approval/records/"+
            recordId+"/advance",{
            method:"POST",credentials:"same-origin",
            headers:{"Content-Type":"application/json","X-CSRF-Token":csrf},
            body:JSON.stringify({action:"submit",expectedVersion:1})
          });
          return {status:r.status,body:await r.json()};
        }""",self.record_id)
        if posted["status"]!=200:
            raise AssertionError("W20_B2_REAL_CHROMIUM_WORKFLOW_FAILED_"+str(posted))
        head9=s._business_head()
        def native_updated():
            x=self.cons._inspect()
            if (x["clean"] and x["cursor"]==9 and
                x["receiptCount"]==9 and x["mappingCount"]==8 and
                len(x["rows"])==8 and
                any(r["contract_no"]=="HT-2026-000001" and
                    r["status"]=="PendingLevel1"
                    for r in x["rows"])):
                return x
            return None
        native=self.pub._poll(native_updated,seconds=19)
        committed=self.pub._head(9,7,seconds=23)
        browser=self.pub._browser(8)
        html=s._request()[2].decode()
        s.check("P0B-45-real-B2-Chromium-workflow-update-B11-Native-publication",
                posted["body"]["version"]==2 and
                posted["body"]["status"]=="PendingLevel1" and
                head9["head"]==9 and
                native["cursor"]==native["receiptCount"]==9 and
                native["mappingCount"]==8 and
                committed["epoch"]==7 and browser and
                "PendingLevel1" in html and
                self.external.poll() is None and
                s.physical()["app-b"]==app_b,
                {"authenticatedB2WorkflowHTTP":200,
                 "workflowStatus":"PendingLevel1","workflowRecordVersion":2,
                 "trueB11OutboxHead":9,"durableNativeCursor":9,
                 "realNativeMappedRows":8,
                 "autoPublisherActivationEpoch":7,
                 "sameB17BrowserRows":8})

        timed=self._dispatch("send")
        physical=self._sql()
        own=self._dispatch("inspect")
        code,remote=self._get(self.token_query,timed["changeId"])
        s.check("P0B-46-real-external-SQL-effect-committed-before-HTTP-timeout",
                timed["decision"]=="UNKNOWN" and
                timed["attempts"]==1 and
                timed["safeToAutoRetry"] is False and
                len(physical["effects"])==len(physical["receipts"])==1 and
                physical["effects"][0]["change_id"]==timed["changeId"] and
                physical["effects"][0]["record_id"]==self.record_id and
                physical["effects"][0]["workflow_version"]==2 and
                own["state"]=="UNKNOWN" and own["attempts"]==1 and
                code==200 and remote["decision"]=="COMMITTED" and
                remote["effect"]["recordId"]==self.record_id and
                remote["receipt"]["payloadHash"]==
                  physical["effects"][0]["payload_hash"],
                {"actualExternalHTTPClient":"Kernel UID",
                 "clientObserved":"UNKNOWN_AFTER_TIMEOUT",
                 "physicallyCommittedExternalBusinessEffects":1,
                 "physicallyCommittedExternalReceipts":1,
                 "B2Journal":own["state"],"originalChangeId":timed["changeId"],
                 "distinctExternalHTTPResult":code})

        recon=self._dispatch("reconcile")
        reread=self._dispatch("inspect")
        retry=self._dispatch("send")
        second=self._sql()
        unauthorized=self._get("INVALID_TOKEN",timed["changeId"])
        changed_payload={
            "changeId":timed["changeId"],
            "recordId":self.record_id,
            "contractNo":"HT-2026-000001",
            "workflowVersion":2,
            "workflowStatus":"Approved", # same CID, different payload
            "action":"CONTRACT_WORKFLOW_NOTIFICATION"
        }
        conflict=self._post(self.token_send,changed_payload)
        after=self._sql()
        s.check("P0B-47-external-receipt-exact-changeId-confirms-UNKNOWN-once",
                recon["decision"]=="CONFIRMED" and
                recon["attempts"]==1 and recon["receiptVerified"] and
                reread["state"]=="CONFIRMED" and reread["attempts"]==1 and
                retry["decision"]=="CONFIRMED" and
                retry["externalPostReplayed"] is False and
                second==after==physical and
                unauthorized[0]==401 and conflict==(409,{
                    "error":"EXTERNAL_CHANGE_ID_REUSED"}) and
                s.physical()["app-b"]==app_b,
                {"B2Reconciliation":"CONFIRMED",
                 "outboundAttempts":1,
                 "externalEffectCountAfterRetry":1,
                 "externalReceiptCountAfterRetry":1,
                 "unauthorizedReceiptHTTP":unauthorized[0],
                 "changedPayloadSameChangeIdHTTP":conflict[0],
                 "noOtherAppEffect":True})

        # Independent Kernel receipt includes original workflow identity.
        x=s.physical()["app-a"]
        record=[r for r in x["records"] if r["id"]==self.record_id]
        s.check("P0B-48-W20-independent-B2-B11-external-oracles-no-side-effect-replay",
                len(record)==1 and
                record[0]["version"]==2 and
                record[0]["value"]["status"]=="PendingLevel1" and
                self.cons._inspect()["cursor"]==9 and
                self.cons._inspect()["receiptCount"]==9 and
                self.pub._head(9,7,seconds=4)["epoch"]==7 and
                s._request()[0]==200 and
                reread["remote_receipt"] is not None and
                physical["effects"][0]["payload_hash"]==
                  remote["payloadHash"] and
                self.external.poll() is None,
                {"originalB2RecordVersion":2,
                 "originalB2WorkflowStatus":"PendingLevel1",
                 "B11NativeReceiptCursor":9,
                 "externalCommittedBusinessId":timed["changeId"],
                 "externalResponseWasTimeout":True,
                 "B2OriginalChangeIdReceipt":"CONFIRMED",
                 "autoRetryCount":0,"G1FormalW20FullPass":False})

        return {"checks":5,"realB2Workflow":True,
                "externalBusinessSeparateLinuxUid":uid,
                "externalPhysicalEffectCount":1,
                "B2ExternalDispatchState":"CONFIRMED",
                "outboundAttempts":1,"B11NativeCursor":9,
                "B2ActivationEpoch":7,"g1Passed":False}

    def stop(self):
        if self.external is not None:
            try:
                pid=json.loads(self.ready.read_text()).get("pid")
                if pid:
                    self.s.execute(["sudo","-n","kill","-TERM",
                                    str(pid)],strict=False)
                self.external.wait(timeout=5)
            except Exception:
                self.external.terminate()
            self.external=None
