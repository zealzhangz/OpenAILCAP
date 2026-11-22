"""Pure-unit fast tests; E2E separately runs actual official Saltcorn CLI."""
from __future__ import annotations
import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
sys.path.insert(0,str(ROOT/"g1-b01-b2"))
from schema_core import sha
from pack_approval_gate import PackApprovalGate,PackGateDenied,_full_diff
from projector import compile_release

def fixture():
    defs=json.loads((ROOT/"g1-b01-b2"/"contract_spec.json").read_text())
    template=json.loads((ROOT/"platform-saltcorn"/"contract-pack.json").read_text())
    v1={"version":1,"draftRevision":4,"manifestHash":sha(defs),
        "definitions":defs}
    v3=copy.deepcopy(v1)
    v3["version"]=3
    v3["draftRevision"]=16
    v3["definitions"]["view.contracts"]["columns"]=[
        "contract_no","title","amount_minor","status"]
    v3["manifestHash"]=sha(v3["definitions"])
    base=compile_release(v1,template)["projectionPack"]
    good=compile_release(v3,template)["projectionPack"]
    state={"source":v3}
    gate=PackApprovalGate(source_reader=lambda:state["source"],
                          template=template,baseline_pack=base)
    return gate,base,good,state

def throws(code, fn):
    with unittest.TestCase().assertRaises(PackGateDenied) as c:
        fn()
    if c.exception.code!=code:
        raise AssertionError((code,c.exception.code))

