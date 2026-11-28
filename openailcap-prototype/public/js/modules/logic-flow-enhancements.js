/* LogicFlow interaction enhancements: operate on the current graph, never fixed demo data. */
Object.assign(App.mods.flow, {
  save() {
    Store.save();
    UI.toast('逻辑流程草稿已保存');
  },
  connect() {
    const f=Store.get('logicFlows')[0];
    if(f.nodes.length<2) return UI.toast('至少需要两个节点才能连线','warn');
    const opts=f.nodes.map(n=>'<option value="'+UI.esc(n.id)+'">'+UI.esc(n.label)+' · '+n.id+'</option>').join('');
    UI.modal({
      title:'创建节点连线',
      body:'<div class="form-item"><label>起点</label><select class="input" id="edgeFrom">'+opts+'</select></div>'+
        '<div class="form-item"><label>终点</label><select class="input" id="edgeTo">'+opts+'</select></div>'+
        '<div class="form-item"><label>分支条件（可选）</label><input class="input" id="edgeWhen" placeholder="true / false / success"></div>',
      okText:'创建连线',
      onOk:()=>{
        const from=document.getElementById('edgeFrom').value;
        const to=document.getElementById('edgeTo').value;
        const when=document.getElementById('edgeWhen').value.trim();
        if(from===to) return UI.toast('起点和终点不能相同','err');
        if(f.edges.some(e=>e.f===from&&e.t===to)) return UI.toast('连线已存在','warn');
        f.edges.push({f:from,t:to,...(when?{when}:{})});
        Store.save();UI.closeModal();this.draw();UI.toast('连线已创建');
      }
    });
  },
  removeEdge() {
    const f=Store.get('logicFlows')[0];
    if(!f.edges.length) return UI.toast('当前没有连线','info');
    const opts=f.edges.map((e,i)=>{
      const a=f.nodes.find(n=>n.id===e.f),b=f.nodes.find(n=>n.id===e.t);
      return '<option value="'+i+'">'+UI.esc(a?.label||e.f)+' → '+UI.esc(b?.label||e.t)+(e.when?' ['+e.when+']':'')+'</option>';
    }).join('');
    UI.modal({title:'删除节点连线',body:'<select class="input" id="edgeRemove">'+opts+'</select>',okText:'删除',onOk:()=>{
      f.edges.splice(Number(document.getElementById('edgeRemove').value),1);
      Store.save();UI.closeModal();this.draw();UI.toast('连线已删除');
    }});
  },
  testGraph() {
    UI.modal({title:'逻辑图模拟测试',size:'lg',footer:false,body:
      '<div class="form-item"><label>输入 JSON</label><textarea class="input mono" id="logicInput" style="min-height:100px">{ "amount": 152000, "customer": "C-001" }</textarea></div>'+
      '<button class="btn btn-p" onclick="LogicM.runGraphTest()">运行模拟</button><div id="logicRunOut" class="mt10"></div>'+
      '<p class="help">本地只验证图结构可达性和简单条件分支，不执行外部 API 或数据库副作用。</p>'});
  },
  runGraphTest() {
    const f=Store.get('logicFlows')[0],out=document.getElementById('logicRunOut');
    let vars;
    try{vars=JSON.parse(document.getElementById('logicInput').value);}catch(e){out.innerHTML='<div class="err-msg">JSON 格式错误</div>';return;}
    const start=f.nodes.find(n=>n.type==='event'||n.type==='start');
    if(!start){out.innerHTML='<div class="err-msg">缺少开始/事件节点</div>';return;}
    const visited=[],queue=[start.id],seen=new Set();let guard=0;
    while(queue.length&&guard++<100){
      const id=queue.shift();if(seen.has(id))continue;seen.add(id);
      const n=f.nodes.find(x=>x.id===id);if(!n)continue;visited.push(n);
      let edges=f.edges.filter(e=>e.f===id);
      if(n.type==='condition'&&n.expr){
        const m=n.expr.match(/([\w.]+)\s*(>=|<=|>|<|==|!=)\s*([\d.]+)/);
        if(m){
          const left=m[1].split('.').reduce((v,k)=>v==null?undefined:v[k],vars),right=Number(m[3]);
          const result=m[2]==='>'?left>right:m[2]==='>='?left>=right:m[2]==='<'?left<right:m[2]==='<='?left<=right:m[2]==='=='?left==right:left!=right;
          const chosen=edges.filter(e=>String(e.when||'').toLowerCase()===(result?'true':'false'));
          if(chosen.length)edges=chosen;
        }
      }
      if(edges.length>1)edges=edges.slice(0,1);
      edges.forEach(e=>queue.push(e.t));
    }
    const labels=visited.map(n=>n.label),status=guard>=100?'循环保护中止':'模拟完成';
    Store.data.logicLogs=Store.data.logicLogs||[];
    Store.data.logicLogs.unshift({id:'run_'+Date.now(),flowId:f.id,input:vars,path:labels,status,time:new Date().toISOString()});
    Store.save();
    out.innerHTML='<div class="tl">'+visited.map((n,i)=>'<div class="tl-item"><div class="tl-t">'+(i+1)+'. '+UI.esc(n.label)+'</div><div class="tl-d">'+n.type+' · '+n.id+'</div></div>').join('')+'</div>'+
      '<div class="success">'+status+' · 实际遍历 '+visited.length+'/'+f.nodes.length+' 个可达节点</div>';
  },
  graphCode() {
    const f=Store.get('logicFlows')[0];
    const code='// Generated from current LogicFlow definition\nexport const flow = '+JSON.stringify(f,null,2)+' as const;\n\n'+
      'export async function execute(input: Record<string, unknown>, ctx: { invoke: (node: unknown, vars: Record<string, unknown>) => Promise<unknown> }) {\n'+
      '  const vars = { ...input };\n  const visited: string[] = [];\n'+
      '  // Validate expressions and enforce tool permissions in the backend runtime.\n'+
      '  for (const node of flow.nodes) { visited.push(node.id); await ctx.invoke(node, vars); }\n'+
      '  return { vars, visited };\n}';
    UI.modal({title:'基于当前画布生成代码',size:'lg',footer:false,body:
      '<div class="code-view"><pre>'+UI.esc(code)+'</pre></div>'+
      '<p class="help">生成内容引用当前节点与连线定义；生产执行器须在受限后端运行时完成分支求值、权限检查与副作用控制。</p>'});
  },
  aiGen() {
    UI.modal({title:'逻辑流程生成助手',body:
      '<div class="form-item"><label>描述业务逻辑</label><textarea class="input" id="logicPrompt" style="min-height:100px">提交订单时，金额超过 10000 通知审批人，否则直接保存，最后返回结果</textarea></div>'+
      '<p class="help">当前为本地规则模板演示；生产版本接入 Agent。</p>',
      okText:'生成并替换画布',onOk:()=>this.generateFromPrompt()});
  },
  generateFromPrompt() {
    const prompt=document.getElementById('logicPrompt')?.value?.trim();
    if(!prompt)return UI.toast('请描述业务逻辑','err');
    const f=Store.get('logicFlows')[0],now=Date.now();
    const match=prompt.match(/(?:超过|大于|高于|>=|>)\s*([\d,]+)/);
    const threshold=Number((match?.[1]||'10000').replace(/,/g,''));
    const start='ai_start_'+now,cond='ai_cond_'+now,yes='ai_yes_'+now,no='ai_no_'+now,end='ai_end_'+now;
    const notify=/通知|提醒|消息/.test(prompt);
    f.name=prompt.slice(0,36);
    f.nodes=[
      {id:start,type:'event',label:'业务触发',x:40,y:100},
      {id:cond,type:'condition',label:'业务条件判断',expr:'amount > '+threshold,x:250,y:100},
      {id:yes,type:notify?'notify':'data',label:notify?'发送业务通知':'保存业务数据',op:'insert',x:480,y:20},
      {id:no,type:'data',label:'默认业务处理',op:'insert',x:480,y:180},
      {id:end,type:'end',label:'流程结束',x:720,y:100}
    ];
    f.edges=[{f:start,t:cond},{f:cond,t:yes,when:'true'},{f:cond,t:no,when:'false'},{f:yes,t:end},{f:no,t:end}];
    Store.save();UI.closeModal();this.sel=null;this.draw();
    UI.toast('已生成 '+f.nodes.length+' 个节点和 '+f.edges.length+' 条连线');
  }
});
