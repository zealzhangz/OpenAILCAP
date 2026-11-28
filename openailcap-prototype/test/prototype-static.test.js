import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile, readdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';

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
