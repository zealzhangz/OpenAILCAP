// __CFG__ is replaced with a trusted test-case JSON by generate.py.
// Runs in real Saltcorn CLI context. Lab-only privileged CLI; not authenticating.
const cfg = __CFG__;
let txStarted = false;
let outcome = "UNEXPECTED";
let observed = null;
try {
  // Real SQLite transaction, unlike Saltcorn's SQLite withTransaction wrapper.
  await db.query("BEGIN IMMEDIATE");
  txStarted = true;
  const cursor = await db.query(
    "SELECT revision FROM _openailcap_s1_guard WHERE resource_id=?", [cfg.field]);
  const row = cursor.rows[0];
  if (!row) throw new Error("UNKNOWN_RESOURCE");
  observed = row.revision;
  if (row.revision !== cfg.expected_revision) {
    await db.query("ROLLBACK");
    txStarted = false;
    outcome = "STALE";
  } else {
    const table = Table.findOne({name:"s1_contracts"});
    if (!table) throw new Error("MISSING_NATIVE_TABLE");
    const field = table.getFields().find((f)=>f.name===cfg.field);
    if (!field) throw new Error("MISSING_NATIVE_FIELD");
    await field.update({label:cfg.value});
    if (cfg.fail_after_model_write) throw new Error("INJECTED_POST_FIELD_WRITE");
    await db.query(
      "UPDATE _openailcap_s1_guard SET revision=revision+1 WHERE resource_id=? AND revision=?",
      [cfg.field,cfg.expected_revision]);
    const modified = (await db.query("SELECT changes() AS count")).rows[0].count;
    if (modified !== 1) throw new Error("REVISION_UPDATE_FAILED");
    await db.query("COMMIT");
    txStarted = false;
    outcome = "APPLIED";
  }
} catch(e) {
  if (txStarted) {
    await db.query("ROLLBACK");
    txStarted = false;
  }
  if (cfg.fail_after_model_write && String(e.message).includes("INJECTED_POST_FIELD_WRITE")) {
    outcome = "ROLLED_BACK";
  } else {
    throw e;
  }
}
console.log(["S1","ATOMIC",outcome].join("_")+"|"+JSON.stringify({
  id:cfg.id,resource:cfg.field,base:cfg.expected_revision,actual_before:observed,
  new_label:cfg.value,operation_outcome:outcome
}));
