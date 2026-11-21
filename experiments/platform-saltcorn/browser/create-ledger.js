// A deliberately incomplete CAS sidecar; actual Web field editor ignores it.
const table=Table.findOne({name:"s1_contracts"});
const title=table.getFields().find(f=>f.name==="title");
if(!title || title.label!=="Title") throw new Error("UNEXPECTED_INITIAL_TITLE");
await db.query("CREATE TABLE _openailcap_s1_browser_ledger(resource_id TEXT PRIMARY KEY,revision INTEGER NOT NULL)");
await db.query("INSERT INTO _openailcap_s1_browser_ledger(resource_id,revision) VALUES (?,?)",["title",0]);
console.log("S1_BROWSER_LEDGER|"+JSON.stringify({revision:0,field:"title"}));
