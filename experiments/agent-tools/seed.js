// Creates real low-code business rows using Saltcorn Table.insertRow.
// The existing native Insert Trigger automatically persists approval routes.
const table=Table.findOne({name:"s1_bench_contracts"});
if(!table) throw new Error("NATIVE_CONTRACT_TABLE_NOT_FOUND");
for(const [number,cents] of [["S1-AGENT-HIGH-1",100000001],
                              ["S1-AGENT-NORMAL-1",100000000]]){
  const id=await table.insertRow({
      number,
      title:"Typed Agent Tool Research "+number,
      amount_decimal:Math.floor(cents/100)+"."+String(cents%100).padStart(2,"0"),
      amount_minor:cents,owner_id:"test-creator",status:"Draft"
  });
  if(!Number.isInteger(id))throw new Error("NATIVE_INSERT_FAILED "+number);
  console.log("S1_AGENT_SEED|"+JSON.stringify({number,id,amount_minor:cents}));
}
