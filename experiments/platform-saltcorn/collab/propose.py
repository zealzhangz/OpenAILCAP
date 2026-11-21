#!/usr/bin/env python3
"""One REAL optional DeepSeek patch proposal after a real Chromium human save.

The LLM ONLY sees a read-only physical SQLite-backed snapshot and a fixed
typed function. It cannot edit Saltcorn, write code, or mint credentials.
Default is a deterministic NON-AI native platform preflight.
"""
import argparse
import json
import os
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError

MODEL="deepseek-flash"
API="https://api.deepseek.com/chat/completions"
TARGET="AI Reviewed Status"
FIRST="Human First Saved"

def validate_patch(p,snapshot):
    if not isinstance(p,dict) or set(p)!={
            "field","expected_title","expected_status","new_label"}:
        raise RuntimeError("AGENT_PATCH_SCHEMA_INVALID")
    if p["field"]!="status":
        raise RuntimeError("AGENT_PATCH_CANNOT_CHANGE_HUMAN_TITLE")
    if p["expected_title"]!=snapshot["title_label"] or \
       p["expected_status"]!=snapshot["status_label"]:
        raise RuntimeError("AGENT_DID_NOT_GROUND_ON_REAL_NATIVE_SNAPSHOT")
    if p["new_label"]!=TARGET:
        raise RuntimeError("AGENT_PATCH_DEVIATED_FROM_REQUEST")
    if any(not isinstance(x,str) or not 1<=len(x)<=80 for x in p.values()):
        raise RuntimeError("AGENT_PATCH_INVALID_TEXT")
    return p

def propose(snapshot,live):
    if snapshot["title_label"]!=FIRST or snapshot["status_label"]!="Status":
        raise RuntimeError("REAL_HUMAN_CHANGE_NOT_YET_CONFIRMED")
    if not live:
        return {
          "patch":{"field":"status","expected_title":snapshot["title_label"],
                   "expected_status":snapshot["status_label"],
                   "new_label":TARGET},
          "model_inference_executed":False,
          "source":"REVIEWED_DETERMINISTIC_PLATFORM_PREFLIGHT_NOT_AI"
        }
    key=os.getenv("DEEPSEEK_KEY")
    if not key:
        raise RuntimeError("DEEPSEEK_KEY_NOT_AVAILABLE")
    system=("你是受限的 Saltcorn 低代码配置修改规划器。你只能调用 propose_native_field_patch 函数一次，"
            "仅允许修改 status 字段的显示标签，不得修改人工刚设置的 title 显示标签。"
            "expected_title 和 expected_status 必须严格取自当前真实应用快照，不可猜测。"
            "不能调用数据库、Shell、运行 JS、批准合同或访问密钥。")
    user=json.dumps({
      "user_request":"保留人工最新设置的 title 标签不变，把 status 字段显示标签调整为 AI Reviewed Status。",
      "real_saltcorn_native_field_snapshot":{
        "title_label":snapshot["title_label"],
        "status_label":snapshot["status_label"]},
      "allowed_target_field":"status",
      "required_new_label":TARGET
    },ensure_ascii=False)
    tool={"type":"function","function":{
      "name":"propose_native_field_patch",
      "description":"Propose a single allowlisted label edit, grounded to the real Saltcorn field snapshot",
      "parameters":{
        "type":"object","additionalProperties":False,
        "required":["field","expected_title","expected_status","new_label"],
        "properties":{
          "field":{"type":"string","enum":["status"]},
          "expected_title":{"type":"string"},
          "expected_status":{"type":"string"},
          "new_label":{"type":"string"}
        }
      }}}
    payload={
      "model":MODEL,
      "messages":[{"role":"system","content":system},{"role":"user","content":user}],
      "tools":[tool],"tool_choice":"required",
      "thinking":{"type":"disabled"},"temperature":0,
      "max_tokens":200,"stream":False
    }
    request=Request(API,method="POST",
          headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"},
          data=json.dumps(payload,ensure_ascii=False).encode("utf-8"))
    try:
        with urlopen(request,timeout=35) as response:
            result=json.load(response)
    except HTTPError as e:
        raise RuntimeError("DEEPSEEK_HTTP_"+str(e.code)) from None
    except Exception:
        raise RuntimeError("DEEPSEEK_NETWORK_OR_RESPONSE_ERROR") from None
    choices=result.get("choices") or []
    calls=choices[0].get("message",{}).get("tool_calls",[]) if choices else []
    if len(calls)!=1 or calls[0].get("function",{}).get("name")!="propose_native_field_patch":
        raise RuntimeError("DEEPSEEK_TOOL_CONTRACT_NOT_RESPECTED")
    try:
        args=json.loads(calls[0]["function"]["arguments"])
    except (ValueError,TypeError,KeyError):
        raise RuntimeError("DEEPSEEK_INVALID_TOOL_ARGS") from None
    usage=result.get("usage") if isinstance(result.get("usage"),dict) else {}
    return {
      "patch":validate_patch(args,snapshot),
      "model_inference_executed":True,
      "model":MODEL,
      "model_calls":1,
      "function_calls":1,
      "usage_tokens":{k:usage[k] for k in
        ("prompt_tokens","completion_tokens","total_tokens")
        if isinstance(usage.get(k),int)},
      "provider_response_id_present":bool(result.get("id"))
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--human-snapshot",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--live",action="store_true")
    a=p.parse_args()
    human=json.loads(Path(a.human_snapshot).read_text(encoding="utf-8"))
    if human.get("phase")!="first" or human.get("result")!="PASS" or \
       not human.get("real_native_saltcorn_ui"):
        raise RuntimeError("NO_VERIFIED_REAL_HUMAN_BROWSER_EDIT")
    snapshot=human["snapshot"]
    result=propose(snapshot,a.live)
    validate_patch(result["patch"],snapshot)
    result["original_native_snapshot"]={
      "title":snapshot["title_label"],"status":snapshot["status_label"]}
    result["research_scope"]={
      "AI_generated_code":False,
      "model_has_write_tools":False,
      "actual_approval_for_mutation":"Trusted research controller only",
      "real_browser_was_used_before_model":True,
      "native_editor_side_CAS_added":False
    }
    Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",
                              encoding="utf-8")
    print("S1_COLLAB_PROPOSAL|"+json.dumps({
      "inference":result["model_inference_executed"],"model":result.get("model"),
      "field":result["patch"]["field"],
      "observed_human_title":result["patch"]["expected_title"],
      "observed_status":result["patch"]["expected_status"],
      "proposed_label":result["patch"]["new_label"],
      "tokens":result.get("usage_tokens",{})
    },ensure_ascii=False),flush=True)

if __name__=="__main__":
    main()
