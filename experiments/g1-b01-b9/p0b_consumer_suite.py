"""P0-B-16..23: same B2 authority, B11/B14 autonomous durable consumer,
existing B15/B17 publisher/Chrome; real process, SQLite, AF_UNIX and outage.
No second Domain Kernel/authority and no manual Saltcorn row-seeding.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import pwd
import secrets
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError
from urllib.request import Request,urlopen


KERN="ailcapb9kern"
RUNT="ailcapb9run"
PLUG="ailcapb9plug"
PUBL="ailcapb9pub"
READ="ailcapb9ro"
CONS="ailcapb9cons"
IPC_GROUP="ailcapb9ipc"
ROUTE="/v5/apps/app-a/projection/signed-pull"


class ConsumerRound:
    def __init__(self,suite,*,native_cmd,native_runtime,human_page):
        self.s=suite
        self.native_cmd=native_cmd
        self.human_page=human_page
        self.native_db=native_runtime/"projection-p0b-consumer.sqlite"
        self.stage=suite.stage
        self.home=suite.home
        self.priv=self.home/"consumer-private"
        self.ipc=self.home/"consumer-ipc"
        self.readydir=self.home/"consumer-ready"
        self.sock=self.ipc/"signed.sock"
        self.cfg=self.priv/"consumer-config.json"
        self.status=self.priv/"state.json"
        self.source_cfg=suite.authority_dir/"p0b-outbox-source.json"
        self.pubkey=self.stage/"p0b-public-ed25519.hex"
        self.source_token=secrets.token_urlsafe(42)
        self.port=None
        self.source_meta=None
        self.source_proc=None
        self.native_proc=None
        self.consumer_proc=None
        self.steps=[]
        self.started=False

    def _call(self,owner,argv,**kw):
        return self.s._user_call(owner,argv,**kw)

    def _inspect(self):
        result=self._call(RUNT,[
            self.stage/"g1-b01-b9"/"p0b_consumer_native_ipc.py",
            "--db",self.native_db,"--inspect"])
        return self.s.single(result.stdout,"P0B_NATIVE_DURABLE_ORACLE")

    def _status(self):
        script=("import json,sys,pathlib\n"
                "p=pathlib.Path(sys.argv[1]);"
                "print(json.dumps(json.loads(p.read_text())) if p.exists() else '{}')")
        data=self._call(CONS,["-c",script,self.status])
        return json.loads(data.stdout.strip())

    def _wait_status(self,predicate,seconds=13):
        until=time.monotonic()+seconds
        last={}
        while time.monotonic()<until:
            last=self._status()
            if predicate(last):
                return last
            time.sleep(.10)
        raise AssertionError("P0B_DURABLE_STATE_TIMEOUT|"+str(last))

    def _wait_native(self,count,seconds=13):
        until=time.monotonic()+seconds
        last=None
        while time.monotonic()<until:
            last=self._inspect()
            if (last.get("clean") and last.get("cursor")==count and
                last.get("receiptCount")==count and
                last.get("mappingCount")==count and
                len(last.get("rows",[]))==count):
                return last
            time.sleep(.10)
        raise AssertionError("P0B_DURABLE_CURSOR_TIMEOUT|"+str(last))

    def _source_request(self,token):
        req=Request("http://127.0.0.1:"+str(self.port)+ROUTE,
                    data=b'{"after":0,"limit":20}',method="POST",
                    headers={"Authorization":"Bearer "+token,
                             "Content-Type":"application/json"})
        try:
            with urlopen(req,timeout=3) as resp:
                return resp.status,json.loads(resp.read())
        except HTTPError as exc:
            return exc.code,json.loads(exc.read())

    def _start_source(self,round_number):
        ready=self.home/"ready"/("p0b-signed-source-"+str(round_number)+".json")
        log=self.home/("p0b-signed-source-"+str(round_number)+".log")
        self.source_proc=subprocess.Popen([
            "sudo","-n","runuser","-u",KERN,"--",sys.executable,"-u",
            str(self.stage/"g1-b01-b9"/"p0b_signed_outbox_server.py"),
            "--config",str(self.source_cfg),"--ready",str(ready)
        ],cwd=str(self.stage),stdin=subprocess.DEVNULL,
          stdout=log.open("w"),stderr=subprocess.STDOUT)
        for _ in range(100):
            if ready.is_file():break
            if self.source_proc.poll() is not None:
                raise AssertionError("SIGNED_SOURCE_LAUNCH_FAILED "+log.read_text()[-500:])
            time.sleep(.08)
        if not ready.is_file():
            raise AssertionError("SIGNED_SOURCE_START_TIMEOUT "+log.read_text()[-500:])
        self.source_meta=json.loads(ready.read_text())
        if self.source_meta["uid"]!=pwd.getpwnam(KERN).pw_uid:
            raise AssertionError("SIGNED_SOURCE_NOT_REAL_KERNEL_UID")
        status,body=self._source_request(self.source_token)
        if status!=200 or body["head"]!=2:
            # The second successful restart occurs after B2's third form write.
            if not(round_number==2 and status==200 and body["head"]==3):
                raise AssertionError("SIGNED_SOURCE_HEAD_OR_AUTH_INVALID")
        return self.source_meta

    def _stop_source(self):
        if self.source_meta:
            self.s.execute(["sudo","-n","kill","-TERM",
                            str(self.source_meta["pid"])],strict=False)
            self.source_meta=None
        if self.source_proc:
            try:self.source_proc.wait(timeout=4)
            except subprocess.TimeoutExpired:pass
            self.source_proc=None

    def _start_consumer(self):
        log=self.home/("p0b-consumer-"+str(len(self.steps))+".log")
        self.consumer_proc=subprocess.Popen([
            "sudo","-n","runuser","-u",CONS,"--",sys.executable,"-u",
            str(self.stage/"g1-b01-b9"/"p0b_durable_consumer.py"),
            "--config",str(self.cfg),"--status",str(self.status)
        ],cwd=str(self.stage),stdin=subprocess.DEVNULL,
          stdout=log.open("w"),stderr=subprocess.STDOUT)
        return self._wait_status(lambda x:x.get("state") in (
            "STARTING","APPLIED","CAUGHT_UP"),seconds=9)

    def _stop_consumer(self):
        try:
            state=self._status()
            if type(state.get("pid")) is int and state["pid"]>0:
                self.s.execute(["sudo","-n","kill","-TERM",
                                str(state["pid"])],strict=False)
            if self.consumer_proc:
                try:self.consumer_proc.wait(timeout=4)
                except subprocess.TimeoutExpired:pass
        finally:
            self.consumer_proc=None

    def _setup(self):
        first=self.s.physical()["app-a"]
        if first["publishedVersion"]!=1 or len(first["records"])!=2:
            raise AssertionError("P0B_CONSUMER_NOT_THE_PRIOR_SAME_B2_INSTANCE")
        # An *unseeded* real official Saltcorn Pack. All business data in
        # this derived DB must be populated by the actual signed consumer.
        pack=self.stage/"projection-v1-preview.json"
        reset=self.native_cmd(["saltcorn","reset-schema","-f"],self.native_db)
        installed=self.native_cmd(["saltcorn","install-pack","-f",pack],
                                  self.native_db)
        initial=self.native_cmd([
            sys.executable,self.stage/"g1-b01-b9"/"p0b_consumer_native_ipc.py",
            "--db",self.native_db,"--init"],self.native_db)
        if not(reset.returncode==installed.returncode==initial.returncode==0):
            raise AssertionError("P0B_NATIVE_FRESH_REAL_CLI_FAILED")
        empty=self._inspect()
        if empty["rows"]!=[] or empty["cursor"]!=0:
            raise AssertionError("P0B_CONSUMER_NATIVE_WAS_SEEDED")

        for dir in (self.priv,self.ipc,self.readydir):
            dir.mkdir(mode=0o700)
        self.s.execute(["sudo","-n","chown","-R",
                        RUNT+":"+IPC_GROUP,self.ipc])
        self.s.execute(["sudo","-n","chmod","2750",self.ipc])
        self.s.execute(["sudo","-n","chown","-R",
                        RUNT+":"+RUNT,self.readydir])
        self.s.execute(["sudo","-n","chmod","0755",self.readydir])

        self.pubkey.write_text(self.s.public_key+"\n",encoding="utf-8")
        self.pubkey.chmod(0o444)
        self.s.execute(["sudo","-n","chown","-R",
                        CONS+":"+CONS,self.priv])
        # Create under a runner-owned 0600 file and install into Kernel's
        # 0700 private directory with a single trusted root operation.
        with socket.socket() as port:
            port.bind(("127.0.0.1",0))
            self.port=port.getsockname()[1]
        seed=self.home/"p0b-signed-source-seed.json"
        seed.write_text(json.dumps({
            "db":str(self.s.authority_db),"key":str(self.s.key),
            "token":self.source_token,"port":self.port}))
        seed.chmod(0o600)
        self.s.execute(["sudo","-n","install","-o",KERN,"-g",KERN,
                        "-m","0600",seed,self.source_cfg])
        seed.unlink()
        self.cfg_temp=self.home/"p0b-consumer-config-seed.json"
        self.cfg_temp.write_text(json.dumps({
            "sourceUrl":"http://127.0.0.1:"+str(self.port)+ROUTE,
            "token":self.source_token,
            "nativeSocket":str(self.sock),"intervalMs":90
        }))
        self.cfg_temp.chmod(0o600)
        self.s.execute(["sudo","-n","install","-o",CONS,"-g",CONS,
                        "-m","0600",self.cfg_temp,self.cfg])
        self.cfg_temp.unlink()
        self._start_source(1)
        status,body=self._source_request("WRONG_TOKEN")
        if status!=401:
            raise AssertionError("P0B_UNSIGNED_PUBLIC_SOURCE_EXPOSED")
        self.source_auth_denied=(status==401)

        log=self.home/"p0b-native-broker.log"
        ready=self.readydir/"signed-native.json"
        self.native_proc=subprocess.Popen([
            "sudo","-n","runuser","-u",RUNT,"--",sys.executable,"-u",
            str(self.stage/"g1-b01-b9"/"p0b_consumer_native_ipc.py"),
            "--db",str(self.native_db),"--socket",str(self.sock),
            "--ready",str(ready),"--public-key-file",str(self.pubkey),
            "--consumer-uid",str(pwd.getpwnam(CONS).pw_uid)
        ],cwd=str(self.stage),stdin=subprocess.DEVNULL,
          stdout=log.open("w"),stderr=subprocess.STDOUT)
        for _ in range(100):
            if ready.is_file():break
            if self.native_proc.poll() is not None:
                raise AssertionError("P0B_SIGNED_IPC_PROCESS_EXITED "+
                                     log.read_text()[-600:])
            time.sleep(.08)
        if not ready.is_file():
            raise AssertionError("P0B_NATIVE_BROKER_READY_TIMEOUT "+
                                 log.read_text()[-600:])
        self.broker_meta=json.loads(ready.read_text())
        if self.broker_meta["uid"]!=pwd.getpwnam(RUNT).pw_uid:
            raise AssertionError("P0B_SIGNED_BROKER_NOT_NATIVE_UID")
        self.started=True
        return empty

    def run(self):
        try:
            return self._run_inner()
        finally:
            self.stop()

    def _run_inner(self):
        s=self.s
        empty=self._setup()
        cons_uid=pwd.getpwnam(CONS).pw_uid
        ids={x:pwd.getpwnam(x).pw_uid for x in (
            KERN,RUNT,PLUG,PUBL,READ,CONS)}
        s.check("P0B-16-real-B11-fresh-Native-signed-IPC-and-Kernel-source",
                empty["cursor"]==0 and empty["rows"]==[] and
                self.source_auth_denied and len(set(ids.values()))==6 and
                self.broker_meta["consumerUid"]==cons_uid and
                self.broker_meta["signatures"]=="B14-Ed25519" and
                s._business_head()["head"]==2 and
                s.physical()["app-a"]["publishedVersion"]==1,
                {"sixSeparateUIDs":ids,"nativeNewSQLiteUnseeded":True,
                 "b14SourceBearerAuthRequired":True,
                 "nativeSignedPeerUidGate":True,
                 "realOfficialSaltcornPack":True})

        self._start_consumer()
        state2=self._wait_native(2)
        status2=self._wait_status(lambda x:x.get("cursor")==2 and
                                 x.get("state") in ("CAUGHT_UP","APPLIED"))
        old_snapshot=s._sha()
        s.check("P0B-17-separate-UID-autoconsumes-2-B14-events-native-durable",
                state2["clean"] and state2["cursor"]==2 and
                state2["receiptCount"]==state2["mappingCount"]==2 and
                s.native_physical(self.native_db)["businessRows"]==
                    sorted([r["value"] for r in
                            s.physical()["app-a"]["records"]],
                           key=lambda r:r["contract_no"]) and
                status2["cursor"]==2 and
                old_snapshot is not None,
                {"nativeDurableCursor":2,"receipts":2,"mappings":2,
                 "signedEventsApplied":2,"manualSaltcornRowSeed":False,
                 "publisherNotYetPromotedNewNative":True})

        before_replay=self._inspect()
        replay=self._call(CONS,[
            self.stage/"g1-b01-b9"/"p0b_durable_consumer.py",
            "--config",self.cfg,"--replay"])
        receipt=s.single(replay.stdout,"P0B_REPLAY")
        after_replay=self._inspect()
        s.check("P0B-18-verified-replay-is-idempotent-with-same-durable-receipts",
                receipt=={"before":2,"after":2,"applied":0,"replayed":2} and
                after_replay==before_replay,
                {"sameTransactionCursor":2,"actualReplayCount":2,
                 "duplicateRows":0,"receiptIDsStill":2})

        pid1=self._status()["pid"]
        self._stop_consumer()
        paused=self._inspect()
        self._start_consumer()
        state2_again=self._wait_native(2)
        running=self._wait_status(lambda x:x.get("cursor")==2 and
                                 x.get("state") in ("CAUGHT_UP","APPLIED"))
        pid2=running["pid"]
        s.check("P0B-19-consumer-process-restart-resumes-native-checkpoint",
                pid1!=pid2 and
                state2_again==paused and
                running["cursor"]==2 and
                self.native_proc.poll() is None and
                self._source_request(self.source_token)[0]==200,
                {"oldConsumerPid":pid1,"newConsumerPid":pid2,
                 "nativeCursorPersisted":2,"noDuplicateReceipts":True})

        # Only the Kernel signing source dies; 6th-UID consumer/native
        # broker and B2 Kernel continue running without restart.
        before=s._sha()
        self._stop_source()
        lost=self._wait_status(lambda x:x.get("state")=="SOURCE_UNAVAILABLE")
        pre_write_native=self._inspect()
        post=self.human_page.evaluate("""async () => {
          const r=await fetch("/v2/apps/app-a/runtime/forms/form.contracts/records",{
            method:"POST",credentials:"same-origin",
            headers:{"Content-Type":"application/json","X-CSRF-Token":csrf},
            body:JSON.stringify({contract_no:"HT-2026-000003",
              title:"S1 Durable Source Recovery Contract",
              amount_minor:300000003})
          });
          return {status:r.status,body:await r.json()};
        }""")
        b2=s._business_head()
        blocked=s._request()[0]
        s.page.reload(wait_until="domcontentloaded")
        lagging=self._inspect()
        s.check("P0B-20-source-outage-no-advance-B2-write-fails-closed",
                lost["state"]=="SOURCE_UNAVAILABLE" and
                post["status"]==200 and b2["head"]==3 and
                s.physical()["app-a"]["publishedVersion"]==1 and
                lagging["cursor"]==pre_write_native["cursor"]==2 and
                lagging["receiptCount"]==2 and blocked==503 and
                s.page.locator("th").count()==0 and
                s._sha()==before and
                self.native_proc.poll() is None,
                {"actualSourceKilled":True,"consumerFailures":lost["failures"],
                 "newB2BusinessHead":3,"persistentNativeCursor":2,
                 "staleB17HTTP":503,"verifiedSnapshotUntouched":True})

        # Reuse the EXACT pinned key, source token and fixed local port;
        # existing consumer/native broker MUST catch up themselves.
        self._start_source(2)
        live3=self._wait_native(3,seconds=17)
        consumer3=self._wait_status(lambda x:x.get("cursor")==3 and
                                   x.get("state") in ("APPLIED","CAUGHT_UP"))
        s.check("P0B-21-source-restored-automatic-signed-B11-resume-to-three",
                live3["clean"] and live3["cursor"]==3 and
                live3["receiptCount"]==live3["mappingCount"]==3 and
                consumer3["cursor"]==3 and
                self._request_no_side_effect(s)==503 and
                s._sha()==before and
                s.physical()["app-a"]["publishedVersion"]==1,
                {"nativeCursor":3,"durableReceipts":3,
                 "sourceReconnectWithoutConsumerRestart":True,
                 "stillFailClosedBeforeB15":True})

        current=s._sign()
        native3=s.native_physical(self.native_db)
        code,published=s._publish(
            "automated-consumer-recovered-three",
            s._candidate(current,native3))
        s.page.reload(wait_until="domcontentloaded")
        page_status,headers,body=s._request()
        authority=s.physical()
        s.check("P0B-22-B15-verified-auto-Consumer-SQL-to-same-B17-browser",
                code==0 and published["version"]==1 and
                published["rows"]==3 and
                s._sha()!=before and page_status==200 and
                headers.get("X-OpenAILCAP-Release")=="1" and
                s.page.locator("tbody tr").count()==3 and
                all(name in body.decode("utf-8") for name in (
                    "HT-2026-000001","HT-2026-000002",
                    "HT-2026-000003")) and
                len(authority["app-a"]["records"])==3 and
                authority["app-b"]==s.app_b and
                s.router.poll() is None,
                {"liveB2Records":3,"b14EventCount":3,"nativeCursor":3,
                 "B17BrowserRows":3,"sameRouter":True,
                 "noManualNativeBusinessSeed":True})

        # Explicit Linux DAC + actual low-privilege IPC attack probes.
        test=("import os,sys\n"
              "try:\n fd=os.open(sys.argv[1],os.O_RDONLY);os.close(fd);print('OPENED')\n"
              "except OSError:print('DENIED')")
        cons_db=self._call(CONS,["-c",test,self.native_db],
                           strict=False).stdout.strip()
        cons_kernel=self._call(CONS,["-c",test,s.authority_db],
                               strict=False).stdout.strip()
        socket_probe=("import socket,sys\n"
                      "s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)\n"
                      "try:\n s.connect(sys.argv[1]);print('CONNECTED')\n"
                      "except PermissionError:print('DENIED')\n"
                      "except OSError as exc:print('UNEXPECTED_'+str(exc.errno))\n"
                      "finally:s.close()")
        plug_sock=self._call(PLUG,["-c",socket_probe,self.sock],
                             strict=False).stdout.strip()
        read_sock=self._call(READ,["-c",socket_probe,self.sock],
                             strict=False).stdout.strip()
        source_bad=self._source_request("UNAUTHORIZED")[0]
        s.check("P0B-23-consumer-DAC-and-unsigned-Plugin-IPC-bypass-denied",
                cons_db==cons_kernel==plug_sock==read_sock=="DENIED" and
                source_bad==401 and
                self._inspect()["clean"] and
                self._inspect()["cursor"]==3 and
                s._request()[0]==200 and
                self.consumer_proc.poll() is None,
                {"consumerReadsNativeDB":cons_db,
                 "consumerReadsKernelDB":cons_kernel,
                 "pluginAFUnixSocketConnect":plug_sock,
                 "readonlyAFUnixSocketConnect":read_sock,
                 "anonymousB14SourceStatus":401,
                 "durableHead":3,"nativeSignedBrokerUid":
                     self.broker_meta["uid"]})
        return {"checks":8,"autoNativeApplies":3,"nativeDurableReceipts":3,
                "sourceOutageRecovered":True,"consumerRestartRecovered":True,
                "signedB14EventsEnforcedNativeIPC":True,
                "noManualRowSeed":True,"modelCalls":0,"g1Passed":False,
                "productionFullG1":False}

    def _request_no_side_effect(self,s):
        return s._request()[0]

    def stop(self):
        if self.consumer_proc is not None:
            try:self._stop_consumer()
            except Exception:pass
        if self.source_meta:
            try:self._stop_source()
            except Exception:pass
        if self.native_proc is not None:
            try:
                ready=self.broker_meta if hasattr(self,"broker_meta") else None
                if ready and type(ready.get("pid")) is int:
                    self.s.execute(["sudo","-n","kill","-TERM",
                                    str(ready["pid"])],strict=False)
                self.native_proc.wait(timeout=4)
            except Exception:pass
            self.native_proc=None
