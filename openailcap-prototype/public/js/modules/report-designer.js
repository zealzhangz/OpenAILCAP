/* ============ Module 7: 报表设计器 (GB 6.2.5) ============ */
App.mods.report = {
  render() {
    const r = Store.get('reports')[0];
    return `
    <div class="page-head"><h1>📈 报表设计器</h1><span class="sub">${r.name} · GB 6.2.5 图文/表格编辑 + 数据流转输出 + 数据整合 + 模板</span>
      <span class="spacer"></span>
      <button class="btn" onclick="UI.toast('已导出 Excel')">⬇️ Excel</button>
      <button class="btn" onclick="UI.toast('已导出 PDF')">⬇️ PDF</button>
      <button class="btn" onclick="ReportM.tpl()">📚 报表模板库</button>
      <button class="btn" onclick="ReportM.sources()">🔗 数据源</button>
      <button class="btn btn-p" onclick="UI.toast('报表已保存并发布')">💾 保存</button>
    </div>
    <div class="designer designer-no-left" style="height:auto;min-height:560px">
      <div class="dz-center" style="background:#fff"><div class="dz-canvas" id="rpCanvas">
        <div class="card" style="padding:18px">
          <div class="flex" style="margin-bottom:12px"><b style="font-size:15px">月度销售统计报表</b>
            <span class="spacer"></span><span class="muted">数据源: Order · 更新: 每 5 分钟自动刷新 (GB 6.2.5.2.4 c)</span></div>
          <div class="grid cols-4" style="margin-bottom:14px">
            ${[['销售额','¥ 8,462,300','+12.4%'],['订单数','1,284','+8.2%'],['客单价','¥ 6,590','-2.1%'],['退款率','1.2%','-0.3%']]
            .map(([l,v,t])=>`<div class="stat-tile"><div><div class="l">${l}</div>
            <div class="v">${v}<span class="trend ${t.startsWith('-')?'down':'up'}">${t}</span></div></div></div>`).join('')}
          </div>
          <div class="grid cols-2">
            <div class="card"><div class="card-h">📊 按月销售额（表格编辑：分组/小计/交叉表头/下钻/分页）</div>
              <div class="card-b"><div class="tbl-wrap"><table class="tbl">
              <thead><tr><th>月份</th><th>订单数</th><th>销售额</th><th>同比</th></tr></thead><tbody>
              ${[['2026-08','1,102','7,204,000','+6%'],['2026-09','1,187','7,890,500','+9.5%'],['2026-10','1,201','7,990,000','+1.3%'],['2026-11(月内)','1,284','8,462,300','+12.4%']]
              .map(r=>`<tr>${r.map(c=>`<td>${c}</td>`).join('')}</tr>`).join('')}
              <tr style="font-weight:800;background:#f8faff"><td>合计/小计</td><td>4,774</td><td>31,546,800</td><td>—</td></tr>
              </tbody></table></div>
              <div class="tbl-pagination"><a class="link">◀ 上一页</a> 1 / 12 <a class="link">下一页 ▶</a> <a class="link" onclick="UI.toast('下钻至订单明细')">下钻明细 ▸</a></div>
            </div></div>
            <div class="card"><div class="card-h">📈 近 30 天订单趋势（拖拽式图文组件）</div>
              <div class="card-b"><div id="rpTrend"></div></div></div>
          </div>
          <div class="grid cols-2 mt14">
            <div class="card"><div class="card-h">🥧 客户等级分布（饼图组件）</div><div class="card-b"><div id="rpPie"></div></div></div>
            <div class="card"><div class="card-h">📊 销售员业绩 Top5（柱状组件）</div><div class="card-b"><div id="rpBar"></div></div></div>
          </div>
        </div>
      </div></div>
      <div class="dz-right">
        <div class="form-item"><label>数据源整合（GB 6.2.5.2.4 提取/清理/更新）</label>
          <select class="input"><option>Order 主表</option><option>+ Customer 关联</option><option>+ API 外部 ERP 数据</option><option>+ Excel 上传补充</option></select></div>
        <div class="form-item"><label>图表类型</label><select class="input">
          <option>柱状图</option><option>折线图</option><option>饼图/环形</option><option>散点</option><option>热力</option><option>漏斗</option></select></div>
        <div class="form-item"><label>维度 / 指标</label>
          <div class="item">维度: order_date(月) · status</div><div class="item">指标: SUM(amount) · COUNT(*)</div></div>
        <div class="form-item"><label>筛选器</label>
          <div class="flex wrap"><span class="tag tag-blue">日期范围</span><span class="tag tag-blue">客户等级</span><span class="tag tag-blue">部门</span>
          <a class="link" onclick="UI.toast('新增筛选器')">＋</a></div></div>
        <div class="form-item"><label>自动更新</label><div class="flex"><div class="switch on" onclick="this.classList.toggle('on')"></div><span class="muted">每 5 分钟</span></div></div>
        <button class="btn btn-p" style="width:100%" onclick="UI.toast('🤖 AI 已根据数据分布推荐：改用双轴折线+柱，突出转化率')">🤖 AI 图表推荐</button>
      </div>
    </div>`;
  },
  mount() { setTimeout(()=>{ Charts.line(document.getElementById('rpTrend'),
      Array.from({length:30},(_,i)=>(i+1)+''), [{name:'订单量',data:Array.from({length:30},()=>30+Math.round(Math.random()*40))},
      {name:'金额(万)',data:Array.from({length:30},()=>5+Math.round(Math.random()*9)),dash:false}], {noDots:true});
    Charts.pie(document.getElementById('rpPie'), ['A1 战略','A2 重点','B 普通','C 其他'], [412,537,286,49]);
    Charts.bar(document.getElementById('rpBar'), ['孙十','吴九','钱七','冯二','郑一'], [182,164,150,132,118]); }, 60); },
  tpl() { UI.modal({ title:'📚 报表模板库（GB 6.2.5.3 L2）', size:'lg', footer:false, body:`
    <div class="grid cols-3">${[['月度经营看板','📊','KPI+趋势+排名'],['财务对账单','💰','分组小计+交叉表'],['库存周报','📦','下钻+导出'],
      ['人力盘点','👥','多维透视'],['项目进度','📋','甘特+燃尽'],['销售漏斗','🎯','漏斗+转化率']].map(([n,i,d])=>`
      <div class="item" style="cursor:pointer" onclick="UI.toast('模板「${n}」已创建副本')"><div style="font-size:24px">${i}</div><b>${n}</b><div class="muted">${d}</div></div>`).join('')}</div>` });
  },
  sources() { UI.modal({ title:'🔗 数据源管理', size:'lg', footer:false, body:`
    ${[['PostgreSQL 主库','✅ 已连接','12 表'],['MySQL ERP','✅ 已连接','只读'],['REST API(物流)','✅ 已连接','限流 100/min'],['Excel 上传','📁 最近: 2026-11-20','人工刷新']].map(([n,s,d])=>`
    <div class="item"><div class="flex"><b>${n}</b><span class="tag tag-green">${s}</span><span class="muted" style="margin-left:auto">${d}</span></div></div>`).join('')}
    <button class="btn btn-p" onclick="UI.toast('数据源连接向导（GB 6.5.7 数据源管理）')">＋ 新增数据源</button>` });
  },
};

