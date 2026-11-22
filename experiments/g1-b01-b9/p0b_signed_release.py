"""P0-B bounded B14 Ed25519 attestation of CURRENT B2 published Model/View.

Only the trusted Kernel Linux UID may sign, with its real 0700 private
authority.sqlite and Ed25519 private key. Consumers see just the public key.
Separate domain from B14 signed BUSINESS events; never sign caller JSON.
No claim of B4 code, Form/Workflow runtime parity, PKI or key rotation.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,Ed25519PublicKey)
from cryptography.hazmat.primitives import serialization

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
sys.path.insert(0,str(ROOT/"g1-b01-b2"))
sys.path.insert(0,str(ROOT/"g1-b01-b14"))
from schema_core import SchemaStore,Actor
from projector import compile_release,check_compiled
from signed_projection import make_keypair,key_id

DOMAIN=b"OpenAILCAP/G1/B14/B2-current-published-release/v1\x00"
PAYLOAD_FIELDS={"app","version","draftRevision","manifestHash",
                "projectionPackHash","viewColumns"}
SIGNED_FIELDS={"payload","keyId","signature"}


class ReleaseSignatureRejected(Exception):
    def __init__(self,code):
        super().__init__(code)
        self.code=code


def canon(x):
    return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(",",":"))


def verify(signed,public_hex):
    if not isinstance(signed,dict) or set(signed)!=SIGNED_FIELDS:
        raise ReleaseSignatureRejected("SIGNED_RELEASE_SHAPE_INVALID")
    p=signed["payload"]
    if not isinstance(p,dict) or set(p)!=PAYLOAD_FIELDS or (
        p["app"]!="app-a" or type(p["version"]) is not int or
        p["version"]<1 or type(p["draftRevision"]) is not int or
        not isinstance(p["viewColumns"],list) or
        not p["viewColumns"] or
        any(col not in ("contract_no","title","amount_minor","status")
            for col in p["viewColumns"]) or
        len(set(p["viewColumns"]))!=len(p["viewColumns"]) or
        any(not isinstance(p[k],str) or not re.fullmatch(r"[0-9a-f]{64}",p[k])
            for k in ("manifestHash","projectionPackHash"))):
        raise ReleaseSignatureRejected("SIGNED_RELEASE_PAYLOAD_INVALID")
    try:
        public=bytes.fromhex(public_hex)
        if len(public)!=32 or key_id(public)!=signed["keyId"]:
            raise ReleaseSignatureRejected("SIGNED_RELEASE_KEY_MISMATCH")
        signature=base64.b64decode(signed["signature"],validate=True)
        Ed25519PublicKey.from_public_bytes(public).verify(
            signature,DOMAIN+canon(p).encode("utf-8"))
        return p
    except ReleaseSignatureRejected:
        raise
    except Exception:
        raise ReleaseSignatureRejected("SIGNED_RELEASE_SIGNATURE_INVALID") from None


def _scope(db,key):
    if not (str(db).startswith("/tmp/s1-b9-derive-") and
            str(db).endswith("/authority-private/authority.sqlite") and
            str(key).startswith("/tmp/s1-b9-derive-") and
            "/authority-private/" in str(key)):
        raise ReleaseSignatureRejected("KERNEL_PRIVATE_PATH_SCOPE_INVALID")
    folder=Path(db).parent
    if folder.stat().st_mode&0o077 or folder.stat().st_uid!=os.getuid():
        raise ReleaseSignatureRejected("KERNEL_PRIVATE_DAC_INVALID")


def sign_from_current_db(db,key,template):
    _scope(db,key)
    key=Path(key)
    if key.stat().st_mode&0o077 or key.stat().st_uid!=os.getuid():
        raise ReleaseSignatureRejected("SIGNING_KEY_EXPOSED")
    # Physically read the LIVE authoritative B2 pointer under KERNEL UID;
    # the client is not allowed to supply version/hash/specs for signing.
    source=SchemaStore(db).release(
        Actor("p0b-kernel-release-signer","app-a",can_runtime=True),"app-a")
    projection=compile_release(source,json.loads(Path(template).read_text()))
    check_compiled(projection)
    payload={
        "app":"app-a","version":source["version"],
        "draftRevision":source["draftRevision"],
        "manifestHash":source["manifestHash"],
        "projectionPackHash":projection["projectionPackHash"],
        "viewColumns":source["definitions"]["view.contracts"]["columns"]
    }
    private=Ed25519PrivateKey.from_private_bytes(key.read_bytes())
    public=private.public_key().public_bytes(
        serialization.Encoding.Raw,serialization.PublicFormat.Raw)
    signed={"payload":payload,"keyId":key_id(public),
            "signature":base64.b64encode(
                private.sign(DOMAIN+canon(payload).encode("utf-8"))
            ).decode("ascii")}
    if verify(signed,public.hex())!=payload:
        raise ReleaseSignatureRejected("KERNEL_SELF_VERIFICATION_FAILED")
    return signed


def main():
    p=argparse.ArgumentParser()
    p.add_argument("action",choices=("init","sign"))
    p.add_argument("--key",required=True)
    p.add_argument("--db",required=True)
    p.add_argument("--template")
    a=p.parse_args()
    _scope(a.db,a.key)
    if a.action=="init":
        public=make_keypair(a.key)
        print("P0B_PUBLIC_KEY|"+public,flush=True)
    else:
        if not a.template:
            raise SystemExit("KERNEL_TEMPLATE_REQUIRED")
        signed=sign_from_current_db(a.db,a.key,a.template)
        print("P0B_SOURCE|"+canon(signed),flush=True)


if __name__=="__main__":
    main()
