/* ============ Store — mock data for ALL 14 modules (localStorage persisted) ============ */
const Store = {
  data: {},
  load() {
    const raw = localStorage.getItem('oac_store_v2');
    if (raw) { try { this.data = JSON.parse(raw); return; } catch(e){} }
    this.data = this.seed();
    this.save();
  },
  save() { localStorage.setItem('oac_store_v2', JSON.stringify(this.data)); },
  reset() { localStorage.removeItem('oac_store_v2'); this.load(); },

  seed() {
    const now = '2026-11-28';
    return {
      /* ---- M1 Applications ---- */
      apps: [
        { id:'app_001', name:'订单管理系统', desc:'订单全生命周期管理：录入→审批→发货→结算', type:'form', icon:'📦', status:'published', version:'v2.3.1', owner:'张三', updated:'2026-11-27 15:20', tags:['电商','核心'], env:{dev:'v2.3.1',test:'v2.3.1',prod:'v2.3.0'} },
        { id:'app_002', name:'请假审批', desc:'员工请假申请与多级审批', type:'workflow', icon:'🏖️', status:'published', version:'v1.4.0', owner:'王五', updated:'2026-11-26 09:10', tags:['HR'], env:{dev:'v1.4.0',test:'v1.4.0',prod:'v1.4.0'} },
        { id:'app_003', name:'客户 CRM', desc:'客户档案、跟进记录、商机管理', type:'form', icon:'👥', status:'draft', version:'v0.9.2', owner:'李四', updated:'2026-11-25 18:40', tags:['销售'], env:{dev:'v0.9.2',test:'—',prod:'—'} },
        { id:'app_004', name:'库存管理', desc:'入库/出库/盘点/预警', type:'form', icon:'🏬', status:'published', version:'v1.1.5', owner:'赵六', updated:'2026-11-24 11:05', tags:['供应链'], env:{dev:'v1.1.5',test:'v1.1.4',prod:'v1.1.4'} },
        { id:'app_005', name:'采购合同审批', desc:'合同起草→法务→财务→签署', type:'workflow', icon:'📝', status:'published', version:'v2.0.0', owner:'孙十', updated:'2026-11-23 14:30', tags:['法务','财务'], env:{dev:'v2.0.0',test:'v2.0.0',prod:'v2.0.0'} },
      ],
      appVersions: [
        { appId:'app_001', list:[
          { v:'v2.3.1', time:'2026-11-27 15:20', by:'李四', note:'字段校验增强', type:'AI' },
          { v:'v2.3.0', time:'2026-11-20 10:02', by:'张三', note:'新增发票子表', type:'人工' },
          { v:'v2.2.4', time:'2026-11-12 16:44', by:'张三', note:'审批条件调整', type:'AI' } ] },
      ],
      artifacts: [
        { id:'art_001', appId:'app_001', version:'v2.3.1', size:'4.2 MB', time:'2026-11-27 15:21', schema:true, seed:true, assets:true, checksum:'sm3:a3f8…9c2d' },
        { id:'art_002', appId:'app_002', version:'v1.4.0', size:'2.8 MB', time:'2026-11-26 09:12', schema:true, seed:false, assets:true, checksum:'sm3:7b1e…44fa' },
      ],
      /* ---- M2 Organization ---- */
      depts: [
        { id:'d1', name:'华创科技', code:'HC', parentId:null, manager:'e1' },
        { id:'d2', name:'销售部', code:'HC-XS', parentId:'d1', manager:'e4' },
        { id:'d3', name:'销售一部', code:'HC-XS-01', parentId:'d2', manager:'e6' },
        { id:'d4', name:'技术部', code:'HC-JS', parentId:'d1', manager:'e2' },
        { id:'d5', name:'人力资源部', code:'HC-HR', parentId:'d1', manager:'e3' },
        { id:'d6', name:'财务部', code:'HC-CW', parentId:'d1', manager:'e8' },
      ],
      positions: [
        { id:'p1', name:'总经理', level:'M5', template:'tpl_ceo' }, { id:'p2', name:'部门总监', level:'M4', template:'tpl_dir' },
        { id:'p3', name:'销售主管', level:'M3', template:'tpl_sales_lead' }, { id:'p4', name:'销售专员', level:'M1', template:'tpl_sales' },
        { id:'p5', name:'技术总监', level:'M4', template:'tpl_cto' }, { id:'p6', name:'工程师', level:'M2', template:'tpl_dev' },
        { id:'p7', name:'HR 专员', level:'M2', template:'tpl_hr' }, { id:'p8', name:'财务经理', level:'M3', template:'tpl_fin' },
      ],
      employees: [
        { id:'e1', name:'周百', code:'E001', dept:'d1', pos:'p1', mgr:null, email:'zhoubai@hc.com', phone:'138****0001', active:true },
        { id:'e2', name:'李四', code:'E002', dept:'d4', pos:'p5', mgr:'e1', email:'lisi@hc.com', phone:'139****0002', active:true },
        { id:'e3', name:'王五', code:'E003', dept:'d5', pos:'p2', mgr:'e1', email:'wangwu@hc.com', phone:'137****0003', active:true },
        { id:'e4', name:'赵六', code:'E004', dept:'d2', pos:'p2', mgr:'e1', email:'zhaoliu@hc.com', phone:'136****0004', active:true },
        { id:'e5', name:'钱七', code:'E005', dept:'d4', pos:'p6', mgr:'e2', email:'qianqi@hc.com', phone:'135****0005', active:true },
        { id:'e6', name:'孙十', code:'E006', dept:'d3', pos:'p3', mgr:'e4', email:'sunshi@hc.com', phone:'134****0006', active:true },
        { id:'e7', name:'吴九', code:'E007', dept:'d3', pos:'p4', mgr:'e6', email:'wujiu@hc.com', phone:'133****0007', active:true },
        { id:'e8', name:'郑一', code:'E008', dept:'d6', pos:'p8', mgr:'e1', email:'zhengyi@hc.com', phone:'132****0008', active:true },
        { id:'e9', name:'冯二', code:'E009', dept:'d5', pos:'p7', mgr:'e3', email:'fenger@hc.com', phone:'131****0009', active:true },
      ],
      empChanges: [
        { id:'c1', emp:'e7', type:'transfer', from:'销售一部', to:'销售一部', note:'岗位由销售专员 → 销售主管(代理)', time:'2026-11-20', by:'赵六' },
        { id:'c2', emp:'e5', type:'promotion', from:'工程师 M1', to:'工程师 M2', note:'年度晋升', time:'2026-10-15', by:'李四' },
      ],
      /* ---- M3 Data models ---- */
      models: [
        { id:'m1', name:'Order', display:'订单表', appId:'app_001', x:30, y:20,
          fields:[
            {name:'id', type:'string', pk:true, req:true, len:32}, {name:'order_no', type:'string', req:true, unique:true, len:32},
            {name:'customer_id', type:'string', req:true, ref:'Customer'}, {name:'amount', type:'decimal', req:true, prec:'10,2'},
            {name:'status', type:'enum', req:true, dict:'order_status'}, {name:'order_date', type:'datetime', req:true},
            {name:'remark', type:'text'} ] },
        { id:'m2', name:'Customer', display:'客户表', appId:'app_001', x:560, y:30,
          fields:[
            {name:'id', type:'string', pk:true, req:true, len:32}, {name:'name', type:'string', req:true, len:64},
            {name:'level', type:'enum', dict:'customer_level'}, {name:'phone', type:'string', encrypt:true},
            {name:'email', type:'string'} ] },
        { id:'m3', name:'OrderLine', display:'订单明细', appId:'app_001', x:300, y:270,
          fields:[
            {name:'id', type:'string', pk:true, req:true}, {name:'order_id', type:'string', req:true, ref:'Order'},
            {name:'sku', type:'string', req:true}, {name:'qty', type:'int', req:true}, {name:'price', type:'decimal', req:true} ] },
        { id:'m4', name:'LeaveRequest', display:'请假单', appId:'app_002', x:40, y:300,
          fields:[
            {name:'id', type:'string', pk:true}, {name:'emp_id', type:'string', req:true, ref:'Employee'},
            {name:'days', type:'int', req:true}, {name:'type', type:'enum', dict:'leave_type'}, {name:'reason', type:'text', req:true} ] },
      ],
      relations: [ {id:'r1', from:'m1', f:'customer_id', to:'m2', t:'id', type:'N:1'}, {id:'r2', from:'m3', f:'order_id', to:'m1', t:'id', type:'N:1'} ],
      dicts: [
        { id:'dict1', code:'order_status', name:'订单状态', type:'list', items:[
          {v:'draft', zh:'草稿', en:'Draft', sort:1}, {v:'confirmed', zh:'已确认', en:'Confirmed', sort:2},
          {v:'shipped', zh:'已发货', en:'Shipped', sort:3}, {v:'completed', zh:'已完成', en:'Completed', sort:4} ] },
        { id:'dict2', code:'customer_level', name:'客户等级', type:'tree', items:[
          {v:'A', zh:'A 类-战略客户', en:'A-Strategic', children:[{v:'A1', zh:'年框客户', en:'Annual'},{v:'A2', zh:'重点客户', en:'Key'}]},
          {v:'B', zh:'B 类-普通客户', en:'B-Regular'} ] },
        { id:'dict3', code:'leave_type', name:'请假类型', type:'list', items:[
          {v:'annual', zh:'年假', en:'Annual'},{v:'sick', zh:'病假', en:'Sick'},{v:'personal', zh:'事假', en:'Personal'},{v:'marriage', zh:'婚假', en:'Marriage'} ] },
      ],
      /* ---- M4 Forms ---- */
      forms: [
        { id:'f1', appId:'app_001', name:'订单创建表单', fields:[
          {id:'x1', label:'订单编号', field:'order_no', type:'text', req:true, span:12, ai:true},
          {id:'x2', label:'客户', field:'customer_id', type:'select', req:true, span:12, dictFrom:'Customer'},
          {id:'x3', label:'订单金额', field:'amount', type:'number', req:true, span:12, rules:['positive','max:9999999']},
          {id:'x4', label:'下单日期', field:'order_date', type:'date', req:true, span:12},
          {id:'x5', label:'备注', field:'remark', type:'textarea', span:24},
          {id:'x6', label:'发票抬头', field:'invoice', type:'text', span:12, showIf:'amount>=100'} ] },
      ],
      /* ---- M5 Logic flows ---- */
      logicFlows: [
        { id:'lf1', name:'订单创建校验', appId:'app_001', nodes:[
          {id:'n1', type:'event', label:'表单提交', x:30, y:40},
          {id:'n2', type:'condition', label:'金额>10000?', x:230, y:40, expr:'${amount} > 10000'},
          {id:'n3', type:'data', label:'写入订单', x:430, y:-30, op:'insert'},
          {id:'n4', type:'api', label:'通知审批人', x:430, y:120, method:'POST', url:'/api/notify'},
          {id:'n5', type:'end', label:'返回结果', x:640, y:40} ],
          edges:[{f:'n1',t:'n2'},{f:'n2',t:'n3',when:'false'},{f:'n2',t:'n4',when:'true'},{f:'n3',t:'n5'},{f:'n4',t:'n5'}] },
      ],
      /* ---- M6 BPM ---- */
      bpmDefs: [
        { id:'bp1', name:'订单审批流程', appId:'app_001', version:'v3', status:'published', sla:'4h',
          nodes:[
            {id:'s1', type:'start', label:'开始', x:20, y:120},
            {id:'t1', type:'user', label:'销售主管审批', x:170, y:120, assignee:'mgr:direct', sla:'4h', actions:['approve','reject','delegate','cc']},
            {id:'g1', type:'gateway', label:'金额>=10万?', x:340, y:120, expr:'${amount} >= 100000'},
            {id:'t2', type:'user', label:'总经理审批', x:500, y:30, assignee:'pos:p1', sla:'8h'},
            {id:'t3', type:'user', label:'仓库验收', x:500, y:210, assignee:'dept:d3', sla:'24h'},
            {id:'e1', type:'end', label:'结束', x:680, y:120} ],
          edges:[{f:'s1',t:'t1'},{f:'t1',t:'g1'},{f:'g1',t:'t2',when:'是'},{f:'g1',t:'t3',when:'否'},{f:'t2',t:'e1'},{f:'t3',t:'e1'}] },
      ],
      /* ---- Tasks & instances ---- */
      tasks: [
        { id:'tk1', title:'订单 SO-2026-1101 审批', app:'app_001', node:'销售主管审批', from:'吴九', pri:'high', sla:'3h12m', state:'pending', amount:152000 },
        { id:'tk2', title:'请假单 LV-2026-088 审批', app:'app_002', node:'部门总监审批', from:'冯二', pri:'mid', sla:'1d', state:'pending' },
        { id:'tk3', title:'合同 CT-2026-032 用印审批', app:'app_005', node:'财务经理审批', from:'孙十', pri:'high', sla:'超期 2h', state:'pending' },
        { id:'tk4', title:'订单 SO-2026-1098 审批', app:'app_001', node:'销售主管审批', from:'吴九', pri:'low', sla:'-', state:'done', result:'approved' },
        { id:'tk5', title:'请假单 LV-2026-085 审批', app:'app_002', node:'部门总监审批', from:'钱七', pri:'mid', sla:'-', state:'done', result:'rejected' },
        { id:'tk6', title:'采购单 PO-2026-220 审批', app:'app_004', node:'仓库验收', from:'系统自动', pri:'low', sla:'-', state:'forwarded' },
      ],
      instances: [
        { id:'pi1', no:'PI-2026-1101', def:'订单审批流程', starter:'吴九', start:'11-28 09:12', state:'运行中', node:'总经理审批', elapsed:'2h05m', sla:'ok', steps:[
          {node:'开始', state:'done', time:'09:12', by:'系统'},{node:'销售主管审批', state:'done', time:'09:31', by:'孙十 ✓同意'},
          {node:'金额>=10万?', state:'done', time:'09:31', by:'条件:是'},{node:'总经理审批', state:'running', time:'09:31起', by:'周百'} ] },
        { id:'pi2', no:'PI-2026-1099', def:'订单审批流程', starter:'吴九', start:'11-27 16:40', state:'已完成', node:'结束', elapsed:'5h32m', sla:'ok', steps:[
          {node:'开始', state:'done'},{node:'销售主管审批', state:'done', by:'孙十 ✓'},{node:'仓库验收', state:'done', by:'仓库组 ✓'},{node:'结束', state:'done'} ] },
        { id:'pi3', no:'PI-2026-1087', def:'请假审批', starter:'冯二', start:'11-26 10:02', state:'已挂起', node:'部门总监审批', elapsed:'2d 04h', sla:'overdue', steps:[
          {node:'开始', state:'done'},{node:'直属主管审批', state:'done', by:'王五 ✓'},{node:'部门总监审批', state:'running', by:'等待 赵六'} ] },
      ],
      /* ---- M7 Reports ---- */
      reports: [
        { id:'rp1', name:'月度销售统计', type:'table', source:'Order', time:'2026-11-20', charts:['bar','line'] },
        { id:'rp2', name:'客户等级分布', type:'pie', source:'Customer', time:'2026-11-18' },
        { id:'rp3', name:'订单趋势(近30天)', type:'line', source:'Order', time:'2026-11-15' },
      ],
      dashboards: [
        { id:'db1', name:'销售作战室', widgets:[
          {id:'w1', type:'kpi', title:'本月销售额', span:3, metric:'¥ 8,462,300', trend:'+12.4%'},
          {id:'w2', type:'kpi', title:'订单数', span:3, metric:'1,284', trend:'+8.2%'},
          {id:'w3', type:'kpi', title:'平均客单价', span:3, metric:'¥ 6,590', trend:'-2.1%'},
          {id:'w4', type:'kpi', title:'SLA 达标率', span:3, metric:'96.5%', trend:'+1.3%'},
          {id:'w5', type:'line', title:'近 30 天订单趋势', span:8},
          {id:'w6', type:'pie', title:'客户等级分布', span:4},
          {id:'w7', type:'bar', title:'销售员业绩 Top5', span:6},
          {id:'w8', type:'gauge', title:'流程准时率', span:6} ] },
      ],
      /* ---- M9 settings ---- */
      menus: [
        {id:'mn1', label:'销售工作台', icon:'🏠', path:'/sales', roles:['all']},
        {id:'mn2', label:'订单管理', icon:'📦', path:'/orders', roles:['sales','admin'], children:[
          {id:'mn21', label:'订单列表', path:'/orders/list'},{id:'mn22', label:'创建订单', path:'/orders/new'},
          {id:'mn23', label:'订单报表', path:'/orders/report', roles:['admin','sales_lead']} ] },
        {id:'mn3', label:'审批中心', icon:'✅', path:'/approve', roles:['all']},
        {id:'mn4', label:'系统管理', icon:'⚙️', path:'/admin', roles:['admin']},
      ],
      params: [
        {id:'pp1', code:'order.max_amount', name:'单笔订单上限', value:'9999999', group:'业务', desc:'超过需总经理审批'},
        {id:'pp2', code:'notify.email.switch', name:'邮件通知开关', value:'on', group:'通知'},
        {id:'pp3', code:'session.timeout', name:'会话超时(分钟)', value:'30', group:'安全'},
        {id:'pp4', code:'ai.model', name:'默认 AI 模型', value:'claude-sonnet', group:'AI'},
      ],
      jobs: [
        {id:'jb1', name:'每日报表生成', cron:'0 6 * * *', state:'on', last:'11-28 06:00 ✓', next:'11-29 06:00'},
        {id:'jb2', name:'库存低量扫描', cron:'*/30 * * * *', state:'on', last:'11-28 16:30 ✓', next:'11-28 17:00'},
        {id:'jb3', name:'SLA 超期提醒', cron:'0 9,14 * * 1-5', state:'on', last:'11-28 14:00 ✓', next:'11-28(工作日)'},
        {id:'jb4', name:'历史数据归档', cron:'0 3 1 * *', state:'off', last:'12-01 03:00', next:'-'},
      ],
      msgTemplates: [
        {id:'mt1', code:'approve.wait', name:'审批待办提醒', channel:'站内信+邮件', state:'on'},
        {id:'mt2', code:'approve.overdue', name:'审批超期告警', channel:'站内信+短信', state:'on'},
        {id:'mt3', code:'instance.done', name:'流程完成通知', channel:'站内信', state:'on'},
      ],
      /* ---- M10 permissions ---- */
      roles: [
        {id:'r1', name:'平台管理员', code:'admin', users:2, sys:true},
        {id:'r2', name:'租户管理员', code:'tenant_admin', users:5},
        {id:'r3', name:'应用开发者', code:'developer', users:12},
        {id:'r4', name:'审批人', code:'approver', users:26},
        {id:'r5', name:'普通用户', code:'user', users:210},
      ],
      permResources: ['应用管理','表单设计','数据建模','流程设计','数据查看','数据编辑','数据删除','数据导出','审批处理','系统配置','审计日志'],
      permMatrix: { '平台管理员':[1,1,1,1,1,1,1,1,1,1,1], '租户管理员':[1,1,1,1,1,1,0,1,1,1,1], '应用开发者':[1,1,1,1,1,0,0,1,0,0,0], '审批人':[0,0,0,0,1,1,0,0,1,0,0], '普通用户':[0,0,0,0,1,0,0,0,0,0,0] },
      apiKeys: [
        {id:'k1', name:'开放 API-订单同步', key:'oac_live_3f8a***9c2', scope:'app:read,app:write', created:'2026-10-01', last:'11-27', state:'on'},
        {id:'k2', name:'企业微信推送', key:'oac_live_7b1e***44f', scope:'msg:send', created:'2026-09-15', last:'11-28', state:'on'},
      ],
      /* ---- M11 data rows ---- */
      dataRows: {
        m1: [
          {id:'SO-2026-1101', order_no:'SO-2026-1101', customer:'华辰集团(A1)', amount:'152,000.00', status:'已确认', date:'11-28 09:12'},
          {id:'SO-2026-1100', order_no:'SO-2026-1100', customer:'恒信贸易(B)', amount:'12,800.00', status:'草稿', date:'11-28 08:40'},
          {id:'SO-2026-1099', order_no:'SO-2026-1099', customer:'蓝天科技(A2)', amount:'8,600.00', status:'已完成', date:'11-27 16:40'},
          {id:'SO-2026-1098', order_no:'SO-2026-1098', customer:'明达制造(B)', amount:'45,300.00', status:'已发货', date:'11-27 14:02'},
          {id:'SO-2026-1097', order_no:'SO-2026-1097', customer:'华辰集团(A1)', amount:'230,000.00', status:'已确认', date:'11-26 11:18'},
        ],
        m2: [
          {id:'C-001', name:'华辰集团', level:'A1', phone:'138****3211', email:'contact@huachen.com'},
          {id:'C-002', name:'蓝天科技', level:'A2', phone:'139****5520', email:'bd@lantian.cn'},
          {id:'C-003', name:'恒信贸易', level:'B', phone:'137****8834', email:'sales@hengxin.com'},
        ] },
      /* ---- M13 security ---- */
      kmsKeys: [
        {id:'km1', alg:'SM2', use:'签名/密钥交换', version:'v1', created:'2026-06-01', expire:'2029-06-01', state:'on'},
        {id:'km2', alg:'SM4', use:'字段/传输加密', version:'v2', created:'2026-09-01', expire:'2026-12-01(90天轮换)', state:'on'},
        {id:'km3', alg:'SM3', use:'完整性校验', version:'v1', created:'2026-06-01', expire:'长期', state:'on'},
      ],
      maskRules: [
        {id:'ms1', field:'phone', label:'手机号', rule:'保留前3后2', sample:'138****0001', on:true},
        {id:'ms2', field:'idCard', label:'身份证', rule:'保留前3后1', sample:'310**********5', on:true},
        {id:'ms3', field:'bankCard', label:'银行卡', rule:'仅显示后4位', sample:'************8888', on:true},
        {id:'ms4', field:'email', label:'邮箱', rule:'保留前3字符', sample:'con***@hc.com', on:false},
      ],
      auditLogs: [
        {id:'al1', time:'11-28 16:42', user:'张三', action:'修改', res:'表单[订单创建表单] 字段[金额] 校验规则', ip:'10.2.3.11', level:'info', hash:'sm3:8f2a…c31'},
        {id:'al2', time:'11-28 15:20', user:'李四', action:'AI生成', res:'订单管理系统 v2.3.1 字段推荐(5项采纳3项)', ip:'10.2.3.15', level:'info', hash:'sm3:2b7e…9d4'},
        {id:'al3', time:'11-28 14:03', user:'钱七', action:'访问拒绝', res:'尝试导出[客户表]数据(无权限)', ip:'10.4.1.88', level:'warn', hash:'sm3:5c11…e82'},
        {id:'al4', time:'11-28 11:30', user:'王五', action:'登录', res:'SSO 登录成功(MFA)', ip:'10.2.5.2', level:'info', hash:'sm3:d904…17a'},
        {id:'al5', time:'11-28 09:15', user:'系统', action:'部署', res:'app_001 v2.3.1 → prod (灰度10%)', ip:'internal', level:'info', hash:'sm3:aa3f…b25'},
      ],
      /* ---- M14 ops ---- */
      deployments: [
        {id:'dp1', app:'app_001', ver:'v2.3.1', env:'prod', mode:'灰度 10%', time:'11-28 09:15', state:'成功', by:'流水线', canRollback:true},
        {id:'dp2', app:'app_001', ver:'v2.3.1', env:'test', mode:'全量', time:'11-27 18:00', state:'成功', by:'流水线', canRollback:true},
        {id:'dp3', app:'app_002', ver:'v1.4.0', env:'prod', mode:'全量', time:'11-26 09:20', state:'成功', by:'王五', canRollback:true},
        {id:'dp4', app:'app_003', ver:'v0.9.2', env:'dev', mode:'手动', time:'11-25 18:45', state:'成功', by:'李四', canRollback:false},
      ],
      alerts: [
        {id:'ar1', level:'error', title:'订单审批 P99 延迟 1.2s(阈值 800ms)', time:'11-28 15:02', state:'firing', source:'api-gateway'},
        {id:'ar2', level:'warn', title:'app_003 测试环境 CPU 82%', time:'11-28 13:40', state:'firing', source:'k8s'},
        {id:'ar3', level:'warn', title:'SM4 密钥 12 月 1 日到期，请轮换', time:'11-28 09:00', state:'ack', source:'kms'},
        {id:'ar4', level:'info', title:'v2.3.1 灰度 10% 错误率 0.02%(正常)', time:'11-28 10:00', state:'resolved', source:'canary'},
      ],
      logStats: { today:'1,284,392', err:'412', warn:'2,306', retained:'90 天' },
    };
  },
  get(k) { return this.data[k]; },
  set(k, v) { this.data[k] = v; this.save(); },
  find(k, id) { return (this.data[k]||[]).find(x => x.id === id); },
  push(k, item) { this.data[k].push(item); this.save(); },
  remove(k, id) { this.data[k] = this.data[k].filter(x => x.id !== id); this.save(); },
  update(k, id, patch) { const i = this.data[k].findIndex(x=>x.id===id); if(i>-1){ Object.assign(this.data[k][i], patch); this.save(); } },
};
