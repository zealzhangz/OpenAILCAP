// Saltcorn built-in run_js_code Action; action runs on real Table.insertRow.
const routes = Table.findOne({name:"s1_bench_routes"});
if (!routes) throw new Error("S1_ROUTE_TABLE_MISSING");
const high = row.amount_minor > 100000000; // strict > 1,000,000.00 CNY
await routes.insertRow({contract_ref:row.id,route:high?"HIGH":"NORMAL",
  stage:row.status || "Draft"},undefined,undefined,true);
return {s1_route_recorded:true};
