/* ============ i18n — full zh-CN / en-US dictionary ============ */
const I18N = {
  'zh-CN': {
    'app.tagline':'AI 原生低代码平台','common.create':'新建','common.edit':'编辑','common.delete':'删除','common.save':'保存',
    'common.cancel':'取消','common.confirm':'确认','common.close':'关闭','common.search':'搜索','common.export':'导出',
    'common.import':'导入','common.refresh':'刷新','common.detail':'详情','common.status':'状态','common.actions':'操作',
    'common.name':'名称','common.desc':'描述','common.type':'类型','common.owner':'负责人','common.updated':'更新时间',
    'common.created':'创建时间','common.version':'版本','common.all':'全部','common.enable':'启用','common.disable':'停用',
    'common.test':'测试','common.publish':'发布','common.deploy':'部署','common.rollback':'回滚','common.download':'下载',
    'common.copy':'复制','common.save.ok':'保存成功','common.delete.ok':'删除成功','common.op.ok':'操作成功',
    'nav.group.dev':'开发中心','nav.group.run':'运行中心','nav.group.gov':'治理中心',
    'nav.home':'工作台','nav.apps':'应用管理','nav.org':'组织架构','nav.model':'数据建模','nav.form':'表单设计',
    'nav.flow':'逻辑编排','nav.bpm':'BPM 流程','nav.tasks':'任务待办','nav.inst':'流程实例','nav.report':'报表设计',
    'nav.screen':'数据大屏','nav.settings':'基础配置','nav.perm':'权限管理','nav.data':'数据管理','nav.code':'代码开发',
    'nav.sec':'安全合规','nav.ops':'运维部署','nav.msg':'消息中心',
    'home.hello':'下午好，张三','home.sub':'今天有 {n} 个待办任务，3 条系统消息',
    'home.todo':'我的待办','home.apps':'我的应用','home.metrics':'平台指标','home.quick':'快捷操作',
    'home.activity':'最近动态','home.gen5min':'AI 生成应用','home.metric.apps':'运行应用','home.metric.inst':'本月流程实例',
    'home.metric.sla':'SLA 达标率','home.metric.ai':'AI 生成次数','home.metric.uptime':'平台可用性',
  },
  'en-US': {
    'app.tagline':'AI-Native Low-Code Platform','common.create':'Create','common.edit':'Edit','common.delete':'Delete','common.save':'Save',
    'common.cancel':'Cancel','common.confirm':'Confirm','common.close':'Close','common.search':'Search','common.export':'Export',
    'common.import':'Import','common.refresh':'Refresh','common.detail':'Detail','common.status':'Status','common.actions':'Actions',
    'common.name':'Name','common.desc':'Description','common.type':'Type','common.owner':'Owner','common.updated':'Updated',
    'common.created':'Created','common.version':'Version','common.all':'All','common.enable':'Enable','common.disable':'Disable',
    'common.test':'Test','common.publish':'Publish','common.deploy':'Deploy','common.rollback':'Rollback','common.download':'Download',
    'common.copy':'Copy','common.save.ok':'Saved','common.delete.ok':'Deleted','common.op.ok':'Success',
    'nav.group.dev':'Development','nav.group.run':'Runtime','nav.group.gov':'Governance',
    'nav.home':'Workbench','nav.apps':'Applications','nav.org':'Organization','nav.model':'Data Modeling','nav.form':'Form Designer',
    'nav.flow':'Logic Flow','nav.bpm':'BPM Designer','nav.tasks':'My Tasks','nav.inst':'Instances','nav.report':'Report Designer',
    'nav.screen':'Dashboard','nav.settings':'Settings','nav.perm':'Permissions','nav.data':'Data Management','nav.code':'Code Dev',
    'nav.sec':'Security','nav.ops':'Operations','nav.msg':'Messages',
    'home.hello':'Good afternoon, Zhang San','home.sub':'You have {n} pending tasks and 3 system messages today',
    'home.todo':'My Tasks','home.apps':'My Applications','home.metrics':'Platform Metrics','home.quick':'Quick Actions',
    'home.activity':'Recent Activity','home.gen5min':'AI Generate App','home.metric.apps':'Running Apps','home.metric.inst':'Instances (Month)',
    'home.metric.sla':'SLA Compliance','home.metric.ai':'AI Generations','home.metric.uptime':'Uptime',
  }
};
I18N.t = function(key, vars) {
  const d = I18N[App?.lang || 'zh-CN'] || I18N['zh-CN'];
  let s = d[key] ?? I18N['zh-CN'][key] ?? key;
  if (vars) for (const k in vars) s = s.replace('{' + k + '}', vars[k]);
  return s;
};
