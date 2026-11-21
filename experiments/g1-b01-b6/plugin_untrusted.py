"""INTENTIONALLY UNTRUSTED plugin fixture, executed only inside Docker.

This script is deliberately capable of arbitrary Python instructions. It
actively attempts host DB, secret, Docker daemon socket, writable mount and
external network access. Its JSON tool request is NOT trusted by the host.
"""
import json
import os
import socket
import sqlite3
from pathlib import Path


def try_open_rw(name):
    try:
        fd = os.open(name, os.O_RDWR)
        os.close(fd)
        return "OPENED"
    except (OSError, ValueError):
        return "DENIED"


def try_host_db(name):
    try:
        con=sqlite3.connect("file:"+name+"?mode=rw",uri=True,timeout=0.2)
        con.execute("SELECT name FROM sqlite_master LIMIT 1").fetchone()
        con.close()
        return "CONNECTED"
    except (OSError, sqlite3.Error, ValueError):
        return "DENIED"


def try_socket(name):
    sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
    sock.settimeout(0.8)
    try:
        sock.connect(name)
        return "CONNECTED"
    except (OSError, ValueError):
        return "DENIED"
    finally:
        sock.close()


def try_outbound():
    sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    sock.settimeout(0.8)
    try:
        sock.connect(("1.1.1.1",443))
        return "CONNECTED"
    except OSError:
        return "DENIED"
    finally:
        sock.close()


def main():
    # The payload and source are isolated to /workspace, which is read-only.
    payload=json.loads(Path("/workspace/request.json").read_text(encoding="utf-8"))
    db=payload["hostDbPath"]
    sentinel=payload["hostSentinelPath"]
    probes={
        "containerUid":os.getuid(),
        "dockerSocket":try_socket("/var/run/docker.sock"),
        "hostSqliteRwConnect":try_host_db(db),
        "hostDbFileWrite":try_open_rw(db),
        "hostSentinelRead":try_open_rw(sentinel),
        "containerPluginFileWrite":try_open_rw("/workspace/plugin_untrusted.py"),
        "internetTcp":try_outbound(),
        "hostSecretInherited":bool(os.getenv("S1_B6_HOST_SENTINEL")),
        "containerHasDatabaseLibrary":True
    }
    # The caller may deliberately craft hostile fields such as actorId,
    # administrator roles, app-b, SQL tools or code.publish.
    print(json.dumps({
        "protocol":"S1_B6_PLUGIN_REQUEST_V1",
        "request":payload["request"],
        "probes":probes
    },ensure_ascii=False,separators=(",",":")),flush=True)


if __name__=="__main__":
    main()
