/* M04 local prototype: executable field rules and persisted preview submissions. */
(function(){
  const Form=App.mods.form;
  const esc=UI.esc;
  const RULES={
    required:{label:'必填',needsValue:false},
    positive:{label:'正数',needsValue:false},
    min:{label:'最小值',needsValue:true},
    max:{label:'最大值',needsValue:true},
    length:{label:'长度范围',needsValue:true},
    regex:{label:'正则表达式',needsValue:true}
  };
  const allRules=f=>{
    if(!Array.isArray(f.rules))f.rules=[];
    f.rules=f.rules.map(rule=>{
      if(typeof rule!=='string')return rule;
      const m=rule.match(/^([a-z]+)(?::(.*))?$/);
      return m?{id:'legacy_'+m[1]+'_'+(m[2]||''),type:m[1],value:m[2]||'',message:''}:{id:'legacy_unknown',type:'unsupported',value:rule,message:'未知的旧版规则'};
    });
    return f.rules;
  };
  const ruleLabel=r=>RULES[r.type]?.label||r.type;
  Form.addRule=function(){
    const field=Store.get('forms')[0].fields.find(x=>x.id===this.selField);
    if(!field)return UI.toast('请先选择字段','warn');
    const body=UI.drawerForm([
      {key:'type',label:'规则类型',type:'select',options:Object.entries(RULES).map(([v,r])=>({v,l:r.label}))},
      {key:'value',label:'参数（最小值/最大值/长度区间/正则）',type:'text'},
      {key:'message',label:'错误提示',type:'text'}
    ],{type:'required',message:'请检查此字段'});
    UI.modal({title:'添加校验规则 · '+field.label,body,okText:'保存规则',onOk:()=>{
      const v=UI.collectForm(),def=RULES[v.type];
      if(!def)return UI.toast('规则类型无效','err');
      if(def.needsValue&&!String(v.value||'').trim())return UI.toast('该规则需要填写参数','warn');
      if(v.type==='length'&&!/^\d+\s*-\s*\d+$/.test(v.value))return UI.toast('长度范围格式应为 min-max','warn');
      if(v.type==='regex'){try{new RegExp(v.value);}catch(e){return UI.toast('正则表达式无效','err');}}
      if(['min','max'].includes(v.type)&&!Number.isFinite(Number(v.value)))return UI.toast('请输入有效数字','err');
      allRules(field).push({id:'rule_'+Date.now(),type:v.type,value:v.value||'',message:v.message||def.label+'校验未通过'});
      Store.save();if(this.capture)this.capture();UI.closeModal();this.drawCanvas();UI.toast('校验规则已保存到本地表单');
    }});
  };
  Form.removeRule=function(ruleId){
    const field=Store.get('forms')[0].fields.find(x=>x.id===this.selField);if(!field)return;
    field.rules=allRules(field).filter(r=>r.id!==ruleId);Store.save();if(this.capture)this.capture();this.drawCanvas();
  };
  const baseProps=Form.renderProps;
  Form.renderProps=function(){
    baseProps.call(this);
    const field=Store.get('forms')[0].fields.find(x=>x.id===this.selField);
    const panel=document.getElementById('fieldProps');if(!field||!panel)return;
    const rules=allRules(field);
    const section=document.createElement('section');section.className='form-item';
    section.innerHTML='<label>可执行校验规则</label><div class="rule-list">'+
      (rules.length?rules.map(r=>'<div class="item flex"><span class="tag tag-blue">'+esc(ruleLabel(r))+'</span><span class="muted">'+esc(r.value||r.message||'')+'</span><button class="btn btn-sm btn-danger" data-remove-rule="'+esc(r.id||'')+'">移除</button></div>').join(''):'<div class="muted">暂无规则</div>')+
      '</div><button type="button" class="btn btn-sm mt10" id="addFormRule">＋ 添加校验规则</button>';
    panel.appendChild(section);
    const dictionaries=Store.get('dicts')||[];
    const dictSection=document.createElement('section');dictSection.className='form-item';
    dictSection.innerHTML='<label>选项数据字典（本地）</label><select class="input" id="formDictionaryRef"><option value="">不绑定字典</option>'+dictionaries.map(d=>'<option value="'+esc(d.code)+'" '+(field.dictCode===d.code?'selected':'')+'>'+esc(d.name)+' · '+esc(d.code)+'</option>').join('')+'</select><div class="help">仅对下拉、单选、复选组件生效；引用当前浏览器字典数据。</div>';
    panel.appendChild(dictSection);
    dictSection.querySelector('#formDictionaryRef').addEventListener('change',event=>{
      field.dictCode=event.target.value||undefined;Store.save();if(this.capture)this.capture();UI.toast('字典引用已保存到本地表单');
    });
    section.querySelector('#addFormRule').addEventListener('click',()=>this.addRule());
    section.querySelectorAll('[data-remove-rule]').forEach(b=>b.addEventListener('click',()=>this.removeRule(b.dataset.removeRule)));
  };
  Form.evaluateRule=function(rule,value){
    const v=value==null?'':String(value);
    switch(rule.type){
      case 'required':return v.trim()!=='';
      case 'positive':return v.trim()===''||Number.isFinite(Number(v))&&Number(v)>0;
      case 'min':return v.trim()===''||Number(v)>=Number(rule.value);
      case 'max':return v.trim()===''||Number(v)<=Number(rule.value);
      case 'length':{const m=String(rule.value).match(/^(\d+)\s*-\s*(\d+)$/);return !!m&&v.length>=Number(m[1])&&v.length<=Number(m[2]);}
      case 'regex':try{return v===''||new RegExp(rule.value).test(v);}catch(e){return false;}
      default:return false;
    }
  };
  Form.validateValues=function(form,values){
    const errors=[];
    (form.fields||[]).forEach(field=>{
      const value=values[field.field];
      if(field.req&&!this.evaluateRule({type:'required'},value))errors.push({field:field.field,message:field.label+'为必填项'});
      allRules(field).forEach(rule=>{
        if(!this.evaluateRule(rule,value))errors.push({field:field.field,message:rule.message||field.label+': '+ruleLabel(rule)+'校验未通过'});
      });
      if(field.showIf&&!this.evaluateVisibility(field.showIf,values))return;
    });
    return errors;
  };
  Form.evaluateVisibility=function(expression,values){
    const m=String(expression||'').trim().match(/^([A-Za-z_][A-Za-z0-9_]*)\s*(>=|<=|==|!=|>|<)\s*(-?\d+(?:\.\d+)?|'[^'\\]*'|"[^"\\]*")$/);
    if(!m)return false;
    const actual=values[m[1]],raw=m[3].replace(/^['"]|['"]$/g,'');
    if(actual===undefined)return false;
    const a=Number(actual),b=Number(raw),numeric=String(actual).trim()!==''&&Number.isFinite(a)&&Number.isFinite(b);
    const left=numeric?a:String(actual),right=numeric?b:raw;
    switch(m[2]){case'>':return left>right;case'<':return left<right;case'>=':return left>=right;case'<=':return left<=right;case'==':return left==right;case'!=':return left!=right;default:return false;}
  };
  Form.openSubmissionPreview=function(){
    const form=Store.get('forms')[0];if(!form)return UI.toast('没有可预览的表单','err');
    const fields=form.fields.filter(f=>!['line','divider','text-view','line-chart','bar-chart','image-banner','video'].includes(f.type));
    const controls=fields.map(f=>{
      const required=f.req?' <span class="req">*</span>':'';
      let input='';
      const dict=(Store.get('dicts')||[]).find(d=>d.code===f.dictCode);
      const flatten=(items,prefix='')=>(items||[]).flatMap(item=>{
        const label=prefix+item.zh;
        return [{v:item.v,label}].concat(flatten(item.children||[],label+' / '));
      });
      const options=dict?flatten(dict.items):[];
      if(f.type==='textarea')input='<textarea class="input" data-submit-field="'+esc(f.field)+'"></textarea>';
      else if(f.type==='select')input=options.length?'<select class="input" data-submit-field="'+esc(f.field)+'"><option value="">请选择</option>'+options.map(o=>'<option value="'+esc(o.v)+'">'+esc(o.label)+'</option>').join('')+'</select>':'<input class="input" data-submit-field="'+esc(f.field)+'" placeholder="未绑定字典，请输入选项值">';
      else if(f.type==='radio')input=options.length?'<div class="btn-row wrap">'+options.map(o=>'<label class="item"><input type="radio" name="radio_'+esc(f.field)+'" data-submit-field="'+esc(f.field)+'" value="'+esc(o.v)+'"> '+esc(o.label)+'</label>').join('')+'</div>':'<input class="input" data-submit-field="'+esc(f.field)+'" placeholder="未绑定字典，请输入选项值">';
      else if(f.type==='checkbox')input=options.length?'<div class="btn-row wrap">'+options.map(o=>'<label class="item"><input type="checkbox" data-submit-field="'+esc(f.field)+'" value="'+esc(o.v)+'"> '+esc(o.label)+'</label>').join('')+'</div>':'<input class="input" data-submit-field="'+esc(f.field)+'" placeholder="未绑定字典，请输入选项值">';
      else if(f.type==='switch')input='<select class="input" data-submit-field="'+esc(f.field)+'"><option value="">请选择</option><option value="true">是</option><option value="false">否</option></select>';
      else input='<input class="input" type="'+(f.type==='number'?'number':f.type==='date'?'date':f.type==='datetime'?'datetime-local':'text')+'" data-submit-field="'+esc(f.field)+'">';
      return '<div class="form-item" data-preview-row="'+esc(f.field)+'"><label>'+esc(f.label)+required+'</label>'+input+'</div>';
    }).join('');
    const body='<div class="device-frame"><div style="padding:20px"><h3>'+esc(form.name)+'</h3><p class="muted">表单版本：'+esc(String(form.revision||1))+' · LOCAL DEMO</p>'+controls+
      '<div id="formValidationErrors" class="alert alert-error" hidden></div><div class="btn-row"><button class="btn btn-p" id="submitLocalForm">本地模拟提交</button><button class="btn" id="saveDraftForm">暂存草稿</button></div></div></div>';
    UI.modal({title:'表单预览与提交',size:'lg',footer:false,body});
    const submit=async status=>{
      const values={};
      fields.forEach(f=>{
        const controls=[...document.querySelectorAll('[data-submit-field="'+CSS.escape(f.field)+'"]')];
        if(f.type==='checkbox')values[f.field]=controls.filter(el=>el.checked).map(el=>el.value);
        else if(f.type==='radio')values[f.field]=controls.find(el=>el.checked)?.value||'';
        else values[f.field]=controls[0]?.value??'';
      });
      const visible={};fields.forEach(f=>visible[f.field]=!f.showIf||this.evaluateVisibility(f.showIf,values));
      const errors=this.validateValues(form,values).filter(e=>visible[e.field]!==false);
      const box=document.getElementById('formValidationErrors');
      if(errors.length){box.hidden=false;box.innerHTML='<b>请修正以下问题：</b><ul>'+errors.map(e=>'<li>'+esc(e.message)+'</li>').join('')+'</ul>';return;}
      const rows=Store.data.formSubmissions||(Store.data.formSubmissions=[]);
      const record={id:'submission_'+Date.now(),formId:form.id,formRevision:form.revision||1,payload:values,status,submittedAt:new Date().toISOString(),source:'LOCAL DEMO'};
      rows.unshift(record);Store.save();
      box.hidden=false;box.className='alert alert-success';box.textContent=(status==='submitted'?'本地模拟提交成功':'草稿已暂存')+'；记录 ID：'+record.id+'。数据仅保存在当前浏览器。';
      document.getElementById('submitLocalForm').disabled=true;document.getElementById('saveDraftForm').disabled=true;
      UI.toast(status==='submitted'?'本地模拟提交已保存':'本地草稿已保存');
    };
    document.getElementById('submitLocalForm').addEventListener('click',()=>submit('submitted'));
    document.getElementById('saveDraftForm').addEventListener('click',()=>submit('draft'));
  };
  // Keep the original design preview intact; expose executable local preview separately.

  Form.validateModelReferences=function(form,spec){
    const errors=[],models=spec?.dataModels||[];
    const model=form.modelRef?models.find(m=>m.id===form.modelRef||m.name===form.modelRef):null;
    if(form.modelRef&&!model)errors.push({path:'modelRef',message:'引用的数据模型不存在'});
    const keys=new Set();
    (form.fields||[]).forEach((field,index)=>{
      const path='fields['+index+']';
      if(!field.field||typeof field.field!=='string'){errors.push({path:path+'.field',message:'字段 key 不能为空'});return;}
      if(keys.has(field.field))errors.push({path:path+'.field',message:'表单字段 key 重复'});
      keys.add(field.field);
      const candidates=model?[model]:models;
      const matches=candidates.flatMap(m=>(m.fields||[]).filter(f=>f.name===field.field).map(f=>({model:m,field:f})));
      if(!matches.length)errors.push({path:path+'.field',message:'找不到匹配的数据模型字段：'+field.field});
      if(matches.length>1)errors.push({path:path+'.field',message:'字段名在多个数据模型中重复，必须指定唯一模型引用'});
      if(matches.length===1){
        const type=String(matches[0].field.type||'').toLowerCase();
        const component=String(field.type||'text').toLowerCase();
        const numeric=['int','integer','decimal','float'].includes(type);
        if(component==='number'&&!numeric)errors.push({path:path+'.type',message:'数字控件与模型字段类型不兼容'});
        if(['date','datetime'].includes(component)&&!['date','datetime','time','string'].includes(type))errors.push({path:path+'.type',message:'日期控件与模型字段类型不兼容'});
        if(['select','radio','checkbox'].includes(component)&&!['string','text','int','integer','enum'].includes(type))errors.push({path:path+'.type',message:'选项控件与模型字段类型不兼容'});
      }
    });
    return errors;
  };
  Form.validateAndSave=function(){
    const form=Store.get('forms')[0];if(!form)return UI.toast('没有可保存的表单','err');
    const specs=Store.get('appSpecs')||[];
    const spec=specs.find(s=>s.meta?.appId===form.appId);
    if(!spec)return UI.toast('未找到该应用的 AppSpec；为避免旁路保存，已阻止提交','warn');
    const errors=this.validateModelReferences(form,spec);
    const hasDictionaryRef=(form.fields||[]).some(field=>field.dictCode);
    if(hasDictionaryRef&&spec.schemaVersion!=='1.1.0')errors.push({path:'schemaVersion',message:'表单绑定了数据字典，必须先将 AppSpec 迁移到 1.1.0'});
    if(errors.length)return UI.modal({title:'表单模型引用校验失败',footer:false,body:'<div class="alert alert-error"><ul>'+errors.map(e=>'<li>'+esc(e.path)+': '+esc(e.message)+'</li>').join('')+'</ul></div>'});
    const specForm={id:form.id,appId:form.appId,name:form.name,fields:form.fields.map(f=>{
      const dictionary=f.dictCode?(Store.get('dicts')||[]).find(d=>d.code===f.dictCode):null;
      return {id:f.id,label:f.label,field:f.field,type:f.type,req:!!f.req,span:f.span,rules:f.rules||[],
        ...(dictionary?{dictionaryRef:{dictionaryId:dictionary.id,version:1}}:{})};
    })};
    const next=JSON.parse(JSON.stringify(spec));
    if(next.schemaVersion==='1.1.0'){
      const normalizeItems=items=>(items||[]).map(item=>({value:item.v,labels:{'zh-CN':item.zh||item.en||String(item.v),'en-US':item.en||item.zh||String(item.v)},...(item.children?{children:normalizeItems(item.children)}:{})}));
      next.dictionaries=(Store.get('dicts')||[]).map(d=>({id:d.id,code:d.code,name:d.name,version:1,type:d.type==='tree'?'tree':'list',items:normalizeItems(d.items)}));
    }
    next.forms=next.forms||[];
    const index=next.forms.findIndex(f=>f.id===form.id);
    if(index>=0)next.forms[index]=specForm;else next.forms.push(specForm);
    const result=AppSpec.validate(next);
    if(!result.valid)return UI.modal({title:'AppSpec 校验失败',footer:false,body:'<div class="alert alert-error"><ul>'+result.errors.map(e=>'<li>'+esc(e.path)+': '+esc(e.message)+'</li>').join('')+'</ul></div>'});
    const stored=specs.findIndex(s=>s.meta?.appId===next.meta.appId);
    specs[stored]=next;Store.save();UI.toast('表单已通过本地 AppSpec 引用校验并写入 AppSpec');
  };
  Form.previewRuntime=function(){this.openSubmissionPreview();};
})();
