"""Minimal Linux UID launch shim: private environment via one-use stdin.

sudo/runuser may reset PATH, HOME and arbitrary Saltcorn settings. Passing
SQLITE_FILEPATH/SALTCORN_SESSION_SECRET in arguments of env leaks them through
/proc/cmdline. The trusted CI controller instead pipes whitelisted settings
into THIS process after the switch to the requested OS user, then execs the
real official Saltcorn CLI. Credentials never appear in process arguments.
This is a controlled CI launcher, not a production plugin isolation daemon.
"""
import json
import os
import sys


ALLOWED={"PATH","HOME","SQLITE_FILEPATH",
         "SALTCORN_SESSION_SECRET","SALTCORN_NWORKERS"}


def main():
    if len(sys.argv)<2:raise SystemExit("MISSING_COMMAND")
    line=sys.stdin.buffer.readline(8193)
    if not line or len(line)>8192:
        raise SystemExit("ENV_PAYLOAD_INVALID")
    env=json.loads(line)
    if not isinstance(env,dict) or set(env)!=ALLOWED or not all(
        isinstance(value,str) for value in env.values()
    ):
        raise SystemExit("ENV_KEYS_INVALID")
    if not env["SQLITE_FILEPATH"].startswith("/tmp/s1-b8-saltcorn-"):
        raise SystemExit("UNTRUSTED_DB_PATH")
    if len(env["SALTCORN_SESSION_SECRET"])<32:
        raise SystemExit("SESSION_SECRET_INVALID")
    os.umask(0o077)
    os.execvpe(sys.argv[1],sys.argv[1:],env)


if __name__=="__main__":
    main()
