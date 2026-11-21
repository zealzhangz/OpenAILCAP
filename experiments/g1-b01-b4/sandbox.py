"""Trusted host-only B4 Docker executor; no model access to Docker or DB.

Every call uses the same pinned local image ID, a read-only bind mount,
no network, no Linux capabilities, no privilege elevation, bounded CPU/RAM.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from policy import RuleError,oracle,source_hash,validate_source


@dataclass(frozen=True)
class SandboxProof:
    source_hash: str
    cases: int
    image_id: str
    result: int | None


class DockerSandbox:
    def __init__(self,image_id=None):
        self.image_id=image_id or os.environ.get("S1_B4_IMAGE_ID","")
        if not re.fullmatch(r"sha256:[a-f0-9]{64}",self.image_id):
            raise RuleError("PINNED_IMAGE_ID_REQUIRED")
        self.worker=Path(__file__).with_name("worker.py")

    def command(self,path):
        return [
            "docker","run","--rm",
            "--pull=never","--network=none","--read-only",
            "--cap-drop=ALL","--security-opt=no-new-privileges",
            "--pids-limit=32","--memory=192m","--cpus=1",
            "--user=65534:65534","--tmpfs","/tmp:rw,nosuid,nodev,size=8m",
            "--mount","type=bind,src="+str(path)+",dst=/workspace,readonly",
            "--workdir","/workspace","--entrypoint","python3",
            self.image_id,"-I","-B","/workspace/worker.py"
        ]

    def test(self,src,payload=None):
        approved=validate_source(src)
        if payload is not None:
            if not isinstance(payload,dict) or set(payload)!={
                "amount_minor","supplier_score","months_active"
            }:
                raise RuleError("RUNTIME_INPUT_SHAPE")
            oracle(payload["amount_minor"],payload["supplier_score"],
                   payload["months_active"]) # validate independently before sandbox
        with tempfile.TemporaryDirectory(prefix="s1-b4-sandbox-") as tmp:
            path=Path(tmp)
            path.chmod(0o755) # container user=65534 must be able to traverse
            (path/"rule.py").write_text(src,encoding="utf-8")
            (path/"worker.py").write_bytes(self.worker.read_bytes())
            if payload is not None:
                (path/"payload.json").write_text(json.dumps(payload),encoding="utf-8")
            for f in path.iterdir():
                f.chmod(0o644)
            try:
                run=subprocess.run(self.command(path),capture_output=True,text=True,
                                   timeout=45,check=False)
            except (subprocess.TimeoutExpired,OSError):
                raise RuleError("SANDBOX_PROCESS_FAILED") from None
            if run.returncode!=0:
                raise RuleError("SANDBOX_TEST_FAILED")
            try:
                observed=json.loads(run.stdout.strip())
            except (ValueError,TypeError):
                raise RuleError("SANDBOX_OUTPUT_INVALID") from None
            if (not isinstance(observed,dict) or
                observed.get("status")!="PASS" or
                observed.get("passed")!=432 or observed.get("cases")!=432 or
                observed.get("sourceHash")!=approved["sourceHash"]):
                raise RuleError("SANDBOX_ORACLE_INCOMPLETE")
            score=observed.get("result")
            if payload is None and score is not None:
                raise RuleError("SANDBOX_RESULT_INVALID")
            if payload is not None and (
                type(score) is not int or
                score!=oracle(payload["amount_minor"],payload["supplier_score"],
                              payload["months_active"])
            ):
                raise RuleError("SANDBOX_RESULT_MISMATCH")
            return SandboxProof(approved["sourceHash"],432,self.image_id,score)
