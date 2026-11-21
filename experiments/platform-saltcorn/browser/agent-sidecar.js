// Simulated CLI automation. This is NOT a production Agent or authenticated API.
// Intentionally checks only sidecar revision, NOT the actual browser-edited field.
let inTx=false, outcome="UNSET";
try {
  await db.query("BEGIN IMMEDIATE");
  inTx=true;
  const rev=(await db.query(
    "SELECT revision FROM _openailcap_s1_browser_ledger WHERE resource_id=?",["title"])).rows[0].revision;
  if(rev!==0) throw new Error("UNEXPECTED_SIDECAR_REVISION");
  const table=Table.findOne({name:"s1_contracts"});
  const field=table.getFields().find(f=>f.name==="title");
  if(!field) throw new Error("MISSING_TITLE");
  // Deliberately overwrites human UI edit, demonstrating bypass vulnerability.
  await field.update({label:"Agent Overwrites Browser"});
  await db.query("UPDATE _openailcap_s1_browser_ledger SET revision=1 WHERE resource_id=?",["title"]);
  await db.query("COMMIT");
  inTx=false;
  outcome="APPLIED";
}catch(e){
  if(inTx) await db.query("ROLLBACK");
  throw e;
}
console.log("S1_BROWSER_AGENT|"+JSON.stringify({outcome,claimed_base:0,
  final_label:"Agent Overwrites Browser",risk:"Browser UI writes do not update sidecar ledger"}));
