// Executed by real "saltcorn run-js -f" in the native platform context.
// All business mutations go through real Table.insertRow/updateRow and the
// native Saltcorn Validate/Insert triggers imported through Pack.
// No AI or authenticated browser actor is involved. Authoritative role tokens
// are absent: actor_role is an asserted test field, NOT a trusted principal.
const data = __FROZEN_CASES__;
const contracts=Table.findOne({name:"s1_bench_contracts"});
const requests=Table.findOne({name:"s1_bench_action_requests"});
const routes=Table.findOne({name:"s1_bench_routes"});
const approvals=Table.findOne({name:"s1_bench_approvals"});
if(!contracts || !requests || !routes || !approvals)
  throw new Error("S1_NATIVE_BENCH_TABLES_MISSING");

// Do not parse monetary input with parseFloat/Number on the original string.
function parseMoney(value){
  if(typeof value!=="string" || !/^\d{1,10}(?:\.\d{1,2})?$/.test(value))
    return {error:"INVALID_AMOUNT"};
  const [whole,fraction=""]=value.split(".");
  const cents=Number(whole)*100 + Number((fraction+"00").slice(0,2));
  if(!Number.isSafeInteger(cents)||cents<0||cents>999999999999)
    return {error:"INVALID_AMOUNT"};
  return {minor:cents,canonical:String(Number(whole))+"."+String(cents%100).padStart(2,"0"),
          level:cents>100000000?"HIGH":"NORMAL"};
}
async function createCase(number,input,status="Draft"){
  const parsed=parseMoney(input);
  if(parsed.error) return {error:parsed.error,number};
  const id=await contracts.insertRow({
      number,title:"S1 Native Trigger Workflow "+number,
      amount_decimal:parsed.canonical,amount_minor:parsed.minor,
      owner_id:"creator-research-1",status
  });
  if(!Number.isInteger(id)) throw new Error("S1_NATIVE_CONTRACT_INSERT_FAILURE "+number+" "+JSON.stringify(id));
  return {id,number,minor:parsed.minor,level:parsed.level};
}
async function dispatch(contractId,action,actor_role,requestId){
  // Actual BEGIN IMMEDIATE surrounds native trigger actions on ONE SQLite connection.
  // This is a research harness around Saltcorn, NOT the native HTTP transaction.
  await db.query("BEGIN IMMEDIATE");
  try {
    const outcome={};
    const response=await requests.insertRow({
      request_id:requestId,contract_ref:contractId,action,
      actor_role,actor_id:"research-"+actor_role,
      occurred_at:"2026-11-21T00:00:00Z",reason:"S1-native-action"},undefined,outcome);
    const error=(response&&typeof response==="object"&&response.error)||
                (outcome&&outcome.error);
    if(error){
      await db.query("ROLLBACK");
      return {actual_error:String(error),accepted:false};
    }
    if(!Number.isInteger(response)){
      await db.query("ROLLBACK");
      return {actual_error:"UNEXPECTED_INSERT_RESPONSE:"+JSON.stringify(response),accepted:false};
    }
    await db.query("COMMIT");
    return {accepted:true,request_row_id:response};
  }catch(e){
    await db.query("ROLLBACK");
    throw e;
  }
}
for(const item of data.amount_cases){
  const created=await createCase("AM-"+item.id,item.amount);
  console.log("S1_AMOUNT|"+JSON.stringify({
    id:item.id,input:item.amount,
    inserted:!!created.id,
    actual_error:created.error||null,
    native_row_id:created.id||null,
    derived_level:created.level||null,
    derived_minor:created.minor===undefined?null:created.minor}));
}
for(const item of data.transition_cases){
  const level=item.level;
  const amount=level==="HIGH"?"1000000.01":"1000000.00";
  const created=await createCase("ST-"+item.id,amount,item.from);
  if(!created.id) throw new Error("S1_TRANSITION_FIXTURE_FAILED "+item.id);
  const result=await dispatch(created.id,item.action,item.role,"req-"+item.id);
  const actual=await contracts.getRow({id:created.id});
  const ar=await approvals.getRows({contract_ref:created.id});
  const requestRows=await requests.getRows({contract_ref:created.id});
  console.log("S1_STATE|"+JSON.stringify({
    id:item.id,input_state:item.from,input_role:item.role,input_action:item.action,
    actual_status:actual.status,
    actual_error:result.actual_error||null,
    accepted:result.accepted,
    native_request_count:requestRows.length,
    native_approval_count:ar.length}));
}
const sequences=[
 ["normal",[["submit","creator"],["approve","approver1"]],"1000000.00"],
 ["high",[["submit","creator"],["approve","approver1"],["approve","approver2"]],"1000000.01"],
 ["reject",[["submit","creator"],["reject","approver1"]],"1000000.01"]
];
for(const [name,actions,amount] of sequences){
  const created=await createCase("SEQ-"+name,amount);
  let rejected=null;
  const intermediate=[];
  for(let i=0;i<actions.length;i++){
    const [action,role]=actions[i];
    const result=await dispatch(created.id,action,role,"req-"+name+"-"+i);
    if(!result.accepted){rejected=result.actual_error;break;}
    intermediate.push((await contracts.getRow({id:created.id})).status);
  }
  const actual=await contracts.getRow({id:created.id});
  const ar=await approvals.getRows({contract_ref:created.id});
  console.log("S1_SEQUENCE|"+JSON.stringify({
    id:name,actual_status:actual.status,
    actual_steps:intermediate,actual_approval_count:ar.length,
    error:rejected}));
}
console.log("S1_DRIVER_COMPLETE|"+JSON.stringify({
  amount_case_count:data.amount_cases.length,
  transition_case_count:data.transition_cases.length,
  sequence_count:sequences.length,
  all_executed_via_native_table_api:true
}));
