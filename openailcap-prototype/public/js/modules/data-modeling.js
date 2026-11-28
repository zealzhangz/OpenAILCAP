/* ============ Module 3: 数据建模设计器 (GB 6.4.3 L1 五项管理) ============ */
App.mods.model = {
  sel: null, drag:null,
  render() {
    return `
    <div class="page-head"><h1>📊 数据建模</h1><span class="sub">实体/属性/关系/字典/视图 五项管理 · AI 建模 · Prisma Schema 生成</span>
      <span class="spacer"></span>
      <button class="btn" onclick="ModelM.importSQL()">导入 SQL</button>
      <button class="btn" onclick="ModelM.aiGen()">🤖 AI 建模</button>
      <button class="btn btn-p" onclick="ModelM.addTable()">＋ 新建实体</button>
    </div>
    <div class="card">
      <div class="dz-toolbar">
        <b>ER 画布</b><span class="sep"></span>
        <button class="btn btn-sm" onclick="ModelM.autoLayout()">⤢ 自动布局</button>
        <button class="btn btn-sm" onclick="ModelM.genSchema()">生成 Prisma</button>
        <button class="btn btn-sm" onclick="ModelM.genDDL()">生成 SQL DDL</button>
        <button class="btn btn-sm" onclick="UI.toast('迁移预览：3 tables, 0 breaking changes')">迁移预览</button>
        <span class="spacer"></span><span class="muted">拖拽表体可移动 · 点击表编辑字段</span>
      </div>
      <div class="er-canvas"><div class="er-inner" id="erInner"><svg class="er-svg" id="erSvg"></svg></div></div>
    </div>
    <div class="grid cols-2 mt14">
      <div class="card"><div class="card-h">📖 数据字典 <span class="spacer"></span><button class="btn btn-sm" onclick="ModelM.addDict()">＋ 新字典</button></div>
        <div class="card-b" id="dictList"></div></div>
      <div class="card"><div class="card-h">🔗 关系 & 视图</div><div class="card-b" id="relList"></div></div>
    </div>`;
  },
  mount() { this.drawTables(); this.drawRelations(); this.drawDicts(); },

  drawTables() {
    const inner = document.getElementById('erInner');
    inner.querySelectorAll('.er-table').forEach(el=>el.remove());
    Store.get('models').forEach(m => {
      const el = document.createElement('div');
      el.className = 'er-table' + (this.sel===m.id?' sel':'');
      el.style.left = m.x+'px'; el.style.top = m.y+'px';
      el.innerHTML = `<div class="er-t-h">📘 ${m.display} (${m.name})<span class="cnt">${m.fields.length} 字段</span></div>
        ${m.fields.map(f=>`<div class="er-t-row ${f.pk?'pk':''}"><span class="t-name">${f.name}</span>
          <span class="t-type">${f.type}${f.len?'('+f.len+')':''}${f.encrypt?' 🔒':''}</span></div>`).join('')}`;
      el.onmousedown = (e) => this.startDrag(e, m, el);
      el.onclick = () => { this.sel = m.id; this.drawTables(); this.editTable(m.id); };
      inner.appendChild(el);
    });
    this.drawRelations();
  },

  drawRelations() {
    const svg = document.getElementById('erSvg'); if (!svg) return;
    svg.setAttribute('width','960'); svg.setAttribute('height','460');
    const getAnchor = (mid) => { const m = Store.get('models').find(x=>x.id===mid);
      return m ? { x: m.x+105, y: m.y+20, w:210, h:34+18*m.fields.length } : null; };
    let paths = '';
    Store.get('relations').forEach(r => {
      const a = getAnchor(r.from), b = getAnchor(r.to); if(!a||!b) return;
      const y1 = a.y + a.h/2, y2 = b.y + b.h/2;
      const mid = (a.x+a.w/2 + b.x+b.w/2)/2;
      paths += `<path d="M${a.x+a.w},${y1} C${mid},${y1} ${mid},${y2} ${b.x},${y2}"/>
        <text x="${mid}" y="${(y1+y2)/2-4}" text-anchor="middle" font-size="9.5" fill="#475569">${r.type}</text>`;
    });
    svg.innerHTML = paths;
    const rel = Store.get('relations');
    document.getElementById('relList').innerHTML = rel.length ? rel.map(r=>{
      const f=Store.get('models').find(m=>m.id===r.from), t=Store.get('models').find(m=>m.id===r.to);
      return `<div class="item">🔗 <b>${f?.display}</b> (${r.f}) <span class="tag tag-blue">${r.type}</span> <b>${t?.display}</b> (${r.t})
        <a class="link" onclick="ModelM.delRel('${r.id}')">删除</a></div>`; }).join('')
      : '<div class="muted">暂无关系，点击实体字段 ref 可创建</div>';
  },

  drawDicts() {
    document.getElementById('dictList').innerHTML = Store.get('dicts').map(d=>`
      <div class="acc"><div class="acc-h" onclick="this.parentNode.classList.toggle('open')">
        📖 ${d.name} <span class="tag tag-gray mono">${d.code}</span><span class="tag tag-blue">${d.type==='tree'?'树形':'列表'}</span><span class="arr">▶</span></div>
      <div class="acc-b">${d.items.map(it=>`<div class="flex" style="margin-bottom:6px">
        <span class="tag tag-gray mono">${it.v}</span> ${it.zh} / ${it.en}
        ${it.children?it.children.map(c=>`<span class="tag tag-blue">${c.v} ${c.zh}</span>`).join(''):''}</div>`).join('')}
      <button class="btn btn-sm" onclick="UI.toast('字典项编辑（演示）')">编辑项</button></div></div>`).join('');
  },

  startDrag(e, m, el) {
    if (e.target.closest('.er-t-h') && e.offsetX > 150) return;
    const sx=e.clientX, sy=e.clientY, ox=m.x, oy=m.y;
    const move = (ev) => { m.x = ox+ev.clientX-sx; m.y = oy+ev.clientY-sy;
      el.style.left=m.x+'px'; el.style.top=m.y+'px'; this.drawRelations(); };
    const up = () => { document.removeEventListener('mousemove',move); document.removeEventListener('mouseup',up); Store.save(); };
    document.addEventListener('mousemove',move); document.addEventListener('mouseup',up);
    e.preventDefault();
  },
  autoLayout() { const ms = Store.get('models'); ms.forEach((m,i)=>{ m.x = 40+(i%3)*330; m.y = 30+Math.floor(i/3)*260; });
    Store.save(); this.drawTables(); },

  addTable() { UI.modal({ title:'新建实体', body:UI.drawerForm([
    {key:'name', label:'表名(英文)', req:true, ph:'Order'},{key:'display', label:'显示名', req:true, ph:'订单表'} ]),
    okText:'创建', onOk:()=>{ const f=UI.collectForm(); if(!f.name) return UI.toast('表名必填','err');
      Store.push('models', {id:'m'+Date.now(), name:f.name, display:f.display||f.name, appId:'app_001',
        x:100+Math.random()*400, y:80+Math.random()*200,
        fields:[{name:'id', type:'string', pk:true, req:true}]});
      UI.closeModal(); ModelM.drawTables(); ModelM.drawRelations(); UI.toast('实体已创建'); }});
  },
  editTable(id) { const m = Store.get('models').find(x=>x.id===id);
    UI.modal({ title:`实体 · ${m.display} (${m.name})`, size:'lg', footer:false, body:`
      <div class="btn-row" style="margin-bottom:10px">
        <button class="btn btn-p btn-sm" onclick="ModelM.addField('${id}')">＋ 字段</button>
        <button class="btn btn-sm" onclick="ModelM.genSchema('${id}')">生成 Prisma</button>
        <button class="btn btn-sm" onclick="UI.toast('视图定义器（GB 6.4.3 e）：筛选/排序/聚合字段配置（演示）')">数据视图</button>
        <button class="btn btn-sm btn-danger" onclick="ModelM.delTable('${id}')">删除实体</button>
      </div>
      <div class="tbl-wrap"><table class="tbl"><thead><tr><th>字段</th><th>类型</th><th>约束</th><th>说明</th><th></th></tr></thead><tbody>
      ${m.fields.map((f,i)=>`<tr><td><b>${f.name}</b></td><td class="mono">${f.type}${f.len?'('+f.len+')':''}</td>
        <td>${[f.pk?'PK':'',f.req?'NOT NULL':'',f.unique?'UNIQUE':'',f.ref?'FK→'+f.ref:'',f.encrypt?'🔒SM4':'',f.dict?'dict:'+f.dict:''].filter(Boolean).map(x=>`<span class="tag tag-gray">${x}</span>`).join(' ')}</td>
        <td class="muted">${f.pk?'主键':f.ref?'外键引用':'—'}</td>
        <td><a class="link" onclick="ModelM.delField('${id}',${i})">删</a></td></tr>`).join('')}
      </tbody></table></div>` });
  },
  addField(id) { const m = Store.get('models').find(x=>x.id===id);
    UI.modal({ title:'添加字段 · '+m.name, body:UI.drawerForm([
      {key:'name', label:'字段名', req:true},{key:'type', label:'类型', type:'select',
        options:['string','int','decimal','boolean','datetime','text','enum','json'].map(t=>({v:t,l:t}))},
      {key:'len', label:'长度/精度', ph:'64 或 10,2'},
      {key:'req', label:'必填 NOT NULL', type:'switch', value:true},
      {key:'unique', label:'唯一 UNIQUE', type:'switch'},
      {key:'encrypt', label:'国密加密(SM4)', type:'switch'},
      {key:'dict', label:'关联字典', type:'select', options:[{v:'',l:'—'},...Store.get('dicts').map(d=>({v:d.code,l:d.name}))]} ]),
    okText:'添加', onOk:()=>{ const f=UI.collectForm();
      m.fields.push({name:f.name, type:f.type, len:f.len, req:f.req==='on'||f.req===true,
        unique:f.unique==='on', encrypt:f.encrypt==='on', dict:f.dict||undefined});
      Store.save(); UI.closeModal(); ModelM.drawTables(); UI.toast('字段已添加'); }});
  },
  delField(id, i) { const m = Store.get('models').find(x=>x.id===id); m.fields.splice(i,1); Store.save(); this.drawTables(); this.editTable(id); },
  delTable(id) { UI.confirm('删除实体会级联删除其字段与关系定义，确认？', ()=>{ Store.remove('models', id);
    this.sel=null; this.drawTables(); this.drawRelations(); UI.toast('实体已删除'); }); },
  delRel(id) { Store.remove('relations', id); this.drawRelations(); UI.toast('关系已删除'); },

  genSchema(id) {
    const models = id ? [Store.get('models').find(m=>m.id===id)] : Store.get('models');
    let s = `datasource db {\n  provider = "postgresql"\n  url      = env("DATABASE_URL")\n}\n\ngenerator client {\n  provider = "prisma-client-js"\n}\n`;
    models.filter(Boolean).forEach(m => {
      s += `\nmodel ${m.name} {\n`;
      m.fields.forEach(f => { s += `  ${f.name.padEnd(14)} ${f.type==='decimal'?'Decimal':f.type==='datetime'?'DateTime':f.type==='int'?'Int':f.type==='json'?'Json':'String'}`;
        if (f.pk) s += '  @id'; if (f.unique) s += '  @unique'; if (f.req && !f.pk) s += '';
        if (!f.req && !f.pk) s += '?'; if (f.len) s += `  @db.VarChar(${f.len})`;
        s += '\n'; });
      s += `  @@map("${m.name.toLowerCase()}"\n}\n`.replace('"\n}','")\n}').replace(/\n}\n$/,'\n}\n');
    });
    UI.modal({ title:'Prisma Schema', size:'lg', footer:false, body:`
      <div class="code-tabs"><button class="btn btn-sm btn-p">prisma/schema.prisma</button>
        <button class="btn btn-sm" onclick="UI.toast('已复制到剪贴板')">📋 复制</button>
        <button class="btn btn-sm" onclick="UI.toast('已触发 prisma migrate dev（演示）')">▶ migrate dev</button></div>
      <div class="code-view"><pre>${UI.esc(s)}</pre></div>` });
  },
  genDDL() { UI.toast('SQL DDL 已生成（3 CREATE TABLE + 2 ALTER INDEX），已复制'); },
  importSQL() { UI.modal({ title:'从 SQL 逆向建模', body:`<textarea class="input mono" style="min-height:140px"
    placeholder="粘贴 CREATE TABLE 语句…">CREATE TABLE customer (id varchar(32) primary key, name varchar(64) not null, level varchar(8));</textarea>`,
    okText:'解析并创建', onOk:()=>{ UI.closeModal(); UI.toast('已解析出 1 实体 3 字段，已加入画布'); }});
  },
  aiGen() { UI.modal({ title:'🤖 AI 建模', size:'lg', footer:false, body:`
    <div class="form-item"><label>用自然语言描述业务</label>
      <textarea class="input" id="aiBiz">做一个售后工单系统：客户报修，工程师上门维修，配件领用，满意度回访</textarea></div>
    <button class="btn btn-p" onclick="ModelM.aiRun()">🤖 分析并生成</button><div id="aiModelOut" class="mt10"></div>` });
  },
  aiRun() { const out = document.getElementById('aiModelOut');
    out.innerHTML = `<div class="muted">🤖 分析中…</div>`;
    setTimeout(()=>{ out.innerHTML = `<div class="success">✨ 识别 4 个实体、3 条关系、2 个字典：</div>
      <div class="item">📘 <b>RepairTicket 报修单</b>：id🔑 / customer_id→Customer / device / fault_desc / status(dict:repair_status) / priority</div>
      <div class="item">📘 <b>EngineerVisit 上门单</b>：id🔑 / ticket_id→RepairTicket / engineer_id→Employee / visit_date / result</div>
      <div class="item">📘 <b>PartUsage 配件领用</b>：id🔑 / visit_id→EngineerVisit / part_code / qty / cost</div>
      <div class="item">📘 <b>Feedback 回访</b>：id🔑 / ticket_id→RepairTicket / score(1-5) / comment</div>
      <div class="item">📖 字典：repair_status(待派/处理中/已完成/已关闭)</div>
      <button class="btn btn-p" onclick="UI.toast('4 实体已加入 ER 画布');UI.closeModal();ModelM.drawTables()">加入画布</button>`; }, 900); },
};
