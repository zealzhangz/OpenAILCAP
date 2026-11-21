"""B11 restricted native launcher for actual Saltcorn CLI under runtime Linux UID.

sudo/runuser resets environment, so the trusted CI coordinator provides
a one-use stdin JSON after the user switch. The only allowed native SQLite
path is an isolated DERIVED database under /tmp/s1-b11-project-..., NEVER the
authority path. This is a controlled experiment helper, not production
process sandboxing.
"""
import json
import os
import sys


ALLOWED={"PATH","HOME","SQLITE_FILEPATH",
         "SALTCORN_SESSION_SECRET","SALTCORN_NWORKERS"}


def main():
    if len(sys.argv)<2:raise SystemExit("NATIVE_NO_COMMAND")
    raw=sys.stdin.buffer.readline(8193)
    if len(raw)>8192:raise SystemExit("NATIVE_LAUNCH_ENV_TOO_BIG")
    args=json.loads(raw)
    if not isinstance(args,dict) or set(args)!=ALLOWED or not all(
        isinstance(v,str) and v for v in args.values()
    ):
        raise SystemExit("NATIVE_LAUNCH_INVALID_ENV")
    if (not args["SQLITE_FILEPATH"].startswith("/tmp/s1-b11-project-") or
        "/runtime-private/projection-" not in args["SQLITE_FILEPATH"] or
        not args["SQLITE_FILEPATH"].endswith(".sqlite")):
        raise SystemExit("NATIVE_LAUNCH_NOT_DERIVED_DB")
    if (not args["HOME"].startswith("/tmp/s1-b11-project-") or
        "/runtime-private" not in args["HOME"]):
        raise SystemExit("NATIVE_LAUNCH_INVALID_HOME")
    if len(args["SALTCORN_SESSION_SECRET"])<32:
        raise SystemExit("NATIVE_LAUNCH_SECRET_TOO_SHORT")
    os.umask(0o077)
    os.execvpe(sys.argv[1],sys.argv[1:],args)


if __name__=="__main__":main()
