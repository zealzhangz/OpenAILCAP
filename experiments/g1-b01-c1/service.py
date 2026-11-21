"""G1-B01 C1 research service: one SQLite transactional mutation path for test principals.

NOT a Saltcorn plugin, production auth service, or completed W01-W24 acceptance.
Only Python standard library is required.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlsplit


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


class GateError(Exception):
    def __init__(self, status, code):
        super().__init__(code)
        self.status = status
        self.code = code


@dataclass(frozen=True)
class Principal:
    name: str
    app_id: str
    role: str
    can_write: bool = True
    resources: tuple[str, ...] = ("*",)
    active: bool = True
    fields: tuple[str, ...] = ("*",)  # permission enforced server-side, not only manifest


class Store:
    """Authority for revisions, resource data, receipts and audit on one SQLite DB."""

    def __init__(self, path):
        self.path = str(path)

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout = 10000")
        db.execute("PRAGMA foreign_keys = ON")
        return db

    def initialize(self):
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
            CREATE TABLE IF NOT EXISTS resources (
                app_id TEXT NOT NULL, resource_id TEXT NOT NULL,
                revision INTEGER NOT NULL, doc TEXT NOT NULL,
                content_hash TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'ACTIVE',
                PRIMARY KEY (app_id, resource_id)
            );
            CREATE TABLE IF NOT EXISTS receipts (
                app_id TEXT NOT NULL, change_id TEXT NOT NULL,
                principal TEXT NOT NULL, request_digest TEXT NOT NULL,
                response TEXT NOT NULL,
                PRIMARY KEY (app_id, change_id)
            );
            CREATE TABLE IF NOT EXISTS audit (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_id TEXT NOT NULL, resource_id TEXT NOT NULL,
                principal TEXT NOT NULL, change_id TEXT NOT NULL,
                old_revision INTEGER NOT NULL, new_revision INTEGER NOT NULL
            );
            """)

    def bootstrap_for_test(self, app_id, resource_id, doc):
        """Fixture setup only. Not exposed by the HTTP service."""
        if set(doc) != {"label", "status"}:
            raise ValueError("fixture requires label and status")
        with self._connect() as db:
            db.execute("INSERT INTO resources VALUES (?,?,?,?,?,?)",
                       (app_id, resource_id, 0, canonical(doc), digest(doc), "ACTIVE"))

    @staticmethod
    def authorize(principal, app_id, resource_id, write=False):
        if not principal or not principal.active:
            raise GateError(401, "AUTH_REQUIRED")
        if principal.app_id != app_id or (
            "*" not in principal.resources and resource_id not in principal.resources
        ):
            raise GateError(403, "FORBIDDEN")
        if write and not principal.can_write:
            raise GateError(403, "READ_ONLY")

    @staticmethod
    def _load(db, app_id, resource_id):
        row = db.execute(
            "SELECT * FROM resources WHERE app_id=? AND resource_id=?",
            (app_id, resource_id),
        ).fetchone()
        if row is None:
            raise GateError(404, "RESOURCE_NOT_FOUND")
        if row["state"] != "ACTIVE":
            raise GateError(423, "RESOURCE_QUARANTINED")
        doc = json.loads(row["doc"])
        if digest(doc) != row["content_hash"]:
            db.execute(
                "UPDATE resources SET state='QUARANTINED' "
                "WHERE app_id=? AND resource_id=?",
                (app_id, resource_id),
            )
            db.commit()  # persist quarantine independently of a rejected mutation
            raise GateError(409, "OUT_OF_BAND_DRIFT")
        return row, doc

    def snapshot(self, principal, app_id, resource_id):
        self.authorize(principal, app_id, resource_id)
        db = self._connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            row, doc = self._load(db, app_id, resource_id)
            value = {"applicationId": app_id, "resourceId": resource_id,
                     "revision": row["revision"], "contentHash": row["content_hash"],
                     "content": doc, "state": row["state"]}
            db.commit()
            return value
        except BaseException:
            if db.in_transaction:
                db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _validate(change):
        if not isinstance(change, dict) or set(change) != {
            "changeId", "resourceId", "expectedRevision", "baseContentHash", "operations"
        }:
            raise GateError(422, "INVALID_CHANGE")
        if not isinstance(change["changeId"], str) or not re.fullmatch(
            r"[A-Za-z0-9_-]{4,96}", change["changeId"]
        ):
            raise GateError(422, "INVALID_CHANGE")
        if not isinstance(change["resourceId"], str) or len(change["resourceId"]) > 128:
            raise GateError(422, "INVALID_CHANGE")
        if type(change["expectedRevision"]) is not int or change["expectedRevision"] < 0:
            raise GateError(422, "INVALID_CHANGE")
        if not isinstance(change["baseContentHash"], str) or not re.fullmatch(
            r"[0-9a-f]{64}", change["baseContentHash"]
        ):
            raise GateError(422, "INVALID_CHANGE")
        ops = change["operations"]
        if not isinstance(ops, list) or len(ops) != 1 or not isinstance(ops[0], dict):
            raise GateError(422, "INVALID_CHANGE")
        op = ops[0]
        if set(op) != {"op", "path", "value"} or op["op"] != "replace":
            raise GateError(422, "INVALID_CHANGE")
        if op["path"] not in ("/label", "/status") or (
            not isinstance(op["value"], str) or not 1 <= len(op["value"]) <= 120
        ):
            raise GateError(422, "INVALID_CHANGE")

    def apply(self, principal, app_id, change, *, inject_fault=False):
        self._validate(change)
        resource_id = change["resourceId"]
        self.authorize(principal, app_id, resource_id, write=True)
        target_field = change["operations"][0]["path"][1:]
        if "*" not in principal.fields and target_field not in principal.fields:
            raise GateError(403, "FIELD_FORBIDDEN")
        request_digest = digest(change)
        db = self._connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute(
                "SELECT * FROM receipts WHERE app_id=? AND change_id=?",
                (app_id, change["changeId"]),
            ).fetchone()
            if previous:
                if (previous["principal"] != principal.name or
                        previous["request_digest"] != request_digest):
                    raise GateError(409, "CHANGE_ID_REUSED")
                response = json.loads(previous["response"])
                db.commit()
                return {**response, "replayed": True}
            row, doc = self._load(db, app_id, resource_id)
            if (row["revision"] != change["expectedRevision"] or
                    row["content_hash"] != change["baseContentHash"]):
                raise GateError(409, "VERSION_CONFLICT")
            key = change["operations"][0]["path"][1:]
            doc[key] = change["operations"][0]["value"]
            new_revision = row["revision"] + 1
            new_hash = digest(doc)
            result = db.execute(
                "UPDATE resources SET doc=?, revision=?, content_hash=? "
                "WHERE app_id=? AND resource_id=? AND revision=? AND content_hash=?",
                (canonical(doc), new_revision, new_hash, app_id, resource_id,
                 row["revision"], row["content_hash"]),
            )
            if result.rowcount != 1:
                raise GateError(409, "VERSION_CONFLICT")
            if inject_fault:
                raise RuntimeError("TEST_INJECTED_FAILURE")
            response = {"decision": "APPLIED", "resourceId": resource_id,
                        "previousRevision": row["revision"], "revision": new_revision,
                        "contentHash": new_hash, "changeId": change["changeId"]}
            db.execute(
                "INSERT INTO receipts VALUES (?,?,?,?,?)",
                (app_id, change["changeId"], principal.name,
                 request_digest, canonical(response)),
            )
            db.execute(
                "INSERT INTO audit (app_id,resource_id,principal,change_id,"
                "old_revision,new_revision) VALUES (?,?,?,?,?,?)",
                (app_id, resource_id, principal.name, change["changeId"],
                 row["revision"], new_revision),
            )
            db.commit()
            return {**response, "replayed": False}
        except BaseException:
            if db.in_transaction:
                db.rollback()
            raise
        finally:
            db.close()

    def raw_metrics_for_test(self, app_id, resource_id):
        with self._connect() as db:
            row = db.execute(
                "SELECT revision, doc, state FROM resources "
                "WHERE app_id=? AND resource_id=?",
                (app_id, resource_id),
            ).fetchone()
            receipts = db.execute(
                "SELECT COUNT(*) FROM receipts WHERE app_id=?", (app_id,)
            ).fetchone()[0]
            audit = db.execute(
                "SELECT COUNT(*) FROM audit WHERE app_id=?", (app_id,)
            ).fetchone()[0]
            return {"revision": row["revision"], "doc": json.loads(row["doc"]),
                    "state": row["state"], "receipts": receipts, "audit": audit}


