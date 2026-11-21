// Runs INSIDE the real Saltcorn CLI context via "saltcorn run-js -f".
const contracts = Table.findOne({name:"s1_contracts"});
if (!contracts) throw new Error("Native contract table not in Saltcorn model state");
const first = await contracts.insertRow({
  contract_no:"HT-2026-000001",
  title:"S1 Platform Contract",
  amount_minor:100000001, // 1,000,000.01 yuan in cents; avoid JS float for money
  status:"Draft"
});
if (!first) throw new Error("Native Table.insertRow returned no row");
const found = await contracts.getRows({contract_no:"HT-2026-000001"});
if (!found || found.length !== 1) throw new Error("Cannot query seeded native row");
console.log(JSON.stringify({seeded:true,contract_no:found[0].contract_no,id:found[0].id}));
