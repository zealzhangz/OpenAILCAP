"""H01/H03 persistence SPIKE: governed app-resource commits on *real SQLite*.

NOT production-ready auth, sandboxing, deployment, or a low-code runtime.
The actor parameter is assumed to be supplied by a trusted API gateway.
"""
from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
from dataclasses import dataclass
from contextlib import closing
from pathlib import Path
from typing import Any


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


class Rejected(Exception):
    def __init__(self, code: str, detail: str = ""):
        self.code = code
        super().__init__(f"{code}: {detail}")


@dataclass
class Snapshot:
    app_id: str
    revision: int
    fingerprint: str
    resources: dict[str, dict[str, Any]]


INITIAL = {
    "contract-page": {"domain": "ui", "data": {"title": "合同信息", "layout": {"columns": 2}}, "refs": []},
    "submit-btn": {"domain": "ui", "data": {"label": "提交", "style": {"background": "blue"}}, "refs": ["contract-page"]},
    "approval": {"domain": "workflow", "data": {"operator": ">", "threshold": 1000000}, "refs": ["contract-page"]},
    "submit-event": {"domain": "workflow", "data": {"action": "submit"}, "refs": ["submit-btn", "approval"]},
    "custom-code": {"domain": "code", "data": {"source": "return prefix + seq"}, "refs": []},
    "plugin": {"domain": "plugin", "data": {"config": {"mode": "strict", "unknown_field": {"v": 17}}}, "refs": []},
}


def set_field(identifier: str, path: str, value: Any) -> dict[str, Any]:
    return {"kind": "set", "id": identifier, "path": path, "value": value}


def create(identifier: str, resource: dict[str, Any]) -> dict[str, Any]:
    return {"kind": "create", "id": identifier, "resource": resource}


def delete(identifier: str) -> dict[str, Any]:
    return {"kind": "delete", "id": identifier}


def get_field(resource: dict[str, Any], path: str) -> Any:
    obj: Any = resource
    for segment in path.split("."):
        if not isinstance(obj, dict) or segment not in obj:
            raise Rejected("BAD_PATH", path)
        obj = obj[segment]
    return copy.deepcopy(obj)


