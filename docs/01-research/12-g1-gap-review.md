# S1 阶段 G1 证据复审（中期，非通过报告）

复审日期：2026-11-21。依据：[原始任务 README](../../README.md) 第一阶段 1.1—1.5 和 G1；本页使用 **Go / Conditional Go / No-Go** 对下一阶段准备状态进行约束。

## 一、概览与当前决策

**S1 研究可以继续，G1 尚未通过，S2 不应开始完整功能设计。** 已形成：固定 SHA 的四项目研究线索、22 项能力分级矩阵、18 项合同平台验收任务的预注册规范、可运行的 H01/H03 内存/SQLite 前置实验，以及一次真实第三方平台安装失败记录。但尚无任何一套真实参考低代码平台上的合同业务验收通过结果。

| 关键统计 | 当前 |
|---|---|
| 四平台统一能力索引 | 22 项；有分级证据，但没有整体运行验证 |
| 核心架构假设（按平台级标准） | 0/8 已验证；H01/H03 有机制级证据 |
| 统一合同平台验收任务 | 0/18 执行通过，18 NOT_RUN |
| 内存结构方案比较 | 两种结构各 10/10 用例通过；28/28 单测通过（机制级） |
| SQLite 实际数据库测试 | 23/23 单测通过（前置模型级） |
| 第三方完整平台启动 | 0；NocoBase v3 官方创建器遇到模板下载 E530 |
| 四组第三阶段完整 PoC | 0/4 |
| G1 门禁 | **未通过** |

## 二、按 README 第 1 阶段逐项核查

| 原任务 | 已获得的证据 | 仍缺的验收 |
|---|---|---|
| 1.1 候选项目筛选 | ToolJet / Appsmith / Budibase / NocoBase v3 已核查固定 SHA 和核心路径 | 版本、Edition、许可的深入逐模块比较 |
| 1.2 功能研究 | [22 项能力对照矩阵](09-capability-matrix.md) 和机器可读 JSON | 基于真实部署的功能验证，剔除仅文档功能 |
| 1.3 架构研究 | [ToolJet MCP 写入链](04-tooljet-sync-trace.md)、[CE/EE 与 Runner 边界](07-persistence-and-license.md) | 至少一套真实设计态→存储→运行态服务端完整链；插件/AI 权限执行环 |
| 1.4 同一业务场景复现 | [冻结的合同验收协议](10-contract-benchmark.md)；纯模型级人机一致性和 SQLite 事务实验 | 真实平台创建合同 CRUD/审批/自定义代码/人工→AI 交替编辑等 |
| 1.5 六类交付 | 假设表、关键机制、源码证据与部分对照矩阵 | 深度综合报告、最终可借鉴机制与不复用清单、正式 G1 ADR |

## 三、架构可借鉴项与明确应避免项

**可以借鉴（不等于复制代码）**：

- ToolJet 的结构化 App Plan、服务端页面/事件事务与 MCP 增量写入前置校验；
- Appsmith 的 widget registry（避免编辑器循环依赖）、published/unpublished 页面分离；
- Budibase 的数据绑定上下文以及自动化步骤注册；
- NocoBase v3 的 plugin manifest、Runner 本地授权/任务领取/凭据生命周期分层。

**不要直接复用或推定可复用**：

- ToolJet Code Mode 的 EE 子模块服务端（CE 是 stub，许可证和源码不可用边界未破）；
- 将 ToolJet MCP 的本地代码同步测试当成全平台一致性保证；
- 将 Budibase 的业务 AI Agent 当作 AI 软件开发 Agent；
- 将 NocoBase v2 无代码设计器功能直接计入 NocoBase v3 Core；
- 将 NocoBase v3 LICENSE.txt 简化成“纯 Apache-2.0 不受额外限制”；
- 将 GitHub Actions 的 SQLite 模型实验标为“生产多租户安全”；
- 将 Python 模型里的 actor 参数当成真正的用户认证凭据。

## 四、ATAM 风格的关键风险权衡

