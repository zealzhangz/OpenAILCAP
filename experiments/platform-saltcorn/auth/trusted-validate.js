// Native Saltcorn run_js_code Validate action.
// TRUSTED IDENTITY: user is Saltcorn request's authenticated User, passed by
// api.ts -> table.tryInsertRow(..., req.user) -> Validate Trigger.
// The posted actor_role and actor_id fields are UNTRUSTED assertions.
// Hardcoded fixture users are LAB ONLY, never a general RBAC design.
const expectedByEmail={
  "s1-creator@example.invalid":"creator",
  "s1-approver1@example.invalid":"approver1",
  "s1-approver2@example.invalid":"approver2",
  "s1-viewer@example.invalid":"viewer"
};
if(!user || !Number.isInteger(+user.id) || !user.email)
  return {error:"AUTH_REQUIRED"};
const expectedRole=expectedByEmail[String(user.email).toLowerCase()];
if(!expectedRole || +user.role_id!==80)
  return {error:"AUTH_ROLE_UNKNOWN"};
if(row.actor_role!==expectedRole || String(row.actor_id)!==String(user.id))
  return {error:"IDENTITY_MISMATCH"};
const contracts=Table.findOne({name:"s1_bench_contracts"});
const contract=await contracts.getRow({id:row.contract_ref});
if(!contract) return {error:"NOT_FOUND"};
const status=contract.status;
const high=contract.amount_minor>100000000;
let required=null;
if(row.action==="submit"){
  if(status!=="Draft") return {error:"INVALID_STATE"};
  required="creator";
}else if(row.action==="approve" || row.action==="reject"){
  if(status==="Submitted") required="approver1";
  else if(status==="Level1Approved" && high) required="approver2";
  else return {error:"INVALID_STATE"};
}else return {error:"INVALID_ACTION"};
if(expectedRole!==required) return {error:"FORBIDDEN"};
return {s1_identity_bound_to_native_session:true};
