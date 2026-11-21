"""S1 B3 bounded real DeepSeek request -> untrusted typed plan (research only).

Only the human-authored trusted controller ever runs B2 schema mutation commands.
DeepSeek has no bearer token, DB credentials, shell or publication permission.
Online mode performs exactly ONE HTTPS chat-completions request, no retries.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"g1-b01-b2"))
from schema_core import Rejected, validate_definition, verify_refs, sha

MODEL="deepseek-flash"
ENDPOINT="https://api.deepseek.com/chat/completions"
RESOURCE_IDS=("model.contracts","form.contracts","view.contracts","workflow.approval")
CONTRACT_FIELDS={
    "contract_no":("string",True),
    "title":("string",True),
    "amount_minor":("integer",True),
    "status":("string",True),
}
REQUEST=(
    "请创建一个可运行的企业合同登记与审批应用。合同包含合同编号、标题、金额和审批状态。"
    "用户可以通过表单登记合同，台账列表显示合同编号、标题、金额和当前状态；"
    "合同金额严格超过100万元时需要两级审批，100万元及以下一级即可审批通过。"
    "金额内部以整数分保存。请只做低代码配置，不编写代码。"
)

SYSTEM=(
    "你是 OpenAILCAP 受限低代码配置规划 Agent。"
    "你只能调用 propose_application_plan 函数一次。"
    "此接口只提交候选元数据，模型不能执行命令、调用其他工具或发布。"
    "严格创建 4 项，顺序必须是 model.contracts / form.contracts / view.contracts / workflow.approval。"
    "DataModel 定义对象：kind='model',table='contracts',fields 为四个对象，"
    "每个对象只有 name,type,required 三键，字段依次为："
    "contract_no:string、title:string、amount_minor:integer、status:string，四个 required 均 true。"
    "Form 定义对象：kind='form',model='model.contracts',title 为中文，"
    "fields 只包含 contract_no,title,amount_minor，不包含系统自动设置的 status。"
    "View 定义对象：kind='view',model='model.contracts',title 为中文，"
    "columns 包含上述四个字段（各一次）。"
    "Workflow 定义对象：kind='workflow',model='model.contracts',"
    "amountField='amount_minor',statusField='status',thresholdMinor=100000000（整数分）。"
    "所有内容严格为 JSON 对象；不得输出 SQL、JS、Python、账户、身份、密钥或发布命令。"
)
TOOL={"type":"function","function":{
    "name":"propose_application_plan",
    "description":"Submit an UNTRUSTED four-resource typed low-code application definition proposal for host validation",
    "parameters":{
        "type":"object","additionalProperties":False,"required":["operations"],
        "properties":{
            "operations":{
                "type":"array","minItems":4,"maxItems":4,
                "items":{"type":"object","additionalProperties":False,
                    "required":["resourceId","definition"],
                    "properties":{
                        "resourceId":{"type":"string","enum":list(RESOURCE_IDS)},
                        "definition":{"type":"object"}
                    }}
            }
        }
    }
}}

def check_plan(payload):
    """Independent machine validator: never trust the model's success statement."""
    if not isinstance(payload,dict) or set(payload)!={"operations"}:
        raise Rejected(422,"PLAN_SHAPE_INVALID")
    operations=payload["operations"]
    if not isinstance(operations,list) or len(operations)!=4:
        raise Rejected(422,"PLAN_LENGTH_INVALID")
    if len(json.dumps(payload,ensure_ascii=False))>12000:
        raise Rejected(422,"PLAN_TOO_LARGE")
    defs={}
    for index,(op,expected) in enumerate(zip(operations,RESOURCE_IDS)):
        if not isinstance(op,dict) or set(op)!={"resourceId","definition"} or (
            op["resourceId"]!=expected
        ):
            raise Rejected(422,"PLAN_RESOURCE_ORDER_OR_ID_INVALID")
        definition=op["definition"]
        validate_definition(expected,definition)
        defs[expected]=definition
        verify_refs(defs)  # A single missing reference prevents ALL execution.
    model=defs["model.contracts"]
    actual={field["name"]:(field["type"],field["required"]) for field in model["fields"]}
    if (model["table"]!="contracts" or actual!=CONTRACT_FIELDS or
            len(model["fields"])!=4):
        raise Rejected(422,"SEMANTIC_MODEL_MISMATCH")
    form=defs["form.contracts"]
    if set(form["fields"])!={"contract_no","title","amount_minor"} or len(form["fields"])!=3:
        raise Rejected(422,"SEMANTIC_FORM_MISMATCH")
    view=defs["view.contracts"]
    if set(view["columns"])!=set(CONTRACT_FIELDS) or len(view["columns"])!=4:
        raise Rejected(422,"SEMANTIC_VIEW_MISMATCH")
    flow=defs["workflow.approval"]
    if (flow["amountField"]!="amount_minor" or flow["statusField"]!="status" or
            flow["thresholdMinor"]!=100000000):
        raise Rejected(422,"SEMANTIC_WORKFLOW_MISMATCH")
    for key in ("form.contracts","view.contracts"):
        if any(ord(c)<32 or c in "<>&" for c in defs[key]["title"]):
            raise Rejected(422,"UNSAFE_PRESENTATION_TITLE")
    return {"operations":operations,"planHash":sha(defs),"definitions":defs}


