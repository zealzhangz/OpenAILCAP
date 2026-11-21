"""S1 B2 domain schema/manifest/runtime spike, not a production low-code engine.

SQLite single-file transactions; no eval, dynamic SQL, LLM, or plugin code.
Entire draft mutations are authorized domain commands with app-level CAS.
Published releases are immutable copies; runtime uses the published copy only.
"""
from __future__ import annotations

import hashlib
import json
import re
import secrets
import sqlite3
from dataclasses import dataclass


def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha(value):
    return hashlib.sha256(canon(value).encode()).hexdigest()


class Rejected(Exception):
    def __init__(self, status: int, code: str):
        super().__init__(code)
        self.status = status
        self.code = code


@dataclass(frozen=True)
class Actor:
    name: str
    app: str
    kinds: tuple[str, ...] = ("model", "form", "view", "workflow")
    can_publish: bool = False
    can_runtime: bool = False
    active: bool = True


RESOURCE = re.compile(r"^(model|form|view|workflow)\.[a-z][a-z0-9_]{0,39}$")
FIELD = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
CHANGE = re.compile(r"^[A-Za-z0-9_-]{4,96}$")
TYPES = {"string", "integer"}


def validate_definition(resource_id, spec):
    match = RESOURCE.fullmatch(resource_id) if isinstance(resource_id, str) else None
    if not match or not isinstance(spec, dict):
        raise Rejected(422, "INVALID_RESOURCE")
    kind = match.group(1)
    if spec.get("kind") != kind:
        raise Rejected(422, "KIND_MISMATCH")
    if kind == "model":
        if set(spec) != {"kind", "table", "fields"} or not (
            isinstance(spec["table"], str) and FIELD.fullmatch(spec["table"])
        ):
            raise Rejected(422, "INVALID_MODEL")
        fields = spec["fields"]
        if not isinstance(fields, list) or not (1 <= len(fields) <= 16):
            raise Rejected(422, "INVALID_FIELDS")
        names = set()
        for f in fields:
            if not isinstance(f, dict) or set(f) != {"name", "type", "required"}:
                raise Rejected(422, "INVALID_FIELDS")
            if not isinstance(f["name"], str) or not FIELD.fullmatch(f["name"]):
                raise Rejected(422, "INVALID_FIELDS")
            if f["name"] in names or f["type"] not in TYPES or type(f["required"]) is not bool:
                raise Rejected(422, "INVALID_FIELDS")
            names.add(f["name"])
    elif kind in ("form", "view"):
        key = "fields" if kind == "form" else "columns"
        if set(spec) != {"kind", "model", "title", key} or not (
            isinstance(spec["model"], str) and RESOURCE.fullmatch(spec["model"]) and
            spec["model"].startswith("model.")
        ):
            raise Rejected(422, "INVALID_PRESENTATION")
        if (not isinstance(spec["title"], str) or not 1 <= len(spec["title"]) <= 90 or
                not isinstance(spec[key], list) or not 1 <= len(spec[key]) <= 16 or
                len(set(spec[key])) != len(spec[key]) or
                any(not isinstance(x, str) or not FIELD.fullmatch(x) for x in spec[key])):
            raise Rejected(422, "INVALID_PRESENTATION")
    else:
        if set(spec) != {"kind", "model", "amountField", "statusField", "thresholdMinor"}:
            raise Rejected(422, "INVALID_WORKFLOW")
        if (not isinstance(spec["model"], str) or not RESOURCE.fullmatch(spec["model"]) or
            not spec["model"].startswith("model.") or
            any(not isinstance(spec[k], str) or not FIELD.fullmatch(spec[k])
                for k in ("amountField", "statusField")) or
                type(spec["thresholdMinor"]) is not int or
                not 0 <= spec["thresholdMinor"] <= 10**12):
            raise Rejected(422, "INVALID_WORKFLOW")
    return kind


