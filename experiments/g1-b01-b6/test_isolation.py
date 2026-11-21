"""B6 independent host-side rejection and exact Docker CLI policy tests."""
import json
import re
import tempfile
import unittest
from pathlib import Path
from plugin_isolation import DockerPlugin,IsolationFailure,complete_isolation

IMAGE="sha256:"+"1"*64
TOKEN="t"*36
BASE="http://127.0.0.1:19999"


def fixture(**changes):
    obj={"protocol":"S1_B6_PLUGIN_REQUEST_V1",
         "request":{"app":"app-a","tool":"draft.read","args":{}},
         "probes":{"containerUid":65534,"dockerSocket":"DENIED",
                   "hostSqliteRwConnect":"DENIED","hostDbFileWrite":"DENIED",
                   "hostDbFileRead":"DENIED",
                   "hostSentinelRead":"DENIED","containerPluginFileWrite":"DENIED",
                   "internetTcp":"DENIED","hostSecretInherited":False}}
    obj.update(changes)
    return obj


class HostPolicyUnit(unittest.TestCase):
    def new(self):return DockerPlugin(IMAGE,BASE,TOKEN,"app-a","view-plugin")
    def reject(self,code,fn):
        with self.assertRaises(IsolationFailure) as e:fn()
        self.assertEqual(e.exception.code,code)
    def test_pinned_image_required(self):
        self.reject("IMAGE_PIN_REQUIRED",
                    lambda:DockerPlugin("python:latest",BASE,TOKEN,"app-a","plug"))
    def test_image_exact_hash(self):
        self.assertEqual(self.new().image_id,IMAGE)
    def test_short_host_token_refused(self):
        self.reject("TRUSTED_HOST_TOKEN_REQUIRED",
                    lambda:DockerPlugin(IMAGE,BASE,"no","app-a","plug"))
    def test_broker_only_local_loopback(self):
        self.reject("TRUSTED_LOOPBACK_REQUIRED",
                    lambda:DockerPlugin(IMAGE,"http://api.example.com",TOKEN,
                                        "app-a","plug"))
    def test_invalid_plugin_id_refused(self):
        self.reject("PLUGIN_ID_INVALID",
                    lambda:DockerPlugin(IMAGE,BASE,TOKEN,"app-a","../root"))
    def test_invalid_app_id_refused(self):
        self.reject("INVALID_APP",
                    lambda:DockerPlugin(IMAGE,BASE,TOKEN,"/etc/passwd","p-safe"))
    def test_no_network(self):
        self.assertIn("--network=none",self.new().docker_argv(Path("/tmp/safe")))
    def test_nonroot_and_no_privilege(self):
        x=self.new().docker_argv(Path("/tmp/safe"))
        self.assertIn("--user=65534:65534",x)
        self.assertIn("--cap-drop=ALL",x)
        self.assertIn("--security-opt=no-new-privileges",x)
        self.assertNotIn("--privileged",x)
    def test_no_docker_sock_or_db_mount(self):
        x=self.new().docker_argv(Path("/tmp/safe"))
        mounts=[x[i+1] for i,v in enumerate(x[:-1]) if v=="--mount"]
        self.assertEqual(mounts,
                         ["type=bind,src=/tmp/safe,dst=/workspace,readonly"])
        self.assertNotIn("/var/run/docker.sock"," ".join(x))
    def test_readonly_cpu_memory_and_pid_bounds(self):
        x=self.new().docker_argv(Path("/tmp/safe"))
        for flag in ("--read-only","--pids-limit=32","--memory=192m",
                     "--cpus=1","--pull=never","--rm"):
            self.assertIn(flag,x)
    def test_output_extra_fields_rejected(self):
        data=fixture(unapprovedRole="admin")
        self.reject("PLUGIN_PROTOCOL_INVALID",
                    lambda:DockerPlugin.parse(json.dumps(data)))
    def test_output_wrong_protocol_rejected(self):
        data=fixture(protocol="S1_B5_NOT_PLUGIN")
        self.reject("PLUGIN_PROTOCOL_INVALID",
                    lambda:DockerPlugin.parse(json.dumps(data)))
    def test_output_malformed_json_refused(self):
        self.reject("PLUGIN_OUTPUT_NOT_JSON",lambda:DockerPlugin.parse("{"))
    def test_output_long_refused(self):
        self.reject("PLUGIN_OUTPUT_LIMIT",
                    lambda:DockerPlugin.parse("x"*40000))
    def test_actor_field_in_envelope_rejected(self):
        data=fixture()
        data["request"]["actorId"]="admin"
        self.reject("PLUGIN_REQUEST_INVALID",
                    lambda:DockerPlugin.parse(json.dumps(data)))
    def test_request_arguments_shape_required(self):
        data=fixture()
        data["request"]["args"]=["runSql"]
        self.reject("PLUGIN_REQUEST_INVALID",
                    lambda:DockerPlugin.parse(json.dumps(data)))
    def test_valid_output_parsed_but_not_trusted(self):
        data=fixture()
        req,probes=DockerPlugin.parse(json.dumps(data))
        self.assertEqual(req["tool"],"draft.read")
        self.assertTrue(complete_isolation(probes))
    def test_root_uid_fails_isolation(self):
        x=fixture()["probes"];x["containerUid"]=0
        self.assertFalse(complete_isolation(x))
    def test_network_success_fails_isolation(self):
        x=fixture()["probes"];x["internetTcp"]="CONNECTED"
        self.assertFalse(complete_isolation(x))
    def test_host_database_read_access_fails_isolation(self):
        x=fixture()["probes"];x["hostDbFileRead"]="OPENED"
        self.assertFalse(complete_isolation(x))
    def test_host_secret_exposure_fails_isolation(self):
        x=fixture()["probes"];x["hostSecretInherited"]=True
        self.assertFalse(complete_isolation(x))
    def test_local_db_connected_fails_isolation(self):
        x=fixture()["probes"];x["hostSqliteRwConnect"]="CONNECTED"
        self.assertFalse(complete_isolation(x))
    def test_mounted_workspace_mutability_fails(self):
        x=fixture()["probes"];x["containerPluginFileWrite"]="OPENED"
        self.assertFalse(complete_isolation(x))
    def test_egress_tool_path_blocks_slash(self):
        status,data=self.new()._forward("../../admin",{})
        self.assertEqual((status,data["error"]),(403,"TOOL_NAME_INVALID"))
    def test_egress_typed_payload_bound(self):
        status,data=self.new()._forward("metadata.upsert",{"payload":"x"*40000})
        self.assertEqual((status,data["error"]),(422,"TOOL_PAYLOAD_TOO_LARGE"))

if __name__=="__main__":unittest.main()
