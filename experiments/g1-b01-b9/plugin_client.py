"""P0-A first integrated three-writer probe (real independent Linux plugin UID).

The trusted CI controller passes a one-shot JSON request on stdin after
runuser changes UID. No bearer is placed in argv, env, source, or files.
This is NOT a production plugin installer or a Docker security boundary.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from urllib.parse import urlsplit


def probe(db_path, config_path):
    def open_file(path, flags):
        try:
            fd = os.open(path, flags | getattr(os, "O_NOFOLLOW", 0))
            os.close(fd)
            return "OPENED"
        except OSError:
            return "DENIED"

    def sql_write(path):
        try:
            with sqlite3.connect("file:" + path + "?mode=rw", uri=True) as conn:
                conn.execute("UPDATE apps SET revision=revision")
                conn.commit()
            return "UPDATED"
        except sqlite3.Error:
            return "DENIED"

    return {
        "uid": os.getuid(),
        "authorityRead": open_file(db_path, os.O_RDONLY),
        "authorityWrite": open_file(db_path, os.O_RDWR),
        "authoritySQLWrite": sql_write(db_path),
        "authorityConfigRead": open_file(config_path, os.O_RDONLY),
    }


def call_tool(data):
    base = data["base"]
    url = urlsplit(base)
    if (url.scheme != "http" or url.hostname != "127.0.0.1" or
            not url.port or url.path or url.query or url.fragment or
            url.username or url.password):
        raise ValueError("PLUGIN_TARGET_INVALID")
    if data["app"] not in {"app-a", "app-b"}:
        raise ValueError("PLUGIN_APP_INVALID")
    if data["tool"] not in {
            "draft.read", "metadata.upsert", "app.publish",
            "code.publish", "release.read"}:
        raise ValueError("PLUGIN_TOOL_INVALID")
    if not isinstance(data["token"], str) or len(data["token"]) < 24:
        raise ValueError("PLUGIN_GRANT_INVALID")
    body = json.dumps(data["args"], ensure_ascii=False).encode()
    request = Request(
        base + "/v3/apps/" + data["app"] + "/tools/" + data["tool"],
        data=body, method="POST", headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + data["token"],
        })
    try:
        with urlopen(request, timeout=12) as response:
            return {"uid": os.getuid(), "status": response.status,
                    "body": json.loads(response.read(65536))}
    except HTTPError as exc:
        return {"uid": os.getuid(), "status": exc.code,
                "body": json.loads(exc.read(65536))}


def process(data):
    if not isinstance(data, dict):
        raise ValueError("PLUGIN_REQUEST_INVALID")
    if data.get("kind") == "probe" and set(data) == {
            "kind", "authorityDb", "authorityConfig"}:
        return probe(data["authorityDb"], data["authorityConfig"])
    if data.get("kind") == "tool" and set(data) == {
            "kind", "base", "token", "app", "tool", "args"}:
        return call_tool(data)
    raise ValueError("PLUGIN_REQUEST_SHAPE_INVALID")


if __name__ == "__main__":
    # Zero raw request logging: stdin can contain a short-lived tool grant.
    result = process(json.load(sys.stdin))
    print("S1_P0A_PLUGIN|" + json.dumps(
        result, ensure_ascii=False, sort_keys=True), flush=True)
