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

  /* AI wizard: describe → clarify → plan → generate */
  aiWizard() {
    let step = 0; const answers = {};
    const questions = [
      { q:'1️⃣ 这是什么行业的系统？', opts:['电商','B2B','制造','通用'] },
      { q:'2️⃣ 预计并发用户量？', opts:['<100','100-1000','>1000'] },
      { q:'3️⃣ 需要哪些模块？', opts:['表单+数据','+工作流审批','+报表分析','全部'] },
      { q:'4️⃣ 数据是否需要国密加密？', opts:['是(合规)','否'] },
    ];
    const draw = () => {
      if (step < questions.length) {
        UI.modal({ title:'AI 生成向导 · 需求澄清', icon:'🤖', size:'lg', footer:false, body:`
          <div class="gen-steps">${['需求','澄清','计划','生成'].map((s,i)=>`<div class="gen-step ${i===1?'doing':''}">${s}</div>`).join('')}</div>
          <div class="gen-step done" style="display:none"></div>
          <p style="font-size:13px;font-weight:700;margin-bottom:10px">${questions[step].q}</p>
          <div class="btn-row wrap">
            ${questions[step].opts.map(o=>`<button class="btn" onclick="AppsM.aiAnswer('${o}')">${o}</button>`).join('')}
          </div>`});
      } else if (step === questions.length) {
        const plan = `📦 应用名称：销售订单管理系统\n🏢 行业：${answers[0]}　并发：${answers[1]}　模块：${answers[2]}　国密：${answers[3]}\n\n📊 数据模型（3 张表 18 字段）：Order / Customer / OrderLine\n🧭 工作流（3 环节）：主管审批 → 金额网关(≥10万→总经理) → 仓库验收\n🔐 角色（3 个）：销售专员 / 销售主管 / 管理员\n📈 报表（2 个）：月度销售统计、订单趋势\n🛡️ 合规：手机号/金额 SM4 加密、全操作审计`;
        UI.modal({ title:'AI 生成向导 · 生成计划确认', icon:'📋', size:'lg', body:
          `<div class="gen-steps">${['需求','澄清','计划','生成'].map((s,i)=>`<div class="gen-step ${i<2?'done':i===2?'doing':''}">${s}</div>`).join('')}</div>
          <div class="code-view" style="max-height:230px">${UI.esc(plan)}</div>`,
          okText:'🚀 确认并生成', onOk:() => AppsM.aiRun() });
      }
    };
    this._answers = answers; this._drawAI = draw; draw();
  },
  aiAnswer(v) { this._answers[this._step||(this._step=0)] = v; this._step++; this._drawAI(); },
  aiRun() {
    let s = 0; const names = ['解析需求(NLU)','生成数据模型','生成表单定义','生成 BPM 流程','配置权限/国密','打包制品'];
    UI.modal({ title:'AI 正在生成…', icon:'⚡', size:'lg', footer:false, body:`
      <div class="gen-steps" id="genSteps">${names.map((n,i)=>`<div class="gen-step" id="gs${i}">${n}</div>`).join('')}</div>
      <div class="progress"><i id="genBar" style="width:0%"></i></div>
      <div class="muted mt10" id="genLog">排队中…</div>` });
    const timer = setInterval(() => {
      if (s < names.length) {
        document.getElementById('gs'+s)?.classList.add('done');
        document.getElementById('genLog').textContent = '✓ ' + names[s] + ' 完成';
        s++; const gs = document.getElementById('gs'+s); if (gs) gs.classList.add('doing');
        document.getElementById('genBar').style.width = (s/names.length*100)+'%';
      } else {
        clearInterval(timer); UI.closeModal();
        Store.push('apps', { id:'app_'+Date.now(), name:'销售订单管理系统(AI)', desc:'AI 一句话生成：电商订单全流程', type:'form', icon:'🛒', status:'draft', version:'v0.1.0', owner:'AI 助手', updated:'刚刚', tags:['AI生成'], env:{dev:'v0.1.0',test:'—',prod:'—'} });
        AppsM.draw(); UI.toast('AI 应用生成完成！已加入应用列表'); this._step=0;
      }
    }, 600);
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
