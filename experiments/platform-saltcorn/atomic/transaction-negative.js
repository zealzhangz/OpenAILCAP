// Real Saltcorn SQLite withTransaction failure injection. Expected NEGATIVE result.
const table = Table.findOne({ name: "s1_contracts" });
const field = table.getFields().find((f) => f.name === "title");
if (!field || field.label !== "Title") throw new Error("UNEXPECTED_TX_FIXTURE");
let aborted = false;
try {
  await db.withTransaction(async () => {
    await field.update({ label: "Unrolled Back Label" });
    throw new Error("INJECTED_ABORT_AFTER_REAL_WRITE");
  });
} catch (e) {
  if (!String(e.message).includes("INJECTED_ABORT_AFTER_REAL_WRITE")) throw e;
  aborted = true;
}
if (!aborted) throw new Error("TRANSACTION_WRAPPER_DID_NOT_PROPAGATE");
const rows = (await db.query(
  "SELECT label FROM _sc_fields WHERE table_id=(SELECT id FROM _sc_tables WHERE name=?) AND name=?",
  ["s1_contracts", "title"]
)).rows;
console.log(["S1", "WRAPPER", "RESULT"].join("_") + "|" + JSON.stringify({
  error_was_raised: aborted, observed_title: rows[0].label,
  unsafe_write_survived_exception: rows[0].label === "Unrolled Back Label"
}));
