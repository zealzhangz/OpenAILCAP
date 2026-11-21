// Negative: native editor write does not update an external CAS ledger.
const table = Table.findOne({name:"s1_contracts"});
if (!table) throw new Error("MISSING_TABLE");
const field = table.getFields().find(f=>f.name==="status");
if (!field || field.label!=="Automation Checked") throw new Error("UNEXPECTED_BEFORE_BYPASS");
await field.update({label:"Ungoverned Human"});
console.log(["S1","BYPASS","HUMAN"].join("_")+"|"+JSON.stringify({
  result:"Native model update applied without sidecar ledger change",label:"Ungoverned Human"
}));
