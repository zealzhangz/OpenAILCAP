/* BPMN designer enhancements: graph-driven BPMN 2.0 interchange and process simulation. */
Object.assign(App.mods.bpm, {
  save() { Store.save();UI.toast('BPMN 流程草稿已保存'); },
  xmlEscape(value) { return String(value??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&apos;'); },
  bpmnType(type) {
    return ({start:'startEvent',end:'endEvent',user:'userTask',service:'serviceTask',auto:'serviceTask',gateway:'exclusiveGateway',parallel:'parallelGateway',inclusive:'inclusiveGateway',sub:'subProcess',dataobj:'dataObjectReference',datastore:'dataStoreReference',timer:'intermediateCatchEvent',msg:'intermediateCatchEvent'})[type]||'task';
  },
  exportBpmn() {
    const d=Store.get('bpmDefs')[0],nodes=d.nodes||[],edges=d.edges||[];
    const ids=new Set(nodes.map(n=>n.id));
    const invalid=edges.filter(e=>!ids.has(e.f)||!ids.has(e.t));
    if(invalid.length)return UI.toast('存在引用不存在节点的连线，无法导出','err');
    const xmlNodes=nodes.map(n=>{
      const tag=this.bpmnType(n.type);
      const incoming=edges.filter(e=>e.t===n.id).map(e=>'<bpmn:incoming>'+this.xmlEscape(e.id||('Flow_'+e.f+'_'+e.t))+'</bpmn:incoming>').join('');
      const outgoing=edges.filter(e=>e.f===n.id).map(e=>'<bpmn:outgoing>'+this.xmlEscape(e.id||('Flow_'+e.f+'_'+e.t))+'</bpmn:outgoing>').join('');
      const body=(tag==='startEvent'||tag==='endEvent'||tag==='exclusiveGateway'||tag==='parallelGateway'||tag==='inclusiveGateway'||tag==='dataObjectReference'||tag==='dataStoreReference')?'':incoming+outgoing;
      return '<bpmn:'+tag+' id="'+this.xmlEscape(n.id)+'" name="'+this.xmlEscape(n.label)+'">'+body+'</bpmn:'+tag+'>';
    }).join('\n');
    const xmlEdges=edges.map(e=>'<bpmn:sequenceFlow id="'+this.xmlEscape(e.id||('Flow_'+e.f+'_'+e.t))+'" sourceRef="'+this.xmlEscape(e.f)+'" targetRef="'+this.xmlEscape(e.t)+'" name="'+this.xmlEscape(e.when||'')+'"/>').join('\n');
    const xml='<?xml version="1.0" encoding="UTF-8"?>\n'+
      '<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:oac="https://openailcap.dev/bpmn" id="Definitions_'+this.xmlEscape(d.id)+'" targetNamespace="https://openailcap.dev/bpmn">\n'+
      '  <bpmn:process id="'+this.xmlEscape(d.id)+'" name="'+this.xmlEscape(d.name)+'" isExecutable="true">\n'+xmlNodes+'\n'+xmlEdges+'\n  </bpmn:process>\n</bpmn:definitions>';
    UI.modal({title:'导出 BPMN 2.0 XML',size:'xl',footer:false,body:
      '<div class="code-view"><pre>'+UI.esc(xml)+'</pre></div>'+
      '<div class="btn-row mt10"><button class="btn btn-p" onclick="BpmM.downloadBpmn()">下载 XML</button></div>'});
    this._lastXml=xml;
  },
  downloadBpmn() {
    if(!this._lastXml)return UI.toast('请先生成 BPMN XML','warn');
    const blob=new Blob([this._lastXml],{type:'application/xml;charset=utf-8'});
    const url=URL.createObjectURL(blob),a=document.createElement('a');
    a.href=url;a.download=(Store.get('bpmDefs')[0].name||'process')+'.bpmn';a.click();URL.revokeObjectURL(url);
  },
  importBpmn() {
    UI.modal({title:'导入 BPMN 2.0 XML',size:'lg',body:
      '<div class="form-item"><label>BPMN XML</label><textarea class="input mono" id="bpmnImportXml" style="min-height:220px" placeholder="粘贴 BPMN 2.0 definitions XML"></textarea></div>',
      okText:'解析并替换当前流程',onOk:()=>this.parseBpmnImport()});
  },
  parseBpmnImport() {
    const raw=document.getElementById('bpmnImportXml').value;
    if(!raw.trim())return UI.toast('请粘贴 BPMN XML','err');
    const xml=new DOMParser().parseFromString(raw,'application/xml');
    if(xml.querySelector('parsererror'))return UI.toast('XML 解析失败，请检查格式','err');
    const process=xml.getElementsByTagNameNS('*','process')[0];
    if(!process)return UI.toast('未找到 BPMN process','err');
    const map={startEvent:'start',endEvent:'end',userTask:'user',serviceTask:'service',exclusiveGateway:'gateway',parallelGateway:'parallel',inclusiveGateway:'inclusive',subProcess:'sub',dataObjectReference:'dataobj',dataStoreReference:'datastore',intermediateCatchEvent:'timer'};
    const nodes=[],edges=[];let index=0;
    Array.from(process.children).forEach(el=>{
      const local=el.localName;
      if(local==='sequenceFlow'){
        edges.push({id:el.getAttribute('id'),f:el.getAttribute('sourceRef'),t:el.getAttribute('targetRef'),when:el.getAttribute('name')||''});
      }else if(map[local]){
        nodes.push({id:el.getAttribute('id')||('node_'+index),type:map[local],label:el.getAttribute('name')||local,x:30+(index%4)*190,y:50+Math.floor(index/4)*150});
        index++;
      }
    });
    if(!nodes.length)return UI.toast('没有识别到可支持的 BPMN 节点','err');
    const ids=new Set(nodes.map(n=>n.id)),valid=edges.filter(e=>ids.has(e.f)&&ids.has(e.t));
    const d=Store.get('bpmDefs')[0];d.nodes=nodes;d.edges=valid;d.version='v'+(Number(String(d.version||'v1').replace(/\D/g,''))+1);
    Store.save();UI.closeModal();this.draw();UI.toast('已导入 '+nodes.length+' 个节点、'+valid.length+' 条连线');
  },
  connect() {
    const d=Store.get('bpmDefs')[0],opts=d.nodes.map(n=>'<option value="'+UI.esc(n.id)+'">'+UI.esc(n.label)+' · '+n.id+'</option>').join('');
    if(d.nodes.length<2)return UI.toast('至少需要两个节点','warn');
    UI.modal({title:'连接 BPMN 节点',body:
      '<div class="form-item"><label>起点</label><select class="input" id="bpmFrom">'+opts+'</select></div>'+
      '<div class="form-item"><label>终点</label><select class="input" id="bpmTo">'+opts+'</select></div>'+
      '<div class="form-item"><label>流转条件/名称</label><input class="input" id="bpmWhen"></div>',
      okText:'添加连线',onOk:()=>{
        const f=document.getElementById('bpmFrom').value,t=document.getElementById('bpmTo').value;
        if(f===t)return UI.toast('不能连接到自身','err');
        if(d.edges.some(e=>e.f===f&&e.t===t))return UI.toast('连线已存在','warn');
        d.edges.push({id:'Flow_'+Date.now(),f,t,when:document.getElementById('bpmWhen').value.trim()});
        Store.save();UI.closeModal();this.draw();UI.toast('BPMN 连线已添加');
      }});
  },
  removeEdge() {
    const d=Store.get('bpmDefs')[0];if(!d.edges.length)return UI.toast('没有可删除连线','info');
    const opts=d.edges.map((e,i)=>'<option value="'+i+'">'+e.f+' → '+e.t+(e.when?' ['+e.when+']':'')+'</option>').join('');
    UI.modal({title:'删除 BPMN 连线',body:'<select class="input" id="bpmEdgeRemove">'+opts+'</select>',okText:'删除',onOk:()=>{
      d.edges.splice(Number(document.getElementById('bpmEdgeRemove').value),1);Store.save();UI.closeModal();this.draw();UI.toast('连线已删除');
    }});
  },
  simulate() {
    const d=Store.get('bpmDefs')[0],start=d.nodes.find(n=>n.type==='start');
    if(!start)return UI.toast('流程缺少开始事件','err');
    const visited=[],queue=[start.id],seen=new Set();let guard=0;
    while(queue.length&&guard++<100){const id=queue.shift();if(seen.has(id))continue;seen.add(id);
      const n=d.nodes.find(x=>x.id===id);if(!n)continue;visited.push(n);
      let edges=d.edges.filter(e=>e.f===id);
      if(n.type==='gateway'&&edges.length>1)edges=edges.slice(0,1);
      edges.forEach(e=>queue.push(e.t));
    }
    const log={id:'bpm_sim_'+Date.now(),definitionId:d.id,visited:visited.map(n=>n.id),labels:visited.map(n=>n.label),status:guard>=100?'循环保护中止':'仿真完成',time:new Date().toISOString()};
    Store.data.bpmSimulationLogs=Store.data.bpmSimulationLogs||[];Store.data.bpmSimulationLogs.unshift(log);Store.save();
    UI.modal({title:'BPMN 流程仿真',size:'lg',footer:false,body:
      '<div class="tl">'+visited.map((n,i)=>'<div class="tl-item"><div class="tl-t">'+(i+1)+'. '+UI.esc(n.label)+'</div><div class="tl-d">'+n.type+' · '+n.id+'</div></div>').join('')+'</div>'+
      '<div class="success">'+log.status+' · 遍历 '+visited.length+'/'+d.nodes.length+' 个可达节点</div>'+
      '<p class="help">本地仿真只检查图可达性，不执行用户任务、服务任务或外部副作用；真实流程执行须接入 BPMN 引擎。</p>'});
  },
  publish() {
    const d=Store.get('bpmDefs')[0];
    const starts=d.nodes.filter(n=>n.type==='start').length,ends=d.nodes.filter(n=>n.type==='end').length;
    if(starts!==1||ends<1)return UI.toast('发布校验失败：流程必须有且仅有一个开始事件并至少有一个结束事件','err');
    const ids=new Set(d.nodes.map(n=>n.id));if(d.edges.some(e=>!ids.has(e.f)||!ids.has(e.t)))return UI.toast('发布校验失败：存在无效连线','err');
    d.status='published';d.publishedAt=new Date().toISOString();Store.save();UI.toast('流程定义已发布为 '+d.version);
  }
});
