"""Offline input, scope, stale snapshot and fixed output tests, no model API."""
import unittest
from propose import validate_patch

S={"title_label":"Human First Saved","status_label":"Status"}
P={"field":"status","expected_title":"Human First Saved",
   "expected_status":"Status","new_label":"AI Reviewed Status"}

class CollabContract(unittest.TestCase):
    def rejects(self,code,p):
        with self.assertRaises(RuntimeError) as caught:
            validate_patch(p,S)
        self.assertEqual(str(caught.exception),code)
    def test_valid_patch(self):
        self.assertEqual(validate_patch(dict(P),S),P)
    def test_ai_cannot_change_human_title(self):
        p={**P,"field":"title"}
        self.rejects("AGENT_PATCH_CANNOT_CHANGE_HUMAN_TITLE",p)
    def test_unknown_tool_parameter_rejected(self):
        self.rejects("AGENT_PATCH_SCHEMA_INVALID",{**P,"sql":"DROP TABLE"})
    def test_old_title_snapshot_rejected(self):
        self.rejects("AGENT_DID_NOT_GROUND_ON_REAL_NATIVE_SNAPSHOT",
                    {**P,"expected_title":"Title"})
    def test_old_target_snapshot_rejected(self):
        self.rejects("AGENT_DID_NOT_GROUND_ON_REAL_NATIVE_SNAPSHOT",
                    {**P,"expected_status":"Draft"})
    def test_unapproved_target_rejected(self):
        self.rejects("AGENT_PATCH_DEVIATED_FROM_REQUEST",
                    {**P,"new_label":"Whatever"})
    def test_no_leakage_of_extra_fields(self):
        self.rejects("AGENT_PATCH_SCHEMA_INVALID",{**P,"actor_id":"admin"})

    def test_native_cli_log_parser_ignores_source_code_echo(self):
        import json
        import tempfile
        from pathlib import Path
        from verify import event
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"cli.log"
            path.write_text(
              'const marker="S1_COLLAB_NATIVE_CAS|"; console.log(marker+JSON.stringify(...));\n'
              + 'S1_COLLAB_NATIVE_CAS|'+json.dumps({"decision":"APPLIED"})+'\n',
              encoding="utf-8")
            self.assertEqual(event(path),{"decision":"APPLIED"})

if __name__=="__main__":
    unittest.main()
