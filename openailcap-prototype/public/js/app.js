/* ============ App — router / nav / lang / theme / search / AI assistant ============ */
const App = {
  lang: 'zh-CN', route: 'home', mods: {},

  NAV: [
    { group:'nav.group.dev' },
    { id:'home',    ico:'🏠', label:'nav.home' },
    { id:'apps',    ico:'📱', label:'nav.apps' },
    { id:'org',     ico:'🏢', label:'nav.org' },
    { id:'model',   ico:'📊', label:'nav.model' },
    { id:'form',    ico:'🧩', label:'nav.form' },
    { id:'flow',    ico:'🔀', label:'nav.flow' },
    { id:'bpm',     ico:'🧭', label:'nav.bpm' },
    { id:'code',    ico:'💻', label:'nav.code' },
    { group:'nav.group.run' },
    { id:'tasks',   ico:'✅', label:'nav.tasks', badge:()=>Store.get('tasks').filter(t=>t.state==='pending').length },
    { id:'inst',    ico:'📄', label:'nav.inst' },
    { id:'report',  ico:'📈', label:'nav.report' },
    { id:'screen',  ico:'🖥️', label:'nav.screen' },
    { id:'data',    ico:'🗄️', label:'nav.data' },
    { group:'nav.group.gov' },
    { id:'settings',ico:'⚙️', label:'nav.settings' },
    { id:'perm',    ico:'🔐', label:'nav.perm' },
    { id:'sec',     ico:'🛡️', label:'nav.sec' },
    { id:'ops',     ico:'🚀', label:'nav.ops' },
    { id:'msg',     ico:'🔔', label:'nav.msg', badge:()=>3 },
  ],

  boot() {
    Store.load();
    // register module aliases (FormM, LogicM, ...) for cross-module & onclick references
    const aliasMap = { apps:'AppsM', org:'OrgM', model:'ModelM', form:'FormM', flow:'LogicM', bpm:'BpmM',
      tasks:'TasksM', inst:'InstM', report:'ReportM', screen:'ScreenM', settings:'SettingsM',
      perm:'PermM', data:'DataM', code:'CodeM', sec:'SecM', ops:'OpsM', msg:'MsgM' };
    for (const [r, a] of Object.entries(aliasMap)) if (this.mods[r]) globalThis[a] = this.mods[r];
    this.renderNav();
    this.bindTopbar();
    this.bindAI();
    this.go('home');
  },

  renderNav() {
    const nav = document.getElementById('nav');
    nav.innerHTML = this.NAV.map(n => {
      if (n.group) return `<div class="nav-group-title">${I18N.t(n.group)}</div>`;
      const b = n.badge ? n.badge() : 0;
      return `<div class="nav-item" data-route="${n.id}" onclick="App.go('${n.id}')">
        <span class="ico">${n.ico}</span>${I18N.t(n.label)}
        ${b ? `<span class="badge">${b}</span>` : ''}</div>`;
    }).join('');
  },

  go(route, param) {
    this.route = route;
    document.querySelectorAll('.nav-item').forEach(el => el.classList.toggle('active', el.dataset.route===route));
    const n = this.NAV.find(x=>x.id===route);
    document.getElementById('crumb').innerHTML = n ? `${I18N.t(n.group||'nav.group.dev')} / <b style="color:var(--text)">${I18N.t(n.label)}</b>` : '';
    const page = document.getElementById('page');
    const mod = this.mods[route];
    page.innerHTML = mod ? mod.render(param) : `<div class="empty"><div class="big">🚧</div>页面开发中…</div>`;
    if (mod && mod.mount) setTimeout(()=>mod.mount(param), 30);
    this.bindI18nNodes();
  },

  bindI18nNodes() {
    document.querySelectorAll('[data-i18n]').forEach(el => { el.textContent = I18N.t(el.dataset.i18n); });
  },

  switchLang() {
    this.lang = this.lang==='zh-CN' ? 'en-US' : 'zh-CN';
    document.getElementById('langLabel').textContent = this.lang==='zh-CN'?'中':'EN';
    document.documentElement.lang = this.lang;
    this.renderNav(); this.go(this.route);
    UI.toast(this.lang==='zh-CN' ? '已切换为中文' : 'Switched to English', 'info');
  },

  bindTopbar() {
    document.getElementById('btnLang').onclick = () => this.switchLang();
    document.getElementById('btnSearch').onclick = () => this.openSearch();
    document.getElementById('btnMsg').onclick = () => this.go('msg');
    document.getElementById('btnTheme').onclick = (e) => {
      const b = e.currentTarget; const dark = b.textContent==='🌙';
      b.textContent = dark ? '☀️' : '🌙';
      document.documentElement.style.filter = dark ? 'invert(0.92) hue-rotate(180deg)' : '';
      UI.toast(dark?'暗色模式（演示）':'已恢复亮色', 'info');
    };
    document.addEventListener('keydown', e => {
      if ((e.ctrlKey||e.metaKey) && e.key==='k') { e.preventDefault(); this.openSearch(); }
      if ((e.ctrlKey||e.metaKey) && e.key==='i') { e.preventDefault(); AI.toggle(); }
    });
  },

  openSearch() {
    document.getElementById('searchMask').classList.add('open');
    const inp = document.getElementById('searchInput');
    inp.focus(); inp.oninput = () => this.doSearch(inp.value);
    this.doSearch('');
  },

  doSearch(q) {
    q = (q||'').trim().toLowerCase();
    const res = [];
    const push=(icon,text,route)=>{ if(!q || text.toLowerCase().includes(q)) res.push({icon,text,route}); };
    Store.get('apps').forEach(a=>push('📱', a.name+' '+a.desc, 'apps'));
    Store.get('models').forEach(m=>push('📊', m.display+' '+m.name, 'model'));
    Store.get('bpmDefs').forEach(b=>push('🧭', b.name, 'bpm'));
    Store.get('logicFlows').forEach(f=>push('🔀', f.name, 'flow'));
    Store.get('employees').forEach(e=>push('👤', e.name+' '+e.code, 'org'));
    Store.get('dicts').forEach(d=>push('📖', d.name, 'settings'));
    Store.get('reports').forEach(r=>push('📈', r.name, 'report'));
    document.getElementById('searchResults').innerHTML = res.length
      ? res.slice(0,8).map(r=>`<div class="item" onclick="UI.closeSearch();App.go('${r.route}')" style="cursor:pointer">${r.icon} <b>${UI.esc(r.text)}</b></div>`).join('')
      : `<div class="muted" style="padding:10px">未找到匹配结果</div>`;
  },

  /* ---------- AI assistant ---------- */
  bindAI() {
    document.getElementById('aiFab').onclick = () => AI.toggle();
    document.getElementById('aiClose').onclick = () => AI.toggle();
    document.getElementById('aiSend').onclick = () => AI.send();
    document.getElementById('aiInput').addEventListener('keydown', e => {
      if (e.key==='Enter' && !e.shiftKey) { e.preventDefault(); AI.send(); }
    });
    AI.greet();
  },
};

