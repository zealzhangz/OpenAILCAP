"""Deterministic, in-memory domain-model Spike; not a production database or runtime.

Two storage designs share the same *governed* command semantics so tests can isolate
representation trade-offs from concurrent-edit correctness. Python stdlib only.
"""
from __future__ import annotations

import copy
import hashlib
import json
import threading
from dataclasses import dataclass
from typing import Any


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


class ModelError(Exception):
    def __init__(self, code: str, message: str = "") -> None:
        self.code = code
        super().__init__(message or code)


class InjectedFailure(ModelError):
    def __init__(self) -> None:
        super().__init__("INJECTED_FAILURE", "Simulated failure before commit")


@dataclass(frozen=True)
class Snapshot:
    revision: int
    fingerprint: str
    resources: dict[str, dict[str, Any]]


@dataclass(frozen=True)
class Receipt:
    revision: int
    fingerprint: str
    merged: bool
    changed_ids: tuple[str, ...]


BASE_RESOURCES = {
    "page-contract-form": {
        "id": "page-contract-form", "domain": "ui", "refs": [],
        "data": {"title": "合同表单", "layout": {"columns": 2}},
    },
    "button-submit": {
        "id": "button-submit", "domain": "ui", "refs": ["page-contract-form"],
        "data": {"label": "提交", "style": {"background": "blue"}},
    },
    "rule-threshold": {
        "id": "rule-threshold", "domain": "workflow", "refs": ["page-contract-form"],
        "data": {"operator": ">", "amount": 1000000, "nextStep": "level2"},
    },
    "event-submit": {
        "id": "event-submit", "domain": "workflow", "refs": ["button-submit", "rule-threshold"],
        "data": {"trigger": "click"},
    },
    "code-number-generator": {
        "id": "code-number-generator", "domain": "code", "refs": [],
        "data": {"source": "return prefix + seq", "kind": "function"},
    },
    "plugin-contract": {
        "id": "plugin-contract", "domain": "plugin", "refs": [],
        "data": {"config": {"mode": "strict", "futureX": {"enabled": True, "vendor": {"key": "v1"}}}},
    },
}


def operation_set(resource: str, path: str, value: Any) -> dict[str, Any]:
    return {"op": "set", "id": resource, "path": path, "value": value}


def operation_delete(resource: str) -> dict[str, Any]:
    return {"op": "delete", "id": resource}


def operation_create(resource: dict[str, Any]) -> dict[str, Any]:
    return {"op": "create", "resource": copy.deepcopy(resource)}


def _get(obj: Any, segments: list[str]) -> Any:
    cur = obj
    for item in segments:
        if not isinstance(cur, dict) or item not in cur:
            return {"__missing_value__": True}
        cur = cur[item]
    return copy.deepcopy(cur)


def _set(obj: dict[str, Any], segments: list[str], value: Any) -> None:
    if not segments or segments[0] not in ("data", "refs"):
        raise ModelError("IMMUTABLE_FIELD", "Only data fields and whole refs lists are editable")
    if segments[0] == "refs" and len(segments) != 1:
        raise ModelError("INVALID_PATH", "refs must be replaced as one list")
    if segments[0] == "data" and len(segments) < 2:
        raise ModelError("INVALID_PATH", "Cannot replace an entire data object")
    current = obj
    for part in segments[:-1]:
        if not isinstance(current, dict) or part not in current or not isinstance(current[part], dict):
            raise ModelError("INVALID_PATH", "Path does not exist")
        current = current[part]
    if segments[-1] not in current:
        # This constrained experiment does not test adding arbitrary schema fields.
        raise ModelError("INVALID_PATH", "Unknown leaf path")
    current[segments[-1]] = copy.deepcopy(value)


def _validate(resources: dict[str, dict[str, Any]]) -> None:
    for identifier, resource in resources.items():
        if resource.get("id") != identifier or not isinstance(resource.get("domain"), str):
            raise ModelError("RESOURCE_IDENTITY", identifier)
        if not isinstance(resource.get("data"), dict):
            raise ModelError("INVALID_DATA", identifier)
        refs = resource.get("refs")
        if not isinstance(refs, list) or not all(isinstance(ref, str) for ref in refs):
            raise ModelError("INVALID_REFS", identifier)
        for ref in refs:
            if ref not in resources:
                raise ModelError("BROKEN_REFERENCE", f"{identifier} -> {ref}")


