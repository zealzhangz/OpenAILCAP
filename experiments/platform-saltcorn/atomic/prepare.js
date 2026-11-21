// Lab-only revision table; native Saltcorn editors do NOT maintain this.
const table = Table.findOne({ name: "s1_contracts" });
if (!table) throw new Error("NO_REAL_SALTCORN_TABLE");
const title = table.getFields().find((f) => f.name === "title");
const status = table.getFields().find((f) => f.name === "status");
if (!title || !status) throw new Error("MISSING_FIELDS");
if (title.label !== "Unrolled Back Label") throw new Error("NEGATIVE_CONTROL_MUST_RUN_FIRST");
await title.update({label:"Title"});
if (status.label !== "Status") throw new Error("UNEXPECTED_STATUS");
await db.query("CREATE TABLE IF NOT EXISTS _openailcap_s1_guard (resource_id TEXT PRIMARY KEY, revision INTEGER NOT NULL)");
await db.query("INSERT INTO _openailcap_s1_guard (resource_id, revision) VALUES (?,?)", ["title",0]);
await db.query("INSERT INTO _openailcap_s1_guard (resource_id, revision) VALUES (?,?)", ["status",0]);
console.log(["S1","PREPARED"].join("_")+"|"+JSON.stringify({resources:["title","status"],revision:0}));
