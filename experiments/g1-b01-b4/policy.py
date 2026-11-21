"""B4 bounded pure-function code proposal: NEVER execute model source in host."""
import ast,hashlib,json,os,re
from pathlib import Path
from urllib.error import HTTPError,URLError
from urllib.request import Request,urlopen

class RuleError(Exception):
    def __init__(self,code): super().__init__(code);self.code=code

ARGS=("amount_minor","supplier_score","months_active")
REQUIRED="supplier_tenure_risk_scoring"
CAPABILITIES=("form_input","list_view","amount_threshold_approval")
MODEL="deepseek-flash"
API="https://api.deepseek.com/chat/completions"
NAMES=re.compile(r"^[a-z][a-z0-9_]{0,39}$")
NODES=(ast.Module,ast.FunctionDef,ast.arguments,ast.arg,ast.Assign,ast.AugAssign,
       ast.If,ast.Return,ast.Expr,ast.Name,ast.Load,ast.Store,ast.Constant,
       ast.Compare,ast.BoolOp,ast.UnaryOp,ast.BinOp,ast.IfExp,ast.Call,
       ast.Add,ast.Sub,ast.Mult,ast.FloorDiv,ast.Mod,ast.And,ast.Or,ast.Not,
       ast.USub,ast.UAdd,ast.Gt,ast.GtE,ast.Lt,ast.LtE,ast.Eq,ast.NotEq)

def source_hash(src):
    return hashlib.sha256(src.encode("utf-8")).hexdigest()

def select_mode(required,offered=CAPABILITIES):
    if required not in (REQUIRED,*CAPABILITIES):raise RuleError("CAPABILITY_UNKNOWN")
    if required in offered:return "LOW_CODE"
    if required==REQUIRED:return "CUSTOM_CODE"
    raise RuleError("CAPABILITY_MISSING")

def validate_source(src):
    if not isinstance(src,str) or not 20<=len(src)<=6000 or len(src.splitlines())>100:
        raise RuleError("SOURCE_SIZE_INVALID")
    if "\x00" in src or "\r" in src or chr(96)*3 in src:
        raise RuleError("SOURCE_ENCODING_INVALID")
    try:tree=ast.parse(src,mode="exec")
    except (SyntaxError,ValueError,RecursionError):
        raise RuleError("SOURCE_SYNTAX_INVALID") from None
    if len(tree.body)!=1 or not isinstance(tree.body[0],ast.FunctionDef):
        raise RuleError("ONE_FUNCTION_REQUIRED")
    fn=tree.body[0]
    if (fn.name!="score_contract" or fn.decorator_list or fn.returns is not None
        or fn.type_params or fn.args.posonlyargs or fn.args.kwonlyargs
        or fn.args.vararg or fn.args.kwarg or fn.args.defaults
        or fn.args.kw_defaults or [a.arg for a in fn.args.args]!=list(ARGS)
        or any(a.annotation is not None for a in fn.args.args)):
        raise RuleError("SIGNATURE_FORBIDDEN")
    nodes=list(ast.walk(tree))
    if len(nodes)>250:raise RuleError("SOURCE_COMPLEXITY_LIMIT")
    for n in nodes:
        if not isinstance(n,NODES):raise RuleError("AST_NODE_FORBIDDEN")
        if isinstance(n,ast.Name) and (
           not NAMES.fullmatch(n.id) or n.id.startswith("_")):
            raise RuleError("IDENTIFIER_FORBIDDEN")
        if isinstance(n,ast.Call) and (
            not isinstance(n.func,ast.Name) or n.func.id not in ("min","max")
            or n.keywords or not 2<=len(n.args)<=3):
            raise RuleError("FUNCTION_CALL_FORBIDDEN")
        if isinstance(n,ast.Assign) and (
            len(n.targets)!=1 or not isinstance(n.targets[0],ast.Name)):
            raise RuleError("ASSIGNMENT_FORBIDDEN")
        if isinstance(n,ast.AugAssign) and not isinstance(n.target,ast.Name):
            raise RuleError("ASSIGNMENT_FORBIDDEN")
        if isinstance(n,ast.Expr) and (
            n is not fn.body[0] or not isinstance(n.value,ast.Constant)
            or not isinstance(n.value.value,str) or len(n.value.value)>150):
            raise RuleError("EXPRESSION_FORBIDDEN")
        if isinstance(n,ast.Constant) and (
            type(n.value) not in (int,bool,str) or
            (type(n.value) is str and len(n.value)>150) or
            (type(n.value) is int and abs(n.value)>10**13)):
            raise RuleError("CONSTANT_FORBIDDEN")
    if not any(isinstance(n,ast.Return) for n in ast.walk(fn)):
        raise RuleError("RETURN_REQUIRED")
    try:compile(tree,"<untrusted-code>","exec")
    except (ValueError,SyntaxError,OverflowError):
        raise RuleError("SOURCE_COMPILE_FAILED") from None
    return {"source":src,"sourceHash":source_hash(src),"astNodes":len(nodes)}

