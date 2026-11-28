/* ============ 任务待办中心 (GB 6.4.6.2.1 c) ============ */
App.mods.tasks = {
  render() {
    const tasks = Store.get('tasks');
    const cols = [['pending','待处理','⏳'],['forwarded','已转办','↪️'],['done','已完成','✅'],['suspended','已挂起','⏸️']];
    const n = tasks.filter(t=>t.state==='pending').length;
    return `
    <div class="page-head"><h1>✅ 任务待办</h1><span class="sub">个人/团队待办 · 批量审批 · SLA 预警 · 委托代理</span>
      <span class="spacer"></span>
      <button class="btn" onclick="TasksM.batchApprove()">⚡ 批量同意</button>
      <button class="btn" onclick="UI.toast('已开启自动委托：休假期间由代理人处理')">🤝 委托代理设置</button>
    </div>
    <div class="grid cols-4">
      ${[['待处理',tasks.filter(t=>t.state==='pending').length,'var(--warning-soft)','⏳'],
         ['超期风险',1,'var(--danger-soft)','🔴'],
         ['本周已完成',24,'var(--success-soft)','✅'],
         ['平均处理时长','1.8h','var(--info-soft)','⏱️']].map(([l,v,c,i])=>`
      <div class="stat-tile"><div class="ic" style="background:${c}">${i}</div>
      <div><div class="v">${v}</div><div class="l">${l}</div></div></div>`).join('')}
    </div>
    <div class="card mt14"><div class="card-b"><div class="kanban" id="kanban">
      ${cols.map(([s,label,ico])=>`<div class="kb-col" data-state="${s}">
        <div class="kb-col-h">${ico} ${label}<span class="n">${tasks.filter(t=>t.state===s).length}</span></div>
        ${tasks.filter(t=>t.state===s).map(t=>`
        <div class="kb-card" draggable="true" ondragstart="event.dataTransfer.setData('id','${t.id}')">
          <div class="kb-t">${UI.esc(t.title)}</div>
          <div class="kb-m">${UI.priTag(t.pri)} <span>${t.from}</span><span>${t.app==='app_001'?'订单':'请假/合同'}</span></div>
          <div class="kb-m"><span class="${t.sla.startsWith('超期')?'':'muted'}">${t.sla.startsWith('超期')?'🔴 '+t.sla:'⏱ '+t.sla}</span></div>
          ${t.state==='pending'?`<div class="btn-row" style="margin-top:8px">
            <button class="btn btn-sm btn-p" onclick="TasksM.approve('${t.id}')">同意</button>
            <button class="btn btn-sm btn-danger" onclick="TasksM.reject('${t.id}')">拒绝</button>
            <button class="btn btn-sm" onclick="TasksM.more('${t.id}')">更多</button></div>`:''}
        </div>`).join('')}
      </div>`).join('')}
    </div></div></div>
    <div class="card mt14"><div class="card-h">SLA 统计</div><div class="card-b" id="slaStats"></div></div>`;
  },
  mount() { this.sla();
    document.querySelectorAll('.kb-col').forEach(col => {
      col.ondragover = e => e.preventDefault();
      col.ondrop = e => { const id = e.dataTransfer.getData('id'); const t = Store.find('tasks', id);
        if (t) { t.state = col.dataset.state; Store.save(); App.go('tasks'); UI.toast(`任务已移动到「${col.dataset.state}」`); } };
    });
  },
  sla() { const el = document.getElementById('slaStats'); if (!el) return;
    el.innerHTML = `<div class="grid cols-3">
      <div><div class="muted">审批准时率</div><div id="slaG1"></div></div>
      <div style="grid-column:span 2"><div class="muted">各环节平均耗时（小时）</div><div id="slaH"></div></div></div>`;
    setTimeout(()=>{ Charts.gauge(document.getElementById('slaG1'), 96.5, {label:'SLA 达标'});
      Charts.hbar(document.getElementById('slaH'), ['主管审批','总经理审批','仓库验收','HR 备案'], [0.5, 2.5, 1.2, 0.3], {fmt:v=>v+'h'}); }, 50);
  },
  approve(id) { const t = Store.find('tasks', id);
    UI.modal({ title:'审批 · '+t.title, body:`
      ${UI.kvGrid([['发起人', t.from],['当前环节', t.node],['SLA', t.sla]])}
      <div class="form-item mt10"><label>审批意见</label><textarea class="input" placeholder="同意，注意发货时效…"></textarea></div>
      <div class="flex"><div class="switch on" onclick="this.classList.toggle('on')"></div>
        <span class="muted">SM2 电子签名 + 可信时间戳（GB 合规）</span></div>`,
      okText:'✅ 同意并签名', onOk:()=>{ Store.update('tasks', id, {state:'done', result:'approved'});
        UI.closeModal(); App.go('tasks'); UI.toast('审批完成，流程已流转下一环节'); }});
  },
  reject(id) { const t = Store.find('tasks', id);
    UI.modal({ title:'拒绝 · '+t.title, body:`<div class="form-item"><label>拒绝原因（必填）</label>
      <textarea class="input">金额与合同不符，请修正后重新提交</textarea></div>
      <div class="form-item"><label>回退到</label><select class="input"><option>发起人（重新提交）</option><option>上一环节</option></select></div>`,
      okText:'❌ 确认拒绝', onOk:()=>{ Store.update('tasks', id, {state:'done', result:'rejected'});
        UI.closeModal(); App.go('tasks'); UI.toast('已拒绝并回退至发起人'); }});
  },
  more(id) { UI.modal({ title:'更多操作', footer:false, body:`
    ${[['↪️ 转办给他人','选择接收人后任务转移'],['🤝 委托代理','设置代理人代为审批'],['➕ 加签（会签/或签）','增加审批人并行/串行'],
       ['📢 抄送','通知相关人员知悉'],['⏸️ 挂起','暂停等待补充材料'],['👁️ 查看流程图','高亮当前节点']]
      .map(([a,d])=>`<div class="item" style="cursor:pointer" onclick="UI.closeModal();UI.toast('${a.replace(/'/g,'')}（演示）')"><b>${a}</b><div class="muted">${d}</div></div>`).join('')}` });
  },
  batchApprove() { const pend = Store.get('tasks').filter(t=>t.state==='pending');
    UI.confirm(`批量同意 ${pend.length} 个待办任务？<br><span class="muted">将逐一生成电子签名与审计记录</span>`, () => {
      pend.forEach(t=>Store.update('tasks', t.id, {state:'done', result:'approved'}));
      App.go('tasks'); UI.toast(`${pend.length} 个任务已批量审批完成`); }, false);
  },
};

