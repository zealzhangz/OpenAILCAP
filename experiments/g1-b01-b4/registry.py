"""B4 companion extension registry bound atomically to B2 published manifest.

This is host-internal trusted orchestrator code, NOT a public HTTP endpoint.
The model never receives a registry actor, Docker access or a publish token.
"""
from __future__ import annotations

import json
import sqlite3

from policy import RuleError,oracle,source_hash,validate_source
from sandbox import DockerSandbox,SandboxProof
from schema_core import SchemaStore,Actor,Rejected,sha


class ExtensionRegistry:
    def __init__(self,b2:SchemaStore,sandbox:DockerSandbox):
        self.b2=b2
        self.sandbox=sandbox

    def init(self):
        with self.b2.connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS extension_artifacts (
              app TEXT NOT NULL, artifact_hash TEXT NOT NULL,
              source TEXT NOT NULL, image_id TEXT NOT NULL,
              verified_cases INTEGER NOT NULL,
              b2_version INTEGER NOT NULL, b2_manifest_hash TEXT NOT NULL,
              PRIMARY KEY(app,artifact_hash)
            );
            CREATE TABLE IF NOT EXISTS extension_releases (
              app TEXT NOT NULL, version INTEGER NOT NULL,
              artifact_hash TEXT NOT NULL,
              b2_version INTEGER NOT NULL, b2_manifest_hash TEXT NOT NULL,
              PRIMARY KEY(app,version)
            );
            CREATE TABLE IF NOT EXISTS extension_pointers (
              app TEXT PRIMARY KEY, version INTEGER NOT NULL
            );
            """)

    @staticmethod
    def _schema(db,app):
        a=db.execute("SELECT current_release,revision FROM apps WHERE app=?",
                     (app,)).fetchone()
        if not a or a["current_release"] is None:
            raise Rejected(409,"B2_NOT_PUBLISHED")
        r=db.execute("SELECT version,manifest,hash FROM releases "
                     "WHERE app=? AND version=?",
                     (app,a["current_release"])).fetchone()
        if not r or sha(json.loads(r["manifest"]))!=r["hash"]:
            raise Rejected(409,"B2_RELEASE_HASH_INVALID")
        return {"version":r["version"],"hash":r["hash"],
                "appRevision":a["revision"]}

    @staticmethod
    def _current(db,app):
        r=db.execute("SELECT version FROM extension_pointers WHERE app=?",
                     (app,)).fetchone()
        return r["version"] if r else 0

    @staticmethod
    def _authorize(actor,app,*,publish=False,runtime=False):
        SchemaStore.authorize(actor,app,publish=publish,runtime=runtime)

    def stage(self,actor:Actor,app:str,source:str,proof:SandboxProof):
        self._authorize(actor,app,publish=True)
        checked=validate_source(source)
        if (not isinstance(proof,SandboxProof) or
            proof.source_hash!=checked["sourceHash"] or
            proof.cases!=432 or proof.result is not None or
            proof.image_id!=self.sandbox.image_id):
            raise Rejected(422,"BUILD_ATTESTATION_INVALID")
        with self.b2.connect() as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                s=self._schema(db,app)
                db.execute("INSERT OR IGNORE INTO extension_artifacts "
                           "(app,artifact_hash,source,image_id,verified_cases,"
                           "b2_version,b2_manifest_hash) VALUES (?,?,?,?,?,?,?)",
                           (app,checked["sourceHash"],source,proof.image_id,proof.cases,
                            s["version"],s["hash"]))
                row=db.execute("SELECT * FROM extension_artifacts "
                               "WHERE app=? AND artifact_hash=?",
                               (app,checked["sourceHash"])).fetchone()
                if (row["source"]!=source or row["b2_version"]!=s["version"] or
                    row["b2_manifest_hash"]!=s["hash"]):
                    raise Rejected(409,"ARTIFACT_BINDING_CONFLICT")
                db.execute("INSERT INTO events(app,actor,event,rid,app_revision) "
                           "VALUES (?,?,?,?,?)",
                           (app,actor.name,"EXTENSION_BUILD_VERIFIED",
                            checked["sourceHash"],s["appRevision"]))
                db.commit()
                return {"artifactHash":checked["sourceHash"],
                        "boundB2Version":s["version"],
                        "boundManifestHash":s["hash"],"testedCases":proof.cases}
            except BaseException:
                if db.in_transaction:db.rollback()
                raise

    def publish(self,actor,app,artifact_hash,expected_extension_version,
                *,inject_failure=False):
        self._authorize(actor,app,publish=True)
        if type(expected_extension_version) is not int or expected_extension_version<0:
            raise Rejected(422,"INVALID_EXPECTED_VERSION")
        with self.b2.connect() as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                s=self._schema(db,app)
                cur=self._current(db,app)
                if cur!=expected_extension_version:
                    raise Rejected(409,"EXTENSION_VERSION_CONFLICT")
                r=db.execute("SELECT * FROM extension_artifacts WHERE app=? "
                             "AND artifact_hash=?",
                             (app,artifact_hash)).fetchone()
                if not r:
                    raise Rejected(404,"BUILD_NOT_VERIFIED")
                if (r["b2_version"]!=s["version"] or
                    r["b2_manifest_hash"]!=s["hash"]):
                    raise Rejected(409,"B2_RELEASE_CHANGED")
                if source_hash(r["source"])!=r["artifact_hash"]:
                    raise Rejected(409,"ARTIFACT_HASH_DRIFT")
                v=db.execute("SELECT COALESCE(MAX(version),0)+1 FROM "
                             "extension_releases WHERE app=?",(app,)).fetchone()[0]
                db.execute("INSERT INTO extension_releases VALUES (?,?,?,?,?)",
                           (app,v,artifact_hash,s["version"],s["hash"]))
                db.execute("INSERT INTO extension_pointers VALUES (?,?) "
                           "ON CONFLICT(app) DO UPDATE SET version=excluded.version",
                           (app,v))
                db.execute("INSERT INTO events(app,actor,event,rid,app_revision) "
                           "VALUES (?,?,?,?,?)",
                           (app,actor.name,"EXTENSION_PUBLISH",
                            artifact_hash,s["appRevision"]))
                if inject_failure:
                    raise RuntimeError("INJECTED_EXTENSION_PUBLISH_FAILURE")
                db.commit()
                return {"publishedExtensionVersion":v,
                        "artifactHash":artifact_hash,"boundB2Version":s["version"]}
            except BaseException:
                if db.in_transaction:db.rollback()
                raise

    def rollback(self,actor,app,expected_extension_version,target):
        self._authorize(actor,app,publish=True)
        if type(expected_extension_version) is not int or type(target) is not int:
            raise Rejected(422,"INVALID_EXPECTED_VERSION")
        with self.b2.connect() as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                s=self._schema(db,app)
                if self._current(db,app)!=expected_extension_version:
                    raise Rejected(409,"EXTENSION_VERSION_CONFLICT")
                r=db.execute("SELECT * FROM extension_releases WHERE app=? "
                             "AND version=?",(app,target)).fetchone()
                if not r:raise Rejected(404,"EXTENSION_VERSION_NOT_FOUND")
                if (r["b2_version"]!=s["version"] or
                    r["b2_manifest_hash"]!=s["hash"]):
                    raise Rejected(409,"B2_RELEASE_CHANGED")
                db.execute("UPDATE extension_pointers SET version=? WHERE app=?",
                           (target,app))
                db.execute("INSERT INTO events(app,actor,event,rid,app_revision) "
                           "VALUES (?,?,?,?,?)",
                           (app,actor.name,"EXTENSION_ROLLBACK",
                            str(target),s["appRevision"]))
                db.commit()
                return {"activeExtensionVersion":target}
            except BaseException:
                if db.in_transaction:db.rollback()
                raise

    def _active(self,actor,app):
        self._authorize(actor,app,runtime=True)
        with self.b2.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                s=self._schema(db,app)
                cur=self._current(db,app)
                if cur==0:raise Rejected(404,"EXTENSION_NOT_DEPLOYED")
                r=db.execute("SELECT * FROM extension_releases WHERE app=? "
                             "AND version=?",(app,cur)).fetchone()
                if not r:raise Rejected(409,"EXTENSION_RELEASE_MISSING")
                if (r["b2_version"]!=s["version"] or
                    r["b2_manifest_hash"]!=s["hash"]):
                    raise Rejected(409,"B2_RELEASE_CHANGED")
                art=db.execute("SELECT * FROM extension_artifacts WHERE app=? "
                               "AND artifact_hash=?",
                               (app,r["artifact_hash"])).fetchone()
                if not art or source_hash(art["source"])!=art["artifact_hash"]:
                    raise Rejected(409,"ARTIFACT_HASH_DRIFT")
                value={"source":art["source"],"sourceHash":art["artifact_hash"],
                       "extensionVersion":cur,"b2Version":s["version"],
                       "b2ManifestHash":s["hash"]}
                db.commit()
                return value
            except BaseException:
                if db.in_transaction:db.rollback()
                raise

    def score_record(self,actor,app,record_id,supplier_score,months_active):
        self._authorize(actor,app,runtime=True)
        active=self._active(actor,app)
        view=self.b2.view_rows(actor,app,"view.contracts")
        if view["version"]!=active["b2Version"]:
            raise Rejected(409,"B2_RELEASE_CHANGED")
        matches=[r for r in view["rows"] if r["recordId"]==record_id]
        if len(matches)!=1:raise Rejected(404,"CONTRACT_NOT_FOUND")
        amount=matches[0]["cells"].get("amount_minor")
        if type(amount) is not int:
            raise Rejected(422,"CONTRACT_AMOUNT_UNAVAILABLE")
        payload={"amount_minor":amount,
                 "supplier_score":supplier_score,"months_active":months_active}
        oracle(**payload) # fail-closed input bounds before sandbox invocation
        proof=self.sandbox.test(active["source"],payload)
        if proof.source_hash!=active["sourceHash"]:
            raise Rejected(409,"RUNTIME_CODE_HASH_DRIFT")
        risk=proof.result
        return {"recordId":record_id,"riskScore":risk,
                "riskTier":"HIGH" if risk>=60 else ("MEDIUM" if risk>=30 else "LOW"),
                "extensionVersion":active["extensionVersion"],
                "baseB2Version":active["b2Version"],
                "modelCodeSourceHash":active["sourceHash"]}

    def physical(self,app):
        """Lab oracle only; not exposed through public HTTP."""
        with self.b2.connect() as db:
            return {
                "activeExtensionVersion":self._current(db,app),
                "artifacts":db.execute(
                    "SELECT COUNT(*) FROM extension_artifacts WHERE app=?",
                    (app,)).fetchone()[0],
                "releases":db.execute(
                    "SELECT COUNT(*) FROM extension_releases WHERE app=?",
                    (app,)).fetchone()[0]
            }
