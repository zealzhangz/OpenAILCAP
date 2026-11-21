"""Untrusted OS-native plugin/CLI direct DB probes (not browser or host-root).

Runs under real distinct Linux UID via runuser. Tests read/write paths,
SQLite URI/SQL UPDATE, broker credential storage and /proc/<kernel>/environ.
Prints *only* outcome categories, never values or credentials.
"""
from __future__ import annotations
import argparse
import json
import os
import sqlite3
from pathlib import Path


def file_probe(path,flags):
    try:
        fd=os.open(path,flags)
        os.close(fd)
        return "ALLOWED"
    except OSError:
        return "DENIED"


def sqlite_probe(path,mode,write=False):
    try:
        db=sqlite3.connect(
            "file:"+str(path)+"?mode="+mode,
            uri=True,timeout=0.2)
        if write:
            # A real native SQLite direct UPDATE, not merely a connection
            # attempt. If it succeeds the trust boundary has failed.
            db.execute("UPDATE apps SET revision=revision WHERE app='app-a'")
            db.commit()
        else:
            db.execute("SELECT COUNT(*) FROM sqlite_master").fetchone()
        db.close()
        return "ALLOWED"
    except (sqlite3.Error,OSError,ValueError):
        return "DENIED"


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--db",required=True)
    p.add_argument("--config",required=True)
    p.add_argument("--kernel-pid",type=int,required=True)
    a=p.parse_args()
    probes={
        "uid":os.getuid(),
        "euid":os.geteuid(),
        "dbOpenRead":file_probe(a.db,os.O_RDONLY),
        "dbOpenWrite":file_probe(a.db,os.O_RDWR),
        "dbSqliteRead":sqlite_probe(a.db,"ro"),
        "dbSqliteDirectUpdate":sqlite_probe(a.db,"rw",write=True),
        "configRead":file_probe(a.config,os.O_RDONLY),
        "kernelEnvironRead":file_probe(
            "/proc/"+str(a.kernel_pid)+"/environ",os.O_RDONLY),
        "kernelFdDirectoryRead":"ALLOWED" if os.access(
            "/proc/"+str(a.kernel_pid)+"/fd",os.R_OK) else "DENIED",
    }
    print("S1_B7_DIRECT_PROBE|"+json.dumps(probes,sort_keys=True))


if __name__=="__main__":main()
