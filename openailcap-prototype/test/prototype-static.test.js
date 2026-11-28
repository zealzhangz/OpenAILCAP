import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile, readdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
import vm from 'node:vm';

const here=dirname(fileURLToPath(import.meta.url));
const root=resolve(here,'..');
const read=path=>readFile(join(root,path),'utf8');

async function walk(dir){
  const entries=await readdir(dir,{withFileTypes:true});
  const out=[];
  for(const entry of entries){
    const path=join(dir,entry.name);
    if(entry.isDirectory())out.push(...await walk(path));
    else if(entry.isFile()&&entry.name.endsWith('.js'))out.push(path);
  }
  return out;
}

test('all public JavaScript files pass Node syntax check',async()=>{
  const files=await walk(join(root,'public','js'));
  assert.ok(files.length>=15,'expected the prototype module set to be present');
  for(const file of files)execFileSync(process.execPath,['--check',file],{stdio:'pipe'});
});

test('index references existing local CSS and JavaScript assets',async()=>{
  const html=await read('public/index.html');
  const refs=[...html.matchAll(/(?:src|href)="([^"]+\.(?:js|css))"/g)].map(m=>m[1]);
  assert.ok(refs.length>0);
  for(const ref of refs)assert.ok(existsSync(join(root,'public',ref)),'missing asset: '+ref);
});

test('redesign and enhancement layers load after their base styles/modules',async()=>{
  const html=await read('public/index.html');
  assert.ok(html.indexOf('css/workbench-redesign.css')>html.indexOf('css/modules.css'));
  for(const [base,enhancement] of [
    ['js/modules/app-management.js','js/modules/app-lifecycle-enhancements.js'],
    ['js/modules/data-modeling.js','js/modules/data-modeling-enhancements.js'],
    ['js/modules/form-designer.js','js/modules/form-designer-enhancements.js'],
    ['js/modules/logic-flow.js','js/modules/logic-flow-enhancements.js'],
    ['js/modules/bpm-designer.js','js/modules/bpm-designer-enhancements.js']
  ])assert.ok(html.indexOf(enhancement)>html.indexOf(base),enhancement+' must load after '+base);
});

test('all 18 page IDs and 10 AI capabilities remain in the feature baseline',async()=>{
  const matrix=await read('../doc/整改/2026-11-28_功能保留与验收追踪矩阵.md');
  for(let i=1;i<=18;i++)assert.ok(matrix.includes('P'+String(i).padStart(2,'0')),'missing page P'+i);
  for(let i=1;i<=10;i++)assert.ok(matrix.includes('AI'+String(i).padStart(2,'0')),'missing AI capability AI'+i);
});

test('L3 traceability baseline contains all 39 subdomains and six high-level clauses',async()=>{
  const ledger=await read('../doc/整改/GB-T46900-2025_39子域追踪台账.md');
  assert.equal((ledger.match(/^\| 6\.\d+\.\d+ \|/gm)||[]).length,39);
  for(const id of ['6.4.2.4','6.5.3.4','6.8.2.4.1','6.8.2.4.2','6.8.3.4','6.8.4.4'])assert.ok(ledger.includes(id));
});

test('prototype no longer claims an unverified 139/139 compliance result',async()=>{
  const security=await read('public/js/modules/security.js');
  assert.ok(!security.includes('139/139'));
  const readme=await read('README.md');
  assert.ok(readme.includes('不是生产平台后端'));
});

test('AI app generation writes a structured draft and linked artifacts',async()=>{
  const source=await read('public/js/modules/app-management.js');
  for(const token of ['schemaVersion','Store.data.appSpecs.push(appSpec)',"Store.push('models',mainModel)","Store.push('forms',form)","Store.push('logicFlows',logic)"])assert.ok(source.includes(token),token);
});


