/* ============ Module 12: 代码开发 (GB 6.2.8 + 6.4.2) ============ */
App.mods.code = {
  tab: 0,
  FILES: [
    {p:'services/', n:'order.ts', t:'service', code:
`import { db } from '@/lib/db';
import { cache } from '@/lib/cache';

/** 计算订单折扣 — AI 生成 + 人工微调 */
export async function calcDiscount(order: Order, customer: Customer) {
  if (!order || !customer) throw new Error('invalid input');   // 参数校验
  const key = \`disc:\${customer.id}\`;
  const cached = await cache.get(key);                          // 资源隔离缓存
  if (cached) return cached;

  let rate = 0;
  if (customer.level === 'A1' && order.amount > 100000) rate = 0.15;
  else if (customer.level === 'A2') rate = 0.10;
  else if (order.amount > 10000) rate = 0.05;

  await cache.set(key, rate, 60);                               // TTL 60s
  return rate;
}` },
    {p:'services/', n:'leave.ts', t:'service', code:
`/** 请假审批辅助：按组织架构定位审批人 */
export async function resolveApprover(empId: string) {
  const emp = await db.employee.findUnique({ where: { id: empId }, include: { manager: true } });
  if (!emp?.manager) throw new Error('未配置直属主管');
  return emp.manager.id;                                        // GB 6.2.3.3.1 汇报线
}` },
    {p:'functions/', n:'invoice.ts', t:'custom fn', code:
`/** 自定义函数（GB 6.4.2.3 a） */
export function invoiceTitle(order: Order): string {
  return order.invoice ?? order.customer.name;
}` },
  ],
  render() {
    return `
    <div class="page-head"><h1>💻 代码开发</h1><span class="sub">Monaco 编辑器 · AI 补全/单测生成/审查 · 断点调试 · 版本管理</span><span class="spacer"></span>
      <button class="btn" onclick="CodeM.aiTest()">🧪 AI 生成单测</button>
      <button class="btn" onclick="CodeM.review()">🩺 代码审查</button>
      <button class="btn" onclick="CodeM.debug()">🐞 断点调试</button>
      <button class="btn" onclick="UI.toast('已提交 Git commit 3f8a9c2，触发流水线')">💾 提交</button>
      <button class="btn btn-p" onclick="CodeM.deploy()">🚀 部署沙箱</button>
    </div>
    <div class="designer designer-no-left" style="height:calc(100vh - var(--header-h) - 92px)">
      <div class="dz-center" style="background:#0f172a;overflow:auto">
        <div style="display:flex;gap:0;border-bottom:1px solid #1e293b;background:#0b1220;padding:0 8px">
          ${CodeM.FILES.map((f,i)=>`<button class="tab ${CodeM.tab===i?'active':''}" style="color:${CodeM.tab===i?'#e2e8f0':'#64748b'};border:none"
          onclick="CodeM.tab=${i};App.go('code')">${f.n}</button>`).join('')}
        </div>
        <div class="code-view" style="margin:14px;border:none;max-height:calc(100% - 120px)"><pre>${UI.esc(CodeM.FILES[CodeM.tab].code)}</pre></div>
      </div>
      <div class="dz-right">
        <div class="dz-cat">🤖 AI 编码助手</div>
        <div class="item"><b>行内补全建议</b><div class="mono muted mt10">const rate = await this.<b style="color:var(--primary)">getRateFor(customer.level)</b></div>
        <div class="btn-row mt10"><button class="btn btn-sm btn-p" onclick="UI.toast('已采纳')">Tab 采纳</button><button class="btn btn-sm" onclick="UI.toast('已忽略')">Esc</button></div></div>
        <div class="item"><b>实时诊断</b><div class="mt10">
        <div>🟡 未使用变量 <span class="mono">key2</span> (L12)</div>
        <div>🔵 建议提取常量 DISCOUNT_A1</div><div>✅ 无注入风险 · 无越权访问</div></div></div>
        <div class="dz-cat">沙箱执行（GB 6.2.8.2.1）</div>
        <div class="item"><div class="kv">${[['CPU 限额','0.5 核'],['内存','512MB'],['超时','5s'],['网络','白名单'],['文件系统','tmpfs 隔离']]
        .map(([k,v])=>`<div class="k">${k}</div><div class="v">${v}</div>`).join('')}</div>
        <div class="progress mt10"><i style="width:64%"></i></div><div class="muted">测试 8/8 通过 · 覆盖率 96% · 312ms</div></div>
        <div class="dz-cat">版本（GB 6.2.8.3 c）</div>
        <div class="item mono">3f8a9c2 fix: 折扣缓存 TTL<br>b21d77e feat: A2 等级折扣<br>88e01ac init</div>
        <div class="dz-cat">函数文档</div>
        <div class="muted">calcDiscount(order, customer) → rate 0~0.15，缓存 60s，见 JSDoc</div>
      </div>
    </div>`;
  },
  mount() {},
  aiTest() { UI.modal({ title:'🧪 AI 生成单元测试', size:'lg', footer:false, body:`
    <div class="code-view" style="max-height:280px"><pre>${UI.esc(
`describe('calcDiscount', () => {
  it('A1 + >10万 → 15%',  () => expect(rate('A1', 150000)).toBe(0.15));
  it('A2 任意金额 → 10%',  () => expect(rate('A2', 5000)).toBe(0.10));
  it('普通 >1万 → 5%',     () => expect(rate('B',  20000)).toBe(0.05));
  it('普通 ≤1万 → 0',      () => expect(rate('B',   9999)).toBe(0));
  it('空客户 → 抛错',      () => expect(() => rate(null, 1)).toThrow());
  it('缓存命中不重复计算', () => { spy(cache.get); ... });
});`)}</pre></div>
    <div class="filter-bar mt10"><span class="tag tag-green">6 用例通过</span><span class="tag tag-blue">覆盖率 96%</span>
    <span class="tag tag-purple">边界: 0/负数/超大值 已覆盖</span></div>` });
  },
  review() { UI.modal({ title:'🩺 AI 代码审查（GB 6.9.3.2.2 优化生成）', size:'lg', footer:false, body:`
    ${[['🔴 高危','order.ts L22 直接拼接排序字段 → 改用参数化白名单','SQL 注入'],
       ['🟠 中危','leave.ts 未处理 manager 离职场景 → 增加 fallback 队列','健壮性'],
       ['🔵 建议','提取魔法数字 0.15 为配置项（与权限矩阵联动）','可维护性'],
       ['🟢 合规','敏感字段已走 SM4 通道；日志无 PII 泄露','GB 6.6.3']].map(([lv,txt,tag])=>`
      <div class="item"><div class="flex">${lv}<span class="tag tag-gray" style="margin-left:auto">${tag}</span></div>
      <div class="mt10">${txt}</div><div class="btn-row mt10"><button class="btn btn-sm btn-p" onclick="UI.toast('AI 修复已应用')">一键修复</button></div></div>`).join('')}` });
  },
  debug() { UI.modal({ title:'🐞 断点调试', footer:false, body:`
    <div class="kv">${[['断点','order.ts L18 (条件 amount>100000)'],['当前栈','calcDiscount ← orderCreateCheck'],
    ['变量','{ order: {amount: 152000}, customer: {level: "A1"} }'],['快照','已保存 3 个变量快照']].map(([k,v])=>`<div class="k">${k}</div><div class="v mono" style="font-weight:500">${UI.esc(v)}</div>`).join('')}</div>
    <div class="btn-row mt10"><button class="btn btn-sm" onclick="UI.toast('单步进入')">F11 步入</button>
    <button class="btn btn-sm" onclick="UI.toast('单步跳过')">F10 跳过</button><button class="btn btn-sm" onclick="UI.toast('继续')">F5 继续</button></div>` });
  },
  deploy() { UI.toast('已构建并部署至沙箱实例 sandbox-7f3a（GB 6.2.8.1 代码引擎）'); },
};

