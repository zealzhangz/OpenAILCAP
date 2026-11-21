"""Trusted fixture helper. No service endpoint; never a production sandbox."""
import json
import os
from pathlib import Path
import sqlite3
import sys


def probe(args):
    path = Path(args["path"])
    op = args["operation"]
    if op == "read":
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as db:
            return db.execute("SELECT title FROM s1_contracts ORDER BY id").fetchall()
    if op == "write-open":
        os.close(os.open(path, os.O_WRONLY))
    elif op == "sql-update":
        with sqlite3.connect(path) as db:
            db.execute("UPDATE s1_contracts SET title=?", (args["title"],))
    elif op == "chmod":
        path.chmod(0o660)
    elif op == "unlink":
        path.unlink()
    elif op == "replace":
        source = Path(args["source"])
        source.write_bytes(b"B16 replacement attack fixture")
        os.replace(source, path)
    elif op == "session":
        with sqlite3.connect(path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS b16_probe(value TEXT)")
            db.execute("INSERT INTO b16_probe VALUES ('session write allowed')")
    elif op != "read":
        raise ValueError("unknown operation")
    return True


def main():
    args = json.loads(sys.stdin.buffer.readline(16385))
    if sys.argv[1] == "exec":
        allowed = {"PATH", "HOME", "SQLITE_FILEPATH", "SALTCORN_NWORKERS",
                   "SALTCORN_SESSION_SECRET"}
        if set(args) != allowed or not all(isinstance(v, str) for v in args.values()):
            raise ValueError("invalid environment")
        os.umask(0o077)
        os.execvpe(sys.argv[2], sys.argv[2:], args)
    else:
        try:
            value = probe(args)
            result = {"ok": True, "value": value, "uid": os.getuid()}
        except (OSError, sqlite3.Error) as exc:
            result = {"ok": False, "error": type(exc).__name__,
                      "errno": getattr(exc, "errno", None),
                      "sqliteCode": getattr(exc, "sqlite_errorname", None),
                      "message": str(exc), "uid": os.getuid()}
        print(json.dumps(result))


if __name__ == "__main__":
    main()
