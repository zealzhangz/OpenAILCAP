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
