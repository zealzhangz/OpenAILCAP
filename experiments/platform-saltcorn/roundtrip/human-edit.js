// Simulates a human-authored *saved* change through Saltcorn's native Field API.
// IMPORTANT: not the visual browser editor and not AI.
const table = Table.findOne({name: "s1_contracts"});
if (!table) throw new Error("MISSING_PLATFORM_TABLE");
const field = table.getFields().find(x => x.name === "title");
if (!field) throw new Error("MISSING_TITLE");
if (field.label !== "Title") throw new Error("UNEXPECTED_TITLE_BEFORE_MANUAL: " + field.label);
await field.update({label: "Human Reviewed Title"});
console.log(JSON.stringify({event:"human-authored-field-change",previous:"Title",next:"Human Reviewed Title"}));