/* ============ 流程实例管理 (GB 6.4.6) ============ */
App.mods.inst = {
  render() {
    const inst = Store.get('instances');
    return `
    <div class="page-head"><h1>📄 流程实例</h1><span class="sub">实例监控 · 性能分析 · 通知警报 · 挂起/恢复/终止</span><span class="spacer"></span>
      <button class="btn" onclick="InstM.export()">📤 导出报表</button></div>
    <div class="grid cols-4">
      ${[['运行中',inst.filter(i=>i.state==='运行中').length,'var(--info-soft)','▶️'],
         ['已完成',inst.filter(i=>i.state==='已完成').length,'var(--success-soft)','✅'],
         ['已挂起',inst.filter(i=>i.state==='已挂起').length,'var(--warning-soft)','⏸️'],
         ['超期',inst.filter(i=>i.sla==='overdue').length,'var(--danger-soft)','🔴']].map(([l,v,c,i])=>`
      <div class="stat-tile"><div class="ic" style="background:${c}">${i}</div><div><div class="v">${v}</div><div class="l">${l}</div></div></div>`).join('')}
    </div>
    <div class="card mt14"><div class="card-h">实例甘特视图</div><div class="card-b"><div class="gantt">
      ${inst.map(i=>`<div class="g-row"><div class="g-lbl">${i.no} · ${i.def}<br><span class="muted">${i.starter} · ${i.start}</span></div>
        <div class="g-track"><div class="g-bar ${i.sla==='overdue'?'over':i.state==='已完成'?'done':i.state==='已挂起'?'wait':'run'}"
        style="left:${10+Math.random()*20}%;width:${40+Math.random()*40}%">${i.node} · ${i.elapsed}</div></div></div>`).join('')}
    </div></div></div>
    <div class="card mt14"><div class="card-h">实例列表</div><div class="card-b">
      ${UI.table({ cols:[
        {key:'no',label:'实例号'},{key:'def',label:'流程'},{key:'starter',label:'发起人'},
        {key:'state',label:'状态',render:r=>UI.statusTag(r.state==='运行中'?'running':r.state==='已完成'?'done':'suspended')},
        {key:'node',label:'当前节点'},{key:'elapsed',label:'耗时'},
        {key:'sla',label:'SLA',render:r=>r.sla==='overdue'?'<span class="tag tag-red">已超期</span>':r.sla==='ok'?'<span class="tag tag-green">正常</span>':'—'}],
        rows: inst, actions: r=>`<a class="link" onclick="InstM.detail('${r.id}')">详情</a>
        <a class="link" onclick="UI.toast('实例已挂起','warn')">挂起</a>` })}</div></div>`;
  },
  mount() {},
  detail(id) { const pi = Store.find('instances', id);
    UI.modal({ title:`实例详情 · ${pi.no}`, size:'lg', footer:false, body:`
      <div class="grid cols-2">
        <div>${UI.kvGrid([['流程定义', pi.def],['发起人', pi.starter],['开始时间', pi.start],
          ['状态', pi.state],['当前节点', pi.node],['累计耗时', pi.elapsed],['SLA', pi.sla==='overdue'?'🔴 已超期':'✅ 正常']])}
        <div class="btn-row mt10">
          <button class="btn btn-sm" onclick="UI.toast('已恢复运行')">▶️ 恢复</button>
          <button class="btn btn-sm" onclick="UI.toast('已跳转至指定节点','warn')">⏭️ 跳转</button>
          <button class="btn btn-sm btn-danger" onclick="UI.toast('实例已终止并触发补偿','err')">⏹️ 终止</button>
          <button class="btn btn-sm" onclick="UI.toast('已转派给 赵六')">↪️ 重新分配</button>
        </div></div>
        <div><b>流程变量</b><div class="code-view" style="max-height:110px"><pre>${UI.esc(
`{ "amount": 152000, "customer": "C-001",
  "approver": "周百", "status": "pending" }`)}</pre></div></div>
      </div>
      <div class="mt14"><b>执行轨迹</b><div class="tl mt10">
        ${pi.steps.map(s=>`<div class="tl-item ${s.state==='running'?'warn':''}">
        <div class="tl-t">${s.state==='done'?'✅':s.state==='running'?'⏳':'⬚'} ${s.node} ${s.by?'· '+s.by:''}</div>
        <div class="tl-d">${s.time||''}</div></div>`).join('')}</div></div>
      <div class="mt10"><b>审计链（不可篡改）</b>
        <div class="item mono">sm3: pi1→al1→al2→… 完整性校验通过 ✅（GB 6.7.6 / 6.6.3 c）</div></div>` });
  },
  export() { UI.toast('实例报表已导出 Excel'); },
};
