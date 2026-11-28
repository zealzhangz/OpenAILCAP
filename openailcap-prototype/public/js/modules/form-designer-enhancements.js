/* Form designer behavior enhancements. Existing component catalogue and field metadata remain intact. */
const FormEnhance = App.mods.form;
FormEnhance._history = FormEnhance._history || [];
FormEnhance._historyIndex = FormEnhance._historyIndex ?? -1;
FormEnhance._historyFormId = null;
FormEnhance.ensureHistory = function() {
  const f=Store.get('forms')[0]; if(!f)return;
  if(this._historyFormId!==f.id){this._history=[];this._historyIndex=-1;this._historyFormId=f.id;this.capture();}
};
FormEnhance.capture = function() {
  const f=Store.get('forms')[0];if(!f)return;
  const snap=JSON.stringify(f);
  if(this._history[this._historyIndex]===snap)return;
  this._history=this._history.slice(0,this._historyIndex+1);
  this._history.push(snap);
  if(this._history.length>50)this._history.shift();
  this._historyIndex=this._history.length-1;
};
const formBaseMount=FormEnhance.mount;
FormEnhance.mount=function(){this.ensureHistory();formBaseMount.call(this);};
const formBaseDrop=FormEnhance.drop;
FormEnhance.drop=function(ev,type){this.ensureHistory();this.capture();formBaseDrop.call(this,ev,type);this.capture();};
const formBaseDelete=FormEnhance.delField;
FormEnhance.delField=function(id){this.ensureHistory();this.capture();formBaseDelete.call(this,id);this.capture();};
const formBaseUp=FormEnhance.up;
FormEnhance.up=function(k,v){this.ensureHistory();this.capture();formBaseUp.call(this,k,v);this.capture();};
FormEnhance.undo=function(){
  this.ensureHistory();if(this._historyIndex<=0)return UI.toast('没有可撤销的操作','info');
  this._historyIndex--;Store.data.forms[0]=JSON.parse(this._history[this._historyIndex]);Store.save();this.drawCanvas();UI.toast('已撤销');
};
FormEnhance.redo=function(){
  this.ensureHistory();if(this._historyIndex>=this._history.length-1)return UI.toast('没有可重做的操作','info');
  this._historyIndex++;Store.data.forms[0]=JSON.parse(this._history[this._historyIndex]);Store.save();this.drawCanvas();UI.toast('已重做');
};
FormEnhance.save=function(){
  const f=Store.get('forms')[0];f.updatedAt=new Date().toISOString();f.revision=(f.revision||0)+1;
  Store.save();this.capture();UI.toast('表单已保存 · 修订版 '+f.revision);
};
FormEnhance.setLayout=function(value){
  this.layout=value;const f=Store.get('forms')[0];f.layout=value;Store.save();this.drawCanvas();UI.toast('布局已切换：'+value);
};
const formBaseDraw=FormEnhance.drawCanvas;
FormEnhance.drawCanvas=function(){
  formBaseDraw.call(this);
  const grid=document.getElementById('cvFields');if(!grid)return;
  const layout=this.layout||Store.get('forms')[0].layout||'栅格布局';
  grid.dataset.layout=layout;
  if(layout==='表格布局'){
    grid.style.gridTemplateColumns='1fr';
    grid.querySelectorAll('.cv-field').forEach(el=>el.style.gridColumn='span 24');
  }else{
    grid.style.gridTemplateColumns='repeat(24,minmax(0,1fr))';
    grid.querySelectorAll('.cv-field').forEach((el,i)=>{const f=Store.get('forms')[0].fields[i];el.style.gridColumn='span '+(layout==='自由布局'?(f.span||12):(f.span||12));});
  }
};
FormEnhance.aiFields=function(){
  const candidates=[
    ['收货地址','text','收货地址/安装地点'],['配送方式','select','物流/服务方式'],
    ['优惠券码','text','优惠或费用代码'],['紧急程度','radio','工单/审批优先级'],
    ['业务负责人','user','责任人选择']
  ];
  const body=candidates.map((x,i)=>'<label class="item flex"><input type="checkbox" data-ai-field="'+i+'" checked><b>'+x[0]+'</b><span class="tag tag-gray">'+x[1]+'</span><span class="muted" style="margin-left:auto">'+x[2]+'</span></label>').join('');
  UI.modal({title:'AI 字段建议（可选择采纳项）',size:'lg',body:'<p class="muted">根据当前表单字段与业务上下文给出建议。请勾选需要添加的字段。</p>'+body,okText:'添加所选字段',onOk:()=>{
    const selected=[...document.querySelectorAll('[data-ai-field]:checked')].map(el=>candidates[Number(el.dataset.aiField)]);
    if(!selected.length)return UI.toast('请至少选择一个字段','warn');
    const f=Store.get('forms')[0],existing=new Set(f.fields.map(x=>x.label));
    selected.filter(x=>!existing.has(x[0])).forEach(x=>f.fields.push({id:'ai_'+Date.now()+'_'+f.fields.length,label:x[0],field:'ai_'+f.fields.length,type:x[1],req:false,span:12,ai:true}));
    Store.save();this.capture();UI.closeModal();this.drawCanvas();UI.toast('已添加 '+selected.length+' 项所选字段建议');
  }});
};
