// Trusted P0-B E2E controller invokes official Saltcorn CLI *only after*
// independently verified B2 form.submit + B11 signed authoritative outbox.
// The disposable Native DB is a derived projection, never a source of truth.
// This is NOT an autonomous CDC consumer or general production migration.
const table=Table.findOne({name:"s1_contracts"});
if(!table) throw new Error("P0B_SALTCORN_NATIVE_TABLE_MISSING");
const existing=await table.getRows({contract_no:"HT-2026-000002"});
if(existing.length!==0) throw new Error("P0B_DUPLICATE_NATIVE_RECORD");
const id=await table.insertRow({
  contract_no:"HT-2026-000002",
  title:"S1 Authority Next Contract",
  amount_minor:200000002,
  status:"Draft"
});
if(!id) throw new Error("P0B_NATIVE_ROW_INSERT_FAILED");
const found=await table.getRows({contract_no:"HT-2026-000002"});
if(found.length!==1 || found[0].title!=="S1 Authority Next Contract")
  throw new Error("P0B_NATIVE_POST_WRITE_SQL_DRIFT");
console.log("P0B_NATIVE_AUTHORITY_CATCHUP|"+JSON.stringify({
  seeded:true,contractNo:"HT-2026-000002"
}));
