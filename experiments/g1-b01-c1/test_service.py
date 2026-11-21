"""Deterministic C1 preflight; NOT the native Saltcorn W01-W24 acceptance suite."""
import json
import multiprocessing
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from service import GateError, Principal, Store, change_from, serve_local


def _race_worker(path, snapshot, change_id, barrier, result_queue):
    service = Store(path)
    agent = Principal("agent", "app-a", "agent")
    barrier.wait(timeout=15)
    try:
        value = service.apply(
            agent, "app-a", change_from(snapshot, change_id, "label", change_id)
        )
        result_queue.put(value["decision"])
    except GateError as exc:
        result_queue.put(exc.code)


class StorePreflight(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.tmp.name) / "c1.sqlite")
        self.store = Store(self.path)
        self.store.initialize()
        self.store.bootstrap_for_test("app-a", "field.title",
                                      {"label": "Initial", "status": "Draft"})
        self.store.bootstrap_for_test("app-b", "field.title",
                                      {"label": "Other App", "status": "Draft"})
        self.human = Principal("human", "app-a", "browser")
        self.agent = Principal("agent", "app-a", "agent")
        self.plugin = Principal("plugin", "app-a", "plugin", resources=("field.title",))
        self.readonly = Principal("reader", "app-a", "read-only", can_write=False)
        self.other_app = Principal("other", "app-b", "browser")

    def tearDown(self):
        self.tmp.cleanup()

    def snap(self, principal=None, app="app-a"):
        return self.store.snapshot(principal or self.human, app, "field.title")

    def patch(self, principal, snapshot, key, value, cid):
        return self.store.apply(
            principal, principal.app_id, change_from(snapshot, cid, key, value)
        )

    def assert_error(self, code, callable_):
        with self.assertRaises(GateError) as cm:
            callable_()
        self.assertEqual(cm.exception.code, code)

    def test_three_actor_sequential_changes_have_one_ledger(self):
        self.patch(self.human, self.snap(), "label", "Human", "change-001")
        self.patch(self.agent, self.snap(), "status", "Agent", "change-002")
        self.patch(self.plugin, self.snap(), "label", "Plugin", "change-003")
        result = self.snap()
        self.assertEqual(result["revision"], 3)
        self.assertEqual(result["content"], {"label": "Plugin", "status": "Agent"})
        metrics = self.store.raw_metrics_for_test("app-a", "field.title")
        self.assertEqual((metrics["receipts"], metrics["audit"]), (3, 3))

    def test_web_before_agent_same_field_rejected(self):
        old = self.snap()
        self.patch(self.human, old, "label", "Human", "change-004")
        self.assert_error(
            "VERSION_CONFLICT",
            lambda: self.patch(self.agent, old, "label", "Lost", "change-005"),
        )
        self.assertEqual(self.snap()["content"]["label"], "Human")

    def test_agent_before_web_same_field_rejected(self):
        old = self.snap()
        self.patch(self.agent, old, "status", "Agent", "change-006")
        self.assert_error(
            "VERSION_CONFLICT",
            lambda: self.patch(self.human, old, "status", "Lost", "change-007"),
        )
        self.assertEqual(self.snap()["content"]["status"], "Agent")

    def test_explicit_refresh_preserves_disjoint_fields(self):
        stale = self.snap()
        self.patch(self.human, stale, "label", "New Name", "change-008")
        self.assert_error(
            "VERSION_CONFLICT",
            lambda: self.patch(self.agent, stale, "status", "Reviewed", "change-009"),
        )
        self.patch(self.agent, self.snap(), "status", "Reviewed", "change-010")
        self.assertEqual(self.snap()["content"],
                         {"label": "New Name", "status": "Reviewed"})

    def test_retry_returns_original_receipt_after_newer_edit(self):
        original = change_from(self.snap(), "change-011", "label", "First")
        first = self.store.apply(self.agent, "app-a", original)
        self.patch(self.human, self.snap(), "label", "Second", "change-012")
        replay = self.store.apply(self.agent, "app-a", original)
        self.assertTrue(replay["replayed"])
        self.assertEqual(replay["revision"], first["revision"])
        self.assertEqual(replay["contentHash"], first["contentHash"])
        self.assertEqual(self.snap()["revision"], 2)
        self.assertEqual(self.store.raw_metrics_for_test("app-a", "field.title")
                         ["audit"], 2)

    def test_reusing_change_id_different_digest_or_actor_fails(self):
        s = self.snap()
        original = change_from(s, "change-013", "label", "First")
        self.store.apply(self.agent, "app-a", original)
        changed = change_from(s, "change-013", "label", "Second")
        self.assert_error("CHANGE_ID_REUSED",
                          lambda: self.store.apply(self.agent, "app-a", changed))
        self.assert_error("CHANGE_ID_REUSED",
                          lambda: self.store.apply(self.plugin, "app-a", original))

    def test_mid_transaction_failure_rolls_back_all_resources_receipts(self):
        original = self.snap()
        with self.assertRaisesRegex(RuntimeError, "TEST_INJECTED_FAILURE"):
            self.store.apply(
                self.agent, "app-a",
                change_from(original, "change-014", "status", "ShouldRollback"),
                inject_fault=True,
            )
        after = self.snap()
        self.assertEqual(after, original)
        metrics = self.store.raw_metrics_for_test("app-a", "field.title")
        self.assertEqual((metrics["audit"], metrics["receipts"]), (0, 0))

    def test_out_of_band_change_is_quarantined_without_revision_advance(self):
        with sqlite3.connect(self.path) as db:
            db.execute(
                "UPDATE resources SET doc=? WHERE app_id=? AND resource_id=?",
                ('{"label":"Outside","status":"Draft"}', "app-a", "field.title"),
            )
        self.assert_error("OUT_OF_BAND_DRIFT", lambda: self.snap())
        self.assert_error(
            "RESOURCE_QUARANTINED",
            lambda: self.store.apply(
                self.agent, "app-a",
                {"changeId": "change-015", "resourceId": "field.title",
                 "expectedRevision": 0, "baseContentHash": "0" * 64,
                 "operations": [{"op": "replace", "path": "/label",
                                 "value": "Never"}]},
            ),
        )
        metrics = self.store.raw_metrics_for_test("app-a", "field.title")
        self.assertEqual(metrics["state"], "QUARANTINED")
        self.assertEqual((metrics["revision"], metrics["audit"]), (0, 0))

    def test_spoofed_actor_role_tenant_inputs_rejected(self):
        change = change_from(self.snap(), "change-016", "label", "Nope")
        for extra in (("actorId", "admin"), ("role", "owner"),
                      ("tenantId", "app-b")):
            attack = {**change, extra[0]: extra[1]}
            self.assert_error(
                "INVALID_CHANGE",
                lambda attack=attack: self.store.apply(self.agent, "app-a", attack),
            )
        self.assertEqual(self.snap()["revision"], 0)

    def test_app_and_readonly_boundary(self):
        snapshot = self.snap()
        change = change_from(snapshot, "change-017", "label", "Nope")
        self.assert_error("FORBIDDEN",
                          lambda: self.store.apply(self.other_app, "app-a", change))
        self.assert_error("READ_ONLY",
                          lambda: self.store.apply(self.readonly, "app-a", change))
        self.assertEqual(self.snap()["revision"], 0)
        self.assertEqual(self.snap(self.other_app, "app-b")["revision"], 0)

    def test_unknown_change_and_forged_resource_not_accepted(self):
        attack = change_from(self.snap(), "change-018", "label", "Nope")
        attack["operations"][0]["path"] = "/__proto__"
        self.assert_error("INVALID_CHANGE",
                          lambda: self.store.apply(self.agent, "app-a", attack))
        attack["operations"][0]["path"] = "/label"
        attack["resourceId"] = "other.resource"
        self.assert_error("RESOURCE_NOT_FOUND",
                          lambda: self.store.apply(self.agent, "app-a", attack))

    def test_independent_process_cas_one_wins_one_conflicts(self):
        initial = self.snap()
        ctx = multiprocessing.get_context("spawn")
        barrier = ctx.Barrier(2)
        queue = ctx.Queue()
        workers = [
            ctx.Process(target=_race_worker,
                        args=(self.path, initial, f"race-{n:04}", barrier, queue))
            for n in range(2)
        ]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(20)
        try:
            self.assertTrue(all(p.exitcode == 0 for p in workers))
            outcomes = sorted(queue.get(timeout=5) for _ in range(2))
            self.assertEqual(outcomes, ["APPLIED", "VERSION_CONFLICT"])
            self.assertEqual(self.snap()["revision"], 1)
            self.assertEqual(self.store.raw_metrics_for_test("app-a", "field.title")
                             ["audit"], 1)
        finally:
            for worker in workers:
                if worker.is_alive():
                    worker.terminate()
                    worker.join(5)

    def test_human_edit_without_any_model_dependency(self):
        result = self.patch(self.human, self.snap(), "label", "Manual", "change-019")
        self.assertEqual(result["decision"], "APPLIED")
        self.assertEqual(self.snap()["content"]["label"], "Manual")


