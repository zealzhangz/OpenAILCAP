"""B10 route CAS, release verification and fail-closed policy unit tests.

These are NOT counted as genuine Saltcorn/Chromium behavior; the real three-
UID two-server test is in experiment.py and GitHub Actions.
"""
from __future__ import annotations
import copy
import json
import threading
import unittest
from unittest.mock import patch

from router import (Router,Refused,ROUTE,HASH,CHANGE,canon,
                    fetch_native,query_current_release)


TOKEN="X"*48
ADMIN="A"*48
V1={"version":1,"hash":"1"*64}
V2={"version":2,"hash":"2"*64}
HTML=b"<html><body>HT-2026-000001</body></html>"


class B10RouteContract(unittest.TestCase):
    def setUp(self):
        self.router=Router(33123,TOKEN,ADMIN)
        self.release=patch("router.query_current_release",return_value=V1)
        self.native=patch("router.fetch_native",return_value=HTML)
        self.release_mock=self.release.start()
        self.native_mock=self.native.start()
    def tearDown(self):
        self.release.stop()
        self.native.stop()

    def candidate(self,version=1,sha0=None,port=3140):
        return {"version":version,"manifestHash":sha0 or
                ("1"*64 if version==1 else "2"*64),
                "port":port,"marker":"HT-2026-000001"}

    def change(self,cid="b10unit-first-0001",epoch=0,frm=None,target=1,
               sha0="1"*64):
        return {"changeId":cid,"expectedEpoch":epoch,
                "expectedFromVersion":frm,"targetVersion":target,
                "manifestHash":sha0}

    def rejected(self,fn,status,code):
        with self.assertRaises(Refused) as e:
            fn()
        self.assertEqual((e.exception.status,e.exception.code),
                         (status,code))

    def test_01_invalid_ephemeral_bearer_denied(self):
        with self.assertRaises(ValueError):
            Router(123,"weak","short")

    def test_02_initial_route_is_unavailable(self):
        self.rejected(self.router.capture,503,"NO_ACTIVE_VERSION")

    def test_03_initial_epoch_and_unset_version(self):
        s=self.router.snapshot()
        self.assertEqual((s["epoch"],s["activeVersion"]),(0,None))

    def test_04_public_health_has_no_credentials(self):
        self.assertNotIn(TOKEN,canon(self.router.snapshot()))
        self.assertNotIn(ADMIN,canon(self.router.snapshot()))

    def test_05_admin_bearer_is_required(self):
        self.rejected(lambda:self.router.authorize(""),
                      401,"ADMIN_AUTH_REQUIRED")

    def test_06_invalid_admin_bearer_is_required(self):
        self.rejected(lambda:self.router.authorize("Bearer "+TOKEN),
                      401,"ADMIN_AUTH_REQUIRED")

    def test_07_valid_admin_bearer_accepted(self):
        self.assertIsNone(self.router.authorize("Bearer "+ADMIN))

    def test_08_candidate_exact_shape_required(self):
        self.rejected(lambda:self.router.register({"port":3140}),
                      422,"ARGUMENTS_INVALID")

    def test_09_candidate_invalid_sha_rejected(self):
        body=self.candidate()
        body["manifestHash"]="bad"
        self.rejected(lambda:self.router.register(body),
                      422,"CANDIDATE_INVALID")

    def test_10_publishing_a_cannot_register_b(self):
        self.rejected(lambda:self.router.register(self.candidate(2)),
                      409,"NOT_CURRENT_VERIFIED_RELEASE")

    def test_11_candidate_registered_by_current_source_only(self):
        r=self.router.register(self.candidate())
        self.assertTrue(r["businessReadiness"])
        self.assertEqual(self.router.snapshot()["candidateVersions"],[1])

    def test_12_failing_backend_probe_does_not_register(self):
        self.native_mock.side_effect=Refused(503,"BACKEND_READINESS_FAILED")
        self.rejected(lambda:self.router.register(self.candidate()),
                      503,"BACKEND_READINESS_FAILED")
        self.assertEqual(self.router.snapshot()["candidateVersions"],[])

    def test_13_probe_business_sentinel_is_called(self):
        self.router.register(self.candidate())
        self.native_mock.assert_called_once_with(3140,"HT-2026-000001")

    def test_14_registration_idempotent(self):
        self.router.register(self.candidate())
        self.assertTrue(self.router.register(self.candidate())["alreadyRegistered"])

    def test_15_registered_version_is_immutable(self):
        self.router.register(self.candidate())
        self.rejected(
            lambda:self.router.register(self.candidate(port=3141)),
            409,"VERSION_ALREADY_REGISTERED")

    def test_16_unknown_candidate_never_switched(self):
        self.rejected(lambda:self.router.switch(self.change()),
                      404,"CANDIDATE_NOT_REGISTERED")

    def test_17_switch_uses_B2_verified_release_pointer(self):
        self.router.register(self.candidate())
        self.release_mock.return_value=V2
        self.rejected(lambda:self.router.switch(self.change()),
                      409,"KERNEL_PUBLISH_POINTER_MISMATCH")

    def test_18_successful_switch_increments_epoch(self):
        self.router.register(self.candidate())
        result=self.router.switch(self.change())
        self.assertEqual((result["version"],result["epoch"]),(1,1))

    def test_19_switch_replay_does_not_increment_epoch(self):
        self.router.register(self.candidate())
        self.router.switch(self.change())
        rep=self.router.switch(self.change())
        self.assertTrue(rep["replayed"])
        self.assertEqual(self.router.snapshot()["epoch"],1)

    def test_20_reused_change_id_new_fingerprint_fails(self):
        self.router.register(self.candidate())
        self.router.switch(self.change())
        self.rejected(lambda:self.router.switch(self.change(sha0="2"*64)),
                      409,"CHANGE_ID_REUSED")

    def test_21_stale_route_epoch_fails(self):
        self.router.register(self.candidate())
        self.router.switch(self.change())
        self.rejected(lambda:self.router.switch(
            self.change(cid="b10unit-stale",epoch=0)),
            409,"ROUTE_EPOCH_CONFLICT")

    def test_22_stale_origin_version_fails(self):
        self.router.register(self.candidate())
        self.router.switch(self.change())
        self.rejected(lambda:self.router.switch(
            self.change(cid="b10unit-stale-from",epoch=1,frm=None)),
            409,"ROUTE_EPOCH_CONFLICT")

    def test_23_bad_switch_payload_has_no_side_effect(self):
        self.router.register(self.candidate())
        self.rejected(lambda:self.router.switch({"changeId":"broken"}),
                      422,"ARGUMENTS_INVALID")
        self.assertEqual(self.router.snapshot()["epoch"],0)

    def test_24_candidate_hash_mismatch_cannot_switch(self):
        self.router.register(self.candidate())
        self.rejected(lambda:self.router.switch(self.change(sha0="2"*64)),
                      409,"CANDIDATE_HASH_CONFLICT")

    def test_25_backend_crash_during_switch_keeps_old_route(self):
        self.router.register(self.candidate())
        self.router.switch(self.change())
        self.release_mock.return_value=V2
        self.router.register(self.candidate(2,port=3141))
        self.native_mock.side_effect=Refused(503,"BACKEND_READINESS_FAILED")
        self.rejected(lambda:self.router.switch(
            self.change(cid="b10unit-unready",epoch=1,frm=1,
                        target=2,sha0="2"*64)),
            503,"BACKEND_READINESS_FAILED")
        self.assertEqual(self.router.snapshot()["activeVersion"],1)

    def test_26_fresh_target_registration_after_latest_release(self):
        self.release_mock.return_value=V2
        r=self.router.register(self.candidate(2,port=3141))
        self.assertEqual(r["version"],2)

    def test_27_capture_reference_remains_old_after_switch(self):
        self.router.register(self.candidate())
        self.router.switch(self.change())
        old,epoch=self.router.capture()
        self.release_mock.return_value=V2
        self.router.register(self.candidate(2,port=3141))
        self.router.switch(self.change(
            cid="b10unit-new",epoch=1,frm=1,target=2,sha0="2"*64))
        self.assertEqual((old.version,epoch),(1,1))
        self.assertEqual(self.router.snapshot()["activeVersion"],2)
        self.router.finish()
        self.assertEqual(self.router.snapshot()["inflight"],0)

    def test_28_no_proxy_write_to_b2_via_native_tools(self):
        self.assertEqual(self.router.kernel_token,TOKEN)
        self.assertEqual(self.router.snapshot()["candidateVersions"],[])

    def test_29_negative_invalid_backend_port(self):
        self.rejected(lambda:fetch_native(0,"HT-2026-000001"),
                      422,"BACKEND_PORT_INVALID")

    def test_30_negative_missing_business_marker(self):
        self.rejected(lambda:fetch_native(3141,"none"),
                      422,"MARKER_INVALID")

    def test_31_replayed_epoch_does_not_overwrite_inflight_tuple(self):
        self.router.register(self.candidate())
        self.router.switch(self.change())
        first,epoch=self.router.capture()
        self.router.switch(self.change())
        self.assertEqual((first.version,epoch),(1,1))
        self.router.finish()

    def test_32_two_concurrent_same_change_ids_exactly_once(self):
        self.router.register(self.candidate())
        results=[]
        def change():
            results.append(self.router.switch(self.change()))
        workers=[threading.Thread(target=change) for _ in range(4)]
        for t in workers:t.start()
        for t in workers:t.join()
        self.assertEqual(self.router.snapshot()["epoch"],1)
        self.assertEqual(sum(not x["replayed"] for x in results),1)

    def test_33_current_release_reader_failed_closed(self):
        self.router.register(self.candidate())
        self.release_mock.side_effect=Refused(
            503,"KERNEL_RELEASE_NOT_VERIFIABLE")
        self.rejected(lambda:self.router.switch(self.change()),
                      503,"KERNEL_RELEASE_NOT_VERIFIABLE")

    def test_34_native_route_constant_read_only(self):
        self.assertEqual(ROUTE,"/view/s1_contract_list")


if __name__=="__main__":
    unittest.main()
