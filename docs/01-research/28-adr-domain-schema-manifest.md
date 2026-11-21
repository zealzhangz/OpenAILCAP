# ADR-S1-002：暂以分域 Schema + Manifest 作为 S3 优先验证架构

- 日期：2026-11-21
- 状态：**Proposed / Conditional**。S1 研究优先级决定，不是 S3 最终技术选型
- 关联假设：H01 H02 H03 H04 H05 H07 H08
- 输入：[综合研究 28](28-s1-synthesis-and-architecture-comparison.md)、[ADR-S1-001](17-provisional-adr-guarded-editing.md)、[模型层实验 05](05-roundtrip-results.md)、[Saltcorn 原生实测 18](18-saltcorn-sqlite-atomic-evidence.md)、[真实人机实验 27](27-real-deepseek-human-roundtrip-evidence.md)

## 决策问题

人工可视编辑、AI 配置修改及 AI 代码工件，是否必须共享一个巨大统一 Application IR？能否以**领域资源 Schema + 只包含关系和版本的 Application Manifest**保证引用、版本、发布与回滚，同时避免 DSL 膨胀？

### 决策

**允许将分域 Schema + Manifest 作为 S3 第一优先 PoC；保留全局 IR 作为同任务对照组；现阶段不采用“直接依赖传统平台原生设计器 + 旁路 AI 版本表”作为目标内核。**

这只是研究资源配置决策。无论 A/B 资源表达，所有写入必须经过可信命令入口的身份校验、权限、强制版本检查、引用完整性、事务提交及审计；若原生编辑器存在旁路，则 AI 应失败关闭，而非“尽力合并”。

## 候选方案

A. 全局 canonical IR：所有实体规约成统一中间对象并编译为运行时产物。优点为全局校验潜力；缺点为 DSL 类型膨胀、与原生设计器同步不可逆及定制代码投影成本。暂无平台级完整验证。

B. 分域 Schema + Manifest：领域独立演进，Manifest 记录资源 ID、Schema 版本、引用和 CodeArtifact 内容哈希；跨资源验证器和冻结发布快照组成一致性边界。优先验证，但未证明生产可靠性。

C. 原生平台 DB/Pack + Agent 侧 CAS：短期集成快，但 [18](18-saltcorn-sqlite-atomic-evidence.md)/[19](19-real-browser-edit-evidence.md) 已证明原生 Web/CLI 路径可绕过 Agent 版本表，旧数据会覆盖。作为目标方案否决，保留对照。

## 关键观测

- 内存 A/B 各 10/10 [05](05-roundtrip-results.md)；不能由此得出 B 优于 A。
- SQLite 中受控原子写可拒绝冲突，但 Saltcorn SQLite `withTransaction` 的研究版本没有实现有效 SQL 回滚；[18](18-saltcorn-sqlite-atomic-evidence.md) 为负对照。
- 真实 Chromium 旧表单覆盖 [19](19-real-browser-edit-evidence.md)；研究 Web+模拟 Agent 网关内可 409，原生 Web 不能自动继承该特性 [20](20-governed-http-evidence.md)。
- DeepSeek 在 6 题路由中 6/6、20/20 [26](26-deepseek-mode-route-evidence.md)，真实浏览器顺序非冲突修改 16/16 [27](27-real-deepseek-human-roundtrip-evidence.md)，都没有构成统一 IR 必要性的证明。

## 建议的最小领域契约（设计草案，未实现）

~~~json
{
  "manifestVersion": 1,
  "applicationId": "contracts-demo",
  "revision": 12,
  "resources": [
    {"id":"model.contract","kind":"data-model","schemaVersion":1,"revision":3,"contentHash":"sha256:<digest>"},
    {"id":"page.contract-list","kind":"page","schemaVersion":1,"revision":4,"dependsOn":["model.contract"],"contentHash":"sha256:<digest>"},
    {"id":"rule.amount-approval","kind":"business-rule","schemaVersion":1,"revision":5,"dependsOn":["model.contract","code.approval"],"contentHash":"sha256:<digest>"},
    {"id":"code.approval","kind":"code-artifact","schemaVersion":1,"revision":2,"gitCommit":"<commit>","contentHash":"sha256:<digest>"}
  ],
  "deployment": {"sourceRevision":12,"verifiedArtifactId":"<immutable-build-id>"}
}
~~~

上方 `<...>` 是占位符，不是已经运行或存在的对象。Manifest 可以是派生构建输入，但**不能作为未经监管外部人工修改的事实来源**。

建议命令契约：`getCapabilities` / `readResourceSnapshot` / `planChange` / `validateChange` / `applyPatch(expectedRevision,fingerprint,changeId)` / `verifyBuild` / `publishVerifiedSnapshot`。开发 Agent 不可直接拿 DB 管理员身份、生产 Shell 或可编辑任意路径的权限。

## S3 判据：用实验反驳本决策

固定同一合同业务和相同场景集，对全局 IR 与分域方案分别执行：
1. 一次人工建立数据模型、表单、工作流，模型服务关闭时可继续开发。
2. Agent 添加字段、重命名字段，验证所有页面/流程/权限/代码引用，不能残留悬挂引用。
3. 人工先改页面文案，Agent 再改代码工件，第二次人工编辑后都无损。
4. 对旧同字段编辑做两个真实 HTTP 并发请求：只能一方成功，另一方显式 409；不同字段无丢失。
5. 验证插件新资源类型、版本升级/回滚、失败构建与发布恢复；编排不可出现无验收的成功发布。
6. 记录每个方案的变更文件数、需新增核心代码处数、场景通过率、回滚成功率、人工工时、模型 Token/成本。

预先冻结评分和失败阈值，按准确性、安全性、迁移复杂度、版本可靠性排序，不按源码行数或者团队主观喜好裁决。如果 B 不能保持引用/发布原子性，应引入有限 canonical IR 或转 A；若两者皆不能支持统一写入，应优先修正写路径而非增大表示模型。

## 安全和许可证前置要求

所有人工/Agent/插件操作在同一可信服务端边界授权；凭据不得传给模型；危险代码执行通过隔离工作区并限资源；插件能力显式声明权限和副作用。ToolJet CE/EE 和 NocoBase v3 特殊许可须独立审核后才能讨论源码级复用。不得从 Saltcorn 研究性的 direct SQL 技巧推导正式适配方案。

## 重新评估触发器

- S3 对照发现领域资源引用一致性显著弱于统一 IR；
- 出现无法覆盖的原生设计器旁路写入；
- 插件新增必须频繁修改核心导致扩展性退化；
- 代码/Schema 发布快照无法原子冻结、恢复；
- 许可证或安全边界否定具体内核集成路线。

**目前结论：选下一步验证路径，而非宣告架构已证明。**
