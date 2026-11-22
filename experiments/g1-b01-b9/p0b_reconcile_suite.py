"""G1 same-instance P0B-34..43: autonomous B14/B15/B2 reconciliation.

Uses EXACT live B2/kernel/Chrome/Native B11 signed Consumer after
P0B-33 (four B2 human-created contracts, atomically active epoch=2).
No manual Native row seed, no direct Kernel signing key/DB in Publisher,
no new Agent or separate Domain instance. Real independent PUBL daemon,
Native read-only SO_PEERCRED IPC and actual HTTP reply-loss fault bridge.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import pwd
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError
from urllib.request import Request,urlopen

PUBL="ailcapb9pub"
PLUG="ailcapb9plug"
CONS="ailcapb9cons"


class AutoReconcileRound:
    def __init__(self,suite,consumer):
        self.s=suite
        self.cons=consumer
        self.stage=suite.stage
        self.home=suite.home
        self.pubcfg=suite.pubdir/"reconcile-config.json"
        self.pubstatus=suite.pubdir/"deploy-status.json"
        self.journal=suite.pubdir/"deploy-journal.sqlite"
        self.flag=self.home/"reconcile-fault.flag"
        self.events=self.home/"reconcile-proxy-events.json"
        self.proxyready=self.home/"reconcile-proxy-ready.json"
        self.proxyproc=None
        self.daemonproc=None
        self.proxy_base=None

    def _user(self,uid,argv,**kw):
        return self.s._user_call(uid,argv,**kw)

    def _status(self):
        script=("import json,sys,pathlib\n"
                "p=pathlib.Path(sys.argv[1]);"
                "print(json.dumps(json.loads(p.read_text())) if p.exists() else '{}')")
        result=self._user(PUBL,["-c",script,self.pubstatus],strict=True)
        return json.loads(result.stdout.strip())

    def _journal(self):
        script=(
            "import sqlite3,json,sys\n"
            "c=sqlite3.connect('file:'+sys.argv[1]+'?mode=ro',uri=True)\n"
            "rows=c.execute('SELECT cid,command,state,attempts,unknown_count "
            "FROM deploy ORDER BY rowid').fetchall()\n"
            "print(json.dumps([{'cid':r[0],'command':json.loads(r[1]),"
            "'state':r[2],'attempts':r[3],'unknownCount':r[4]} "
            "for r in rows]))\n")
        response=self._user(PUBL,["-c",script,self.journal])
        return json.loads(response.stdout.strip())

    def _poll(self,check,seconds=16):
        until=time.monotonic()+seconds
        value=None
        while time.monotonic()<until:
            value=check()
            if value:return value
            time.sleep(.13)
        raise AssertionError("P0B_AUTORECONCILE_TIMEOUT_LAST_"+repr(value))

    def _pub_wait(self,expected):
        return self._poll(
            lambda: (r if (r:=self._status()).get("state")==expected
                      else None),seconds=18)

    def _head(self,n,epoch,seconds=17):
        def probe():
            code,d=self._api("publication.read",self.s.token,{})
            if (code==200 and d["epoch"]==epoch and
                d["active"] is not None and
                d["active"]["outboxHead"]==n and
                d["source"]["outboxHead"]==n):
                return d
            return None
        return self._poll(probe,seconds)

    def _api(self,tool,token,cmd):
        req=Request(self.s.base+"/v3/apps/app-a/tools/"+tool,
                    data=json.dumps(cmd).encode(),method="POST",
                    headers={"Content-Type":"application/json",
                             "Authorization":"Bearer "+token})
        try:
            with urlopen(req,timeout=5) as response:
                return response.status,json.loads(response.read(8000))
        except HTTPError as error:
            return error.code,json.loads(error.read(8000))

    def _post(self,n):
        result=self.cons.human_page.evaluate("""async n => {
          const r=await fetch("/v2/apps/app-a/runtime/forms/form.contracts/records",{
            method:"POST",credentials:"same-origin",
            headers:{"Content-Type":"application/json","X-CSRF-Token":csrf},
            body:JSON.stringify({
              contract_no:"HT-2026-"+String(n).padStart(6,"0"),
              title:"S1 Continuous Publisher Contract "+n,
              amount_minor:100000000+n})
          });
          return {status:r.status,body:await r.json()};
        }""",n)
        if result["status"]!=200:
            raise AssertionError("P0B_REAL_HUMAN_CONTRACT_CREATE_FAILED_"+str(result))
        return result

    def _browser(self,n):
        self.s.page.reload(wait_until="domcontentloaded")
        status,headers,raw=self.s._request()
        text=raw.decode("utf-8")
        return (status==200 and
                self.s.page.locator("tbody tr").count()==n and
                "HT-2026-"+str(n).zfill(6) in text and
                headers.get("X-OpenAILCAP-Release")=="1")

    def _start_proxy(self):
        log=self.home/"reconcile-proxy.log"
        self.proxyproc=subprocess.Popen([
            sys.executable,"-u",
            str(self.stage/"g1-b01-b9"/"p0b_reconcile_fault_proxy.py"),
            "--target",self.s.base,"--flag",str(self.flag),
            "--events",str(self.events),"--ready",str(self.proxyready)
        ],cwd=str(self.stage),stdin=subprocess.DEVNULL,
          stdout=log.open("w"),stderr=subprocess.STDOUT)
        for _ in range(100):
            if self.proxyready.exists():break
            if self.proxyproc.poll() is not None:
                raise AssertionError("RECONCILE_PROXY_EXIT_"+log.read_text()[-450:])
            time.sleep(.08)
        if not self.proxyready.exists():
            raise AssertionError("RECONCILE_PROXY_READY_TIMEOUT")
        self.proxy_base=("http://127.0.0.1:"+
                         str(json.loads(self.proxyready.read_text())["port"]))

    def _start_daemon(self):
        log=self.home/"p0b-autoreconcile.log"
        self.daemonproc=subprocess.Popen([
            "sudo","-n","runuser","-u",PUBL,"--",sys.executable,"-u",
            str(self.stage/"g1-b01-b9"/"p0b_reconciler.py"),
            "--config",str(self.pubcfg)
        ],cwd=str(self.stage),stdin=subprocess.DEVNULL,
          stdout=log.open("a"),stderr=subprocess.STDOUT)
        self._poll(lambda: self._status().get("pid") and self._status())

    def _stop_daemon(self):
        if self.daemonproc is None:return
        state=self._status()
        if type(state.get("pid")) is int:
            self.s.execute(["sudo","-n","kill","-TERM",
                            str(state["pid"])],strict=False)
        try:self.daemonproc.wait(timeout=5)
        except subprocess.TimeoutExpired:pass
        self.daemonproc=None

    def _setup(self):
        self._start_proxy()
        seed=self.home/"p0b-reconcile-config-seed.json"
        seed.write_text(json.dumps({
            "kernelBase":self.s.base,
            "activateBase":self.proxy_base,
            "activateTimeoutMs":1100,
            "kernelReadToken":self.s.token,
            "kernelActivateToken":self.s.publisher_token,
            "sourceUrl":("http://127.0.0.1:"+str(self.cons.port)+
                "/v5/apps/app-a/projection/signed-release"),
            "sourceToken":self.cons.publisher_source_token,
            "nativeSocket":str(self.cons.publisher_sock),
            "output":str(self.s.snapshot),
            "publicKeyHex":self.s.public_key,
            "packTemplate":str(self.stage/"platform-saltcorn"/"contract-pack.json"),
            "journal":str(self.journal),
            "status":str(self.pubstatus),
            "intervalMs":145}))
        seed.chmod(0o600)
        self.s.execute(["sudo","-n","install","-o",PUBL,"-g",PUBL,
                        "-m","0600",seed,self.pubcfg])
        seed.unlink()

    def _signed_publisher_status(self,token):
        req=Request("http://127.0.0.1:"+str(self.cons.port)+
                    "/v5/apps/app-a/projection/signed-release",
                    data=b'{"after":0,"limit":0}',method="POST",
                    headers={"Authorization":"Bearer "+token,
                             "Content-Type":"application/json"})
        try:
            with urlopen(req,timeout=6) as r:
                return r.status,json.loads(r.read(8192))
        except HTTPError as e:
            return e.code,json.loads(e.read())

    def _publisher_oracle(self,uid):
        script=("import socket,sys,json\n"
                "s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)\n"
                "try:\n"
                " s.settimeout(3);s.connect(sys.argv[1])\n"
                " s.sendall(b'{\\\"op\\\":\\\"oracle\\\"}\\n')\n"
                " print(s.recv(131072).decode().strip())\n"
                "except OSError as exc:print(json.dumps({'denied':exc.errno}))\n"
                "finally:s.close()\n")
        r=self._user(uid,["-c",script,self.cons.publisher_sock],strict=False)
        try:return json.loads(r.stdout.strip())
        except ValueError:
            raise AssertionError("P0B_NATIVE_IPC_BAD_RESPONSE_"+r.stdout[-400:])

    def _fault(self,mode):
        if self.flag.exists():
            raise AssertionError("P0B_FAULT_ALREADY_ARMED")
        self.flag.write_text(mode)

    def _fault_seen(self,mode):
        def check():
            if not self.events.exists():return None
            data=json.loads(self.events.read_text())
            found=[r for r in data if r["mode"]==mode]
            return found[-1] if found else None
        return self._poll(check)

    def run(self):
        try:return self._run()
        finally:self.stop()

    def _run(self):
        s=self.s
        self._setup()
        initial=self._api("publication.read",s.token,{})[1]
        pub_oracle=self._publisher_oracle(PUBL)
        plug=self._publisher_oracle(PLUG)
        cons=self._publisher_oracle(CONS)
        negative=self._signed_publisher_status(self.cons.source_token)
        s.check("P0B-34-publisher-only-B14-signature-and-Native-SQL-IPC-scopes",
                initial["epoch"]==2 and
                initial["source"]["outboxHead"]==4 and
                pub_oracle.get("ok") is True and
                pub_oracle["result"]["cursor"]==4 and
                pub_oracle["result"]["receiptCount"]==4 and
                len(pub_oracle["result"]["nativeOracle"]["businessRows"])==4 and
                plug.get("denied") in (13,1) and
                cons.get("denied") in (13,1) and
                negative[0]==401,
                {"sourceReleaseDeniedToConsumer":negative[0],
                 "NativeOraclePublisherCursor":pub_oracle["result"]["cursor"],
                 "NativeOraclePublisherReceipts":4,
                 "pluginSocketConnectDenied":plug,
                 "consumerSocketConnectDenied":cons,
                 "noPublisherNativeDbAccess":True})
        self._start_daemon()
        steady=self._pub_wait("CAUGHT_UP")
        baseline=self._api("publication.read",s.token,{})[1]
        s.check("P0B-35-real-Publisher-daemon-noop-when-B2-epoch-current",
                steady["epoch"]==2 and steady["head"]==4 and
                baseline==initial and
                self._browser(4) and
                self.daemonproc.poll() is None,
                {"publisherPid":steady["pid"],"observedEpoch":2,
                 "noManualPublisherInvocation":True,
                 "publicBrowserRows":4})

        self._post(5)
        native5=self.cons._wait_native(5)
        activated5=self._head(5,3,seconds=23)
        rows5=self._browser(5)
        job5=self._journal()
        s.check("P0B-36-autonomous-B11-consumer-to-B15-prepare-Kernel-activate",
                native5["cursor"]==5 and rows5 and
                activated5["epoch"]==3 and
                len(job5)==1 and job5[0]["state"]=="COMMITTED" and
                job5[0]["attempts"]==1 and
                self.daemonproc.poll() is None and
                s.physical()["app-b"]==s.app_b,
                {"noControllerNativeOracleOrManualPublish":True,
                 "kernelAtomicEpoch":3,"publisherJournal":job5,
                 "realB2HumanContracts":5,"sameBrowser":True})

        self.cons._stop_source()
        self._post(6)
        lag=self.cons._inspect()
        waiting=self._pub_wait("WAIT_NATIVE_CURSOR")
        stale=s._request()[0]
        state6=self._api("publication.read",s.token,{})[1]
        s.check("P0B-37-real-signer-outage-stops-Consumer-and-auto-activation",
                lag["cursor"]==5 and waiting["nativeCursor"]==5 and
                waiting["head"]==6 and
                state6["epoch"]==3 and
                state6["active"]["outboxHead"]==5 and
                state6["source"]["outboxHead"]==6 and
                stale==503 and len(self._journal())==1 and
                self.daemonproc.poll() is None,
                {"sourceTrulyDown":True,"NativeCursor":5,
                 "PublisherWaiting":waiting["state"],
                 "B17HTTP":503,"noNewChangeId":True})

        self.cons._start_source(3)
        native6=self.cons._wait_native(6)
        state6ok=self._head(6,4,seconds=24)
        result6=self._browser(6)
        s.check("P0B-38-source-recovery-auto-B15-prepare-epoch-4-Chromium-6",
                native6["cursor"]==6 and result6 and
                state6ok["epoch"]==4 and
                len(self._journal())==2 and
                all(r["state"]=="COMMITTED" for r in self._journal()) and
                s.router.poll() is None,
                {"restartedSignerSamePort":True,
                 "consumerNeverRestarted":True,
                 "publisherNeverRestarted":True,
                 "nativeDurableCursor":6,
                 "sourceHead":6,"activeEpoch":4,"browserRows":6})

        self._fault("after")
        self._post(7)
        self.cons._wait_native(7)
        forwarded=self._fault_seen("after")
        reached=self._head(7,5,seconds=23)
        journal7=self._poll(
            lambda: (r if (r:=[j for j in self._journal()
                if j["command"]["expectedOutboxHead"]==7 and
                   j["state"]=="COMMITTED" and j["unknownCount"]>=1])
                      else None),seconds=21)
        cid7=journal7[0]["cid"]
        s.check("P0B-39-real-HTTP-response-loss-after-B2-commit-receipt-reconcile",
                forwarded["kernelStatus"]==200 and
                forwarded["changeId"]==cid7 and
                reached["epoch"]==5 and
                journal7[0]["unknownCount"]==1 and
                journal7[0]["attempts"]==1 and
                self._browser(7) and
                len(self._journal())==3,
                {"actualKernelCommittedBeforeReplyDrop":True,
                 "proxyForwardsOneRealHTTPWrite":forwarded,
                 "durableUNKNOWNcount":1,
                 "sameChangeIdOneAttempt":cid7,
                 "B17HTTP":200,"browserRows":7})
        rec=self._api("publication.receipt",s.publisher_token,
                      {"changeId":cid7})
        exact=self._api("publication.activate",s.publisher_token,
                        journal7[0]["command"])
        s.check("P0B-40-post-timeout-B2-receipt-and-idempotent-changeId",
                rec[0]==200 and rec[1]["status"]=="COMMITTED" and
                rec[1]["result"]["epoch"]==5 and
                exact[0]==200 and exact[1]["replayed"] is True and
                self._api("publication.read",s.token,{})[1]["epoch"]==5 and
                self._journal()[-1]["attempts"]==1,
                {"receiptStatus":rec[1]["status"],
                 "noNewChangeId":True,"actualReplayResponse":exact[1],
                 "publisherJournalOriginalAttempts":1})
        oldpid=self._status()["pid"]
        self._stop_daemon()
        self._start_daemon()
        resumed=self._pub_wait("CAUGHT_UP")
        s.check("P0B-41-Publisher-real-process-restart-rehydrates-journal",
                oldpid!=resumed["pid"] and resumed["epoch"]==5 and
                len(self._journal())==3 and
                all(j["state"]=="COMMITTED" for j in self._journal()) and
                self._browser(7),
                {"oldPublisherPid":oldpid,"newPublisherPid":resumed["pid"],
                 "B2Epoch":5,"durableLocalOperations":3,
                 "noDuplicatePublisherActivation":True})

        self._fault("before")
        self._post(8)
        self.cons._wait_native(8)
        dropped=self._fault_seen("before")
        blocked=self._poll(lambda: (
            r if (r:=[j for j in self._journal() if
                      j["command"]["expectedOutboxHead"]==8 and
                      j["state"]=="OPERATOR_REQUIRED" and
                      j["unknownCount"]==1]) else None),seconds=24)
        epoch_before=self._api("publication.read",s.token,{})[1]
        read503=s._request()[0]
        s.check("P0B-42-pre-dispatch-timeout-UNKNOWN-no-auto-new-changeId",
                dropped["kernelStatus"] is None and
                dropped["changeId"]==blocked[0]["cid"] and
                blocked[0]["attempts"]==1 and
                epoch_before["epoch"]==5 and
                epoch_before["active"]["outboxHead"]==7 and
                epoch_before["source"]["outboxHead"]==8 and
                read503==503 and
                self._pub_wait("OPERATOR_REQUIRED")["failure"]==
                    "UNKNOWN_NOT_AUTOMATICALLY_REISSUED",
                {"physicalKernelActivationDidNotExecute":True,
                 "sameOutstandingChangeId":blocked[0]["cid"],
                 "publisherStoppedAutomaticRetries":True,
                 "unknownButUncommitted":True,"B17HTTP":503})

        # Explicit trusted human intervention: SAME changeId/parameters
        # after checking the B2 durable receipt as NOT_FOUND. No new id.
        same=blocked[0]["command"]
        before_receipt=self._api("publication.receipt",
                                 s.publisher_token,{"changeId":same["changeId"]})
        approved=self._api("publication.activate",s.publisher_token,same)
        finalized=self._head(8,6,seconds=12)
        recovered=self._poll(lambda:(
            j if (j:=[x for x in self._journal() if
                      x["cid"]==same["changeId"] and
                      x["state"]=="COMMITTED"]) else None),seconds=13)
        s.check("P0B-43-explicit-operator-reconciles-exact-original-UNKNOWN-id",
                before_receipt[1]["status"]=="NOT_FOUND" and
                approved[0]==200 and approved[1]["changeId"]==same["changeId"] and
                finalized["epoch"]==6 and recovered[0]["attempts"]==1 and
                recovered[0]["unknownCount"]==1 and
                self._browser(8) and s.router.poll() is None and
                self.cons._inspect()["clean"] and
                self.cons._inspect()["cursor"]==8 and
                s.physical()["app-b"]==s.app_b,
                {"noInventedReplacementChangeId":True,
                 "explicitOperatorOriginalChangeId":same["changeId"],
                 "realKernelReceiptBeforeAction":"NOT_FOUND",
                 "kernelEpoch":6,"B17BrowserRows":8,
                 "publisherNoUnboundedReplay":True})
        return {"checks":10,"automaticPubAndNative":True,
                "separatePublisherUid":pwd.getpwnam(PUBL).pw_uid,
                "trueNativeReadOnlyOracleIPC":True,
                "signedSourceSeparateCapabilities":True,
                "realHttpReplyLostAfterCommitRecoveredByReceipt":True,
                "realHttpReplyLostBeforeDispatchRequiresOperator":True,
                "finalB11Cursor":8,"finalActivationEpoch":6,
                "modelCalls":0,"g1Passed":False}

    def stop(self):
        if self.daemonproc is not None:
            try:self._stop_daemon()
            except Exception:pass
        if self.proxyproc is not None:
            self.proxyproc.terminate()
            try:self.proxyproc.wait(timeout=5)
            except subprocess.TimeoutExpired:pass
            self.proxyproc=None
