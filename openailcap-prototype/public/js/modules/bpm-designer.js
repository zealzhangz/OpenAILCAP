/* ============ Module 6: BPM 流程设计器 (GB 6.2.3 + 6.4.6) ============ */
App.mods.bpm = {
  sel: null, drag: null,
  NODES: [
    ['事件','start','🟢 开始'],['事件','end','🔴 结束'],['事件','timer','⏰ 定时事件'],['事件','msg','📨 消息事件'],
    ['任务','user','👤 用户任务'],['任务','service','⚙️ 服务任务'],['任务','auto','🤖 AI 任务'],
    ['网关','gateway','◐ 条件网关'],['网关','parallel','⫸ 并行网关'],['网关','inclusive','◑ 包容网关'],
    ['其他','sub','⬜ 子流程'],['其他','dataobj','📄 数据对象'],['其他','datastore','🗄️ 数据存储区'],
  ],
  render() {
    const d = Store.get('bpmDefs')[0];
    return `
    <div class="page-head"><h1>🧭 BPM 流程设计器</h1><span class="sub">${d.name} ${d.version} · BPMN 2.0 · 回退/委托/抄送 · 规则引擎 · 仿真</span>
      <span class="spacer"></span>
      <button class="btn" onclick="BpmM.simulate()">🧪 流程仿真</button>
      <button class="btn" onclick="BpmM.connect()">↗ 连线</button>
      <button class="btn" onclick="BpmM.removeEdge()">删除连线</button>
      <button class="btn" onclick="BpmM.save()">💾 保存</button>
      <button class="btn" onclick="BpmM.rules()">📐 规则引擎</button>
      <button class="btn" onclick="BpmM.importBpmn()">📥 导入 BPMN</button>
      <button class="btn" onclick="BpmM.exportBpmn()">📤 导出 XML</button>
      <button class="btn" onclick="BpmM.version()">🕘 版本 v3</button>
      <button class="btn btn-p" onclick="BpmM.publish()">🚀 发布</button>
    </div>
    <div class="designer designer-no-left">
      <div class="dz-center" style="padding:0"><div class="flow-wrap">
        <svg class="flow-svg" width="1100" height="560" id="bpmSvg">
          <defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
          <path d="M0,0 L8,4 L0,8 z" fill="#94a3b8"/></marker></defs></svg>
        <div class="flow-inner" id="bpmInner"></div></div></div>
      <div class="dz-right" id="bpmProps"><div class="muted">点击节点配置</div></div>
    </div>
    <div class="card mt14"><div class="card-h">节点库 <span class="spacer"></span>
      <button class="btn btn-sm" onclick="UI.toast('🤖 AI 已生成「请假三级审批」流程：主管→总监→HR，含金额网关与 SLA')">🤖 AI 生成流程</button></div>
      <div class="card-b"><div class="flex wrap" style="gap:6px">
      ${BpmM.NODES.map(([c,t,l])=>`<span class="dz-item" draggable="true" style="margin:0" ondragstart="BpmM.drag='${t}'"
        onclick="BpmM.drop(null,'${t}')">${l}</span>`).join('')}</div></div></div>`;
  },
  mount() { this.draw(); },
  draw() {
    const d = Store.get('bpmDefs')[0];
    const inner = document.getElementById('bpmInner'); if (!inner) return;
    inner.innerHTML = '';
    d.nodes.forEach(n => {
      const el = document.createElement('div');
      const cls = {start:'ev',end:'end',gateway:'gw',parallel:'gw',inclusive:'gw',user:'task',service:'svc',auto:'svc',sub:'task',timer:'ev',msg:'ev',dataobj:'svc',datastore:'svc'}[n.type]||'task';
      el.className = 'fnode ' + cls + (this.sel===n.id?' sel':'');
      el.style.left=n.x+'px'; el.style.top=n.y+'px'; el.style.width = n.type==='gateway'?'170px':'150px';
      el.innerHTML = `<div class="flex"><span>${{start:'🟢',end:'🔴',gateway:'◐',parallel:'⫸',inclusive:'◑',user:'👤',service:'⚙️',auto:'🤖',sub:'⬜',timer:'⏰',msg:'📨',dataobj:'📄',datastore:'🗄️'}[n.type]||'▪'}</span>
        <b class="fn-t">${n.label}</b></div>
        ${n.assignee?`<div class="fn-s">${this.assigneeLabel(n.assignee)}</div>`:''}
        ${n.sla?`<div class="fn-s">⏱ SLA ${n.sla}</div>`:''}
        ${n.expr?`<div class="fn-s mono">${UI.esc(n.expr)}</div>`:''}`;
      el.onclick = () => { this.sel=n.id; this.draw(); this.props(n); };
      el.onmousedown = e => this.startDrag(e, n, el);
      inner.appendChild(el);
    });
    const pos = id => d.nodes.find(n=>n.id===id);
    let p = '';
    d.edges.forEach(e => { const a=pos(e.f), b=pos(e.t); if(!a||!b) return;
      const x1=a.x+(a.type==='gateway'?170:150), y1=a.y+28, x2=b.x, y2=b.y+28, mid=(x1+x2)/2;
      p += `<path class="${e.when?'cond':''}" d="M${x1},${y1} C${mid},${y1} ${mid},${y2} ${x2},${y2}"/>`;
      if (e.when) p += `<text x="${(x1+x2)/2}" y="${(y1+y2)/2-3}" text-anchor="middle" font-size="10" fill="#d97706">${e.when}</text>`; });
    document.getElementById('bpmSvg').innerHTML = p;
  },
  assigneeLabel(a) {
    if (a.startsWith('mgr:')) return '👔 直属主管（组织架构）';
    if (a.startsWith('pos:')) return '🎯 岗位: ' + (Store.get('positions').find(p=>p.id===a.split(':')[1])||{}).name;
    if (a.startsWith('dept:')) return '🏢 部门: ' + (Store.get('depts').find(d=>d.id===a.split(':')[1])||{}).name;
    if (a==='ai') return '🤖 AI 智能分配';
    return a;
  },
  startDrag(e,n,el) { const sx=e.clientX, sy=e.clientY, ox=n.x, oy=n.y;
    const mv = ev => { n.x=ox+ev.clientX-sx; n.y=oy+ev.clientY-sy; el.style.left=n.x+'px'; el.style.top=n.y+'px'; BpmM.draw(); };
    const up = () => { document.removeEventListener('mousemove',mv); document.removeEventListener('mouseup',up); Store.save(); };
    document.addEventListener('mousemove',mv); document.addEventListener('mouseup',up); e.preventDefault(); },
  drop(ev,type) { const t=type||this.drag; if(!t) return; this.drag=null;
    const d=Store.get('bpmDefs')[0]; const rect=document.getElementById('flowWrap').getBoundingClientRect();
    const label = this.NODES.find(n=>n[1]===t)[2].split(' ')[1]||t;
    d.nodes.push({id:'b'+Date.now(), type:t, label, x:ev?ev.clientX-rect.left-75:60, y:ev?ev.clientY-rect.top-20:60});
    Store.save(); this.draw(); UI.toast('节点已添加'); },
  props(n) {
    document.getElementById('bpmProps').innerHTML = `
      <div class="form-item"><label>名称</label><input class="input" value="${UI.esc(n.label)}"
        oninput="BpmM.upNode('${n.id}','label',this.value)"></div>
      ${n.type==='user'?`
      <div class="form-item"><label>审批人规则（GB 6.2.3.3.1 参与者）</label>
        <select class="input" onchange="BpmM.upNode('${n.id}','assignee', this.value.startsWith('指定')?'mgr:direct':this.value)">
          ${['mgr:direct|👔 直属主管（汇报线）','pos:p1|🎯 指定岗位: 总经理','pos:p2|🎯 指定岗位: 部门总监','dept:d3|🏢 指定部门: 销售一部','ai|🤖 AI 智能分配（负载+专长）']
            .map(o=>{const [v,l]=o.split('|');return `<option value="${v}" ${n.assignee===v?'selected':''}>${l}</option>`}).join('')}
        </select></div>
      <div class="form-item"><label>审批操作</label><div class="btn-row wrap">
        ${['同意','拒绝','转办','委托','加签','抄送','回退'].map(a=>`<span class="tag ${(n.actions||['approve','reject']).length?'tag-green':'tag-gray'}" style="cursor:pointer"
          onclick="UI.toast('已切换操作：${a}')">${a}</span>`).join('')}</div></div>
      <div class="form-item"><label>SLA 超期</label><div class="form-row">
        <input class="input" value="${n.sla||'4h'}" oninput="BpmM.upNode('${n.id}','sla',this.value)">
        <select class="input"><option>升级上级</option><option>站内+短信</option><option>自动通过</option></select></div></div>
      <div class="form-item"><label>表单权限（本环节）</label><div class="btn-row wrap">
        ${['订单金额:只读','客户:隐藏','备注:可编辑'].map(x=>`<span class="tag tag-blue">${x}</span>`).join('')}
        <a class="link" onclick="UI.toast('环节表单字段权限配置（GB 6.2.3.2.2 b）')">配置…</a></div></div>`:''}
      ${n.type==='gateway'||n.type==='parallel'||n.type==='inclusive'?`
      <div class="form-item"><label>网关类型</label><select class="input">
        <option ${n.type==='gateway'?'selected':''}>条件网关(互斥)</option><option ${n.type==='parallel'?'selected':''}>并行网关</option>
        <option ${n.type==='inclusive'?'selected':''}>包容网关</option></select></div>
      <div class="form-item"><label>分支条件</label>
        <div class="item mono">${UI.esc(n.expr||'${amount} >= 100000')}</div>
        <div class="item mono">else → 默认分支</div>
        <a class="link" onclick="UI.toast('AI 已优化条件：建议增加空值保护')">🤖 AI 优化条件</a></div>`:''}
      ${n.type==='start'?`<div class="form-item"><label>发起方式</label><select class="input"><option>手动提交表单</option><option>API 触发</option><option>定时触发</option></select></div>
      <div class="form-item"><label>动态子流程（GB 6.2.3.3.2 a）</label><div class="switch on" onclick="this.classList.toggle('on')"></div>
      <div class="help">按集合变量为每笔子单创建子流程实例</div></div>`:''}
      ${n.type==='user'||n.type==='start'?`<div class="form-item"><label>自由流转（GB 6.2.3.3.2 b）</label>
      <div class="flex"><div class="switch" onclick="this.classList.toggle('on')"></div><span class="muted">允许跳转目标范围</span>
      <select class="input" style="width:auto"><option>任意已办节点</option><option>指定节点</option></select></div></div>
      <div class="form-item"><label>人工环节多任务（GB 6.2.3.3.2 c）</label>
      <select class="input"><option>单人处理</option><option>按参与者数量并行建任务</option><option>会签(全部通过)</option><option>或签(任一通过)</option></select></div>`:''}
      <div class="form-item"><label>电子签名（合规）</label><div class="flex">
      <div class="switch on" onclick="this.classList.toggle('on')"></div><span class="muted">SM2 签名 + 时间戳</span></div></div>
      <button class="btn btn-danger btn-sm" style="width:100%" onclick="BpmM.delNode('${n.id}')">删除节点</button>`;
  },
  upNode(id,k,v) { const d=Store.get('bpmDefs')[0]; const n=d.nodes.find(x=>x.id===id);
    if(n){n[k]=v;Store.save();this.draw();} },
  delNode(id) { const d=Store.get('bpmDefs')[0]; d.nodes=d.nodes.filter(n=>n.id!==id);
    d.edges=d.edges.filter(e=>e.f!==id&&e.t!==id); this.sel=null; Store.save(); this.draw();
    document.getElementById('bpmProps').innerHTML='<div class="muted">已删除</div>'; },

  simulate() { UI.modal({ title:'🧪 流程仿真（GB 6.4.6.3 L2）', size:'lg', footer:false, body:`
    <div class="form-row"><div class="form-item"><label>连通性检查</label><div class="success">✅ 无孤立节点 · 所有网关有默认分支</div></div>
    <div class="form-item"><label>模拟 1,000 单据执行</label><div class="success">✅ 平均 3.2h · P95 7.8h · 瓶颈: 总经理审批</div></div></div>
    <div class="code-view" style="max-height:200px"><pre>${UI.esc(
`Step1 开始          ─ 1000 通过
Step2 销售主管审批  ─ 通过 972 | 拒绝 28 | 超期 12
Step3 金额网关      ─ ≥10万 214 → 总经理 | 否 758 → 仓库
Step4 总经理审批    ─ 通过 208 | 退回 6
Step5 仓库验收      ─ 通过 751 | 异常 7
Step6 结束          ─ 完成 965 (96.5%)`)}</pre></div>
    <button class="btn btn-p mt10" onclick="UI.toast('模拟变量已生成，可逐步单步执行')">▶ 逐步模拟执行</button>` });
  },
  rules() { UI.modal({ title:'📐 规则引擎（GB 6.4.6.2.3）', size:'lg', footer:false, body:`
    <div class="filter-bar"><button class="btn btn-sm btn-p">＋ 新建规则</button>
      <span class="muted">规则库 12 条 · 版本管理开启</span></div>
    ${[['R-011 金额分级审批','amount>=100000 → route:CEO','v3','on'],
       ['R-012 VIP 自动折扣','customer.level=A1 → discount:0.15','v1','on'],
       ['R-013 重复订单拦截','same_no within 24h → reject','v2','on']].map(([n,e,v,s])=>`
      <div class="item"><div class="flex"><b>${n}</b><span class="tag tag-gray">${v}</span>${UI.statusTag(s)}
      <a class="link" style="margin-left:auto" onclick="UI.toast('规则版本历史/优先级配置')">版本</a></div>
      <div class="mono muted">${UI.esc(e)}</div></div>`).join('')}` });
  },
  importBpmn() { UI.toast('BPMN XML 已解析导入（3 任务 1 网关）'); },
  exportBpmn() { UI.modal({ title:'📤 导出 BPMN 2.0 XML', size:'lg', footer:false, body:
    `<div class="code-view"><pre>${UI.esc(`<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL">
  <process id="orderApproval" name="订单审批流程" isExecutable="true">
    <startEvent id="s1" name="开始"/>
    <userTask id="t1" name="销售主管审批" oac:assignee="mgr:direct" oac:sla="4h"/>
    <exclusiveGateway id="g1" name="金额>=10万?"/>
    <userTask id="t2" name="总经理审批" oac:assignee="pos:p1"/>
    <endEvent id="e1"/>
    <sequenceFlow sourceRef="g1" targetRef="t2"><conditionExpression>${'{amount>=100000}'}</conditionExpression></sequenceFlow>
  </process>
</definitions>`)}</pre></div>` });
  },
  version() { UI.modal({ title:'🕘 流程版本', footer:false, body:`
    ${[['v3','当前','条件网关增加默认分支'],['v2','—','新增总经理环节'],['v1','—','初始版本']].map(([v,cur,n])=>`
    <div class="item"><b>${v}</b> ${cur?`<span class="tag tag-green">${cur}</span>`:''} — ${n}
    ${cur?'':'<a class="link" onclick="UI.toast(已切换到'+v+')">切换</a>'}</div>`).join('')}` });
  },
  publish() { UI.confirm('发布 v3 到测试环境？（生产发布需走审批+灰度）', ()=>UI.toast('v3 已发布至 test 环境成功')); },
};
