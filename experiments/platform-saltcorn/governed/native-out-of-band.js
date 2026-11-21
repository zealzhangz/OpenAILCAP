// Intentional bypass negative control.
// This uses Saltcorn's *real* native Field.update API, bypassing the LAB gateway.
// Gateway should detect metadata fingerprint drift and FAIL CLOSED thereafter.
const table = Table.findOne({name:"s1_contracts"});
if (!table) throw new Error("S1_NATIVE_TABLE_NOT_FOUND");
const field = table.getFields().find(f => f.name === "title");
if (!field) throw new Error("S1_NATIVE_FIELD_NOT_FOUND");
await field.update({label:"Native Outside Gateway"});
console.log("S1_NATIVE_BYPASS|"+JSON.stringify({
  platform:"Saltcorn",resource:"title",new_label:"Native Outside Gateway",
  governance:"explicitly_bypassed_for_negative_control"
}));
