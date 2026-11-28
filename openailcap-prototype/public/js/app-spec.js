/* AppSpec 1.0.0 structural and cross-reference validator.
 * Runtime validation is deterministic and side-effect free. Server/compiler validation
 * must additionally run the canonical JSON Schema validator and domain-specific checks.
 */
const AppSpec = {
  VERSION:'1.0.0',
  validate(spec) {
    const errors=[];
    const need=(condition,path,message)=>{if(!condition)errors.push({path,message});};
    need(!!spec&&typeof spec==='object'&&!Array.isArray(spec),'$','must be an object');
    if(!spec||typeof spec!=='object'||Array.isArray(spec))return {valid:false,errors};
    need(spec.schemaVersion===this.VERSION,'schemaVersion','unsupported AppSpec version');
    for(const key of ['meta','dataModels','relations','ui','forms','logic','workflows','security','i18n','deployment'])
      need(Object.prototype.hasOwnProperty.call(spec,key),'$.'+key,'required property is missing');
    need(typeof spec.meta?.appId==='string'&&!!spec.meta.appId,'meta.appId','must be a non-empty string');
    need(typeof spec.meta?.name==='string'&&!!spec.meta.name,'meta.name','must be a non-empty string');
    for(const key of ['ui','security','i18n','deployment'])need(!!spec[key]&&typeof spec[key]==='object'&&!Array.isArray(spec[key]),key,'must be an object');
    for(const key of ['dataModels','relations','forms','logic','workflows'])
      need(Array.isArray(spec[key]),key,'must be an array');
    if(errors.length)return {valid:false,errors};
    const models=spec.dataModels,forms=spec.forms;
    const modelIds=new Set(),formIds=new Set();
    models.forEach((m,i)=>{
      if(!m||typeof m!=='object'||Array.isArray(m)){need(false,'dataModels['+i+']','must be an object');return;}
      need(typeof m.id==='string'&&!!m.id,'dataModels['+i+'].id','must be a non-empty string');
      need(!modelIds.has(m.id),'dataModels['+i+'].id','duplicate model id');
      modelIds.add(m.id);
      need(m.appId===undefined||m.appId===spec.meta.appId,'dataModels['+i+'].appId','must match meta.appId');
      need(Array.isArray(m.fields),'dataModels['+i+'].fields','must be an array');
      const names=new Set();
      (m.fields||[]).forEach((f,j)=>{
        need(typeof f.name==='string'&&!!f.name,'dataModels['+i+'].fields['+j+'].name','must be a non-empty string');
        need(!names.has(f.name),'dataModels['+i+'].fields['+j+'].name','duplicate field name');
        names.add(f.name);
      });
      need((m.fields||[]).filter(f=>f.pk).length<=1,'dataModels['+i+'].fields','at most one primary key is supported by this model version');
    });
    forms.forEach((f,i)=>{
      if(!f||typeof f!=='object'||Array.isArray(f)){need(false,'forms['+i+']','must be an object');return;}
      need(typeof f.id==='string'&&!!f.id,'forms['+i+'].id','must be a non-empty string');
      need(!formIds.has(f.id),'forms['+i+'].id','duplicate form id');
      formIds.add(f.id);
      need(f.appId===undefined||f.appId===spec.meta.appId,'forms['+i+'].appId','must match meta.appId');
      need(Array.isArray(f.fields),'forms['+i+'].fields','must be an array');
      (f.fields||[]).forEach((field,j)=>{
        const exists=models.some(m=>(m.fields||[]).some(x=>x.name===field.field));
        need(exists,'forms['+i+'].fields['+j+'].field','field must exist in an AppSpec data model');
      });
    });
    (spec.ui.pages||[]).forEach((p,i)=>{
      if(p.formId)need(formIds.has(p.formId),'ui.pages['+i+'].formId','references an unknown form');
    });
    spec.relations.forEach((r,i)=>{
      if(!r||typeof r!=='object'||Array.isArray(r)){need(false,'relations['+i+']','must be an object');return;}
      const from=models.find(m=>m.id===r.from),to=models.find(m=>m.id===r.to);
      need(!!from,'relations['+i+'].from','references an unknown model');
      need(!!to,'relations['+i+'].to','references an unknown model');
      if(from)need((from.fields||[]).some(f=>f.name===r.f),'relations['+i+'].f','references an unknown source field');
      if(to)need((to.fields||[]).some(f=>f.name===r.t),'relations['+i+'].t','references an unknown target field');
    });
    for(const group of ['logic','workflows'])spec[group].forEach((graph,i)=>{
      if(!graph||typeof graph!=='object'||Array.isArray(graph)){need(false,group+'['+i+']','must be an object');return;}
      const ids=new Set((graph.nodes||[]).map(n=>n.id));
      need(Array.isArray(graph.nodes),group+'['+i+'].nodes','must be an array');
      need(Array.isArray(graph.edges),group+'['+i+'].edges','must be an array');
      (graph.edges||[]).forEach((edge,j)=>{
        need(ids.has(edge.f),group+'['+i+'].edges['+j+'].f','references an unknown source node');
        need(ids.has(edge.t),group+'['+i+'].edges['+j+'].t','references an unknown target node');
      });
    });
    need(Array.isArray(spec.security?.roles),'security.roles','must be an array');
    need(Array.isArray(spec.i18n?.locales)&&spec.i18n.locales.length>0,'i18n.locales','must contain at least one locale');
    need(Array.isArray(spec.deployment?.environments),'deployment.environments','must be an array');
    return {valid:errors.length===0,errors};
  },
  assert(spec) {
    const result=this.validate(spec);
    if(!result.valid)throw new Error('Invalid AppSpec: '+result.errors.map(e=>e.path+' '+e.message).join('; '));
    return spec;
  }
};
