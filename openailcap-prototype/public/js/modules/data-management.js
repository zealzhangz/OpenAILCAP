/* ============ Module 10: 权限管理 (GB 6.3.3 + 6.1.6 + 6.6.3a) ============ */
App.mods.perm = {
  tab: 0,
  render() {
    return `
    <div class="page-head"><h1>🔐 权限管理</h1><span class="sub">RBAC+ABAC · 角色管理/资源授权/权限查询/权限调整 · API 开放</span>
      <span class="spacer"></span><button class="btn btn-p" onclick="PermM.addRole()">＋ 新建角色</button></div>
    <div class="card"><div class="card-b">
      <div class="tabs">${['角色管理','权限矩阵','资源授权','权限查询','权限调整','API Key'].map((t,i)=>
        `<button class="tab ${PermM.tab===i?'active':''}" onclick="PermM.tab=${i};App.go('perm')">${t}</button>`).join('')}</div>
      ${PermM.body()}
    </div></div>`;
  },
  body() {
    const M = PermM;
    if (this.tab===0) return UI.table({
      cols:[{key:'name',label:'角色'},{key:'code',label:'编码',render:r=>`<span class="mono">${r.code}</span>`},
        {key:'users',label:'用户数'},{key:'_sys',label:'类型',render:r=>r.sys?'<span class="tag tag-purple">系统内置</span>':'<span class="tag tag-gray">自定义</span>'}],
      rows: Store.get('roles'),
      actions: r=>`<a class="link" onclick="PermM.roleUsers('${r.id}')">分配用户</a><a class="link" onclick="UI.toast('已删除')">删除</a>` })
      + `<div class="help mt10">角色维护 + 用户增删改查（GB 6.3.3.2.1）</div>`;
    if (this.tab===1) {
      const rs = Store.get('roles').map(r=>r.name);
      return `<div class="perm-matrix" style="--pmc:${rs.length}">
        <div class="pm-row"><div class="pm-cell head">资源 / 操作</div>${rs.map(r=>`<div class="pm-cell head">${r}</div>`).join('')}</div>
        ${Store.get('permResources').map((res,ri)=>`<div class="pm-row"><div class="pm-cell res">${res}</div>
        ${rs.map((r,ci)=>`<div class="pm-cell"><div class="pm-check ${Store.get('permMatrix')[r][ri]?'on':''}"
          onclick="this.classList.toggle('on');UI.toast('权限已更新并记录审计日志')"></div></div>`).join('')}</div>`).join('')}
      </div>
      <div class="filter-bar mt10"><span class="tag tag-blue">应用访问</span><span class="tag tag-blue">页面权限</span><span class="tag tag-blue">数据行级</span>
      <span class="tag tag-blue">功能按钮级</span><span class="tag tag-blue">接口权限</span>
      <span class="muted">五类资源授权（GB 6.3.3.2.2）· 变更实时生效并写审计</span></div>`;
    }
    if (this.tab===2) return `<div class="grid cols-2">
      <div><b>数据行级规则（ABAC 条件表达式）</b>
      ${[['销售专员','creator == current_user AND status != completed'],['销售主管','dept == current_user.dept'],['财务','amount >= 0 (全部可见)']]
      .map(([r,e])=>`<div class="item"><b>${r}</b><div class="mono muted mt10">${UI.esc(e)}</div>
      <div class="btn-row mt10"><a class="link" onclick="UI.toast('表达式编辑器')">编辑</a><a class="link" onclick="UI.toast('已测试 3 条样例数据通过')">测试</a></div></div>`).join('')}</div>
      <div><b>接口级授权</b>
      ${[['GET /api/orders','user,approver'],['POST /api/orders','sales'],['DELETE /api/orders/:id','admin'],['GET /api/reports','all']].map(([api,roles])=>`
      <div class="item mono">${api} <span class="tag tag-gray" style="float:right">${roles}</span></div>`).join('')}
      <div class="help mt10">接口权限授权（GB 6.3.3.2.2 e）</div></div></div>`;
    if (this.tab===3) return `<div class="filter-bar">
      <select class="input"><option>按用户查询</option><option>按资源查询</option></select>
      <input class="input" placeholder="输入用户：吴九" value="吴九"><button class="btn btn-p" onclick="PermM.query()">查询</button></div>
      <div id="permQ"><div class="muted">点击查询查看用户的有效权限（继承+额外+ABAC 汇总）</div></div>`;
    if (this.tab===4) return `<div class="grid cols-2">
      <div><b>权限复制</b><div class="item mt10">从角色 <select class="input" style="width:auto"><option>应用开发者</option></select>
      复制到 <select class="input" style="width:auto"><option>审批人</option></select>
      <button class="btn btn-sm btn-p" onclick="UI.toast('已复制 30 项权限')">执行</button></div></div>
      <div><b>权限转移（GB 6.3.3.3 L2）</b><div class="item mt10">用户 吴九 的额外权限转移给 孙十
      <button class="btn btn-sm" onclick="UI.toast('已转移 2 项额外权限')">转移</button></div></div></div>`;
    return UI.table({
      cols:[{key:'name',label:'名称'},{key:'key',label:'Key',render:r=>`<span class="mono">${r.key}</span>`},
        {key:'scope',label:'授权范围',render:r=>`<span class="mono muted">${r.scope}</span>`},
        {key:'created',label:'创建'},{key:'last',label:'最近调用'},{key:'state',label:'状态',render:r=>UI.statusTag(r.state)}],
      rows: Store.get('apiKeys'),
      actions: r=>`<a class="link" onclick="UI.toast('已轮换密钥')">轮换</a><a class="link" onclick="UI.toast('已吊销','err')">吊销</a>` })
      + `<div class="help mt10">对外开放能力（GB 6.8.4.2 L1 对外 API）· 限流 1000/min · IP 白名单</div>`;
  },
  addRole() { UI.modal({ title:'新建角色', body:UI.drawerForm([
    {key:'name', label:'角色名称', req:true},{key:'code', label:'编码', req:true},
    {key:'desc', label:'描述', type:'textarea'}]), okText:'创建',
    onOk:()=>{ const f=UI.collectForm(); Store.push('roles', {id:'r'+Date.now(), name:f.name, code:f.code, users:0});
      Store.data.permMatrix[f.name] = Store.get('permResources').map(()=>0); Store.save();
      UI.closeModal(); App.go('perm'); UI.toast('角色已创建'); }});
  },
  roleUsers(id) { const r = Store.find('roles', id);
    UI.modal({ title:`分配用户 · ${r.name}`, size:'lg', footer:false, body:`
      <div class="filter-bar"><input class="input" placeholder="搜索用户"><button class="btn btn-sm btn-p">＋ 添加</button></div>
      ${Store.get('employees').slice(0,6).map(e=>`<div class="item"><div class="flex"><b>${e.name}</b>
      <span class="muted">${e.code} · ${(Store.get('positions').find(p=>p.id===e.pos)||{}).name}</span>
      <a class="link" style="margin-left:auto" onclick="UI.toast('已移除','warn')">移除</a></div></div>`).join('')}` });
  },
  query() { document.getElementById('permQ').innerHTML = `
    <div class="success">✅ 吴九 的有效权限（共 8 项）</div>
    <div class="grid cols-2 mt10"><div><b>来自角色「销售专员」</b>
    ${['订单查看','订单创建','订单编辑(本人)'].map(p=>`<div class="item">✅ ${p} <span class="tag tag-gray">继承</span></div>`).join('')}</div>
    <div><b>额外授予</b>${['数据导出','报表查看'].map(p=>`<div class="item">✅ ${p} <span class="tag tag-blue">直接授予</span></div>`).join('')}
    <div class="item">⛔ 客户手机号查看 <span class="tag tag-red">ABAC 拒绝: level!=A*</span></div></div></div>`; },
};

