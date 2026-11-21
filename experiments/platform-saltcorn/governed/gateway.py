#!/usr/bin/env python3
"""OpenAILCAP S1 research gateway for ONE Saltcorn metadata resource family.

LAB ONLY: connects directly to Saltcorn SQLite _sc_fields to test a governed
HTTP write contract. No claim of integration with Saltcorn native editor,
cache invalidation, multi-node deployment, or production security.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import html
import json
import os
import re
import secrets
import sqlite3
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

APP = "s1-contract"
RESOURCES = {"title", "status"}
HUMAN = "s1-human@example.invalid"
CHANGE_ID = re.compile(r"^[a-zA-Z0-9_-]{8,64}$")


def fingerprint(resource: str, label: str) -> str:
    data = json.dumps({"app": APP, "resource": resource, "label": label},
                      sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(data).hexdigest()


class Rejected(Exception):
    def __init__(self, status: int, code: str):
        self.status = status
        self.code = code
        super().__init__(code)


class Storage:
    def __init__(self, path: str):
        self.path = path
        self.bootstrap()

    def connect(self):
        conn = sqlite3.connect(self.path, timeout=20, isolation_level=None)
        conn.execute("PRAGMA busy_timeout=20000")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    @staticmethod
    def native_field(conn, resource):
        row = conn.execute(
            "SELECT f.id,f.label FROM _sc_fields f JOIN _sc_tables t "
            "ON t.id=f.table_id WHERE t.name='s1_contracts' AND f.name=?",
            (resource,)).fetchone()
        if row is None:
            raise Rejected(404, "RESOURCE_NOT_FOUND")
        return row

    def bootstrap(self):
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS _openailcap_s1_http_guard("
                "app_id TEXT NOT NULL, resource_id TEXT NOT NULL,"
                "revision INTEGER NOT NULL, fingerprint TEXT NOT NULL,"
                "PRIMARY KEY(app_id,resource_id))"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS _openailcap_s1_http_changes("
                "change_id TEXT PRIMARY KEY, request_hash TEXT NOT NULL,"
                "resource_id TEXT NOT NULL, receipt TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS _openailcap_s1_http_audit("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, actor TEXT NOT NULL,"
                "resource_id TEXT NOT NULL, outcome TEXT NOT NULL,"
                "change_id TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)"
            )
            for resource in sorted(RESOURCES):
                _, label = self.native_field(conn, resource)
                conn.execute(
                    "INSERT OR IGNORE INTO _openailcap_s1_http_guard"
                    "(app_id,resource_id,revision,fingerprint) VALUES (?,?,0,?)",
                    (APP, resource, fingerprint(resource, label)),
                )
            conn.execute("COMMIT")

    def audit(self, actor, resource, outcome, change_id=None):
        with self.connect() as conn:
            conn.execute("INSERT INTO _openailcap_s1_http_audit"
                         "(actor,resource_id,outcome,change_id) VALUES(?,?,?,?)",
                         (actor, resource, outcome, change_id))

    def read(self, resource):
        with self.connect() as conn:
            _, label = self.native_field(conn, resource)
            state = conn.execute(
                "SELECT revision,fingerprint FROM _openailcap_s1_http_guard "
                "WHERE app_id=? AND resource_id=?", (APP, resource)).fetchone()
            if state is None:
                raise Rejected(404, "RESOURCE_NOT_FOUND")
            if fingerprint(resource, label) != state[1]:
                raise Rejected(409, "OUT_OF_BAND_DRIFT")
            return {"app_id": APP, "resource_id": resource, "label": label,
                    "revision": state[0], "fingerprint": state[1]}

    def update(self, actor, resource, base_revision, base_fp, label, change_id,
               failure_after_write=False):
        if not isinstance(label, str) or not 1 <= len(label) <= 100 or "\x00" in label:
            raise Rejected(422, "INVALID_LABEL")
        if not isinstance(base_revision, int) or isinstance(base_revision, bool) or base_revision < 0:
            raise Rejected(422, "INVALID_REVISION")
        if not isinstance(base_fp, str) or not re.fullmatch(r"[a-f0-9]{64}", base_fp):
            raise Rejected(422, "INVALID_FINGERPRINT")
        if not isinstance(change_id, str) or not CHANGE_ID.fullmatch(change_id):
            raise Rejected(422, "INVALID_CHANGE_ID")
        payload = json.dumps(
            {"actor": actor, "resource": resource, "base": base_revision,
             "base_fp": base_fp, "label": label},
            sort_keys=True, separators=(",", ":")).encode()
        request_hash = hashlib.sha256(payload).hexdigest()
        try:
            with self.connect() as conn:
                conn.execute("BEGIN IMMEDIATE")
                field_id, actual_label = self.native_field(conn, resource)
                state = conn.execute(
                    "SELECT revision,fingerprint FROM _openailcap_s1_http_guard "
                    "WHERE app_id=? AND resource_id=?", (APP, resource)).fetchone()
                if state is None or fingerprint(resource, actual_label) != state[1]:
                    raise Rejected(409, "OUT_OF_BAND_DRIFT")
                prev = conn.execute(
                    "SELECT request_hash,resource_id,receipt "
                    "FROM _openailcap_s1_http_changes WHERE change_id=?",
                    (change_id,)).fetchone()
                if prev:
                    if prev[0] != request_hash or prev[1] != resource:
                        raise Rejected(409, "CHANGE_ID_REUSED")
                    receipt = json.loads(prev[2])
                    if state[0] != receipt["revision"] or state[1] != receipt["fingerprint"]:
                        raise Rejected(409, "STALE_REPLAY")
                    conn.execute("COMMIT")
                    return {**receipt, "replayed": True}
                if state[0] != base_revision or state[1] != base_fp:
                    raise Rejected(409, "VERSION_CONFLICT")
                new_fp = fingerprint(resource, label)
                changed = conn.execute(
                    "UPDATE _sc_fields SET label=? WHERE id=?", (label, field_id)
                ).rowcount
                if changed != 1:
                    raise RuntimeError("NATIVE_WRITE_MISSING")
                if failure_after_write:
                    raise RuntimeError("INJECTED_FAILURE_AFTER_NATIVE_SQL_WRITE")
                changed = conn.execute(
                    "UPDATE _openailcap_s1_http_guard SET revision=?,fingerprint=? "
                    "WHERE app_id=? AND resource_id=? AND revision=? AND fingerprint=?",
                    (base_revision + 1, new_fp, APP, resource, base_revision, base_fp)
                ).rowcount
                if changed != 1:
                    raise RuntimeError("LEDGER_WRITE_MISSING")
                receipt = {"app_id": APP, "resource_id": resource, "revision": base_revision + 1,
                           "fingerprint": new_fp, "label": label}
                conn.execute(
                    "INSERT INTO _openailcap_s1_http_changes"
                    "(change_id,request_hash,resource_id,receipt) VALUES(?,?,?,?)",
                    (change_id, request_hash, resource, json.dumps(receipt, sort_keys=True)),
                )
                conn.execute(
                    "INSERT INTO _openailcap_s1_http_audit"
                    "(actor,resource_id,outcome,change_id) VALUES (?,?,?,?)",
                    (actor, resource, "APPLIED", change_id),
                )
                conn.execute("COMMIT")
                return {**receipt, "replayed": False}
        except sqlite3.Error:
            raise Rejected(503, "DATABASE_ERROR")
        except RuntimeError as exc:
            if str(exc) == "INJECTED_FAILURE_AFTER_NATIVE_SQL_WRITE":
                raise Rejected(500, "INJECTED_ROLLBACK")
            raise Rejected(500, "TRANSACTION_FAILED")


class Server(ThreadingHTTPServer):
    allow_reuse_address = True
    def __init__(self, addr, db, password, agent_token, read_token, test_mode):
        super().__init__(addr, Handler)
        self.store = Storage(db)
        self.password = password
        self.agent_token = agent_token
        self.read_token = read_token
        self.test_mode = test_mode
        self.sessions = {}


class Handler(BaseHTTPRequestHandler):
    server: Server

    def log_message(self, fmt, *args):
        # Never print raw Authorization, session cookies, body, or CSRF token.
        print(json.dumps({"event": "http", "method": self.command,
                          "path": urlsplit(self.path).path,
                          "status_line": fmt % args}), flush=True)

    def json_response(self, status, payload):
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def html_response(self, status, body, cookie=None):
        raw = ("<!doctype html><html lang='en'><meta charset='utf-8'>"
               "<title>OpenAILCAP S1 Governed Editor</title>"
               "<body>" + body + "</body></html>").encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'none'; form-action 'self'; base-uri 'none'")
        self.send_header("X-Content-Type-Options", "nosniff")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def redirect(self, dest):
        self.send_response(303)
        self.send_header("Location", dest)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def form(self):
        length = int(self.headers.get("Content-Length", "0"))
        if not 0 < length <= 16000:
            raise Rejected(413, "INVALID_BODY_SIZE")
        if "application/x-www-form-urlencoded" not in self.headers.get("Content-Type", ""):
            raise Rejected(415, "INVALID_CONTENT_TYPE")
        return {k: v[-1] for k, v in parse_qs(
            self.rfile.read(length).decode("utf-8"), keep_blank_values=True).items()}

    def json_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        if not 0 < length <= 16000:
            raise Rejected(413, "INVALID_BODY_SIZE")
        if "application/json" not in self.headers.get("Content-Type", ""):
            raise Rejected(415, "INVALID_CONTENT_TYPE")
        try:
            data = json.loads(self.rfile.read(length))
        except (ValueError, UnicodeError):
            raise Rejected(400, "INVALID_JSON")
        if not isinstance(data, dict):
            raise Rejected(400, "INVALID_JSON")
        return data

    def session(self):
        raw = self.headers.get("Cookie", "")
        cookies = SimpleCookie()
        try:
            cookies.load(raw)
        except Exception:
            return None
        value = cookies.get("s1_session")
        return self.server.sessions.get(value.value) if value else None

    def bearer(self, allow_read_only=True):
        header = self.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            raise Rejected(401, "AUTH_REQUIRED")
        token = header[7:]
        if hmac.compare_digest(token, self.server.agent_token):
            return "agent"
        if hmac.compare_digest(token, self.server.read_token):
            if allow_read_only:
                return "readonly"
            raise Rejected(403, "READ_ONLY")
        raise Rejected(401, "AUTH_REQUIRED")

    @staticmethod
    def resource(parts):
        if len(parts) != 5 or parts[0:2] != ["api", "apps"] or parts[3] != "resources":
            raise Rejected(404, "NOT_FOUND")
        if parts[2] != APP:
            raise Rejected(403, "APP_FORBIDDEN")
        if parts[4] not in RESOURCES:
            raise Rejected(404, "RESOURCE_NOT_FOUND")
        return parts[4]

    def do_GET(self):
        try:
            path = urlsplit(self.path).path
            parts = [p for p in path.split("/") if p]
            if path == "/health":
                return self.json_response(200, {"status": "OK", "scope": "LAB_ONLY"})
            if path == "/login":
                return self.html_response(200,
                    "<h1>Research Login</h1><form method='post' action='/login'>"
                    "<input name='email' type='email' value='s1-human@example.invalid'>"
                    "<input name='password' type='password'>"
                    "<button type='submit'>Log in</button></form>")
            if len(parts) == 2 and parts[0] == "edit" and parts[1] in RESOURCES:
                session = self.session()
                if not session:
                    return self.redirect("/login")
                resource = parts[1]
                state = self.server.store.read(resource)
                return self.html_response(200, 
                    f"<h1>Governed research editor: {html.escape(resource)}</h1>"
                    f"<div id='revision'>Revision {state['revision']}</div>"
                    f"<form method='post' action='/edit/{resource}'>"
                    f"<input name='label' value='{html.escape(state['label'], quote=True)}'>"
                    f"<input type='hidden' name='base_revision' value='{state['revision']}'>"
                    f"<input type='hidden' name='base_fingerprint' value='{state['fingerprint']}'>"
                    f"<input type='hidden' name='change_id' value='{secrets.token_hex(16)}'>"
                    f"<input type='hidden' name='csrf' value='{session['csrf']}'>"
                    "<button type='submit'>Save</button></form>")
            if len(parts) == 5 and parts[:2] == ["api", "apps"]:
                self.bearer()
                resource = self.resource(parts)
                return self.json_response(200, self.server.store.read(resource))
            raise Rejected(404, "NOT_FOUND")
        except Rejected as e:
            self.json_response(e.status, {"error": e.code})
        except Exception:
            self.json_response(500, {"error": "INTERNAL_ERROR"})

    def do_POST(self):
        actor = "unauthenticated"
        resource = "unknown"
        change_id = None
        try:
            path = urlsplit(self.path).path
            parts = [p for p in path.split("/") if p]
            if path == "/login":
                data = self.form()
                ok = (data.get("email") == HUMAN and
                      hmac.compare_digest(data.get("password", ""), self.server.password))
                if not ok:
                    raise Rejected(401, "LOGIN_FAILED")
                token = secrets.token_urlsafe(32)
                self.server.sessions[token] = {"user": HUMAN, "csrf": secrets.token_urlsafe(24)}
                self.send_response(303)
                self.send_header("Location", "/edit/title")
                self.send_header("Set-Cookie",
                    "s1_session="+token+"; HttpOnly; SameSite=Strict; Path=/")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            if len(parts) == 2 and parts[0] == "edit" and parts[1] in RESOURCES:
                resource = parts[1]
                session = self.session()
                if not session:
                    raise Rejected(401, "AUTH_REQUIRED")
                actor = "human"
                data = self.form()
                if not hmac.compare_digest(data.get("csrf", ""), session["csrf"]):
                    raise Rejected(403, "CSRF_REQUIRED")
                change_id = data.get("change_id")
                try:
                    revision = int(data.get("base_revision", "invalid"))
                except ValueError:
                    raise Rejected(422, "INVALID_REVISION")
                receipt = self.server.store.update(
                    actor, resource, revision, data.get("base_fingerprint"),
                    data.get("label"), change_id)
                return self.html_response(200,
                    f"<h1>SAVED</h1><div id='saved_revision'>{receipt['revision']}</div>"
                    f"<a href='/edit/{resource}'>Edit again</a>")
            if len(parts) == 5 and parts[:2] == ["api", "apps"]:
                actor = self.bearer(allow_read_only=False)
                resource = self.resource(parts)
                data = self.json_body()
                change_id = data.get("change_id")
                receipt = self.server.store.update(
                    actor, resource, data.get("base_revision"), data.get("base_fingerprint"),
                    data.get("label"), change_id,
                    failure_after_write=(self.server.test_mode and
                        self.headers.get("X-S1-Inject-Failure") == "after-write"))
                return self.json_response(200, receipt)
            raise Rejected(404, "NOT_FOUND")
        except Rejected as e:
            if resource != "unknown":
                try:
                    self.server.store.audit(actor, resource, e.code, change_id)
                except Exception:
                    pass
            return self.json_response(e.status, {"error": e.code})
        except Exception:
            return self.json_response(500, {"error": "INTERNAL_ERROR"})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--port", type=int, default=3200)
    opts = ap.parse_args()
    secrets_env = ("S1_HUMAN_PASSWORD", "S1_AGENT_TOKEN", "S1_READ_TOKEN")
    if any(not os.getenv(key) or len(os.getenv(key, "")) < 20 for key in secrets_env):
        raise SystemExit("Missing or short lab credentials")
    if not Path(opts.db).is_file():
        raise SystemExit("Existing real Saltcorn SQLite fixture required")
    server = Server(("127.0.0.1", opts.port), opts.db,
                    os.environ["S1_HUMAN_PASSWORD"], os.environ["S1_AGENT_TOKEN"],
                    os.environ["S1_READ_TOKEN"], os.getenv("S1_TEST_MODE") == "1")
    print(json.dumps({"status": "READY", "port": opts.port,
                      "scope": "localhost-research-only"}), flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
