"""B14 cryptographic source-auth and independent read-only IPC contracts."""
import copy
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from signed_projection import (make_keypair,sign_event,verify_event,
                               SignatureRefused)
from signed_native_ipc import SignedBroker
from guard_router import source_events,verify
from audit_reader import native_snapshot

SAMPLE={"app":"app-a","seq":1,"model":"model.contracts",
        "recordId":"a1b2c3d4e5f6071829","version":1,
        "cells":{"contract_no":"HT-2026-000001",
                 "title":"B2 real contract","amount_minor":100,
                 "status":"Draft"},"eventHash":"a"*64}


class B14SignedContracts(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/"signing.raw"
        self.pub=make_keypair(self.path)
        self.event=sign_event(SAMPLE,self.path)
        self.broker=SignedBroker("/tmp/nonexistent",1001,self.pub)
    def tearDown(self):self.tmp.cleanup()
    def test_01_key_is_ed25519_public_32_bytes(self):
        self.assertEqual(len(bytes.fromhex(self.pub)),32)
    def test_02_private_file_is_0600(self):
        self.assertEqual(self.path.stat().st_mode&0o777,0o600)
    def test_03_valid_source_event_signature(self):
        self.assertEqual(verify_event(self.event,self.pub),SAMPLE)
    def test_04_deterministic_event_signature(self):
        self.assertEqual(sign_event(SAMPLE,self.path),self.event)
    def test_05_event_signature_binds_contract_title(self):
        forged=copy.deepcopy(self.event)
        forged["cells"]["title"]="ATTACK"
        with self.assertRaises(SignatureRefused):verify_event(forged,self.pub)
    def test_06_event_signature_binds_sequence(self):
        forged=copy.deepcopy(self.event)
        forged["seq"]=2
        with self.assertRaises(SignatureRefused):verify_event(forged,self.pub)
    def test_07_event_signature_binds_app(self):
        forged=copy.deepcopy(self.event)
        forged["app"]="app-b"
        with self.assertRaises(SignatureRefused):verify_event(forged,self.pub)
    def test_08_event_signature_binds_version(self):
        forged=copy.deepcopy(self.event)
        forged["version"]=2
        with self.assertRaises(SignatureRefused):verify_event(forged,self.pub)
    def test_09_event_signature_binds_event_hash(self):
        forged=copy.deepcopy(self.event)
        forged["eventHash"]="b"*64
        with self.assertRaises(SignatureRefused):verify_event(forged,self.pub)
    def test_10_reject_unknown_key_id(self):
        forged=copy.deepcopy(self.event)
        forged["keyId"]="x"*24
        with self.assertRaises(SignatureRefused):verify_event(forged,self.pub)
    def test_11_reject_other_public_key(self):
        with tempfile.TemporaryDirectory() as t:
            other=make_keypair(Path(t)/"other")
        with self.assertRaises(SignatureRefused):
            verify_event(self.event,other)
    def test_12_reject_missing_signature(self):
        forged=copy.deepcopy(self.event)
        del forged["eventSig"]
        with self.assertRaises(SignatureRefused):verify_event(forged,self.pub)
    def test_13_reject_extra_field(self):
        forged=copy.deepcopy(self.event)
        forged["cmd"]="rm -rf"
        with self.assertRaises(SignatureRefused):verify_event(forged,self.pub)
    def test_14_reject_truncated_signature(self):
        forged=copy.deepcopy(self.event)
        forged["eventSig"]="YQ=="
        with self.assertRaises(SignatureRefused):verify_event(forged,self.pub)
    def test_15_reject_nonbase64_signature(self):
        forged=copy.deepcopy(self.event)
        forged["eventSig"]="!"*88
        with self.assertRaises(SignatureRefused):verify_event(forged,self.pub)
    def test_16_private_key_regeneration_forbidden(self):
        with self.assertRaises(SignatureRefused):make_keypair(self.path)
    def test_17_native_reject_unsigned_apply(self):
        response=self.broker.execute("consumer",1001,{
            "op":"apply","batch":{"app":"app-a","after":0,"events":[SAMPLE]}})
        self.assertFalse(response["ok"])
        self.assertEqual(response["error"],"SIGNED_EVENT_SHAPE_INVALID")
    def test_18_native_reject_forged_hash_valid_event(self):
        forged=copy.deepcopy(self.event)
        forged["cells"]["title"]="ATTACK"
        response=self.broker.execute("consumer",1001,{
            "op":"apply","batch":{"app":"app-a","after":0,"events":[forged]}})
        self.assertEqual(response["error"],"EVENT_SIGNATURE_INVALID")
    def test_19_native_reject_wrong_uid(self):
        response=self.broker.execute("consumer",1002,{"op":"audit"})
        self.assertEqual(response["error"],"PEER_UID_FORBIDDEN")
    def test_20_native_reject_guard_role(self):
        response=self.broker.execute("guard",1001,{"op":"snapshot"})
        self.assertEqual(response["error"],"IPC_ROLE_FORBIDDEN")
    def test_21_native_reject_invalid_batch(self):
        response=self.broker.execute("consumer",1001,{
            "op":"apply","batch":{"app":"app-a","events":[]}})
        self.assertEqual(response["error"],"SIGNED_BATCH_INVALID")
    def test_22_native_valid_signature_still_subject_to_B11_SQL_rules(self):
        response=self.broker.execute("consumer",1001,{
            "op":"apply","batch":{"app":"app-a","after":0,
                                  "events":[self.event]}})
        self.assertFalse(response["ok"])
        self.assertNotIn(response["error"],
                         ("EVENT_SIGNATURE_INVALID","SIGNED_EVENT_SHAPE_INVALID"))
    def test_23_signature_does_not_reveal_private_key(self):
        self.assertEqual(len(self.path.read_bytes()),32)
        self.assertNotIn(self.path.read_bytes().hex(),str(self.event))
    def test_24_native_broker_has_only_pinned_public_key(self):
        self.assertEqual(set(self.broker.__dict__),
                         {"db","consumer_uid","router_uid","lock","public_hex"})


if __name__=="__main__":unittest.main()