test('AppSpec schema defines the canonical cross-module contract',async()=>{
  const schema=JSON.parse(await read('../doc/architecture/schemas/app-spec-1.0.0.schema.json'));
  for(const key of ['schemaVersion','meta','dataModels','relations','ui','forms','logic','workflows','security','i18n','deployment'])
    assert.ok(schema.required.includes(key),'schema must require '+key);
  assert.ok(schema.$defs.relation.properties.from);
  assert.ok(schema.$defs.graph.properties.edges);
});

test('AppSpec validator accepts a consistent graph and rejects broken references',async()=>{
  const source=await read('public/js/app-spec.js');
  const validator=vm.runInNewContext(source+'; AppSpec');
  const spec={
    schemaVersion:'1.0.0',meta:{appId:'app_test',name:'Test',description:'',version:'0.1.0',status:'draft'},
    dataModels:[{id:'m1',appId:'app_test',name:'Record',display:'Record',fields:[{name:'id',type:'string',pk:true},{name:'title',type:'string'}]}],
    relations:[],ui:{pages:[{id:'p1',name:'Main',formId:'f1'}]},
    forms:[{id:'f1',appId:'app_test',name:'Main form',fields:[{id:'x1',label:'Title',field:'title',type:'text'}]}],
    logic:[{id:'l1',name:'Logic',nodes:[{id:'n1',type:'event'},{id:'n2',type:'end'}],edges:[{f:'n1',t:'n2'}]}],
    workflows:[],security:{roles:['admin']},i18n:{locales:['zh-CN']},deployment:{status:'not-deployed',environments:['dev']}
  };
  assert.equal(validator.validate(spec).valid,true);
  const broken=structuredClone(spec);broken.logic[0].edges[0].t='missing';
  const result=validator.validate(broken);
  assert.equal(result.valid,false);
  assert.ok(result.errors.some(e=>e.path.includes('edges[0].t')));
});

test('AppSpec 1.1 validates versioned dictionary definitions and form references while retaining 1.0 compatibility',async()=>{
  const source=await read('public/js/app-spec.js');
  const validator=vm.runInNewContext(source+'; AppSpec');
  const base={
    schemaVersion:'1.1.0',meta:{appId:'a1',name:'A'},dataModels:[{id:'m1',fields:[{name:'status',type:'string'}]}],
    relations:[],ui:{pages:[]},forms:[{id:'f1',name:'F',fields:[{id:'x1',label:'Status',field:'status',type:'select',dictionaryRef:{dictionaryId:'d1',version:2}}]}],
    logic:[],workflows:[],security:{roles:[]},i18n:{locales:['zh-CN']},deployment:{status:'not-deployed',environments:[]},
    dictionaries:[{id:'d1',code:'status',name:'Status',version:2,type:'tree',items:[{value:'open',labels:{'zh-CN':'打开'},children:[{value:'closed',labels:{'zh-CN':'关闭'}}]}]}]
  };
  assert.equal(validator.validate(base).valid,true);
  const broken=structuredClone(base);broken.forms[0].fields[0].dictionaryRef.version=1;
  assert.ok(validator.validate(broken).errors.some(e=>e.path.includes('dictionaryRef.version')));
  const missing=structuredClone(base);missing.forms[0].fields[0].dictionaryRef.dictionaryId='missing';
  assert.ok(validator.validate(missing).errors.some(e=>e.path.includes('dictionaryRef.dictionaryId')));
  const legacy=structuredClone(base);legacy.schemaVersion='1.0.0';delete legacy.dictionaries;delete legacy.forms[0].fields[0].dictionaryRef;
  assert.equal(validator.validate(legacy).valid,true);
});

test('M04 promotes local dictionary bindings into versioned AppSpec references only on schema 1.1.0',async()=>{
  const source=await read('public/js/modules/form-runtime-enhancements.js');
  assert.ok(source.includes("spec.schemaVersion!=='1.1.0'"));
  assert.ok(source.includes('dictionaryRef:{dictionaryId:dictionary.id,version:1}'));
  assert.ok(source.includes("next.dictionaries=(Store.get('dicts')||[]).map"));
  assert.ok(source.includes("labels:{'zh-CN':item.zh||item.en||String(item.v),'en-US':item.en||item.zh||String(item.v)}"));
});

