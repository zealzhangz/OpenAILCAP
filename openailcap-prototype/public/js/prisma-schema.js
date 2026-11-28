/* Deterministic Prisma schema generator for the local prototype. No database side effects. */
(function(root){
  const IDENT=/^[A-Za-z][A-Za-z0-9_]*$/;
  const TYPE_MAP={
    string:{type:'String',native:n=>n?('@db.VarChar('+n+')'):''},
    text:{type:'String',native:()=> '@db.Text'},
    int:{type:'Int',native:()=>''},
    decimal:{type:'Decimal',native:n=>{if(!n)return '@db.Decimal(18,2)';const m=String(n).match(/^(\\d{1,2})\\s*,\\s*(\\d{1,2})$/);if(!m)throw Error('decimal 长度/精度必须为 precision,scale，例如 10,2');return '@db.Decimal('+m[1]+','+m[2]+')';}},
    boolean:{type:'Boolean',native:()=>''},
    datetime:{type:'DateTime',native:()=> '@db.Timestamptz(6)'},
    json:{type:'Json',native:()=>''}
  };
  function fail(errors){const e=new Error('Prisma Schema 生成失败：\\n- '+errors.join('\\n- '));e.name='PrismaSchemaError';throw e;}
  function generate(models,relations,onlyId){
    const selected=(models||[]).filter(m=>!onlyId||m.id===onlyId);
    if(!selected.length)fail([onlyId?'指定实体不存在':'没有可生成的实体']);
    const errors=[],byId=new Map(),byName=new Map();
    selected.forEach(m=>{
      if(!IDENT.test(m.name||''))errors.push('实体名 '+(m.name||'(空)')+' 不是合法 Prisma 标识符');
      if(byId.has(m.id))errors.push('重复实体 ID：'+m.id);
      if(byName.has(m.name))errors.push('重复实体名：'+m.name);
      byId.set(m.id,m);byName.set(m.name,m);
      if(!Array.isArray(m.fields)||!m.fields.length)errors.push('实体 '+m.name+' 至少需要一个字段');
      const names=new Set();
      (m.fields||[]).forEach(f=>{
        if(!IDENT.test(f.name||''))errors.push(m.name+'.'+(f.name||'(空)')+' 不是合法字段标识符');
        if(names.has(f.name))errors.push(m.name+'.'+f.name+' 字段重复');
        names.add(f.name);
        if(!f.pk&&!TYPE_MAP[f.type])errors.push(m.name+'.'+f.name+' 不支持类型 '+f.type+'；enum 请先定义显式 Prisma enum');
        if(f.pk&&f.req===false)errors.push(m.name+'.'+f.name+' 主键不能为可空');
      });
      if((m.fields||[]).filter(f=>f.pk).length!==1)errors.push(m.name+' 必须且只能有一个主键字段');
    });
    const rels=(relations||[]).filter(r=>selected.some(m=>m.id===r.from)||selected.some(m=>m.id===r.to));
    const relationLines=new Map(selected.map(m=>[m.id,[]]));
    const relationNames=new Set();
    rels.forEach((r,i)=>{
      const child=byId.get(r.from),parent=byId.get(r.to);
      if(!child||!parent){errors.push('关系 '+(r.id||i)+' 的两端实体必须同时包含在本次生成范围内');return;}
      const fk=(child.fields||[]).find(f=>f.name===r.f),target=(parent.fields||[]).find(f=>f.name===r.t);
      if(!fk)errors.push('关系 '+(r.id||i)+' 外键字段 '+child.name+'.'+r.f+' 不存在');
      if(!target)errors.push('关系 '+(r.id||i)+' 引用字段 '+parent.name+'.'+r.t+' 不存在');
      if(fk&&target&&fk.type!==target.type)errors.push('关系 '+(r.id||i)+' 两端字段类型不一致：'+fk.type+' / '+target.type);
      if(!fk||!target)return;
      const oneToOne=/1\\s*:\\s*1/.test(r.type||'')||!!fk.unique;
      const name='Rel_'+child.name+'_'+r.f+'_'+parent.name;
      if(relationNames.has(name))errors.push('关系名称冲突：'+name);
      relationNames.add(name);
      const childProp=parent.name.charAt(0).toLowerCase()+parent.name.slice(1);
      const parentProp=child.name.charAt(0).toLowerCase()+child.name.slice(1)+'Records';
      relationLines.get(child.id).push('  '+childProp+(oneToOne&&!fk.req?'?':'')+' '+parent.name+(oneToOne&&!fk.req?'?':'')+' @relation("'+name+'", fields: ['+r.f+'], references: ['+r.t+'])');
      relationLines.get(parent.id).push('  '+parentProp+(oneToOne?'?':'')+' '+(oneToOne?child.name:child.name+'[]')+' @relation("'+name+'")');
    });
    if(errors.length)fail(errors);
    const blocks=selected.map(m=>{
      const lines=['model '+m.name+' {'];
      (m.fields||[]).forEach(f=>{
        const spec=TYPE_MAP[f.type],type=f.pk?'String':spec.type;
        let line='  '+f.name.padEnd(20)+' '+type;
        if(!f.pk&&!f.req)line+='?';
        if(f.pk)line+=' @id';
        if(f.unique&&!f.pk)line+=' @unique';
        if(f.default!==undefined&&f.default!==null&&f.default!==''){
          const v=f.default;
          if(typeof v==='number'&&Number.isFinite(v))line+=' @default('+v+')';
          else if(typeof v==='boolean')line+=' @default('+v+')';
          else if(typeof v==='string'&&/^[A-Za-z_][A-Za-z0-9_]*$/.test(v)&&['now','autoincrement','uuid','cuid'].includes(v))line+=' @default('+v+'())';
          else if(typeof v==='string')line+=' @default("'+v.replace(/\\/g,'\\\\').replace(/"/g,'\\"')+'")';
          else errors.push(m.name+'.'+f.name+' 默认值类型不受支持');
        }else if(f.pk&&f.generated==='uuid')line+=' @default(uuid())';
        else if(f.pk&&f.generated==='cuid')line+=' @default(cuid())';
        if(f.updatedAt)line+=' @updatedAt';
        try{if(spec)line+=' '+spec.native(f.len);}catch(e){errors.push(m.name+'.'+f.name+': '+e.message);}
        lines.push(line);
      });
      lines.push(...relationLines.get(m.id));
      (m.fields||[]).filter(f=>f.index&&!f.pk&&!f.unique).forEach(f=>lines.push('  @@index(['+f.name+'])'));
      lines.push('  @@map("'+m.name.toLowerCase()+'")','}');
      return lines.join('\\n');
    });
    if(errors.length)fail(errors);
    return 'datasource db {\\n  provider = "postgresql"\\n  url      = env("DATABASE_URL")\\n}\\n\\ngenerator client {\\n  provider = "prisma-client-js"\\n}\\n\\n'+blocks.join('\\n\\n')+'\\n';
  }
  root.PrismaSchema={generate};
})(typeof window!=='undefined'?window:globalThis);
