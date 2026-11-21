"""S1 B5 broker contract tests. Pure permission checks; no fake build PASS."""
import json,sys,secrets,tempfile,time,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"g1-b01-b2"))
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"g1-b01-b4"))
from schema_core import Actor,SchemaStore,Rejected
from tool_broker import ToolBroker

class NeverRunSandbox:
    image_id="sha256:"+"0"*64
    def test(self,source):
        raise AssertionError("untrusted caller must not reach executor")

class BrokerUnit(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.db=SchemaStore(Path(self.temp.name)/"b5.sqlite")
        self.db.init()
        self.db.seed_app_for_test("app-a")
        self.db.seed_app_for_test("app-b")
        self.registry=type("Registry",(),{"sandbox":NeverRunSandbox()})()
        self.g=ToolBroker(self.db,self.registry)
        self.human=Actor("human-a","app-a",can_publish=True,can_runtime=True)
        self.agent=Actor("agent-a","app-a",can_publish=False)
        self.plugin=Actor("plugin-a","app-a",kinds=("view",))
        self.readonly=Actor("read-a","app-a",kinds=(),can_runtime=True)
        self.ht=secrets.token_urlsafe(25)
        self.at=secrets.token_urlsafe(25)
        self.pt=secrets.token_urlsafe(25)
        self.rt=secrets.token_urlsafe(25)
        self.g.grant(self.ht,self.human,{"app.publish","app.rollback",
                                          "code.stage","code.publish","code.rollback",
                                          "release.read","metadata.upsert"})
        self.g.grant(self.at,self.agent,{"metadata.upsert","code.verify"})
        self.g.grant(self.pt,self.plugin,{"metadata.upsert"})
        self.g.grant(self.rt,self.readonly,{"release.read"})
    def tearDown(self):self.temp.cleanup()
    def reject(self,status,code,token,app,tool,args):
        with self.assertRaises(Rejected) as c:
            self.g.call(token,app,tool,args)
        self.assertEqual((c.exception.status,c.exception.code),(status,code))
    def test_random_tokens_have_separate_grants(self):
        self.assertNotEqual(self.ht,self.pt)
        self.assertNotEqual(self.pt,self.at)
    def test_agent_cannot_publish_app(self):
        self.reject(403,"TOOL_NOT_GRANTED",self.at,"app-a","app.publish",{})
    def test_agent_cannot_publish_code(self):
        self.reject(403,"TOOL_NOT_GRANTED",self.at,"app-a","code.publish",{})
    def test_agent_cannot_stage_code(self):
        self.reject(403,"TOOL_NOT_GRANTED",self.at,"app-a","code.stage",{})
    def test_plugin_cannot_verify_code(self):
        self.reject(403,"TOOL_NOT_GRANTED",self.pt,"app-a","code.verify",{})
    def test_plugin_cannot_stage_code(self):
        self.reject(403,"TOOL_NOT_GRANTED",self.pt,"app-a","code.stage",{})
    def test_plugin_cannot_grant_self_new_tools(self):
        self.reject(403,"TOOL_NOT_GRANTED",self.pt,"app-a","tool.grant",{})
    def test_plugin_cross_app_denied(self):
        self.reject(403,"CROSS_APP_FORBIDDEN",self.pt,"app-b","metadata.upsert",{})
    def test_unknown_token_denied(self):
        self.reject(401,"TOOL_GRANT_EXPIRED_OR_REVOKED","fake","app-a",
                    "metadata.upsert",{})
    def test_revoked_token_denied(self):
        self.g.revoke(self.pt)
        self.reject(401,"TOOL_GRANT_EXPIRED_OR_REVOKED",self.pt,"app-a",
                    "metadata.upsert",{})
    def test_expired_token_denied(self):
        self.g.grant(self.pt,self.plugin,{"metadata.upsert"},ttl_seconds=-1)
        self.reject(401,"TOOL_GRANT_EXPIRED_OR_REVOKED",self.pt,"app-a",
                    "metadata.upsert",{})
    def test_plugin_kind_fails_before_mutation(self):
        snap=self.db.draft(self.human,"app-a")
        cmd={"changeId":"b5-plugin-bad-model","resourceId":"model.contracts",
             "expectedAppRevision":0,"expectedRevision":None,
             "baseContentHash":None,
             "definition":{"kind":"model","table":"x",
                           "fields":[{"name":"a","type":"string","required":True}]}}
        self.reject(403,"KIND_FORBIDDEN",self.pt,"app-a",
                    "metadata.upsert",{"command":cmd})
        self.assertEqual(self.db.draft(self.human,"app-a"),snap)
    def test_argument_injection_rejected(self):
        self.reject(422,"TOOL_ARGUMENTS_INVALID",self.at,"app-a",
                    "metadata.upsert",{"command":{},"actorId":"admin"})
    def test_readonly_cannot_mutate(self):
        self.reject(403,"TOOL_NOT_GRANTED",self.rt,"app-a",
                    "metadata.upsert",{})
    def test_human_wrong_args_no_publish(self):
        self.reject(422,"TOOL_ARGUMENTS_INVALID",self.ht,"app-a",
                    "app.publish",{"manifestHash":"skip"})
    def test_agent_code_verify_reaches_only_trusted_sandbox(self):
        with self.assertRaises(AssertionError):
            self.g.call(self.at,"app-a","code.verify",{
                "source":"def score_contract(amount_minor, supplier_score, months_active):\n"
                         "    return 0\n"})
    def test_actor_inactive_rejected(self):
        x=Actor("retired","app-a",active=False)
        token=secrets.token_urlsafe(25)
        self.g.grant(token,x,{"metadata.upsert"})
        self.reject(401,"TOOL_GRANT_EXPIRED_OR_REVOKED",token,"app-a",
                    "metadata.upsert",{})
    def test_grant_unknown_tool_cannot_register(self):
        with self.assertRaises(ValueError):
            self.g.grant(secrets.token_urlsafe(25),self.agent,{"sql.admin"})
    def test_readonly_release_needs_actual_publication(self):
        self.reject(404,"NOT_PUBLISHED",self.rt,"app-a",
                    "release.read",{})

if __name__=="__main__":unittest.main()
