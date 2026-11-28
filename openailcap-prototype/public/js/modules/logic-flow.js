/* ============ Module 5: 逻辑编排设计器 (GB 6.2.4) ============ */
App.mods.flow = {
  sel: null, drag: null,
  NODES: [
    ['事件','event','📌 事件触发'],['事件','timer','⏰ 定时器'],['事件','webhook','🔗 Webhook'],
    ['控制','condition','⚡ 条件判断'],['控制','switch','🔀 多路分支'],['控制','loop','🔄 循环'],['控制','parallel','↔️ 并行'],['控制','delay','⏸️ 延迟'],
    ['数据','data','🗄️ 数据操作'],['数据','variable','📝 变量赋值'],
    ['服务','api','🌐 API 调用'],['服务','function','🎯 函数调用'],['服务','notify','📨 消息通知'],
    ['异常','error','🚨 异常处理'],['异常','try','🧪 Try/Catch'],
  ],
  render() {
    const f = Store.get('logicFlows')[0];
    return `
    <div class="page-head"><h1>🔀 逻辑编排</h1><span class="sub">${f.name} · GB 6.2.4 执行控制/事件/数据操作/编排调试</span>
      <span class="spacer"></span>
      <button class="btn" onclick="LogicM.testGraph()">▶️ 模拟测试</button>
      <button class="btn" onclick="LogicM.debug()">🐞 断点调试</button>
      <button class="btn" onclick="LogicM.connect()">↗ 连线</button>
      <button class="btn" onclick="LogicM.removeEdge()">删除连线</button>
      <button class="btn" onclick="LogicM.graphCode()">⚡ 生成代码</button>
      <button class="btn" onclick="LogicM.logs()">📜 执行日志</button>
      <button class="btn btn-p" onclick="LogicM.save()">💾 保存</button>
    </div>
    <div class="designer designer-no-left">
      <div class="dz-center" style="padding:0"><div class="flow-wrap" id="flowWrap"
        ondragover="event.preventDefault()" ondrop="LogicM.drop(event)">
        <svg class="flow-svg" width="1100" height="560" id="flowSvg">
          <defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
          <path d="M0,0 L8,4 L0,8 z" fill="#94a3b8"/></marker></defs></svg>
        <div class="flow-inner" id="flowInner"></div>
      </div></div>
      <div class="dz-right" id="nodeProps"><div class="muted">点击节点配置属性</div></div>
    </div>
    <div class="card mt14" style="margin-left:0"><div class="card-h">节点库（点击或拖入画布）
      <span class="spacer"></span><button class="btn btn-sm" onclick="LogicM.aiGen()">🤖 AI 生成流程</button></div>
      <div class="card-b"><div class="flex wrap" style="gap:6px">
      ${LogicM.NODES.map(([c,t,l])=>`<span class="dz-item" draggable="true" style="margin:0"
        ondragstart="LogicM.drag='${t}'" onclick="LogicM.drop(null,'${t}')">${l}</span>`).join('')}</div></div></div>`;
  },
  mount() { this.draw(); },
  draw() {
    const f = Store.get('logicFlows')[0];
    const inner = document.getElementById('flowInner'); if (!inner) return;
    inner.innerHTML = '';
    f.nodes.forEach(n => {
      const el = document.createElement('div');
      const cls = {event:'ev',condition:'gw',switch:'gw',loop:'task',data:'svc',api:'svc',function:'svc',notify:'svc',error:'err',try:'err',end:'end',timer:'ev',webhook:'ev',parallel:'task',delay:'task',variable:'svc'}[n.type]||'task';
      el.className = 'fnode ' + cls + (this.sel===n.id?' sel':'');
      el.style.left = n.x+'px'; el.style.top = n.y+'px';
      el.innerHTML = `<div class="flex"><span class="fn-ic">${{event:'📌',condition:'⚡',data:'🗄️',api:'🌐',end:'🏁',notify:'📨',timer:'⏰',webhook:'🔗',switch:'🔀',loop:'🔄',parallel:'↔️',delay:'⏸️',variable:'📝',function:'🎯',error:'🚨',try:'🧪'}[n.type]||'▪'}</span>
        <b class="fn-t">${n.label}</b></div>
        ${n.expr?`<div class="fn-s mono">${UI.esc(n.expr)}</div>`:''}
        ${n.url?`<div class="fn-s mono">${n.method} ${UI.esc(n.url)}</div>`:''}
        ${n.op?`<div class="fn-s">op: ${n.op}</div>`:''}`;
      el.onclick = () => { this.sel = n.id; this.draw(); this.props(n); };
      el.onmousedown = (e) => this.startDrag(e, n, el);
      inner.appendChild(el);
    });
    this.drawEdges();
  },
  drawEdges() {
    const f = Store.get('logicFlows')[0];
    const pos = id => f.nodes.find(n=>n.id===id);
    let p = '';
    f.edges.forEach(e => { const a=pos(e.f), b=pos(e.t); if(!a||!b) return;
      const x1=a.x+150, y1=a.y+28, x2=b.x, y2=b.y+28;
      const mid=(x1+x2)/2;
      p += `<path class="${e.when?'cond':''}" d="M${x1},${y1} C${mid},${y1} ${mid},${y2} ${x2},${y2}"/>`;
      if (e.when) p += `<text x="${mid}" y="${(y1+y2)/2-3}" text-anchor="middle" font-size="10" fill="#d97706">${e.when}</text>`; });
    document.getElementById('flowSvg').innerHTML = p;
  },
  startDrag(e, n, el) {
    const sx=e.clientX, sy=e.clientY, ox=n.x, oy=n.y;
    const mv = ev => { n.x=ox+ev.clientX-sx; n.y=oy+ev.clientY-sy; el.style.left=n.x+'px'; el.style.top=n.y+'px'; this.drawEdges(); };
    const up = () => { document.removeEventListener('mousemove',mv); document.removeEventListener('mouseup',up); Store.save(); };
    document.addEventListener('mousemove',mv); document.addEventListener('mouseup',up); e.preventDefault();
  },
  drop(ev, type) { const t = type || this.drag; if (!t) return; this.drag=null;
    const f = Store.get('logicFlows')[0];
    const rect = document.getElementById('flowWrap').getBoundingClientRect();
    const x = ev ? ev.clientX-rect.left-75 : 60, y = ev ? ev.clientY-rect.top-20 : 40+Math.random()*80;
    const label = this.NODES.find(n=>n[1]===t)[2].split(' ')[1]||t;
    f.nodes.push({ id:'n'+Date.now(), type:t, label, x:Math.max(0,x), y:Math.max(0,y) });
    Store.save(); this.draw(); UI.toast('节点已添加：'+label);
  },
  props(n) {
    document.getElementById('nodeProps').innerHTML = `
      <div class="form-item"><label>节点名称</label><input class="input" value="${UI.esc(n.label)}"
        oninput="LogicM.upNode('${n.id}','label',this.value)"></div>
      <div class="form-item"><label>类型</label><input class="input" value="${n.type}" disabled></div>
      ${n.type==='condition'?`<div class="form-item"><label>条件表达式（语法规则图形界面 GB6.4.2）</label>
        <input class="input mono" value="${UI.esc(n.expr||'')}" placeholder="\${amount} > 10000"
        oninput="LogicM.upNode('${n.id}','expr',this.value)">
        <div class="btn-row mt10"><a class="link" onclick="UI.toast('表达式编辑器：变量面板 + 函数联想 + 校验')">打开表达式编辑器</a></div></div>`:''}
      ${n.type==='data'?`<div class="form-item"><label>操作</label><select class="input" onchange="LogicM.upNode('${n.id}','op',this.value)">
        ${['select','insert','update','delete','aggregate'].map(o=>`<option ${n.op===o?'selected':''}>${o}</option>`).join('')}</select></div>
      <div class="form-item"><label>目标模型</label><select class="input">
        ${Store.get('models').map(m=>`<option>${m.name}</option>`).join('')}</select></div>`:''}
      ${n.type==='api'?`<div class="form-item"><label>Method</label><select class="input" onchange="LogicM.upNode('${n.id}','method',this.value)">
        ${['GET','POST','PUT','DELETE'].map(m=>`<option ${n.method===m?'selected':''}>${m}</option>`).join('')}</select></div>
      <div class="form-item"><label>URL</label><input class="input mono" value="${UI.esc(n.url||'')}"
        oninput="LogicM.upNode('${n.id}','url',this.value)"></div>
      <div class="form-item"><label>超时/重试</label><div class="form-row"><input class="input" value="5000ms">
        <input class="input" value="3 次"></div></div>`:''}
      ${n.type==='variable'?`<div class="form-item"><label>变量名</label><input class="input mono" placeholder="result"></div>
      <div class="form-item"><label>赋值表达式</label><input class="input mono" placeholder="\${order.amount} * 0.9"></div>`:''}
      <div class="form-item"><label>错误处理</label><select class="input">
        <option>冒泡到全局 Catch</option><option>重试后继续</option><option>跳过并告警</option></select></div>
      <button class="btn btn-danger btn-sm" style="width:100%" onclick="LogicM.delNode('${n.id}')">删除节点</button>`;
  },
  upNode(id, k, v) { const f = Store.get('logicFlows')[0]; const n = f.nodes.find(x=>x.id===id);
    if (n) { n[k]=v; Store.save(); if (k==='label'||k==='expr'||k==='method'||k==='url') this.draw(); } },
  delNode(id) { const f = Store.get('logicFlows')[0];
    f.nodes = f.nodes.filter(n=>n.id!==id); f.edges = f.edges.filter(e=>e.f!==id&&e.t!==id);
    this.sel=null; Store.save(); this.draw(); document.getElementById('nodeProps').innerHTML='<div class="muted">已删除</div>'; },

  test() { const f = Store.get('logicFlows')[0];
    UI.modal({ title:'▶️ 模拟测试', size:'lg', footer:false, body:`
      <div class="form-item"><label>模拟输入（GB 6.2.4.3 模拟测试）</label>
        <textarea class="input mono">{ "amount": 152000, "customer": "C-001" }</textarea></div>
      <div class="tl" style="margin:10px 0">
        ${f.nodes.map((n,i)=>`<div class="tl-item"><div class="tl-t">✓ ${n.label}</div>
        <div class="tl-d">${n.type} · ${(i+1)*120}ms ${n.expr?'· 求值: true':''}</div></div>`).join('')}
      </div>
      <div class="success">✅ 全链路执行成功 · 总耗时 620ms · 输出: { status: 'ok', notify: true }</div>` });
  },
  debug() { UI.toast('断点已设在节点 [金额>10000?]，单步执行查看变量快照（GB 6.4.5 L2）', 'info'); },
  genCode() { const f = Store.get('logicFlows')[0];
    const code = `// Auto-generated by OpenAILCAP LogicFlow: ${f.name}\nexport async function orderCreateCheck(input: OrderInput) {\n  const vars: Record<string, any> = { ...input };\n  // node: 表单提交 (event)\n  // node: 金额>10000? (condition)\n  if (vars.amount > 10000) {\n    // node: 通知审批人 (api)\n    await fetch('/api/notify', {\n      method: 'POST',\n      headers: { 'Content-Type': 'application/json' },\n      body: JSON.stringify({ orderId: vars.id, level: 'manager' }),\n    });\n  }\n  // node: 写入订单 (data)\n  await db.order.create({ data: vars });\n  return { status: 'ok' };\n}`;
    UI.modal({ title:'⚡ 生成代码', size:'lg', footer:false, body:`
      <div class="code-tabs"><button class="btn btn-sm btn-p">TypeScript</button>
        <button class="btn btn-sm" onclick="UI.toast('Python 版本生成中…')">Python</button>
        <button class="btn btn-sm" onclick="UI.toast('已复制')">📋 复制</button></div>
      <div class="code-view"><pre>${UI.esc(code)}</pre></div>
      <div class="filter-bar mt10"><span class="tag tag-green">语法检查通过</span><span class="tag tag-green">安全扫描: 无注入</span>
      <span class="tag tag-blue">测试覆盖建议: 6 用例</span></div>` });
  },
  logs() { UI.modal({ title:'📜 执行日志', size:'lg', footer:false, body:`
    <div class="filter-bar"><input class="input" placeholder="关键字/级别过滤" style="width:200px">
      <select class="input"><option>全部级别</option><option>ERROR</option><option>INFO</option></select>
      <span class="muted">今日 1,284 次执行 · 失败 2</span></div>
    <div class="code-view" style="max-height:260px"><pre>${UI.esc(
`16:42:11 INFO  [lf1] flow start, input={amount:152000}
16:42:11 INFO  [lf1] node[金额>10000?] eval=true
16:42:11 INFO  [lf1] node[通知审批人] POST /api/notify 200 (48ms)
16:42:12 INFO  [lf1] flow done (620ms)
16:40:03 ERROR [lf1] node[API] timeout after 5000ms, retry 1/3
15:58:44 INFO  [lf1] flow done (588ms)`)}</pre></div>` });
  },
  aiGen() { UI.modal({ title:'🤖 AI 生成逻辑流程', body:`<div class="form-item"><label>用自然语言描述逻辑</label>
      <textarea class="input">提交订单时：金额超过10万走总经理审批，5万到10万走部门经理，其余自动通过；全部写入审计日志</textarea></div>
    <button class="btn btn-p" onclick="UI.toast('🤖 已生成 9 个节点 + 3 条网关分支，已放入画布');UI.closeModal()">🤖 生成</button>` });
  },
};
