#!/usr/bin/env python3
"""Real native adaptation vs minimal public-snapshot rendering, bounded scope."""
import argparse
import hashlib
from html import escape
import json
import os
from pathlib import Path
import pwd
import secrets
import shutil
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "g1-b01-b16"))
from experiment import fixture_directory, required, run
from patch_native import ORIGINAL_SHA

APPLY, WEB, VIEW = "ailcapb16apply", "ailcapb16web", "ailcapb17view"
MANIFEST = "a" * 64
ROUTE = "/view/s1_contract_list"
HOSTILE = '<img src=x onerror="window.__b17_xss=1">'


def request(port, path=ROUTE, method="GET"):
    try:
        with urlopen(Request(f"http://127.0.0.1:{port}{path}", method=method), timeout=3) as response:
            return response.status, response.read().decode(), dict(response.headers)
    except HTTPError as exc:
        return exc.code, exc.read().decode(), dict(exc.headers)


def stop(proc):
    run(["sudo", "-n", "kill", "-TERM", "--", f"-{proc.pid}"])
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        run(["sudo", "-n", "kill", "-KILL", "--", f"-{proc.pid}"])
        proc.wait(timeout=5)


def browser(port, expected):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch()
        page = br.new_page()
        page.on("dialog", lambda dialog: dialog.dismiss())
        response = page.goto(f"http://127.0.0.1:{port}{ROUTE}")
        text = page.locator("body").inner_text()
        result = {"status": response.status, "contractVisible": "HT-2026-000001" in text,
                  "titleVisible": expected in text, "integerVisible": "100000001" in text,
                  "injectedImageCount": page.locator("img[onerror]").count(),
                  "scriptExecuted": page.evaluate("window.__b17_xss === 1"), "bodyText": text[:6000]}
        br.close()
        return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    opts = parser.parse_args()
    output = Path(opts.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    evidence = {"experiment": "S1_B17_READONLY_ROUTE_COMPARISON", "checks": [],
                "formalG1Passed": False, "modelCalls": 0, "b15SignedPublisherIntegrated": False,
                "sourceFreshnessEnforced": False, "nativePatchBudget": {"files": 1, "calls": 1}}

    def check(label, passed, observation):
        item = {"id": f"B17-{len(evidence['checks']) + 1:02d}-{label}",
                "status": "PASS" if passed else "FAIL", "observed": observation}
        evidence["checks"].append(item)
        print(json.dumps(item), flush=True)
        if not passed:
            raise AssertionError(label)

    try:
        uids = {name: pwd.getpwnam(name).pw_uid for name in (APPLY, WEB, VIEW)}
        check("three-independent-uids", len(set(uids.values())) == 3 and min(uids.values()) > 0, uids)
        global_root = Path(required(["npm", "root", "-g"]).strip())
        upstream = global_root / "@saltcorn/cli/node_modules/@saltcorn/server/dist/serve.js"
        backup = output.parent / "original-serve.js"
        processes = []
        patched = False
        with fixture_directory() as root:
            root.chmod(0o755)
            source = root / "source"
            source.mkdir(mode=0o755)
            for original in (HERE / "snapshot_web.py", HERE / "fixture_snapshot.py",
                             HERE.parent / "g1-b01-b16/worker.py",
                             HERE.parent / "platform-saltcorn/contract-pack.json",
                             HERE.parent / "platform-saltcorn/seed-contract.js"):
                shutil.copyfile(original, source / original.name)
                (source / original.name).chmod(0o644)
            native_dir, apply_home, web_home, public = [root / name for name in
                                                     ("native", "apply-home", "web-home", "published")]
            for directory, owner, group in ((native_dir, APPLY, "ailcapb16read"),
                                             (apply_home, APPLY, "ailcapb16read"),
                                             (web_home, WEB, "ailcapb16read"),
                                             (public, APPLY, "ailcapb17pub")):
                directory.mkdir(mode=0o750)
                required(["sudo", "-n", "chown", f"{owner}:{group}", directory])
            # New atomic snapshot files inherit the separate publication group.
            required(["sudo", "-n", "chmod", "2750", public])
            db, snapshot = native_dir / "native.sqlite", public / "published.sqlite"
            secret = secrets.token_urlsafe(40)

            def as_user(user, command):
                return ["sudo", "-n", "runuser", "-u", user, "--", *map(str, command)]

            def launch_env(user):
                return json.dumps({"PATH": os.environ["PATH"], "HOME": str(apply_home if user == APPLY else web_home),
                                   "SQLITE_FILEPATH": str(db), "SALTCORN_NWORKERS": "1",
                                   "SALTCORN_SESSION_SECRET": secret}) + "\n"

            def native(user, args):
                return run(as_user(user, [sys.executable, source / "worker.py", "exec", "saltcorn", *args]),
                           input=launch_env(user), cwd=source)

            def probe(user, operation, path=db, **kwargs):
                result = run(as_user(user, [sys.executable, source / "worker.py", "probe"]),
                             input=json.dumps({"operation": operation, "path": str(path), **kwargs}) + "\n")
                if result.returncode:
                    raise RuntimeError(result.stderr[-1000:])
                return json.loads(result.stdout)

            def native_hash():
                return required(["sudo", "-n", "sha256sum", db]).split()[0]

            def publish(head, manifest=MANIFEST):
                return required(as_user(APPLY, [sys.executable, source / "fixture_snapshot.py",
                    "--native-db", db, "--output", snapshot, "--head", str(head), "--manifest", manifest]))

            def start(label, command, port, stdin=None):
                logfile = output.parent / (label + ".log")
                with logfile.open("w") as stream:
                    proc = subprocess.Popen(command, cwd=source, stdin=subprocess.PIPE if stdin else subprocess.DEVNULL,
                                            stdout=stream, stderr=subprocess.STDOUT, text=True, start_new_session=True)
                processes.append(proc)
                if stdin:
                    proc.stdin.write(stdin)
                    proc.stdin.close()
                deadline = time.monotonic() + 35
                status = None
                while proc.poll() is None and time.monotonic() < deadline:
                    try:
                        status, body, _ = request(port)
                        if status == 200 and "HT-2026-000001" in body:
                            break
                    except (OSError, URLError, TimeoutError):
                        pass
                    time.sleep(.2)
                log = logfile.read_text(errors="replace").replace(secret, "[REDACTED]")
                observation = {"httpStatus": status, "exitCode": proc.poll(),
                               "readonlyError": "SQLITE_READONLY" in log,
                               "patchReached": "B17_RESEARCH_SKIP_OFFLINE_STORE_CONFIG" in log,
                               "logTail": log[-2500:]}
                return proc, observation

            try:
                for args in (["reset-schema", "-f"], ["install-pack", "-f", str(source / "contract-pack.json")],
                             ["create-user", "--admin", "--email", "b17@example.invalid", "--password", secrets.token_urlsafe(36)],
                             ["run-js", "-f", str(source / "seed-contract.js")]):
                    result = native(APPLY, args)
                    if result.returncode:
                        raise RuntimeError(result.stderr[-1500:])
                required(["sudo", "-n", "chown", f"{APPLY}:ailcapb16read", db])
                required(["sudo", "-n", "chmod", "0640", db])
                check("same-real-native-fixture", probe(WEB, "read")["value"] == [["S1 Platform Contract"]],
                      {"origin": "real Saltcorn pack, synthetic row, both routes share four fields"})
                baseline, baseline_observed = start("native-writable-control", as_user(APPLY,
                    [sys.executable, source / "worker.py", "exec", "saltcorn", "serve", "--host", "127.0.0.1",
                     "--port", "3167", "--noscheduler"]), 3167, launch_env(APPLY))
                seen = browser(3167, "S1 Platform Contract") if baseline_observed["httpStatus"] == 200 else {}
                check("writable-native-browser-control", seen.get("titleVisible", False), {**baseline_observed, "browser": seen})
                stop(baseline)
                processes.remove(baseline)
                for suffix in ("-sessions.sqlite", "-sessions.sqlite-journal", "-sessions.sqlite-wal", "-sessions.sqlite-shm"):
                    required(["sudo", "-n", "rm", "-f", str(db) + suffix])
                session = probe(WEB, "session", web_home / "sessions.sqlite")
                required(["sudo", "-n", "ln", "-s", web_home / "sessions.sqlite", str(db) + "-sessions.sqlite"])
                check("session-file-writable", session["ok"], session)
                patch_result = required(["sudo", "-n", sys.executable, HERE / "patch_native.py", "apply",
                                         "--file", upstream, "--backup", backup])
                patched = True
                check("one-hash-pinned-call-adapted", json.loads(patch_result)["changedCalls"] == 1, json.loads(patch_result))
                before = native_hash()
                args = as_user(WEB, [sys.executable, source / "worker.py", "exec", "saltcorn", "serve",
                                    "--host", "127.0.0.1", "--port", "3167", "--noscheduler", "--nomigrate"])
                proc_a, observed_a = start("native-adapted", args, 3167, launch_env(WEB))
                evidence["nativeAdaptation"] = observed_a
                check("native-adaptation-outcome-classified", observed_a["patchReached"] and
                      (observed_a["httpStatus"] == 200 or observed_a["readonlyError"]), observed_a)
                if observed_a["httpStatus"] == 200:
                    seen = browser(3167, "S1 Platform Contract")
                    evidence["nativeBrowser"] = seen
                    check("native-adapted-browser", seen["contractVisible"] and seen["titleVisible"], seen)
                check("native-db-unchanged", native_hash() == before, {"sha256": before})
                denied = probe(WEB, "sql-update", title="UNAUTHORIZED")
                check("adapted-web-still-cannot-write", not denied["ok"] and denied["sqliteCode"] == "SQLITE_READONLY", denied)
                stop(proc_a)
                processes.remove(proc_a)
                changed = probe(APPLY, "sql-update", title=HOSTILE)
                check("same-hostile-business-text", changed["ok"], {"title": HOSTILE})
                proc_a, observed_a2 = start("native-adapted-hostile", args, 3167, launch_env(WEB))
                evidence["nativeHostileStartup"] = observed_a2
                check("native-second-start-classified", observed_a2["patchReached"] and
                      (observed_a2["httpStatus"] == 200 or observed_a2["readonlyError"]), observed_a2)
                if observed_a2["httpStatus"] == 200:
                    seen = browser(3167, HOSTILE)
                    evidence["nativeHostileBrowser"] = seen
                    evidence["nativeLiteralTextFidelityPassed"] = seen["titleVisible"]
                    # Preserve literal-fidelity failure separately; continue the other candidate.
                    check("native-hostile-no-execution", not seen["scriptExecuted"] and seen["injectedImageCount"] == 0, seen)
                stop(proc_a)
                processes.remove(proc_a)
                restored = required(["sudo", "-n", sys.executable, HERE / "patch_native.py", "restore",
                                     "--file", upstream, "--backup", backup])
                patched = False
                check("upstream-restored", json.loads(restored)["sha256"] == ORIGINAL_SHA, json.loads(restored))
                publish(4)
                denied_native = probe(VIEW, "read")
                raw_open = run(as_user(VIEW, [sys.executable, "-c", "import os,sys; os.close(os.open(sys.argv[1],os.O_RDONLY))", db]))
                denied_native["rawOpenPermissionDenied"] = raw_open.returncode != 0 and "PermissionError" in raw_open.stderr
                check("snapshot-web-cannot-read-native-db", not denied_native["ok"] and denied_native["rawOpenPermissionDenied"], denied_native)
                for operation in ("write-open", "unlink"):
                    denied = probe(VIEW, operation, snapshot)
                    check("snapshot-web-" + operation + "-denied", not denied["ok"] and denied["errno"] == 13, denied)
                view_home = root / "view-home"
                view_home.mkdir(mode=0o700)
                required(["sudo", "-n", "chown", f"{VIEW}:ailcapb17pub", view_home])
                denied = probe(VIEW, "replace", snapshot, source=str(view_home / "replacement.tmp"))
                check("snapshot-web-replace-denied", not denied["ok"] and denied["errno"] == 13, denied)
                proc_b, observed_b = start("snapshot-web", as_user(VIEW, [sys.executable, source / "snapshot_web.py",
                    "--snapshot", snapshot, "--publisher-uid", str(uids[APPLY]), "--manifest", MANIFEST, "--port", "3168"]), 3168)
                evidence["snapshotStartup"] = observed_b
                check("snapshot-real-http", observed_b["httpStatus"] == 200, observed_b)
                seen = browser(3168, HOSTILE)
                check("snapshot-real-browser-escaped-text", seen["titleVisible"] and seen["contractVisible"] and
                      seen["integerVisible"] and not seen["scriptExecuted"] and seen["injectedImageCount"] == 0, seen)
                _, _, headers = request(3168)
                check("snapshot-route-and-method-boundary", request(3168, "/auth/login")[0] == 404 and
                      request(3168, ROUTE, "POST")[0] == 405 and "default-src 'none'" in headers["Content-Security-Policy"],
                      {"otherRoute": 404, "post": 405, "csp": headers["Content-Security-Policy"]})
                changed = probe(APPLY, "sql-update", title="Published generation two")
                code, body, _ = request(3168)
                check("last-published-not-source-freshness", changed["ok"] and code == 200 and escape(HOSTILE) in body and "Published generation two" not in body,
                      {"nativeChanged": True, "snapshotNotRepublished": True, "meaning": "last-published semantics; NOT B15 current-source guard"})
                publish(8)
                seen = browser(3168, "Published generation two")
                check("atomic-republish-visible-without-web-restart", seen["titleVisible"] and proc_b.poll() is None, seen)
                saved = public / "saved.sqlite"
                required(as_user(APPLY, ["mv", snapshot, saved]))
                check("missing-snapshot-fails-closed", request(3168)[0] == 503, {"httpStatus": 503})
                required(as_user(APPLY, ["mv", saved, snapshot]))
                required(as_user(APPLY, [sys.executable, "-c", "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); c.execute(\"UPDATE published_contracts SET title='CORRUPT'\"); c.commit(); c.close()", snapshot]))
                check("digest-tamper-fails-closed", request(3168)[0] == 503, {"httpStatus": 503})
                publish(8, "b" * 64)
                check("wrong-release-fails-closed", request(3168)[0] == 503, {"httpStatus": 503})
                publish(8)
                check("valid-republish-recovers", request(3168)[0] == 200, {"httpStatus": 200})
                evidence["nativeReadonlyListFeasible"] = observed_a["httpStatus"] == 200
                evidence["snapshotReadonlyListFeasible"] = observed_b["httpStatus"] == 200
            finally:
                for proc in processes:
                    stop(proc)
                if patched:
                    required(["sudo", "-n", sys.executable, HERE / "patch_native.py", "restore",
                              "--file", upstream, "--backup", backup])
    except Exception as exc:
        evidence["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        evidence["passCount"] = sum(x["status"] == "PASS" for x in evidence["checks"])
        output.write_text(json.dumps(evidence, indent=2) + "\n")


if __name__ == "__main__":
    main()
