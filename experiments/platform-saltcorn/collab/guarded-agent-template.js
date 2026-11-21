// Saltcorn native CLI research adapter, human reviewed and PRE-INSTALLED.
// Real DeepSeek is only allowed to submit typed parameter JSON, NEVER JS.
// Guard against changes to both human title and AI target since snapshot.
// IMPORTANT: Native browser editor does NOT use this CAS; this guards only
// Agent writes and cannot protect an old native browser form from overwriting.
const proposal=__VERIFIED_LABEL_PATCH_JSON__;
if(proposal.field!=="status" ||
   proposal.expected_title!=="Human First Saved" ||
   proposal.expected_status!=="Status" ||
   proposal.new_label!=="AI Reviewed Status")
   throw new Error("PATCH_NOT_ALLOWLISTED");
const table=Table.findOne({name:"s1_contracts"});
const title=table.getFields().find(f=>f.name==="title");
const status=table.getFields().find(f=>f.name==="status");
if(!title||!status)throw new Error("NATIVE_FIELD_NOT_FOUND");
let began=false;
try{
  await db.query("BEGIN IMMEDIATE");
  began=true;
  const rows=(await db.query(
    "SELECT name,label FROM _sc_fields WHERE table_id=? AND name IN (?,?)",
    [table.id,"title","status"]
  )).rows;
  const labels=Object.fromEntries(rows.map(r=>[r.name,r.label]));
  if(labels.title!==proposal.expected_title ||
     labels.status!==proposal.expected_status){
    await db.query("ROLLBACK");
    began=false;
    console.log("S1_COLLAB_NATIVE_CAS|"+JSON.stringify({
      decision:"STALE_REJECTED",
      title_observed:labels.title,
      status_observed:labels.status,
      requested_target:proposal.field,
      native_write_attempted:false
    }));
  }else{
    await status.update({label:proposal.new_label});
    const after=(await db.query(
      "SELECT name,label FROM _sc_fields WHERE table_id=? AND name IN (?,?)",
      [table.id,"title","status"]
    )).rows;
    const newLabels=Object.fromEntries(after.map(r=>[r.name,r.label]));
    if(newLabels.title!==proposal.expected_title ||
       newLabels.status!==proposal.new_label)
       throw new Error("NATIVE_WRITE_POSTCONDITION_NOT_MET");
    await db.query("COMMIT");
    began=false;
    console.log("S1_COLLAB_NATIVE_CAS|"+JSON.stringify({
      decision:"APPLIED",
      title_observed:newLabels.title,
      status_observed:newLabels.status,
      requested_target:proposal.field,
      native_write_attempted:true
    }));
  }
}catch(e){
  if(began)await db.query("ROLLBACK");
  throw e;
}
