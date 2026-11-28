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
    const s = q.toLowerCase();
    if (s.includes('请假') || s.includes('审批') || s.includes('流程')) return `好的，我已理解你想要【请假审批】类应用。基于澄清对话，建议如下方案：\n\n📋 数据模型：LeaveRequest（emp_id, days, type, reason）\n🧭 BPM 流程：直属主管 → (days>3? 部门总监) → HR 备案\n🔐 角色：员工/主管/HR\n📈 报表：请假统计（按类型/部门）\n\n已为你生成草稿应用「请假审批」，去【应用管理】查看 → 点右上角"打开"即可编辑。`;
    if (s.includes('模型') || s.includes('数据表') || s.includes('er')) return `我推荐的数据模型如下（已同步到【数据建模】画布）：\n\nCustomer 客户表：id🔑 name level(dict) phone(SM4加密) email\nOrder 订单表：id🔑 order_no(UQ) customer_id→Customer amount status(dict) order_date\nOrderLine 明细：id🔑 order_id→Order sku qty price\n\n关系：Order N:1 Customer；OrderLine N:1 Order\n索引建议：order_no 唯一索引、(customer_id, order_date) 复合索引。`;
    if (s.includes('函数') || s.includes('代码') || s.includes('折扣') || s.includes('计算')) return `已为你生成 TypeScript 函数（可在【逻辑编排】或【代码开发】中查看）：\n\nfunction calcDiscount(order, customer) {\n  if (customer.level==='A1' && order.amount>100000) return 0.15;\n  if (customer.level==='A2') return 0.10;\n  if (order.amount>10000) return 0.05;\n  return 0;\n}\n\n配套单测 8 个用例已生成，覆盖率 96%。安全性检查：无注入风险 ✅`;
    if (s.includes('待办') || s.includes('任务')) return `你当前有 ${Store.get('tasks').filter(t=>t.state==='pending').length} 个待办：\n\n🔴 订单 SO-2026-1101 审批（3h12m 后超期）\n🟠 请假单 LV-2026-088 审批（1 天内）\n🔴 合同 CT-2026-032 用印审批（已超期 2h）\n\n建议优先处理已超期的用印审批。去【任务待办】处理 →`;
    if (s.includes('审批人') || s.includes('配置') || s.includes('怎么')) return `BPM 审批人支持 5 种配置方式（【BPM 流程】→ 选中节点 → 右侧面板）：\n1️⃣ 指定人：直接选某个员工\n2️⃣ 直属主管：按组织架构汇报线自动定位\n3️⃣ 指定岗位：如"总经理(p1)"所有在职人员\n4️⃣ 指定部门：如"仓库验收 → 销售一部(d3)"\n5️⃣ 表达式：如 \${order.owner.dept.manager}\n\n也可开启 AI 智能分配（按负载+专长加权）。`;
    return `收到！关于「${q}」\n\n我结合平台知识给出要点：\n• 若是新建应用 → 推荐走"AI 一句话生成"，5 分钟出骨架\n• 若是复杂逻辑 → 用【逻辑编排】可视化节点，可导出 TS 代码\n• 若涉及权限 → 【权限管理】矩阵支持到按钮/字段级\n• 国标合规相关 → 【安全合规】已内置国密 SM2/3/4\n\n需要我直接帮你做哪一步？可以回复"生成XX应用"或"打开XX模块"。`;
  },
};