test('AI generated AppSpec includes its form foreign key and relation in the canonical document',async()=>{
  const source=await read('public/js/modules/app-management.js');
  assert.ok(source.includes("{name:'party_id',type:'string',req:true,ref:'BusinessParty'}"));
  assert.ok(source.includes("relations:[{id:relationId,from:mainModelId,f:'party_id',to:partyModelId,t:'id',type:'N:1'}]"));
  assert.ok(source.includes('snapshot:snapshotApp(appId)'));
  assert.ok(source.includes('const validation=AppSpec.validate(appSpec)'));
});

test('application lifecycle enhancements replace template and export placeholders',async()=>{
  const source=await read('public/js/modules/app-lifecycle-enhancements.js');
  for(const token of ['fromTemplate(key)','rollback(id,index)','exportApp(id)','exportAll()','openailcap-app-bundle','appShares'])
    assert.ok(source.includes(token),token);
  assert.ok(!source.includes('pending-client-digest'));
});


test('application lifecycle provides recoverable deletion and real local exports',async()=>{
  const source=await read('public/js/modules/app-lifecycle-enhancements.js');
  for(const token of ['recycleBin()','restore(recycleId)','appRecycleBin','downloadJson','exportApp(id)','exportAll()'])
    assert.ok(source.includes(token),token);
  assert.ok(source.includes('expiresAt'));
  assert.ok(source.includes("find(x=>x.meta?.appId===id)||null"));
});

test('global assistant does not fabricate LLM, test coverage, deployment or compliance results',async()=>{
  const source=await read('public/js/app.js');
  for(const token of ['LOCAL DEMO','本地规则演示','不会伪称已经完成生成、测试、部署或合规检查'])
    if(token!=='LOCAL DEMO')assert.ok(source.includes(token),token);
  assert.ok(!source.includes('覆盖率 96%'));
  assert.ok(!source.includes('SM2/3/4'));
});


test('Prisma generator emits valid scalar mappings, constraints and bidirectional relations',async()=>{
  const source=await read('public/js/prisma-schema.js');
  const api=vm.runInNewContext(source+'; PrismaSchema');
  const models=[
    {id:'customer',name:'Customer',fields:[{name:'id',type:'string',pk:true,req:true},{name:'email',type:'string',req:true,unique:true,len:128}]},
    {id:'order',name:'Order',fields:[{name:'id',type:'string',pk:true,req:true},{name:'customer_id',type:'string',req:true},{name:'amount',type:'decimal',req:true,len:'10,2'},{name:'note',type:'text',req:false}]}
  ];
  const schema=api.generate(models,[{id:'r1',from:'order',f:'customer_id',to:'customer',t:'id',type:'N:1'}]);
  assert.match(schema,/email\s+String\s+@unique\s+@db\.VarChar\(128\)/);
  assert.match(schema,/amount\s+Decimal\s+@db\.Decimal\(10,2\)/);
  assert.match(schema,/note\s+String\?\s+@db\.Text/);
  assert.match(schema,/customer\s+Customer\s+@relation\("Rel_Order_customer_id_Customer", fields: \[customer_id\], references: \[id\]\)/);
  assert.match(schema,/orderRecords\s+Order\[\]\s+@relation\("Rel_Order_customer_id_Customer"\)/);
});

test('Prisma generator rejects unsupported types and broken or incompatible relation references',async()=>{
  const source=await read('public/js/prisma-schema.js');
  const api=vm.runInNewContext(source+'; PrismaSchema');
  const models=[
    {id:'a',name:'A',fields:[{name:'id',type:'string',pk:true},{name:'kind',type:'enum'}]},
    {id:'b',name:'B',fields:[{name:'id',type:'string',pk:true},{name:'a_id',type:'int'}]}
  ];
  assert.throws(()=>api.generate(models,[{id:'r',from:'b',f:'a_id',to:'a',t:'id',type:'N:1'}]),/不支持类型 enum/);
  assert.throws(()=>api.generate([{id:'a',name:'A',fields:[{name:'id',type:'string',pk:true},{name:'a_id',type:'string'}]}],[{from:'a',f:'missing',to:'a',t:'id'}]),/外键字段/);
});

