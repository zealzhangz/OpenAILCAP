"""Independent scenario/verifier fixtures. Engine is not allowed to modify assertions."""
from __future__ import annotations
import copy
import hashlib
from typing import Callable
from engine import Store, ModelError, operation_create as create, operation_delete as delete, operation_set as setval


def rejected(expected: str, action: Callable[[], object]) -> None:
    try:
        action()
    except ModelError as err:
        assert err.code == expected, f"Expected {expected}, got {err.code}: {err}"
    else:
        raise AssertionError(f"Expected {expected}, operation succeeded")


def c01(store: Store) -> None:
    base = store.snapshot()
    store.apply(actor="human", change_id="c01-human", base=base,
                operations=[setval("button-submit", "data.style.background", "gray")])
    receipt = store.apply(actor="ai", change_id="c01-agent", base=base,
                          operations=[setval("button-submit", "data.label", "送审")])
    item = store.resources()["button-submit"]["data"]
    assert item["style"]["background"] == "gray" and item["label"] == "送审"
    assert receipt.merged


def c02(store: Store) -> None:
    base = store.snapshot()
    store.apply(actor="human", change_id="c02-human", base=base,
                operations=[setval("button-submit", "data.label", "保存")])
    rejected("WRITE_CONFLICT", lambda: store.apply(actor="ai", change_id="c02-agent", base=base,
             operations=[setval("button-submit", "data.label", "送审")]))
    assert store.resources()["button-submit"]["data"]["label"] == "保存"


def c03(store: Store) -> None:
    base = store.snapshot()
    store.simulated_out_of_band_edit("button-submit", "data.style.background", "gray")
    assert store.snapshot().revision == base.revision
    assert store.snapshot().fingerprint != base.fingerprint
    rejected("SNAPSHOT_DRIFT", lambda: store.apply(actor="ai", change_id="c03-agent", base=base,
             operations=[setval("button-submit", "data.label", "送审")]))
    # A raw same-revision edit is not a trusted baseline. The editor's change
    # must first be adopted as a tracked revision (or always use the same write API).
    store.reconcile_external_revision(actor="human")
    fresh = store.snapshot()
    store.apply(actor="ai", change_id="c03-agent-retry", base=fresh,
                operations=[setval("button-submit", "data.label", "送审")])
    assert store.resources()["button-submit"]["data"]["style"]["background"] == "gray"


def c04(store: Store) -> None:
    base = store.snapshot()
    store.apply(actor="human", change_id="c04-delete", base=base,
                operations=[setval("event-submit", "refs", ["rule-threshold"]), delete("button-submit")])
    rejected("WRITE_CONFLICT", lambda: store.apply(actor="ai", change_id="c04-stale", base=base,
             operations=[setval("event-submit", "refs", ["button-submit", "rule-threshold"])]))
    fresh = store.snapshot()
    rejected("BROKEN_REFERENCE", lambda: store.apply(actor="ai", change_id="c04-new", base=fresh,
             operations=[setval("event-submit", "refs", ["button-submit"])]))
    assert "button-submit" not in store.resources()


def c05(store: Store) -> None:
    base = store.snapshot()
    store.apply(actor="human", change_id="c05-rule", base=base,
                operations=[setval("rule-threshold", "data.amount", 2000000)])
    store.apply(actor="ai", change_id="c05-layout", base=base,
                operations=[setval("page-contract-form", "data.layout.columns", 3)])
    now = store.resources()
    assert now["rule-threshold"]["data"]["amount"] == 2000000
    assert now["page-contract-form"]["data"]["layout"]["columns"] == 3


def c06(store: Store) -> None:
    base = store.snapshot()
    future = copy.deepcopy(base.resources["plugin-contract"]["data"]["config"]["futureX"])
    store.apply(actor="human", change_id="c06-mode", base=base,
                operations=[setval("plugin-contract", "data.config.mode", "relaxed")])
    store.apply(actor="ai", change_id="c06-button", base=base,
                operations=[setval("button-submit", "data.label", "提交合同")])
    now = store.resources()["plugin-contract"]["data"]["config"]
    assert now["mode"] == "relaxed" and now["futureX"] == future


def c07(store: Store) -> None:
    before = store.snapshot()
    ops = [setval("page-contract-form", "data.title", "合同登记"),
           setval("rule-threshold", "data.amount", 500000)]
    rejected("INJECTED_FAILURE", lambda: store.apply(actor="ai", change_id="c07-broken", base=before,
             operations=ops, fail_after=1))
    assert store.snapshot() == before, "Partial changes leaked"
    store.apply(actor="ai", change_id="c07-retry", base=before, operations=ops)
    assert store.snapshot().fingerprint != before.fingerprint
    store.rollback(before.revision)
    assert store.snapshot().fingerprint == before.fingerprint
    assert store.snapshot().revision > before.revision


def c08(store: Store) -> None:
    base = store.snapshot()
    ops = [create({"id": "event-notify", "domain": "workflow", "refs": ["rule-threshold"],
                   "data": {"trigger": "approved"}})]
    first = store.apply(actor="ai", change_id="c08-unique", base=base, operations=ops)
    again = store.apply(actor="ai", change_id="c08-unique", base=base, operations=ops)
    assert first == again
    assert store.snapshot().revision == first.revision
    assert list(store.resources()).count("event-notify") == 1
    rejected("IDEMPOTENCY_REUSE", lambda: store.apply(actor="ai", change_id="c08-unique", base=base,
             operations=[setval("button-submit", "data.label", "different")]))


def c09(store: Store) -> None:
    base = store.snapshot()
    new_source = "return prefix + '-' + str(seq).zfill(6)"
    store.apply(actor="human", change_id="c09-code", base=base,
                operations=[setval("code-number-generator", "data.source", new_source)])
    store.apply(actor="ai", change_id="c09-meta", base=base,
                operations=[setval("page-contract-form", "data.title", "合同档案")])
    final_source = store.resources()["code-number-generator"]["data"]["source"]
    assert hashlib.sha256(final_source.encode()).hexdigest() == hashlib.sha256(new_source.encode()).hexdigest()
    assert store.resources()["page-contract-form"]["data"]["title"] == "合同档案"


def c10(store: Store) -> None:
    base = store.snapshot()
    # All operations use the same API; no LLM client is imported or required.
    store.apply(actor="human", change_id="c10-human-1", base=base,
                operations=[create({"id": "input-description", "domain": "ui",
                                    "refs": ["page-contract-form"],
                                    "data": {"label": "合同说明", "required": False}})])
    intermediate = store.snapshot()
    store.apply(actor="human", change_id="c10-human-2", base=intermediate,
                operations=[setval("rule-threshold", "data.amount", 1500000)])
    store.apply(actor="ai", change_id="c10-agent", base=intermediate,
                operations=[setval("button-submit", "data.label", "保存合同")])
    now = store.resources()
    assert now["input-description"]["data"]["label"] == "合同说明"
    assert now["rule-threshold"]["data"]["amount"] == 1500000
    assert now["button-submit"]["data"]["label"] == "保存合同"


CASES: dict[str, Callable[[Store], None]] = {
    "C01-disjoint-same-resource": c01,
    "C02-overlap-conflict": c02,
    "C03-equal-revision-content-drift": c03,
    "C04-deleted-reference": c04,
    "C05-cross-domain-disjoint": c05,
    "C06-unknown-plugin-fields": c06,
    "C07-transaction-and-rollback": c07,
    "C08-idempotency": c08,
    "C09-human-code-preservation": c09,
    "C10-manual-no-ai-required": c10,
}