/* ============ Module 13: 安全与合规 (GB 6.6 全域) ============ */
App.mods.sec = {
  tab: 0,
  render() { return `
    <div class="page-head"><h1>🛡️ 安全与合规</h1><span class="sub">国密 SM2/SM3/SM4 · 脱敏 · 防篡取 · 平台/应用安全 · 审计报告</span></div>
    <div class="card"><div class="card-b">
      <div class="tabs">${['国密与密钥','数据脱敏','防篡取','身份与访问','审计日志','合规报告'].map((t,i)=>
        `<button class="tab ${SecM.tab===i?'active':''}" onclick="SecM.tab=${i};App.go('sec')">${t}</button>`).join('')}
      ${SecM.body()}
    </div></div>`;
  },
  body() {
    if (this.tab===0) return `
      <div class="grid cols-3">
      ${Store.get('kmsKeys').map(k=>`<div class="kms-card" style="background:${k.alg==='SM2'?'#fef3c7':k.alg==='SM4'?'#e0f2fe':'#dcfce7'};background:var(--surface)">
        <div class="kms-ic" style="background:${k.alg==='SM2'?'#fef3c7':k.alg==='SM4'?'#e0f2fe':'#dcfce7'}">🔑</div>
        <div><b>GM/${k.alg}</b> <span class="tag tag-gray">${k.version}</span>
        <div class="muted mt10">${k.use}</div><div class="muted">${k.created} ~ ${k.expire}</div></div>
        <div style="margin-left:auto">${UI.statusTag(k.state)}</div></div>`).join('')}
      </div>
      <div class="grid cols-2 mt14">
        <div class="card"><div class="card-h">传输加密（GB 6.6.2）</div><div class="card-b">
        <div class="flex" style="margin-bottom:8px"><div class="switch on"></div>TLS 1.3 + 国密双证书 (SM2/SM4)</div>
        <div class="flex" style="margin-bottom:8px"><div class="switch on"></div>数据完整性校验（SM3 HMAC）</div>
        <div class="flex"><div class="switch on"></div>PFS 前向保密</div>
        <div class="help mt10">算法符合国家密码管理机构要求（GB 6.6.2.2 a）✅</div></div></div>
        <div class="card"><div class="card-h">密钥轮换</div><div class="card-b">
        <div class="kv">${[['策略','90 天自动轮换'],['下次轮换','2026-12-01'],['旧版本保留','7 天（解密存量）'],['托管','HSM / Vault']]
        .map(([k,v])=>`<div class="k">${k}</div><div class="v">${v}</div>`).join('')}</div>
        <button class="btn btn-sm mt10" onclick="UI.toast('SM4 v3 已生成并生效，v2 进入保留期')">立即轮换 SM4</button></div></div>
      </div>`;
    if (this.tab===1) return `<div class="card"><div class="card-h">脱敏规则（GB 6.6.3 e）</div><div class="card-b">
      ${UI.table({ cols:[{key:'label',label:'字段'},{key:'field',label:'key',render:r=>`<span class="mono">${r.field}</span>`},
        {key:'rule',label:'规则'},{key:'sample',label:'效果示例',render:r=>`<span class="mono">${r.sample}</span>`},
        {key:'on',label:'状态',render:r=>UI.statusTag(r.on?'on':'off')}],
        rows: Store.get('maskRules'),
        actions:r=>`<a class="link" onclick="Store.update('maskRules','${r.id}',{on:!r.on});App.go('sec')">${r.on?'停用':'启用'}</a>` })}
      <div class="help">导出/展示链路统一生效；AI 生成代码自动继承脱敏中间件（安全开发框架）</div></div></div>`;
    if (this.tab===2) return `<div class="grid cols-2">
      <div class="card watermark-demo"><div class="card-h">界面水印预览（GB 6.6.3 f）</div><div class="card-b" style="height:180px">
      <div class="muted">水印内容：用户名 · 部门 · 时间戳 · IP</div>
      <div class="btn-row mt10"><button class="btn btn-sm" onclick="UI.toast('水印设置')">水印配置</button></div></div></div>
      <div class="card"><div class="card-h">防截屏 / 防复制</div><div class="card-b">
      <div class="flex" style="margin-bottom:8px"><div class="switch on"></div>敏感页面禁用右键/复制</div>
      <div class="flex" style="margin-bottom:8px"><div class="switch on"></div>监听截屏行为并告警</div>
      <div class="flex"><div class="switch on"></div>导出强制二次认证</div>
      <div class="help mt10">数据防篡取（GB 6.6.3 f）</div></div></div></div>`;
    if (this.tab===3) return `<div class="grid cols-2">
      <div class="card"><div class="card-h">平台身份鉴别（GB 6.6.4）</div><div class="card-b">
      <div class="kv">${[['密码策略','12 位+复杂度+90天过期'],['MFA','TOTP + 短信双因子'],['SSO','OIDC / SAML2.0'],['会话','30min 空闲超时'],['登录保护','5 次失败锁定 15min']]
      .map(([k,v])=>`<div class="k">${k}</div><div class="v">${v}</div>`).join('')}</div></div></div>
      <div class="card"><div class="card-h">应用安全（GB 6.6.5）</div><div class="card-b">
      <div class="kv">${[['安全开发框架','AI 代码安全基线(内置 32 规则)'],['SQL 注入','参数化查询全覆盖 ✅'],['XSS','自动转义+CSP ✅'],['CSRF','双提交 Cookie ✅'],['WAF','OWASP Top10 规则集 ✅']]
      .map(([k,v])=>`<div class="k">${k}</div><div class="v">${v}</div>`).join('')}</div>
      <div class="help mt10">细粒度访问控制策略可配置（GB 6.6.5.2 c）</div></div></div></div>`;
    if (this.tab===4) return `<div class="filter-bar">
      <select class="input"><option>全部级别</option><option>WARN+</option><option>ERROR</option></select>
      <input class="input" placeholder="用户/资源/IP" style="width:180px">
      <button class="btn btn-sm" onclick="UI.toast('已导出审计报告 PDF')">📤 导出</button>
      <span class="muted">日志链完整性: sm3 hash-chain ✅ · 保留 730 天</span></div>
      <div class="tl mt10">${Store.get('auditLogs').map(l=>`<div class="tl-item ${l.level==='warn'?'warn':''}">
      <div class="tl-t">${l.action} · ${UI.esc(l.res)} ${l.level==='warn'?'<span class="tag tag-red">已告警</span>':''}</div>
      <div class="tl-d">${l.time} · ${l.user} · ${l.ip} · <span class="mono">${l.hash}</span></div></div>`).join('')}</div>`;
    return `<div class="grid cols-2">
      <div class="card"><div class="card-h">GB/T 46900-2025 达标状态</div><div class="card-b">
      ${[['基础级 L1','✅ 139/139'],['进阶级 L2','⚠️ 82/95（多端/大屏进行中）'],['引领级 L3','⏳ 规划']]
      .map(([k,v])=>`<div class="desc-list dl"><span class="dt">${k}</span><span class="dd"><b>${v}</b></span></div>`).join('')}
      <button class="btn btn-p mt10" onclick="UI.toast('合规自检报告已生成（含证据链）')">生成合规自检报告</button></div></div>
      <div class="card"><div class="card-h">定期审计报告（GB 6.7.6.2.3）</div><div class="card-b">
      ${[['2026-11 安全审计','4 发现(0 高危)','已整改'],['2026-10 操作审计','2 异常操作','已确认'],['2026-Q3 合规审计','1 项待办：密钥到期提醒策略','整改中']]
      .map(([n,f,s])=>`<div class="item"><div class="flex"><b>${n}</b><span class="tag ${s.includes('整改中')?'tag-orange':'tag-green'}" style="margin-left:auto">${s}</span></div>
      <div class="muted mt10">${f} · <a class="link" onclick="UI.toast('报告已下载')">下载</a></div></div>`).join('')}</div></div></div>`;
  },
};
