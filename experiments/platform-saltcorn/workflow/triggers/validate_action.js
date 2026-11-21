// Saltcorn native Validate trigger for incoming business action request.
// This validates an asserted actor_role string, not authenticated user identity.
const contracts=Table.findOne({name:"s1_bench_contracts"});
const contract=await contracts.getRow({id:row.contract_ref});
if(!contract) return {error:"NOT_FOUND"};
const status=contract.status;
const high=contract.amount_minor>100000000;
const act=row.action, role=row.actor_role;
let required=null;
if(act==="submit"){
  if(status!=="Draft") return {error:"INVALID_STATE"};
  required="creator";
}else if(act==="approve" || act==="reject"){
  if(status==="Submitted") required="approver1";
  else if(status==="Level1Approved" && high) required="approver2";
  else return {error:"INVALID_STATE"};
}else return {error:"INVALID_ACTION"};
if(role!==required) return {error:"FORBIDDEN"};
return {s1_business_validation:"OK"};
