"""G1 P0-B-24..33: B2 single-transaction active-publication CAS in SAME B9.

Reuse existing trusted Domain Kernel, actual B11/B14 durable consumer,
saltcorn, B15 Publisher, same B17 public browser.  No second Kernel or
domain DB. The controller is research-authorized publisher (not SSO).

A Publisher PREPARE alone must never make a new candidate visible: Kernel
atomically records content-addressed verified snapshot identity against
the current release and *business* head. Reader binds every GET to
B2's committed epoch+snapshot and checks the current source in the
same Kernel read transaction before and after.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError
from urllib.request import Request,urlopen

KERN="ailcapb9kern"
PUBL="ailcapb9pub"


class PublicationActivationRound:
    def __init__(self,suite,consumer):
        self.s=suite
        self.cons=consumer
        self.first=None
        self.first_command=None

    def _tool(self,tool,token,args,app="app-a"):
        req=Request(
            self.s.base+"/v3/apps/"+app+"/tools/"+tool,
            data=json.dumps(args,separators=(",",":")).encode(),
            headers=({"Authorization":"Bearer "+token}
                     if token is not None else {})|{
                         "Content-Type":"application/json"},
            method="POST")
        try:
            with urlopen(req,timeout=12) as resp:
                return resp.status,json.loads(resp.read(5000))
        except HTTPError as exc:
            return exc.code,json.loads(exc.read(5000))

    def _state(self):
        code,result=self._tool("publication.read",self.s.token,{})
        if code!=200:
            raise AssertionError("P0B_PUBLICATION_STATE_NOT_AVAILABLE_"+str(result))
        return result

    def _activate(self,cmd,token=None):
        return self._tool(
            "publication.activate",
            self.s.publisher_token if token is None else token,cmd)

    def _cmd(self,candidate,epoch,change_id,head):
        return {
            "changeId":change_id,"expectedEpoch":epoch,
            "candidateSha256":candidate["snapshotSha256"],
            "expectedVersion":candidate["version"],
            "expectedOutboxHead":head
        }

    def _prepare(self,tag,*,failure=False):
        signed=self.s._sign()
        native=self.s.native_physical(self.cons.native_db)
        return self.s._publish(
            tag,self.s._candidate(signed,native),
            failure=failure,prepare=True)

    def _physical(self):
        script=(
            "import json,sqlite3,sys\n"
            "db=sqlite3.connect('file:'+sys.argv[1]+'?mode=ro',uri=True)\n"
            "db.row_factory=sqlite3.Row\n"
            "r=db.execute('SELECT * FROM p0b_public_activations "
            "WHERE app=\\'app-a\\'').fetchone()\n"
            "x=db.execute('SELECT change_id FROM p0b_activation_receipts "
            "WHERE app=\\'app-a\\' ORDER BY change_id').fetchall()\n"
            "release=db.execute('SELECT current_release FROM apps "
            "WHERE app=\\'app-a\\'').fetchone()[0]\n"
            "head=db.execute('SELECT COUNT(*) FROM b11_outbox "
            "WHERE app=\\'app-a\\'').fetchone()[0]\n"
            "print('P0B_ATOMIC_B2_SQL|'+json.dumps({"
            "'active':dict(r) if r else None,"
            "'receipts':[x[0] for x in x],"
            "'currentRelease':release,'outboxHead':head}))\n")
        result=self.s._user_call(
            KERN,["-c",script,self.s.authority_db],timeout=15)
        return self.s.single(result.stdout,"P0B_ATOMIC_B2_SQL")

    def _artifact(self,sha,operation):
        path=self.s.pubdir/"candidates"/(sha+".sqlite")
        script=(
            "import os,sys,pathlib,hashlib\n"
            "p=pathlib.Path(sys.argv[1]);a=sys.argv[2]\n"
            "backup=p.with_suffix('.backup')\n"
            "if a=='corrupt':\n"
            " raw=p.read_bytes()\n"
            " if hashlib.sha256(raw).hexdigest()!=p.stem:"
            " raise RuntimeError('SOURCE_CANDIDATE_NAME_HASH_DRIFT')\n"
            " fd=os.open(backup,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o640)\n"
            " with os.fdopen(fd,'wb') as f:"
            "  f.write(raw);f.flush();os.fsync(f.fileno())\n"
            " with open(p,'r+b') as f:"
            "  f.write(b'P0B_CORRUPTED_SQLITE!');f.flush();os.fsync(f.fileno())\n"
            "elif a=='restore':\n"
            " os.replace(backup,p)\n"
            " folder=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)\n"
            " try:os.fsync(folder)\n"
            " finally:os.close(folder)\n"
            " if hashlib.sha256(p.read_bytes()).hexdigest()!=p.stem:"
            "  raise RuntimeError('FAILED_TO_RESTORE_SIGNED_CANDIDATE')\n"
            "else:raise RuntimeError('OPERATION_FORBIDDEN')\n"
            "print('P0B_CANDIDATE_'+a.upper()+'|'+p.stem)\n")
        return self.s._user_call(PUBL,["-c",script,path,operation],timeout=12)

    def _kernel_injected_rollback(self,cmd):
        script=(
            "import json,sys\n"
            "sys.path.insert(0,sys.argv[1])\n"
            "from p0b_activation import Activation,ActivationRejected\n"
            "try:\n"
            " Activation(sys.argv[2]).activate("
            "'b9-human-approved-release',json.loads(sys.argv[3]),"
            "fail_before_commit=True)\n"
            "except ActivationRejected as exc:\n"
            " print('P0B_ACTIVATION_INJECT|'+exc.code)\n"
            "else:\n"
            " raise RuntimeError('INJECTED_ACTIVATION_WAS_COMMITTED')\n")
        response=self.s._user_call(
            KERN,["-c",script,self.s.stage/"g1-b01-b9",
                  self.s.authority_db,json.dumps(cmd)])
        return response.stdout.strip()

    def run(self):
        s=self.s
        head=s._business_head()
        start=self._state()
        legacy_sha=s._sha()
        before_http=s._request()[0]
        candidate_status,candidate=self._prepare("p0b-before-commit-three")
        after_prepare=self._state()
        phys0=self._physical()
        s.check("P0B-24-B15-fsync-prepared-candidate-not-active-until-B2-CAS",
                candidate_status==0 and candidate["prepared"] is True and
                candidate["activationRequired"] is True and
                len(candidate["snapshotSha256"])==64 and
                head["head"]==3 and start["epoch"]==0 and
                start["active"] is None and after_prepare==start and
                phys0["active"] is None and phys0["receipts"]==[] and
                s._sha()==legacy_sha and before_http==200 and
                s._request()[0]==200,
                {"preparedArtifactSha256":candidate["snapshotSha256"],
                 "legacySnapshotBytesUnchanged":True,
                 "KernelActiveEpoch":0,"publicReadStill":200,
                 "persistentActivationRowBefore":None})

        cmd=self._cmd(candidate,0,"p0b-first-atomic-activation",3)
        denied=self._activate(cmd,token=s.token)
        anonymous=self._tool("publication.activate",None,cmd)
        forbidden_app=self._tool("publication.activate",s.publisher_token,
                                 cmd,app="app-b")
        missing=self._activate(
            {**cmd,"changeId":"p0b-missing-candidate",
             "candidateSha256":"0"*64})
        wrong_epoch=self._activate(
            {**cmd,"changeId":"p0b-incorrect-epoch","expectedEpoch":1})
        s.check("P0B-25-Kernel-activation-rejects-unauthorized-stale-and-missing",
                denied==(403,{"error":"TOOL_NOT_GRANTED"}) and
                anonymous[0]==401 and forbidden_app[0]==403 and
                missing==(409,{"error":"ACTIVATION_CANDIDATE_INVALID"}) and
                wrong_epoch==(409,{"error":"ACTIVATION_EPOCH_CONFLICT"}) and
                self._physical()==phys0 and s._request()[0]==200,
                {"readOnlyActivateHTTP":denied[0],
                 "unauthorizedHTTP":anonymous[0],
                 "crossAppHTTP":forbidden_app[0],
                 "missingSignedArtifact":missing[1].get("error"),
                 "staleCAS":wrong_epoch[1].get("error"),
                 "noKernelActivationCommitted":True})

        broken_status,broken=self._prepare("p0b-injected-prepared-build",
                                           failure=True)
        s.check("P0B-26-publisher-preparation-failure-leaves-B2-pointer-unchanged",
                broken_status==2 and
                broken=="PUBLISH_BUILD_FAILURE_INJECTED" and
                self._physical()==phys0 and s._sha()==legacy_sha and
                s._request()[0]==200,
                {"failure":broken,"noActiveMutation":True,
                 "B17LegacyStill200":True,
                 "unchangedLiveSnapshotSha":legacy_sha})

        response,activated=self._activate(cmd)
        first=self._state()
        now=self._physical()
        s.page.reload(wait_until="domcontentloaded")
        page,headers,body=s._request()
        s.check("P0B-27-single-B2-TX-commit-signed-content-hash-epoch",
                response==200 and activated["decision"]=="ACTIVATED" and
                activated["epoch"]==1 and
                first["epoch"]==1 and
                first["active"]["snapshotSha256"]==
                   candidate["snapshotSha256"] and
                first["active"]["rowsDigest"]==head["rowsDigest"] and
                first["active"]["outboxHead"]==3 and
                first["source"]=={
                    k:first["active"][k] for k in first["source"]
                } and
                now["active"]["epoch"]==1 and
                now["active"]["candidate_sha"]==
                    candidate["snapshotSha256"] and
                now["receipts"]==[cmd["changeId"]] and
                s._sha()==legacy_sha and
                page==200 and headers.get("X-OpenAILCAP-Release")=="1" and
                s.page.locator("tbody tr").count()==3 and
                s.router.poll() is None,
                {"B2AtomicEpoch":1,"DBRelease":now["currentRelease"],
                 "DBOutboxHead":now["outboxHead"],
                 "ReaderSHA":candidate["snapshotSha256"],
                 "publicChromiumRows":3,
                 "oldPublisherLegacyFileNotReplaced":True,
                 "durableActivationReceipt":cmd["changeId"]})

        repeat=self._activate(cmd)
        reused=self._activate(
            {**cmd,"expectedEpoch":0,"candidateSha256":"0"*64})
        stale=self._activate(
            {**cmd,"changeId":"p0b-stale-epoch-after-commit"})
        s.check("P0B-28-activation-changeId-idempotency-CAS-conflict",
                repeat[0]==200 and repeat[1]["replayed"] is True and
                repeat[1]["epoch"]==1 and
                reused==(409,{"error":"ACTIVATION_CHANGE_ID_REUSED"}) and
                stale==(409,{"error":"ACTIVATION_EPOCH_CONFLICT"}) and
                self._state()==first and
                self._physical()==now and s._request()[0]==200,
                {"replayedSameChangeId":True,
                 "changedReceiptPayload":"DENIED",
                 "staleExpectedEpoch":"DENIED",
                 "B2PhysicalReceiptCount":1})

        self._artifact(candidate["snapshotSha256"],"corrupt")
        corrupted=s._request()[0]
        s.page.reload(wait_until="domcontentloaded")
        unchanged=self._state()
        self._artifact(candidate["snapshotSha256"],"restore")
        recovered=s._request()[0]
        s.page.reload(wait_until="domcontentloaded")
        s.check("P0B-29-post-activation-file-tamper-fails-closed-and-recovers",
                corrupted==503 and
                unchanged==first and recovered==200 and
                s.page.locator("tbody tr").count()==3 and
                s._sha()==legacy_sha and
                self._state()==first and self._physical()==now,
                {"tamperedContentAddressedSQL_HTTP":503,
                 "restoredVerifiedB17HTTP":200,
                 "noEpochMutation":True,
                 "noUnverifiedHTMLServed":True,
                 "sameRunningReaderAndBrowser":True})

        # The already-active Kernel pointer covers B11 head=3. A fourth
        # *real B2 human form submission* must invalidate it even when
        # the consumer catches up automatically under the same release v1.
        post=self.cons.human_page.evaluate("""async () => {
          const r=await fetch("/v2/apps/app-a/runtime/forms/form.contracts/records",{
            method:"POST",credentials:"same-origin",
            headers:{"Content-Type":"application/json","X-CSRF-Token":csrf},
            body:JSON.stringify({contract_no:"HT-2026-000004",
              title:"S1 Atomic Activation Contract",
              amount_minor:400000004})
          });
          return {status:r.status,body:await r.json()};
        }""")
        future=s._business_head()
        caught_up=self.cons._wait_native(4,seconds=17)
        changed=self._state()
        before_switch=s._request()[0]
        s.page.reload(wait_until="domcontentloaded")
        s.check("P0B-30-new-B2-business-commit-invalidates-old-active-epoch",
                post["status"]==200 and future["head"]==4 and
                caught_up["cursor"]==4 and caught_up["receiptCount"]==4 and
                changed["epoch"]==1 and changed["active"]==first["active"] and
                changed["source"]["outboxHead"]==4 and
                changed["source"]["rowsDigest"]!=first["source"]["rowsDigest"] and
                before_switch==503 and s.page.locator("th").count()==0 and
                s._sha()==legacy_sha and s.router.poll() is None,
                {"realHumanB2FormHTTP":post["status"],
                 "sourceOutboxHead":4,"automaticSignedConsumerCursor":4,
                 "activeEpochStill":1,
                 "beforeActivationBrowserHTTP":503,
                 "oldSignedCandidateNotSuperseded":True})

        stale_activation=self._activate(
            {**cmd,"changeId":"p0b-trying-to-promote-old-head",
             "expectedEpoch":1})
        new_status,new_candidate=self._prepare("p0b-fourth-business-ready")
        pending=self._state()
        s.check("P0B-31-old-prepared-artifact-rejected-new-candidate-invisible",
                stale_activation==(409,{"error":"ACTIVATION_B2_SOURCE_MOVED"}) and
                new_status==0 and new_candidate["prepared"] and
                new_candidate["snapshotSha256"]!=candidate["snapshotSha256"] and
                self.cons._inspect()["cursor"]==4 and
                pending["epoch"]==1 and
                pending["active"]==first["active"] and
                pending["source"]["outboxHead"]==4 and
                s._request()[0]==503 and
                self._physical()=={
                    **now,"outboxHead":4
                },
                {"outdatedCandidate":"DENIED",
                 "newPreparedHead":4,"B2AtomicEpochNotMoved":1,
                 "noDirectPublisherSwap":True,
                 "B17StillFailClosed":True})
        nextcmd=self._cmd(
            new_candidate,1,"p0b-failure-then-real-CAS-one",4)
        injected=self._kernel_injected_rollback(nextcmd)
        after_inject=self._physical()
        s.check("P0B-32-Kernel-B2-TX-injected-precommit-failure-rolls-back",
                injected=="P0B_ACTIVATION_INJECT|ACTIVATION_FAILURE_INJECTED" and
                after_inject=={
                    **now,"outboxHead":4
                } and
                self._state()==pending and
                s._request()[0]==503 and s._sha()==legacy_sha,
                {"injectedKernelPreCommitException":True,
                 "noActivationReceiptPersisted":True,
                 "B2AtomicEpochStill":1,
                 "readerNeverServedStale":True})

        contenders=[
            nextcmd,
            {**nextcmd,"changeId":"p0b-concurrent-CAS-loser"}
        ]
        with ThreadPoolExecutor(max_workers=2) as pool:
            result=list(pool.map(self._activate,contenders))
        successes=[value for value in result if value[0]==200]
        conflict=[value for value in result if value[0]==409]
        final=self._state()
        physically=self._physical()
        s.page.reload(wait_until="domcontentloaded")
        http,headers,html=s._request()
        s.check("P0B-33-two-concurrent-Kernel-CAS-one-wins-four-live-rows",
                len(successes)==1 and
                successes[0][1]["replayed"] is False and
                successes[0][1]["decision"]=="ACTIVATED" and
                successes[0][1]["epoch"]==2 and
                len(conflict)==1 and conflict[0][1]=={
                    "error":"ACTIVATION_EPOCH_CONFLICT"} and
                final["epoch"]==2 and
                final["active"]["snapshotSha256"]==
                    new_candidate["snapshotSha256"] and
                final["source"]["outboxHead"]==4 and
                physically["active"]["epoch"]==2 and
                physically["active"]["candidate_sha"]==
                    new_candidate["snapshotSha256"] and
                len(physically["receipts"])==2 and
                physically["outboxHead"]==4 and
                http==200 and headers.get("X-OpenAILCAP-Release")=="1" and
                s.page.locator("tbody tr").count()==4 and
                "HT-2026-000004" in html.decode() and
                self.cons._inspect()["clean"] and
                self.cons._inspect()["cursor"]==4 and
                s._sha()==legacy_sha and s.router.poll() is None and
                s.physical()["app-b"]==s.app_b,
                {"concurrentActivateHTTP":[x[0] for x in result],
                 "atomicB2PublicationEpoch":2,
                 "activationReceipts":physically["receipts"],
                 "finalB2Release":physically["currentRelease"],
                 "finalB11Head":physically["outboxHead"],
                 "publicB17ChromiumRows":4,
                 "sameRouterAndLegacyBytes":True,
                 "modelCalls":0})
        return {
            "checks":10,"atomicKernelB2ActivationEpoch":2,
            "verifiedImmutableContentAddressedCandidate":True,
            "consumerDurableCursor":4,
            "B17ChromiumRows":4,
            "postActivationTamper503":True,
            "crashBeforeCommitRollback":True,
            "actualConcurrentCasOneWinner":True,
            "oldB2ReleaseVersion":1,
            "productionZeroDowntime":False,
            "crossDbAtomic":False,
            "g1Passed":False
        }