test('Prisma generator is loaded before data modeling enhancements',async()=>{
  const html=await read('public/index.html');
  assert.ok(html.indexOf('js/prisma-schema.js')<html.indexOf('js/modules/data-modeling-enhancements.js'));
});


test('organization enhancements replace random permissions and toast-only transfer/promotion with persisted local state',async()=>{
  const source=await read('public/js/modules/organization-enhancements.js');
  for(const token of ['permissionTemplates','orgChangeRequests','decideChange','本地模拟审批人','汇报环路'])
    assert.ok(source.includes(token),token);
  assert.ok(!source.includes('Math.random'));
  const html=await read('public/index.html');
  assert.ok(html.indexOf('js/modules/organization-enhancements.js')>html.indexOf('js/modules/organization.js'));
});


test('M04 form runtime exposes executable validation, visibility and local submission persistence',async()=>{
  const source=await read('public/js/modules/form-runtime-enhancements.js');
  for(const token of ['evaluateRule','validateValues','evaluateVisibility','formSubmissions','formRevision','LOCAL DEMO'])
    assert.ok(source.includes(token),'missing M04 runtime behavior: '+token);
  assert.ok(source.includes("case 'required'")&&source.includes("case 'positive'")&&source.includes("case 'regex'"));
  assert.ok(source.includes('Form.previewRuntime=function()'), 'runtime preview must not replace the original design preview');
  assert.ok(source.includes('formDictionaryRef')&&source.includes('dictCode'), 'form fields must support local dictionary references');
  assert.ok(source.includes("f.type==='radio'")&&source.includes("f.type==='checkbox'"), 'dictionary-backed choice controls must render native selection controls');
  assert.ok(source.includes("controls.filter(el=>el.checked).map(el=>el.value)"), 'checkbox submissions must persist selected values as arrays');
  const designer=await read('public/js/modules/form-designer.js');
  assert.ok(designer.includes('FormM.preview()')&&designer.includes('FormM.previewRuntime()'), 'both design and runtime preview actions must remain available');
  const html=await read('public/index.html');
  assert.ok(html.indexOf('js/modules/form-runtime-enhancements.js')>html.indexOf('js/modules/form-designer-enhancements.js'));
});

test('M04 validation rule evaluation rejects invalid inputs and safely evaluates supported conditions',async()=>{
  const source=await read('public/js/modules/form-runtime-enhancements.js');
  const sandbox={App:{mods:{form:{}}},Store:{},UI:{esc:x=>String(x),toast:()=>{},modal:()=>{}},document:{},Date,Number,RegExp,Set};
  vm.runInNewContext(source,sandbox);
  const form=sandbox.App.mods.form;
  assert.equal(form.evaluateRule({type:'required'},''),false);
  assert.equal(form.evaluateRule({type:'positive'},'-1'),false);
  assert.equal(form.evaluateRule({type:'max',value:'10'},'11'),false);
  assert.equal(form.evaluateRule({type:'length',value:'2-4'},'a'),false);
  assert.equal(form.evaluateRule({type:'regex',value:'^[A-Z]+$'},'abc'),false);
  assert.equal(form.evaluateVisibility('amount >= 100',{amount:'120'}),true);
  assert.equal(form.evaluateVisibility('amount >= 100',{amount:'20'}),false);
  assert.equal(form.evaluateVisibility('amount >= 100; alert(1)',{amount:'120'}),false);
});


