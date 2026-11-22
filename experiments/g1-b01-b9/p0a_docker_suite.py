"""G1 P0-A: real untrusted Docker plugin on SAME live B9 authority+native instance.

Reuses the actual B6 no-network, read-only, no-capabilities Docker runtime
and trusted stdout -> v3 B5 ToolBroker relay. The Docker process receives no
tool credential or authority/Native filesystem mount.

Not a production plugin lifecycle manager, not a full W/TC acceptance runner.
"""
from __future__ import annotations

import copy
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import re
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "g1-b01-b6"))
from plugin_isolation import DockerPlugin, complete_isolation


def run_suite(*, context, base, token_plugin, token_agent, authority_db,
              authority_config, native_db, native_page, native_physical,
              physical, http, make_mutation, check):
    image_id = os.environ.get("S1_B9_PINNED_DOCKER_IMAGE", "")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id):
        raise AssertionError("P0A_DOCKER_IMAGE_ID_MISSING")
    inspected = subprocess.run(
        ["docker", "image", "inspect", image_id, "--format", "{{.Id}}"],
        capture_output=True, text=True, timeout=15, check=True)
    if inspected.stdout.strip() != image_id:
        raise AssertionError("P0A_DOCKER_ACTUAL_IMAGE_DIFFERS")
    plugin = DockerPlugin(image_id, base, token_plugin, "app-a",
                          "p0a-integrated-docker")
    argv = plugin.docker_argv("/tmp/s1-b6-constraint-introspection")
    # This is an assertion on the exact trusted Docker invocation, not a
    # claim that inspecting argv alone proves kernel isolation.
    mandatory = {
        "--network=none", "--read-only", "--cap-drop=ALL",
        "--security-opt=no-new-privileges", "--user=65534:65534",
        "--pids-limit=32", "--memory=192m", "--cpus=1",
        "--pull=never",
    }
    check("P0A-16-pinned-real-Docker-and-deny-by-default-argv",
          mandatory.issubset(set(argv)) and
          image_id in argv and "--privileged" not in argv and
          all(secret not in " ".join(argv) for secret in (
              token_plugin, token_agent, str(authority_db),
              str(authority_config), str(native_db))) and
          "--mount" in argv and
          argv.count("--mount") == 1 and
          argv.count("--network=none") == 1,
          {"imageId":image_id, "noNetwork":True,"readOnly":True,
           "noHostDatabaseMount":True,"noSecretInDockerArgv":True})

    def isolated(app, tool, args):
        # Every invocation executes actual arbitrary Python in a NEW
        # Docker container. Trusted host gives only JSON request to the
        # stdout tool relay; no bearer goes into Docker, including env.
        return plugin.run({"app":app,"tool":tool,"args":args},
                          authority_db, authority_config)

    def agent(tool, args):
        return http(base,"app-a",tool,token_agent,args)

    def draft():
        status, body = agent("draft.read", {})
        if status != 200:
            raise AssertionError("P0A_DOCKER_AGENT_READ_INVALID")
        return body

    def view_command(snapshot, title, change_id):
        updated = copy.deepcopy(snapshot["resources"][
            "view.contracts"]["definition"])
        updated["title"] = title
        return make_mutation(snapshot, "view.contracts", updated, change_id)

    start = physical()
    if start["app-a"]["revision"] != 12 or (
            start["app-a"]["publishedVersion"] != 1):
        raise AssertionError("P0A_DOCKER_PREVIOUS_SUITE_NOT_SAME_INSTANCE")
    old_native = native_physical(native_db)
    observed = isolated("app-a", "draft.read", {})
    check("P0A-17-real-untrusted-Docker-process-isolated-and-reads-tools",
          complete_isolation(observed.probes) and
          observed.http_status == 200 and
          observed.result.get("appRevision") == 12 and
          observed.result.get("publishedVersion") == 1 and
          physical() == start,
          {"dockerUid":observed.probes.get("containerUid"),
           "dockerSocket":observed.probes.get("dockerSocket"),
           "hostSqliteRw":observed.probes.get("hostSqliteRwConnect"),
           "hostSqliteRead":observed.probes.get("hostDbFileRead"),
           "hostSecretRead":observed.probes.get("hostSentinelRead"),
           "outboundTcp":observed.probes.get("internetTcp"),
           "toolHTTP":observed.http_status,"physicalNoChange":True})

    # These tool calls all involve real Docker invocations on this Kernel,
    # and are checked against an independent physical SQL snapshot.
    original = draft()
    model_cmd = make_mutation(
        original, "model.contracts",
        original["resources"]["model.contracts"]["definition"],
        "p0a-docker-model-forbidden")
    denied = {
        "publish": isolated("app-a","app.publish",{"command":{}}),
        "code": isolated("app-a","code.publish",{
            "artifactHash":"0"*64,"expectedExtensionVersion":0}),
        "sql": isolated("app-a","sql.admin",{}),
        "model": isolated("app-a","metadata.upsert",{"command":model_cmd}),
    }
    check("P0A-18-real-Docker-plugin-privileged-tools-refused",
          all(r.http_status == 403 for r in denied.values()) and
          physical() == start,
          {"status":{k:v.http_status for k,v in denied.items()},
           "unauthorizedSqlReceiptDelta":0})

    cross = isolated("app-b","draft.read",{})
    injected = isolated("app-a","metadata.upsert",{
        "command":make_mutation(
            original,"view.contracts",
            original["resources"]["view.contracts"]["definition"],
            "p0a-docker-fake-root-role"),
        "actorId":"root","role":"administrator","appId":"app-b"})
    check("P0A-19-cross-app-and-authority-forgery-refused-inside-relay",
          cross.http_status == 403 and
          cross.result.get("error")=="PLUGIN_CROSS_APP_FORBIDDEN" and
          injected.http_status == 422 and
          injected.result.get("error")=="TOOL_ARGUMENTS_INVALID" and
          physical() == start,
          {"crossApp":cross.http_status,"forgedClaims":injected.http_status,
           "trustedIdentityFromGrant":True,"physicalUnchanged":True})

    # Actual successful mutation from the untrusted Docker plugin has the
    # exact same commit/receipt/audit path as Chromium + Agent + Linux UID P.
    first_cmd = view_command(
        draft(), "P0A-Docker-View-Approved",
        "p0a-docker-same-kernel-first")
    before_write=physical()
    write=isolated("app-a","metadata.upsert",{"command":first_cmd})
    after_write=physical()
    check("P0A-20-real-Docker-plugin-writes-only-governed-view",
          write.http_status == 200 and
          write.result.get("appRevision") == 13 and
          after_write["app-a"]["revision"] == 13 and
          after_write["app-a"]["receipts"] ==
              before_write["app-a"]["receipts"]+1 and
          len(after_write["app-a"]["events"]) ==
              len(before_write["app-a"]["events"])+1 and
          after_write["app-a"]["events"][-1]["actor"] ==
              "p0a-native-plugin" and
          after_write["app-a"]["resources"]["view.contracts"]["title"] ==
              "P0A-Docker-View-Approved" and
          after_write["app-a"]["publishedVersion"] == 1 and
          after_write["app-b"] == before_write["app-b"],
          {"DockerToolHTTP":write.http_status,
           "actorFromTrustedGrant":after_write["app-a"]["events"][-1]["actor"],
           "appRevision":after_write["app-a"]["revision"],
           "oneReceiptAndEvent":True})

    # Real Docker process and Agent race for the SAME old View title in
    # one B2 BEGIN IMMEDIATE authority transaction. Exactly one may win.
    snapshot = draft()
    docker_cmd = view_command(
        snapshot, "P0A-Docker-Race-Title", "p0a-docker-race")
    agent_cmd = view_command(
        snapshot, "P0A-Agent-Race-Title", "p0a-agent-docker-race")
    before_race=physical()
    with ThreadPoolExecutor(max_workers=2) as pool:
        docker_future=pool.submit(
            isolated,"app-a","metadata.upsert",{"command":docker_cmd})
        agent_future=pool.submit(
            agent,"metadata.upsert",{"command":agent_cmd})
        docker_race=docker_future.result()
        agent_race=agent_future.result()
    after_race=physical()
    winning_title = ("P0A-Docker-Race-Title" if docker_race.http_status==200
                     else "P0A-Agent-Race-Title")
    check("P0A-21-Agent-vs-real-Docker-plugin-race-single-winner",
          sorted((docker_race.http_status,agent_race[0])) == [200,409] and
          after_race["app-a"]["revision"] ==
              before_race["app-a"]["revision"]+1 and
          after_race["app-a"]["receipts"] ==
              before_race["app-a"]["receipts"]+1 and
          len(after_race["app-a"]["events"]) ==
              len(before_race["app-a"]["events"])+1 and
          after_race["app-a"]["resources"]["view.contracts"]["title"] ==
              winning_title and
          after_race["app-b"] == before_race["app-b"],
          {"DockerHTTP":docker_race.http_status,
           "AgentHTTP":agent_race[0], "physicalWinner":winning_title,
           "oneSQLReceipt":True})

    # The first Docker commit is still replayable after a newer writer won.
    # Neither another Actor nor a modified digest can steal its receipt.
    before_replay=physical()
    replay=isolated("app-a","metadata.upsert",{"command":first_cmd})
    other=agent("metadata.upsert",{"command":first_cmd})
    forged=copy.deepcopy(first_cmd)
    forged["definition"]["title"]="P0A-FORGED-DOCKER-REPLAY"
    altered=isolated("app-a","metadata.upsert",{"command":forged})
    check("P0A-22-real-Docker-idempotency-cross-subject-and-digest",
          replay.http_status == 200 and
          replay.result.get("replayed") is True and
          replay.result.get("appRevision") == 13 and
          other[0] == 409 and
          other[1].get("error") == "CHANGE_ID_REUSED" and
          altered.http_status == 409 and
          altered.result.get("error") == "CHANGE_ID_REUSED" and
          physical() == before_replay,
          {"oldChangeIdReplay":replay.http_status,
           "otherActor":other[0],"forgedDigest":altered.http_status,
           "physicalUnchanged":True})

    # Genuine Chromium old-form conflict AFTER real Docker has written.
    page=context.new_page()
    try:
        page.goto(base+"/editor/app-a",wait_until="domcontentloaded")
        page.wait_for_function(
            "() => document.getElementById('message').textContent.includes('已加载草稿')",
            timeout=12000)
        page.locator("#resource-id").fill("view.contracts")
        page.locator("#select").click()
        old_rev=int(page.locator("#revision").inner_text())
        if old_rev != after_race["app-a"]["revision"]:
            raise AssertionError("P0A_DOCKER_CHROMIUM_NOT_CURRENT")
        stale_form=json.loads(page.locator("#definition").input_value())
        stale_form["title"]="P0A-Human-Stale-After-Real-Container"
        page.locator("#definition").fill(
            json.dumps(stale_form,ensure_ascii=False))
        before_browser=physical()
        fresh_cmd=view_command(
            draft(),"P0A-Docker-Wins-Human-Stale",
            "p0a-docker-vs-actual-chromium")
        fresh=isolated("app-a","metadata.upsert",{"command":fresh_cmd})
        with page.expect_response(
            lambda r: r.request.method=="POST" and
                      r.url.endswith("/v2/apps/app-a/commands"),
            timeout=12000
        ) as wait:
            page.locator("#save").click()
        stale=wait.value
        page.wait_for_function(
            "() => document.getElementById('message').textContent.includes('409')",
            timeout=12000)
        after_browser=physical()
        check("P0A-23-real-Docker-before-stale-Chromium-409",
              fresh.http_status == 200 and
              stale.status == 409 and
              stale.json().get("error")=="APP_REVISION_CONFLICT" and
              after_browser["app-a"]["revision"] ==
                  before_browser["app-a"]["revision"]+1 and
              after_browser["app-a"]["receipts"] ==
                  before_browser["app-a"]["receipts"]+1 and
              len(after_browser["app-a"]["events"]) ==
                  len(before_browser["app-a"]["events"])+1 and
              after_browser["app-a"]["resources"]["view.contracts"]["title"] ==
                  "P0A-Docker-Wins-Human-Stale",
              {"DockerHTTP":fresh.http_status,"realChromiumHTTP":stale.status,
               "staleFormDidNotOverwrite":True,
               "physicalRevision":after_browser["app-a"]["revision"]})
    finally:
        page.close()

    native_page.reload(wait_until="domcontentloaded")
    end=physical()
    native_end=native_physical(native_db)
    check("P0A-24-combined-physical-oracle-Docker-not-published-v1",
          end["app-a"]["revision"] == start["app-a"]["revision"]+3 and
          end["app-a"]["receipts"] == start["app-a"]["receipts"]+3 and
          len(end["app-a"]["events"]) == len(start["app-a"]["events"])+3 and
          end["app-a"]["publishedVersion"] == 1 and
          end["app-a"]["releases"] == 2 and
          end["app-a"]["resourceHashesValid"] and
          end["app-a"]["manifestMatches"] and
          end["app-a"]["releaseHashesValid"] and
          end["app-b"] == start["app-b"] and
          native_end == old_native and
          "HT-2026-000001" in native_page.content(),
          {"appARevision":end["app-a"]["revision"],
           "authorizedCommits":3,
           "publishedVersion":1,
           "NativePhysicalSnapshotIdentical":True,
           "NativeHTMLUnpublishedDraftNotLeaked":True,
           "otherAppUnchanged":True})

    return {
        "checks":9, "actualDocker":True,
        "pluginTokenVisibleToContainer":False,
        "actualDockerOsCapabilities":"network-none,read-only,nonroot,no-new-privileges",
        "pluginInstallerOrRevocationProven":False,
        "nativeServerStillPublishedV1":True,
        "formalWOrTCFullPass":False,
        "modelCalls":0
    }
