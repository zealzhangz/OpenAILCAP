/* ============ Module 14: 运维与部署 (GB 6.7 全域) ============ */
App.mods.ops = {
  tab: 0,
  render() { return `
    <div class="page-head"><h1>🚀 运维部署</h1><span class="sub">监控/日志/告警/部署/高可用 · GB 6.7.2-6.7.6</span></div>
    <div class="grid cols-4">
      ${[['API P95','268ms','var(--success-soft)','⚡'],['错误率','0.02%','var(--success-soft)','📉'],
        ['今日请求','1.28M','var(--info-soft)','📈'],['可用性','99.97%','var(--success-soft)','✅']].map(([l,v,c,i])=>`
      <div class="stat-tile"><div class="ic" style="background:${c}">${i}</div><div><div class="v">${v}</div><div class="l">${l}</div></div></div>`).join('')}
    </div>
    <div class="card mt14"><div class="card-b">
      <div class="tabs">${['监控','部署与制品','告警','日志','高可用'].map((t,i)=>
        `<button class="tab ${OpsM.tab===i?'active':''}" onclick="OpsM.tab=${i};App.go('ops')">${t}</button>`).join('')}
      ${OpsM.body()}
    </div></div>`;
  },
  body() {
    if (this.tab===0) return `<div class="grid cols-2">
      <div class="card"><div class="card-h">📊 系统与应用监控（GB 6.7.2.2）</div><div class="card-b">
        <div id="opsCpu"></div><div id="opsQps"></div>
        <div class="grid cols-4" style="gap:8px;margin-top:8px">
        ${[['CPU','46%'],['内存','63%'],['磁盘','38%'],['连接数','184']].map(([k,v])=>
        `<div class="item tc"><div class="muted">${k}</div><b>${v}</b></div>`).join('')}</div></div></div>
      <div class="card"><div class="card-h">🗄️ 数据库 & 网络（GB 6.7.2.2.3/4）</div><div class="card-b">
        <div class="kv">${[['慢查询(>500ms)','3 条/日'],['锁等待','均值 12ms'],['缓存命中率','87.4%'],['带宽利用率','31%'],['丢包率','0.01%'],['异常流量','未检出']]
        .map(([k,v])=>`<div class="k">${k}</div><div class="v">${v}</div>`).join('')}</div>
        <div class="help mt10">安全监控（L2）：未授权访问尝试 2 次/日已拦截 · 漏洞扫描: 0 高危</div></div></div>
      </div>`;
    if (this.tab===1) return `
      <div class="card"><div class="card-h">部署流水线（GB 6.7.5.2 a 自动化/流水线）</div><div class="card-b">
      <div class="pipe">
        ${[['构建','✅'],['单测 96%','✅'],['安全扫描','✅'],['打包制品','✅'],['灰度 10%','⏳'],['全量','—']]
        .map(([s,st],i)=>`<div class="pipe-step ${st==='✅'?'done':''}"><div class="pc">${st==='✅'?'✅':st==='⏳'?'⏳':'○'}</div>${s}</div>`).join('')}
      </div>
      <div class="filter-bar"><button class="btn btn-p btn-sm" onclick="UI.toast('流水线已触发 #412')">▶ 触发发布</button>
      <button class="btn btn-sm" onclick="UI.toast('已回滚至 v2.3.0（2 分钟完成）','warn')">⏪ 回滚</button>
      <select class="input" style="width:auto"><option>环境: test</option><option>环境: pre</option><option>环境: prod</option></select>
      <span class="muted">离线包生成: ✅（GB 6.1.3.2.1 e）</span></div></div></div>
      <div class="card mt14"><div class="card-h">部署历史</div><div class="card-b">
      ${UI.table({ cols:[{key:'app',label:'应用'},{key:'ver',label:'版本'},{key:'env',label:'环境'},
        {key:'mode',label:'方式'},{key:'time',label:'时间'},{key:'by',label:'触发'},
        {key:'state',label:'状态',render:r=>UI.statusTag(r.state)}],
        rows: Store.get('deployments'),
        actions:r=>`<a class="link" onclick="UI.toast('部署详情+日志')">日志</a>
        ${r.canRollback?`<a class="link" onclick="UI.confirm('确认回滚 ${r.ver}? ',()=>UI.toast('回滚完成'))">回滚</a>`:''}` })}
      <div class="help mt10">备份还原已纳入发布前置检查（GB 6.7.5.2 c）</div></div></div>`;
    if (this.tab===2) return `<div class="grid cols-2">
      <div><b>告警规则（GB 6.7.4.3.2）</b>
      ${[['API P95 > 800ms','持续 5min','邮件+钉钉','error'],['错误率 > 1%','立即','电话','error'],
        ['CPU > 80%','持续 10min','钉钉','warn'],['SM4 密钥到期','提前 7 天','站内','warn']]
      .map(([r,c,ch,lv])=>`<div class="item"><b>${r}</b>
      <div class="muted mt10">触发: ${c} · 通知: ${ch} · 级别: ${lv}</div></div>`).join('')}
      <button class="btn btn-sm" onclick="UI.toast('新建告警规则')">＋ 新建规则</button>
      <div class="help mt10">收敛降噪: 同源告警 5min 窗口聚合（GB 6.7.4.3.3）</div></div>
      <div><b>当前告警</b>
      ${Store.get('alerts').map(a=>`<div class="item"><div class="flex">
      ${a.level==='error'?'🔴':a.level==='warn'?'🟠':'🔵'} <b>${UI.esc(a.title)}</b>
      ${UI.statusTag(a.state)}<span class="muted" style="margin-left:auto">${a.time}</span></div>
      <div class="muted mt10">来源: ${a.source} · <a class="link" onclick="UI.toast('告警已确认')">确认</a>
      <a class="link" onclick="UI.toast('已自动恢复并取消告警')">自动恢复</a></div></div>`).join('')}
      <div class="card"><div class="card-h">告警分析（GB 6.7.4.3.4）</div><div class="card-b"><div id="alertChart"></div></div></div></div>
      </div>`;
    if (this.tab===3) return `<div class="filter-bar">
      <select class="input" style="width:auto"><option>全部来源</option><option>应用</option><option>网关</option><option>DB</option><option>安全</option></select>
      <input class="input" placeholder="关键字…" style="width:180px"><button class="btn btn-sm btn-p">检索</button>
      <span class="muted">今日 ${Store.get('logStats').today} 条 · ERROR ${Store.get('logStats').err} · WARN ${Store.get('logStats').warn} · 保留 ${Store.get('logStats').retained}</span></div>
      <div class="code-view" style="max-height:300px"><pre>${UI.esc(
`16:45:01 INFO  gateway  GET /api/orders 200 12ms user=吴九
16:44:58 WARN  app_003  slow query: SELECT * FROM customer WHERE ... 612ms
16:44:12 INFO  bpm      PI-2026-1101 step[总经理审批] notified 周百
16:43:40 ERROR api      POST /api/notify timeout(5000ms) retry 1/3
16:43:02 INFO  audit    al5 deploy app_001 v2.3.1 prod canary10% hash=sm3:aa3f`)}</pre></div>
      <div class="filter-bar mt10"><span class="tag tag-blue">归档: 每日 03:00 → OSS</span><span class="tag tag-blue">还原: 支持按天回放</span>
      <span class="muted">日志归档备份（GB 6.7.3.2.3）· 检索/聚合分析（GB 6.7.3.3）</span></div>`;
    return `<div class="grid cols-2">
      <div class="card"><div class="card-h">集群状态（GB 6.7.5.3 L2 高可用）</div><div class="card-b">
      <div class="grid cols-3" style="gap:8px">
      ${[['api-gateway','2/2','✅'],['app-server','3/3','✅'],['worker','2/2','✅'],['pg-primary','1/1','✅'],['pg-replica','2/2','✅'],['redis','3/3','✅']]
      .map(([n,p,s])=>`<div class="item tc"><b>${n}</b><div class="muted">${p}</div>${UI.statusTag(s==='✅'?'success':'error')}</div>`).join('')}</div>
      <div class="btn-row mt10"><button class="btn btn-sm" onclick="UI.toast('滚动更新中… 0 中断')">滚动更新</button>
      <button class="btn btn-sm" onclick="UI.toast('已扩容 app-server 3→5')">弹性扩容</button></div></div></div>
      <div class="card"><div class="card-h">灾备（RTO 5min / RPO 15min）</div><div class="card-b">
      <div class="tl">
      <div class="tl-item"><div class="tl-t">✅ 上次切换演练 11-20 · RTO 3m41s</div><div class="tl-d">主库故障注入 → 自动主从切换</div></div>
      <div class="tl-item"><div class="tl-t">✅ 异地备份同步 11-28 03:00</div><div class="tl-d">跨区域 OSS · 增量每小时</div></div>
      <div class="tl-item"><div class="tl-t">📅 下次全链路演练 12-20</div><div class="tl-d">含 DNS 切换与回切</div></div></div></div></div></div>`;
  },
  mount() { setTimeout(()=>{ const c1=document.getElementById('opsCpu'), c2=document.getElementById('opsQps'), c3=document.getElementById('alertChart');
    if (c1) Charts.line(c1, ['-6h','-4h','-2h','now'], [{name:'CPU%',data:[38,44,52,46]},{name:'MEM%',data:[55,58,61,63]}], {h:120,noDots:true,legend:false});
    if (c2) Charts.line(c2, ['-6h','-4h','-2h','now'], [{name:'QPS',data:[820,910,1240,1080]}], {h:110,noDots:true,legend:false});
    if (c3) Charts.bar(c3, ['周一','周二','周三','周四','周五'], [4,2,7,3,1], {h:130}); }, 60); },
};

