"""G1 P0-A trusted Pack admission gate for DISPOSABLE Saltcorn staging only.

Every submitted Pack is fully diffed against an independently checked
running Native baseline. Only the EXACT Pack freshly compiled from the
B2 v3 release.read (not a plugin-supplied Pack/manifest/version) is admissible.
A simulated privileged human grants a one-use HMAC-bound approval. Install
happens on a separate staging DB, never the live runtime DB.

LIMITATIONS: prototype trusted-controller approval, NOT production SSO, does
not prevent the Saltcorn owner from directly changing its disposable DB; no
signed source/atomic public cutover/Code/Workflow semantics.
"""
from __future__ import annotations

import copy
import hashlib
import hmac
import json
import secrets
import time
from pathlib import Path

from projector import (ProjectionRejected, check_compiled, compile_release,
                       canon, hash_pack)

MAX_PACK_BYTES = 262144
MAX_DIFF_ENTRIES = 4096
MAX_DEPTH = 24


class PackGateDenied(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _pointer_segment(s):
    return str(s).replace("~", "~0").replace("/", "~1")


def _full_diff(before, after):
    """JSON-pointer diff: also reports removals, list changes and new keys.

    This does not omit "unimportant" Pack domains (roles/plugins/pages/etc.).
    It does not naively use truthiness (False, None, 0 are distinct values).
    """
    changes = []
    def walk(a, b, path, depth):
        if depth > MAX_DEPTH or len(changes) > MAX_DIFF_ENTRIES:
            raise PackGateDenied("PACK_DIFF_LIMIT")
        if isinstance(a, dict) and isinstance(b, dict):
            for key in sorted(a.keys() | b.keys()):
                location = path + "/" + _pointer_segment(key)
                if key not in a:
                    changes.append({"path": location,"operation":"add",
                                    "after":copy.deepcopy(b[key])})
                elif key not in b:
                    changes.append({"path": location,"operation":"remove",
                                    "before":copy.deepcopy(a[key])})
                else:
                    walk(a[key], b[key], location, depth+1)
        elif isinstance(a,list) and isinstance(b,list):
            for i in range(max(len(a),len(b))):
                location = path + "/" + str(i)
                if i >= len(a):
                    changes.append({"path":location,"operation":"add",
                                    "after":copy.deepcopy(b[i])})
                elif i >= len(b):
                    changes.append({"path":location,"operation":"remove",
                                    "before":copy.deepcopy(a[i])})
                else:
                    walk(a[i],b[i],location,depth+1)
        elif type(a) is not type(b) or a!=b:
            changes.append({"path":path or "/","operation":"replace",
                            "before":copy.deepcopy(a),"after":copy.deepcopy(b)})
    walk(before,after,"",0)
    if len(changes)>MAX_DIFF_ENTRIES:
        raise PackGateDenied("PACK_DIFF_LIMIT")
    return changes


def _check_pack(value):
    if not isinstance(value,dict):
        raise PackGateDenied("PACK_OBJECT_REQUIRED")
    try:
        encoded=canon(value).encode("utf-8")
    except (TypeError,ValueError,RecursionError):
        raise PackGateDenied("PACK_JSON_INVALID") from None
    if not 0<len(encoded)<=MAX_PACK_BYTES:
        raise PackGateDenied("PACK_SIZE_LIMIT")
    return len(encoded)


class PackApprovalGate:
    def __init__(self, *, source_reader, template, baseline_pack,
                 approved_human="b9-human-approved-release"):
        self._source_reader=source_reader
        self._template=copy.deepcopy(template)
        self._baseline=copy.deepcopy(baseline_pack)
        self._baseline_sha=hash_pack(baseline_pack)
        self._human=approved_human
        self._secret=secrets.token_bytes(32)
        self._plans={}
        self._used=set()
        _check_pack(self._baseline)

    def _source(self):
        try:
            source=self._source_reader()
            compiled=compile_release(source,self._template)
            check_compiled(compiled)
        except (ProjectionRejected,KeyError,ValueError,TypeError):
            raise PackGateDenied("SOURCE_NOT_VERIFIED") from None
        if compiled["app"]!="app-a" or compiled["sourceVersion"]<1:
            raise PackGateDenied("SOURCE_APP_UNSUPPORTED")
        return compiled

    def review(self, candidate):
        """Return FULL diff even when candidate adds unrelated Pack resources."""
        size=_check_pack(candidate)
        source=self._source()
        diff=_full_diff(self._baseline,candidate)
        expected=source["projectionPack"]
        accepted = (candidate == expected and
                    hash_pack(candidate)==source["projectionPackHash"])
        return {
            "app":"app-a",
            "sourceVersion":source["sourceVersion"],
            "manifestHash":source["manifestHash"],
            "baselinePackHash":self._baseline_sha,
            "candidatePackHash":hash_pack(candidate),
            "expectedPackHash":source["projectionPackHash"],
            "diff":diff,"diffCount":len(diff),"candidateBytes":size,
            "decision":"REVIEWABLE" if accepted else "REJECTED_UNTRUSTED_PACK",
            "safeScope":["model.contracts","view.contracts"]
        }

    @staticmethod
    def _fingerprint(review):
        return hashlib.sha256(canon({k:review[k] for k in (
            "app","sourceVersion","manifestHash","baselinePackHash",
            "candidatePackHash","expectedPackHash","diff"
        )}).encode()).hexdigest()

    def propose(self,candidate):
        report=self.review(candidate)
        if report["decision"]!="REVIEWABLE":
            raise PackGateDenied("UNVETTED_PACK_DEFAULT_DENY")
        nonce=secrets.token_hex(20)
        plan={"nonce":nonce,"fingerprint":self._fingerprint(report),
              "report":report}
        self._plans[nonce]=plan
        return copy.deepcopy(plan)

    def approve(self,plan,*,actor,privileged=False):
        if actor!=self._human or privileged is not True:
            raise PackGateDenied("PACK_PRIVILEGED_HUMAN_REQUIRED")
        nonce=plan.get("nonce") if isinstance(plan,dict) else None
        registered=self._plans.get(nonce)
        if registered is None or registered!=plan or nonce in self._used:
            raise PackGateDenied("PACK_PLAN_UNRECOGNIZED")
        payload={
            "nonce":nonce,"fingerprint":plan["fingerprint"],
            "actor":actor,"issuedAt":int(time.time())
        }
        signature=hmac.new(self._secret,canon(payload).encode(),
                           hashlib.sha256).hexdigest()
        return {**payload,"signature":signature}

    def apply(self,plan,approval,candidate,*,executor):
        nonce=plan.get("nonce") if isinstance(plan,dict) else None
        registered=self._plans.get(nonce)
        if not isinstance(plan,dict) or registered is None or (
            registered!=plan) or nonce in self._used:
            raise PackGateDenied("PACK_PLAN_UNRECOGNIZED")
        if not isinstance(approval,dict) or set(approval)!={
            "nonce","fingerprint","actor","issuedAt","signature"
        }:
            raise PackGateDenied("PACK_APPROVAL_REQUIRED")
        if approval["nonce"]!=nonce or approval["actor"]!=self._human or (
            approval["fingerprint"]!=plan["fingerprint"]):
            raise PackGateDenied("PACK_APPROVAL_WRONG_SCOPE")
        payload={k:approval[k] for k in (
            "nonce","fingerprint","actor","issuedAt"
        )}
        signature=hmac.new(self._secret,canon(payload).encode(),
                           hashlib.sha256).hexdigest()
        if not isinstance(approval["signature"],str) or not hmac.compare_digest(
            signature,approval["signature"]
        ):
            raise PackGateDenied("PACK_APPROVAL_FORGED")
        if type(approval["issuedAt"]) is not int or (
            not 0<=time.time()-approval["issuedAt"]<180):
            raise PackGateDenied("PACK_APPROVAL_EXPIRED")
        # Revalidate source pointer AND every Pack byte immediately before
        # dispatch. Changed authority release => old approval cannot apply.
        fresh=self.review(candidate)
        if fresh["decision"]!="REVIEWABLE" or (
            self._fingerprint(fresh)!=plan["fingerprint"]):
            raise PackGateDenied("PACK_SOURCE_MOVED_OR_CANDIDATE_CHANGED")
        self._used.add(nonce)  # one-shot EVEN when executor fails.
        # The EXECUTOR is the trusted staging-only native launcher.
        result=executor(copy.deepcopy(candidate))
        # A move while native import executed makes stage UNTRUSTED.
        after=self.review(candidate)
        if after["decision"]!="REVIEWABLE" or (
            self._fingerprint(after)!=plan["fingerprint"]):
            raise PackGateDenied("PACK_SOURCE_MOVED_DURING_INSTALL")
        return {"decision":"STAGED_ONLY","sourceVersion":after["sourceVersion"],
                "manifestHash":after["manifestHash"],
                "packHash":after["candidatePackHash"],
                "diffHash":plan["fingerprint"],"diffCount":after["diffCount"],
                "actor":self._human,"executorResult":result}

    @property
    def used_count(self):
        return len(self._used)
