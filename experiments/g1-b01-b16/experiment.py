#!/usr/bin/env python3
"""B16: falsify unmodified Saltcorn read-only Web feasibility using real UIDs.

Independent bounded probe, not a copy of the cumulative B11--B15 harness.
Synthetic contract fixture; no claim of B2 signed-source integration.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import pwd
import secrets
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

HERE = Path(__file__).resolve().parent
APPLY = "ailcapb16apply"
WEB = "ailcapb16web"
GROUP = "ailcapb16read"
ROUTE = "/view/s1_contract_list"


def run(argv, **kwargs):
    return subprocess.run(list(map(str, argv)), capture_output=True, text=True,
                          timeout=180, **kwargs)


def required(argv):
    result = run(argv)
    if result.returncode:
        raise RuntimeError(result.stderr[-1000:])
    return result.stdout


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@contextmanager
def fixture_directory():
    path = Path(tempfile.mkdtemp(prefix="s1-b16-probe-"))
    try:
        yield path
    finally:
        required(["sudo", "-n", "chown", "-R", f"{os.getuid()}:{os.getgid()}", path])
        shutil.rmtree(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    options = parser.parse_args()
    output = Path(options.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    logs = output.parent / "b16-logs"
    logs.mkdir(exist_ok=True)
    evidence = {"experiment": "S1_B16_NATIVE_WEB_APPLY_UID_READONLY",
                "formalG1Passed": False, "modelCalls": 0,
                "b15Integrated": False, "checks": [], "variants": {}}

    def check(name, passed, observed):
        item = {"id": name, "status": "PASS" if passed else "FAIL",
                "observed": observed}
        evidence["checks"].append(item)
        print(json.dumps(item), flush=True)
        if not passed:
            raise AssertionError(name)

    try:
        uids = {name: pwd.getpwnam(name).pw_uid for name in (APPLY, WEB)}
        check("B16-01-independent-nonroot-identities",
              len(set(uids.values())) == 2 and min(uids.values()) > 0, uids)
        evidence["saltcornVersion"] = required(["saltcorn", "--version"]).strip()
        with fixture_directory() as location:
            base = Path(location)
            base.chmod(0o755)
            stage = base / "source"
            stage.mkdir(mode=0o755)
            for source in (HERE / "worker.py",
                           HERE.parent / "platform-saltcorn/contract-pack.json",
                           HERE.parent / "platform-saltcorn/seed-contract.js"):
                shutil.copyfile(source, stage / source.name)
                (stage / source.name).chmod(0o644)
            dbdir, apphome, webhome = [base / n for n in ("derived", "apply-home", "web-home")]
            for directory, user in ((dbdir, APPLY), (apphome, APPLY), (webhome, WEB)):
                directory.mkdir(mode=0o750)
                required(["sudo", "-n", "chown", f"{user}:{GROUP}", directory])
            worker = stage / "worker.py"
            db = dbdir / "native.sqlite"
            secret = secrets.token_urlsafe(40)

            def prefix(user, action):
                return ["sudo", "-n", "runuser", "-u", user, "--",
                        sys.executable, str(worker), action]

            def env(user, database=db):
                return {"PATH": os.environ["PATH"],
                        "HOME": str(apphome if user == APPLY else webhome),
                        "SQLITE_FILEPATH": str(database),
                        "SALTCORN_NWORKERS": "1", "SALTCORN_SESSION_SECRET": secret}

            def native(user, args, database=db):
                result = run(prefix(user, "exec") + ["saltcorn"] + args,
                             input=json.dumps(env(user, database)) + "\n", cwd=stage)
                return result

            def probe(user, operation, path=db, **args):
                result = run(prefix(user, "probe"), input=json.dumps(
                    {"path": str(path), "operation": operation, **args}) + "\n", cwd=stage)
                if result.returncode:
                    raise RuntimeError(result.stderr[-1000:])
                return json.loads(result.stdout)

            def protect():
                required(["sudo", "-n", "chown", f"{APPLY}:{GROUP}", db])
                required(["sudo", "-n", "chmod", "0640", db])

            def physical_hash():
                # Controller uses independent read access, not a Web assertion.
                return required(["sudo", "-n", "sha256sum", db]).split()[0]

            def serve(label, user, flags, expected_title):
                logfile = logs / f"{label}.log"
                port = 3166
                with logfile.open("w") as stream:
                    proc = subprocess.Popen(prefix(user, "exec") + ["saltcorn", "serve",
                        "--host", "127.0.0.1", "--port", str(port), "--noscheduler", *flags],
                        cwd=stage, stdin=subprocess.PIPE, stdout=stream,
                        stderr=subprocess.STDOUT, text=True, start_new_session=True)
                proc.stdin.write(json.dumps(env(user)) + "\n")
                proc.stdin.close()
                result = {"uid": uids[user], "flags": flags, "httpStatus": None,
                          "businessVisible": False, "browserVisible": False}
                try:
                    deadline = time.monotonic() + 40
                    while time.monotonic() < deadline:
                        if proc.poll() is not None:
                            break
                        try:
                            with urlopen(f"http://127.0.0.1:{port}{ROUTE}", timeout=2) as response:
                                body = response.read().decode()
                                result["httpStatus"] = response.status
                                result["businessVisible"] = expected_title in body and "HT-2026-000001" in body
                                if result["businessVisible"]:
                                    from playwright.sync_api import sync_playwright
                                    with sync_playwright() as pw:
                                        browser = pw.chromium.launch()
                                        page = browser.new_page()
                                        page.goto(f"http://127.0.0.1:{port}{ROUTE}")
                                        text = page.locator("body").inner_text()
                                        result["browserVisible"] = expected_title in text and "HT-2026-000001" in text
                                        browser.close()
                                    break
                        except HTTPError as exc:
                            result["httpStatus"] = exc.code
                        except (OSError, URLError, TimeoutError):
                            pass
                        time.sleep(.2)
                    result["exitBeforeCleanup"] = proc.poll()
                finally:
                    # runuser and child CLI share this dedicated process group.
                    run(["sudo", "-n", "kill", "-TERM", "--", f"-{proc.pid}"])
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        run(["sudo", "-n", "kill", "-KILL", "--", f"-{proc.pid}"])
                        proc.wait(timeout=5)
                    raw = logfile.read_text(errors="replace").replace(secret, "[REDACTED]")
                    logfile.write_text(raw)
                    result["logSha256"] = sha(logfile)
                    result["readonlyError"] = "SQLITE_READONLY" in raw
                    result["cannotOpenError"] = "SQLITE_CANTOPEN" in raw
                    result["logTail"] = raw[-3500:]
                    evidence["variants"][label] = result
                    print(json.dumps({"variant": label, **result}), flush=True)
                return result

            for args in (["reset-schema", "-f"],
                         ["install-pack", "-f", str(stage / "contract-pack.json")],
                         ["create-user", "--admin", "--email", "b16@example.invalid",
                          "--password", secrets.token_urlsafe(36)],
                         ["run-js", "-f", str(stage / "seed-contract.js")]):
                result = native(APPLY, args)
                if result.returncode:
                    raise RuntimeError(result.stderr[-1500:] + result.stdout[-1500:])
            protect()
            check("B16-02-real-native-contract-fixture", probe(APPLY, "read")["value"] == [["S1 Platform Contract"]],
                  {"fixture": "synthetic native contract, not B2 signed projection"})
            baseline = serve("writable-control", APPLY, [], "S1 Platform Contract")
            check("B16-03-writable-native-browser-control",
                  baseline["businessVisible"] and baseline["browserVisible"], baseline)
            protect()
            # Remove baseline session artifacts before testing no writable Session.
            for suffix in ("-sessions.sqlite", "-sessions.sqlite-journal", "-sessions.sqlite-wal", "-sessions.sqlite-shm"):
                required(["sudo", "-n", "rm", "-f", str(db) + suffix])
            before = physical_hash()
            check("B16-04-web-read-native-sql", probe(WEB, "read")["ok"], probe(WEB, "read"))
            for number, op in enumerate(("write-open", "sql-update", "chmod", "unlink", "replace"), 5):
                args = {"title": "UNAUTHORIZED", "source": str(webhome / "replacement.tmp")}
                observation = probe(WEB, op, **args)
                denied = not observation["ok"] and (observation["errno"] in (1, 13) or
                          observation["sqliteCode"] == "SQLITE_READONLY")
                check(f"B16-{number:02d}-web-{op}-denied", denied, observation)
            cli = native(WEB, ["run-js", "-c",
                "await db.query(\"UPDATE s1_contracts SET title='CLI_UNAUTHORIZED'\");"])
            cli_log = (cli.stdout + cli.stderr).replace(secret, "[REDACTED]")
            (logs / "web-cli-write.log").write_text(cli_log)
            check("B16-10-real-native-cli-write-denied", cli.returncode != 0 and "SQLITE_READONLY" in cli_log,
                  {"exitCode": cli.returncode, "logTail": cli_log[-1200:]})
            strict = serve("readonly-default", WEB, [], "S1 Platform Contract")
            check("B16-11-readonly-default-outcome-classified",
                  (strict["businessVisible"] and strict["browserVisible"]) or
                  (not strict["businessVisible"] and (strict["readonlyError"] or strict["cannotOpenError"])), strict)
            check("B16-12-default-and-attacks-db-unchanged", physical_hash() == before,
                  {"beforeSha256": before, "afterSha256": physical_hash()})
            # The protected directory stays Apply-owned and not Web-writable.
            # Only the Session symlink target is in Web's writable home.
            session_target = webhome / "sessions.sqlite"
            session = probe(WEB, "session", path=session_target)
            required(["sudo", "-n", "ln", "-s", session_target, str(db) + "-sessions.sqlite"])
            check("B16-13-separate-session-writable", session["ok"], session)
            split = serve("readonly-nomigrate-split-session", WEB, ["--nomigrate"], "S1 Platform Contract")
            check("B16-14-split-session-outcome-classified",
                  (split["businessVisible"] and split["browserVisible"]) or
                  (not split["businessVisible"] and split["readonlyError"]), split)
            check("B16-15-split-session-db-unchanged", physical_hash() == before,
                  {"beforeSha256": before, "afterSha256": physical_hash()})
            applied = probe(APPLY, "sql-update", title="Apply UID controlled update")
            check("B16-16-apply-uid-retains-write", applied["ok"] and
                  probe(WEB, "read")["value"] == [["Apply UID controlled update"]], applied)
            after_apply = physical_hash()
            restarted = serve("readonly-after-apply-restart", WEB, ["--nomigrate"], "Apply UID controlled update")
            check("B16-17-restart-outcome-and-integrity",
                  physical_hash() == after_apply and
                  ((restarted["businessVisible"] and restarted["browserVisible"]) or
                   (not restarted["businessVisible"] and restarted["readonlyError"])), restarted)
            # Deliberately unsafe disposable copy: file mode alone is insufficient.
            unsafe = webhome / "unsafe-native.sqlite"
            required(["sudo", "-n", "cp", db, unsafe])
            required(["sudo", "-n", "chown", f"{APPLY}:{GROUP}", unsafe])
            required(["sudo", "-n", "chmod", "0640", unsafe])
            replaced = probe(WEB, "replace", path=unsafe, source=str(webhome / "unsafe-replacement.tmp"))
            check("B16-18-negative-control-writable-parent-replaces-readonly-file", replaced["ok"],
                  {"replacement": replaced, "meaning": "unsafe configuration reproduced, not security PASS"})
            evidence["unmodifiedReadonlyWebFeasible"] = bool(split["businessVisible"] and split["browserVisible"])
            evidence["conclusion"] = ("LIMITED_PUBLIC_LIST_READONLY_SUCCESS" if evidence["unmodifiedReadonlyWebFeasible"]
                                      else "UNMODIFIED_READONLY_WEB_STARTUP_BLOCKED")
    except Exception as exc:
        evidence["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        evidence["passCount"] = sum(c["status"] == "PASS" for c in evidence["checks"])
        evidence["checkCount"] = len(evidence["checks"])
        output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
