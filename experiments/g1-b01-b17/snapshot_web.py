"""Bounded public-list renderer for B15-shaped atomic snapshots.

Trusts the local Publisher UID and pinned manifest, NOT a self-hash as a
signature. Does not check B2 freshness. Research HTTP server, not production.
"""
import argparse
from contextlib import closing
import hashlib
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import sqlite3
import stat

ROUTE = "/view/s1_contract_list"
MAX_BYTES = 1024 * 1024
MAX_ROWS = 256
FIELDS = ["contract_no", "title", "amount_minor", "status"]


class SnapshotRejected(Exception):
    pass


def rows_digest(rows):
    canonical = json.dumps(sorted(rows, key=lambda r: r["contract_no"]),
                           ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def load_snapshot(path, publisher_uid, manifest):
    """Read ONE file descriptor into bounded memory, so a swap cannot mix files.

    Atomic Publisher replacement is required; in-place writes are unsupported.
    Parent path comes from the trusted controller and cannot be Web-writable.
    """
    try:
        path = Path(path)
        parent = path.parent.lstat()
        if not stat.S_ISDIR(parent.st_mode) or parent.st_uid != publisher_uid or parent.st_mode & 0o022:
            raise SnapshotRejected("PARENT_POLICY")
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            info = os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != publisher_uid or
                    info.st_mode & 0o022 or info.st_nlink > 1 or
                    not 0 < info.st_size <= MAX_BYTES):
                raise SnapshotRejected("FILE_POLICY")
            with os.fdopen(fd, "rb", closefd=False) as handle:
                payload = handle.read(MAX_BYTES + 1)
            if len(payload) != info.st_size or len(payload) > MAX_BYTES:
                raise SnapshotRejected("SIZE")
        finally:
            os.close(fd)
        with closing(sqlite3.connect(":memory:")) as db:
            db.deserialize(payload)
            db.execute("PRAGMA query_only=ON")
            db.execute("PRAGMA trusted_schema=OFF")
            db.row_factory = sqlite3.Row
            objects = list(db.execute("SELECT name,type FROM sqlite_master"))
            if ({r["name"] for r in objects if r["type"] == "table"} !=
                    {"published_contracts", "published_state"} or
                    any(r["type"] in {"view", "trigger"} for r in objects)):
                raise SnapshotRejected("SCHEMA")
            for table, expected in (("published_contracts", FIELDS),
                                     ("published_state", ["head", "rows_digest", "manifest_hash"])):
                if [r["name"] for r in db.execute(f"PRAGMA table_info({table})")] != expected:
                    raise SnapshotRejected("COLUMNS")
            states = db.execute("SELECT * FROM published_state LIMIT 2").fetchall()
            if (len(states) != 1 or states[0]["manifest_hash"] != manifest or
                    type(states[0]["head"]) is not int or states[0]["head"] < 0):
                raise SnapshotRejected("STATE")
            rows = [dict(r) for r in db.execute(
                "SELECT contract_no,title,amount_minor,status FROM published_contracts "
                "ORDER BY contract_no LIMIT ?", (MAX_ROWS + 1,))]
            if len(rows) > MAX_ROWS:
                raise SnapshotRejected("ROW_LIMIT")
            for row in rows:
                if any(type(row[key]) is not str or len(row[key]) > 4096
                       for key in ("contract_no", "title", "status")):
                    raise SnapshotRejected("TEXT")
                if type(row["amount_minor"]) is not int or not 0 <= row["amount_minor"] <= 2**53 - 1:
                    raise SnapshotRejected("AMOUNT")
            if len({r["contract_no"] for r in rows}) != len(rows):
                raise SnapshotRejected("DUPLICATES")
            if rows_digest(rows) != states[0]["rows_digest"]:
                raise SnapshotRejected("DIGEST")
            return {"head": states[0]["head"], "rows": rows}
    except (OSError, sqlite3.Error, ValueError, TypeError, OverflowError) as exc:
        raise SnapshotRejected("UNAVAILABLE") from exc


def render(snapshot):
    cells = "".join("<tr>" + "".join("<td>" + escape(str(row[key]), quote=True) + "</td>"
                                    for key in FIELDS) + "</tr>" for row in snapshot["rows"])
    return ("<!doctype html><html lang=\"en\"><meta charset=\"utf-8\">"
            "<title>Contracts</title><body><h1>Contracts</h1><table><thead><tr>"
            "<th>Contract Number</th><th>Title</th><th>Amount in CNY cents</th><th>Status</th>"
            "</tr></thead><tbody>" + cells + "</tbody></table></body></html>").encode()


def server(config):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, code, body):
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path != ROUTE:
                return self.reply(404, b"Not found")
            try:
                body = render(load_snapshot(config.snapshot, config.publisher_uid, config.manifest))
            except SnapshotRejected:
                return self.reply(503, b"Published snapshot unavailable")
            self.reply(200, body)

        def do_POST(self):
            self.reply(405, b"Method not allowed")

        do_PUT = do_DELETE = do_PATCH = do_POST
    return ThreadingHTTPServer(("127.0.0.1", config.port), Handler)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--publisher-uid", type=int, required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--port", type=int, default=3168)
    args = parser.parse_args()
    if args.publisher_uid == os.getuid() or not re.fullmatch(r"[0-9a-f]{64}", args.manifest):
        raise SystemExit("independent Publisher UID and pinned manifest required")
    with server(args) as http:
        print(json.dumps({"uid": os.getuid(), "port": http.server_port}), flush=True)
        http.serve_forever()


if __name__ == "__main__":
    main()
