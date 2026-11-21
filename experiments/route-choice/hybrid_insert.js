// Native Saltcorn Insert Trigger: persisted low-code Field + custom
// conditional cross-table audit. All code is reviewed and preinstalled.
const audit=Table.findOne({name:"s1_route_hybrid_audit"});
if (!audit) throw new Error("S1_ROUTE_HYBRID_AUDIT_TABLE_MISSING");
const high=row.amount_minor>100000000;
await audit.insertRow({
   contract_ref:row.id,
   outcome:high?"HIGH":"NORMAL",
   approval_note_snapshot:row.approval_note
},undefined,undefined,true);
return {created_audit:true};
