/* ============ Module 1: 应用管理中心 (GB 6.1) ============ */
App.mods.apps = {
  render() {
    const apps = Store.get('apps');
    return `
    <div class="page-head">
      <h1>📱 应用管理</h1><span class="sub">覆盖 GB 6.1.2-6.1.6：信息/发布/版本/制品/开发权限</span>
      <span class="spacer"></span>
      <button class="btn" onclick="AppsM.exportAll()">⬇️ 导出全部</button>
      <button class="btn btn-p" onclick="AppsM.openCreate()">＋ 创建应用</button>
    </div>
    <div class="filter-bar">
      <input class="input" placeholder="🔍 搜索应用…" oninput="AppsM.filter(this.value)">
      <select class="input" onchange="AppsM.filterStatus(this.value)">
        <option value="">全部状态</option><option value="published">已发布</option><option value="draft">草稿</option>
      </select>
      <span class="muted">共 ${apps.length} 个应用</span>
    </div>
    <div class="grid cols-4 mb0" id="appStat">
      <div class="stat-tile"><div class="ic" style="background:var(--primary-soft);color:var(--primary)">📱</div>
        <div><div class="v">${apps.length}</div><div class="l">全部应用</div></div></div>
      <div class="stat-tile"><div class="ic" style="background:var(--success-soft);color:var(--success)">✅</div>
        <div><div class="v">${apps.filter(a=>a.status==='published').length}</div><div class="l">已发布</div></div></div>
      <div class="stat-tile"><div class="ic" style="background:var(--warning-soft);color:var(--warning)">✏️</div>
        <div><div class="v">${apps.filter(a=>a.status==='draft').length}</div><div class="l">草稿中</div></div></div>
      <div class="stat-tile"><div class="ic" style="background:#f3e8ff;color:var(--accent)">🤖</div>
        <div><div class="v">37</div><div class="l">本月 AI 生成</div></div></div>
    </div>
    <div class="card mt14"><div class="card-b" id="appGrid"></div></div>`;
  },
  mount() { this.draw(); },

  draw() {
    const apps = Store.get('apps');
    document.getElementById('appGrid').innerHTML = apps.map(a => `
      <div class="item" style="display:grid;grid-template-columns:44px 1fr auto;gap:12px;align-items:center;border-left-color:${a.status==='published'?'var(--success)':'var(--warning)'}">
        <div style="width:44px;height:44px;border-radius:10px;background:var(--primary-soft);display:grid;place-items:center;font-size:20px">${a.icon}</div>
        <div>
          <div class="flex" style="gap:8px"><b style="font-size:13.5px">${UI.esc(a.name)}</b>
            ${UI.statusTag(a.status)} ${a.tags.map(t=>`<span class="tag tag-purple">${t}</span>`).join('')}</div>
          <div class="muted" style="margin-top:3px">${UI.esc(a.desc)}</div>
          <div class="muted" style="margin-top:4px">${a.version} · ${a.owner} · ${a.updated} · 环境 dev/test/prod: ${a.env.dev}/${a.env.test}/${a.env.prod}</div>
        </div>
        <div class="btn-row" style="justify-content:flex-end">
          <button class="btn btn-sm" onclick="AppsM.detail('${a.id}')">打开</button>
          <button class="btn btn-sm" onclick="AppsM.versions('${a.id}')">版本</button>
          <button class="btn btn-sm" onclick="AppsM.artifact('${a.id}')">制品</button>
          <button class="btn btn-sm" onclick="AppsM.share('${a.id}')">分享</button>
          <button class="btn btn-sm btn-danger" onclick="AppsM.del('${a.id}')">删除</button>
        </div>
      </div>`).join('');
  },

  filter(q) { document.querySelectorAll('#appGrid .item').forEach(el => { el.style.display = el.textContent.toLowerCase().includes(q.toLowerCase()) ? '' : 'none'; }); },
  filterStatus(s) { document.querySelectorAll('#appGrid .item').forEach((el,i) => {
    const a = Store.get('apps')[i]; el.style.display = (!s || a.status===s) ? '' : 'none'; }); },

  /* ---- creation: 3 routes (template / AI / manual) ---- */
  openCreate() {
    UI.modal({ title:'创建应用', icon:'✨', size:'lg', footer:false, body:`
      <div class="flex wrap" style="gap:10px;margin-bottom:14px">
        <button class="btn btn-p" onclick="AppsM.aiWizard()">🤖 AI 一句话生成（推荐）</button>
        <button class="btn" onclick="AppsM.manualCreate()">📝 手工创建</button>
        <button class="btn" onclick="AppsM.fromTemplate()">📦 从模板创建</button>
      </div>
      <div class="grid cols-3" id="tplGrid">
        ${[['CRM 管理系统','👥','客户/商机/跟进'],['进销存','🏬','商品/库存/出入库'],['OA 审批中心','✅','通用审批模板']]
        .map(([n,i,d])=>`<div class="item" style="cursor:pointer" onclick="UI.toast('模板 ${n} 已载入（演示）')">
          <div style="font-size:26px">${i}</div><b>${n}</b><div class="muted">${d}</div></div>`).join('')}
      </div>`});
  },

  /* AI wizard: requirement → clarify → review → generate AppSpec and linked design artifacts */
  aiWizard() {
    this._aiWizard = { step:0, description:'', answers:{} };
    const questions = [
      { q:'这是什么行业/业务场景？', opts:['电商','B2B','制造','通用'] },
      { q:'预计并发用户量？', opts:['小于 100','100–1000','大于 1000'] },
      { q:'需要哪些能力模块？', opts:['表单+数据','表单+数据+审批','表单+数据+审批+报表','全部'] },
      { q:'是否需要国密保护？', opts:['是，需要纳入安全设计','否，按普通数据保护'] },
    ];
    this._drawAI = () => {
      const w = this._aiWizard;
      const step = w.step;
      const progress = ['需求','澄清','计划','生成'];
      if (step === 0) {
        UI.modal({ title:'AI 生成向导 · 需求描述', icon:'🤖', size:'lg', footer:false, body:`
          <div class="gen-steps">${progress.map((s,i)=>`<div class="gen-step ${i===0?'doing':''}">${s}</div>`).join('')}</div>
          <p class="muted" style="margin-bottom:10px">描述希望构建的应用。生成结果会进入应用、数据模型、表单、逻辑和流程设计工作区。</p>
          <textarea class="input" id="aiRequirement" style="min-height:100px" placeholder="例如：建设一个制造企业设备维修工单系统，包含报修、派工、维修、备件领用和验收">${UI.esc(w.description)}</textarea>
          <div class="btn-row" style="justify-content:flex-end;margin-top:12px"><button class="btn btn-p" onclick="AppsM.aiDescribe()">继续需求澄清</button></div>` });
      } else if (step <= questions.length) {
        const q = questions[step-1];
        UI.modal({ title:'AI 生成向导 · 需求澄清', icon:'🤖', size:'lg', footer:false, body:`
          <div class="gen-steps">${progress.map((s,i)=>`<div class="gen-step ${i<1?'done':i===1?'doing':''}">${s}</div>`).join('')}</div>
          <p class="muted" style="margin-bottom:8px">问题 ${step}/${questions.length}</p>
          <p style="font-size:14px;font-weight:700;margin-bottom:12px">${q.q}</p>
          <div class="btn-row wrap">${q.opts.map(o=>`<button class="btn" onclick="AppsM.aiAnswer('${o}')">${o}</button>`).join('')}</div>` });
      } else {
        const a = w.answers;
        const name = this.aiAppName(w.description);
        const plan = [
          '应用名称：'+name,
          '业务需求：'+w.description,
          '行业：'+a[0]+'；并发规模：'+a[1],
          '模块范围：'+a[2]+'；国密要求：'+a[3],
          '',
          '生成对象：AppSpec、数据模型、表单、逻辑流程、审批流程（按模块范围）',
          '安全策略：'+(a[3].startsWith('是')?'字段加密候选标记、最小权限、审计要求；密钥管理需后端 KMS 实现':'最小权限、审计与数据保护策略'),
          '发布策略：生成草稿，不自动部署；用户检查差异后再发布'
        ].join('\n');
        UI.modal({ title:'AI 生成向导 · 计划确认', icon:'📋', size:'lg', body:`
          <div class="gen-steps">${progress.map((s,i)=>`<div class="gen-step ${i<2?'done':i===2?'doing':''}">${s}</div>`).join('')}</div>
          <div class="code-view" style="max-height:280px"><pre>${UI.esc(plan)}</pre></div>
          <p class="help">当前仓库原型使用本地规则模板生成，不代表已连接真实大模型。生成结果可编辑并保存在浏览器原型状态中。</p>`,
          okText:'确认并生成草稿', onOk:() => AppsM.aiRun() });
      }
    };
    this._drawAI();
  },
  aiAppName(description) {
    const s = String(description||'').trim().replace(/[。！？.!?]+$/,'');
    if (!s) return '新建业务应用';
    const cleaned = s.replace(/^(我需要|我要|请帮我|建设|开发|做一个|创建一个|搭建一个)/,'').trim();
    return cleaned.length > 28 ? cleaned.slice(0,28)+'…' : cleaned;
  },
  aiDescribe() {
    const input = document.getElementById('aiRequirement');
    const value = input ? input.value.trim() : '';
    if (!value) return UI.toast('请先描述应用需求','err');
    this._aiWizard.description = value;
    this._aiWizard.step = 1;
    this._drawAI();
  },
  aiAnswer(value) {
    const w = this._aiWizard;
    if (!w || w.step < 1 || w.step > 4) return;
    w.answers[w.step-1] = value;
    w.step += 1;
    this._drawAI();
  },
  aiRun() {
    const w = this._aiWizard;
    if (!w || !w.description || Object.keys(w.answers).length !== 4) {
      UI.closeModal(); return UI.toast('需求信息不完整，请重新运行生成向导','err');
    }
    const appId = 'app_'+Date.now();
    const appName = this.aiAppName(w.description);
    const cryptoRequired = String(w.answers[3]).startsWith('是');
    const useWorkflow = /审批|工作流|流程|全部/.test(w.answers[2]);
    const useReport = /报表|全部/.test(w.answers[2]);
    const mainModelId = 'model_'+appId;
    const partyModelId = 'party_'+appId;
    const formId = 'form_'+appId;
    const flowId = 'logic_'+appId;
    const bpmId = 'bpm_'+appId;
    const mainModel = { id:mainModelId, name:'BusinessRecord', display:'业务主记录', appId, x:60, y:40,
      fields:[
        {name:'id',type:'string',pk:true,req:true,len:36},
        {name:'record_no',type:'string',req:true,unique:true,len:48},
        {name:'title',type:'string',req:true,len:160},
        {name:'description',type:'text'},
        {name:'status',type:'string',req:true,len:32},
        {name:'created_at',type:'datetime',req:true},
        ...(cryptoRequired?[{name:'sensitive_payload',type:'text',encrypt:true}]:[])
      ]};
    const partyModel = { id:partyModelId, name:'BusinessParty', display:'业务对象/客户', appId, x:430, y:60,
      fields:[{name:'id',type:'string',pk:true,req:true,len:36},{name:'name',type:'string',req:true,len:120},{name:'contact',type:'string',encrypt:cryptoRequired}]};
    const relationId = 'rel_'+appId;
    const form = { id:formId, appId, name:appName+' · 主表单', fields:[
      {id:'fld_'+appId+'_1',label:'业务编号',field:'record_no',type:'text',req:true,span:12},
      {id:'fld_'+appId+'_2',label:'业务标题',field:'title',type:'text',req:true,span:12},
      {id:'fld_'+appId+'_3',label:'业务对象',field:'party_id',type:'select',req:true,span:12},
      {id:'fld_'+appId+'_4',label:'业务说明',field:'description',type:'textarea',span:24},
      {id:'fld_'+appId+'_5',label:'状态',field:'status',type:'select',req:true,span:12},
      ...(cryptoRequired?[{id:'fld_'+appId+'_6',label:'敏感信息',field:'sensitive_payload',type:'textarea',span:24,encrypted:true}]:[])
    ]};
    const logic = {id:flowId,name:appName+' · 提交校验',appId,nodes:[
      {id:'start_'+appId,type:'event',label:'表单提交',x:40,y:80},
      {id:'validate_'+appId,type:'condition',label:'必填与权限校验',x:240,y:80,expr:'record_no && title && party_id'},
      {id:'save_'+appId,type:'data',label:'保存业务记录',x:460,y:80,op:'insert'},
      {id:'end_'+appId,type:'end',label:'返回结果',x:680,y:80}
    ],edges:[{f:'start_'+appId,t:'validate_'+appId},{f:'validate_'+appId,t:'save_'+appId,when:'valid'},{f:'save_'+appId,t:'end_'+appId}]};
    const appSpec = {
      schemaVersion:'1.0.0',
      meta:{appId,name:appName,description:w.description,industry:w.answers[0],concurrency:w.answers[1],modules:w.answers[2],cryptoRequired,version:'0.1.0',status:'draft'},
      dataModels:[mainModel,partyModel],
      ui:{pages:[{id:'page_'+appId,name:'业务管理',formId}]},
      forms:[form],
      logic:[logic],
      workflows:useWorkflow?[{id:bpmId,name:appName+' · 审批流程',version:1,nodes:[
        {id:'start',type:'start',label:'开始'},
        {id:'submit',type:'user',label:'业务提交/确认',assignee:'initiator'},
        {id:'approve',type:'user',label:'业务审批',assignee:'role:approver'},
        {id:'end',type:'end',label:'结束'}
      ],edges:[{f:'start',t:'submit'},{f:'submit',t:'approve'},{f:'approve',t:'end'}]}]:[],
      security:{roles:['应用管理员','业务经办人','业务审批人'],cryptoRequired,auditRequired:true},
      reports:useReport?[{id:'report_'+appId,name:appName+' · 业务统计',type:'table-and-trend'}]:[],
      i18n:{locales:['zh-CN','en-US']},
      deployment:{status:'not-deployed',environments:['dev','test','prod']}
    };
    const names=['解析需求','生成 AppSpec','生成数据模型','生成表单定义','生成逻辑编排','生成审批与权限配置','保存草稿'];
    let s=0;
    UI.modal({title:'正在生成应用草稿',icon:'⚙️',size:'lg',footer:false,body:`
      <div class="gen-steps" id="genSteps">${names.map((n,i)=>`<div class="gen-step" id="gs${i}">${n}</div>`).join('')}</div>
      <div class="progress"><i id="genBar" style="width:0%"></i></div><div class="muted mt10" id="genLog">正在准备结构化规格…</div>`});
    const timer=setInterval(()=>{
      if(s<names.length){
        document.getElementById('gs'+s)?.classList.add('done');
        const log=document.getElementById('genLog'); if(log) log.textContent='✓ '+names[s]+' 完成';
        s++;
        const next=document.getElementById('gs'+s); if(next) next.classList.add('doing');
        const bar=document.getElementById('genBar'); if(bar) bar.style.width=(s/names.length*100)+'%';
      } else {
        clearInterval(timer);
        Store.data.appSpecs=Store.data.appSpecs||[];
        Store.data.appSpecs.push(appSpec);
        Store.push('apps',{id:appId,name:appName,desc:w.description,type:useWorkflow?'workflow':'form',icon:'🧩',status:'draft',version:'v0.1.0',owner:'AI 助手',updated:'刚刚',tags:['AI生成',w.answers[0]],env:{dev:'v0.1.0',test:'—',prod:'—'}});
        Store.push('models',mainModel); Store.push('models',partyModel);
        Store.push('relations',{id:relationId,from:mainModelId,f:'party_id',to:partyModelId,t:'id',type:'N:1'});
        Store.push('forms',form); Store.push('logicFlows',logic);
        if(useWorkflow) Store.push('bpmDefs',{id:bpmId,name:appName+' · 审批流程',appId,version:'v1',status:'draft',sla:'按应用配置',nodes:appSpec.workflows[0].nodes,edges:appSpec.workflows[0].edges});
        Store.push('appVersions',{appId,list:[{v:'v0.1.0',time:new Date().toLocaleString(),by:'AI 助手',note:'基于需求描述生成 AppSpec 与设计草稿',type:'AI'}]});
        Store.save();
        UI.closeModal(); this._aiWizard=null; AppsM.draw();
        UI.toast('应用草稿已创建：AppSpec、数据模型、表单、逻辑'+(useWorkflow?'、审批流程':'')+'已写入原型状态');
      }
    },350);
  },

  manualCreate() {
    UI.modal({ title:'手工创建应用', icon:'📝', body:UI.drawerForm([
      {key:'name', label:'应用名称', req:true, ph:'如：售后服务管理'},
      {key:'desc', label:'应用描述', type:'textarea'},
      {key:'type', label:'应用类型', type:'select', options:[{v:'form',l:'表单类'},{v:'workflow',l:'工作流类'},{v:'code',l:'自定义编码'}]},
      {key:'icon', label:'图标(emoji)', value:'🧊'},
      {key:'acl', label:'访问权限', type:'select', options:[{v:'private',l:'私有'},{v:'team',l:'团队可见'},{v:'public',l:'公开'}]},
    ]), okText:'创建', onOk:() => {
      const f = UI.collectForm(); if (!f.name) return UI.toast('名称必填','err');
      Store.push('apps', { id:'app_'+Date.now(), name:f.name, desc:f.desc||'—', type:f.type||'form', icon:f.icon||'🧊', status:'draft', version:'v0.1.0', owner:'张三', updated:'刚刚', tags:[], env:{dev:'v0.1.0',test:'—',prod:'—'} });
      UI.closeModal(); AppsM.draw(); UI.toast('应用创建成功');
    }});
  },
  fromTemplate() { UI.toast('模板已载入草稿应用（演示）'); UI.closeModal(); },

  detail(id) {
    const a = Store.find('apps', id);
    UI.modal({ title:`${a.icon} ${a.name}`, size:'lg', footer:false, body:`
      <div class="tabs" id="adTabs">
        <button class="tab active" onclick="AppDetail.tab(0)">概览</button>
        <button class="tab" onclick="AppDetail.tab(1)">版本历史</button>
        <button class="tab" onclick="AppDetail.tab(2)">制品</button>
        <button class="tab" onclick="AppDetail.tab(3)">开发权限</button>
      </div>
      <div class="tab-pane active" id="adp0">${UI.kvGrid([
        ['应用 ID', a.id],['类型', a.type],['负责人', a.owner],['版本', a.version],
        ['环境', `dev ${a.env.dev} / test ${a.env.test} / prod ${a.env.prod}`],
        ['标签', a.tags.map(t=>`<span class="tag tag-purple">${t}</span>`).join(' ')],
        ['元数据', '分类: 电商核心 / 标签: 订单,发票 (GB 6.1.2 元数据管理)']])}</div>
      <div class="tab-pane" id="adp1"><div class="desc-list">${(Store.get('appVersions')[0]?.list||[]).map(v=>`
        <div class="dl"><span class="dt">${v.v}</span><span class="dd">${v.note} — ${v.by} · ${v.time} <span class="tag ${v.type==='AI'?'tag-purple':'tag-gray'}">${v.type}</span>
        <a class="link" onclick="UI.toast('已回退至 ${v.v}（演示）', 'warn')">回退</a></span></div>`).join('')}</div></div>
      <div class="tab-pane" id="adp2">${(Store.get('artifacts')||[]).map(t=>`<div class="item">📦 ${t.version} · ${t.size} · ${t.time} · ${t.checksum}
        <a class="link" onclick="UI.toast('制品下载中…')">下载</a></div>`).join('')||'<div class="muted">暂无制品</div>'}</div>
      <div class="tab-pane" id="adp3"><div class="perm-matrix" style="--pmc:2">
        <div class="pm-row"><div class="pm-cell head">开发者</div><div class="pm-cell head">界面/模型/编排</div></div>
        ${[['李四','✅✅✅'],['张三','✅✅✅'],['钱七','👁️✅❌']].map(([u,p])=>`<div class="pm-row"><div class="pm-cell res">${u}</div><div class="pm-cell">${p}</div></div>`).join('')}
      </div></div>` });
  },

  versions(id) { UI.toast('请在应用详情 → 版本历史 中查看', 'info'); },
  artifact(id) {
    UI.modal({ title:'生成应用制品', icon:'📦', body:`
      <div class="pipe">
        ${['Schema','种子数据','资源文件','组件清单'].map((s,i)=>`<div class="pipe-step ${i<2?'done':''}" id="ps${i}"><div class="pc">${i<2?'✅':'⏳'}</div>${s}</div>`).join('')}
      </div>
      <div class="filter-bar"><label class="flex"><div class="switch on" id="artSchema"></div>包含 Prisma Schema</label>
      <label class="flex"><div class="switch on" id="artSeed"></div>包含初始化数据</label>
      <label class="flex"><div class="switch on" id="artAssets"></div>包含资源文件</label></div>
      <div class="help">制品将生成 checksum（SM3 完整性校验），支持跨环境导入安装（GB 6.1.5）。</div>`,
      okText:'开始生成', onOk:() => { UI.closeModal(); UI.toast('制品 v2.3.1 已生成（4.2MB），可在制品仓库下载/安装'); }});
  },
  share(id) { UI.modal({ title:'分享应用', icon:'🔗', body:`
    <div class="form-item"><label>分享给（邮箱，逗号分隔）</label><input class="input" id="shareTo" placeholder="dev@hc.com, pm@hc.com"></div>
    <div class="form-item"><label>权限</label><select class="input" id="shareRole"><option>可查看</option><option>可编辑</option><option>管理员</option></select></div>
    <div class="item mono">只读链接: https://oac.hc.com/s/${id.slice(-6)}?t=8h</div>`,
    okText:'发送邀请', onOk:() => { UI.closeModal(); UI.toast('邀请已发送'); }});
  },
  del(id) { const a = Store.find('apps', id);
    UI.confirm(`确定删除应用 <b>${UI.esc(a.name)}</b>？<br><span class="muted">应用会进入回收站保留 30 天（GB 6.1.2 删除操作）</span>`, () => {
      Store.remove('apps', id); AppsM.draw(); UI.toast('已移入回收站'); });
  },
  exportAll() { UI.toast('已导出 5 个应用的配置包（demo.json）'); },
  exportApp(id) { UI.toast('应用配置已导出'); },
};
const AppDetail = { tab(i) { document.querySelectorAll('#adTabs .tab').forEach((t,j)=>t.classList.toggle('active',i===j));
  document.querySelectorAll('#adTabs ~ .tab-pane, [id^="adp"]').forEach((p,j)=>p.classList.toggle('active', j===i)); } };
