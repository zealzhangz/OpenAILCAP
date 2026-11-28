/* ============ Module 4: 表单设计器 (GB 6.2.2) ============ */
App.mods.form = {
  selField: null, dragType: null,
  FIELDS: [
    ['基础','text','📝 单行文本'],['基础','textarea','📄 多行文本'],['基础','number','🔢 数字'],['基础','date','📅 日期'],
    ['基础','datetime','🕐 日期时间'],['基础','select','📋 下拉选择'],['基础','radio','🔵 单选'],['基础','checkbox','☑️ 复选'],
    ['高级','table','📊 子表格'],['高级','file','📂 文件上传'],['高级','image','🖼️ 图片'],['高级','user','👤 人员选择'],
    ['高级','dept','🏢 部门选择'],['高级','region','🗺️ 行政区划'],['高级','rate','⭐ 评分'],['高级','switch','🎚️ 开关'],
    ['展示','divider','➖ 分割线'],['展示','text-view','📌 文本说明'],['展示','calc','🧮 计算字段'],['展示','sign','✍️ 手写签名'],
    ['图表','line-chart','📈 折线图'],['图表','bar-chart','📊 柱状图'],['素材','image-banner','/banner 横幅'],['素材','video','🎬 视频'],
  ],
  LAYOUTS: ['栅格布局','自由布局','表格布局','嵌套布局','页签布局','堆叠布局'],

  render() {
    const f = Store.get('forms')[0];
    return `
    <div class="page-head"><h1>🧩 表单设计器</h1><span class="sub">${f.name} · GB 6.2.2 组件/样式/数据/交互 + 多端适配</span>
      <span class="spacer"></span>
      <button class="btn btn-sm" onclick="FormM.undo()" title="撤销">↩️</button>
      <button class="btn btn-sm" onclick="FormM.redo()" title="重做">↪️</button>
      <select class="input" style="width:auto" onchange="FormM.setLayout(this.value)">
        ${FormM.LAYOUTS.map(l=>`<option>${l}</option>`).join('')}</select>
      <button class="btn" onclick="FormM.preview()">👁️ 预览</button>
      <button class="btn" onclick="FormM.multiLang()">🌐 多语言</button>
      <button class="btn btn-p" onclick="FormM.save()">💾 保存</button>
    </div>
    <div class="designer">
      <div class="dz-left">
        <div class="dz-left-h">组件库（拖拽到画布）</div>
        <input class="input" style="margin:0 8px;width:calc(100% - 16px)" placeholder="🔍 搜索组件…" oninput="FormM.filterComp(this.value)">
        ${[['基础字段'],['高级字段'],['展示字段'],['图表组件'],['素材组件']].map(([c])=>`<div class="dz-cat">${c}</div>`).join('')}
        ${FormM.FIELDS.map(([cat,t,label])=>`<div class="dz-item" draggable="true" data-type="${t}"
          ondragstart="FormM.dragStart(event,'${t}')" onclick="FormM.drop(null,'${t}')">
          <span>${label.split(' ')[0]}</span>${label.split(' ')[1]}</div>`).join('')}
        <div class="dz-cat">AI</div>
        <div class="dz-item" style="border-style:dashed" onclick="FormM.aiFields()">🤖 AI 推荐字段</div>
      </div>
      <div class="dz-center"><div class="dz-canvas" id="formCanvas"
        ondragover="event.preventDefault()" ondrop="FormM.drop(event)">
        <div class="card" style="max-width:760px;margin:0 auto;padding:20px 24px">
          <h3 style="margin-bottom:14px">📋 ${f.name}</h3>
          <div class="grid" style="grid-template-columns:repeat(24,1fr);gap:8px" id="cvFields"></div>
        </div></div></div>
      <div class="dz-right" id="fieldProps"><div class="muted">选中字段后在此配置属性</div></div>
    </div>`;
  },
  mount() { this.drawCanvas(); },
  dragStart(e, t) { this.dragType = t; e.target.classList.add('dragging'); },
  filterComp(q) { document.querySelectorAll('.dz-item').forEach(el=>{ el.style.display = el.textContent.toLowerCase().includes(q.toLowerCase())?'':'none'; }); },

  drop(ev, type) {
    const t = type || this.dragType; if (!t) return;
    this.dragType = null;
    const f = Store.get('forms')[0];
    f.fields.push({ id:'x'+Date.now(), label:{text:'文本',number:'数字',date:'日期',select:'选择',textarea:'说明',table:'子表',file:'附件'}[t]||t,
      field:'field_'+(f.fields.length+1), type:t, req:false, span:12 });
    Store.save(); this.drawCanvas();
  },

  drawCanvas() {
    const f = Store.get('forms')[0];
    document.getElementById('cvFields').innerHTML = f.fields.map((x,i)=>`
      <div class="cv-field ${this.selField===x.id?'sel':''}" style="grid-column:span ${x.span}"
        onclick="FormM.pick('${x.id}')">
        <div class="fld-label">${x.label} ${x.req?'<span class="req">*</span>':''}
          ${x.ai?'<span class="tag tag-purple">AI</span>':''} ${x.showIf?`<span class="tag tag-blue">条件显示</span>`:''}</div>
        ${this.renderCtrl(x)}
        <button class="btn btn-sm btn-danger del" onclick="event.stopPropagation();FormM.delField('${x.id}')">删除</button>
      </div>`).join('');
    this.renderProps();
  },
  renderCtrl(x) {
    const map = {
      text:'<div class="fake-input">请输入…</div>', textarea:'<div class="fake-input" style="height:50px">请输入内容…</div>',
      number:'<div class="fake-input">0.00</div>', date:'<div class="fake-input">📅 2026-11-28</div>',
      datetime:'<div class="fake-input">🕐 2026-11-28 16:00</div>',
      select:'<div class="fake-input">请选择 ▾</div>', radio:'<div class="fake-input">🔵 🔵 🔵</div>',
      checkbox:'<div class="fake-input">☑️ ☑️</div>', table:'<div class="fake-input" style="height:44px">📊 子表格（+行 -行）</div>',
      file:'<div class="fake-input">📂 点击或拖拽上传</div>', image:'<div class="fake-input">🖼️</div>',
      user:'<div class="fake-input">👤 选择人员</div>', dept:'<div class="fake-input">🏢 选择部门</div>',
      sign:'<div class="fake-input" style="height:44px">✍️ 手写签名区</div>', calc:'<div class="fake-input">= amount * 0.13</div>',
      line:'<div style="border-top:1px dashed var(--border)"></div>',
      'divider':'<div style="border-top:1px solid var(--border);margin:4px 0"></div>',
      'text-view':'<div class="muted">这是一段说明文本…</div>',
      'line-chart':'<div class="fake-input" style="height:44px">📈 折线图</div>', 'bar-chart':'<div class="fake-input" style="height:44px">📊 柱状图</div>',
      'image-banner':'<div class="fake-input" style="height:44px">🖼️ 横幅图</div>', video:'<div class="fake-input" style="height:44px">🎬 视频播放器</div>',
      region:'<div class="fake-input">🗺️ 省 / 市 / 区</div>', rate:'<div class="fake-input">⭐⭐⭐⭐⭐</div>', switch:'<div class="fake-input">🎚️</div>',
    };
    return map[x.type] || map.text;
  },

  pick(id) { this.selField = id; this.drawCanvas(); },
  delField(id) { const f = Store.get('forms')[0]; f.fields = f.fields.filter(x=>x.id!==id);
    if (this.selField===id) this.selField=null; Store.save(); this.drawCanvas(); UI.toast('字段已删除'); },

  renderProps() {
    const f = Store.get('forms')[0]; const x = f.fields.find(v=>v.id===this.selField);
    const el = document.getElementById('fieldProps');
    if (!x) { el.innerHTML = '<div class="muted">选中字段后在此配置属性</div>'; return; }
    el.innerHTML = `
      <div class="form-item"><label>标签 label</label><input class="input" value="${UI.esc(x.label)}"
        oninput="FormM.up('label',this.value)"></div>
      <div class="form-item"><label>字段 field</label><input class="input mono" value="${x.field}"
        oninput="FormM.up('field',this.value)"></div>
      <div class="form-row">
        <div class="form-item"><label>占位宽度 span</label><select class="input" onchange="FormM.up('span',+this.value)">
          ${[6,8,12,16,24].map(s=>`<option ${s===x.span?'selected':''}>${s}</option>`).join('')}</select></div>
        <div class="form-item"><label>类型</label><input class="input" value="${x.type}" disabled></div>
      </div>
      <div class="flex" style="margin-bottom:10px"><div class="switch ${x.req?'on':''}" onclick="FormM.up('req',this.classList.toggle('on'))"></div><span>必填 required</span></div>
      <div class="form-item"><label>校验规则</label>
        <div class="btn-row wrap">
          ${['必填','正数','最大:9999999','唯一','长度:2-64','自定义正则'].map(r=>`<span class="tag tag-blue" style="cursor:pointer" onclick="UI.toast('已应用规则：${r}')">${r}</span>`).join('')}
        </div></div>
      <div class="form-item"><label>默认值 / 联动</label>
        <input class="input" placeholder="如：={{DATE()}}" value="${UI.esc(x.def||'')}" oninput="FormM.up('def',this.value)"></div>
      <div class="form-item"><label>条件显示 showIf（GB 界面交互）</label>
        <input class="input mono" placeholder="amount>=100" value="${UI.esc(x.showIf||'')}"
          oninput="FormM.up('showIf',this.value)"></div>
      <div class="form-item"><label>字段级权限（GB 6.3.3 数据权限）</label>
        <div class="btn-row wrap">
          <span class="tag tag-green">销售员:可见</span><span class="tag tag-gray">审批人:可见</span>
          <a class="link" onclick="UI.toast('权限配置弹层（角色×字段读写）')">配置…</a></div></div>
      <div class="form-item"><label>交互事件（点击/失焦/变更）</label>
        <button class="btn btn-sm" onclick="UI.toast('事件绑定：onBlur 校验 / onChange 联动 / onClick 提交')">⚡ 绑定事件</button></div>
      <div class="form-item"><label>AI 优化</label>
        <button class="btn btn-sm" onclick="UI.toast('🤖 已优化 label 与校验规则')">🤖 智能建议</button></div>`;
  },
  up(k, v) { const f = Store.get('forms')[0]; const x = f.fields.find(y=>y.id===this.selField);
    if (x) { x[k] = v; Store.save(); if (k==='label'||k==='span'||k==='req') this.drawCanvas(); } },

  aiFields() {
    UI.modal({ title:'🤖 AI 字段推荐', body:`<div class="muted" style="margin-bottom:10px">基于「订单表单」上下文与 1,284 个同类表单统计：</div>
      ${[['收货地址','text','92% 的订单表单包含'],['配送方式','select','行业模板推荐'],['优惠券码','text','同类场景 71%'],['紧急程度','radio','审批场景 83%'],['销售负责人','user','组织架构联动']].map(([l,t,w])=>`
      <div class="item"><div class="flex"><input type="checkbox" checked> <b>${l}</b><span class="tag tag-gray">${t}</span>
      <span class="muted" style="margin-left:auto">${w}</span></div></div>`).join('')}`,
      okText:'批量添加 5 个字段', onOk:()=>{ UI.closeModal(); UI.toast('已添加 5 个 AI 推荐字段'); const f=Store.get('forms')[0];
        ['收货地址','配送方式','优惠券码','紧急程度','销售负责人'].forEach(l=>f.fields.push({id:'x'+Date.now()+Math.random(),label:l,field:'ai_'+l,type:l==='配送方式'?'select':l==='紧急程度'?'radio':'text',req:false,span:12,ai:true}));
        Store.save(); FormM.drawCanvas(); }});
  },
  preview() { const f = Store.get('forms')[0];
    UI.modal({ title:'👁️ 表单预览', size:'lg', footer:false, body:`<div class="device-frame">
      <div class="df-bar"><i style="background:#ff5f57"></i><i style="background:#febc2e"></i><i style="background:#28c840"></i></div>
      <div style="padding:20px"><h3 style="margin-bottom:14px">${f.name}</h3>
      ${f.fields.map(x=>`<div class="form-item"><label>${x.label}${x.req?'<span class="req">*</span>':''}</label>${FormM.renderCtrl(x).replace('fake-input','input')}</div>`).join('')}
      <div class="btn-row"><button class="btn btn-p">提交</button><button class="btn">暂存</button></div></div></div>` });
  },
  multiLang() { UI.modal({ title:'🌐 表单多语言配置', size:'lg', footer:false, body:`
    <div class="tbl-wrap"><table class="tbl"><thead><tr><th>字段</th><th>中文</th><th>English</th><th>AI 翻译</th></tr></thead><tbody>
    ${Store.get('forms')[0].fields.slice(0,6).map(x=>`<tr><td class="mono">${x.field}</td><td>${x.label}</td>
      <td>${({订单编号:'Order No.',客户:'Customer',订单金额:'Amount',下单日期:'Order Date',备注:'Remark',发票抬头:'Invoice Title'})[x.label]||x.label+' (EN)'}</td>
      <td><a class="link" onclick="UI.toast('🤖 AI 翻译完成')">翻译</a></td></tr>`).join('')}
    </tbody></table></div>` });
  },
};
