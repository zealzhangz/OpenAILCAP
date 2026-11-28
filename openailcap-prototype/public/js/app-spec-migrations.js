/* Explicit, non-destructive AppSpec migrations. Preview only: callers must obtain user approval before persistence. */
(function(root){
  const clone=value=>JSON.parse(JSON.stringify(value));
  const fail=(errors,path,message)=>errors.push({path,message});
  const normalizeItems=(items,path,errors)=>{
    if(!Array.isArray(items)){fail(errors,path,'dictionary items must be an array');return [];}
    return items.map((item,index)=>{
      const p=path+'['+index+']';
      if(!item||typeof item!=='object'){fail(errors,p,'dictionary item must be an object');return null;}
      const value=item.v!==undefined?item.v:item.value;
      if(!['string','number'].includes(typeof value))fail(errors,p+'.value','dictionary item requires a string or number value');
      const labels={};
      const zh=item.zh??item.labels?.['zh-CN'];
      const en=item.en??item.labels?.['en-US'];
      if(typeof zh==='string'&&zh)labels['zh-CN']=zh;
      if(typeof en==='string'&&en)labels['en-US']=en;
      if(!Object.keys(labels).length)fail(errors,p+'.labels','dictionary item requires at least one non-empty zh/en label');
      const result={value,labels};
      if(item.children!==undefined)result.children=normalizeItems(item.children,p+'.children',errors);
      return result;
    }).filter(Boolean);
  };
  function preview(spec,options={}){
    const errors=[],warnings=[],changedPaths=[];
    if(!spec||typeof spec!=='object'||Array.isArray(spec)){fail(errors,'$','AppSpec must be an object');return {ok:false,errors,warnings,changedPaths};}
    if(spec.schemaVersion==='1.1.0')return {ok:true,sourceVersion:'1.1.0',targetVersion:'1.1.0',migrated:clone(spec),errors,warnings,changedPaths};
    if(spec.schemaVersion!=='1.0.0'){fail(errors,'schemaVersion','only AppSpec 1.0.0 can be migrated to 1.1.0');return {ok:false,errors,warnings,changedPaths};}
    const next=clone(spec),sourceDictionaries=options.dictionaries||[];
    if(!Array.isArray(sourceDictionaries))fail(errors,'dictionaries','migration dictionary source must be an array');
    const byCode=new Map(),ids=new Set(),codes=new Set();
    const dictionaries=(Array.isArray(sourceDictionaries)?sourceDictionaries:[]).map((d,i)=>{
      const p='sourceDictionaries['+i+']';
      if(!d||typeof d!=='object'){fail(errors,p,'dictionary must be an object');return null;}
      if(typeof d.code!=='string'||!d.code.trim())fail(errors,p+'.code','dictionary code is required');
      if(typeof d.id!=='string'||!d.id.trim())fail(errors,p+'.id','stable dictionary id is required');
      if(ids.has(d.id))fail(errors,p+'.id','duplicate dictionary id');
      if(codes.has(d.code))fail(errors,p+'.code','duplicate dictionary code');
      ids.add(d.id);codes.add(d.code);
      if(!['list','tree'].includes(d.type))fail(errors,p+'.type','dictionary type must be list or tree');
      if(d.type==='list'&&(d.items||[]).some(item=>item?.children?.length))fail(errors,p+'.items','list dictionary cannot contain child items');
      const normalized={id:d.id,code:d.code,name:typeof d.name==='string'&&d.name.trim()?d.name:d.code,version:Number.isInteger(d.version)&&d.version>0?d.version:1,type:d.type,items:normalizeItems(d.items,p+'.items',errors)};
      byCode.set(d.code,normalized);
      return normalized;
    }).filter(Boolean);
    const seenFormIds=new Set();
    (next.forms||[]).forEach((form,i)=>{
      const fp='forms['+i+']';
      if(!form||typeof form!=='object'){fail(errors,fp,'form must be an object');return;}
      if(!form.id||seenFormIds.has(form.id))fail(errors,fp+'.id','form id must be present and unique');
      seenFormIds.add(form.id);
      if(form.modelRef){
        const model=(next.dataModels||[]).find(m=>m.id===form.modelRef);
        if(!model)fail(errors,fp+'.modelRef','references an unknown data model');
        const fieldNames=new Set();
        (form.fields||[]).forEach((field,j)=>{
          const p=fp+'.fields['+j+']';
          if(field.dictFrom!==undefined||field.dictionarySource!==undefined)fail(errors,p,'external dictionary source cannot be migrated automatically');
          if(field.dictionaryRef)fail(errors,p+'.dictionaryRef','1.0.0 field unexpectedly contains dictionaryRef; manual review required');
          if(field.dictCode){
            const dictionary=byCode.get(field.dictCode);
            if(!dictionary)fail(errors,p+'.dictCode','no unique local dictionary matches code '+field.dictCode);
            else {field.dictionaryRef={dictionaryId:dictionary.id,version:dictionary.version};changedPaths.push(p+'.dictionaryRef');}
            delete field.dictCode;
            changedPaths.push(p+'.dictCode');
          }
          if(field.field){
            if(fieldNames.has(field.field))fail(errors,p+'.field','duplicate form field key');
            fieldNames.add(field.field);
            if(!model) return;
            if(!(model.fields||[]).some(mf=>mf.name===field.field))fail(errors,p+'.field','does not exist in the form model '+form.modelRef);
          }
        });
      }else{
        (form.fields||[]).forEach((field,j)=>{
          const p=fp+'.fields['+j+']';
          if(field.dictFrom!==undefined||field.dictionarySource!==undefined)fail(errors,p,'external dictionary source cannot be migrated automatically');
          if(field.dictCode){
            const dictionary=byCode.get(field.dictCode);
            if(!dictionary)fail(errors,p+'.dictCode','no unique local dictionary matches code '+field.dictCode);
            else {field.dictionaryRef={dictionaryId:dictionary.id,version:dictionary.version};changedPaths.push(p+'.dictionaryRef');}
            delete field.dictCode;changedPaths.push(p+'.dictCode');
          }
        });
      }
    });
    next.schemaVersion='1.1.0';next.dictionaries=dictionaries;changedPaths.push('schemaVersion','dictionaries');
    if(errors.length)return {ok:false,sourceVersion:'1.0.0',targetVersion:'1.1.0',errors,warnings,changedPaths};
    const validator=options.validate||(root.AppSpec&&root.AppSpec.validate&&root.AppSpec.validate.bind(root.AppSpec));
    if(typeof validator!=='function')fail(errors,'$','AppSpec validator is unavailable; migration preview cannot be approved');
    else {
      const result=validator(next);
      if(!result?.valid)(result?.errors||[{path:'$',message:'AppSpec validation failed'}]).forEach(e=>fail(errors,e.path||'$',e.message||'AppSpec validation failed'));
    }
    return {ok:errors.length===0,sourceVersion:'1.0.0',targetVersion:'1.1.0',migrated:errors.length?undefined:next,errors,warnings,changedPaths};
  }
  root.AppSpecMigrations={preview};
})(typeof window!=='undefined'?window:globalThis);