class HttpPreflight(StorePreflight):
    """Test HTTP adapter with fixture-issued sessions/tokens, not native Saltcorn auth."""

    def setUp(self):
        super().setUp()
        self.server = serve_local(
            self.store,
            {"token-agent": self.agent, "token-plugin": self.plugin,
             "token-reader": self.readonly},
            {"session-human": (self.human, "csrf-secret")},
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        super().tearDown()

    def call(self, method, path, *, token=None, cookie=None, csrf=None, payload=None):
        headers = {}
        if token is not None:
            headers["Authorization"] = "Bearer " + token
        if cookie is not None:
            headers["Cookie"] = "sid=" + cookie
        if csrf is not None:
            headers["X-CSRF-Token"] = csrf
        data = None
        if payload is not None:
            data = json.dumps(payload).encode()
            headers["Content-Type"] = "application/json"
        req = Request(self.base + path, method=method, data=data, headers=headers)
        try:
            with urlopen(req, timeout=10) as response:
                return response.status, json.load(response)
        except HTTPError as exc:
            return exc.code, json.loads(exc.read())

    def test_http_three_actor_shared_mutation_and_readback(self):
        path = "/v1/apps/app-a/resources/field.title"
        write = "/v1/apps/app-a/changes"
        status, snapshot = self.call("GET", path, cookie="session-human")
        self.assertEqual(status, 200)
        status, _ = self.call("POST", write, cookie="session-human",
                              csrf="csrf-secret",
                              payload=change_from(snapshot, "http-001", "label", "Human"))
        self.assertEqual(status, 200)
        status, snapshot = self.call("GET", path, token="token-agent")
        self.assertEqual(status, 200)
        status, _ = self.call("POST", write, token="token-agent",
                              payload=change_from(snapshot, "http-002", "status", "AI"))
        self.assertEqual(status, 200)
        status, snapshot = self.call("GET", path, token="token-plugin")
        self.assertEqual(status, 200)
        status, _ = self.call("POST", write, token="token-plugin",
                              payload=change_from(snapshot, "http-003", "label", "Plugin"))
        self.assertEqual(status, 200)
        status, final = self.call("GET", path, cookie="session-human")
        self.assertEqual(status, 200)
        self.assertEqual(final["content"], {"label": "Plugin", "status": "AI"})
        self.assertEqual(final["revision"], 3)

    def test_http_web_stale_form_rejected_with_409(self):
        path = "/v1/apps/app-a/resources/field.title"
        write = "/v1/apps/app-a/changes"
        _, old = self.call("GET", path, cookie="session-human")
        first = change_from(old, "http-004", "label", "B")
        second = change_from(old, "http-005", "label", "A-STALE")
        self.assertEqual(self.call("POST", write, cookie="session-human",
                                   csrf="csrf-secret", payload=first)[0], 200)
        status, body = self.call("POST", write, cookie="session-human",
                                 csrf="csrf-secret", payload=second)
        self.assertEqual((status, body["error"]), (409, "VERSION_CONFLICT"))
        self.assertEqual(self.snap()["content"]["label"], "B")

    def test_http_csrf_expired_token_and_readonly_deny(self):
        path = "/v1/apps/app-a/changes"
        change = change_from(self.snap(), "http-006", "label", "Nope")
        status, body = self.call("POST", path, cookie="session-human", payload=change)
        self.assertEqual((status, body["error"]), (403, "CSRF_REQUIRED"))
        status, body = self.call("POST", path, token="expired-token", payload=change)
        self.assertEqual((status, body["error"]), (401, "AUTH_REQUIRED"))
        status, body = self.call("POST", path, token="token-reader", payload=change)
        self.assertEqual((status, body["error"]), (403, "READ_ONLY"))
        status, body = self.call("POST", path, token="token-agent",
                                 payload={**change, "role": "admin"})
        self.assertEqual((status, body["error"]), (422, "INVALID_CHANGE"))
        self.assertEqual(self.snap()["revision"], 0)

    def test_http_drift_failclosed_for_agent(self):
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE resources SET doc=? WHERE app_id='app-a' "
                       "AND resource_id='field.title'",
                       ('{"label":"Outside","status":"Draft"}',))
        status, body = self.call("GET",
                                 "/v1/apps/app-a/resources/field.title",
                                 token="token-agent")
        self.assertEqual((status, body["error"]), (409, "OUT_OF_BAND_DRIFT"))
        self.assertEqual(self.store.raw_metrics_for_test("app-a", "field.title")
                         ["state"], "QUARANTINED")


if __name__ == "__main__":
    unittest.main()
