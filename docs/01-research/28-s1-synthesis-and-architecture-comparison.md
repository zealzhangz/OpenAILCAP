# S1 开源低代码平台综合深度研究与架构候选比较（2026-11-21）

> 状态：S1 综合分析交付；不是 G1 通过证明或 S3 技术架构定稿。基准仓库 commit: `07cf929471f7f3bba9f93579916b7da4dea6ca33`；主要输入为 [能力矩阵](09-capability-matrix.md)、[证据台账](02-evidence.md)、[G1 缺口](12-g1-gap-review.md) 和 14—27 号原生实验报告。

## 1. 研究问题、取证边界

OpenAILCAP 的决定性问题不是“哪款低代码产品功能最多”，而是如何在**完全不使用 AI 的人工模式**、AI 配置开发和 AI 自定义代码三种模式之间共用应用资源、权限、版本、验证及部署语义。

证据等级：S0=该实验在 GitHub Actions 中真实执行且有独立断言；S1=固定源码位置/测试静态阅读；S2=官方文档；UNK=尚未验证。下面对外部四平台**只采用源码/官方文档证据**，不冒称实际部署。Saltcorn 是第五个 S0 纵向切片，不表示其产品已满足 OpenAILCAP 全部要求。

## 2. 四个平台和 Saltcorn 的可追溯比较

