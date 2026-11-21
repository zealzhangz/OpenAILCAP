"""Optional real model tool-calling probe, never run without explicit credentials.

GitHub Models was retired on 2026-07-30; do NOT point to that API.
Model sees read-only tool schemas and app data, never Saltcorn credentials,
human grants, CSRF, passwords or arbitrary shell/plugin code.
"""
from __future__ import annotations
import json
import os
import secrets
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from broker import ToolError

def actual_model_probe(broker, session_key, contract_no):
    key=os.environ.get("OPENAILCAP_LLM_API_KEY")
    model=os.environ.get("OPENAILCAP_LLM_MODEL")
    api_url=os.environ.get("OPENAILCAP_LLM_CHAT_URL")
    if not key or not model or not api_url:
        raise ToolError("REAL_MODEL_NOT_CONFIGURED")
    u=urlparse(api_url)
    if u.scheme!="https" or not u.hostname or u.username or u.password or u.fragment:
        raise ToolError("REAL_MODEL_ENDPOINT_MUST_BE_TRUSTED_HTTPS")
    catalog=[x for x in broker.catalog(session_key) if x["name"]!="contract.action"]
    tools=[{"type":"function",
            "function":{"name":x["name"].replace(".","_"),
                        "description":x["description"],
                        "parameters":x["parameters"]}} for x in catalog]
    names={x["name"].replace(".","_"):x["name"] for x in catalog}
    prompt=("仅使用给出的只读工具，查询合同 "+contract_no+
            " 的真实状态和审批路由。不要猜测，不要请求写入或执行代码。")
    payload={"model":model,"messages":[
        {"role":"system","content":"你是受限的低代码业务检查 Agent。只能发起白名单只读函数调用，绝不可批准合同或执行代码。"},
        {"role":"user","content":prompt}],
        "tools":tools,"tool_choice":"required",
        "thinking":{"type":"disabled"},"temperature":0,
        "max_tokens":256,"stream":False}
    try:
        req=Request(api_url,data=json.dumps(payload,ensure_ascii=False).encode("utf-8"),
                    headers={"Content-Type":"application/json",
                             "Authorization":"Bearer "+key},
                    method="POST")
        with urlopen(req,timeout=35) as res:
            response=json.load(res)
    except HTTPError as exc:
        # No response body or Authorization headers in public CI logs.
        raise ToolError("MODEL_HTTP_STATUS_" + str(exc.code))
    except Exception:
        raise ToolError("MODEL_INFERENCE_FAILED")
    if not isinstance(response,dict) or not response.get("choices"):
        raise ToolError("NO_VALID_MODEL_RESPONSE")
    message=response["choices"][0].get("message",{})
    calls=message.get("tool_calls",[])
    if not 1<=len(calls)<=2:
        raise ToolError("MODEL_TOOL_COUNT_INVALID")
    observations=[]
    for call in calls:
        fun=call.get("function",{})
        name=fun.get("name","")
        if name not in names:
            raise ToolError("MODEL_REQUESTED_UNAVAILABLE_TOOL")
        try:
            args=json.loads(fun.get("arguments",""))
        except (ValueError,TypeError):
            raise ToolError("MODEL_MALFORMED_TOOL_ARGUMENTS")
        if args!={"number":contract_no}:
            raise ToolError("MODEL_RESOURCE_SCOPE_MISMATCH")
        original_name=names[name]
        output=broker.execute(session_key,original_name,args,
                              call_id="llm-"+secrets.token_hex(12))
        observations.append({"tool":original_name,"arguments_validated":True,
                             "result":output})
    usage=response.get("usage") if isinstance(response.get("usage"),dict) else {}
    return {"model_inference_executed":True,"model_id":model,
            "usage_tokens":{k:usage[k] for k in ("prompt_tokens","completion_tokens","total_tokens") if isinstance(usage.get(k),int)},
            "tool_calls_executed":len(observations),
            "no_mutating_tools_exposed":True,
            "observations":observations,
            "model_provider_response_id_present":bool(response.get("id"))}