/* ============ Module 11: 数据管理 (GB 6.4.3 + 6.5.7) ============ */
App.mods.data = {
  model: 'm1', selRows: [],
  render() {
    return `
    <div class="page-head"><h1>🗄️ 数据管理</h1><span class="sub">运行时数据 CRUD · 导入导出 · 备份恢复 · 多数据源 · 结构迁移</span><span class="spacer"></span>
      <select class="input" style="width:auto" onchange="DataM.model=this.value;App.go('data')">
        ${Store.get('models').map(m=>`<option value="${m.id}" ${m.id===DataM.model?'selected':''}>${m.display}</option>`).join('')}</select>
      <button class="btn" onclick="DataM.import()">📥 导入</button>
      <button class="btn" onclick="DataM.export()">📤 导出</button>
      <button class="btn btn-p" onclick="DataM.addRow()">＋ 新增记录</button>
    </div>
    <div class="filter-bar">
      <input class="input" placeholder="🔍 关键字搜索…" style="width:200px" oninput="DataM.search(this.value)">
      <select class="input"><option>全部状态</option><option>草稿</option><option>已确认</option><option>已发货</option><option>已完成</option></select>
      <button class="btn btn-sm" onclick="UI.toast('高级筛选：金额区间/日期范围/客户等级')">高级筛选</button>
      <span class="muted">视图: </span>
      ${['表格','表单','看板','日历'].map((v,i)=>`<span class="tag ${i===0?'tag-blue':'tag-gray'}" style="cursor:pointer" onclick="UI.toast('切换视图: ${v}')">${v}</span>`).join('')}
    </div>
    <div class="card"><div class="card-b" id="dataTbl"></div></div>
    <div class="grid cols-3 mt14">
      <div class="card"><div class="card-h">💾 备份与还原（GB 6.4.3.3.1）</div><div class="card-b">
        <div class="kv">${[['上次全量备份','11-28 03:00 ✓'],['增量备份','每小时 ✓'],['异地备份','已启用 ✓'],['保留策略','30 天/12 月/永久']] .map(([k,v])=>`<div class="k">${k}</div><div class="v">${v}</div>`).join('')}</div>
        <div class="btn-row mt10"><button class="btn btn-sm" onclick="UI.toast('手动备份已触发')">立即备份</button>
        <button class="btn btn-sm" onclick="UI.toast('快照恢复演练成功(2m14s)')">恢复演练</button></div></div></div>
      <div class="card"><div class="card-h">🔄 结构迁移（GB 6.4.3.3.2 L2）</div><div class="card-b">
        <div class="tl"><div class="tl-item"><div class="tl-t">✅ auto-migrate 检测：Order +1 字段(invoice_no)</div><div class="tl-d">兼容策略: 新列可空，存量数据不回填</div></div>
        <div class="tl-item"><div class="tl-t">✅ 自动备份已先行完成</div><div class="tl-d">归档策略: 旧结构数据 → 冷存储</div></div></div>
        <button class="btn btn-sm" onclick="UI.toast('迁移执行成功，0 行数据丢失')">执行迁移</button></div></div>
      <div class="card"><div class="card-h">🔌 多数据源（GB 6.5.7）</div><div class="card-b">
        ${[['PG 主库(平台)','✅','读写'],['MySQL ERP','✅','只读'],['Oracle 遗留','✅','只读'],['SQLServer 报表','⚠️','连接中']].map(([n,s,m])=>`
        <div class="item"><div class="flex"><b>${n}</b><span class="tag ${s==='✅'?'tag-green':'tag-orange'}">${s}</span>
        <span class="tag tag-gray" style="margin-left:auto">${m}</span></div></div>`).join('')}
        <button class="btn btn-sm" onclick="UI.toast('数据源连接/配置/删除（连接测试通过）')">＋ 管理数据源</button></div></div>`;
  },
  mount() { this.draw(); },
  draw(q) {
    const rows = Store.get('dataRows')[this.model] || [];
    const filtered = q ? rows.filter(r=>JSON.stringify(r).toLowerCase().includes(q.toLowerCase())) : rows;
    const cols = Object.keys(rows[0]||{id:''}).map(k=>({key:k,label:k}));
    document.getElementById('dataTbl').innerHTML = UI.table({
      cols, rows: filtered,
      actions: r=>`<a class="link" onclick="DataM.view('${r.id}')">查看</a><a class="link" onclick="DataM.addRow('${r.id}')">编辑</a><a class="link" onclick="DataM.delRow('${r.id}')">删除</a>` })
    + `<div class="tbl-pagination">共 ${filtered.length} 条 · 已选 0 条
      <span class="spacer" style="flex:1"></span><a class="link" onclick="UI.toast('批量删除需二次确认+审计')">批量操作 ▾</a></div>`;
  },
  search(q) { this.draw(q); },
  view(id) { const rows = Store.get('dataRows')[this.model]; const r = rows.find(x=>x.id===id);
    UI.modal({ title:'记录详情 · '+id, footer:false, body:
      UI.kvGrid(Object.entries(r).map(([k,v])=>[k, k==='amount'?`<span class="watermark-demo">${v}</span>`:v]))
      + `<div class="item mt10 mono">操作历史: 创建(吴九 11-28 09:12) → 修改×2 → 审批通过 — sm3 校验 ✅</div>` });
  },
  addRow(id) { const m = Store.get('models').find(x=>x.id===this.model);
    UI.modal({ title:(id?'编辑':'新增')+'记录 · '+m.display, body:UI.drawerForm(
      m.fields.filter(f=>!f.pk).map(f=>({key:f.name, label:f.name, req:f.req}))),
      okText:'保存', onOk:()=>{ const f=UI.collectForm();
        if (id) { const r = (Store.get('dataRows')[this.model]||[]).find(x=>x.id===id); Object.assign(r, f); Store.save(); }
        else { Store.get('dataRows')[this.model].unshift({id:'NEW-'+Date.now()%10000, ...f}); Store.save(); }
        UI.closeModal(); DataM.draw(); UI.toast('已保存（触发表单校验 + 审计日志 + 逻辑编排）'); }});
  },
  delRow(id) { UI.confirm('删除该记录？将写入审计日志（GB 6.4.3.3.1 c 数据清理）', ()=>{
    Store.data.dataRows[this.model] = Store.data.dataRows[this.model].filter(x=>x.id!==id); Store.save();
    DataM.draw(); UI.toast('已删除'); }); },
  import() { UI.modal({ title:'📥 数据导入', size:'lg', footer:false, body:`
    <div class="item">📄 orders_2026-11.xlsx · 1,204 行</div>
    <div class="success">✅ 校验通过 1,198 · 失败 6（金额格式×4，必填缺失×2）— 失败行已生成错误清单可下载</div>
    <div class="form-item"><label>冲突策略</label><select class="input"><option>按唯一键更新</option><option>跳过</option><option>报错终止</option></select></div>
    <button class="btn btn-p" onclick="UI.closeModal();UI.toast('导入完成 1,198 行')">确认导入</button>` });
  },
  export() { UI.modal({ title:'📤 数据导出', body:UI.drawerForm([
    {key:'fmt', label:'格式', type:'select', options:[{v:'xlsx',l:'Excel'},{v:'csv',l:'CSV'},{v:'pdf',l:'PDF'},{v:'json',l:'JSON'}]},
    {key:'mask', label:'脱敏导出（GB 6.6.3 e）', type:'switch', value:true},
    {key:'scope', label:'范围', type:'select', options:[{v:'cur',l:'当前筛选'},{v:'all',l:'全部'}]}]),
    okText:'导出', onOk:()=>{ UI.closeModal(); UI.toast('导出任务已入队，完成后站内信通知'); }});
  },
};