/* ============ 消息中心 ============ */
App.mods.msg = {
  render() { return `
    <div class="page-head"><h1>🔔 消息中心</h1><span class="sub">站内信 · 邮件/短信触达记录 · 模板管理入口</span><span class="spacer"></span>
      <button class="btn" onclick="UI.toast('已全部标记已读')">全部已读</button></div>
    <div class="grid cols-32"><div class="card"><div class="card-h">收件箱</div><div class="card-b">
      ${[['⚠️','合同 CT-2026-032 用印审批已超期 2h，请立即处理','11-28 16:02',0],
        ['📦','订单 SO-2026-1101 已进入总经理审批环节','11-28 09:31',0],
        ['✅','您提交的 v2.3.1 已完成灰度发布，错误率 0.02%','11-28 10:01',1],
        ['🤖','AI 周报：本周生成应用 37 个，采纳率 82%','11-28 08:00',1],
        ['🔑','SM4 密钥将于 12-01 到期，请安排轮换','11-28 09:00',0]]
      .map(([i,t,tm,read])=>`<div class="item" style="${read?'opacity:.55':''}">
      <div class="flex"><span style="font-size:16px">${i}</span><b>${UI.esc(t)}</b>
      ${read?'':'<span class="dot-ic" style="background:var(--danger)"></span>'}
      <span class="muted" style="margin-left:auto">${tm}</span></div></div>`).join('')}
    </div></div>
    <div><div class="card"><div class="card-h">触达统计</div><div class="card-b" id="msgStats"></div></div>
    <div class="card mt14"><div class="card-h">渠道配置</div><div class="card-b">
    ${[['站内信','✅'],['邮件 SMTP','✅'],['短信(阿里云)','✅'],['钉钉机器人','✅'],['企业微信','✅'],['Webhook','⚠️ 未配置']].map(([n,s])=>`
    <div class="item"><div class="flex"><b>${n}</b><span style="margin-left:auto">${s}</span></div></div>`).join('')}</div></div></div></div>`;
  },
  mount() { setTimeout(()=>Charts.bar(document.getElementById('msgStats'),
    ['站内信','邮件','短信','钉钉','企微'], [12840,8211,436,2100,954], {h:150}), 60); },
};