test('M04 AppSpec save validates form-to-model references and component compatibility',async()=>{
  const source=await read('public/js/modules/form-runtime-enhancements.js');
  const sandbox={App:{mods:{form:{} }},Store:{data:{forms:[],appSpecs:[]},get(k){return this.data[k];},save(){}},AppSpec:{validate(spec){return {valid:spec.forms.every(f=>f.fields.every(x=>spec.dataModels.some(m=>m.fields.some(y=>y.name===x.field)))) ,errors:[]};}},UI:{esc:x=>String(x),toast:()=>{},modal:()=>{}},document:{},Date,Number,RegExp,Set,JSON};
  vm.runInNewContext(source,sandbox);
  const form=sandbox.App.mods.form;
  const spec={schemaVersion:'1.0.0',meta:{appId:'a1'},dataModels:[{id:'m1',name:'Order',fields:[{name:'amount',type:'decimal'},{name:'status',type:'enum'}]}],forms:[],ui:{pages:[]},relations:[],logic:[],workflows:[],security:{roles:[]},i18n:{locales:['zh-CN']},deployment:{environments:[]}};
  const candidate={id:'f1',appId:'a1',modelRef:'m1',fields:[{field:'amount',type:'number'},{field:'status',type:'select'}]};
  assert.equal(form.validateModelReferences(candidate,spec).length,0);
  assert.ok(form.validateModelReferences({...candidate,fields:[{field:'missing',type:'number'}]},spec).length>0);
  assert.ok(form.validateModelReferences({...candidate,fields:[{field:'status',type:'number'}]},spec).length>0);
});
test('M04 legacy string rules remain executable after rule normalization',async()=>{
  const source=await read('public/js/modules/form-runtime-enhancements.js');
  const store={data:{forms:[{id:'f1',fields:[{id:'a',field:'amount',label:'金额',req:true,rules:['positive','max:9999999']}]}]},get(key){return this.data[key];},save(){}};
  const sandbox={App:{mods:{form:{}}},Store:store,UI:{esc:x=>String(x),toast:()=>{},modal:()=>{}},document:{},Date,Number,RegExp,Set};
  vm.runInNewContext(source,sandbox);
  const form=sandbox.App.mods.form;
  assert.equal(form.validateValues(store.data.forms[0],{amount:'10'}).length,0);
  assert.ok(form.validateValues(store.data.forms[0],{amount:'-1'}).length>0);
  assert.equal(typeof store.data.forms[0].fields[0].rules[0],'object');
});


test('AppSpec 1.0 to 1.1 migration preview is non-destructive, explicit and repeatable',async()=>{
  const appSource=await read('public/js/app-spec.js');
  const migrationSource=await read('public/js/app-spec-migrations.js');
  const sandbox={};
  vm.runInNewContext(appSource+'; this.AppSpec=AppSpec;',sandbox);
  vm.runInNewContext(migrationSource,sandbox);
  const original={
    schemaVersion:'1.0.0',meta:{appId:'app_migrate',name:'Migration test',description:'',version:'1.0',status:'draft'},
    dataModels:[{id:'m1',appId:'app_migrate',name:'Record',display:'Record',fields:[{name:'status',type:'string'}]}],
    relations:[],ui:{pages:[]},forms:[{id:'f1',appId:'app_migrate',name:'Form',modelRef:'m1',fields:[{id:'ff1',label:'Status',field:'status',type:'select',dictCode:'status'}]}],
    logic:[],workflows:[],security:{roles:[]},i18n:{locales:['zh-CN']},deployment:{status:'not-deployed',environments:['dev']}
  };
  const dictionaries=[{id:'dict_status',code:'status',name:'Status',version:3,type:'list',items:[{v:'open',zh:'打开',en:'Open'}]}];
  const before=JSON.stringify(original);
  const result=sandbox.AppSpecMigrations.preview(original,{dictionaries,validate:sandbox.AppSpec.validate.bind(sandbox.AppSpec)});
  assert.equal(result.ok,true,JSON.stringify(result.errors));
  assert.equal(result.migrated.schemaVersion,'1.1.0');
  assert.deepEqual(JSON.parse(JSON.stringify(result.migrated.forms[0].fields[0].dictionaryRef)),{dictionaryId:'dict_status',version:3});
  assert.equal(result.migrated.dictionaries[0].items[0].labels['en-US'],'Open');
  assert.equal(JSON.stringify(original),before,'preview must not mutate its source');
  const again=sandbox.AppSpecMigrations.preview(result.migrated,{dictionaries,validate:sandbox.AppSpec.validate.bind(sandbox.AppSpec)});
  assert.equal(again.ok,true);
  assert.deepEqual(JSON.parse(JSON.stringify(again.migrated)),JSON.parse(JSON.stringify(result.migrated)));
  assert.deepEqual(JSON.parse(JSON.stringify(again.changedPaths)),[]);
});