def change_from(snapshot, change_id, field, value):
    return {"changeId": change_id, "resourceId": snapshot["resourceId"],
            "expectedRevision": snapshot["revision"],
            "baseContentHash": snapshot["contentHash"],
            "operations": [{"op": "replace", "path": "/" + field, "value": value}]}


def make_handler(store, bearer_tokens, browser_sessions):
    """Test HTTP edge. Principals are resolved from host-side fixtures, never JSON."""

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass  # avoid recording fixture credentials to CI logs

        def _reply(self, code, obj):
            body = canonical(obj).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _principal(self, write):
            auth = self.headers.get("Authorization", "")
            if auth.startswith("Bearer "):
                result = bearer_tokens.get(auth[7:])
                if result is None or not result.active:
                    raise GateError(401, "AUTH_REQUIRED")
                return result
            cookies = self.headers.get("Cookie", "")
            pair = dict(part.strip().split("=", 1) for part in cookies.split(";")
                        if "=" in part)
            entry = browser_sessions.get(pair.get("sid", ""))
            if entry is None:
                raise GateError(401, "AUTH_REQUIRED")
            principal, csrf = entry
            if not principal.active:
                raise GateError(401, "AUTH_REQUIRED")
            if write and self.headers.get("X-CSRF-Token") != csrf:
                raise GateError(403, "CSRF_REQUIRED")
            return principal

        def _route(self, write):
            parts = [unquote(p) for p in urlsplit(self.path).path.split("/") if p]
            if write and len(parts) == 4 and parts[:2] == ["v1", "apps"] and parts[3] == "changes":
                return parts[2], None
            if not write and len(parts) == 5 and parts[:2] == ["v1", "apps"] and parts[3] == "resources":
                return parts[2], parts[4]
            raise GateError(404, "ROUTE_NOT_FOUND")

        def do_GET(self):
            if self.path == "/health":
                self._reply(200, {"status": "OK", "scope": "C1_RESEARCH_ONLY"})
                return
            try:
                app_id, resource_id = self._route(write=False)
                principal = self._principal(write=False)
                self._reply(200, store.snapshot(principal, app_id, resource_id))
            except GateError as exc:
                self._reply(exc.status, {"error": exc.code})

        def do_POST(self):
            try:
                app_id, _ = self._route(write=True)
                principal = self._principal(write=True)
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 16384:
                    raise GateError(422, "INVALID_CHANGE")
                try:
                    change = json.loads(self.rfile.read(length))
                except (ValueError, UnicodeDecodeError):
                    raise GateError(422, "INVALID_CHANGE")
                self._reply(200, store.apply(principal, app_id, change))
            except GateError as exc:
                self._reply(exc.status, {"error": exc.code})

    return Handler


def serve_local(store, bearer_tokens, browser_sessions, port=0):
    """Callers own server.shutdown(); binding to loopback only."""
    return ThreadingHTTPServer(
        ("127.0.0.1", port), make_handler(store, bearer_tokens, browser_sessions)
    )