def oracle(amount_minor,supplier_score,months_active):
    """Trusted independent business reference; not included as model code."""
    if any(type(v) is not int for v in (amount_minor,supplier_score,months_active)):
        raise RuleError("INPUT_TYPE_INVALID")
    if not 0<=amount_minor<=10**12 or not 0<=supplier_score<=100 or not 0<=months_active<=240:
        raise RuleError("INPUT_RANGE_INVALID")
    a=0 if amount_minor<=100000000 else (20 if amount_minor<=500000000 else 35)
    b=35 if supplier_score<30 else (20 if supplier_score<60 else 0)
    c=25 if months_active<6 else (10 if months_active<24 else 0)
    risk=a+b+c
    if amount_minor>200000000 and supplier_score<45:risk=max(risk,90)
    return min(100,risk)

SYSTEM=(
 "你是 OpenAILCAP 的有限权限代码开发 Agent，只能调用 submit_python_rule 一次提交 source，"
 "没有 Shell、数据库、部署和发布权限。请只返回无代码块的纯 Python 函数代码。"
 "函数签名必须为 def score_contract(amount_minor, supplier_score, months_active):，"
 "无类型注解、类、import、for、while、try、with、属性访问、下标访问、执行指令或文件网络调用；"
 "仅能使用 if/elif/else、整数局部赋值、return、比较、加减乘除及 min/max。"
 "输入均整数：金额 amount_minor 为人民币分(0..10^12)，供应商评分 supplier_score(0..100)，"
 "合作月份 months_active(0..240)。输出整数 0..100 风险分。"
 "金额<=100000000分风险加0，(100000000,500000000]加20，>500000000加35；"
 "供应商评分<30加35，30..59加20，>=60加0；"
 "合作月份<6加25，6..23加10，>=24加0。"
 "覆盖特别规则：金额严格>200000000分且供应商评分严格<45时，"
 "最终风险不得低于90；最终限制在0..100。不得漏掉严格边界。"
 "只能输出这个函数的源代码字符串，不允许额外解释/对象。"
)
REQUEST=("现有 B2 合同低代码执行器只支持金额阈值审批，无法配置供应商评分和合作年限联动的"
         "风险评估；请生成可测试的自定义纯函数业务规则，供平台在受限容器中测试和执行。")
TOOL={"type":"function","function":{"name":"submit_python_rule",
      "description":"Propose an untrusted pure-function Python source string only",
      "parameters":{"type":"object","additionalProperties":False,
          "required":["source"],"properties":{"source":{"type":"string"}}}}}

def parse_proposal(data):
    if not isinstance(data,dict):raise RuleError("MODEL_RESPONSE_INVALID")
    choices=data.get("choices")
    if not isinstance(choices,list) or len(choices)!=1:
        raise RuleError("MODEL_CHOICES_INVALID")
    msg=choices[0].get("message")
    calls=msg.get("tool_calls") if isinstance(msg,dict) else None
    if not isinstance(calls,list) or len(calls)!=1:
        raise RuleError("MODEL_TOOL_COUNT_INVALID")
    f=calls[0].get("function") if isinstance(calls[0],dict) else None
    if not isinstance(f,dict) or f.get("name")!="submit_python_rule":
        raise RuleError("MODEL_TOOL_NAME_INVALID")
    raw=f.get("arguments")
    if not isinstance(raw,str) or len(raw)>12000:raise RuleError("MODEL_ARGS_INVALID")
    try:args=json.loads(raw)
    except (ValueError,TypeError):raise RuleError("MODEL_JSON_INVALID") from None
    if not isinstance(args,dict) or set(args)!={"source"}:
        raise RuleError("MODEL_FIELDS_FORBIDDEN")
    return validate_source(args["source"])

def propose(*,live=False):
    if not live:
        source=Path(__file__).with_name("reviewed_rule.py").read_text(encoding="utf-8")
        return {"inference":False,"modelCalls":0,"toolCalls":0,
                "origin":"HUMAN_WRITTEN_OFFLINE_BASELINE","code":validate_source(source)}
    key=os.environ.get("DEEPSEEK_KEY")
    if not isinstance(key,str) or len(key)<10:raise RuleError("DEEPSEEK_KEY_NOT_AVAILABLE")
    body={"model":MODEL,"messages":[{"role":"system","content":SYSTEM},
                                    {"role":"user","content":REQUEST}],
          "tools":[TOOL],"tool_choice":"required","thinking":{"type":"disabled"},
          "temperature":0,"max_tokens":1700,"stream":False}
    req=Request("https://api.deepseek.com/chat/completions",method="POST",
                headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"},
                data=json.dumps(body,ensure_ascii=False).encode("utf-8"))
    try:
        with urlopen(req,timeout=50) as response:raw=response.read(100001)
    except HTTPError as e:raise RuleError("DEEPSEEK_HTTP_"+str(e.code)) from None
    except (URLError,TimeoutError,OSError):
        raise RuleError("DEEPSEEK_TRANSPORT_FAILURE") from None
    if len(raw)>100000:raise RuleError("DEEPSEEK_RESPONSE_TOO_LARGE")
    try:data=json.loads(raw)
    except (ValueError,UnicodeDecodeError):
        raise RuleError("DEEPSEEK_RESPONSE_JSON_INVALID") from None
    checked=parse_proposal(data)
    usage=data.get("usage")
    usage={k:usage[k] for k in ("prompt_tokens","completion_tokens","total_tokens")
           if isinstance(usage,dict) and type(usage.get(k)) is int}
    return {"inference":True,"modelCalls":1,"toolCalls":1,"model":MODEL,
            "origin":"REAL_DEEPSEEK_CODE_VALIDATED","tokenUsage":usage,"code":checked}
