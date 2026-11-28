/* App lifecycle completion for the browser prototype.
 * All mutations persist to localStorage. This is not a substitute for server-side
 * authorization, artifact signing, immutable storage, or deployment APIs.
 */
const AppsBase = App.mods.apps;
const ensureCollection = key => { Store.data[key]=Store.data[key]||[]; return Store.data[key]; };
const downloadJson = (filename,value) => {
  const blob=new Blob([JSON.stringify(value,null,2)],{type:'application/json;charset=utf-8'});
  const url=URL.createObjectURL(blob),a=document.createElement('a');
  a.href=url;a.download=filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
};
const snapshotApp = id => {
  const app=Store.find('apps',id);if(!app)return null;
  const pick=(key)=>((Store.get(key)||[]).filter(x=>x.appId===id));
  const models=pick('models');
  return {app:structuredClone(app),appSpec:structuredClone((Store.get('appSpecs')||[]).filter(x=>x.meta?.appId===id)),
    models:structuredClone(models),relations:structuredClone((Store.get('relations')||[]).filter(r=>models.some(m=>m.id===r.from)&&models.some(m=>m.id===r.to))),
    forms:structuredClone(pick('forms')),logicFlows:structuredClone(pick('logicFlows')),
    bpmDefs:structuredClone(pick('bpmDefs'))};
};
Object.assign(AppsBase,{

  detail(id) {
    const app=Store.find('apps',id);if(!app)return UI.toast('应用不存在','err');
    const versions=(Store.get('appVersions')||[]).find(x=>x.appId===id)?.list||[];
    const artifacts=(Store.get('artifacts')||[]).filter(x=>x.appId===id);
    const shares=(Store.get('appShares')||[]).filter(x=>x.appId===id);
    UI.modal({title:(app.icon||'📦')+' '+UI.esc(app.name),size:'lg',footer:false,body:
      '<div class="tabs" id="adTabs"><button class="tab active" onclick="AppDetail.tab(0)">概览</button><button class="tab" onclick="AppDetail.tab(1)">版本历史</button><button class="tab" onclick="AppDetail.tab(2)">制品</button><button class="tab" onclick="AppDetail.tab(3)">访问授权</button></div>'+
      '<div class="tab-pane active" id="adp0">'+UI.kvGrid([['应用 ID',app.id],['描述',UI.esc(app.desc||'')],['状态',app.status],['版本',app.version],['负责人',app.owner],['访问范围',app.acl||'未配置'],['环境','dev '+app.env.dev+' / test '+app.env.test+' / prod '+app.env.prod]])+
      '<div class="btn-row mt10"><button class="btn" onclick="AppsM.exportApp(\''+id+'\')">导出配置</button><button class="btn" onclick="AppsM.artifact(\''+id+'\')">生成配置制品</button><button class="btn" onclick="AppsM.share(\''+id+'\')">新增授权申请</button></div></div>'+
      '<div class="tab-pane" id="adp1">'+(versions.length?versions.map((v,i)=>'<div class="item flex"><div><b>'+UI.esc(v.v)+'</b><div class="muted">'+UI.esc(v.note||'')+' · '+UI.esc(v.time||'')+'</div></div><span class="spacer"></span><button class="btn btn-sm" onclick="AppsM.rollback(\''+id+'\','+i+')" '+(v.snapshot?'':'disabled')+'>恢复快照</button></div>').join(''):'<div class="empty">暂无版本</div>')+'</div>'+
      '<div class="tab-pane" id="adp2">'+(artifacts.length?artifacts.map(a=>'<div class="item">📦 '+UI.esc(a.version)+' · '+a.sizeBytes+' bytes · '+UI.esc(a.status)+'</div>').join(''):'<div class="empty">暂无配置制品。点击概览中的“生成配置制品”。</div>')+'</div>'+
      '<div class="tab-pane" id="adp3">'+(shares.length?shares.map(a=>'<div class="item">'+UI.esc(a.subject)+' · '+UI.esc(a.role)+' · '+UI.esc(a.status)+'</div>').join(''):'<div class="empty">暂无本地授权申请</div>')+'</div>'});
  },
  del(id) {
    const app=Store.find('apps',id);if(!app)return UI.toast('应用不存在','err');
    UI.confirm('将应用「'+UI.esc(app.name)+'」移入回收站？关联设计数据会保留，30 天内可恢复。',()=>{
      const snapshot=snapshotApp(id);
      ensureCollection('appRecycleBin').push({id:'recycle_'+Date.now(),appId:id,deletedAt:new Date().toISOString(),expiresAt:new Date(Date.now()+30*86400000).toISOString(),snapshot});
      Store.data.apps=Store.data.apps.filter(x=>x.id!==id);Store.save();this.draw();UI.toast('应用已移入回收站，关联数据已保留');
    });
  },
  recycleBin() {
    const rows=Store.get('appRecycleBin')||[];
    UI.modal({title:'应用回收站',size:'lg',footer:false,body:rows.length?rows.map((r,i)=>'<div class="item flex"><div><b>'+UI.esc(r.snapshot?.app?.name||r.appId)+'</b><div class="muted">删除于 '+UI.esc(r.deletedAt)+' · 到期 '+UI.esc(r.expiresAt)+'</div></div><span class="spacer"></span><button class="btn btn-sm btn-p" onclick="AppsM.restore(\''+r.id+'\')">恢复</button></div>').join(''):'<div class="empty">回收站为空</div>'});
  },
  restore(recycleId) {
    const rows=Store.get('appRecycleBin')||[],entry=rows.find(x=>x.id===recycleId);
    if(!entry)return UI.toast('回收站记录不存在','err');
    if(Date.now()>Date.parse(entry.expiresAt))return UI.toast('已超过保留期限，不能恢复','err');
    const snap=entry.snapshot,app=snap?.app;if(!app)return UI.toast('缺少应用快照，不能恢复','err');
    ensureCollection('apps').push(structuredClone(app));
    const replace=(key,items)=>{Store.data[key]=(Store.data[key]||[]).filter(x=>x.appId!==entry.appId).concat(structuredClone(items||[]));};
    Store.data.appSpecs=(Store.data.appSpecs||[]).filter(x=>x.meta?.appId!==entry.appId).concat(structuredClone(snap.appSpec||[]));
    replace('models',snap.models);replace('forms',snap.forms);replace('logicFlows',snap.logicFlows);replace('bpmDefs',snap.bpmDefs);
    Store.data.appRecycleBin=rows.filter(x=>x.id!==recycleId);Store.save();UI.closeModal();this.draw();UI.toast('应用及其设计数据已恢复');
  },
  fromTemplate(key) {
    const templates={
      crm:{name:'CRM 客户关系管理',desc:'客户档案、商机、跟进记录与销售漏斗',icon:'👥',models:[['Customer','客户档案',['name','phone','email','level']],['Opportunity','销售商机',['title','amount','stage','owner']],['FollowUp','跟进记录',['customer_id','content','next_at']]]},
      inventory:{name:'进销存管理',desc:'商品、库存、入库、出库与盘点',icon:'🏬',models:[['Product','商品档案',['sku','name','unit','price']],['Stock','库存台账',['product_id','warehouse_id','quantity']],['StockMovement','出入库记录',['product_id','direction','quantity','occurred_at']]]},
      oa:{name:'OA 审批中心',desc:'通用申请、审批任务与审批记录',icon:'✅',models:[['Request','申请单',['request_no','title','applicant','status']],['ApprovalRecord','审批记录',['request_id','approver','action','comment']]]}
    };
    const t=templates[key];if(!t)return UI.toast('未知模板，请重新选择','err');
    const id='app_'+Date.now(),now=new Date().toISOString(),models=t.models.map((m,i)=>({id:'model_'+id+'_'+i,appId:id,name:m[0],display:m[1],x:40+i*280,y:50,fields:[
      {name:'id',type:'string',pk:true,req:true,len:36},
      ...m[2].map((name,j)=>({name,type:/amount|price|quantity/.test(name)?'decimal':'string',req:j===0,len:160}))
    ]}));
    const form={id:'form_'+id,appId:id,name:t.name+' · 主表单',fields:models[0].fields.filter(f=>!f.pk).map((f,i)=>({id:'field_'+id+'_'+i,label:f.name,field:f.name,type:f.type==='decimal'?'number':'text',req:!!f.req,span:12}))};
    const spec={schemaVersion:'1.0.0',meta:{appId:id,name:t.name,description:t.desc,version:'0.1.0',status:'draft',createdAt:now,source:'template:'+key},
      dataModels:models,relations:[],ui:{pages:[{id:'page_'+id,name:'业务管理',formId:form.id}]},forms:[form],logic:[],workflows:[],
      security:{roles:['应用管理员','业务经办人'],auditRequired:true},i18n:{locales:['zh-CN']},
      deployment:{status:'not-deployed',environments:['dev','test','prod']}};
    const check=AppSpec.validate(spec);if(!check.valid)return UI.toast('模板 AppSpec 校验失败：'+check.errors.map(e=>e.path).join('、'),'err');
    ensureCollection('appSpecs').push(spec);ensureCollection('apps').push({id,name:t.name,desc:t.desc,type:'form',icon:t.icon,status:'draft',version:'v0.1.0',owner:'当前用户',updated:now,tags:['模板',key],env:{dev:'v0.1.0',test:'—',prod:'—'}});
    ensureCollection('models').push(...models);ensureCollection('forms').push(form);
    ensureCollection('appVersions').push({appId:id,list:[{v:'v0.1.0',time:now,by:'当前用户',note:'从模板 '+key+' 创建',type:'template',snapshot:{app:structuredClone(Store.find('apps',id)),appSpec:structuredClone(spec),models:structuredClone(models),forms:structuredClone([form]),logicFlows:[],bpmDefs:[]}}]});
    Store.save();UI.closeModal();this.draw();UI.toast('模板已实例化为应用草稿，可继续编辑');
  },
  manualCreate() {
    UI.modal({title:'手工创建应用',icon:'📝',body:UI.drawerForm([
      {key:'name',label:'应用名称',req:true,ph:'如：售后服务管理'},
      {key:'desc',label:'应用描述',type:'textarea'},
      {key:'type',label:'应用类型',type:'select',options:[{v:'form',l:'表单类'},{v:'workflow',l:'工作流类'},{v:'code',l:'自定义编码'}]},
      {key:'icon',label:'图标(emoji)',value:'🧩'},
      {key:'acl',label:'访问权限',type:'select',options:[{v:'private',l:'私有'},{v:'team',l:'团队可见'},{v:'public',l:'公开'}]}
    ]),okText:'创建',onOk:()=>{
      const f=UI.collectForm();if(!f.name?.trim())return UI.toast('名称必填','err');
      const id='app_'+Date.now(),now=new Date().toISOString();
      const app={id,name:f.name.trim(),desc:f.desc||'',type:f.type||'form',icon:f.icon||'🧩',status:'draft',version:'v0.1.0',owner:'当前用户',updated:now,tags:[],acl:f.acl||'private',env:{dev:'v0.1.0',test:'—',prod:'—'}};
      const spec={schemaVersion:'1.0.0',meta:{appId:id,name:app.name,description:app.desc,version:'0.1.0',status:'draft',createdAt:now,source:'manual'},
        dataModels:[],relations:[],ui:{pages:[]},forms:[],logic:[],workflows:[],security:{roles:['应用管理员'],auditRequired:true},
        i18n:{locales:['zh-CN']},deployment:{status:'not-deployed',environments:['dev','test','prod']}};
      const check=AppSpec.validate(spec);if(!check.valid)return UI.toast('AppSpec 校验失败：'+check.errors.map(e=>e.path).join('、'),'err');
      ensureCollection('apps').push(app);ensureCollection('appSpecs').push(spec);
      ensureCollection('appVersions').push({appId:id,list:[{v:'v0.1.0',time:now,by:'当前用户',note:'手工创建应用',type:'manual',snapshot:{app:structuredClone(app),appSpec:structuredClone(spec),models:[],forms:[],logicFlows:[],bpmDefs:[]}}]});
      Store.save();UI.closeModal();this.draw();UI.toast('应用及初始 AppSpec 草稿已创建');
    }});
  },
  versions(id) {
    const record=(Store.get('appVersions')||[]).find(x=>x.appId===id),versions=record?.list||[];
    if(!versions.length)return UI.toast('该应用暂无版本记录','info');
    UI.modal({title:'应用版本历史',size:'lg',footer:false,body:versions.map((v,i)=>'<div class="item flex"><div><b>'+UI.esc(v.v)+'</b><div class="muted">'+UI.esc(v.note||'')+' · '+UI.esc(v.by||'')+' · '+UI.esc(v.time||'')+'</div></div><span class="spacer"></span><span class="tag tag-gray">'+UI.esc(v.type||'version')+'</span><button class="btn btn-sm" onclick="AppsM.rollback(\''+id+'\','+i+')">恢复此版本</button></div>').join('')});
  },
  rollback(id,index) {
    const record=(Store.get('appVersions')||[]).find(x=>x.appId===id),v=record?.list?.[index];
    if(!v?.snapshot)return UI.toast('该历史版本没有完整快照，不能执行恢复','warn');
    const snap=v.snapshot;
    const replace=(key,items)=>{Store.data[key]=(Store.data[key]||[]).filter(x=>x.appId!==id).concat(structuredClone(items||[]));};
    const replaceSpecs=items=>{Store.data.appSpecs=(Store.data.appSpecs||[]).filter(x=>x.meta?.appId!==id).concat(structuredClone(items||[]));};
    const apps=Store.data.apps||[],pos=apps.findIndex(x=>x.id===id);if(pos<0)return UI.toast('应用不存在','err');
    apps[pos]=structuredClone(snap.app);replaceSpecs(snap.appSpec?[snap.appSpec]:[]);
    ['models','forms','logicFlows','bpmDefs'].forEach(k=>replace(k,snap[k]));
    const next='v'+(Number(String(apps[pos].version||'v0').replace(/\D/g,''))+1);
    apps[pos].version=next;apps[pos].status='draft';apps[pos].updated=new Date().toISOString();
    record.list.unshift({v:next,time:new Date().toISOString(),by:'当前用户',note:'从 '+v.v+' 恢复并创建新修订',type:'rollback',snapshot:snapshotApp(id)});
    Store.save();UI.closeModal();this.draw();UI.toast('已从历史快照恢复为新草稿 '+next);
  },
  artifact(id) {
    const snapshot=snapshotApp(id);if(!snapshot)return UI.toast('应用不存在','err');
    UI.modal({title:'生成应用配置制品',icon:'📦',body:
      '<p>制品将包含 AppSpec、数据模型、表单、逻辑流程和 BPM 定义。</p>'+
      '<label class="flex"><input type="checkbox" id="artSchema" checked>包含数据模型与 Schema 定义</label>'+
      '<label class="flex"><input type="checkbox" id="artSeed">包含演示种子数据（请勿用于生产）</label>'+
      '<label class="flex"><input type="checkbox" id="artAssets" checked>包含资源清单</label>'+
      '<p class="help">浏览器原型生成的是 JSON 配置包，不是已签名、可部署的生产制品。</p>',
      okText:'生成并下载 JSON',onOk:()=>{
        const includeSeed=document.getElementById('artSeed').checked;
        const artifact={format:'openailcap-app-bundle',bundleVersion:'1.0.0',generatedAt:new Date().toISOString(),
          app:snapshot.app,appSpecs:snapshot.appSpec,models:document.getElementById('artSchema').checked?snapshot.models:[],
          relations:snapshot.relations,forms:snapshot.forms,logicFlows:snapshot.logicFlows,bpmDefs:snapshot.bpmDefs,
          assets:document.getElementById('artAssets').checked?[]:undefined,seedData:includeSeed?{}:undefined};
        const bytes=JSON.stringify(artifact);
        const record={id:'art_'+Date.now(),appId:id,version:snapshot.app.version,format:artifact.format,generatedAt:artifact.generatedAt,sizeBytes:new Blob([bytes]).size,status:'downloaded'};
        ensureCollection('artifacts').push(record);Store.save();downloadJson((snapshot.app.name||id).replace(/[^\p{L}\p{N}_-]+/gu,'_')+'_'+snapshot.app.version+'.json',artifact);
        UI.closeModal();UI.toast('配置 JSON 包已生成并下载；未执行生产签名或部署');
      }});
  },
  share(id) {
    UI.modal({title:'应用访问授权（原型本地记录）',icon:'🔗',body:
      '<div class="form-item"><label>用户标识/邮箱</label><input class="input" id="shareTo" placeholder="user@example.com"></div>'+
      '<div class="form-item"><label>授权角色</label><select class="input" id="shareRole"><option value="viewer">可查看</option><option value="editor">可编辑</option><option value="admin">管理员</option></select></div>'+
      '<p class="help">当前仅将授权申请保存到浏览器原型数据，不发送邮件、不产生可访问链接；生产环境需由后端鉴权服务签发邀请。</p>',
      okText:'保存授权申请',onOk:()=>{
        const subject=document.getElementById('shareTo').value.trim();if(!subject)return UI.toast('请输入用户标识','err');
        ensureCollection('appShares').push({id:'share_'+Date.now(),appId:id,subject,role:document.getElementById('shareRole').value,status:'pending',createdAt:new Date().toISOString()});
        Store.save();UI.closeModal();UI.toast('授权申请已保存在本地原型记录中');
      }});
  },
  exportApp(id) {const snap=snapshotApp(id);if(!snap)return UI.toast('应用不存在','err');downloadJson(snap.app.name+'_configuration.json',snap);},
  exportAll() {
    const apps=Store.get('apps')||[];const bundles=apps.map(a=>snapshotApp(a.id));
    downloadJson('openailcap-applications-export.json',{format:'openailcap-export',version:'1.0.0',exportedAt:new Date().toISOString(),applications:bundles});
    UI.toast('应用配置导出文件已生成');
  }
});
