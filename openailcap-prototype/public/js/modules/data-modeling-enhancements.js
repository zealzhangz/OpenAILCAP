/* Data modeling enhancements: AI proposals are written into the model collection only after user confirmation. */
Object.assign(App.mods.model, {
  aiRun() {
    const prompt=document.getElementById('aiBiz')?.value?.trim();
    if(!prompt)return UI.toast('请先描述业务场景','err');
    let defs;
    if(/维修|工单|设备|报修/.test(prompt)){
      defs=[
        {name:'RepairTicket',display:'维修工单',fields:[['id','string',1],['ticket_no','string',1],['device_name','string',1],['fault_desc','text',1],['status','string',1],['created_at','datetime',1]]},
        {name:'EngineerVisit',display:'工程师上门单',fields:[['id','string',1],['ticket_id','string',1],['engineer_name','string',1],['visit_date','datetime',1],['result','text',0]]},
        {name:'PartUsage',display:'配件领用',fields:[['id','string',1],['visit_id','string',1],['part_code','string',1],['qty','int',1],['cost','decimal',1]]},
        {name:'Feedback',display:'服务回访',fields:[['id','string',1],['ticket_id','string',1],['score','int',1],['comment','text',0]]}
      ];
    }else if(/请假|考勤|员工/.test(prompt)){
      defs=[
        {name:'LeaveRequest',display:'请假申请',fields:[['id','string',1],['employee_name','string',1],['leave_type','string',1],['start_at','datetime',1],['end_at','datetime',1],['reason','text',0]]},
        {name:'Employee',display:'员工档案',fields:[['id','string',1],['employee_no','string',1],['name','string',1],['department','string',1]]}
      ];
    }else if(/订单|采购|销售/.test(prompt)){
      defs=[
        {name:'BusinessOrder',display:'业务订单',fields:[['id','string',1],['order_no','string',1],['customer_id','string',1],['amount','decimal',1],['status','string',1],['created_at','datetime',1]]},
        {name:'Customer',display:'客户档案',fields:[['id','string',1],['name','string',1],['phone','string',0],['email','string',0]]},
        {name:'OrderItem',display:'订单明细',fields:[['id','string',1],['order_id','string',1],['product_name','string',1],['qty','int',1],['price','decimal',1]]}
      ];
    }else{
      defs=[
        {name:'BusinessRecord',display:'业务主记录',fields:[['id','string',1],['record_no','string',1],['title','string',1],['description','text',0],['status','string',1]]},
        {name:'BusinessParty',display:'业务对象',fields:[['id','string',1],['name','string',1],['contact','string',0]]},
        {name:'ActivityLog',display:'业务活动记录',fields:[['id','string',1],['record_id','string',1],['action','string',1],['created_at','datetime',1]]}
      ];
    }
    const stamp=Date.now(),appId='app_001';
    this._pendingAiModels=defs.map((d,i)=>({id:'ai_model_'+stamp+'_'+i,name:d.name,display:d.display,appId,x:50+(i%2)*360,y:40+Math.floor(i/2)*250,fields:d.fields.map((x,j)=>({name:x[0],type:x[1],pk:j===0,req:!!x[2],len:x[1]==='string'?128:undefined}))}));
    const links=[];
    for(let i=1;i<this._pendingAiModels.length;i++){
      const parent=this._pendingAiModels[0],child=this._pendingAiModels[i];
      const fk=child.fields.find(x=>x.name.endsWith('_id'));
      if(fk)links.push({id:'ai_rel_'+stamp+'_'+i,from:child.id,f:fk.name,to:parent.id,t:'id',type:'N:1'});
    }
    this._pendingAiRelations=links;
    const html=this._pendingAiModels.map(m=>'<div class="item"><b>'+m.display+'</b> <span class="tag tag-gray">'+m.name+'</span><div class="muted">'+m.fields.map(f=>f.name+':'+f.type).join(' · ')+'</div></div>').join('');
    const out=document.getElementById('aiModelOut');
    out.innerHTML='<div class="success">已根据描述生成 '+this._pendingAiModels.length+' 个候选实体和 '+links.length+' 条关系（本地规则模板）。</div>'+html+
      '<button class="btn btn-p mt10" onclick="ModelM.applyAiModels()">确认加入 ER 画布</button>';
  },
  applyAiModels() {
    const models=this._pendingAiModels||[];
    if(!models.length)return UI.toast('没有待加入的模型','warn');
    models.forEach(m=>Store.push('models',m));
    (this._pendingAiRelations||[]).forEach(r=>Store.push('relations',r));
    Store.data.appSpecs=Store.data.appSpecs||[];
    Store.data.appSpecs.push({schemaVersion:'1.0.0',meta:{appId:'app_001',source:'data-model-ai-template',prompt:document.getElementById('aiBiz')?.value||''},dataModels:models});
    Store.save();this._pendingAiModels=[];this._pendingAiRelations=[];
    UI.closeModal();this.drawTables();this.drawRelations();
    UI.toast('实体与关系已写入数据模型并持久化');
  },
  migrationPreview() {
    const models=Store.get('models');
    const rows=models.map(m=>'<tr><td>'+UI.esc(m.display)+'</td><td>'+m.fields.length+'</td><td>CREATE/ALTER 计划</td><td><span class="tag tag-orange">待数据库验证</span></td></tr>').join('');
    UI.modal({title:'数据结构迁移预览',size:'lg',footer:false,body:
      '<p class="muted">基于当前模型集合生成迁移清单。此 UI 原型不连接真实 PostgreSQL，不能将预览视为已执行迁移。</p>'+
      '<table class="tbl"><thead><tr><th>实体</th><th>字段数</th><th>迁移动作</th><th>验证状态</th></tr></thead><tbody>'+rows+'</tbody></table>'});
  },
  genDDL() {
    const models=Store.get('models');
    const types={string:'VARCHAR(255)',text:'TEXT',int:'INTEGER',decimal:'NUMERIC(18,2)',boolean:'BOOLEAN',datetime:'TIMESTAMPTZ',json:'JSONB',enum:'VARCHAR(64)'};
    const ddl=models.map(m=>{
      const cols=m.fields.map(f=>{
        let line='  "'+f.name+'" '+(types[f.type]||'TEXT');
        if(f.pk)line+=' PRIMARY KEY';
        else if(f.req)line+=' NOT NULL';
        if(f.unique)line+=' UNIQUE';
        return line;
      });
      return 'CREATE TABLE IF NOT EXISTS "'+m.name.toLowerCase()+'" (\\n'+cols.join(',\\n')+'\\n);';
    }).join('\\n\\n');
    UI.modal({title:'基于当前模型生成 SQL DDL',size:'lg',footer:false,body:
      '<div class="code-view"><pre>'+UI.esc(ddl)+'</pre></div>'+
      '<p class="help">生成结果来自当前模型字段；正式迁移前还需执行外键、索引、租户策略和 PostgreSQL 迁移验证。</p>'});
  }
});


