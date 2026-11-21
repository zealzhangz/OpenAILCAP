#!/usr/bin/env python3
"""ONE optional real DeepSeek response selecting CONFIG/CODE/HYBRID for six cases.

Frozen expected_mode and fixture are NEVER in the model's prompt.
Only sanitized mode choices / token counts are published. NEVER retries model.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

API="https://api.deepseek.com/chat/completions"
MODEL="deepseek-flash"
VALID={"CONFIG","CODE","HYBRID"}

def select(spec, use_model):
    tasks=[{"id":x["id"],"requirement":x["requirement"]} for x in spec["cases"]]
    if not use_model:
        # Deterministic sealed-oracle NATIVE PLATFORM PREFLIGHT only.
        # This must NEVER be counted as real AI model prediction. The separate
        # all-CONFIG baseline is computed by the independent scorer.
        return {"choices":[{"id":x["id"],"mode":x["expected_mode"]}
                           for x in spec["cases"]],
                "model_inference_executed":False,"model_id":None,
                "comparison_baseline":"SEALED_ORACLE_PLATFORM_PREFLIGHT_ONLY"}
    key=os.environ.get("DEEPSEEK_KEY")
    if not key:
        raise RuntimeError("DEEPSEEK_KEY_NOT_CONFIGURED")
    capability=spec["platform_capabilities"]
    # Never send the oracle, fixtures or any Saltcorn credentials to LLM.
    messages=[
      {"role":"system",
       "content":("你是低代码架构能力路由研究中的分类器。给定真实可用能力和用户需求，只能调用 submit_routes 工具一次。"
                  "CONFIG=现成字段、视图和普通配置即可；CODE=保留已有模型，仅须实现现有配置不具备的自定义校验规则；"
                  "HYBRID=既要扩展持久模型/页面配置又要跨表等定制规则。"
                  "勿提供源码、数据库操作或其他工具；按需求本身选择，不能凭某个词偷换。")},
      {"role":"user","content":json.dumps({
         "available_capabilities":capability,"tasks":tasks},ensure_ascii=False)}
    ]
    tool={"type":"function","function":{
      "name":"submit_routes","description":"Choose an implementation path for every task",
      "parameters":{"type":"object","additionalProperties":False,
         "required":["choices"],
         "properties":{"choices":{"type":"array","items":{"type":"object",
            "additionalProperties":False,"required":["id","mode"],
            "properties":{"id":{"type":"string"},
                          "mode":{"type":"string","enum":["CONFIG","CODE","HYBRID"]}}}}}}}}
    payload={"model":MODEL,"messages":messages,"tools":[tool],
             "tool_choice":"required","thinking":{"type":"disabled"},
             "temperature":0,"max_tokens":650,"stream":False}
    request=Request(API,method="POST",
                    data=json.dumps(payload,ensure_ascii=False).encode("utf-8"),
                    headers={"Authorization":"Bearer "+key,
                             "Content-Type":"application/json"})
    try:
        with urlopen(request,timeout=38) as response:
            result=json.load(response)
    except HTTPError as exc:
        # Never log provider error bodies (may contain prompt/context).
        raise RuntimeError("DEEPSEEK_HTTP_"+str(exc.code)) from None
    except Exception:
        raise RuntimeError("DEEPSEEK_NETWORK_OR_RESPONSE_ERROR") from None
    choices=result.get("choices") or []
    calls=choices[0].get("message",{}).get("tool_calls",[]) if choices else []
    if len(calls)!=1 or calls[0].get("function",{}).get("name")!="submit_routes":
        raise RuntimeError("MODEL_DID_NOT_SELECT_REQUIRED_TYPED_TOOL")
    try:
        output=json.loads(calls[0]["function"]["arguments"])
    except (KeyError,ValueError,TypeError):
        raise RuntimeError("MODEL_INVALID_TOOL_JSON") from None
    usage=result.get("usage") if isinstance(result.get("usage"),dict) else {}
    return {"choices":output.get("choices"),
            "model_inference_executed":True,"model_id":MODEL,
            "tool_calls_returned":len(calls),
            "provider_response_id_present":bool(result.get("id")),
            "usage_tokens":{k:usage[k] for k in
                ("prompt_tokens","completion_tokens","total_tokens")
                if isinstance(usage.get(k),int)}}

def validate_choices(spec,prediction):
    items=prediction.get("choices")
    ids={c["id"] for c in spec["cases"]}
    if not isinstance(items,list) or len(items)!=len(ids):
        raise ValueError("MODEL_CHOICES_COUNT_MISMATCH")
    seen=set()
    for item in items:
        if not isinstance(item,dict) or set(item)!={"id","mode"} or \
           item["id"] not in ids or item["mode"] not in VALID or item["id"] in seen:
            raise ValueError("MODEL_CHOICE_INVALID_OR_DUPLICATED")
        seen.add(item["id"])
    if seen!=ids:raise ValueError("MODEL_MISSING_TASK_ID")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--spec",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--live",action="store_true")
    a=p.parse_args()
    spec=json.loads(Path(a.spec).read_text(encoding="utf-8"))
    assert len(spec["cases"])==6 and spec["model_calls_budget"]==1
    prediction=select(spec,a.live)
    validate_choices(spec,prediction)
    prediction["study_id"]=spec["id"]
    # Print ONLY stripped, validated mode decisions. No prompt, secrets, PII.
    print("S1_ROUTE_PREDICTION|"+json.dumps({
       "inference":prediction["model_inference_executed"],
       "model":prediction.get("model_id"),
       "choices":prediction["choices"],
       "usage_tokens":prediction.get("usage_tokens",{})
    },ensure_ascii=False),flush=True)
    Path(a.output).write_text(json.dumps(prediction,ensure_ascii=False,indent=2)+"\n",
                              encoding="utf-8")

if __name__=="__main__":main()
