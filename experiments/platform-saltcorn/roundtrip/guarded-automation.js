// Demonstrates *application-side* stale-base rejection on real Saltcorn model.
// This check is NOT atomic CAS: parallel callers can race between check/update.
// It is a research negative control, NOT a production conflict barrier.
const table = Table.findOne({name:"s1_contracts"});
if (!table) throw new Error("MISSING_PLATFORM_TABLE");
const field = table.getFields().find(x => x.name === "title");
if (!field) throw new Error("MISSING_TITLE");
const expectedBase = "Title";
if (field.label !== expectedBase)
  throw new Error("STALE_BASE title.label expected=" + expectedBase + " actual=" + field.label);
await field.update({label:"Automated Title"});
console.log(JSON.stringify({event:"unexpected-guard-accepted",value:"Automated Title"}));