| 项目 | 最值得参考的机制 | 证据 | 主要缺口/反例 | 对 OpenAILCAP 的判断 |
|---|---|---|---|---|
| ToolJet + tooljet-mcp | 结构化 appPlan、plan lint/diff/readback、Code Sync 的内容哈希检查，服务端 Page/Event/Version 实体 | [固定 SHA 源码矩阵](09-capability-matrix.md#tj-plan)、[同步链](04-tooljet-sync-trace.md) S1 | CE Code Mode 服务端是 stub，EE 实现不能作为可自由复用的开放实现；局部同步检查≠全渠道强一致性 | 借鉴“模型提出有界计划→校验→执行→读回”，不绑定其 EE 代码 |
| Appsmith | widget registry、unpublished/published page 分离、人工可视配置 | [组件注册](09-capability-matrix.md#as-widget)、[Page 源码](09-capability-matrix.md#as-page) S1 | 尚无其 AI 自主开发、人工代码 roundtrip 或生产隔离实测 | 借鉴设计态/发布态分离、按需组件注册；人工路径作为独立一等开发模式 |
| Budibase | Builder 数据绑定上下文、服务端 Automation actions 注册 | [绑定源码](09-capability-matrix.md#bd-bind)、[actions](09-capability-matrix.md#bd-autom) S1 | 业务 Agent 的执行能力≠开发 Agent 修改模型/源码能力；未实测完整版本冲突 | 借鉴明确绑定上下文、能力注册；禁止把业务自动化视为开发编排 |
| NocoBase v3 Core | define/resolve plugin、Agent Runner/job worker、插件/服务分层 | [插件定义](09-capability-matrix.md#nb-define)、[Runner](09-capability-matrix.md#nb-runner) S1 | v3 与 v2 能力不可混同；官方安装模板请求 E530；Runner 隔离不等于完整容器沙箱；LICENSE.txt 附加条款需法律审核 | 借鉴插件生命周期与 Runner 责任边界，不默认将其作为可嵌入内核 |
| Saltcorn 1.7.0-beta.5 | 原生 Table/Field/View、Pack、Validate/Insert Trigger、真实浏览器设计器和 HTTP/SQLite | [14—27 号报告](14-saltcorn-real-platform.md) S0，固定上游 SHA `515254bee5a98df70530cc59846b1df02d5db350` | 真实旧 Web 表单覆盖、旧 Pack 覆盖、sqlite withTransaction 异常不回滚、Agent 侧 CAS 被原生写入绕过；正式合同基准仍 0/18 | 最有价值的是**研究实证基线和负对照**；不推荐原封不动作为 OpenAILCAP 写入内核 |

说明：矩阵的 SRC、DOC、BND、? 不等于真实平台通过，原有 22 项四平台能力矩阵不应转化为加权产品排行榜。Saltcorn 的 S0 通过项也不能直接填入冻结 TC01—TC18。

## 3. 首尾打通的数据流与真实断点

~~~mermaid
flowchart LR
  R[业务需求] --> A[AI: 受限工具/模式提案]
  U[人工设计器] --> C[统一命令入口: 待建设]
  P[插件] --> C
  A --> C
  C --> X{身份/授权/Schema/引用/版本检查}
  X -->|冲突或越权| E[显式拒绝+审计]
  X -->|接受| M[分域资源与代码工件]
  M --> V[独立测试/安全门禁]
  V --> D[草稿/发布版本]
  D --> T[隔离运行时]
  T --> O[物理数据+HTTP+浏览器读回]
~~~

真实实现中，Saltcorn 自带的浏览器编辑器、原生 Field.update 和研究 Agent 侧 CAS **尚未共用 C 节点**；上图是建议架构，不是既有部署图。

- 原生场景切片：[15](15-native-contract-platform-evidence.md) 用 Pack/Table/View/REST 证明实际数据和页面写入。
- 负例：[16](16-saltcorn-roundtrip-evidence.md) 旧 Pack 静默覆盖不相关字段；[18](18-saltcorn-sqlite-atomic-evidence.md) 原生事务包装未实际回滚且绕过外部版本表；[19](19-real-browser-edit-evidence.md) 两个 Chromium 标签页旧表单覆盖。
- 局部正例：[20](20-governed-http-evidence.md) 研究 HTTP 网关内受保护的 Web/Agent 均能 409 拒绝旧版本，但 Saltcorn 原生编辑器未接入该网关。
- 业务约束：[21](21-saltcorn-native-workflow-evidence.md)、[22](22-native-identity-approval-evidence.md) 用真正 Saltcorn Trigger、身份会话/CSRF 和物理业务记录验证金额阈值与审批。
- Agent 约束：[23](23-agent-tool-contract-evidence.md)、[24](24-durable-agent-calls-evidence.md) 证明受限命令、授权/审计及部分持久调用去重机制可运行；未知写入结果不能盲目重试。
- 真正模型参与：[25](25-deepseek-real-tool-call.md)、[26](26-deepseek-mode-route-evidence.md)、[27](27-real-deepseek-human-roundtrip-evidence.md) 分别验证只读工具、6/6 模式选择+20/20 原生断言、真实浏览器→DeepSeek→浏览器 16/16 顺序交接。三个证据都**没有证明模型自主生成代码并自动交付应用**。

## 4. 架构候选：第一性原理与 ATAM 取舍

共同不变量：资源唯一 ID、明确所属 app、Schema version、revision/fingerprint、可追踪引用、资源级权限、可复原历史、不可覆盖的人工变更、配置/源码共同版本标记、运行结果独立验收。

### 候选 A：单体全局 Application IR（强规范化）

所有 Table/Page/Workflow/Permission/CodeArtifact 先汇入统一 IR，人工与 Agent 编辑 IR；平台按目标运行时编译/投影。

优势：跨领域引用分析、统一发布快照和跨运行时迁移在理论上更直观。代价：需要为页面设计器、流程、动态插件和自定义代码创建长期演化的超大中间模型；向原生平台反向同步会产生语义损失和双写一致性难题。模型级 A/B [报告 05](05-roundtrip-results.md) 证明 10/10 测试可跑，**不能证明全局 IR 的长期可扩展性**。

### 候选 B：分域 Schema + Application Manifest（轻规范）

Table/Page/Workflow/Rule/Permission 保留版本化领域 Schema，代码使用 Git/内容哈希工件；Manifest 只保存资源 ID、依赖、版本、接口能力与发布绑定。AI/人工通过统一领域命令提交局部 Patch，而不是直接更改数据库。

优势：最小可行内核、领域可独立升级、不强迫将任意代码翻译成 DSL；与 ToolJet 计划、Appsmith 页面、Budibase binding、NocoBase plugin、Saltcorn 原生对象的观察更相容。代价：跨 Schema 的引用一致性、全应用发布冻结与转换版本需要显式事务/校验器。SQLite 分域结构和真实 Saltcorn 适配实验仅给出**机制可行性**，尚未完成完全对照。

### 候选 C：完全依赖某现有低代码产品原生数据库/设计器 + 外挂 Agent

优势：最短时间得到界面/CRUD。已被真实反例限制：**原生可视编辑器允许绕过 Agent 侧版本表**，导致同字段旧表单静默覆盖；并且 Code Mode/Runner 等特性可能受版本和许可证边界影响。若不修改所有原生写入口，不能作为满足双向编辑安全要求的目标架构。可用作隔离验证底座，不可当成已过门禁的核心设计。

| ATAM 场景/判据 | A 全局 IR | B 分域+Manifest | C 原生系统外挂 |
|---|---|---|---|
| 人工→AI→人工无丢失 | 必须新增统一强制 CAS，IR 自身不解决 | 必须新增统一强制 CAS | 已有绕过与旧页面覆盖反例 |
| 混合配置/代码 | 需 IR 覆盖代码引用与构建版本 | Manifest 显式版本绑定代码工件 | 产品专有扩展点较强耦合 |
| 新增插件无需改核心 | IR 类型兼容/迁移风险 | 独立 Schema+能力清单，需一致性校验 | 取决于上游插件契约 |
| 初期实现成本 | 高（推断，未测） | 中（推断，未测） | 初期低、治理改造不明（推断） |
| 跨运行时可移植 | 潜在较强，转换未证实 | 潜在中等，适配器未证实 | 依赖产品实现 |
| 安全完整性 | 与 IR 无直接因果，需要命令与执行隔离 | 同左 | 原生路径绕过须封堵 |
| 目前可作为首选研究路线 | 保留对照，不定稿 | **优先进入 S3 可证伪 PoC** | **仅作研究对照平台** |

**暂定判断：B 为风险较小的待验证路线，并非已证明性能或总成本优于 A。** G1 可以选择后续 PoC 优先级，不应越权替代 G3 的最终 IR 架构决策。

## 5. 机制可借鉴 / 不能复用 / 需要自主创新

**可借鉴（机制，不暗示复制授权）：**
1. 结构化能力发现、计划 diff、lint、readback（ToolJet MCP）。
2. Widget registry 和设计/发布快照分离（Appsmith）。
3. 数据绑定上下文与 Automation Action 注册（Budibase）。
4. Plugin manifest/runner 工作职责和凭据边界（NocoBase v3）。
5. 低代码元数据+原生业务触发器，受认证会话影响的命令入口（Saltcorn 实测）。
6. 有界工具协议、独立执行器、持久审计、外部状态验证（本仓库研究）。

**不得直接复用或假设成立：**
1. ToolJet CE Code Mode（EE 服务端证据及许可边界）。
2. NocoBase v3 Core 的无条件平台再发行许可；需逐条法务审查。
3. Saltcorn 的原生旧表单/全量 Pack 作为默认 AI 安全写入口。
4. 把独立 Agent 版本账本当成全渠道一致性保证。
5. 把业务 Agent 当成开发 Agent、把 MCP 调用成功等价于应用交付。
6. 把 `withTransaction` 函数名当成可靠原子事务的证明。
7. 把已预装的 JS Trigger 说成 AI 自动编码，把 Playwright 模拟用户说成真实用户亲自批准。

**需要 OpenAILCAP 自主设计与实证：**
- 可信变更命令及跨人工/AI/插件强制统一写入；不可绕过的 revision/fingerprint CAS。
- 类型化 Application Capability Contract（低代码能力/代码扩展能力/副作用/权限/成本）。
- Schema/Manifest/CodeArtifact 对应关系、资源依赖图和可回滚发布快照。
- 开发任务状态机、Agent 安全委托、未知结果对账以及安全执行工作区。
- 全量导入作为单独高权限变更事务，并要求 dry-run、影响分析和人工确认。

## 6. 关键假设及最小可证伪实验（S3 优先）

| 事项 | 最小实验与门槛 | 失败/替代路线 |
|---|---|---|
| H03 全路径强制写入 | 原生浏览器、Agent、插件在同一资源相同旧 revision 并发；同字段必须显式冲突、不同字段可无损合并，物理库无静默覆盖 | 禁止 AI 并行写；更换/改造设计器写入层 |
| H01 分域 Schema 是否足够 | 同业务构建 A/B，测跨资源 rename、依赖闭包、版本回滚与每新增资源类型所需修改范围 | 分域无法表达依赖时引入有限 canonical IR，不做无边界全局 DSL |
| H02/H04 真正 AI 开发闭环 | 从未预置字段/规则开始，模型真实生成 Schema + 代码，独立构建/测试/部署，含失败修复 | 收缩 MVP 代码能力、限定插件契约 |
| H05/H07 受限 Agent 与插件 | 在真实双 app 上做插件发现、身份委托、越权拒绝、崩溃/重放/供应链测试 | 只允许白名单内置功能、隔离 Worker/容器、收窄工具 |
| H06 应用隔离 | 两 app 并行运行、不同凭据、跨应用读取与执行拒绝，故障影响可控 | 逐应用进程/数据库/工作区强化隔离 |

不要为 S1 再重复模型连通测试。把完整 PoC-A/B/C/D 放到第三阶段；本阶段只输出实验风险和可复现证据。

## 7. S1 证据完成度与局限

- 已有 README 1.2 的 22 项四平台静态/官方文档级能力矩阵；1.3 的 ToolJet 深入链和 Saltcorn 实测链；1.4 的真实原生合同纵向切片、审批和人机顺序交接。
- 没有同一业务在四个候选平台上的独立真实对照 benchmark；没有完整 NocoBase v3 创建器跑通记录；没有安全生产级多租户核查。
- 冻结 TC01—TC18 按其**完整原始验收条件**仍 0/18 PASS；数十项子断言 PASS 不得加总换算为 TC 通过。
- 对低代码企业软件许可问题，本报告只给技术性风险提示，不构成法律意见。
- 研究结论需随实际提交 SHA 更新；本报告没有执行新 CI、没有新增 LLM 调用。

下一步：审阅 [ADR-S1-002](28-adr-domain-schema-manifest.md) 和 [G1 正式决策草案](29-g1-decision-review.md)；G1 的结论应严格区分“**研究方向可进入下一阶段**”与“**已建成可安全发布的平台**”。