def assign(resource: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    if parts[0] not in ("data", "refs") or (parts[0] == "data" and len(parts) < 2) or (parts[0] == "refs" and len(parts) != 1):
        raise Rejected("BAD_PATH", path)
    obj: Any = resource
    for item in parts[:-1]:
        if not isinstance(obj, dict) or item not in obj:
            raise Rejected("BAD_PATH", path)
        obj = obj[item]
    if not isinstance(obj, dict) or parts[-1] not in obj:
        raise Rejected("BAD_PATH", path)
    if path == "refs" and (not isinstance(value, list) or not all(isinstance(x, str) for x in value)):
        raise Rejected("BAD_REFS")
    obj[parts[-1]] = copy.deepcopy(value)


def validate(resources: dict[str, dict[str, Any]]) -> None:
    for rid, value in resources.items():
        if not isinstance(rid, str) or not rid or not isinstance(value, dict):
            raise Rejected("BAD_RESOURCE", str(rid))
        if not isinstance(value.get("domain"), str) or not isinstance(value.get("data"), dict):
            raise Rejected("BAD_RESOURCE", rid)
        refs = value.get("refs")
        if not isinstance(refs, list) or not all(isinstance(x, str) for x in refs):
            raise Rejected("BAD_REFS", rid)
        for ref in refs:
            if ref not in resources:
                raise Rejected("BROKEN_REF", f"{rid} -> {ref}")


class Store:
    """Each operation opens its own SQLite connection to exercise DB locks.

    Apps/resources/history/changes/permissions use app_id composite keys. No
    cross-process Python mutex is used. Transactions use BEGIN IMMEDIATE.
    """

    def __init__(self, filename: str | Path):
        self.filename = str(filename)
        self.initialize()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.filename, timeout=5, isolation_level=None)
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def initialize(self) -> None:
        with closing(self._conn()) as con:
            con.executescript("""
            CREATE TABLE IF NOT EXISTS apps (
                app_id TEXT PRIMARY KEY, revision INTEGER NOT NULL, fingerprint TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS resources (
                app_id TEXT NOT NULL, resource_id TEXT NOT NULL, body TEXT NOT NULL,
                PRIMARY KEY (app_id, resource_id),
                FOREIGN KEY (app_id) REFERENCES apps(app_id));
            CREATE TABLE IF NOT EXISTS versions (
                app_id TEXT NOT NULL, revision INTEGER NOT NULL,
                fingerprint TEXT NOT NULL, snapshot TEXT NOT NULL,
                PRIMARY KEY (app_id, revision), FOREIGN KEY (app_id) REFERENCES apps(app_id));
            CREATE TABLE IF NOT EXISTS grants (
                app_id TEXT NOT NULL, actor TEXT NOT NULL, permission TEXT NOT NULL
                    CHECK(permission IN ('read','write')),
                PRIMARY KEY (app_id, actor), FOREIGN KEY (app_id) REFERENCES apps(app_id));
            CREATE TABLE IF NOT EXISTS changes (
                app_id TEXT NOT NULL, change_id TEXT NOT NULL,
                signature TEXT NOT NULL, receipt TEXT NOT NULL,
                PRIMARY KEY (app_id, change_id), FOREIGN KEY (app_id) REFERENCES apps(app_id));
            """)

    def bootstrap_app(self, app_id: str, owner: str = "owner") -> None:
        """Privileged fixture-only action (not an application-facing endpoint)."""
        data = copy.deepcopy(INITIAL)
        validate(data)
        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("INSERT INTO apps VALUES (?, ?, ?)", (app_id, 0, sha(data)))
            self._persist(conn, app_id, data)
            conn.execute("INSERT INTO versions VALUES (?, ?, ?, ?)", (app_id, 0, sha(data), canonical(data)))
            conn.execute("INSERT INTO grants VALUES (?, ?, ?)", (app_id, owner, "write"))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def grant_for_fixture(self, app_id: str, actor: str, permission: str) -> None:
        """Privileged fixture-only action; no ability to grant via app command."""
        if permission not in ("read", "write"):
            raise ValueError(permission)
        with closing(self._conn()) as con:
            con.execute("INSERT INTO grants VALUES (?, ?, ?) ON CONFLICT(app_id,actor) DO UPDATE SET permission=excluded.permission", (app_id, actor, permission))

    @staticmethod
    def _authorize(conn: sqlite3.Connection, app_id: str, actor: str, write: bool) -> None:
        row = conn.execute("SELECT permission FROM grants WHERE app_id=? AND actor=?", (app_id, actor)).fetchone()
        if row is None or (write and row[0] != "write"):
            raise Rejected("FORBIDDEN", f"{actor}/{app_id}")

    @staticmethod
    def _load(conn: sqlite3.Connection, app_id: str) -> Snapshot:
        row = conn.execute("SELECT revision,fingerprint FROM apps WHERE app_id=?", (app_id,)).fetchone()
        if row is None:
            raise Rejected("UNKNOWN_APP", app_id)
        resources = {rid: json.loads(body) for rid, body in conn.execute(
            "SELECT resource_id,body FROM resources WHERE app_id=?", (app_id,))}
        if sha(resources) != row[1]:
            raise Rejected("SNAPSHOT_DRIFT", "Unversioned data exists in resources; fail closed")
        validate(resources)
        return Snapshot(app_id, int(row[0]), row[1], resources)

    def snapshot(self, app_id: str, *, actor: str = "owner") -> Snapshot:
        with closing(self._conn()) as conn:
            conn.execute("BEGIN")  # Stable read snapshot across apps + resources statements
            self._authorize(conn, app_id, actor, False)
            result = self._load(conn, app_id)
            conn.commit()
            return result

    @staticmethod
    def _persist(conn: sqlite3.Connection, app_id: str, state: dict[str, dict[str, Any]]) -> None:
        conn.execute("DELETE FROM resources WHERE app_id=?", (app_id,))
        conn.executemany("INSERT INTO resources (app_id,resource_id,body) VALUES (?,?,?)",
                         [(app_id, rid, canonical(body)) for rid, body in state.items()])

    def apply(self, app_id: str, *, actor: str, change_id: str, base: Snapshot,
              operations: list[dict[str, Any]], fail_after_write: bool = False) -> dict[str, Any]:
        if not change_id or not actor or not operations:
            raise Rejected("BAD_COMMAND")
        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            self._authorize(conn, app_id, actor, True)
            signature = sha({"actor": actor, "base": {"app_id": base.app_id,
                             "revision": base.revision, "fingerprint": base.fingerprint}, "operations": operations})
            current = self._load(conn, app_id)  # fail closed on drift, even during idempotent replay
            saved = conn.execute("SELECT signature,receipt FROM changes WHERE app_id=? AND change_id=?",
                                 (app_id, change_id)).fetchone()
            if saved:
                if saved[0] != signature:
                    raise Rejected("IDEMPOTENCY_REUSE")
                result = json.loads(saved[1])
                conn.commit()
                return result
            if base.app_id != app_id:
                raise Rejected("CROSS_APP_BASE")
            historical = conn.execute("SELECT fingerprint,snapshot FROM versions WHERE app_id=? AND revision=?",
                                     (app_id, base.revision)).fetchone()
            if historical is None or historical[0] != base.fingerprint or json.loads(historical[1]) != base.resources:
                raise Rejected("UNTRUSTED_BASE")
            next_state = copy.deepcopy(current.resources)
            for op in operations:
                verb, rid = op.get("kind"), op.get("id")
                if verb == "set":
                    if rid not in base.resources or rid not in current.resources:
                        raise Rejected("MISSING_RESOURCE", str(rid))
                    path = op["path"]
                    old = get_field(base.resources[rid], path)
                    fresh = get_field(current.resources[rid], path)
                    new = op["value"]
                    if old != fresh and fresh != new:
                        raise Rejected("WRITE_CONFLICT", f"{rid}.{path}")
                    assign(next_state[rid], path, new)
                elif verb == "delete":
                    if rid not in base.resources or rid not in current.resources:
                        raise Rejected("MISSING_RESOURCE", str(rid))
                    if current.resources[rid] != base.resources[rid]:
                        raise Rejected("WRITE_CONFLICT", f"delete {rid}")
                    del next_state[rid]
                elif verb == "create":
                    if not isinstance(rid, str) or not rid or rid in next_state or rid in base.resources:
                        raise Rejected("RESOURCE_EXISTS", str(rid))
                    next_state[rid] = copy.deepcopy(op["resource"])
                else:
                    raise Rejected("UNKNOWN_OPERATION", str(verb))
            validate(next_state)
            revision = current.revision + 1
            fingerprint = sha(next_state)
            self._persist(conn, app_id, next_state)
            if fail_after_write:
                # SQL rows changed inside an open transaction, but app state/version
                # and receipt are not committed. Process restart must not see them.
                raise Rejected("INJECTED_FAILURE")
            conn.execute("UPDATE apps SET revision=?,fingerprint=? WHERE app_id=?",
                         (revision, fingerprint, app_id))
            conn.execute("INSERT INTO versions VALUES (?,?,?,?)",
                         (app_id, revision, fingerprint, canonical(next_state)))
            receipt = {"app_id": app_id, "revision": revision, "fingerprint": fingerprint,
                       "merged": base.revision != current.revision}
            conn.execute("INSERT INTO changes VALUES (?,?,?,?)",
                         (app_id, change_id, signature, canonical(receipt)))
            conn.commit()
            return receipt
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def rollback(self, app_id: str, *, actor: str, to_revision: int) -> dict[str, Any]:
        conn = self._conn()
        try:
            conn.execute("BEGIN IMMEDIATE")
            self._authorize(conn, app_id, actor, True)
            current = self._load(conn, app_id)
            row = conn.execute("SELECT fingerprint,snapshot FROM versions WHERE app_id=? AND revision=?",
                               (app_id, to_revision)).fetchone()
            if not row:
                raise Rejected("UNKNOWN_REVISION")
            target = json.loads(row[1])
            validate(target)
            self._persist(conn, app_id, target)
            new_rev = current.revision + 1
            conn.execute("UPDATE apps SET revision=?,fingerprint=? WHERE app_id=?",
                         (new_rev, row[0], app_id))
            conn.execute("INSERT INTO versions VALUES (?,?,?,?)", (app_id, new_rev, row[0], row[1]))
            conn.commit()
            return {"app_id": app_id, "revision": new_rev, "fingerprint": row[0]}
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()
