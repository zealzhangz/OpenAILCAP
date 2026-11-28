/* Local BPMN draft generator. It is explicitly a template aid, not a connected LLM. */
Object.assign(App.mods.bpm, {
  aiGen() {
    UI.modal({title:'BPMN 流程生成助手',size:'lg',body:
      '<div class="form-item"><label>描述业务流程</label><textarea class="input" id="bpmPrompt" style="min-height:100px">订单提交后由部门主管审批，金额超过 100000 时增加总经理审批，最后进入仓库验收</textarea></div>'+
      '<p class="help">本原型按规则模板生成可编辑草稿，不调用真实模型，也不启动真实流程实例。</p>',
      okText:'生成流程草稿',onOk:()=>this.generateFromPrompt()});
  },
  generateFromPrompt() {
    const prompt=document.getElementById('bpmPrompt')?.value?.trim();
    if(!prompt)return UI.toast('请描述流程','err');
    const d=Store.get('bpmDefs')[0],now=Date.now();
    const amountMatch=prompt.match(/(?:超过|大于|高于|>=|>)\s*([\d,]+)/);
    const hasAmount=!!amountMatch,amount=Number((amountMatch?.[1]||'100000').replace(/,/g,''));
    const hasWarehouse=/仓库|验收|交付/.test(prompt),hasManager=/总经理|多级|金额/.test(prompt);
    const nodes=[{id:'ai_start_'+now,type:'start',label:'开始',x:30,y:130},
      {id:'ai_submit_'+now,type:'user',label:'业务提交/确认',assignee:'initiator',x:200,y:130}];
    const edges=[{f:nodes[0].id,t:nodes[1].id}];
    let previous=nodes[1].id;
    if(hasAmount&&hasManager){
      const gateway='ai_gateway_'+now;
      nodes.push({id:gateway,type:'gateway',label:'金额 > '+amount,expr:'amount > '+amount,x:390,y:130});
      edges.push({f:previous,t:gateway});previous=gateway;
      const gm='ai_gm_'+now;
      nodes.push({id:gm,type:'user',label:'总经理审批',assignee:'pos:p1',sla:'8h',x:600,y:30});
      const dept='ai_dept_'+now;
      nodes.push({id:dept,type:'user',label:'部门主管审批',assignee:'pos:p2',sla:'4h',x:600,y:230});
      edges.push({f:gateway,t:gm,when:'金额超限'},{f:gateway,t:dept,when:'未超限'});
      previous=null;
      if(hasWarehouse){
        const warehouse='ai_warehouse_'+now;
        nodes.push({id:warehouse,type:'user',label:'仓库验收',assignee:'dept:d3',sla:'24h',x:820,y:130});
        edges.push({f:gm,t:warehouse},{f:dept,t:warehouse});previous=warehouse;
      }else{
        const end='ai_end_'+now;nodes.push({id:end,type:'end',label:'结束',x:850,y:130});
        edges.push({f:gm,t:end},{f:dept,t:end});
      }
    }else{
      const approval='ai_approval_'+now;
      nodes.push({id:approval,type:'user',label:'业务审批',assignee:'pos:p2',sla:'4h',x:430,y:130});
      edges.push({f:previous,t:approval});previous=approval;
      if(hasWarehouse){
        const warehouse='ai_warehouse_'+now;
        nodes.push({id:warehouse,type:'user',label:'仓库验收',assignee:'dept:d3',sla:'24h',x:650,y:130});
        edges.push({f:previous,t:warehouse});previous=warehouse;
      }
    }
    if(previous){
      const end='ai_end_'+now;nodes.push({id:end,type:'end',label:'结束',x:Math.max(...nodes.map(n=>n.x))+200,y:130});
      edges.push({f:previous,t:end});
    }
    d.name=prompt.slice(0,32);d.nodes=nodes;d.edges=edges;d.status='draft';
    d.version='v'+(Number(String(d.version||'v1').replace(/\D/g,''))+1);
    Store.save();UI.closeModal();this.sel=null;this.draw();
    UI.toast('已生成 '+nodes.length+' 个节点和 '+edges.length+' 条流程连线');
  }
});
