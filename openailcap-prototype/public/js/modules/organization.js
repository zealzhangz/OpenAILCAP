/* ============ Module 2: 组织架构管理 (GB 6.2.3.3.1 参与者规则) ============ */
App.mods.org = {
  selDept: null, selEmp: null,
  render() {
    return `
    <div class="page-head"><h1>🏢 组织架构</h1><span class="sub">部门/岗位/汇报线 · 审批人规则数据源 · AI 权限推荐</span>
      <span class="spacer"></span>
      <button class="btn" onclick="OrgM.importExcel()">📥 Excel 导入</button>
      <button class="btn" onclick="OrgM.syncAD()">🔄 同步 AD/LDAP</button>
      <button class="btn btn-p" onclick="OrgM.addDept()">＋ 新增部门</button>
    </div>
    <div class="grid cols-32">
      <div class="card"><div class="card-h">架构树 <span class="spacer"></span><span class="muted">${Store.get('employees').length} 人</span></div>
        <div class="card-b org-tree" id="orgTree"></div></div>
      <div>
        <div class="card"><div class="card-h" id="orgSideTitle">详情</div><div class="card-b" id="orgSide">
          <div class="empty"><div class="big">👆</div>点击左侧部门或员工查看详情</div></div></div>
        <div class="card mt14"><div class="card-h">🤖 AI 权限推荐（同岗位统计 + 操作历史 + 主管继承）</div>
          <div class="card-b" id="orgReco"><div class="muted">选择一名员工后自动生成推荐</div></div></div>
      </div>
    </div>
    <div class="card mt14"><div class="card-h">岗位与权限模板 <span class="spacer"></span>
      <button class="btn btn-sm" onclick="OrgM.addPos()">＋ 新增岗位</button></div>
      <div class="card-b" id="posList"></div></div>
    <div class="card mt14"><div class="card-h">变更历史（GB 审计要求）</div><div class="card-b" id="chgList"></div></div>`;
  },
  mount() { this.drawTree(); this.drawPos(); this.drawChg(); },

  drawTree() {
    const depts = Store.get('depts'), emps = Store.get('employees');
    const render = (pid) => {
      const kids = depts.filter(d => d.parentId === pid);
      if (!kids.length) return '';
      return `<ul>${kids.map(d => `<li>
        <div class="org-node dept ${this.selDept===d.id?'sel':''}" onclick="OrgM.pickDept('${d.id}')">
          <span class="n-ic">🏢</span>${UI.esc(d.name)}<span class="tag tag-gray">${d.code}</span></div>
        ${render(d.id)}
        <ul>${emps.filter(e=>e.dept===d.id).map(e=>`<li>
          <div class="org-node ${this.selEmp===e.id?'sel':''}" onclick="OrgM.pickEmp('${e.id}')">
            <span class="n-ic">${e.name[0]}</span>${UI.esc(e.name)}<span class="tag tag-blue">${(Store.get('positions').find(p=>p.id===e.pos)||{}).name||''}</span>
            ${e.active?'':'<span class="tag tag-gray">停用</span>'}</div></li>`).join('')}</ul>
      </li>`).join('')}</ul>`;
    };
    document.getElementById('orgTree').innerHTML = render(null);
  },

  drawPos() {
    document.getElementById('posList').innerHTML = UI.table({
      cols:[{key:'name',label:'岗位'},{key:'level',label:'职级'},{key:'template',label:'权限模板'},
        {key:'_n',label:'在职人数', render:r=>Store.get('employees').filter(e=>e.pos===r.id).length+' 人'}],
      rows: Store.get('positions').map(p=>({...p})),
      actions: r => `<a class="link" onclick="OrgM.editTpl('${r.id}')">编辑模板</a>` });
  },
  drawChg() {
    document.getElementById('chgList').innerHTML = `<div class="tl">${Store.get('empChanges').map(c=>`
      <div class="tl-item"><div class="tl-t">${c.type==='transfer'?'🔄 调岗':'📈 晋升'} · ${c.note}</div>
      <div class="tl-d">${c.time} · 审批人 ${c.by}</div></div>`).join('')}</div>`;
  },

  pickDept(id) { this.selDept=id; this.selEmp=null; this.drawTree();
    const d = Store.find('depts', id); const mgr = Store.find('employees', d.manager);
    document.getElementById('orgSideTitle').textContent = '🏢 ' + d.name;
    document.getElementById('orgReco').innerHTML = '<div class="muted">选择一名员工后自动生成推荐</div>';
    document.getElementById('orgSide').innerHTML = UI.kvGrid([
      ['部门编码', d.code],['上级部门', d.parentId?(Store.find('depts',d.parentId)||{}).name:'—'],
      ['负责人', mgr?mgr.name:'—'],['在职人数', Store.get('employees').filter(e=>e.dept===id).length+' 人'],
      ['审批规则', '可被 BPM 引用为「部门主管」参与者']])
    + `<div class="btn-row mt10"><button class="btn btn-sm" onclick="OrgM.addDept('${id}')">＋ 子部门</button>
       <button class="btn btn-sm" onclick="OrgM.editDept('${id}')">编辑</button>
       <button class="btn btn-sm btn-danger" onclick="OrgM.delDept('${id}')">删除</button></div>`;
  },

  pickEmp(id) { this.selEmp=id; this.selDept=null; this.drawTree();
    const e = Store.find('employees', id);
    const dept = Store.find('depts', e.dept), pos = Store.find('positions', e.pos);
    document.getElementById('orgSideTitle').textContent = '👤 ' + e.name;
    document.getElementById('orgSide').innerHTML = UI.kvGrid([
      ['工号', e.code],['部门', dept?.name||'—'],['岗位', `${pos?.name||''} (${pos?.level||''})`],
      ['直属主管', e.mgr?(Store.find('employees',e.mgr)||{}).name:'—'],['邮箱', e.email],['手机(脱敏)', e.phone],
      ['状态', e.active?'✅ 在职':'⛔ 停用']])
      + `<div class="btn-row mt10"><button class="btn btn-sm" onclick="OrgM.transfer('${id}')">调岗</button>
        <button class="btn btn-sm" onclick="OrgM.promote('${id}')">晋升</button>
        <button class="btn btn-sm" onclick="OrgM.toggleEmp('${id}')">${e.active?'停用':'启用'}</button></div>`;
    /* AI recommendations */
    const recos = [
      {p:'create_order', c:0.95, why:'岗位「'+(pos?.name||'')+'」标准权限'},
      {p:'view_reports', c:0.88, why:'同岗位 90% 成员具备'},
      {p:'export_customer', c:0.65, why:'近 7 天 3 次访问被拒（操作历史）'},
      {p:'approve_subordinate', c:0.60, why:'直属主管拥有且可继承'} ];
    document.getElementById('orgReco').innerHTML = recos.map(r=>`
      <div class="item"><b>${r.p}</b> <span class="tag ${r.c>0.8?'tag-green':r.c>0.6?'tag-orange':'tag-gray'}">置信 ${(r.c*100)|0}%</span>
      <div class="muted">${r.why}</div>
      <div class="btn-row" style="margin-top:6px"><button class="btn btn-sm btn-p" onclick="UI.toast('已授予 ${r.p}')">采纳</button>
      <button class="btn btn-sm" onclick="UI.toast('已忽略')">忽略</button></div></div>`).join('');
  },

  addDept(pid) { UI.modal({ title:'新增部门', body:UI.drawerForm([
    {key:'name', label:'部门名称', req:true},{key:'code', label:'部门编码', req:true, ph:'HC-XX-01'},
    {key:'manager', label:'负责人', type:'select', options:Store.get('employees').map(e=>({v:e.id,l:e.name}))} ]),
    okText:'保存', onOk:() => { const f=UI.collectForm(); if(!f.name||!f.code) return UI.toast('必填项缺失','err');
      Store.push('depts', {id:'d'+Date.now(), name:f.name, code:f.code, parentId:pid||null, manager:f.manager});
      UI.closeModal(); OrgM.drawTree(); UI.toast('部门已创建'); }});
  },
  editDept(id) { const d = Store.find('depts', id);
    UI.modal({ title:'编辑部门', body:UI.drawerForm([{key:'name',label:'名称'},{key:'code',label:'编码'}], d),
      okText:'保存', onOk:()=>{ Store.update('depts', id, UI.collectForm()); UI.closeModal(); OrgM.drawTree(); UI.toast('已保存'); }});
  },
  delDept(id) { UI.confirm('删除部门将同时解除其员工归属关系，确认？', ()=>{ Store.remove('depts', id); OrgM.drawTree(); UI.toast('已删除'); }); },
  addPos() { UI.modal({ title:'新增岗位', body:UI.drawerForm([
    {key:'name',label:'岗位名称',req:true},{key:'level',label:'职级',ph:'M1-M5'},
    {key:'template',label:'权限模板', type:'select', options:[{v:'tpl_sales',l:'销售专员模板'},{v:'tpl_sales_lead',l:'销售主管模板'},{v:'tpl_dev',l:'工程师模板'},{v:'tpl_fin',l:'财务模板'}]}]),
    okText:'保存', onOk:()=>{ Store.push('positions', UI.collectForm()); UI.closeModal(); OrgM.drawPos(); UI.toast('岗位已创建'); }});
  },
  editTpl(id) { const p = Store.find('positions', id);
    UI.modal({ title:`权限模板 · ${p.name}`, size:'lg', footer:false, body:`
      <div class="perm-matrix" style="--pmc:4">
        <div class="pm-row"><div class="pm-cell head">资源</div><div class="pm-cell head">查</div><div class="pm-cell head">增</div><div class="pm-cell head">改</div><div class="pm-cell head">删</div></div>
        ${['订单','客户','报表','审批','导出'].map(res=>`<div class="pm-row"><div class="pm-cell res">${res}</div>
          ${[0,1,2,3].map(()=>`<div class="pm-cell"><div class="pm-check ${Math.random()>0.4?'on':''}" onclick="this.classList.toggle('on')"></div></div>`).join('')}</div>`).join('')}
      </div>`, onOpen:()=>{} });
  },
  transfer(id) { const e = Store.find('employees', id);
    UI.modal({ title:'员工调岗 · '+e.name, body:UI.drawerForm([
      {key:'dept', label:'新部门', type:'select', options:Store.get('depts').map(d=>({v:d.id,l:d.name}))},
      {key:'pos', label:'新岗位', type:'select', options:Store.get('positions').map(p=>({v:p.id,l:p.name}))},
      {key:'mgr', label:'新主管', type:'select', options:Store.get('employees').map(m=>({v:m.id,l:m.name}))},
      {key:'note', label:'调岗原因', type:'textarea'} ]),
      okText:'提交（需审批）', onOk:()=>{ UI.closeModal(); UI.toast('调岗申请已发起，走人事审批流'); }});
  },
  promote(id) { UI.toast('晋升流程已发起（演示）'); },
  toggleEmp(id) { const e = Store.find('employees', id); Store.update('employees', id, {active:!e.active}); OrgM.pickEmp(id); UI.toast(e.active?'已停用':'已启用'); },
  importExcel() { UI.modal({ title:'Excel 批量导入', size:'lg', footer:false, body:`
    <div class="item">📥 拖拽 <b>org.xlsx</b> 到此处（演示）</div>
    <div class="item mono">列: 工号 | 姓名 | 部门编码 | 岗位编码 | 主管工号 | 手机 | 邮箱</div>
    <div class="success">✅ 解析成功：9 行 · 校验通过 9 行 · 冲突 0 行<br>汇报线环路检测：无 · 岗位映射缺失：无</div>
    <button class="btn btn-p" onclick="UI.closeModal();UI.toast('已导入 9 名员工/6 个部门')">确认导入</button>` });
  },
  syncAD() { UI.toast('AD/LDAP 同步完成：新增 0 / 变更 2 / 停用 0'); },
};