def reviewed_offline_plan():
    """Human-written baseline. It MUST NOT be presented as AI output."""
    defs=json.loads((HERE.parent/"g1-b01-b2"/"contract_spec.json").read_text(
        encoding="utf-8"))
    return {"operations":[{"resourceId":k,"definition":defs[k]} for k in RESOURCE_IDS]}


def _decode_tool_call(payload):
    if not isinstance(payload,dict):
        raise Rejected(422,"MODEL_RESPONSE_INVALID")
    choices=payload.get("choices")
    if not isinstance(choices,list) or len(choices)!=1:
        raise Rejected(422,"MODEL_CHOICES_INVALID")
    msg=choices[0].get("message")
    if not isinstance(msg,dict):
        raise Rejected(422,"MODEL_MESSAGE_INVALID")
    calls=msg.get("tool_calls")
    if not isinstance(calls,list) or len(calls)!=1:
        raise Rejected(422,"MODEL_TOOL_CALL_COUNT_INVALID")
    call=calls[0]
    func=call.get("function") if isinstance(call,dict) else None
    if not isinstance(func,dict) or func.get("name")!="propose_application_plan":
        raise Rejected(422,"MODEL_TOOL_NAME_INVALID")
    raw=func.get("arguments")
    if not isinstance(raw,str) or len(raw)>20000:
        raise Rejected(422,"MODEL_TOOL_ARGUMENTS_INVALID")
    try:
        args=json.loads(raw)
    except ValueError:
        raise Rejected(422,"MODEL_TOOL_JSON_INVALID") from None
    return check_plan(args)


def generate(*, live: bool):
    if not live:
        approved=check_plan(reviewed_offline_plan())
        return {"inference":False,"source":"HUMAN_WRITTEN_DETERMINISTIC_PREFLIGHT",
                "modelCalls":0,"toolCalls":0,"model":None,"plan":approved}
    api_key=os.environ.get("DEEPSEEK_KEY")
    if not isinstance(api_key,str) or len(api_key)<10:
        raise Rejected(503,"DEEPSEEK_KEY_NOT_AVAILABLE")
    req_json={
        "model":MODEL,
        "messages":[
            {"role":"system","content":SYSTEM},
            {"role":"user","content":REQUEST}
        ],
        "tools":[TOOL],"tool_choice":"required",
        "thinking":{"type":"disabled"},"temperature":0,
        "max_tokens":1700,"stream":False
    }
    req=Request(ENDPOINT,method="POST",headers={
        "Authorization":"Bearer "+api_key,
        "Content-Type":"application/json"
    },data=json.dumps(req_json,ensure_ascii=False).encode("utf-8"))
    # Exactly one API request. No retry, no logging of headers or raw response.
    try:
        with urlopen(req,timeout=50) as response:
            raw=response.read(120001)
    except HTTPError as exc:
        raise Rejected(502,"DEEPSEEK_HTTP_"+str(exc.code)) from None
    except (URLError,TimeoutError,OSError):
        raise Rejected(502,"DEEPSEEK_TRANSPORT_FAILURE") from None
    if len(raw)>120000:
        raise Rejected(502,"DEEPSEEK_RESPONSE_TOO_LARGE")
    try:
        result=json.loads(raw)
    except (ValueError,UnicodeDecodeError):
        raise Rejected(502,"DEEPSEEK_RESPONSE_NOT_JSON") from None
    approved=_decode_tool_call(result)
    usage=result.get("usage") or {}
    usage={k:usage[k] for k in ("prompt_tokens","completion_tokens","total_tokens")
           if isinstance(usage,dict) and type(usage.get(k)) is int}
    return {"inference":True,
            "source":"REAL_DEEPSEEK_FUNCTION_CALL_VALIDATED",
            "model":MODEL,"modelCalls":1,"toolCalls":1,
            "providerResponseIdPresent":bool(result.get("id")),
            "tokenUsage":usage,"plan":approved}


def redact_observation(result):
    plan=result["plan"]
    return {"inference":result["inference"],"model":result["model"],
            "model_calls":result["modelCalls"],"tool_calls":result["toolCalls"],
            "source":result["source"],"plan_hash":plan["planHash"],
            "resource_ids":list(plan["definitions"]),
            "tokens":result.get("tokenUsage",{})}
