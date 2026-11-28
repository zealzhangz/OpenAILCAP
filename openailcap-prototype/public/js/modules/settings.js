/* ============ Module 9: 基础配置中心 (GB 6.3.2 全 8 项) ============ */
App.mods.settings = {
  tab: 0,
  render() {
    const tabs = ['导航菜单','主题风格','登录页面','应用参数','数据字典','定时调度','消息通知','国际化'];
    return `
    <div class="page-head"><h1>⚙️ 基础配置</h1><span class="sub">GB 6.3.2 基础配置能力子域（L1 全 7 项 + L2 消息通知）</span></div>
    <div class="card"><div class="card-b">
      <div class="tabs">${tabs.map((t,i)=>`<button class="tab ${SettingsM.tab===i?'active':''}" onclick="SettingsM.tab=${i};App.go('settings')">${t}</button>`).join('')}</div>
      <div id="setBody">${SettingsM.body()}</div>
    </div></div>`;
  },
  mount() { if (this.tab===0) this.menuOps(); },
  body() {
    const M = SettingsM;
    if (this.tab===0) return `
      <div class="grid cols-2">
        <div><div class="flex mb0" style="margin-bottom:10px"><b>菜单树</b><span class="spacer"></span>
          <button class="btn btn-sm btn-p" onclick="SettingsM.addMenu()">＋ 一级菜单</button></div>
          <div id="menuTree"></div></div>
        <div><div class="form-item"><label>菜单项编辑</label>
          <div class="form-row"><input class="input" id="mnLabel" placeholder="名称"><input class="input" id="mnIcon" placeholder="图标 emoji"></div>
          <input class="input mt10" id="mnPath" placeholder="路由 /orders/list">
          <div class="form-item mt10"><label>可见角色</label><div class="btn-row wrap">
            ${['全体','销售员','销售主管','管理员'].map(r=>`<span class="tag tag-blue" style="cursor:pointer" onclick="this.classList.toggle('tag-gray')">${r}</span>`).join('')}</div></div>
          <button class="btn btn-p" onclick="SettingsM.saveMenu()">保存菜单项</button>
          <div class="help">支持拖拽排序、风格调整（GB 6.3.2.2.2 导航菜单配置）</div></div></div>
      </div>`;
    if (this.tab===1) return `
      <div class="grid cols-2">
        <div><b>预置主题（GB 6.3.2.2.3）</b><div class="swatch-row mt10">
          ${[['靛蓝','#4f46e5','#7c3aed'],['翠绿','#16a34a','#0d9488'],['海洋','#0284c7','#0891b2'],['烈焰','#dc2626','#f97316'],['石墨','#334155','#0f172a']]
          .map(([n,c1,c2])=>`<div class="swatch" title="${n}" style="width:60px;height:60px;background:linear-gradient(135deg,${c1},${c2})"
            onclick="SettingsM.setTheme('${c1}','${c2}')"></div>`).join('')}</div>
          <div class="help mt10">点击应用主题；支持用户自定义主题配置</div>
        </div>
        <div><div class="device-frame"><div class="df-bar"><i style="background:#ff5f57"></i><i style="background:#febc2e"></i><i style="background:#28c840"></i></div>
          <div class="login-preview" id="pv" style="height:180px"><div class="login-box"><h4>华创科技</h4>
          <div class="fake-i">👤 工号/邮箱</div><div class="fake-i">🔑 密码</div><div class="fake-b">登 录</div></div></div></div></div>
      </div>`;
    if (this.tab===2) return `
      <div class="grid cols-2">
        <div><b>登录页布局配置（GB 6.3.2.2.4）</b>
          <div class="form-item mt10"><label>背景样式</label><div class="swatch-row">
          ${['linear-gradient(135deg,#4f46e5,#7c3aed)','linear-gradient(135deg,#0f172a,#334155)','linear-gradient(135deg,#16a34a,#0d9488)','radial-gradient(circle,#7c3aed,#4f46e5)']
          .map((g,i)=>`<div class="swatch" style="width:56px;height:40px;background:${g}" onclick="SettingsM.setBg('${g}')"></div>`).join('')}</div></div>
          <div class="form-item"><label>登录方式开关</label>
          ${[['账号密码',1],['短信验证码',1],['企业微信扫码',0],['钉钉扫码',0],['LDAP/AD',1],['OAuth2 SSO',1]].map(([n,on])=>`
          <div class="flex" style="margin-bottom:8px"><div class="switch ${on?'on':''}" onclick="this.classList.toggle('on')"></div>${n}</div>`).join('')}</div>
          <div class="form-item"><label>MFA 多因素认证</label><div class="flex"><div class="switch on" onclick="this.classList.toggle('on')"></div><span class="muted">管理员强制开启</span></div></div>
        </div>
        <div><div class="device-frame"><div class="df-bar"><i style="background:#ff5f57"></i><i style="background:#febc2e"></i><i style="background:#28c840"></i></div>
          <div class="login-preview" id="pv2"><div class="login-box"><h4>华创科技</h4>
          <div class="fake-i">👤 工号/邮箱</div><div class="fake-i">🔑 密码</div><div class="fake-i">📱 验证码</div><div class="fake-b">登 录</div>
          <div class="flex" style="justify-content:space-between;font-size:10px;color:var(--text-3);margin-top:6px"><span>企微</span><span>SSO</span><span>LDAP</span></div></div></div></div></div>
      </div>`;
    if (this.tab===3) return UI.table({
      cols:[{key:'code',label:'参数编码',render:r=>`<span class="mono">${r.code}</span>`},{key:'name',label:'参数名称'},
        {key:'value',label:'值'},{key:'group',label:'分组'},{key:'desc',label:'说明',render:r=>`<span class="muted">${r.desc||'—'}</span>`}],
      rows: Store.get('params'),
      actions: r=>`<a class="link" onclick="SettingsM.editParam('${r.id}')">编辑</a>` })
      + `<button class="btn btn-p mt10" onclick="SettingsM.addParam()">＋ 新增参数</button>
      <div class="help">应用参数维护/分类/查询（GB 6.3.2.2.5）</div>`;
    if (this.tab===4) return `<div class="dict-layout">
      <div><b>字典列表</b><div class="mt10" id="dictSide">
      ${Store.get('dicts').map(d=>`<div class="item" style="cursor:pointer"><b>${d.name}</b>
      <span class="tag tag-gray mono">${d.code}</span><span class="tag tag-blue">${d.type==='tree'?'树形':'列表'}</span></div>`).join('')}
      <button class="btn btn-sm" onclick="UI.toast('新建字典（列表式/树形/键值对）')">＋ 新建字典</button></div></div>
      <div><b>字典项维护（GB 6.3.2.2.6）</b><div class="mt10" id="dictItems">
      ${Store.get('dicts')[0].items.map(it=>`<div class="item"><span class="tag tag-gray mono">${it.v}</span>
      <b>${it.zh}</b> <span class="muted">${it.en}</span>
      <a class="link" style="float:right" onclick="UI.toast('已删除')">删除</a>
      ${it.children?it.children.map(c=>`<div style="padding-left:18px"><span class="tag tag-blue">${c.v}</span>${c.zh} <span class="muted">${c.en}</span></div>`).join(''):''}</div>`).join('')}
      <div class="help">支持多层级结构维护、查询过滤、多语言值</div></div></div></div>`;
    if (this.tab===5) return UI.table({
      cols:[{key:'name',label:'任务名称'},{key:'cron',label:'Cron 表达式',render:r=>`<span class="mono">${r.cron}</span>`},
        {key:'state',label:'状态',render:r=>UI.statusTag(r.state)},{key:'last',label:'上次运行'},{key:'next',label:'下次运行'}],
      rows: Store.get('jobs'),
      actions: r=>`<a class="link" onclick="UI.toast('已手动触发运行')">运行</a>
        <a class="link" onclick="Store.update('jobs','${r.id}',{state:'${r.state==='on'?'off':'on}'}'});App.go('settings');UI.toast('已切换')">${r.state==='on'?'停用':'启用'}</a>` })
      + `<div class="help mt10">任务定义/调度策略/人工控制/运行统计与监控（GB 6.3.2.2.7）— 运行成功率 99.2%</div>`;
    if (this.tab===6) return `
      <div class="grid cols-2"><div>${UI.table({
        cols:[{key:'name',label:'模板'},{key:'code',label:'编码',render:r=>`<span class="mono">${r.code}</span>`},
          {key:'channel',label:'渠道'},{key:'state',label:'状态',render:r=>UI.statusTag(r.state)}],
        rows: Store.get('msgTemplates'), actions: r=>`<a class="link" onclick="SettingsM.editTpl('${r.id}')">编辑</a>` })}
        <button class="btn btn-p mt10" onclick="UI.toast('模板含变量: {user} {order} {amount}，支持分类管理')">＋ 新建模板</button></div>
      <div><b>模板预览</b><div class="item mt10">📢 <b>审批待办提醒</b><div class="muted mt10">您好 {user}，订单 {order}（金额 {amount} 元）等待您审批，SLA 剩余 {remain}。</div>
      <div class="btn-row mt10"><span class="tag tag-blue">站内信</span><span class="tag tag-blue">邮件</span><span class="tag tag-gray">短信</span></div></div>
      <div class="help">消息模板/分类配置 + 站内提醒（GB 6.3.2.3 L2 消息通知管理）</div></div></div>`;
    return `<div class="grid cols-2">
      <div><b>语言包管理（GB 6.8.2.4.1）</b><div class="mt10">
      ${[['简体中文 zh-CN','✅ 默认','100%'],['English en-US','✅','100%'],['繁體中文 zh-TW','⏳ 规划','—'],['日本語 ja-JP','⏳ 规划','—']]
      .map(([n,s,c])=>`<div class="item"><div class="flex"><b>${n}</b><span class="tag ${s.startsWith('✅')?'tag-green':'tag-gray'}">${s}</span>
      <span class="muted" style="margin-left:auto">覆盖 ${c}</span></div></div>`).join('')}
      <button class="btn" onclick="UI.toast('已上传语言包 fr-FR.json')">＋ 扩展语言包</button></div></div>
      <div><b>本地化规则</b>
      <div class="form-item mt10"><label>时区处理</label><select class="input"><option>Asia/Shanghai (UTC+8)</option><option>跟随用户浏览器</option><option>UTC</option></select></div>
      <div class="form-item"><label>日期格式</label><select class="input"><option>YYYY-MM-DD HH:mm</option><option>MM/DD/YYYY</option></select></div>
      <div class="form-item"><label>货币</label><select class="input"><option>CNY ¥</option><option>USD $</option><option>EUR €</option></select></div>
      <div class="form-item"><label>多时区支持</label><div class="flex"><div class="switch on" onclick="this.classList.toggle('on')"></div><span class="muted">按用户偏好显示（GB 6.8.2.4.1 e）</span></div></div></div></div>`;
  },
  menuOps() {},
  addMenu() { UI.toast('一级菜单已创建'); },
  saveMenu() { UI.toast('菜单项已保存'); },
  setTheme(c1,c2) { const pv = document.getElementById('pv'); if (pv) { pv.style.setProperty('--pv1',c1); pv.style.setProperty('--pv2',c2); } UI.toast('主题已应用'); },
  setBg(g) { const pv = document.getElementById('pv2'); if (pv) { pv.style.background = g; } UI.toast('登录背景已更新'); },
  addParam() { UI.modal({ title:'新增参数', body:UI.drawerForm([
    {key:'code', label:'编码', req:true},{key:'name', label:'名称', req:true},{key:'value', label:'值'},
    {key:'group', label:'分组', type:'select', options:[{v:'业务',l:'业务'},{v:'通知',l:'通知'},{v:'安全',l:'安全'},{v:'AI',l:'AI'}]}]),
    okText:'保存', onOk:()=>{ Store.push('params', UI.collectForm()); UI.closeModal(); App.go('settings'); UI.toast('参数已保存'); }});
  },
  editParam(id) { const p = Store.find('params', id);
    UI.modal({ title:'编辑参数', body:UI.drawerForm([{key:'name',label:'名称'},{key:'value',label:'值'},{key:'desc',label:'说明',type:'textarea'}], p),
      okText:'保存', onOk:()=>{ Store.update('params', id, UI.collectForm()); UI.closeModal(); App.go('settings'); UI.toast('已保存'); }});
  },
  editTpl(id) { UI.toast('消息模板编辑（演示）'); },
};
