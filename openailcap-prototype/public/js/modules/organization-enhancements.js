/* Organization local-prototype enhancements: persisted permission templates and approval-request lifecycle. */
(function(){
  const Org=App.mods.org;
  const resources=[
    {key:'orders',label:'订单'},{key:'customers',label:'客户'},
    {key:'reports',label:'报表'},{key:'approvals',label:'审批'},{key:'exports',label:'数据导出'}
  ];
  const actions=[{key:'read',label:'查'},{key:'create',label:'增'},{key:'update',label:'改'},{key:'delete',label:'删'},{key:'approve',label:'审'}];
  const defaults={
    tpl_ceo:['orders','customers','reports','approvals','exports'],
    tpl_dir:['orders','customers','reports','approvals'],
    tpl_sales_lead:['orders','customers','reports','approvals'],
    tpl_sales:['orders','customers','reports'],
    tpl_cto:['orders','reports','approvals'],
    tpl_dev:['orders','reports'],
    tpl_hr:['reports','approvals'],
    tpl_fin:['orders','reports','approvals','exports']
  };
  const ensure=(key,fallback)=>{if(!Array.isArray(Store.data[key]))Store.data[key]=fallback;return Store.data[key];};
  const esc=UI.esc;
  Org.editTpl=function(positionId){
    const position=Store.find('positions',positionId);if(!position)return UI.toast('岗位不存在','err');
    const all=Store.data.permissionTemplates||{};
    const saved=all[position.template]||{};
    const allowed=defaults[position.template]||['reports'];
    const body='<p class="muted">权限模板保存到本地演示数据。此配置不会下发生产 RBAC/PDP。</p>'+
      '<div class="perm-matrix" style="--pmc:5"><div class="pm-row"><div class="pm-cell head">资源</div>'+
      actions.map(a=>'<div class="pm-cell head">'+a.label+'</div>').join('')+'</div>'+
      resources.map(res=>'<div class="pm-row"><div class="pm-cell res">'+res.label+'</div>'+
        actions.map(action=>{
          const defaultOn=allowed.includes(res.key)&&(['read'].includes(action.key)||
            (['tpl_ceo','tpl_dir','tpl_sales_lead','tpl_cto','tpl_fin'].includes(position.template)&&['create','update'].includes(action.key))||
            (['tpl_ceo','tpl_fin'].includes(position.template)&&['delete','export'].includes(action.key))||
            (['tpl_ceo','tpl_dir','tpl_sales_lead','tpl_hr','tpl_fin'].includes(position.template)&&action.key==='approve'));
          const checked=(saved[res.key]?.includes(action.key)??defaultOn)?' checked':'';
          return '<div class="pm-cell"><input type="checkbox" data-perm-resource="'+res.key+'" data-perm-action="'+action.key+'"'+checked+' aria-label="'+res.label+action.label+'"></div>';
        }).join('')+'</div>').join('')+'</div>';
    UI.modal({title:'权限模板 · '+position.name,size:'lg',body,okText:'保存本地模板',onOk:()=>{
      const matrix={};
      resources.forEach(r=>{matrix[r.key]=[...document.querySelectorAll('[data-perm-resource="'+r.key+'"]:checked')].map(el=>el.dataset.permAction);});
      Store.data.permissionTemplates=Store.data.permissionTemplates||{};
      Store.data.permissionTemplates[position.template]=matrix;Store.save();UI.closeModal();
      UI.toast('权限模板已保存到本地演示数据');
    }});
  };
  Org.drawChg=function(){
    const pending=ensure('orgChangeRequests',[]).filter(x=>x.status==='pending');
    const history=Store.get('empChanges')||[];
    const requestHtml=pending.map(r=>{
      const employee=Store.find('employees',r.employeeId);
      const target=r.type==='transfer'?'部门/岗位变更':'晋升至 '+(Store.find('positions',r.toPos)||{}).name;
      return '<div class="tl-item"><div class="tl-t">⏳ '+(r.type==='transfer'?'调岗申请':'晋升申请')+' · '+esc(employee?.name||'员工已不存在')+
        ' → '+esc(target)+'</div><div class="tl-d">'+esc(r.reason||'未填写原因')+' · '+esc(r.submittedAt)+' · LOCAL DEMO</div>'+
        '<div class="btn-row mt10"><button class="btn btn-sm btn-p" onclick="OrgM.decideChange(\''+r.id+'\',\'approved\')">本地模拟通过</button>'+
        '<button class="btn btn-sm" onclick="OrgM.decideChange(\''+r.id+'\',\'rejected\')">驳回</button></div></div>';
    }).join('');
    const historyHtml=history.map(c=>'<div class="tl-item"><div class="tl-t">'+(c.type==='transfer'?'🔄 调岗':'📈 晋升')+' · '+esc(c.note||'')+
      '</div><div class="tl-d">'+esc(c.time||'')+' · '+esc(c.by||'')+'</div></div>').join('');
    const el=document.getElementById('chgList');if(el)el.innerHTML='<p class="muted">申请审批仅在本地演示状态流转，不代表真实 HR 审批。</p>'+
      (requestHtml||'<div class="muted">暂无待处理申请</div>')+'<hr>'+(historyHtml||'<div class="muted">暂无历史记录</div>');
  };
  Org.transfer=function(id){
    const employee=Store.find('employees',id);if(!employee)return UI.toast('员工不存在','err');
    const body=UI.drawerForm([
      {key:'dept',label:'新部门',type:'select',options:Store.get('depts').map(d=>({v:d.id,l:d.name})),value:employee.dept},
      {key:'pos',label:'新岗位',type:'select',options:Store.get('positions').map(p=>({v:p.id,l:p.name})),value:employee.pos},
      {key:'mgr',label:'新主管',type:'select',options:[{v:'',l:'无'},...Store.get('employees').filter(e=>e.id!==id).map(e=>({v:e.id,l:e.name}))],value:employee.mgr||''},
      {key:'note',label:'调岗原因',type:'textarea'}
    ],employee);
    UI.modal({title:'员工调岗申请 · '+employee.name,body,okText:'提交本地审批申请',onOk:()=>{
      const values=UI.collectForm();
      if(!Store.find('depts',values.dept)||!Store.find('positions',values.pos))return UI.toast('请选择有效部门和岗位','err');
      if(values.mgr===id)return UI.toast('员工不能将自己设置为直属主管','err');
      let cursor=values.mgr,seen=new Set();
      while(cursor){if(cursor===id)return UI.toast('该主管关系会形成汇报环路','err');if(seen.has(cursor))return UI.toast('现有汇报线已存在环路，请先修复','err');seen.add(cursor);cursor=Store.find('employees',cursor)?.mgr||null;}
      ensure('orgChangeRequests',[]).push({id:'orgchg_'+Date.now(),employeeId:id,type:'transfer',fromDept:employee.dept,fromPos:employee.pos,fromMgr:employee.mgr,toDept:values.dept,toPos:values.pos,toMgr:values.mgr||null,reason:values.note||'',status:'pending',submittedAt:new Date().toISOString()});
      Store.save();UI.closeModal();this.drawChg();UI.toast('调岗申请已保存，等待本地模拟审批');
    }});
  };
  Org.promote=function(id){
    const employee=Store.find('employees',id);if(!employee)return UI.toast('员工不存在','err');
    UI.modal({title:'员工晋升申请 · '+employee.name,body:UI.drawerForm([
      {key:'pos',label:'拟晋升岗位',type:'select',options:Store.get('positions').map(p=>({v:p.id,l:p.name+' ('+p.level+')'})),value:employee.pos},
      {key:'note',label:'晋升理由',type:'textarea'}
    ]),okText:'提交本地审批申请',onOk:()=>{
      const values=UI.collectForm();if(!Store.find('positions',values.pos))return UI.toast('请选择有效岗位','err');
      if(values.pos===employee.pos)return UI.toast('拟晋升岗位与当前岗位相同','warn');
      ensure('orgChangeRequests',[]).push({id:'orgchg_'+Date.now(),employeeId:id,type:'promotion',fromPos:employee.pos,toPos:values.pos,reason:values.note||'',status:'pending',submittedAt:new Date().toISOString()});
      Store.save();UI.closeModal();this.drawChg();UI.toast('晋升申请已保存，等待本地模拟审批');
    }});
  };
  Org.decideChange=function(id,decision){
    const request=ensure('orgChangeRequests',[]).find(x=>x.id===id);
    if(!request||request.status!=='pending')return UI.toast('申请不存在或已处理','err');
    const employee=Store.find('employees',request.employeeId);
    if(!employee)return UI.toast('员工不存在，不能处理申请','err');
    if(decision==='approved'){
      if(request.type==='transfer'){
        if(!Store.find('depts',request.toDept)||!Store.find('positions',request.toPos))return UI.toast('目标部门或岗位已失效','err');
        employee.dept=request.toDept;employee.pos=request.toPos;employee.mgr=request.toMgr||null;
      }else if(request.type==='promotion'){
        if(!Store.find('positions',request.toPos))return UI.toast('目标岗位已失效','err');
        employee.pos=request.toPos;
      }
      Store.data.empChanges=Store.data.empChanges||[];
      Store.data.empChanges.unshift({id:'chg_'+Date.now(),emp:employee.id,type:request.type,from:request.type==='transfer'?request.fromPos:request.fromPos,to:request.toPos,note:request.reason||'本地模拟审批通过',time:new Date().toISOString(),by:'本地模拟审批人'});
    }
    request.status=decision;request.decidedAt=new Date().toISOString();request.decidedBy='本地模拟审批人';
    Store.save();this.drawTree();this.drawPos();this.drawChg();
    if(this.selEmp===employee.id)this.pickEmp(employee.id);
    UI.toast(decision==='approved'?'本地模拟审批已通过':'申请已驳回');
  };
})();
