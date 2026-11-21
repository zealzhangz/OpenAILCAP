#!/usr/bin/env python3
"""Bounded HTTP mutation tool for deterministic agent/plugin processes.

No model call. No database access. Bearer is furnished by trusted test host.
For plugin, the manifest is a client-side contract; authoritative field permission
is independently enforced by the C1 server's Principal.fields.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def call(method, url, token, payload=None):
    headers = {"Authorization": "Bearer " + token}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(url, method=method, headers=headers, data=data)
    try:
        with urlopen(req, timeout=10) as res:
            return res.status, json.load(res)
    except HTTPError as exc:
        return exc.code, json.loads(exc.read())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--caller", choices=("agent", "plugin"), required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--app", default="app-a")
    parser.add_argument("--resource", default="field.title")
    parser.add_argument("--field", choices=("label", "status"), default="status")
    parser.add_argument("--value", required=True)
    parser.add_argument("--change-id", required=True)
    parser.add_argument("--base-revision", type=int)
    parser.add_argument("--base-hash")
    parser.add_argument("--manifest", default=str(Path(__file__).with_name("plugin_manifest.json")))
    args = parser.parse_args()
    token_name = "B1_AGENT_TOKEN" if args.caller == "agent" else "B1_PLUGIN_TOKEN"
    token = os.environ.get(token_name)
    if not token:
        raise SystemExit("NO_AUTHORIZED_TOOL_TOKEN")
    if args.caller == "plugin":
        manifest = json.loads(Path(args.manifest).read_text())
        if (manifest.get("name") != "status-helper" or
            "resource.patch" not in manifest["capabilities"] or
            args.app != manifest["appId"] or
            args.resource not in manifest["resources"] or
            args.field not in manifest["fields"]):
            raise SystemExit("PLUGIN_MANIFEST_DENIED")
    endpoint = args.base + "/v1/apps/" + args.app + "/resources/" + args.resource
    status, snapshot = call("GET", endpoint, token)
    if status != 200:
        print(json.dumps({"caller": args.caller, "status": status, "result": snapshot}))
        return 0
    change = {
        "changeId": args.change_id,
        "resourceId": snapshot["resourceId"],
        "expectedRevision": snapshot["revision"] if args.base_revision is None else args.base_revision,
        "baseContentHash": snapshot["contentHash"] if args.base_hash is None else args.base_hash,
        "operations": [{"op": "replace", "path": "/" + args.field, "value": args.value}]
    }
    status, result = call(
        "POST", args.base + "/v1/apps/" + args.app + "/changes", token, change
    )
    print(json.dumps({"caller": args.caller, "status": status,
                      "result": result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
