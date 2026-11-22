"""P0-A same-live-B9 Kernel: full Native Pack diff, default deny & scoped approval.

Run AFTER real Chrome/Agent/third UID Plugin/actual Docker already changed
this SAME authority.sqlite. Native v1 remains live while approved v3 is
installed into a separate disposable staging SQLite. NO atomic hot cutover.
"""
from __future__ import annotations

import copy
import json
import os

from p0a_docker_suite import DockerPlugin
from pack_approval_gate import PackApprovalGate,PackGateDenied
from projector import compile_release,check_compiled,hash_pack


def run_suite(*, base,context, human_page, token_agent, token_runtime,
              token_publisher, token_plugin, authority_db,
              authority_config, http, broker, physical,
              native_physical, native_cmd, native_runtime, native_live_db,
              native_live_page, pack_v1, template, stage, make_mutation,check):

    def tool(token,command,args):
        return http(base,"app-a",command,token,args)

    def source():
        status,body=tool(token_runtime,"release.read",{})
        if status!=200:
            raise AssertionError("P0A_PACK_CURRENT_SOURCE_UNAVAILABLE")
        return body

    def agent_snapshot():
        status,body=tool(token_agent,"draft.read",{})
        if status!=200:
            raise AssertionError("P0A_PACK_AGENT_DRAFT_UNAVAILABLE")
        return body

    def denied(fn, expected):
        try:
            fn()
        except PackGateDenied as error:
            if error.code != expected:
                raise AssertionError(
                    "PACK_DENY_EXPECTED_"+expected+"_ACTUAL_"+error.code)
            return error.code
        raise AssertionError("PACK_UNAUTHORIZED_ACTION_WAS_ACCEPTED")

    start=physical()
    if start["app-a"]["revision"]!=15 or (
        start["app-a"]["publishedVersion"]!=1 or
        start["app-a"]["releases"]!=2):
        raise AssertionError("P0A_PACK_PREVIOUS_60_CHECKS_NOT_SAME_KERNEL")
    live_before=native_physical(native_live_db)
    # Live Native is actually v1. Bound to independent Native physical SQL,
    # not just to the trusted projector response object.
    if (live_before["viewColumns"] !=
        ["contract_no","amount_minor","status"] or
        "HT-2026-000001" not in native_live_page.content()):
        raise AssertionError("P0A_PACK_RUNNING_NATIVE_BASELINE_DRIFT")
    v1=source()
    compiled_v1=compile_release(v1,template)
    check_compiled(compiled_v1)
    if compiled_v1["projectionPack"]!=pack_v1:
        raise AssertionError("P0A_PACK_ACTUAL_V1_BASELINE_MISMATCH")

    # Same authority DB: Agent changes existing View columns, and the
    # already-authenticated Chromium human publishes the entire draft.
    draft=agent_snapshot()
    view=copy.deepcopy(draft["resources"]["view.contracts"]["definition"])
    view["columns"]=["contract_no","title","amount_minor","status"]
    cmd=make_mutation(draft,"view.contracts",view,
                      "p0a-pack-authorized-view-v3")
    status,edit=tool(token_agent,"metadata.upsert",{"command":cmd})
    human_page.locator("#reload").click()
    human_page.wait_for_function(
        "n => document.getElementById('revision').textContent === String(n)",
        arg=16,timeout=12000)
    with human_page.expect_response(
        lambda r:r.request.method=="POST" and
                 r.url.endswith("/v2/apps/app-a/publish"),timeout=15000
    ) as published:
        human_page.locator("#publish").click()
    publish_result=published.value
    human_page.wait_for_function(
        "() => document.getElementById('published-version').textContent === '3'",
        timeout=15000)
    pbody=publish_result.json()
    v3=source()
    after_publish=physical()
    check("P0A-25-current-B2-source-published-by-real-Chromium",
          status==200 and edit.get("appRevision")==16 and
          publish_result.status==200 and pbody.get("version")==3 and
          v3["version"]==3 and v3["manifestHash"]==
              after_publish["app-a"]["manifestHash"] and
          v3["draftRevision"]==16 and
          after_publish["app-a"]["revision"]==16 and
          after_publish["app-a"]["releases"]==3 and
          after_publish["app-a"]["publishedVersion"]==3 and
          after_publish["app-a"]["receipts"]==
              start["app-a"]["receipts"]+2 and
          after_publish["app-a"]["resourceHashesValid"] and
          after_publish["app-b"]==start["app-b"],
          {"agentHTTP":status,"humanPublishHTTP":publish_result.status,
           "sourceVersion":v3["version"],"appRevision":16,
           "nativeStillOriginalV1":native_physical(native_live_db)==live_before})

    compiled_v3=compile_release(v3,template)
    check_compiled(compiled_v3)
    approved_pack=compiled_v3["projectionPack"]
    gate=PackApprovalGate(source_reader=source,template=template,
                          baseline_pack=pack_v1)
    review=gate.review(approved_pack)
    approved_diff=review["diff"]
    # Compare actual JSON paths, including items added in Native View config,
    # not merely a custom whitelist of "important fields".
    check("P0A-26-complete-deterministic-immutable-Pack-diff",
          review["decision"]=="REVIEWABLE" and
          review["sourceVersion"]==3 and
          review["candidatePackHash"]==
              compiled_v3["projectionPackHash"] and
          review["candidatePackHash"]!=hash_pack(pack_v1) and
          len(approved_diff)>0 and
          any(e["path"].startswith("/views/0/configuration/columns/")
              for e in approved_diff) and
          len({e["path"] for e in approved_diff})==len(approved_diff) and
          gate.review(approved_pack)==review and
          native_physical(native_live_db)==live_before,
          {"sourceVersion":3,"baselineHash":review["baselinePackHash"],
           "approvedHash":review["candidatePackHash"],
           "changedJsonPaths":[e["path"] for e in approved_diff]})

    # Dangerous untrusted whole-Pack imports: investigate all differences
    # including unrelated tables/roles/plugins/triggers even when not part
    # of the supported B9 Model/View projection.
    evil=copy.deepcopy(approved_pack)
    evil.setdefault("tables",[]).append({
        "name":"unrelated_legacy_ledger","fields":[
            {"name":"secret","type":"String","required":False}]})
    evil.setdefault("roles",[]).append({"name":"administrator"})
    evil.setdefault("plugins",[]).append({"name":"arbitrary-os-plugin"})
    evil.setdefault("triggers",[]).append({"name":"outbound-exfiltration"})
    evil["customUnsafeDomain"]={"overwrite":"any"}
    review_evil=gate.review(evil)
    before_unauth=physical()
    rejected=denied(lambda:gate.propose(evil),
                     "UNVETTED_PACK_DEFAULT_DENY")
    stale_v2_pack=compile_release(
        {**v3, "version":2},template)["projectionPack"]
    # The same content but forged/older source version cannot be accepted
    # through caller-supplied version; only current B2 source is authoritative.
    check("P0A-27-full-diff-includes-unrelated-Pack-objects-default-deny",
          rejected=="UNVETTED_PACK_DEFAULT_DENY" and
          review_evil["decision"]=="REJECTED_UNTRUSTED_PACK" and
          all(any(e["path"].startswith("/"+prefix) for e in review_evil["diff"])
              for prefix in ("tables/1","roles/0","plugins/0",
                             "triggers/0","customUnsafeDomain")) and
          len(review_evil["diff"])>len(approved_diff) and
          stale_v2_pack==approved_pack and
          physical()==before_unauth and
          native_physical(native_live_db)==live_before,
          {"untrustedPackHTTP":"NOT_IN_TOOL_CAPABILITY",
           "dangerousDiffPaths":[x["path"] for x in review_evil["diff"]
                                 if any(x["path"].startswith("/"+pre)
                                        for pre in ("tables/1","roles/0",
                                                    "plugins/0","triggers/0",
                                                    "customUnsafeDomain"))],
           "decision":review_evil["decision"],
           "executedNativeCommands":0})

    plan=gate.propose(approved_pack)
    calls=[]
    def should_not_run(candidate):
        calls.append("CALLED")
        return {"unexpected":True}
    missing=denied(
        lambda:gate.apply(plan,None,approved_pack,
                          executor=should_not_run),
        "PACK_APPROVAL_REQUIRED")
    # There is intentionally NO tool grant for pack.install for Agent or P.
    docker_pack_client=DockerPlugin(
        os.environ["S1_B9_PINNED_DOCKER_IMAGE"],base,token_plugin,
        "app-a","p0a-pack-untrusted-container")
    actual_docker= docker_pack_client.run({
        "app":"app-a","tool":"pack.install",
        "args":{"candidatePackHash":review["candidatePackHash"],
                "actorId":"root","role":"administrator"}},
        authority_db,authority_config)
    plugin_attempt={"status":actual_docker.http_status,
                    "body":actual_docker.result,
                    "probes":actual_docker.probes}
    agent_attempt=tool(token_agent,"pack.install",{
        "candidatePackHash":review["candidatePackHash"]})
    check("P0A-28-default-deny-without-approval-and-unlisted-tools",
          missing=="PACK_APPROVAL_REQUIRED" and calls==[] and
          plugin_attempt["status"]==403 and
          plugin_attempt["body"].get("error")=="TOOL_NOT_GRANTED" and
          plugin_attempt["probes"].get("containerUid")==65534 and
          agent_attempt[0]==403 and
          physical()==before_unauth and
          native_physical(native_live_db)==live_before,
          {"noApproval":"DENIED","realDockerPlugin":plugin_attempt["status"],
           "agent":agent_attempt[0],"noNativeCliRun":True})

    no_priv=denied(
        lambda:gate.approve(plan,actor="b9-human-approved-release",
                            privileged=False),
        "PACK_PRIVILEGED_HUMAN_REQUIRED")
    fake_actor=denied(
        lambda:gate.approve(plan,actor="p0a-native-plugin",privileged=True),
        "PACK_PRIVILEGED_HUMAN_REQUIRED")
    approval=gate.approve(plan,actor="b9-human-approved-release",
                          privileged=True)
    forged=copy.deepcopy(approval)
    forged["signature"]="0"*64
    forged_denied=denied(
        lambda:gate.apply(plan,forged,approved_pack,
                          executor=should_not_run),
        "PACK_APPROVAL_FORGED")
    # Tamper one byte in proposal after receiving an otherwise valid receipt.
    modified=copy.deepcopy(approved_pack)
    modified["views"][0]["configuration"]["columns"][0]["field_name"] = "secret"
    wrong_pack=denied(
        lambda:gate.apply(plan,approval,modified,
                          executor=should_not_run),
        "PACK_SOURCE_MOVED_OR_CANDIDATE_CHANGED")
    check("P0A-29-human-scope-and-approval-integrity-reject-forgery",
          no_priv==fake_actor=="PACK_PRIVILEGED_HUMAN_REQUIRED" and
          forged_denied=="PACK_APPROVAL_FORGED" and
          wrong_pack=="PACK_SOURCE_MOVED_OR_CANDIDATE_CHANGED" and
          gate.used_count==0 and calls==[] and
          physical()==before_unauth,
          {"missingPrivilege":"DENIED","pluginApprover":"DENIED",
           "forgedSignature":"DENIED","modifiedPackAfterApproval":"DENIED",
           "nativeCliRun":False})

    # Real CLI (official @saltcorn/cli) is called ONLY through an admitted
    # one-shot approval, and ONLY for a separate disposable staging SQLite.
    staging_db=native_runtime/"p0a-approved-pack-v3-stage.sqlite"
    packfile=stage/"p0a-pack-admitted-v3.json"
    if staging_db.exists() or packfile.exists():
        raise AssertionError("P0A_PACK_STAGE_COLLISION")
    reset=native_cmd(["saltcorn","reset-schema","-f"],staging_db)
    if reset.returncode!=0:
        raise AssertionError("P0A_PACK_REAL_STAGE_RESET_FAILED")
    cli_calls=[]
    def installer(candidate):
        if packfile.exists():
            raise AssertionError("PACK_STAGING_PATH_ALREADY_USED")
        if candidate!=approved_pack:
            raise AssertionError("PACK_CANDIDATE_NOT_THE_APPROVED_BYTES")
        packfile.write_text(json.dumps(
            candidate,ensure_ascii=False,sort_keys=True,indent=2)+"\n",
            encoding="utf-8")
        packfile.chmod(0o444)
        if json.loads(packfile.read_text())!=candidate:
            raise AssertionError("PACK_STAGING_FILE_BYTES_CHANGED")
        actual=native_cmd(["saltcorn","install-pack","-f",packfile],
                          staging_db,timeout=150)
        cli_calls.append(actual.returncode)
        return {"actualNativeCliExit":actual.returncode,
                "disposableStagingOnly":True}
    approved_result=gate.apply(plan,approval,approved_pack,
                               executor=installer)
    seed=native_cmd(["saltcorn","run-js","-f",
                     stage/"platform-saltcorn"/"seed-contract.js"],
                    staging_db)
    staged_native=native_physical(staging_db)
    before_live=native_physical(native_live_db)
    check("P0A-30-approved-exact-Pack-installed-through-actual-Native-CLI",
          approved_result["decision"]=="STAGED_ONLY" and
          approved_result["sourceVersion"]==3 and
          approved_result["packHash"]==review["candidatePackHash"] and
          approved_result["diffCount"]==review["diffCount"] and
          approved_result["actor"]=="b9-human-approved-release" and
          cli_calls==[0] and seed.returncode==0 and
          staged_native["viewColumns"]==
             ["contract_no","title","amount_minor","status"] and
          len(staged_native["businessRows"])==1 and
          staged_native["businessRows"][0]["contract_no"]==
             "HT-2026-000001" and
          before_live==live_before and
          physical()==before_unauth and
          gate.used_count==1,
          {"actualSaltcornCli":cli_calls,"stagedColumns":
              staged_native["viewColumns"],"activeNativeUntouched":True,
           "sourceVersion":3,"diffCount":review["diffCount"],
           "approvedOneShot":True})

    repeated=denied(
        lambda:gate.apply(plan,approval,approved_pack,executor=should_not_run),
        "PACK_PLAN_UNRECOGNIZED")
    # A failure consumes approval and leaves the live Native unchanged.
    second=gate.propose(approved_pack)
    second_approval=gate.approve(
        second,actor="b9-human-approved-release",privileged=True)
    fail_injected=denied(
        lambda:gate.apply(second,second_approval,approved_pack,
                          executor=lambda x: (_ for _ in ()).throw(
                              PackGateDenied("PACK_STAGING_IO_FAILURE"))),
        "PACK_STAGING_IO_FAILURE")
    failed_replay=denied(
        lambda:gate.apply(second,second_approval,approved_pack,
                          executor=should_not_run),
        "PACK_PLAN_UNRECOGNIZED")
    check("P0A-31-approval-single-use-and-transaction-failure-no-live-effect",
          repeated=="PACK_PLAN_UNRECOGNIZED" and
          fail_injected=="PACK_STAGING_IO_FAILURE" and
          failed_replay=="PACK_PLAN_UNRECOGNIZED" and
          gate.used_count==2 and calls==[] and
          physical()==before_unauth and
          native_physical(native_live_db)==live_before,
          {"approvedReplay":"DENIED","failedInstallToken":"CONSUMED",
           "liveNativeNoChange":True,"physicalAuthorityNoChange":True})

    # After rollback, old v3 approval is inadmissible even though its Pack
    # file/compiled hash were valid. The isolated stage is disposable and
    # deliberately never promoted to active Native/route.
    stale_plan=gate.propose(approved_pack)
    stale_approval=gate.approve(
        stale_plan,actor="b9-human-approved-release",privileged=True)
    rollback=broker("app-a","app.rollback",token_publisher,{
        "command":{"changeId":"p0a-approved-stage-not-promoted-rollback",
                   "expectedPublishedVersion":3,"targetVersion":1}})
    stale=denied(
        lambda:gate.apply(stale_plan,stale_approval,approved_pack,
                          executor=should_not_run),
        "PACK_SOURCE_MOVED_OR_CANDIDATE_CHANGED")
    # Remove staged DB because source pointer has rolled back. This cleanup
    # runs as Native UID. No application or other process reads this stage.
    native_cmd(["/usr/bin/rm","-f",staging_db],native_live_db)
    gone=native_cmd(["/usr/bin/test","!","-e",staging_db],native_live_db)
    end=physical()
    native_live_page.reload(wait_until="domcontentloaded")
    check("P0A-32-rollback-invalidates-Pack-approval-no-stage-promotion",
          rollback["decision"]=="ROLLED_BACK" and
          rollback["version"]==1 and
          stale=="PACK_SOURCE_MOVED_OR_CANDIDATE_CHANGED" and
          calls==[] and gone.returncode==0 and
          end["app-a"]["revision"]==16 and
          end["app-a"]["receipts"]==start["app-a"]["receipts"]+3 and
          len(end["app-a"]["events"])==len(start["app-a"]["events"])+3 and
          end["app-a"]["releases"]==3 and
          end["app-a"]["publishedVersion"]==1 and
          end["app-a"]["resourceHashesValid"] and
          end["app-a"]["releaseHashesValid"] and
          end["app-a"]["manifestMatches"] and
          native_physical(native_live_db)==live_before and
          "HT-2026-000001" in native_live_page.content() and
          end["app-b"]==start["app-b"],
          {"draftRevision":end["app-a"]["revision"],
           "activeReleaseVersion":end["app-a"]["publishedVersion"],
           "immutableReleases":end["app-a"]["releases"],
           "staleApproval":"DENIED","stagingDBDeleted":True,
           "realSaltcornRunningV1":True,"crossAppUnchanged":True})
    return {
        "checks":8, "actualNativePackInstallCLI":True,
        "oneShotHostPrivilegedApproval":True,
        "allJsonPointerPackDiffReviewed":True,
        "sourceIsLiveB2ReleaseRead":True,
        "approvedStagingVersion":3,
        "activeNativeNeverHotSwitched":True,
        "productionHumanApprovalOrSSO":False,
        "trueNativeCLIBypassClosed":False,
        "g1Passed":False,
        "modelCalls":0
    }
