"""Independent stdlib adversarial tests; NOT a model-inference experiment."""
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from broker import Broker, SaltcornRest, TrustedSession, ToolError

class FakeAdapter:
    def __init__(self):
        self.sessions={}
        self.contracts={
            "S1-AGENT-HIGH-1":{"id":1,"number":"S1-AGENT-HIGH-1",
                                "status":"Draft","amount_minor":100000001},
            "S1-AGENT-NORMAL-1":{"id":2,"number":"S1-AGENT-NORMAL-1",
                                  "status":"Draft","amount_minor":100000000}}
        self.post_count=0
    def bind(self,key,ctx,csrf): self.sessions[key]=(ctx,csrf)
    def contract(self,key,number):
        if number not in self.contracts:raise ToolError("NOT_FOUND_OR_NONUNIQUE")
        return dict(self.contracts[number])
    def action(self,key,user_id,role,number,action,contract_id):
        self.post_count+=1
        c=self.contracts[number]
        if action=="submit" and role=="creator" and c["status"]=="Draft":
            c["status"]="Submitted"
        elif action=="approve" and role=="approver1" and c["status"]=="Submitted":
            c["status"]="Level1Approved" if c["amount_minor"]>100000000 else "Approved"
        elif action=="approve" and role=="approver2" and c["status"]=="Level1Approved":
            c["status"]="Approved"
        else:raise ToolError("NATIVE_REJECTED")
        return {"success":self.post_count}

class BrokerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.now=[100.]
        self.adapter=FakeAdapter()
        self.b=Broker(str(Path(self.tmp.name)/"audit.sqlite"),self.adapter,
                      now=lambda:self.now[0],max_calls=40)
        self.creator=TrustedSession("C","s1-contract","s1-creator@example.invalid",8,
                                    "creator",frozenset({"contract.read","contract.action"}))
        self.approver=TrustedSession("A","s1-contract","s1-approver1@example.invalid",9,
                                     "approver1",frozenset({"contract.read","contract.action"}))
        self.viewer=TrustedSession("V","s1-contract","s1-viewer@example.invalid",10,
                                   "viewer",frozenset({"contract.read"}))
        for s in (self.creator,self.approver,self.viewer):
            self.b.bind_session(s,None,"csrf-secret-value")
        self.seq=0
    def tearDown(self):self.tmp.cleanup()
    def call(self,actor,tool,args,grant=None):
        self.seq+=1
        return self.b.execute(actor,tool,args,call_id="unit-call-"+str(self.seq).zfill(5),
                              human_grant=grant)
    def rejects(self,code,fn):
        with self.assertRaises(ToolError) as e:fn()
        self.assertEqual(code,e.exception.code)
    def args(self,status="Draft",number="S1-AGENT-HIGH-1",action="submit"):
        return {"number":number,"base_status":status,"action":action}

    def test_read_is_native_backed(self):
        self.assertEqual("Draft",self.call("V","contract.read",{"number":"S1-AGENT-HIGH-1"})["status"])
    def test_viewer_catalog_least_privilege(self):
        self.assertEqual(["contract.read"],[x["name"] for x in self.b.catalog("V")])
    def test_unknown_tool_rejected(self):
        self.rejects("UNKNOWN_TOOL",lambda:self.call("V","system.shell",{"cmd":"id"}))
    def test_no_actor_role_or_extra_keys(self):
        self.rejects("INVALID_ARGUMENTS",lambda:self.call("C","contract.read",
           {"number":"S1-AGENT-HIGH-1","actor_id":"admin"}))
    def test_action_no_grant_rejected(self):
        self.rejects("HUMAN_APPROVAL_REQUIRED",lambda:self.call("C","contract.action",self.args()))
        self.assertEqual(0,self.adapter.post_count)
    def test_viewer_write_scope_rejected(self):
        self.rejects("SCOPE_DENIED",lambda:self.call("V","contract.action",self.args()))
    def test_no_unauthorized_grant_issuance(self):
        self.rejects("HUMAN_APPROVAL_REQUIRED",lambda:
             self.b.issue_human_grant("C","S1-AGENT-HIGH-1","submit",trusted_user_confirmed=False))
    def test_wrong_role_grant_issuance_denied(self):
        self.rejects("ROLE_NOT_DELEGATABLE",lambda:
             self.b.issue_human_grant("A","S1-AGENT-HIGH-1","submit",trusted_user_confirmed=True))
    def test_one_grant_one_success_only(self):
        g=self.b.issue_human_grant("C","S1-AGENT-HIGH-1","submit",trusted_user_confirmed=True)
        self.call("C","contract.action",self.args(),g)
        self.assertEqual("Submitted",self.adapter.contracts["S1-AGENT-HIGH-1"]["status"])
        self.rejects("GRANT_REJECTED",lambda:self.call("C","contract.action",
                     self.args(status="Submitted"),g))
        self.assertEqual(1,self.adapter.post_count)
    def test_expired_grant(self):
        g=self.b.issue_human_grant("C","S1-AGENT-HIGH-1","submit",
                                   trusted_user_confirmed=True,ttl=1)
        self.now[0]=101.
        self.rejects("GRANT_REJECTED",lambda:self.call("C","contract.action",self.args(),g))
    def test_cross_resource_rejected(self):
        g=self.b.issue_human_grant("C","S1-AGENT-HIGH-1","submit",trusted_user_confirmed=True)
        self.rejects("GRANT_REJECTED",lambda:self.call("C","contract.action",
                    self.args(number="S1-AGENT-NORMAL-1"),g))
    def test_cross_user_rejected(self):
        g=self.b.issue_human_grant("C","S1-AGENT-HIGH-1","submit",trusted_user_confirmed=True)
        self.rejects("GRANT_REJECTED",lambda:self.call("A","contract.action",self.args(),g))
    def test_stale_base_fails_before_network(self):
        g=self.b.issue_human_grant("C","S1-AGENT-HIGH-1","submit",trusted_user_confirmed=True)
        self.rejects("STALE_RESOURCE",lambda:self.call("C","contract.action",
                    self.args(status="Submitted"),g))
        self.assertEqual(0,self.adapter.post_count)
    def test_plugin_manifest_not_code_loader(self):
        self.rejects("UNTRUSTED_PLUGIN_HANDLER",lambda:self.b.register_manifest({
             "name":"route-inspector","version":"1.0.0",
             "tool":{"name":"contract.route","handler":"os.system"}}))
        self.b.register_manifest({"name":"route-inspector","version":"1.0.0",
              "tool":{"name":"contract.route","handler":"route_inspector_v1"}})
        self.assertEqual("HIGH",self.call("V","contract.route",
                             {"number":"S1-AGENT-HIGH-1"})["derived_route"])
        self.assertEqual("NORMAL",self.call("V","contract.route",
                             {"number":"S1-AGENT-NORMAL-1"})["derived_route"])
    def test_duplicate_call_id_denied(self):
        arg={"number":"S1-AGENT-HIGH-1"}
        self.b.execute("V","contract.read",arg,call_id="duplicate-call-1")
        self.rejects("DUPLICATE_CALL_ID",lambda:self.b.execute(
            "V","contract.read",arg,call_id="duplicate-call-1"))
    def test_budget_caps_all_tool_calls(self):
        self.b.max_calls=1
        self.call("V","contract.read",{"number":"S1-AGENT-HIGH-1"})
        self.rejects("TOOL_BUDGET_EXHAUSTED",lambda:self.call(
            "V","contract.read",{"number":"S1-AGENT-HIGH-1"}))
    def test_audit_redacted_and_persisted(self):
        self.rejects("UNKNOWN_TOOL",lambda:self.call("V","private.secrets",{"path":"/keys"}))
        self.call("V","contract.read",{"number":"S1-AGENT-HIGH-1"})
        with sqlite3.connect(self.b.path) as db:
            rows=list(db.execute("SELECT result,args_sha256 FROM agent_tool_audit"))
        self.assertEqual(2,len(rows))
        self.assertTrue(all(len(x[1])==64 for x in rows))
    def test_forged_other_app_session_rejected(self):
        other=TrustedSession("bad","other-app","s1-creator@example.invalid",8,
                             "creator",frozenset({"contract.action"}))
        self.rejects("SCOPE_DENIED",lambda:self.b.bind_session(other,None,"csrf-secret-value"))
    def test_local_native_adapter_cannot_point_external(self):
        self.rejects("LAB_LOCALHOST_ONLY",lambda:SaltcornRest("http://external.invalid"))
    def test_missing_session_csrf_rejected(self):
        adapter=SaltcornRest("http://127.0.0.1:3100")
        self.rejects("SESSION_CSRF_MISSING",lambda:adapter.bind("key",None,""))
    def test_wrong_schema_enum_rejected(self):
        self.rejects("INVALID_ARGUMENTS",lambda:self.call("C","contract.action",
                    self.args(action="exec_shell")))

if __name__=="__main__":unittest.main()