/* ============ Module 8: 数据大屏 (GB 6.2.6) ============ */
App.mods.screen = {
  render() {
    const db = Store.get('dashboards')[0];
    return `
    <div class="page-head"><h1>🖥️ 数据大屏</h1><span class="sub">${db.name} · GB 6.2.6 布局/图层/主题/交互/动态更新/分享</span>
      <span class="spacer"></span>
      <button class="btn" onclick="ScreenM.publish()">🔗 发布分享</button>
      <button class="btn" onclick="ScreenM.theme()">🎨 主题</button>
      <button class="btn btn-p" onclick="UI.toast('大屏已保存')">💾 保存</button>
    </div>
    <div class="screen-grid" id="screenGrid">
      ${db.widgets.map(w=>`<div class="screen-card span-${w.span}" draggable="true" data-id="${w.id}">
        <div class="sc-h">${w.title}<span class="ops"><a class="link" onclick="UI.toast('图表配置')">⚙</a><a class="link" onclick="UI.toast('已删除')">✕</a></span></div>
        <div id="w_${w.id}"></div></div>`).join('')}
    </div>
    <div class="card mt14"><div class="card-h">组件库（拖入大屏）</div><div class="card-b"><div class="flex wrap" style="gap:6px">
      ${['KPI 卡','折线图','柱状图','饼图','仪表盘','地图','表格','排行','文本卡','图片卡','视频卡'].map(c=>
      `<span class="dz-item" style="margin:0" onclick="UI.toast('已添加组件：${c}')">${c}</span>`).join('')}</div></div></div>`;
  },
  mount() { setTimeout(()=>{
    Store.get('dashboards')[0].widgets.forEach(w => { const el = document.getElementById('w_'+w.id); if (!el) return;
      if (w.type==='kpi') el.innerHTML = `<div style="font-size:26px;font-weight:800">${w.metric}<span class="trend ${w.trend.startsWith('-')?'down':'up'}">${w.trend}</span></div>`;
      else if (w.type==='line') Charts.line(el, Array.from({length:14},(_,i)=>'11/'+(i+14)), [{name:'订单',data:[62,58,71,66,80,74,88,84,92,87,96,91,105,112]}], {noDots:true,h:170});
      else if (w.type==='pie') Charts.pie(el, ['A1','A2','B','C'], [412,537,286,49], {h:150});
      else if (w.type==='bar') Charts.bar(el, ['孙十','吴九','钱七','冯二','郑一'], [182,164,150,132,118], {h:170});
      else if (w.type==='gauge') Charts.gauge(el, 96.5, {label:'流程准时率'});
    });
    // enable drag reorder
    let src=null;
    document.querySelectorAll('.screen-card').forEach(c => {
      c.ondragstart = e => { src=c; e.dataTransfer.setData('t','1'); };
      c.ondragover = e => { e.preventDefault(); c.classList.add('drag-over'); };
      c.ondragleave = () => c.classList.remove('drag-over');
      c.ondrop = e => { e.preventDefault(); c.classList.remove('drag-over');
        if (src && src!==c) { const grid=document.getElementById('screenGrid');
          grid.insertBefore(src, c); UI.toast('布局已调整（GB 6.2.6.2.1）'); } };
    });
  }, 60); },
  publish() { UI.modal({ title:'🔗 发布分享（GB 6.2.6.3.3）', body:UI.drawerForm([
    {key:'scope', label:'访问范围', type:'select', options:[{v:'pub',l:'公开链接'},{v:'org',l:'组织内'},{v:'role',l:'指定角色'}]},
    {key:'pwd', label:'访问密码', ph:'可选'},
    {key:'expire', label:'有效期', type:'select', options:[{v:'1d',l:'1 天'},{v:'7d',l:'7 天'},{v:'ever',l:'永久'}]}]),
    okText:'生成链接', onOk:()=>{ UI.closeModal();
      UI.modal({ title:'分享链接已生成', footer:false, body:`<div class="item mono">https://screen.hc.com/db1?t=7d&p=✓</div>
      <div class="muted">已配置访问控制；支持嵌入企业门户（GB 6.8.4.3）</div>` }); }});
  },
  theme() { UI.modal({ title:'🎨 大屏主题（GB 6.2.6.2.3）', footer:false, body:`
    <div class="swatch-row">${['#0f172a','#4f46e5','#16a34a','#0284c7','#d97706','#dc2626','#7c3aed'].map(c=>
      `<div class="swatch" style="background:${c}" onclick="UI.toast('主题已切换')"></div>`).join('')}</div>
    <div class="form-item mt14"><label>运行时多主题切换</label><div class="flex"><div class="switch on" onclick="this.classList.toggle('on')"></div><span class="muted">支持明暗一键切换</span></div></div>` });
  },
};