/* ---------- AI assistant engine (rule-based demo, mimicking LLM) ---------- */
const AI = {
  toggle() { document.getElementById('aiPanel').classList.toggle('open'); },
  msgs: [],
  greet() {
    this.push('ai', `你好！我是 OpenAILCAP 开发助手 🤖\n我可以帮你：\n• 一句话生成应用（表单/流程/报表）\n• 生成数据模型与 Prisma Schema\n• 生成逻辑编排代码\n• 解释平台任何功能\n\n试试下面的快捷指令，或直接输入需求。`);
    this.renderChips();
  },
  renderChips() {
    const chips = ['生成请假审批应用','设计客户数据模型','写订单折扣计算函数','当前待办有哪些?','如何配置审批人?'];
    document.getElementById('aiChips').innerHTML = chips.map(c=>`<span class="ai-chip" onclick="AI.quick('${c}')">${c}</span>`).join('');
  },
  quick(t) { document.getElementById('aiInput').value = t; this.send(); },
  push(role, text, typing=false) {
    this.msgs.push({role, text});
    const box = document.getElementById('aiMsgs');
    const el = document.createElement('div');
    el.className = 'msg ' + role;
    if (typing) el.innerHTML = `<span class="typing"><i></i><i></i><i></i></span>`;
    else el.textContent = text;
    box.appendChild(el); box.scrollTop = box.scrollHeight;
    return el;
  },
  send() {
    const inp = document.getElementById('aiInput');
    const q = inp.value.trim(); if (!q) return;
    inp.value = ''; this.push('user', q);
    const typing = this.push('ai', '', true);
    setTimeout(() => { typing.innerHTML = ''; typing.textContent = this.reply(q); }, 700 + Math.random()*600);
  },
  reply(q) {
    const text=String(q||'').trim(),s=text.toLowerCase();
    if (/生成|创建|搭建|开发一个/.test(text) && /应用|系统|审批|工单|管理/.test(text)) {
      if (globalThis.AppsM?.aiWizard) {
        AppsM.aiWizard();
        return '已打开应用生成向导。当前原型使用本地规则模板，不会调用真实大模型；请在向导中补充需求、确认计划，生成结果会先保存为可编辑草稿。';
      }
      return '应用生成模块尚未就绪，请先打开应用管理页面。';
    }
    if (s.includes('模型') || s.includes('数据表') || s.includes('er')) {
      App.go('model');
      return '已打开数据建模工作区。这里展示的是浏览器原型数据；如需新增实体，请在画布中操作。当前全局助手不会声称已自动写入模型。';
    }
    if (s.includes('函数') || s.includes('代码') || s.includes('折扣') || s.includes('计算')) {
      App.go('flow');
      return '已打开逻辑编排工作区。可以在此创建节点和连线；当前原型尚未连接真实代码 Agent、编译器或自动化测试服务。';
    }
    if (s.includes('待办') || s.includes('任务')) {
      const pending=Store.get('tasks').filter(t=>t.state==='pending');
      return '当前原型数据中有 '+pending.length+' 项待办：\n\n'+
        (pending.length?pending.map((t,i)=>(i+1)+'. '+t.title+'（'+t.pri+'，SLA '+t.sla+'）').join('\n'):'暂无待办')+
        '\n\n以上来自浏览器本地演示数据，不代表服务端实时任务。';
    }
    if (s.includes('审批人') || s.includes('配置') || s.includes('怎么')) {
      App.go('bpm');
      return '已打开 BPM 流程设计器。原型支持查看和编辑演示流程图；指定人、直属主管、岗位、部门和表达式等审批人策略，仍需连接组织服务和真实 BPM 引擎后才能在运行时生效。';
    }
    if (s.includes('国标') || s.includes('l3') || s.includes('合规') || s.includes('国密')) {
      App.go('sec');
      return '已打开安全合规工作区。请以 doc/整改/GB-T46900-2025_39子域追踪台账.md 的 S0–S5 状态和测试证据为准；原型页面不构成国标符合性结论，国密能力也不能仅凭界面展示认定已实现。';
    }
    return '收到你的问题：「'+text+'」。当前全局助手是本地规则演示，尚未连接真实 LLM/Agent 服务。它可以帮助定位应用管理、数据建模、逻辑编排、BPM、待办和安全合规工作区；不会伪称已经完成生成、测试、部署或合规检查。';
  }
};
