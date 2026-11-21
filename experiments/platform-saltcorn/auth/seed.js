// Real Saltcorn native contract creation. Native Insert trigger builds routes.
const table=Table.findOne({name:"s1_bench_contracts"});
if(!table) throw new Error("NATIVE_TABLE_MISSING");
const cases=[
  ["S1-AUTH-HIGH-1",100000001],
  ["S1-AUTH-NORMAL-1",100000000],
  ["S1-AUTH-HIGH-REJECT",100000001],
  ["S1-AUTH-HIGH-FORGED",100000001]
];
for(const [number,cents] of cases){
  const id=await table.insertRow({number,title:"Authenticated contract approval "+number,
    amount_decimal:(Math.floor(cents/100))+"."+String(cents%100).padStart(2,"0"),
    amount_minor:cents,owner_id:"creator-research-1",status:"Draft"});
  if(!Number.isInteger(id)) throw new Error("BAD_NATIVE_INSERT "+number);
  console.log("S1_AUTH_SEED|"+JSON.stringify({number,id,cents}));
}
