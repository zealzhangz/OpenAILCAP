// This trusted Saltcorn CLI runner is pre-written. DeepSeek chooses ENUM paths
// only. A single selected route decides which native Table/Trigger is exercised.
const cases=__FROZEN_EXECUTION_CASES_JSON__;
const cfg=Table.findOne({name:"s1_route_cfg"});
const code=Table.findOne({name:"s1_route_code"});
const hybrid=Table.findOne({name:"s1_route_hybrid"});
const audit=Table.findOne({name:"s1_route_hybrid_audit"});
if(!cfg||!code||!hybrid||!audit)
  throw new Error("S1_ROUTE_NATIVE_TABLE_MISSING");
for(const task of cases){
  const f=task.fixture, selected=task.mode;
  let id;
  if(selected==="CONFIG"){
    id=await cfg.insertRow({
      case_id:task.id,
      number:f.number||"CFG-FALLBACK-"+task.id,
      review_note:f.note||"Research configuration note",
      status:f.status||"Draft"
    });
  }else if(selected==="CODE"){
    const number=/^K-[0-9]+-[0-6]$/.test(f.number||"")?f.number:"K-14-0";
    id=await code.insertRow({case_id:task.id,number});
    // Independent negative control; a native Validate Trigger must reject
    // a bad check digit before a physical Saltcorn business row is created.
    const bad=f.invalid_number||"K-14-5";
    const outcome={};
    let response=null, error=null;
    try{
      response=await code.insertRow({case_id:"NEG-"+task.id,number:bad},
                                    undefined,outcome);
      error=outcome.error ||
        (response&&typeof response==="object"&&response.error)||null;
    }catch(e){error=e&&e.message?e.message:String(e);}
    console.log("S1_ROUTE_NEGATIVE|"+JSON.stringify({
      case_id:task.id,number:bad,error:error?String(error):null,
      inserted_id:Number.isInteger(response)?response:null
    }));
  }else if(selected==="HYBRID"){
    id=await hybrid.insertRow({
      case_id:task.id,
      number:f.number||"HYB-FALLBACK-"+task.id,
      amount_minor:Number.isSafeInteger(f.amount_minor)?f.amount_minor:100000000,
      approval_note:f.note||"Research hybrid note"
    });
  }else throw new Error("ROUTE_NOT_ALLOWLISTED");
  if(!Number.isInteger(id))
    throw new Error("S1_ROUTE_NATIVE_INSERT_FAILED "+task.id+
                    " "+JSON.stringify(id));
  console.log("S1_ROUTE_EXEC|"+JSON.stringify({
     case_id:task.id,selected_mode:selected,native_row_id:id
  }));
}
console.log("S1_ROUTE_EXEC_COMPLETE|"+JSON.stringify({
  route_count:cases.length,runtime_native_table_api:true,
  ai_generated_code:false
}));
