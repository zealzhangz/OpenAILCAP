"""B2 pure SQLite engine unit tests. Real Chromium is tested separately."""
import copy
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from schema_core import Actor, Rejected, SchemaStore, sha

SPECS=json.loads(Path(__file__).with_name("contract_spec.json").read_text())

class SchemaUnit(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/"app.sqlite"
        self.store=SchemaStore(self.path)
        self.store.init()
        self.store.seed_app_for_test("app-a")
        self.store.seed_app_for_test("app-b")
        self.human=Actor("human","app-a",can_publish=True,can_runtime=True)
        self.agent=Actor("agent","app-a")
        self.plugin=Actor("plugin","app-a",kinds=("view",))
        self.n=0

    def tearDown(self):
        self.tmp.cleanup()

    def command(self,actor,rid,spec,app="app-a",rev=None,cid=None):
        snap=self.store.draft(actor,app)
        old=snap["resources"].get(rid)
        self.n+=1
        return self.store.mutate(actor,app,{
            "changeId":cid or f"unit-{self.n:04}",
            "resourceId":rid,
            "expectedAppRevision":snap["appRevision"] if rev is None else rev,
            "expectedRevision":old["revision"] if old else None,
            "baseContentHash":old["contentHash"] if old else None,
            "definition":spec
        })

    def seed_all(self):
        for rid,spec in SPECS.items():
            self.command(self.agent,rid,spec)

    def assert_rejected(self,code,fn):
        with self.assertRaises(Rejected) as e:fn()
        self.assertEqual(e.exception.code,code)

    def test_create_and_hash_manifest(self):
        self.seed_all()
        state=self.store.draft(self.human,"app-a")
        self.assertEqual(state["appRevision"],4)
        self.assertEqual(state["manifestHash"],sha(SPECS))
        self.assertEqual(len(state["resources"]),4)

    def test_cross_resource_stale_rejected(self):
        self.command(self.human,"model.contracts",SPECS["model.contracts"])
        self.assert_rejected("APP_REVISION_CONFLICT",
            lambda:self.command(self.agent,"form.contracts",SPECS["form.contracts"],rev=0))
        self.assertEqual(self.store.physical("app-a")["revision"],1)

    def test_cross_app_isolation_and_permissions(self):
        self.assert_rejected("CROSS_APP_FORBIDDEN",
            lambda:self.store.draft(self.human,"app-b"))
        self.assert_rejected("KIND_FORBIDDEN",
            lambda:self.command(self.plugin,"model.contracts",SPECS["model.contracts"]))
        self.assertEqual(self.store.physical("app-a")["revision"],0)

    def test_missing_model_reference_rejected(self):
        self.assert_rejected("BROKEN_MODEL_REFERENCE",
            lambda:self.command(self.agent,"form.contracts",SPECS["form.contracts"]))

    def test_dangling_field_reference_rejected(self):
        self.command(self.agent,"model.contracts",SPECS["model.contracts"])
        bad=copy.deepcopy(SPECS["form.contracts"])
        bad["fields"].append("unknown")
        self.assert_rejected("BROKEN_FIELD_REFERENCE",
            lambda:self.command(self.agent,"form.contracts",bad))

    def test_delete_referenced_model_rejected(self):
        self.seed_all()
        self.assert_rejected("BROKEN_MODEL_REFERENCE",
            lambda:self.command(self.human,"model.contracts",None))
        self.assertEqual(self.store.draft(self.human,"app-a")["appRevision"],4)

    def test_publish_requires_complete_graph(self):
        self.command(self.agent,"model.contracts",SPECS["model.contracts"])
        snapshot=self.store.draft(self.human,"app-a")
        self.assert_rejected("RELEASE_INCOMPLETE",lambda:self.store.publish(
            self.human,"app-a",{"changeId":"pub-0001",
            "expectedAppRevision":snapshot["appRevision"],
            "manifestHash":snapshot["manifestHash"]}))

    def publish(self,actor=None,change_id=None,rev=None):
        actor=actor or self.human
        snapshot=self.store.draft(self.human,"app-a")
        return self.store.publish(actor,"app-a",{
            "changeId":change_id or f"publish-{self.n:04}",
            "expectedAppRevision":snapshot["appRevision"] if rev is None else rev,
            "manifestHash":snapshot["manifestHash"]})

    def test_model_readonly_agent_cannot_publish(self):
        self.seed_all()
        self.assert_rejected("PUBLISH_FORBIDDEN",lambda:self.publish(self.agent))

    def test_idempotent_replay_original_receipt_after_newer_edit(self):
        s=self.store.draft(self.human,"app-a")
        cmd={"changeId":"original-0001","resourceId":"model.contracts",
            "expectedAppRevision":0,"expectedRevision":None,
            "baseContentHash":None,"definition":SPECS["model.contracts"]}
        first=self.store.mutate(self.agent,"app-a",cmd)
        self.command(self.human,"form.contracts",SPECS["form.contracts"])
        second=self.store.mutate(self.agent,"app-a",cmd)
        self.assertTrue(second["replayed"])
        self.assertEqual(first["appRevision"],second["appRevision"])
        self.assertEqual(self.store.physical("app-a")["revision"],2)

    def test_transaction_injected_failure_no_receipt(self):
        s=self.store.draft(self.human,"app-a")
        cmd={"changeId":"fail-0001","resourceId":"model.contracts",
            "expectedAppRevision":0,"expectedRevision":None,
            "baseContentHash":None,"definition":SPECS["model.contracts"]}
        with self.assertRaisesRegex(RuntimeError,"RESEARCH_INJECTED_FAILURE"):
            self.store.mutate(self.agent,"app-a",cmd,fail_before_commit=True)
        self.assertEqual(self.store.physical("app-a")["revision"],0)
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM receipts").fetchone()[0],0)

    def test_runtime_form_view_workflow_threshold(self):
        self.seed_all()
        self.publish(change_id="publish-0001")
        row=self.store.submit_form(self.human,"app-a","form.contracts",{
            "contract_no":"CT-001","title":"Test","amount_minor":100000001
        })
        self.assertEqual(row["data"]["status"],"Draft")
        rid=row["recordId"]
        v=self.store.advance(self.human,"app-a","workflow.approval",rid,"submit",1)
        self.assertEqual(v["status"],"PendingLevel1")
        v=self.store.advance(self.human,"app-a","workflow.approval",rid,"approve",2)
        self.assertEqual(v["status"],"PendingLevel2")
        v=self.store.advance(self.human,"app-a","workflow.approval",rid,"approve",3)
        self.assertEqual(v["status"],"Approved")
        listing=self.store.view_rows(self.human,"app-a","view.contracts")
        self.assertEqual(listing["rows"][0]["cells"]["status"],"Approved")

    def test_runtime_exact_threshold_skips_second_level(self):
        self.seed_all()
        self.publish(change_id="publish-0002")
        row=self.store.submit_form(self.human,"app-a","form.contracts",{
            "contract_no":"CT-002","title":"Exact","amount_minor":100000000})
        self.store.advance(self.human,"app-a","workflow.approval",row["recordId"],"submit",1)
        res=self.store.advance(self.human,"app-a","workflow.approval",row["recordId"],"approve",2)
        self.assertEqual(res["status"],"Approved")

    def test_row_type_and_required_checks(self):
        self.seed_all()
        self.publish(change_id="publish-0003")
        self.assert_rejected("TYPE_MISMATCH",lambda:self.store.submit_form(
            self.human,"app-a","form.contracts",{
                "contract_no":"C-1","title":"X","amount_minor":"100"}))
        self.assert_rejected("REQUIRED_FIELD_MISSING",lambda:self.store.submit_form(
            self.human,"app-a","form.contracts",{"contract_no":"C-2","amount_minor":1}))

    def test_migration_guard_after_runtime_data(self):
        self.seed_all()
        self.publish(change_id="publish-0004")
        self.store.submit_form(self.human,"app-a","form.contracts",{
            "contract_no":"C-3","title":"X","amount_minor":4})
        modified=copy.deepcopy(SPECS["model.contracts"])
        modified["fields"][0]["type"]="integer"
        self.assert_rejected("MIGRATION_REQUIRED",
                             lambda:self.command(self.human,"model.contracts",modified))

    def test_published_snapshot_unmodified_by_draft(self):
        self.seed_all()
        self.publish(change_id="publish-0005")
        modified=copy.deepcopy(SPECS["form.contracts"])
        modified["title"]="Draft Changed"
        self.command(self.human,"form.contracts",modified)
        release=self.store.release(self.human,"app-a")
        self.assertEqual(release["definitions"]["form.contracts"]["title"],"合同登记")
        self.publish(change_id="publish-0006")
        self.assertEqual(self.store.release(self.human,"app-a")["version"],2)
        self.store.rollback(self.human,"app-a",{
            "changeId":"rollback-001",
            "expectedPublishedVersion":2,"targetVersion":1})
        self.assertEqual(self.store.release(self.human,"app-a")["version"],1)

    def test_direct_sql_drift_blocks_draft_but_keeps_release(self):
        self.seed_all()
        self.publish(change_id="publish-0007")
        with self.store.connect() as db:
            db.execute("UPDATE definitions SET spec=? WHERE app='app-a' AND rid='form.contracts'",
                ('{"kind":"form","model":"model.contracts","title":"Unsafe","fields":["title"]}',))
        self.assert_rejected("RESOURCE_DRIFT",lambda:self.store.draft(self.human,"app-a"))
        self.assert_rejected("APP_QUARANTINED",lambda:self.store.draft(self.human,"app-a"))
        self.assertEqual(self.store.release(self.human,"app-a")["version"],1)
        self.assertEqual(self.store.view_rows(self.human,"app-a","view.contracts")["columns"],
                         SPECS["view.contracts"]["columns"])

    def test_malicious_definition_is_schema_rejected(self):
        bad=copy.deepcopy(SPECS["model.contracts"])
        bad["execute"]="process.exit()"
        self.assert_rejected("INVALID_MODEL",lambda:self.command(self.agent,"model.contracts",bad))
        bad2=copy.deepcopy(SPECS["model.contracts"])
        bad2["fields"][0]["type"]=["arbitrary"]
        self.assert_rejected("INVALID_FIELDS",lambda:self.command(self.agent,"model.contracts",bad2))

    def test_stale_publish_does_not_change_release(self):
        self.seed_all()
        self.publish(change_id="publish-0008")
        modified=copy.deepcopy(SPECS["form.contracts"])
        modified["title"]="Later"
        self.command(self.human,"form.contracts",modified)
        self.assert_rejected("PUBLISH_STALE",lambda:self.publish(change_id="publish-0009",rev=4))
        self.assertEqual(self.store.release(self.human,"app-a")["version"],1)

if __name__=="__main__":
    unittest.main()
