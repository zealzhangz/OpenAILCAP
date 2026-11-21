"""Strict B9 adapter: B2 *published and hash-verified* release -> Saltcorn Pack.

The output is a deterministic, disposable DATA/VIEW PROJECTION only. It does
NOT project workflow execution, arbitrary B4 code, plugin permissions, form
security, dynamic cache invalidation or enterprise user model. Never promote a
Saltcorn runtime copy back into authoritative B2 definitions.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from schema_core import sha, validate_definition, verify_refs, Rejected

REQUIRED={"model.contracts","form.contracts","view.contracts",
          "workflow.approval"}
FIELD_TYPES={"string":"String","integer":"Integer"}


class ProjectionRejected(Exception):
    def __init__(self,code):
        self.code=code
        super().__init__(code)


def canon(v):
    return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"))


def hash_pack(pack):
    return hashlib.sha256(canon(pack).encode("utf-8")).hexdigest()


def compile_release(release,template):
    """Only a release returned by trusted B2 release.read is acceptable.

    Verification of hash + semantic refs protects against incorrect exports,
    corrupted snapshots and malicious "draft" substituted by runtime. The
    trusted publisher MUST also check version is the currently verified
    pointer from live kernel; a random signed-looking JSON is not authority.
    """
    if not isinstance(release,dict) or set(release)!={
            "version","manifestHash","draftRevision","definitions"}:
        raise ProjectionRejected("RELEASE_SHAPE_INVALID")
    defs=release["definitions"]
    if not isinstance(defs,dict) or set(defs)!=REQUIRED:
        raise ProjectionRejected("UNSUPPORTED_DEFINITION_SET")
    if type(release["version"]) is not int or release["version"]<1 or (
        type(release["draftRevision"]) is not int
    ):
        raise ProjectionRejected("INVALID_RELEASE_VERSION")
    if not isinstance(release["manifestHash"],str) or sha(defs)!=release["manifestHash"]:
        raise ProjectionRejected("RELEASE_HASH_DRIFT")
    try:
        for rid,spec in defs.items():
            validate_definition(rid,spec)
        verify_refs(defs)
    except Rejected as e:
        raise ProjectionRejected("RELEASE_INVALID_"+e.code) from None
    if not isinstance(template,dict) or not isinstance(template.get("tables"),list) or (
        not isinstance(template.get("views"),list)
    ):
        raise ProjectionRejected("PACK_TEMPLATE_INVALID")
    model=defs["model.contracts"]
    if model["table"]!="contracts":
        raise ProjectionRejected("UNSUPPORTED_MODEL_TABLE")
    fields=model["fields"]
    allowed={"contract_no","title","amount_minor","status"}
    if {f["name"] for f in fields}!=allowed or any(
        {"contract_no":"string","title":"string","amount_minor":"integer",
         "status":"string"}[f["name"]]!=f["type"] for f in fields
    ):
        raise ProjectionRejected("UNSUPPORTED_MODEL_FIELDS")
    view=defs["view.contracts"]
    columns=view["columns"]
    if not columns or len(columns)!=len(set(columns)) or not set(columns)<=allowed:
        raise ProjectionRejected("UNSUPPORTED_VIEW_COLUMNS")
    # Trust boundary: discard any Saltcorn-provided pack edits. Output only
    # from pinned template and kernel verified published definitions.
    pack=copy.deepcopy(template)
    tables=[x for x in pack["tables"] if x.get("name")=="s1_contracts"]
    views=[x for x in pack["views"] if x.get("name")=="s1_contract_list"]
    if len(tables)!=1 or len(views)!=1:
        raise ProjectionRejected("PACK_TEMPLATE_MISSING")
    table=tables[0]
    table_fields={f["name"]:f for f in table["fields"]}
    if set(table_fields)!=allowed:
        raise ProjectionRejected("PACK_TEMPLATE_FIELDS")
    for f in fields:
        label=table_fields[f["name"]]
        if label["type"]!=FIELD_TYPES[f["type"]]:
            raise ProjectionRejected("PACK_TEMPLATE_TYPE_DRIFT")
        label["required"]=f["required"]
    views[0]["configuration"]["columns"]=[
        {"type":"Field","field_name":name,"state_field":"on"}
        for name in columns
    ]
    # Drop any unrelated object from template instead of passing arbitrary
    # executable triggers, plugins, user roles or views to Saltcorn.
    pack["tables"]=[table]
    pack["views"]=[views[0]]
    for key in ("plugins","pages","page_groups","roles","library","triggers",
                "tags","models","model_instances","event_logs","code_pages"):
        pack[key]=[]
    # The v1 fixture's 1:N s1_approvals table is omitted: its workflow is NOT
    # equivalent to B2 typed workflow and must not silently imply parity.
    return {
        "app":"app-a",
        "sourceVersion":release["version"],
        "manifestHash":release["manifestHash"],
        "projectionPackHash":hash_pack(pack),
        "projectionPack":pack,
        "projections":["model.contracts","view.contracts"],
        "notProjected":["form.contracts","workflow.approval","B4 code"]
    }


def check_compiled(package):
    if not isinstance(package,dict) or set(package)!={
        "app","sourceVersion","manifestHash","projectionPackHash",
        "projectionPack","projections","notProjected"
    } or package["app"]!="app-a":
        raise ProjectionRejected("PROJECTION_ENVELOPE_INVALID")
    if hash_pack(package["projectionPack"])!=package["projectionPackHash"]:
        raise ProjectionRejected("PROJECTION_TAMPERED")
    if package["projections"]!=["model.contracts","view.contracts"]:
        raise ProjectionRejected("PROJECTION_SCOPE_INVALID")
    return True


def assert_no_import_from_runtime(source):
    """Safety invariant for the projection updater: no reverse mutations."""
    if isinstance(source,dict) and any(key in source for key in (
        "reverseSync","writeAuthority","promoteSaltcornState"
    )):
        raise ProjectionRejected("REVERSE_SYNC_NOT_SUPPORTED")
    return True