/* ============ 工作台 Home ============ */
App.mods.home = {
  render() {
    const pend = Store.get('tasks').filter(t=>t.state==='pending').length;
    return `
    <div class="page-head" style="margin-bottom:6px"><div><h1>${I18N.t('home.hello')} 👋</h1>
    <div class="muted">${I18N.t('home.sub',{n:pend})}</div></div><span class="spacer"></span>
    <button class="btn btn-p" onclick="AppsM.openCreate()">🤖 ${I18N.t('home.gen5min')}</button></div>
    <div class="grid cols-4">
      ${[['home.metric.apps',5,'📱','var(--primary-soft)','+2',1],
        ['home.metric.inst',846,'📄','var(--info-soft)','+12%',1],
        ['home.metric.sla','96.5%','⏱️','var(--success-soft)','+1.3%',1],
        ['home.metric.ai',37,'🤖','var(--warning-soft)','+9',1]].map(([k,v,i,c,t,up])=>`
      <div class="stat-tile"><div class="ic" style="background:${c}">${i}</div>
      <div><div class="v">${v}<span class="trend ${up?'up':'down'}">${t}</span></div><div class="l">${I18N.t(k)}</div></div></div>`).join('')}
    </div>
    <div class="grid cols-32 mt14">
      <div>
        <div class="card"><div class="card-h">${I18N.t('home.todo')} <span class="spacer"></span>
          <a class="link" onclick="App.go('tasks')">全部 →</a></div><div class="card-b">
          ${Store.get('tasks').filter(t=>t.state==='pending').map(t=>`
          <div class="item"><div class="flex"><b>${UI.esc(t.title)}</b>${UI.priTag(t.pri)}
          <span style="margin-left:auto" class="${t.sla.startsWith('超期')?'':'muted'}">${t.sla}</span></div>
          <div class="muted mt10">来自 ${t.from} · ${t.node}</div>
          <div class="btn-row mt10"><button class="btn btn-sm btn-p" onclick="App.go('tasks')">去审批</button>
          <button class="btn btn-sm" onclick="AI.quick('当前待办有哪些?')">问 AI</button></div></div>`).join('')}
        </div></div>
        <div class="card mt14"><div class="card-h">${I18N.t('home.quick')}</div><div class="card-b">
          <div class="grid cols-3" style="gap:8px">
          ${[['🤖','AI 生成应用',"AppsM.openCreate()"],['🧭','新建流程',"UI.toast('请在 BPM 设计器创建')"],
            ['📊','新建数据模型',"ModelM.addTable()"],['📈','新建报表',"UI.toast('请在报表设计器创建')"],
            ['💻','写自定义代码',"App.go('code')"],['🔐','权限配置',"App.go('perm')"]]
          .map(([i,l,fn])=>`<div class="item tc" style="cursor:pointer" onclick="${fn}">
          <div style="font-size:22px">${i}</div>${l}</div>`).join('')}</div>
        </div></div>
      </div>
      <div>
        <div class="card"><div class="card-h">${I18N.t('home.activity')}</div><div class="card-b">
          <div class="tl">${Store.get('auditLogs').slice(0,4).map(l=>`
          <div class="tl-item ${l.level==='warn'?'warn':''}"><div class="tl-t">${l.action} · ${UI.esc(l.res.slice(0,26))}…</div>
          <div class="tl-d">${l.time} · ${l.user}</div></div>`).join('')}</div></div></div>
        <div class="card mt14"><div class="card-h">${I18N.t('home.metric.uptime')}</div><div class="card-b" id="homeGauge"></div></div>
      </div>
    </div>`;
  },
  mount() { setTimeout(()=>{ const g=document.getElementById('homeGauge'); if (g) Charts.gauge(g, 99.97, {label:'30 天可用性'}); }, 50); },
};
