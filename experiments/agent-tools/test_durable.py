"""S1 research: persistent call claims and crash/duplicate unknown outcomes.

These tests use a fake adapter for deterministic fault injection. The
separate integration tests exercise actual Saltcorn HTTP and physical SQL.
"""
from __future__ import annotations
import sqlite3
import tempfile
import unittest
from pathlib import Path

from broker import Broker, ToolError, TrustedSession


class ControlledAdapter:
    def __init__(self):
        self.writes=0
        self.sessions={}
        self.status="Draft"
        self.fail_after_write=False

    def bind(self, key, ctx, csrf):
        self.sessions[key]=(ctx,csrf)

    def contract(self, key, number):
        return {"id":5,"number":number,
                "status":self.status,"amount_minor":100000001}

    def action(self, key, uid, role, number, action, native_id):
        self.writes+=1
        self.status="Submitted"
        if self.fail_after_write:
            # Models network disconnect AFTER native mutation: no guarantee
            # of a response or safe automatic retry.
            raise ToolError("UNKNOWN_REMOTE_OUTCOME")
        return {"success": 1}


class DurableCalls(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=str(Path(self.temp.name)/"claims.sqlite")
        self.adapter=ControlledAdapter()
        self.subject=TrustedSession("real-creator","s1-contract",
             "s1-creator@example.invalid",8,"creator",
             frozenset({"contract.read","contract.action"}))
        self.broker=self.new_broker()

    def tearDown(self):
        self.temp.cleanup()

    def new_broker(self):
        b=Broker(self.path,self.adapter)
        b.bind_session(self.subject,None,"valid-native-csrf")
        return b

    def action_args(self):
        return {"number":"S1-AGENT-HIGH-1","action":"submit","base_status":"Draft"}

    def grant(self,b):
        return b.issue_human_grant("real-creator","S1-AGENT-HIGH-1",
                                   "submit",trusted_user_confirmed=True)

    def deny(self,code,fn):
        with self.assertRaises(ToolError) as captured:
            fn()
        self.assertEqual(captured.exception.code,code)

    def claim_state(self,call_id):
        with sqlite3.connect(self.path) as db:
            return db.execute("SELECT state FROM agent_tool_call_claims WHERE call_id=?",
                              (call_id,)).fetchone()[0]

    def test_completed_read_unique_across_broker_restart(self):
        call_id="durable-read-0001"
        first=self.broker.execute("real-creator","contract.read",
            {"number":"S1-AGENT-HIGH-1"},call_id=call_id)
        other=self.new_broker()
        self.deny("DUPLICATE_CALL_ID",lambda:other.execute(
            "real-creator","contract.read",{"number":"S1-AGENT-HIGH-1"},call_id=call_id))
        self.assertEqual(first["status"],"Draft")
        self.assertEqual(self.claim_state(call_id),"READ_OK")

    def test_completed_mutation_unique_across_restart(self):
        grant=self.grant(self.broker)
        cid="durable-write-0001"
        result=self.broker.execute("real-creator","contract.action",
               self.action_args(),call_id=cid,human_grant=grant)
        self.assertEqual(result["status"],"NATIVE_ACCEPTED_RECHECK_REQUIRED")
        new=self.new_broker()
        self.deny("DUPLICATE_CALL_ID",lambda:new.execute(
            "real-creator","contract.action",self.action_args(),call_id=cid))
        self.assertEqual(self.adapter.writes,1)
        self.assertEqual(self.claim_state(cid),"MUTATION_ACCEPTED")

    def test_claimed_before_io_crash_stays_unknown_and_blocks_duplicate(self):
        cid="durable-crash-0001"
        self.broker._reserve(cid,"contract.action",self.subject)
        self.assertEqual(self.claim_state(cid),"CLAIMED")
        restarted=self.new_broker()
        self.deny("DUPLICATE_CALL_ID",lambda:restarted.execute(
            "real-creator","contract.read",{"number":"S1-AGENT-HIGH-1"},call_id=cid))
        self.assertEqual(self.adapter.writes,0)
        self.assertEqual(restarted.lookup_call(cid)["state"],"CLAIMED")

    def test_unknown_remote_after_native_write_not_retried(self):
        self.adapter.fail_after_write=True
        grant=self.grant(self.broker)
        cid="durable-unknown-0001"
        self.deny("UNKNOWN_REMOTE_OUTCOME",lambda:self.broker.execute(
            "real-creator","contract.action",self.action_args(),call_id=cid,
            human_grant=grant))
        self.assertEqual(self.adapter.writes,1)
        self.assertEqual(self.adapter.status,"Submitted")
        self.assertEqual(self.claim_state(cid),"UNKNOWN_REMOTE_OUTCOME")
        again=self.new_broker()
        self.deny("DUPLICATE_CALL_ID",lambda:again.execute(
            "real-creator","contract.action",self.action_args(),call_id=cid))
        self.assertEqual(self.adapter.writes,1)

    def test_ledger_unavailable_prevents_any_mutation(self):
        grant=self.grant(self.broker)
        def fail_reserve(*args):
            raise ToolError("DURABLE_LEDGER_UNAVAILABLE")
        self.broker._reserve=fail_reserve
        self.deny("DURABLE_LEDGER_UNAVAILABLE",lambda:self.broker.execute(
            "real-creator","contract.action",self.action_args(),
            call_id="durable-db-offline-1",human_grant=grant))
        self.assertEqual(self.adapter.writes,0)

    def test_duplicate_rejected_across_principals_or_tools(self):
        cid="durable-same-id-01"
        self.broker.execute("real-creator","contract.read",
                 {"number":"S1-AGENT-HIGH-1"},call_id=cid)
        restarted=self.new_broker()
        self.deny("DUPLICATE_CALL_ID",lambda:restarted.execute(
            "real-creator","contract.action",self.action_args(),call_id=cid))
        self.assertEqual(self.adapter.writes,0)

    def test_grants_are_not_persisted_and_die_on_restart(self):
        g=self.grant(self.broker)
        restarted=self.new_broker()
        self.deny("GRANT_REJECTED",lambda:restarted.execute(
            "real-creator","contract.action",self.action_args(),
            call_id="durable-new-call-01",human_grant=g))
        self.assertEqual(self.adapter.writes,0)
        self.assertEqual(self.claim_state("durable-new-call-01"),"GRANT_REJECTED")

    def test_durable_audit_records_hash_only(self):
        cid="durable-audit-0001"
        self.broker.execute("real-creator","contract.read",
            {"number":"S1-AGENT-HIGH-1"},call_id=cid)
        with sqlite3.connect(self.path) as db:
            event=db.execute(
                "SELECT result,args_sha256 FROM agent_tool_audit WHERE call_id=?",
                (cid,)).fetchone()
            claim=db.execute(
                "SELECT state,tool,principal FROM agent_tool_call_claims WHERE call_id=?",
                (cid,)).fetchone()
        self.assertEqual(event[0],"READ_OK")
        self.assertEqual(len(event[1]),64)
        self.assertEqual(claim,("READ_OK","contract.read","s1-creator@example.invalid"))


if __name__=="__main__":
    unittest.main()
