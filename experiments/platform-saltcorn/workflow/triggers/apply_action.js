// Saltcorn native Insert trigger (after request insertion).
// Failure semantics are not assumed atomic on Saltcorn SQLite without explicit tx.
const contracts=Table.findOne({name:"s1_bench_contracts"});
const approvals=Table.findOne({name:"s1_bench_approvals"});
const contract=await contracts.getRow({id:row.contract_ref});
if(!contract || !approvals) throw new Error("S1_MISSING_CONTRACT_OR_APPROVAL_TABLE");
const high=contract.amount_minor>100000000;
let next;
if(row.action==="submit") next="Submitted";
else if(row.action==="reject") next="Rejected";
else if(row.action==="approve" && contract.status==="Submitted")
  next=high?"Level1Approved":"Approved";
else if(row.action==="approve" && contract.status==="Level1Approved" && high)
  next="Approved";
else throw new Error("S1_UNEXPECTED_ACTION_AFTER_VALIDATION");
await contracts.updateRow({status:next},contract.id);
if(row.action==="approve" || row.action==="reject")
  await approvals.insertRow({contract_ref:contract.id,approver_id:row.actor_id,
    actor_role:row.actor_role,action:row.action,
    occurred_at:row.occurred_at || "2026-11-21T00:00:00Z",
    reason:row.reason || "research"},undefined,undefined,true);
return {s1_transition_completed:next};
