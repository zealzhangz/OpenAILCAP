// Simulates an automated scoped mutation via native model API; NOT an LLM Agent.
// Changes status label only; must preserve separate title field.
const table = Table.findOne({name:"s1_contracts"});
if (!table) throw new Error("MISSING_PLATFORM_TABLE");
const field = table.getFields().find(x => x.name === "status");
if (!field || field.label !== "Status") throw new Error("UNEXPECTED_BASE_STATUS");
await field.update({label:"Automated Status"});
console.log(JSON.stringify({event:"scoped-programmatic-field-update",target:"status.label",value:"Automated Status"}));