class PackAdmissionTests(unittest.TestCase):
    def test_full_diff_includes_order_types_add_and_remove(self):
        diff=_full_diff({"roles":[{"name":"editor"}],"plugins":[],"a":True},
                        {"roles":[{"name":"admin"}],"plugins":[{"id":1}],
                         "a":False,"secret":{"flag":0}})
        self.assertEqual({d["path"] for d in diff},
            {"/roles/0/name","/plugins/0","/a","/secret"})
        self.assertIn({"path":"/a","operation":"replace","before":True,
                       "after":False},diff)

    def test_full_diff_tracks_removed_arrays_and_keys(self):
        diff=_full_diff({"a":[1,2,3],"removed":None},
                        {"a":[1]})
        self.assertEqual({x["path"] for x in diff},
                         {"/a/1","/a/2","/removed"})
        self.assertTrue(all(x["operation"]=="remove" for x in diff))

    def test_pack_diff_uses_json_pointer_escape(self):
        diff=_full_diff({"a/b~c":2},{"a/b~c":3})
        self.assertEqual(diff[0]["path"],"/a~1b~0c")

    def test_valid_fresh_release_review_is_nonempty_deterministic(self):
        gate,base,good,_=fixture()
        a=gate.review(good)
        b=gate.review(good)
        self.assertEqual(a,b)
        self.assertEqual(a["decision"],"REVIEWABLE")
        self.assertGreater(a["diffCount"],0)
        self.assertTrue(any(x["path"].startswith(
            "/views/0/configuration/columns") for x in a["diff"]))
        self.assertNotEqual(a["baselinePackHash"],a["candidatePackHash"])

    def test_unlisted_pack_roles_plugins_tables_all_reported_but_denied(self):
        gate,_,good,_=fixture()
        bad=copy.deepcopy(good)
        bad["roles"]=[{"name":"root"}]
        bad["plugins"]=[{"name":"untrusted"}]
        bad["tables"].append({"name":"new-data-table"})
        report=gate.review(bad)
        self.assertEqual(report["decision"],"REJECTED_UNTRUSTED_PACK")
        self.assertTrue(all(any(x["path"].startswith(prefix)
                                for x in report["diff"])
                            for prefix in ("/roles/0","/plugins/0","/tables/1")))
        throws("UNVETTED_PACK_DEFAULT_DENY",lambda:gate.propose(bad))

    def test_no_approval_cannot_call_executor(self):
        gate,_,good,_=fixture()
        plan=gate.propose(good)
        called=[]
        throws("PACK_APPROVAL_REQUIRED",
               lambda:gate.apply(plan,None,good,
                                 executor=lambda x:called.append(x)))
        self.assertEqual(called,[])
        self.assertEqual(gate.used_count,0)

    def test_plugin_and_without_human_privilege_denied(self):
        gate,_,good,_=fixture()
        plan=gate.propose(good)
        throws("PACK_PRIVILEGED_HUMAN_REQUIRED",
               lambda:gate.approve(plan,actor="plugin",privileged=True))
        throws("PACK_PRIVILEGED_HUMAN_REQUIRED",
               lambda:gate.approve(plan,actor="b9-human-approved-release",
                                   privileged=False))

    def test_forged_approval_and_plan_refused(self):
        gate,_,good,_=fixture()
        plan=gate.propose(good)
        approval=gate.approve(plan,actor="b9-human-approved-release",
                              privileged=True)
        altered=copy.deepcopy(approval)
        altered["signature"]="a"*64
        throws("PACK_APPROVAL_FORGED",
               lambda:gate.apply(plan,altered,good,executor=lambda x:x))
        different=copy.deepcopy(plan)
        different["fingerprint"]="b"*64
        throws("PACK_PLAN_UNRECOGNIZED",
               lambda:gate.approve(different,
                  actor="b9-human-approved-release",privileged=True))
        self.assertEqual(gate.used_count,0)

    def test_change_after_approval_cannot_run_cli(self):
        gate,_,good,_=fixture()
        plan=gate.propose(good)
        approval=gate.approve(plan,actor="b9-human-approved-release",
                              privileged=True)
        changed=copy.deepcopy(good)
        changed["views"][0]["name"]="malicious"
        called=[]
        throws("PACK_SOURCE_MOVED_OR_CANDIDATE_CHANGED",
               lambda:gate.apply(plan,approval,changed,
                                 executor=lambda x:called.append(x)))
        self.assertEqual(called,[])

    def test_one_shot_approval_replay_denied(self):
        gate,_,good,_=fixture()
        plan=gate.propose(good)
        approval=gate.approve(plan,actor="b9-human-approved-release",
                              privileged=True)
        calls=[]
        result=gate.apply(plan,approval,good,executor=lambda x:calls.append(x))
        self.assertEqual(result["decision"],"STAGED_ONLY")
        throws("PACK_PLAN_UNRECOGNIZED",
               lambda:gate.apply(plan,approval,good,
                                 executor=lambda x:calls.append(x)))
        self.assertEqual(calls,[good])

    def test_failed_executor_is_also_one_shot(self):
        gate,_,good,_=fixture()
        plan=gate.propose(good)
        approval=gate.approve(plan,actor="b9-human-approved-release",
                              privileged=True)
        def fail(x):raise PackGateDenied("TEST_STAGE_FAILED")
        throws("TEST_STAGE_FAILED",
               lambda:gate.apply(plan,approval,good,executor=fail))
        throws("PACK_PLAN_UNRECOGNIZED",
               lambda:gate.apply(plan,approval,good,executor=fail))
        self.assertEqual(gate.used_count,1)

    def test_old_approval_invalid_when_current_release_rolls_back(self):
        gate,base,good,state=fixture()
        plan=gate.propose(good)
        approval=gate.approve(plan,actor="b9-human-approved-release",
                              privileged=True)
        state["source"]["version"]=1
        called=[]
        throws("PACK_SOURCE_MOVED_OR_CANDIDATE_CHANGED",
               lambda:gate.apply(plan,approval,good,
                                 executor=lambda x:called.append(x)))
        self.assertEqual(called,[])

    def test_approval_expires_after_three_minutes(self):
        gate,_,good,_=fixture()
        plan=gate.propose(good)
        approval=gate.approve(plan,actor="b9-human-approved-release",
                              privileged=True)
        with patch("pack_approval_gate.time.time",
                   return_value=approval["issuedAt"]+181):
            throws("PACK_APPROVAL_EXPIRED",
                   lambda:gate.apply(plan,approval,good,executor=lambda x:x))

    def test_source_error_is_not_silently_treated_as_fresh(self):
        gate,_,good,state=fixture()
        state["source"]["definitions"]["view.contracts"]["title"]="tampered"
        throws("SOURCE_NOT_VERIFIED",lambda:gate.review(good))

if __name__=="__main__":
    unittest.main()