/* Replace the former lossy text formatter with a deterministic, validated generator. */
App.mods.model.genSchema=function(id){
  try{
    const schema=PrismaSchema.generate(Store.get('models'),Store.get('relations'),id);
    UI.modal({title:'Prisma Schema · 结构预览',size:'lg',footer:false,body:
      '<p class="muted">由当前模型与关系确定性生成；仅为本地预览，不会连接数据库或执行迁移。</p>'+
      '<div class="code-tabs"><button class="btn btn-sm btn-p">prisma/schema.prisma</button>'+
      '<button class="btn btn-sm" onclick="ModelM.copySchema()">📋 复制</button></div>'+
      '<div class="code-view"><pre id="generatedPrismaSchema">'+UI.esc(schema)+'</pre></div>'+
      '<p class="help">执行前请在目标项目中运行 Prisma validate，并审查数据库迁移差异。</p>'});
    this._lastGeneratedSchema=schema;
  }catch(error){UI.modal({title:'Prisma Schema 校验失败',footer:false,body:
    '<div class="alert alert-error"><b>无法生成 Schema</b><pre>'+UI.esc(error.message)+'</pre></div>'+
    '<p class="help">修正模型标识符、字段类型、主键或关系引用后重试。</p>'});}
};
App.mods.model.copySchema=async function(){
  if(!this._lastGeneratedSchema)return UI.toast('请先生成 Schema','warn');
  try{await navigator.clipboard.writeText(this._lastGeneratedSchema);UI.toast('Prisma Schema 已复制');}
  catch(e){UI.toast('浏览器未授予剪贴板权限，请手动选择代码复制','warn');}
};
