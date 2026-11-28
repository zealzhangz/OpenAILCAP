/* ============ UI — shared components: modal / toast / table / helpers ============ */
const UI = {
  toast(msg, type='ok') {
    const el = document.createElement('div');
    el.className = 'toast ' + (type==='ok'?'':type);
    el.innerHTML = (type==='ok'?'✅ ':type==='warn'?'⚠️ ':type==='err'?'❌ ':'ℹ️ ') + msg;
    document.getElementById('toasts').appendChild(el);
    setTimeout(()=>{ el.style.opacity='0'; el.style.transition='.3s'; setTimeout(()=>el.remove(), 320); }, 2600);
  },
  modal(opts) {
    const mask = document.getElementById('modalMask'), box = document.getElementById('modalBox');
    box.className = 'modal ' + (opts.size ? 'w-'+opts.size : '');
    box.innerHTML = `
      <div class="modal-h">${opts.icon||''} ${opts.title}<span class="x" onclick="UI.closeModal()">✕</span></div>
      <div class="modal-b" id="modalBody">${opts.body||''}</div>
      ${opts.footer === false ? '' : `<div class="modal-f">
        <button class="btn" onclick="UI.closeModal()">${I18N.t('common.cancel')}</button>
        <button class="btn btn-p" id="modalOk">${opts.okText||I18N.t('common.confirm')}</button>
      </div>`}`;
    mask.classList.add('open');
    if (opts.onOpen) opts.onOpen();
    if (opts.onOk) document.getElementById('modalOk').onclick = () => opts.onOk();
    mask.onclick = (e) => { if (e.target === mask) UI.closeModal(); };
  },
  closeModal() { document.getElementById('modalMask').classList.remove('open'); },
  confirm(msg, onOk, danger=true) {
    UI.modal({ title: danger?'危险操作确认':'操作确认', icon: danger?'⚠️':'❓', size:'',
      body: `<p style="font-size:13px;line-height:1.7">${msg}</p>`,
      okText: danger?'确认删除':I18N.t('common.confirm'), onOk: () => { UI.closeModal(); onOk(); } });
  },
  closeSearch() { document.getElementById('searchMask').classList.remove('open'); },
  /* simple table renderer */
  table({ cols, rows, rowKey='id', actions, empty='暂无数据', page=true }) {
    if (!rows.length) return `<div class="empty"><div class="big">📭</div>${empty}</div>`;
    const head = `<tr>${cols.map(c=>`<th>${c.label}</th>`).join('')}<th style="width:130px">${I18N.t('common.actions')}</th></tr>`;
    const body = rows.map(r => `<tr>${cols.map(c=>`<td>${c.render?c.render(r):r[c.key]??'—'}</td>`).join('')}
      <td><div class="actions">${actions?actions(r):''}</div></td></tr>`).join('');
    return `<div class="tbl-wrap"><table class="tbl"><thead>${head}</thead><tbody>${body}</tbody></table></div>`;
  },
  statusTag(s) {
    const map = { published:['tag-green','已发布'], draft:['tag-orange','草稿'], archived:['tag-gray','已归档'],
      running:['tag-blue','运行中'], done:['tag-green','已完成'], pending:['tag-orange','待处理'],
      overdue:['tag-red','已超期'], success:['tag-green','成功'], failed:['tag-red','失败'],
      on:['tag-green','启用'], off:['tag-gray','停用'], firing:['tag-red','触发中'], ack:['tag-orange','已确认'], resolved:['tag-gray','已恢复'],
      ok:['tag-green','正常'], error:['tag-red','异常'], forwarded:['tag-blue','已转办'], suspended:['tag-orange','已挂起'] };
    const m = map[s] || ['tag-gray', s];
    return `<span class="tag ${m[0]}">${m[1]}</span>`;
  },
  priTag(p) { const m = {high:['tag-red','高'], mid:['tag-orange','中'], low:['tag-blue','低']}; const x=m[p]||['tag-gray',p]; return `<span class="tag ${x[0]}">${x[1]}</span>`; },
  esc(s) { return String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); },
  bindSwitch(sel, onChange) {
    document.querySelectorAll(sel).forEach(el => el.onclick = () => {
      el.classList.toggle('on');
      if (onChange) onChange(el.dataset.id, el.classList.contains('on'));
    });
  },
  drawerForm(fields, values={}) {
    return fields.map(f => {
      if (f.type==='hidden') return '';
      const v = values[f.key] ?? f.value ?? '';
      const req = f.req ? '<span class="req">*</span>' : '';
      let ctrl = '';
      if (f.type==='textarea') ctrl = `<textarea class="input" data-fk="${f.key}">${UI.esc(v)}</textarea>`;
      else if (f.type==='select') ctrl = `<select class="input" data-fk="${f.key}">${f.options.map(o=>`<option value="${o.v}" ${o.v===v?'selected':''}>${o.l}</option>`).join('')}</select>`;
      else if (f.type==='switch') ctrl = `<div class="switch ${v?'on':''}" data-fk="${f.key}" onclick="this.classList.toggle('on')"></div>`;
      else ctrl = `<input class="input" data-fk="${f.key}" type="${f.type||'text'}" value="${UI.esc(v)}" placeholder="${f.ph||''}">`;
      return `<div class="form-item"><label>${f.label}${req}</label>${ctrl}${f.help?`<div class="help">${f.help}</div>`:''}</div>`;
    }).join('');
  },
  collectForm() {
    const out = {};
    document.querySelectorAll('#modalBody [data-fk]').forEach(el => {
      if (el.classList.contains('switch')) out[el.dataset.fk] = el.classList.contains('on');
      else out[el.dataset.fk] = el.value;
    });
    return out;
  },
  kvGrid(pairs) { return `<div class="kv">${pairs.map(([k,v])=>`<div class="k">${k}</div><div class="v">${v}</div>`).join('')}</div>`; },
};