| 技术风险 | A 方案 | B 方案 | 当前最强证据 | 判定 |
|---|---|---|---|---|
| 应用资源统一表示 | 全局 Application IR | 分域 Schema + Manifest | 两方案在同一内存测试中均 10/10；SQLite 持久化走分域 | **未决定**，不能预设 IR |
| AI/人工交错修改 | 全量覆盖 + 版本检查 | 增量 Patch + 内容指纹/三方合并 | 负对照真实复现覆盖失效；资源级 SQLite CAS/事务通过 | 支持增量命令方向，但真实编辑器待验证 |
| 低代码配置与 AI 编码统一 | 强 DSL 全面表达 | 原生配置/代码扩展双路径 | 各平台不同边界、ToolJet CE/EE 明确断点 | 未决定，需真实同场景 |
| 插件 AI 可发现 | 代码搜索学习工具 | Manifest + 类型化能力描述 | NocoBase 声明、ToolJet MCP 计划 Schema | 未做安装新插件的 AI 调用 |
| 运行与沙箱隔离 | 平台进程内执行 | 独立受限执行单元 | NocoBase build isolation 模式和默认 none 证据 | 生产隔离不通过 |
| 参考平台可用于自研 | 直接 fork 核心代码 | 仅学习思想、采用兼容许可模块 | NocoBase v3 附加条款、ToolJet AGPL+EE、Appsmith Apache、Budibase 分包 | 不允许在此时决定 fork |

## 五、阶段继续执行的最小闭环

**下一工作包优先级**：

1. **P0：真实平台可安装性**。优先依据官方版本、资源和许可建立一个最小运行实例，记录镜像 digest/lockfile、进程、健康和启动日志。NocoBase v3 当前 E530 先排查官方模板包访问/版本/授权，不作盲目重试；资源符合时考虑 Appsmith CE 或 Budibase。
2. **P0：最小可验证合同任务**。先做 TC01/TC02/TC03/TC10，覆盖真实数据库、页面、阈值审批、人工/Agent 编辑，不要求先实现全部 18 项。
3. **P0：补真实写入调用链**。至少追踪平台 API/权限→设计态存储→运行态读回→发布；对 EE/闭源断点保留证据级别。
4. **P1：完成源代码/许可评审**。明确开放商业发行的风险与“研究参考 vs 代码集成”的区分。
5. **P1：对照实现与 ADR**。在同一平台改动序列下比较统一 IR 与分域 Schema，不再只测两个内存 JSON 表示。

## 六、G1 的准入条件

- 已完整形成有源代码/官方版本标识的能力差异及许可边界表；
- 实际运行至少一个参考平台并有完整可核对的服务端代码/运行链路；
- 合同场景至少基础 CRUD/工作流可执行且能独立验证、追踪失败；
- 针对最高风险 H01/H03 给出真实设计器/Agent 接手人工修改的对照证据，或清楚标注商业版造成的阻断并调整基线；
- 形成反方评审和 Go/Conditional Go/No-Go 的正式记录。

**当前结论**：Conditional Go 仅用于**继续受控的 S1 研究及小型实验**，不是允许进入 S2 的 G1 Go。下次复审只以实际原始数据变更门禁状态，不按文档数量估算百分比。

## 2026-11-21 远端规范检查回填

[合同规范 GitHub Actions #44868820335](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44868820335) completed/success，金额/状态机 oracle 及 18 项平台任务 NOT_RUN 的基线检查步骤均成功。见 [独立执行记录](13-contract-oracle-ci.md)。该结果不改变阶段 G1 未通过的结论。

## 2026-11-21：首次真实平台实验后重新评估

- 真实 Saltcorn CLI 运行并独立测试：GitHub [Run #44869777036](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44869777036)，7/7 PASS，真正 SQLite metadata / View / REST、匿名拒绝。此项将第三方实际运行平台从 0 更新为 **1**。
- 真实 Saltcorn 原生 Pack 导入合同/审批关联模型、合同数据与可渲染页面：GitHub [Run #44869926796](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44869926796)，9/9 PASS，确为实际第三方服务端和 SQLite，不是自研模型模拟。
- 研究报告：[真实运行时](14-saltcorn-real-platform.md)、[合同配置纵向切片](15-native-contract-platform-evidence.md)。源码/实验工程位于 [experiments/platform-saltcorn](../../experiments/platform-saltcorn/README.md)。

**新的事实**：G1 的“第三方真实平台无法安装”这一阻断已被解决；可直接观察结构化低代码配置入口经模型/字段/视图到运行态产生结果。

**仍有阻断**：Saltcorn Pack 是研究员预先编写，不是 Agent 生成；金额存储为整数分而冻结基准要求 decimal(12,2)，多级审批、真实人员修改/AI 接手、受限插件发现、多应用隔离没有在平台运行；既定四个平台仍未完成统一合同场景真实复现。H01/H03 的核心双向编辑尚无真实设计器实证，因此 18 项冻结合同验收仍 0/18。**G1 保持 NOT_PASSED，仅允许继续 S1 受控研究。** 

**下一关键技术验证**：使用相同真实 Saltcorn Pack 资源执行“人工修改已保存配置 → 旧 Agent 会话持旧快照导入/增量修改”，记录平台 API 对冲突是否拒绝、是否覆盖。与本仓库 CAS + 三方合并机制的真实服务端接入方案做双路线对照，并及时记录失败/安全边界。
