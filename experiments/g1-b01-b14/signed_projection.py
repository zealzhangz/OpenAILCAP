"""B14 Ed25519 domain-separated B2 projection event signing.

The private key is generated and kept ONLY by Kernel UID; consumer and
Saltcorn receive only the pinned public key. The signing service signs the
exact B11 event-time payload (including its hash), never arbitrary JSON from
a consumer. This is a bounded research key v1, not PKI/key rotation.
"""
from __future__ import annotations
import base64
import hashlib
import json
import os
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey,Ed25519PublicKey
from cryptography.hazmat.primitives import serialization

DOMAIN=b"OpenAILCAP/B14/authoritative-contract-event/v1\x00"
FIELDS=frozenset(("app","seq","model","recordId","version","cells","eventHash"))
SIGNED_FIELDS=FIELDS|frozenset(("keyId","eventSig"))


class SignatureRefused(Exception):
    def __init__(self,code):
        self.code=code
        super().__init__(code)


def canon(obj):
    return json.dumps(obj,sort_keys=True,ensure_ascii=False,separators=(",",":"))


def key_id(public_raw):
    return hashlib.sha256(b"OpenAILCAP-B14-ED25519-PUB-V1"+public_raw).hexdigest()[:24]


def make_keypair(private_path):
    path=Path(private_path)
    if path.exists() or path.is_symlink():
        raise SignatureRefused("SIGNING_KEY_ALREADY_EXISTS")
    key=Ed25519PrivateKey.generate()
    raw=key.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption())
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try:
        with os.fdopen(fd,"wb") as f:
            f.write(raw)
    finally:
        os.chmod(path,0o600)
    public=key.public_key().public_bytes(
        serialization.Encoding.Raw,serialization.PublicFormat.Raw)
    return public.hex()


def sign_event(event,private_path):
    if not isinstance(event,dict) or set(event)!=FIELDS:
        raise SignatureRefused("EVENT_SHAPE_INVALID")
    key=Ed25519PrivateKey.from_private_bytes(Path(private_path).read_bytes())
    public=key.public_key().public_bytes(
        serialization.Encoding.Raw,serialization.PublicFormat.Raw)
    sig=key.sign(DOMAIN+canon(event).encode())
    return {**event,"keyId":key_id(public),
            "eventSig":base64.b64encode(sig).decode("ascii")}


def verify_event(signed,public_hex):
    if not isinstance(signed,dict) or set(signed)!=SIGNED_FIELDS:
        raise SignatureRefused("SIGNED_EVENT_SHAPE_INVALID")
    try:
        public=bytes.fromhex(public_hex)
        if len(public)!=32 or signed["keyId"]!=key_id(public):
            raise SignatureRefused("SIGNING_KEY_ID_INVALID")
        sig=base64.b64decode(signed["eventSig"],validate=True)
        if len(sig)!=64:raise SignatureRefused("EVENT_SIGNATURE_INVALID")
        unsigned={k:signed[k] for k in FIELDS}
        Ed25519PublicKey.from_public_bytes(public).verify(
            sig,DOMAIN+canon(unsigned).encode())
        return unsigned
    except SignatureRefused:
        raise
    except (ValueError,TypeError,KeyError,Exception) as exc:
        # Ed25519 InvalidSignature and malformed encoding are fail-closed.
        raise SignatureRefused("EVENT_SIGNATURE_INVALID") from None
