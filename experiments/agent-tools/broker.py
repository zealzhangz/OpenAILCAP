"""S1 RESEARCH ONLY: typed, scoped agent tool broker over real Saltcorn REST.

Not a production Agent, OAuth delegation, multi-app isolation or LLM.
Trusted orchestrator, not the LLM, creates actor-bound sessions and one-use
human grants. Never hand credentials, cookies, CSRF or grants to a model.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import re
import secrets
import sqlite3
import time
from pathlib import Path

APP_ID = "s1-contract"
IDENTITIES = {
    "s1-creator@example.invalid": "creator",
    "s1-approver1@example.invalid": "approver1",
    "s1-approver2@example.invalid": "approver2",
    "s1-viewer@example.invalid": "viewer",
}
NUMBER = re.compile(r"^S1-AGENT-[A-Z0-9-]{1,35}$")
TOOLS = {
    "contract.read": {
        "name": "contract.read",
        "description": "Read an existing contract from real Saltcorn REST. Never mutates.",
        "parameters": {"type": "object", "additionalProperties": False,
                       "required": ["number"],
                       "properties": {"number": {"type": "string"}}},
        "required_scope": "contract.read", "mutates": False
    },
    "contract.action": {
        "name": "contract.action",
        "description": "Execute a Saltcorn action ONLY with separate trusted human grant, never from model text alone.",
        "parameters": {"type": "object", "additionalProperties": False,
                       "required": ["number", "action", "base_status"],
                       "properties": {"number": {"type": "string"},
                                      "action": {"type": "string", "enum": ["submit", "approve", "reject"]},
                                      "base_status": {"type": "string",
                                                      "enum": ["Draft", "Submitted", "Level1Approved"]}}},
        "required_scope": "contract.action", "mutates": True
    }
}

class ToolError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)

def json_schema_validate(schema, args):
    if not isinstance(args, dict):
        raise ToolError("INVALID_ARGUMENTS")
    if set(args) != set(schema["required"]):
        raise ToolError("INVALID_ARGUMENTS")
    for key, prop in schema["properties"].items():
        value = args[key]
        if not isinstance(value, str) or not 1 <= len(value) <= 100:
            raise ToolError("INVALID_ARGUMENTS")
        if "enum" in prop and value not in prop["enum"]:
            raise ToolError("INVALID_ARGUMENTS")

@dataclass(frozen=True)
class TrustedSession:
    session_key: str
    app_id: str
    email: str
    user_id: int
    role: str
    scopes: frozenset[str]
    # Playwright browser context and real authenticated Saltcorn session are
    # bound in adapter, not provided in LLM arguments.

@dataclass
class Grant:
    session_key: str
    app_id: str
    contract_no: str
    action: str
    deadline: float
    consumed: bool = False

class SaltcornRest:
    def __init__(self, base):
        if base != "http://127.0.0.1:3100":
            raise ToolError("LAB_LOCALHOST_ONLY")
        self.base = base
        self.sessions = {}

    def bind(self, session_key, browser_context, csrf):
        if not csrf or len(csrf) < 8:
            raise ToolError("SESSION_CSRF_MISSING")
        self.sessions[session_key] = (browser_context, csrf)

    def json_request(self, session_key, method, path, payload=None):
        if session_key not in self.sessions:
            raise ToolError("NO_NATIVE_SESSION")
        ctx, csrf = self.sessions[session_key]
        headers = {"Accept": "application/json"}
        if method == "POST":
            headers.update({"Content-Type": "application/json", "X-CSRF-Token": csrf})
        url = self.base + path
        try:
            if method == "POST":
                response = ctx.request.post(url, data=json.dumps(payload), headers=headers, timeout=15000)
            elif method == "GET":
                response = ctx.request.get(url, headers=headers, timeout=15000)
            else:
                raise ToolError("METHOD_NOT_ALLOWED")
        except ToolError:
            raise
        except Exception:
            # A POST network failure could mean success without a reply.
            # Never retry mutating calls or assume failure.
            raise ToolError("UNKNOWN_REMOTE_OUTCOME" if method == "POST" else "NATIVE_READ_FAILED")
        if response.url != url or "application/json" not in response.headers.get("content-type", ""):
            raise ToolError("NOT_NATIVE_JSON_RESPONSE")
        try:
            obj = response.json()
        except Exception:
            raise ToolError("INVALID_NATIVE_JSON")
        if response.status != 200 or not isinstance(obj, dict) or "success" not in obj:
            raise ToolError("NATIVE_REJECTED")
        return obj["success"]

    def contract(self, session_key, number):
        rows = self.json_request(session_key, "GET", "/api/s1_bench_contracts/")
        if not isinstance(rows, list):
            raise ToolError("BAD_NATIVE_DATA")
        matches = [row for row in rows if isinstance(row, dict) and row.get("number") == number]
        if len(matches) != 1:
            raise ToolError("NOT_FOUND_OR_NONUNIQUE")
        row = matches[0]
        if not isinstance(row.get("id"), int) or row.get("status") not in (
                "Draft", "Submitted", "Level1Approved", "Approved", "Rejected"):
            raise ToolError("BAD_NATIVE_DATA")
        return {key: row[key] for key in ("id", "number", "status", "amount_minor")}

    def action(self, session_key, user_id, role, number, action, contract_id):
        if role not in {"creator", "approver1", "approver2"}:
            raise ToolError("AGENT_CANNOT_APPROVE")
        payload = {
            "request_id": "s1-agent-" + secrets.token_hex(12),
            "contract_ref": contract_id, "action": action,
            "actor_role": role, "actor_id": str(user_id),
            "occurred_at": "2026-11-21T00:00:00Z",
            "reason": "explicit trusted human grant in S1"
        }
        # Single call only, no retry even on network timeout.
        return self.json_request(session_key, "POST", "/api/s1_bench_action_requests/", payload)

class Broker:
    def __init__(self, sqlite_path, adapter, now=None, max_calls=30):
        self.path = str(sqlite_path)
        self.adapter = adapter
        self.now = now or time.time
        self.max_calls = max_calls
        self.sessions = {}
        self.grants = {}
        self.calls = set()
        self.plugins = {}
        self.call_count = 0
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS agent_tool_audit (id INTEGER PRIMARY KEY,"
                "call_id TEXT NOT NULL, tool TEXT NOT NULL, principal TEXT NOT NULL,"
                "app_id TEXT NOT NULL, args_sha256 TEXT NOT NULL, result TEXT NOT NULL,"
                "created_at TEXT NOT NULL)")

    def bind_session(self, session, ctx, csrf):
        if session.app_id != APP_ID or session.email not in IDENTITIES:
            raise ToolError("SCOPE_DENIED")
        if IDENTITIES[session.email] != session.role or session.user_id <= 0:
            raise ToolError("TRUSTED_SESSION_MISMATCH")
        if session.session_key in self.sessions:
            raise ToolError("SESSION_ALREADY_BOUND")
        self.adapter.bind(session.session_key, ctx, csrf)
        self.sessions[session.session_key] = session

    def catalog(self, session_key):
        session = self._session(session_key)
        specs = list(TOOLS.values()) + list(self.plugins.values())
        return [{k: v for k, v in spec.items() if k in (
            "name", "description", "parameters")}
            for spec in specs if spec["required_scope"] in session.scopes]

    def register_manifest(self, manifest):
        # Declarative plugin metadata, NO arbitrary plugin code, shell or URL.
        if not isinstance(manifest, dict) or set(manifest) != {"name", "version", "tool"}:
            raise ToolError("BAD_PLUGIN_MANIFEST")
        if manifest["name"] != "route-inspector" or manifest["version"] != "1.0.0":
            raise ToolError("PLUGIN_NOT_ALLOWLISTED")
        tool = manifest["tool"]
        if not isinstance(tool, dict) or tool.get("name") != "contract.route" or \
           tool.get("handler") != "route_inspector_v1":
            raise ToolError("UNTRUSTED_PLUGIN_HANDLER")
        self.plugins["contract.route"] = {
            "name": "contract.route", "description": "Read the persisted Saltcorn approval route.",
            "parameters": TOOLS["contract.read"]["parameters"],
            "required_scope": "contract.read", "mutates": False
        }

    def issue_human_grant(self, session_key, number, action, *, trusted_user_confirmed=False, ttl=60):
        # This is intentionally a host-controlled API. Model tool calls never
        # have access to this method, a human grant token, or session secrets.
        subject = self._session(session_key)
        self._validate_number(number)
        if not trusted_user_confirmed or "contract.action" not in subject.scopes:
            raise ToolError("HUMAN_APPROVAL_REQUIRED")
        if action not in ("submit", "approve", "reject"):
            raise ToolError("INVALID_ACTION")
        if (action == "submit" and subject.role != "creator") or \
           (action in ("approve", "reject") and subject.role not in ("approver1", "approver2")):
            raise ToolError("ROLE_NOT_DELEGATABLE")
        if not 1 <= ttl <= 120:
            raise ToolError("GRANT_TTL_INVALID")
        handle = secrets.token_urlsafe(32)
        self.grants[handle] = Grant(session_key, subject.app_id, number, action, self.now() + ttl)
        return handle

    def _session(self, key):
        if key not in self.sessions:
            raise ToolError("UNAUTHENTICATED")
        return self.sessions[key]

    @staticmethod
    def _validate_number(number):
        if not isinstance(number, str) or not NUMBER.fullmatch(number):
            raise ToolError("INVALID_RESOURCE")

    def _record(self, call_id, name, session, args, result):
        digest = hashlib.sha256(json.dumps(args, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO agent_tool_audit"
                       "(call_id,tool,principal,app_id,args_sha256,result,created_at)"
                       " VALUES (?,?,?,?,?,?,?)",
                       (call_id, name, session.email if session else "unauthenticated",
                        session.app_id if session else "unknown", digest, result,
                        datetime.now(timezone.utc).isoformat(timespec="seconds")))

    def execute(self, session_key, tool_name, args, *, call_id, human_grant=None):
        subject = None
        result = "DENIED"
        if not isinstance(call_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{8,64}", call_id):
            raise ToolError("INVALID_CALL_ID")
        if self.call_count >= self.max_calls:
            raise ToolError("TOOL_BUDGET_EXHAUSTED")
        self.call_count += 1
        try:
            subject = self._session(session_key)
            if call_id in self.calls:
                raise ToolError("DUPLICATE_CALL_ID")
            self.calls.add(call_id)
            definitions = {**TOOLS, **self.plugins}
            if tool_name not in definitions:
                raise ToolError("UNKNOWN_TOOL")
            spec = definitions[tool_name]
            if spec["required_scope"] not in subject.scopes:
                raise ToolError("SCOPE_DENIED")
            json_schema_validate(spec["parameters"], args)
            number = args["number"]
            self._validate_number(number)
            current = self.adapter.contract(session_key, number)
            if tool_name == "contract.read":
                result = "READ_OK"
                return current
            if tool_name == "contract.route":
                cents = current["amount_minor"]
                if not isinstance(cents, int):
                    raise ToolError("BAD_NATIVE_DATA")
                route = "HIGH" if cents > 100000000 else "NORMAL"
                result = "READ_ROUTE_OK"
                # Derived route from actual persisted contract amount; not
                # a substitute for independent _sc_bench_routes DB check.
                return {"number": number, "derived_route": route,
                        "source": "native_contract_amount_minor"}
            if tool_name == "contract.action":
                if human_grant is None:
                    raise ToolError("HUMAN_APPROVAL_REQUIRED")
                grant = self.grants.get(human_grant)
                if grant is None or grant.consumed or grant.deadline <= self.now() or \
                   grant.session_key != session_key or grant.app_id != subject.app_id or \
                   grant.contract_no != number or grant.action != args["action"]:
                    raise ToolError("GRANT_REJECTED")
                if current["status"] != args["base_status"]:
                    raise ToolError("STALE_RESOURCE")
                # Once read+verified, consume BEFORE network write. Unknown
                # network outcomes require reconciliation; no blind retries.
                grant.consumed = True
                receipt = self.adapter.action(session_key, subject.user_id, subject.role,
                                              number, args["action"], current["id"])
                result = "MUTATION_ACCEPTED"
                return {"receipt": receipt, "status": "NATIVE_ACCEPTED_RECHECK_REQUIRED",
                        "contract_number": number}
            raise ToolError("UNKNOWN_TOOL")
        except ToolError as e:
            result = e.code
            raise
        finally:
            self._record(call_id, tool_name, subject, args if isinstance(args, dict) else {},
                         result)
