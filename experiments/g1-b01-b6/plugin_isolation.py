"""S1 B6 trusted host-side plugin process sandbox and explicit tool relay.

The untrusted plugin receives only an ephemeral read-only /workspace mount and
request.json: no database, host source tree, Docker socket, tool bearer, host
environment, or network. The host-only relay validates the output envelope
and performs typed v3 requests using the server-side per-plugin grant.

This is a one-shot stdout -> trusted HTTP relay, NOT an interactive SDK,
complete arbitrary-plugin isolation proof or production plugin supervisor.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request,urlopen

IMAGE_ID_RE=re.compile(r"sha256:[0-9a-f]{64}")
PLUGIN_ID_RE=re.compile(r"[a-z][a-z0-9-]{1,38}")
APP_RE=re.compile(r"app-[a-z0-9-]{1,30}")
MAX_BYTES=32768


class IsolationFailure(Exception):
    def __init__(self,code):
        super().__init__(code)
        self.code=code


@dataclass(frozen=True)
class PluginObservation:
    image_id: str
    plugin_id: str
    probes: dict
    http_status: int
    result: dict
    tool: str


class DockerPlugin:
    def __init__(self,image_id,base_url,token,app,plugin_id):
        if not isinstance(image_id,str) or not IMAGE_ID_RE.fullmatch(image_id):
            raise IsolationFailure("IMAGE_PIN_REQUIRED")
        if not isinstance(token,str) or len(token)<20:
            raise IsolationFailure("TRUSTED_HOST_TOKEN_REQUIRED")
        if not isinstance(app,str) or not APP_RE.fullmatch(app):
            raise IsolationFailure("INVALID_APP")
        if not isinstance(plugin_id,str) or not PLUGIN_ID_RE.fullmatch(plugin_id):
            raise IsolationFailure("PLUGIN_ID_INVALID")
        if not re.fullmatch(r"http://127\.0\.0\.1:[0-9]{1,5}",base_url):
            raise IsolationFailure("TRUSTED_LOOPBACK_REQUIRED")
        self.image_id=image_id
        self.base_url=base_url
        self.token=token # never forwarded inside Docker / request.json
        self.app=app
        self.plugin_id=plugin_id
        self.fixture=Path(__file__).with_name("plugin_untrusted.py")

    def docker_argv(self,workdir):
        return [
            "docker","run","--rm","--pull=never",
            "--network=none",
            "--read-only","--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--pids-limit=32","--memory=192m","--cpus=1",
            "--user=65534:65534",
            "--tmpfs","/tmp:rw,nosuid,nodev,noexec,size=8m",
            "--mount","type=bind,src="+str(workdir)+",dst=/workspace,readonly",
            "--workdir","/workspace",
            "--entrypoint","python3",
            self.image_id,"-I","-B","/workspace/plugin_untrusted.py"
        ]

    @staticmethod
    def parse(output):
        if not isinstance(output,str) or not 0<len(output.encode("utf-8"))<=MAX_BYTES:
            raise IsolationFailure("PLUGIN_OUTPUT_LIMIT")
        try:data=json.loads(output)
        except (ValueError,TypeError):
            raise IsolationFailure("PLUGIN_OUTPUT_NOT_JSON") from None
        if not isinstance(data,dict) or set(data)!={"protocol","request","probes"} or (
            data["protocol"]!="S1_B6_PLUGIN_REQUEST_V1"
        ):
            raise IsolationFailure("PLUGIN_PROTOCOL_INVALID")
        req=data["request"]
        if (not isinstance(req,dict) or set(req)!={"app","tool","args"} or
            not isinstance(req["app"],str) or not isinstance(req["tool"],str) or
            not 1<=len(req["tool"])<=64 or
            not isinstance(req["args"],dict)):
            raise IsolationFailure("PLUGIN_REQUEST_INVALID")
        probes=data["probes"]
        if not isinstance(probes,dict) or len(probes)>15:
            raise IsolationFailure("PLUGIN_PROBES_INVALID")
        return req,probes

    def _forward(self,tool,args):
        if "/" in tool or "?" in tool or "#" in tool or not re.fullmatch(
            r"[a-z][a-z0-9_.]{1,50}",tool
        ):
            # No arbitrary HTTP paths or protocols.
            return 403,{"error":"TOOL_NAME_INVALID"}
        raw=json.dumps(args,ensure_ascii=False,separators=(",",":")).encode("utf-8")
        if len(raw)>MAX_BYTES:
            return 422,{"error":"TOOL_PAYLOAD_TOO_LARGE"}
        req=Request(
            self.base_url+"/v3/apps/"+self.app+"/tools/"+tool,
            data=raw,method="POST",headers={
                "Authorization":"Bearer "+self.token,
                "Content-Type":"application/json"
            })
        try:
            with urlopen(req,timeout=45) as res:
                body=res.read(MAX_BYTES+1)
                status=res.status
        except HTTPError as error:
            body=error.read(MAX_BYTES+1)
            status=error.code
        except (OSError,TimeoutError):
            # Unknown delivery outcome: do not automatically retry.
            return 503,{"error":"UPSTREAM_OUTCOME_UNKNOWN"}
        if len(body)>MAX_BYTES:
            raise IsolationFailure("UPSTREAM_RESPONSE_LIMIT")
        try:
            content=json.loads(body)
        except ValueError:
            raise IsolationFailure("UPSTREAM_NOT_JSON") from None
        if not isinstance(content,dict):
            raise IsolationFailure("UPSTREAM_RESPONSE_INVALID")
        return status,content

    def run(self,request,host_db_path,host_sentinel_path):
        if not isinstance(request,dict):
            raise IsolationFailure("PLUGIN_REQUEST_INVALID")
        # The plugin is untrusted and can lie about the app and identity.
        # We NEVER use those assertions as real credentials.
        payload={"request":request,"hostDbPath":str(host_db_path),
                 "hostSentinelPath":str(host_sentinel_path)}
        if len(json.dumps(payload,ensure_ascii=False).encode())>MAX_BYTES:
            raise IsolationFailure("PLUGIN_REQUEST_TOO_LARGE")
        with tempfile.TemporaryDirectory(prefix="s1-b6-plugin-work-") as temp:
            work=Path(temp)
            work.chmod(0o755)
            (work/"plugin_untrusted.py").write_bytes(self.fixture.read_bytes())
            (work/"request.json").write_text(
                json.dumps(payload,ensure_ascii=False),encoding="utf-8")
            for file in work.iterdir():
                file.chmod(0o644)
            argv=self.docker_argv(work)
            try:
                # Docker inherits only the host's CLI environment; env provided
                # explicitly excludes secret-bearing variables even for the
                # Docker CLIENT, and Docker containers do not inherit either.
                result=subprocess.run(
                    argv,capture_output=True,text=True,timeout=25,
                    env={"PATH":os.environ.get("PATH","/usr/bin:/bin"),
                         "HOME":"/tmp","LANG":"C.UTF-8"},check=False)
            except (subprocess.TimeoutExpired,OSError):
                raise IsolationFailure("PLUGIN_DOCKER_FAILED") from None
            if result.returncode!=0:
                raise IsolationFailure("PLUGIN_DOCKER_NONZERO")
            req,probes=self.parse(result.stdout.strip())
        if req["app"]!=self.app:
            status,body=403,{"error":"PLUGIN_CROSS_APP_FORBIDDEN"}
        else:
            status,body=self._forward(req["tool"],req["args"])
        return PluginObservation(
            image_id=self.image_id,plugin_id=self.plugin_id,
            probes=probes,http_status=status,result=body,tool=req["tool"])


def complete_isolation(probes):
    """Independent observable predicate, not an excuse to trust plugin claims.

    Actual host DB snapshots, audit ledger and Docker CLI restrictions must
    ALSO be checked outside the untrusted container in the e2e suite.
    """
    return (isinstance(probes,dict) and
            probes.get("containerUid")==65534 and
            all(probes.get(k)=="DENIED" for k in (
                "dockerSocket","hostSqliteRwConnect","hostDbFileWrite",
                "hostDbFileRead",
                "hostSentinelRead","containerPluginFileWrite","internetTcp"
            )) and probes.get("hostSecretInherited") is False)
