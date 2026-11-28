import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import Ajv2020 from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';

const ajv=new Ajv2020({allErrors:true,strict:false});
addFormats(ajv);
const load=path=>JSON.parse(fs.readFileSync(new URL(path,import.meta.url),'utf8'));
const schema10=load('../../doc/architecture/schemas/app-spec-1.0.0.schema.json');
const schema11=load('../../doc/architecture/schemas/app-spec-1.1.0.schema.json');
const validate10=ajv.compile(schema10);
const validate11=ajv.compile(schema11);
const base=()=>({schemaVersion:'1.0.0',meta:{appId:'a',name:'A',description:'',version:'1.0',status:'draft'},dataModels:[{id:'m',name:'M',display:'M',fields:[{name:'status',type:'string'}]}],relations:[],ui:{pages:[]},forms:[{id:'f',name:'F',fields:[{id:'x',label:'Status',field:'status',type:'select'}]}],logic:[],workflows:[],security:{roles:[]},i18n:{locales:['zh-CN']},deployment:{status:'draft',environments:[]}});
test('official Ajv Draft 2020-12 validator accepts 1.0.0 and 1.1.0 fixtures',()=>{
 const v10=base();
 assert.equal(validate10(v10),true,JSON.stringify(validate10.errors));
 const v11={...v10,schemaVersion:'1.1.0',dictionaries:[{id:'d',code:'status',name:'Status',version:1,type:'list',items:[{value:'open',labels:{'zh-CN':'打开'}}]}]};
 v11.forms[0].fields[0].dictionaryRef={dictionaryId:'d',version:1};
 assert.equal(validate11(v11),true,JSON.stringify(validate11.errors));
});
test('official Ajv rejects cross-version payloads and malformed dictionary refs',()=>{
 const v10=base();
 assert.equal(validate11(v10),false);
 const v11={...v10,schemaVersion:'1.1.0',dictionaries:[]};
 v11.forms[0].fields[0].dictionaryRef={dictionaryId:'d',version:0};
 assert.equal(validate11(v11),false);
 const v10WithDictionary={...v10,dictionaries:[]};
 assert.equal(validate10(v10WithDictionary),false);
});