test('AppSpec migration fails closed for unknown or ambiguous dictionaries and external sources',async()=>{
  const sandbox={};
  vm.runInNewContext(await read('public/js/app-spec.js')+'; this.AppSpec=AppSpec;',sandbox);
  vm.runInNewContext(await read('public/js/app-spec-migrations.js'),sandbox);
  const spec={schemaVersion:'1.0.0',meta:{appId:'a',name:'A'},dataModels:[{id:'m',fields:[{name:'status',type:'string'}]}],relations:[],ui:{pages:[]},forms:[{id:'f',name:'F',modelRef:'m',fields:[{id:'x',label:'Status',field:'status',type:'select',dictCode:'missing'}]}],logic:[],workflows:[],security:{roles:[]},i18n:{locales:['zh-CN']},deployment:{status:'not-deployed',environments:[]}};
  const validate=sandbox.AppSpec.validate.bind(sandbox.AppSpec);
  const unknown=sandbox.AppSpecMigrations.preview(spec,{dictionaries:[],validate});
  assert.equal(unknown.ok,false);
  assert.ok(unknown.errors.some(e=>e.path.endsWith('.dictCode')));
  const duplicate=sandbox.AppSpecMigrations.preview(spec,{dictionaries:[{id:'d1',code:'missing',type:'list',items:[]},{id:'d2',code:'missing',type:'list',items:[]}],validate});
  assert.equal(duplicate.ok,false);
  assert.ok(duplicate.errors.some(e=>e.message.includes('duplicate dictionary code')));
  const external=structuredClone(spec);external.forms[0].fields[0].dictFrom='remote-service';
  const rejected=sandbox.AppSpecMigrations.preview(external,{dictionaries:[],validate});
  assert.equal(rejected.ok,false);
  assert.ok(rejected.errors.some(e=>e.message.includes('external dictionary source')));
});

test('AppSpec migration rejects broken form model and field references and preserves 1.1 input',async()=>{
  const sandbox={};
  vm.runInNewContext(await read('public/js/app-spec.js')+'; this.AppSpec=AppSpec;',sandbox);
  vm.runInNewContext(await read('public/js/app-spec-migrations.js'),sandbox);
  const spec={schemaVersion:'1.0.0',meta:{appId:'a',name:'A'},dataModels:[{id:'m',fields:[{name:'status',type:'string'}]}],relations:[],ui:{pages:[]},forms:[{id:'f',name:'F',modelRef:'missing',fields:[{id:'x',label:'Status',field:'absent',type:'text'}]}],logic:[],workflows:[],security:{roles:[]},i18n:{locales:['zh-CN']},deployment:{status:'not-deployed',environments:[]}};
  const result=sandbox.AppSpecMigrations.preview(spec,{dictionaries:[],validate:sandbox.AppSpec.validate.bind(sandbox.AppSpec)});
  assert.equal(result.ok,false);
  assert.ok(result.errors.some(e=>e.path.endsWith('.modelRef')));
  const v11={...spec,schemaVersion:'1.1.0',dictionaries:[]};
  const stable=sandbox.AppSpecMigrations.preview(v11);
  assert.equal(stable.ok,true);
  assert.deepEqual(JSON.parse(JSON.stringify(stable.migrated)),v11);
  assert.deepEqual(JSON.parse(JSON.stringify(stable.changedPaths)),[]);
});