class Store:
    """Thread-safe, atomic in-memory publish. No durable crash/restart guarantee."""

    def __init__(self, design: str) -> None:
        if design not in ("A-unified-ir", "B-domain-manifest"):
            raise ValueError(design)
        self.design = design
        self._lock = threading.RLock()
        self._revision = 0
        self._raw = self._encode(copy.deepcopy(BASE_RESOURCES))
        self._history: dict[int, dict[str, dict[str, Any]]] = {0: copy.deepcopy(BASE_RESOURCES)}
        self._receipts: dict[str, tuple[str, Receipt]] = {}
        self.audit: list[dict[str, Any]] = []
        _validate(self.resources())

    def _encode(self, resources: dict[str, dict[str, Any]]) -> dict[str, Any]:
        if self.design == "A-unified-ir":
            return {"app_id": "app-contract-01", "resources": copy.deepcopy(resources)}
        domains: dict[str, dict[str, dict[str, Any]]] = {}
        manifest: dict[str, dict[str, str]] = {}
        for identifier, resource in sorted(resources.items()):
            domain = resource["domain"]
            domains.setdefault(domain, {})[identifier] = copy.deepcopy(resource)
            manifest[identifier] = {"domain": domain, "sha256": digest(resource)}
        return {"manifest": {"app_id": "app-contract-01", "resource_index": manifest}, "domains": domains}

    def _decode(self) -> dict[str, dict[str, Any]]:
        if self.design == "A-unified-ir":
            return copy.deepcopy(self._raw["resources"])
        resources: dict[str, dict[str, Any]] = {}
        for domain, entries in self._raw["domains"].items():
            for identifier, resource in entries.items():
                index = self._raw["manifest"]["resource_index"].get(identifier)
                if index != {"domain": domain, "sha256": digest(resource)}:
                    raise ModelError("MANIFEST_MISMATCH", identifier)
                if identifier in resources:
                    raise ModelError("DUPLICATE_RESOURCE", identifier)
                resources[identifier] = copy.deepcopy(resource)
        if set(resources) != set(self._raw["manifest"]["resource_index"]):
            raise ModelError("MANIFEST_MISMATCH", "Orphan index entries")
        return resources

    def resources(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return self._decode()

    def snapshot(self) -> Snapshot:
        with self._lock:
            res = self._decode()
            return Snapshot(self._revision, digest(res), res)

    def serialized_bytes(self) -> int:
        with self._lock:
            return len(canonical(self._raw).encode("utf-8"))

    def simulated_out_of_band_edit(self, identifier: str, path: str, value: Any) -> None:
        """Inject editor drift at SAME revision (deliberately bypassing the command API)."""
        with self._lock:
            res = self._decode()
            if identifier not in res:
                raise ModelError("MISSING_RESOURCE")
            _set(res[identifier], path.split("."), value)
            _validate(res)
            self._raw = self._encode(res)
            # intentionally do not increment revision or update history

    def reconcile_external_revision(self, *, actor: str) -> Receipt:
        """Explicitly adopt an out-of-band editor change as a fresh, tracked version.

        This is a recovery adapter for testing; production should route all editor
        writes through the governed command API instead of permitting this drift.
        """
        with self._lock:
            current = self._decode()
            _validate(current)
            tracked = self._history[self._revision]
            if current == tracked:
                raise ModelError("NO_DRIFT_TO_RECONCILE")
            self._revision += 1
            self._history[self._revision] = copy.deepcopy(current)
            receipt = Receipt(self._revision, digest(current), False, tuple(sorted(current)))
            self.audit.append({"event": "EXTERNAL_RECONCILE", "actor": actor,
                               "revision": self._revision})
            return receipt

    def apply(self, *, actor: str, change_id: str, base: Snapshot,
              operations: list[dict[str, Any]], fail_after: int | None = None) -> Receipt:
        """Governed command: stale-disjoint merge; stale-overlap reject; copy-on-write commit."""
        with self._lock:
            signature = digest({"actor": actor, "base_revision": base.revision,
                                "base_fingerprint": base.fingerprint, "operations": operations})
            if change_id in self._receipts:
                known_signature, known_receipt = self._receipts[change_id]
                if signature != known_signature:
                    raise ModelError("IDEMPOTENCY_REUSE", change_id)
                return known_receipt
            if not actor or not change_id:
                raise ModelError("INVALID_COMMAND")
            reference = self._history.get(base.revision)
            if reference is None or reference != base.resources or digest(reference) != base.fingerprint:
                raise ModelError("UNTRUSTED_BASELINE", "The supplied base is not a stored revision")
            current = self._decode()
            if base.revision == self._revision and base.fingerprint != digest(current):
                raise ModelError("SNAPSHOT_DRIFT", "Same revision, different stored content")
            if base.revision > self._revision:
                raise ModelError("FUTURE_REVISION")
            working = copy.deepcopy(current)
            changed_ids: set[str] = set()
            for pos, operation in enumerate(operations, 1):
                verb = operation.get("op")
                if verb == "set":
                    identifier = operation["id"]
                    if identifier not in base.resources or identifier not in current:
                        raise ModelError("MISSING_RESOURCE", identifier)
                    segments = operation["path"].split(".")
                    before = _get(base.resources[identifier], segments)
                    now = _get(current[identifier], segments)
                    desired = copy.deepcopy(operation["value"])
                    if before != now and now != desired:
                        raise ModelError("WRITE_CONFLICT", f"{identifier}:{operation['path']}")
                    _set(working[identifier], segments, desired)
                    changed_ids.add(identifier)
                elif verb == "delete":
                    identifier = operation["id"]
                    if identifier not in base.resources or identifier not in current:
                        raise ModelError("MISSING_RESOURCE", identifier)
                    if base.resources[identifier] != current[identifier]:
                        raise ModelError("WRITE_CONFLICT", f"delete:{identifier}")
                    del working[identifier]
                    changed_ids.add(identifier)
                elif verb == "create":
                    item = copy.deepcopy(operation["resource"])
                    identifier = item.get("id")
                    if not isinstance(identifier, str) or not identifier:
                        raise ModelError("RESOURCE_IDENTITY")
                    if identifier in base.resources or identifier in working:
                        raise ModelError("RESOURCE_EXISTS", identifier)
                    working[identifier] = item
                    changed_ids.add(identifier)
                else:
                    raise ModelError("UNKNOWN_OPERATION", str(verb))
                if fail_after is not None and pos == fail_after:
                    # Failure happens *before* publish; no partial state escapes.
                    raise InjectedFailure()
            _validate(working)
            self._revision += 1
            self._raw = self._encode(working)
            self._history[self._revision] = copy.deepcopy(working)
            receipt = Receipt(self._revision, digest(working), base.revision != self._revision - 1,
                              tuple(sorted(changed_ids)))
            self._receipts[change_id] = (signature, receipt)
            self.audit.append({"event": "APPLY", "actor": actor, "change_id": change_id,
                               "revision": self._revision, "changed_ids": sorted(changed_ids)})
            return receipt

    def rollback(self, revision: int, *, actor: str = "human") -> Receipt:
        with self._lock:
            target = self._history.get(revision)
            if target is None:
                raise ModelError("UNKNOWN_REVISION", str(revision))
            _validate(target)
            self._revision += 1  # monotonic revision, even when restoring old content
            self._raw = self._encode(copy.deepcopy(target))
            self._history[self._revision] = copy.deepcopy(target)
            receipt = Receipt(self._revision, digest(target), False, tuple(sorted(target)))
            self.audit.append({"event": "ROLLBACK", "actor": actor,
                               "restored_from": revision, "revision": self._revision})
            return receipt


def naive_full_replace_loss() -> bool:
    """Intentionally unsafe negative control: copy a stale full state over human edits."""
    original = copy.deepcopy(BASE_RESOURCES)
    stale = copy.deepcopy(original)
    original["button-submit"]["data"]["style"]["background"] = "gray"
    stale["button-submit"]["data"]["label"] = "送审"
    original = stale  # No precondition, no diff: loses the human edit.
    return original["button-submit"]["data"]["style"]["background"] == "blue"
