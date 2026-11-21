"""S1 B5: TWO authoring representations, ONE frozen runtime contract.

B5 IR is a deliberately distinct *authored control-plane representation*,
NOT an independently implemented runtime. Both tracks compile to B2
DataModel/Form/View/Workflow and B4 governed code-extension contract.
This controls execution-engine confounders while explicitly NOT comparing
two independent full low-code kernels.
"""
from __future__ import annotations
import copy
import json
import re
from schema_core import Rejected, verify_refs, sha

IDS=("model.contracts","form.contracts","view.contracts","workflow.approval")
EXTENSION={"id":"risk","kind":"python-pure","entrypoint":"score_contract",
           "entity":"contracts","amountField":"amount_minor",
           "context":["supplier_score","months_active"]}
ALLOWED_ENTITY="contracts"
SAFE_ID=re.compile(r"^[a-z][a-z0-9_]{0,39}$")

def _deny(error):
    raise Rejected(422,error)

def normalise_domain(specs):
    if not isinstance(specs,dict) or set(specs)!=set(IDS):
        _deny("DOMAIN_RESOURCE_SET_INVALID")
    verify_refs(specs)
    model=specs["model.contracts"]
    form=specs["form.contracts"]
    view=specs["view.contracts"]
    wf=specs["workflow.approval"]
    if (model["table"]!=ALLOWED_ENTITY or
        form["model"]!="model.contracts" or
        view["model"]!="model.contracts" or
        wf["model"]!="model.contracts" or
        wf["amountField"]!="amount_minor" or
        wf["statusField"]!="status"):
        _deny("DOMAIN_SEMANTICS_INVALID")
    if {f["name"] for f in model["fields"]}!={"contract_no","title","amount_minor","status"}:
        _deny("DOMAIN_FIELDS_INVALID")
    if {f["name"]:f["type"] for f in model["fields"]}.get("amount_minor")!="integer":
        _deny("DOMAIN_AMOUNT_INVALID")
    return copy.deepcopy({k:specs[k] for k in IDS})

def to_ir(specs):
    """Derive an IR via semantic mapping, not by nesting raw B2 resources."""
    defs=normalise_domain(specs)
    model,form,view,wf=(defs[x] for x in IDS)
    return {
        "irVersion":1,
        "application":"contract-risk",
        "entity":{"id":"contracts","table":model["table"],
                  "attributes":[{"id":x["name"],"dataType":x["type"],
                                 "mandatory":x["required"]} for x in model["fields"]]},
        "interfaces":[
            {"id":"contracts","type":"form","entity":"contracts",
             "caption":form["title"],"bindings":form["fields"]},
            {"id":"contracts","type":"view","entity":"contracts",
             "caption":view["title"],"bindings":view["columns"]}
        ],
        "processes":[
            {"id":"approval","type":"threshold-approval","entity":"contracts",
             "amount":"amount_minor","state":"status",
             "thresholdMinor":wf["thresholdMinor"]}
        ],
        "extensions":[copy.deepcopy(EXTENSION)]
    }


def from_ir(ir):
    """Strict, lossless compiler only for the registered contract subset."""
    if (not isinstance(ir,dict) or
        set(ir)!={"irVersion","application","entity","interfaces",
                 "processes","extensions"} or
        type(ir["irVersion"]) is not int or ir["irVersion"]!=1 or
        ir["application"]!="contract-risk"):
        _deny("IR_ENVELOPE_INVALID")
    entity=ir["entity"]
    if (not isinstance(entity,dict) or set(entity)!={"id","table","attributes"} or
        entity["id"]!=ALLOWED_ENTITY or entity["table"]!=ALLOWED_ENTITY or
        not isinstance(entity["attributes"],list)):
        _deny("IR_ENTITY_INVALID")
    fields=[]
    for attr in entity["attributes"]:
        if not isinstance(attr,dict) or set(attr)!={"id","dataType","mandatory"}:
            _deny("IR_FIELD_INVALID")
        fields.append({"name":attr["id"],"type":attr["dataType"],
                       "required":attr["mandatory"]})
    interfaces=ir["interfaces"]
    if not isinstance(interfaces,list) or len(interfaces)!=2:
        _deny("IR_INTERFACE_SET_INVALID")
    ifaces={}
    for obj in interfaces:
        if not isinstance(obj,dict) or set(obj)!={"id","type","entity",
                                                  "caption","bindings"}:
            _deny("IR_INTERFACE_INVALID")
        kind=obj["type"]
        if kind not in ("form","view") or kind in ifaces or (
            obj["id"]!=ALLOWED_ENTITY or obj["entity"]!=ALLOWED_ENTITY
        ):
            _deny("IR_INTERFACE_REFERENCE_INVALID")
        ifaces[kind]=obj
    if set(ifaces)!={"form","view"}:
        _deny("IR_INTERFACE_SET_INVALID")
    ps=ir["processes"]
    if not isinstance(ps,list) or len(ps)!=1 or not isinstance(ps[0],dict):
        _deny("IR_PROCESS_INVALID")
    process=ps[0]
    if (set(process)!={"id","type","entity","amount","state",
                      "thresholdMinor"} or
        process["type"]!="threshold-approval" or
        process["id"]!="approval" or process["entity"]!=ALLOWED_ENTITY):
        _deny("IR_PROCESS_INVALID")
    exts=ir["extensions"]
    if not isinstance(exts,list) or exts!=[EXTENSION]:
        _deny("IR_EXTENSION_CONTRACT_INVALID")
    specs={
        "model.contracts":{"kind":"model","table":entity["table"],"fields":fields},
        "form.contracts":{"kind":"form","model":"model.contracts",
                          "title":ifaces["form"]["caption"],
                          "fields":copy.deepcopy(ifaces["form"]["bindings"])},
        "view.contracts":{"kind":"view","model":"model.contracts",
                          "title":ifaces["view"]["caption"],
                          "columns":copy.deepcopy(ifaces["view"]["bindings"])},
        "workflow.approval":{"kind":"workflow","model":"model.contracts",
                            "amountField":process["amount"],
                            "statusField":process["state"],
                            "thresholdMinor":process["thresholdMinor"]}
    }
    defs=normalise_domain(specs)
    return {"definitions":defs,
            "manifestHash":sha(defs),
            "extensionContractHash":sha(EXTENSION)}

def compare_representations(direct):
    domain=normalise_domain(direct)
    ir=to_ir(domain)
    compiled=from_ir(ir)
    return {"domain":domain,"ir":ir,"compiled":compiled,
            "identicalDefinitions":domain==compiled["definitions"],
            "identicalManifest":sha(domain)==compiled["manifestHash"],
            "irRoundtripStable":to_ir(compiled["definitions"])==ir,
            "domainAuthoringJsonBytes":len(json.dumps(domain,ensure_ascii=False,
                                sort_keys=True,separators=(",",":")).encode()),
            "irAuthoringJsonBytes":len(json.dumps(ir,ensure_ascii=False,
                                sort_keys=True,separators=(",",":")).encode()),
            "materializedB2CommandsPerFullCreate":len(IDS)}