def verify_refs(definitions):
    """Validate all cross-resource references, independent of command caller."""
    if len(definitions) > 32:
        raise Rejected(422, "RESOURCE_LIMIT")
    for rid, spec in definitions.items():
        kind = validate_definition(rid, spec)
        if kind == "model":
            continue
        model = definitions.get(spec["model"])
        if model is None or model.get("kind") != "model":
            raise Rejected(422, "BROKEN_MODEL_REFERENCE")
        types = {f["name"]: f["type"] for f in model["fields"]}
        used = spec.get("fields", spec.get("columns", []))
        if any(field not in types for field in used):
            raise Rejected(422, "BROKEN_FIELD_REFERENCE")
        if kind == "workflow" and (
            types.get(spec["amountField"]) != "integer" or
            types.get(spec["statusField"]) != "string"
        ):
            raise Rejected(422, "BROKEN_WORKFLOW_FIELD_TYPE")


class SchemaStore:
    def __init__(self, path):
        self.path = str(path)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=10000")
        return db

    def init(self):
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
              CREATE TABLE IF NOT EXISTS apps(
                app TEXT PRIMARY KEY, revision INTEGER NOT NULL,
                manifest_hash TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'ACTIVE',
                current_release INTEGER
              );
              CREATE TABLE IF NOT EXISTS definitions(
                app TEXT NOT NULL, rid TEXT NOT NULL,
                revision INTEGER NOT NULL, spec TEXT NOT NULL,
                hash TEXT NOT NULL, PRIMARY KEY(app,rid)
              );
              CREATE TABLE IF NOT EXISTS receipts(
                app TEXT NOT NULL, cid TEXT NOT NULL,
                actor TEXT NOT NULL, request_hash TEXT NOT NULL,
                response TEXT NOT NULL, PRIMARY KEY(app,cid)
              );
              CREATE TABLE IF NOT EXISTS events(
                eid INTEGER PRIMARY KEY AUTOINCREMENT,
                app TEXT NOT NULL, actor TEXT NOT NULL, event TEXT NOT NULL,
                rid TEXT NOT NULL, app_revision INTEGER NOT NULL
              );
              CREATE TABLE IF NOT EXISTS releases(
                app TEXT NOT NULL, version INTEGER NOT NULL,
                manifest TEXT NOT NULL, hash TEXT NOT NULL,
                draft_revision INTEGER NOT NULL, PRIMARY KEY(app,version)
              );
              CREATE TABLE IF NOT EXISTS records(
                app TEXT NOT NULL, model TEXT NOT NULL, record_id TEXT NOT NULL,
                version INTEGER NOT NULL, content TEXT NOT NULL,
                PRIMARY KEY(app,model,record_id)
              );
            """)

    def seed_app_for_test(self, app):
        """Only test fixture. No unauthenticated create-app endpoint."""
        if not FIELD.fullmatch(app.replace("-", "_")):
            raise ValueError("app id")
        with self.connect() as db:
            db.execute("INSERT INTO apps VALUES (?,?,?,'ACTIVE',NULL)",
                       (app, 0, sha({})))

    @staticmethod
    def authorize(actor, app, *, kind=None, write=False, publish=False, runtime=False):
        if actor is None or not actor.active:
            raise Rejected(401, "AUTH_REQUIRED")
        if actor.app != app:
            raise Rejected(403, "CROSS_APP_FORBIDDEN")
        if kind is not None and kind not in actor.kinds:
            raise Rejected(403, "KIND_FORBIDDEN")
        if publish and not actor.can_publish:
            raise Rejected(403, "PUBLISH_FORBIDDEN")
        if runtime and not actor.can_runtime:
            raise Rejected(403, "RUNTIME_FORBIDDEN")

    @staticmethod
    def _app(db, app):
        row = db.execute("SELECT * FROM apps WHERE app=?", (app,)).fetchone()
        if row is None:
            raise Rejected(404, "APP_NOT_FOUND")
        if row["state"] != "ACTIVE":
            raise Rejected(423, "APP_QUARANTINED")
        return row

    @staticmethod
    def _all(db, app):
        rows = db.execute("SELECT * FROM definitions WHERE app=? ORDER BY rid",
                          (app,)).fetchall()
        for row in rows:
            spec = json.loads(row["spec"])
            if sha(spec) != row["hash"]:
                db.execute("UPDATE apps SET state='QUARANTINED' WHERE app=?", (app,))
                db.commit()
                raise Rejected(409, "RESOURCE_DRIFT")
        return {row["rid"]: {
            "revision": row["revision"], "contentHash": row["hash"],
            "definition": json.loads(row["spec"])} for row in rows}

    @classmethod
    def _checked(cls, db, app):
        head = cls._app(db, app)
        resources = cls._all(db, app)
        defs = {rid: entry["definition"] for rid, entry in resources.items()}
        if sha(defs) != head["manifest_hash"]:
            db.execute("UPDATE apps SET state='QUARANTINED' WHERE app=?", (app,))
            db.commit()
            raise Rejected(409, "MANIFEST_DRIFT")
        return head, resources

    def draft(self, actor, app):
        self.authorize(actor, app)
        with self.connect() as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                head, resources = self._checked(db, app)
                result = {"applicationId": app, "appRevision": head["revision"],
                          "manifestHash": head["manifest_hash"],
                          "publishedVersion": head["current_release"],
                          "resources": resources}
                db.commit()
                return result
            except BaseException:
                if db.in_transaction:
                    db.rollback()
                raise

    @staticmethod
    def _replay(db, actor, app, cid, request_hash):
        prior = db.execute("SELECT * FROM receipts WHERE app=? AND cid=?",
                           (app, cid)).fetchone()
        if prior is None:
            return None
        if prior["actor"] != actor.name or prior["request_hash"] != request_hash:
            raise Rejected(409, "CHANGE_ID_REUSED")
        return {**json.loads(prior["response"]), "replayed": True}

    @staticmethod
    def _receipt(db, actor, app, cid, request_hash, result):
        db.execute("INSERT INTO receipts VALUES (?,?,?,?,?)",
                   (app, cid, actor.name, request_hash, canon(result)))

    def mutate(self, actor, app, cmd, *, fail_before_commit=False):
        if not isinstance(cmd, dict) or set(cmd) != {
            "changeId", "resourceId", "expectedAppRevision", "expectedRevision",
            "baseContentHash", "definition"
        }:
            raise Rejected(422, "INVALID_COMMAND")
        cid, rid = cmd["changeId"], cmd["resourceId"]
        match = RESOURCE.fullmatch(rid) if isinstance(rid, str) else None
        if not match or not isinstance(cid, str) or not CHANGE.fullmatch(cid):
            raise Rejected(422, "INVALID_COMMAND")
        kind = match.group(1)
        self.authorize(actor, app, kind=kind, write=True)
        if (type(cmd["expectedAppRevision"]) is not int or
                cmd["expectedAppRevision"] < 0 or
                (cmd["expectedRevision"] is not None and
                 (type(cmd["expectedRevision"]) is not int or
                  cmd["expectedRevision"] < 1)) or
                (cmd["baseContentHash"] is not None and
                 (not isinstance(cmd["baseContentHash"], str) or
                  not re.fullmatch(r"[0-9a-f]{64}", cmd["baseContentHash"])))):
            raise Rejected(422, "INVALID_COMMAND")
        if cmd["definition"] is not None:
            validate_definition(rid, cmd["definition"])
        request_hash = sha(cmd)
        with self.connect() as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                # Auth precedes receipt replay; the original receipt remains immutable.
                replay = self._replay(db, actor, app, cid, request_hash)
                if replay:
                    db.commit()
                    return replay
                head, resources = self._checked(db, app)
                if head["revision"] != cmd["expectedAppRevision"]:
                    raise Rejected(409, "APP_REVISION_CONFLICT")
                old = resources.get(rid)
                if old is None:
                    if cmd["expectedRevision"] is not None or cmd["baseContentHash"] is not None:
                        raise Rejected(409, "RESOURCE_VERSION_CONFLICT")
                elif old["revision"] != cmd["expectedRevision"] or (
                        old["contentHash"] != cmd["baseContentHash"]):
                    raise Rejected(409, "RESOURCE_VERSION_CONFLICT")
                defs = {key: value["definition"] for key, value in resources.items()}
                spec = cmd["definition"]
                if spec is None:
                    if old is None:
                        raise Rejected(404, "RESOURCE_NOT_FOUND")
                    del defs[rid]
                else:
                    defs[rid] = spec
                verify_refs(defs)
                if old is not None and old["definition"]["kind"] == "model":
                    self._block_unsafe_migration(db, app, rid, old["definition"], spec)
                new_rev = head["revision"] + 1
                if spec is None:
                    db.execute("DELETE FROM definitions WHERE app=? AND rid=?",
                               (app, rid))
                elif old is None:
                    db.execute("INSERT INTO definitions VALUES (?,?,?,?,?)",
                               (app, rid, 1, canon(spec), sha(spec)))
                else:
                    db.execute("UPDATE definitions SET revision=?, spec=?, hash=? "
                               "WHERE app=? AND rid=?",
                               (old["revision"] + 1, canon(spec), sha(spec), app, rid))
                manifest_hash = sha(defs)
                db.execute("UPDATE apps SET revision=?, manifest_hash=? WHERE app=?",
                           (new_rev, manifest_hash, app))
                result = {"decision": "APPLIED", "resourceId": rid,
                          "appRevision": new_rev, "manifestHash": manifest_hash,
                          "resourceRevision": None if spec is None else
                          (1 if old is None else old["revision"] + 1),
                          "changeId": cid, "replayed": False}
                self._receipt(db, actor, app, cid, request_hash, result)
                db.execute("INSERT INTO events(app,actor,event,rid,app_revision) "
                           "VALUES (?,?,?,?,?)",
                           (app, actor.name, "DELETE" if spec is None else "UPSERT",
                            rid, new_rev))
                if fail_before_commit:
                    raise RuntimeError("RESEARCH_INJECTED_FAILURE")
                db.commit()
                return result
            except BaseException:
                if db.in_transaction:
                    db.rollback()
                raise

    @staticmethod
    def _block_unsafe_migration(db, app, rid, old, spec):
        count = db.execute("SELECT COUNT(*) FROM records WHERE app=? AND model=?",
                           (app, rid)).fetchone()[0]
        if not count:
            return
        if spec is None:
            raise Rejected(422, "MIGRATION_REQUIRED")
        was = {f["name"]: (f["type"], f["required"]) for f in old["fields"]}
        now = {f["name"]: (f["type"], f["required"]) for f in spec["fields"]}
        for name, old_entry in was.items():
            if now.get(name, (None,))[0] != old_entry[0]:
                raise Rejected(422, "MIGRATION_REQUIRED")
        for name, (kind, required) in now.items():
            if name not in was and required:
                raise Rejected(422, "MIGRATION_REQUIRED")

    def publish(self, actor, app, cmd):
        self.authorize(actor, app, publish=True)
        if not isinstance(cmd, dict) or set(cmd) != {
            "changeId", "expectedAppRevision", "manifestHash"
        }:
            raise Rejected(422, "INVALID_COMMAND")
        if (not isinstance(cmd["changeId"], str) or not CHANGE.fullmatch(cmd["changeId"]) or
            type(cmd["expectedAppRevision"]) is not int or
            not isinstance(cmd["manifestHash"], str) or
            not re.fullmatch(r"[0-9a-f]{64}", cmd["manifestHash"])):
            raise Rejected(422, "INVALID_COMMAND")
        cid = cmd["changeId"]
        request_hash = sha({"action": "publish", **cmd})
        with self.connect() as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                replay = self._replay(db, actor, app, cid, request_hash)
                if replay:
                    db.commit()
                    return replay
                head, resources = self._checked(db, app)
                if head["revision"] != cmd["expectedAppRevision"] or (
                    head["manifest_hash"] != cmd["manifestHash"]):
                    raise Rejected(409, "PUBLISH_STALE")
                defs = {rid: v["definition"] for rid, v in resources.items()}
                verify_refs(defs)
                if not {"model", "form", "view", "workflow"}.issubset(
                    {v["kind"] for v in defs.values()}
                ):
                    raise Rejected(422, "RELEASE_INCOMPLETE")
                version = db.execute(
                    "SELECT COALESCE(MAX(version),0)+1 FROM releases WHERE app=?",
                    (app,)).fetchone()[0]
                release_hash = sha(defs)
                db.execute("INSERT INTO releases VALUES (?,?,?,?,?)",
                           (app, version, canon(defs), release_hash, head["revision"]))
                db.execute("UPDATE apps SET current_release=? WHERE app=?",
                           (version, app))
                result = {"decision": "PUBLISHED", "changeId": cid,
                          "version": version, "manifestHash": release_hash,
                          "appRevision": head["revision"], "replayed": False}
                self._receipt(db, actor, app, cid, request_hash, result)
                db.execute("INSERT INTO events(app,actor,event,rid,app_revision) "
                           "VALUES (?,?,?,?,?)",
                           (app, actor.name, "PUBLISH", "application",
                            head["revision"]))
                db.commit()
                return result
            except BaseException:
                if db.in_transaction:
                    db.rollback()
                raise

    def rollback(self, actor, app, cmd):
        self.authorize(actor, app, publish=True)
        if not isinstance(cmd, dict) or set(cmd) != {
            "changeId", "expectedPublishedVersion", "targetVersion"
        } or not isinstance(cmd["changeId"], str) or not CHANGE.fullmatch(
            cmd["changeId"]
        ) or type(cmd["expectedPublishedVersion"]) is not int or (
            type(cmd["targetVersion"]) is not int
        ):
            raise Rejected(422, "INVALID_COMMAND")
        cid, request_hash = cmd["changeId"], sha({"action": "rollback", **cmd})
        with self.connect() as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                replay = self._replay(db, actor, app, cid, request_hash)
                if replay:
                    db.commit()
                    return replay
                head, _ = self._checked(db, app)
                if head["current_release"] != cmd["expectedPublishedVersion"]:
                    raise Rejected(409, "PUBLISH_POINTER_CONFLICT")
                target = db.execute(
                    "SELECT * FROM releases WHERE app=? AND version=?",
                    (app, cmd["targetVersion"])
                ).fetchone()
                if target is None or sha(json.loads(target["manifest"])) != target["hash"]:
                    raise Rejected(409, "RELEASE_HASH_MISMATCH")
                db.execute("UPDATE apps SET current_release=? WHERE app=?",
                           (target["version"], app))
                result = {"decision": "ROLLED_BACK",
                          "version": target["version"], "changeId": cid,
                          "manifestHash": target["hash"], "replayed": False}
                self._receipt(db, actor, app, cid, request_hash, result)
                db.execute("INSERT INTO events(app,actor,event,rid,app_revision) "
                           "VALUES (?,?,?,?,?)",
                           (app, actor.name, "ROLLBACK", "application",
                            head["revision"]))
                db.commit()
                return result
            except BaseException:
                if db.in_transaction:
                    db.rollback()
                raise

    def release(self, actor, app):
        self.authorize(actor, app)
        with self.connect() as db:
            head = self._app(db, app)
            if head["current_release"] is None:
                raise Rejected(404, "NOT_PUBLISHED")
            row = db.execute("SELECT * FROM releases WHERE app=? AND version=?",
                             (app, head["current_release"])).fetchone()
            if not row or sha(json.loads(row["manifest"])) != row["hash"]:
                raise Rejected(409, "RELEASE_HASH_MISMATCH")
            return {"version": row["version"], "manifestHash": row["hash"],
                    "draftRevision": row["draft_revision"],
                    "definitions": json.loads(row["manifest"])}

    def submit_form(self, actor, app, form_id, values):
        self.authorize(actor, app, runtime=True)
        release = self.release(actor, app)
        defs = release["definitions"]
        form = defs.get(form_id)
        if not form or form["kind"] != "form":
            raise Rejected(404, "FORM_NOT_PUBLISHED")
        model = defs[form["model"]]
        fieldtypes = {f["name"]: f for f in model["fields"]}
        if not isinstance(values, dict) or set(values) - set(form["fields"]):
            raise Rejected(422, "INVALID_ROW")
        data = {}
        for name in form["fields"]:
            f = fieldtypes[name]
            value = values.get(name)
            if value is None:
                if f["required"]:
                    raise Rejected(422, "REQUIRED_FIELD_MISSING")
                continue
            if f["type"] == "string":
                if not isinstance(value, str) or not 1 <= len(value) <= 256:
                    raise Rejected(422, "TYPE_MISMATCH")
            elif type(value) is not int or value < 0 or value > 10**14:
                raise Rejected(422, "TYPE_MISMATCH")
            data[name] = value
        for field in model["fields"]:
            if field["name"] == "status" and field["type"] == "string":
                data["status"] = "Draft"
        for f in model["fields"]:
            if f["required"] and f["name"] not in data:
                raise Rejected(422, "REQUIRED_FIELD_MISSING")
        record_id = secrets.token_hex(9)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("INSERT INTO records VALUES (?,?,?,?,?)",
                       (app, form["model"], record_id, 1, canon(data)))
            db.execute("INSERT INTO events(app,actor,event,rid,app_revision) "
                       "VALUES (?,?,?,?,?)",
                       (app, actor.name, "RECORD_CREATED", form["model"],
                        release["draftRevision"]))
            db.commit()
        return {"recordId": record_id, "version": 1, "data": data,
                "releaseVersion": release["version"]}

    def view_rows(self, actor, app, view_id):
        self.authorize(actor, app, runtime=True)
        release = self.release(actor, app)
        view = release["definitions"].get(view_id)
        if not view or view["kind"] != "view":
            raise Rejected(404, "VIEW_NOT_PUBLISHED")
        with self.connect() as db:
            rows = db.execute("SELECT record_id,content FROM records "
                              "WHERE app=? AND model=? ORDER BY rowid",
                              (app, view["model"])).fetchall()
        return {"version": release["version"], "title": view["title"],
                "columns": view["columns"],
                "rows": [{"recordId": row["record_id"],
                          "cells": {k: json.loads(row["content"]).get(k)
                                    for k in view["columns"]}} for row in rows]}

    def advance(self, actor, app, workflow_id, record_id, action, expected_version):
        self.authorize(actor, app, runtime=True)
        release = self.release(actor, app)
        workflow = release["definitions"].get(workflow_id)
        if not workflow or workflow["kind"] != "workflow":
            raise Rejected(404, "WORKFLOW_NOT_PUBLISHED")
        if action not in ("submit", "approve") or type(expected_version) is not int:
            raise Rejected(422, "INVALID_ACTION")
        with self.connect() as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                row = db.execute("SELECT * FROM records WHERE app=? AND model=? "
                                 "AND record_id=?",
                                 (app, workflow["model"], record_id)).fetchone()
                if not row:
                    raise Rejected(404, "RECORD_NOT_FOUND")
                if row["version"] != expected_version:
                    raise Rejected(409, "ROW_VERSION_CONFLICT")
                data = json.loads(row["content"])
                state = data[workflow["statusField"]]
                amount = data[workflow["amountField"]]
                if action == "submit" and state == "Draft":
                    new_state = "PendingLevel1"
                elif action == "approve" and state == "PendingLevel1":
                    new_state = ("PendingLevel2" if
                                 amount > workflow["thresholdMinor"] else "Approved")
                elif action == "approve" and state == "PendingLevel2":
                    new_state = "Approved"
                else:
                    raise Rejected(409, "INVALID_WORKFLOW_TRANSITION")
                data[workflow["statusField"]] = new_state
                result = db.execute("UPDATE records SET content=?,version=? "
                                    "WHERE app=? AND model=? AND record_id=? "
                                    "AND version=?",
                                    (canon(data), row["version"] + 1,
                                     app, workflow["model"], record_id, expected_version))
                if result.rowcount != 1:
                    raise Rejected(409, "ROW_VERSION_CONFLICT")
                db.execute("INSERT INTO events(app,actor,event,rid,app_revision) "
                           "VALUES (?,?,?,?,?)",
                           (app, actor.name, "WORKFLOW_" + action.upper(),
                            workflow_id, release["draftRevision"]))
                db.commit()
                return {"recordId": record_id, "version": row["version"] + 1,
                        "status": new_state, "releaseVersion": release["version"]}
            except BaseException:
                if db.in_transaction:
                    db.rollback()
                raise

    def physical(self, app):
        """Independent test oracle; NOT exported by HTTP."""
        with self.connect() as db:
            a = db.execute("SELECT * FROM apps WHERE app=?", (app,)).fetchone()
            return {"revision": a["revision"], "manifestHash": a["manifest_hash"],
                    "state": a["state"], "currentRelease": a["current_release"],
                    "events": [dict(x) for x in db.execute(
                        "SELECT actor,event,rid,app_revision FROM events WHERE app=? "
                        "ORDER BY eid", (app,))],
                    "releases": [dict(x) for x in db.execute(
                        "SELECT version,hash,draft_revision FROM releases WHERE app=? "
                        "ORDER BY version", (app,))]}
