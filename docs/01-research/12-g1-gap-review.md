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

## 2026-11-21 第三轮 G1 证据更新：写入协议反例

新增 [真实 Saltcorn 三阶段编辑对照](16-saltcorn-roundtrip-evidence.md)，[Run #44871169761](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44871169761) completed/success，18 次物理 SQLite/HTTP 断言全部符合预期。**关键负面结果**：旧完整 Pack 用于自动化视图配置时会把已经保存的无关人工标签改回旧值，说明“把管理员恢复接口直接作为 Agent 修改工具”这条低成本集成路线不可接受。非冲突单字段串行更新保留了不同字段改动；应用层 STALE_BASE 只是非原子预检查。

- H03：特定危险写入路径被真实证伪，但真正 AI/人工浏览器多轮协作和受信 API 并未验证，故状态仍 **未通过**。
- H01：真实资源模型多次变更有证据，但没有统一 IR 与分域 Schema 的同平台 A/B 试验，仍不能最终选型。
- 合同标准 TC01—TC18：仍 **0/18 完整验收**，不能把 A/B/C 实验计为完整合同基准任务成功。
- 真正原子 CAS、业务应用权限、跨应用隔离和自动构建部署：仍待开展。

**门禁决策保持 G1 未通过**。下一阶段优先验证实际浏览器设计器保存路径、原子 expectedRevision 接口，以及具有可信授权的真实 Agent 工具调用，而不是继续写大量静态功能分析。候选 ADR 位于 [研究文档 17](17-provisional-adr-guarded-editing.md)。

## 2026-11-21 G1 再评审：真实事务与写入入口完整性

新增 [报告 18](18-saltcorn-sqlite-atomic-evidence.md)、[原始 Run #44872093657](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44872093657)，观察到真实第三方平台本机 SQLite 两进程并发写入、资源级原子 revision 冲突拒绝、故障注入回滚，且**真实复现了两个负面风险**：（1）Saltcorn 的 SQLite withTransaction 包装层无真实事务回滚，（2）未走治理账本的人工原生修改会被随后的 Agent 侧 CAS 误认为合法并覆盖。

**G1 状态维持 NOT_PASSED**：这次测试验证的是低层协议和真实原生模型 API，不是浏览器登录后的设计器人工保存，不是实际模型 Agent。冻结合同 TC01—TC18 全部仍待完整端到端业务验收，不能借此计入通过。下一个严格门禁是先让真实浏览器/HTTP 人工写入进入同一不可绕过的版本历史，再观察 AI 工具调用的同步、冲突、授权及回滚。强制身份、租户、插件路径与部署仍为后续阻断。

## 2026-11-21 G1 第四次实证复审：真实 Web 人工保存已经验证

新增 **首次浏览器真实人工编辑证据**：[研究报告 19](19-real-browser-edit-evidence.md) 与 [GitHub Actions Run #44873882208](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44873882208)。使用 Chromium 真实 UI 登录临时管理员、两个浏览器标签页 B 后 A 提交字段向导。**9/9 页面与 SQLite 验收通过，但 A 旧表单实际覆盖 B 已保存标签**；模拟 Agent 侧版本账本没有纳入浏览器修改，导致下一轮旧 revision 修改再次静默覆盖。后置 5/5 验收中含危险负面对照。真实 browser GET/POST/CSRF/未登录拒绝均有一手可复核输出。

**风险评审**：G1 在“第三方参考平台真实 Web 用户编辑旅程”的证据缺口已显著缩小，但这不是 OpenAILCAP 人机安全协同能力可行性正向证明。任何只包装 Agent 写入、不改造人工编辑器版本治理的方案继续保持不可接受。仍缺：真正 LLM Agent 的类型化工具调用、正式统一版本化 API（认证、409、幂等、审计）、可运行两级审批/自定义业务规则/插件与多应用隔离，及统一 IR vs 分域 Schema 的真实对比。

**G1：NOT_PASSED；18 项完整合同 TC01—TC18：仍 0/18。** 不得仅依据脚本数量或 CI 绿灯提前进入第二阶段。CI 工具首次失败的 Ubuntu/Playwright 兼容性问题已在成功重跑的固定 Runner 中解除。

## 2026-11-21 G1 进一步实证复审：首次形成限域正向治理闭环

[研究报告 20](20-governed-http-evidence.md)，[GitHub Actions Run #44874668928](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44874668928)：在真实 Saltcorn SQLite 字段元数据上，研究网关自建的浏览器页面和模拟 Agent HTTP 客户端共享版本化原子写入，22/22 测试通过；真实 Saltcorn 原生 Field.update 故意绕过后，网关指纹漂移检测 4/4 通过并拒绝旧请求；原生运行时重启 REST/HTML 可读回。与此前只有危险负例不同，本轮已证实**一个严格受限的正向协议是可运行的**。

**风险边界未消除**：Saltcorn 自带 Web 设计器和插件根本没有接入这套网关，仍可越过研究账本；网关直接写 _sc_fields，绕开平台缓存刷新与业务钩子，不具生产价值。AI 模拟请求仍由确定性代码产生，非 LLM/Agent 工具授权。无合同多级审批、全部关键架构对照、组织多租户安全与自动发布。因此 **G1 NOT_PASSED**，18 项冻结合同验收继续 0/18。

后续 S1 的最高价值工作应转向**真正模型 Agent 的类型化工具与最小权限委托**以及**真实合同多级审批执行**，并以许可可用的平台原生扩展入口而非直接操作内部 SQL 元数据表开展集成。必要时开展正式 G1 差距收敛评审，避免无限重复字段标签版控实验。

## 2026-11-21 第五轮实证复审：真实原生合同两级审批已经运行

新增 [研究报告 21](21-saltcorn-native-workflow-evidence.md)、[GitHub Actions #44876882097](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44876882097) completed/success，真实 Saltcorn Native Table/Field/View/Trigger、冻结金额边界 12/12、审批状态机 12/12、3 条普通/高额二级/驳回连续路径 3/3，以及物理数据库和 REST/HTML 共 **35/35** 独立断言符合预期。这是 1.4 同一合同业务场景首次以**原生业务 Code Action Trigger**运行，而不是简单页面样例或 Python 模拟状态机。

仍无法 G1 Go 的具体原因：**(1)** actor_role 是业务请求字段而非受认证的审批人，错误角色的 FORBIDDEN 只在触发器中返回，不是已验收的真实 HTTP 403；**(2)** Saltcorn amount_decimal SQL 类型为 TEXT，冻结规格是 decimal(12,2)，精度需求仅在研究 JS 预处理校验；**(3)** 事务由研究 CLI 显式 SQL 包裹，没有验收原生 HTTP 动作本身的中断/并发保证；**(4)** 没有真正 LLM Agent 自动配置/生成/修复，也没有网页审批提交、插件和多应用隔离。

**G1 维持 NOT_PASSED**，18 项完整平台合同任务继续 0/18；新实证仅为 TC01/02/03/05/18 的 PARTIAL 机制证据。建议下轮高价值工作：真实用户鉴权审批动作、通过最小特权 Agent Tool 执行同一应用变更、参考平台选型的定量反方评审，不再重复已有字段标签机制实验。

## 2026-11-21 第六轮 G1 评审：真实 Saltcorn 登录身份与原生审批权限实证

[研究报告 22](22-native-identity-approval-evidence.md)、[Actions #44879041055](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44879041055) completed/success，32/32 实测 PASS：四个真实 Saltcorn 用户 Chromium 登录，并用带当前会话 CSRF 的原生 API 写审批动作；平台原生 Validate/Insert Trigger 基于服务端 user.id/email 拒绝伪造身份，真实业务合同在一级/二级批准与驳回过程中产生正确的状态/审批明细；非管理员直接写受保护表失败。对先前“请求中的角色字符串可伪造”这一重要风险给出了限域、有效的正向修复证据。

**仍不可 G1 GO**：（1）所有四个用户 Saltcorn role_id 都是 80，只通过研究代码硬编码邮箱映射业务审批岗位；与多组织 RBAC/人员离岗/行级授权差距明显。（2）Saltcorn 表层越权返回 HTTP **401**，业务不允许返回 HTTP **400**，与冻结 TC04 所需 403 不同；不得将 TC04 标 PASS。（3）合同金额仍是 TEXT + 分而非 decimal(12,2)。（4）没有真实审批网页表单、同一 Saltcorn HTTP 写请求的原子回滚/并发幂等、真正 LLM Agent 工具编排与发布。前两次 CI 还识别了 Session CSRF 缺失会导致重定向后 200 HTML 假成功的危险验收误判，应纳入 G1 的独立 HTTP 成功判据。

因此仍 **S1 IN_PROGRESS、G1 NOT_PASSED，冻结 18 项完整业务任务 0/18 PASS**。新的前进方向：真实 LLM Agent + 带授权/审计的类型化工具；专业 RBAC/审批 UI；金额 SQL 语义与事务边界；正式 G1 对照选型，而不是继续扩大同字段元数据版本实验。

## 2026-11-21 第七轮 G1 审查：真实平台中的受控 Agent 工具机制

[报告 23](23-agent-tool-contract-evidence.md)、[Actions #44881082333](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44881082333) completed/success：21 项独立安全单元 + 29 项实际 Saltcorn 登录/工具/API/真实业务表断言均通过，宿主模拟有约束的短时一次性人工许可后，原生业务流程完成高金额合同两级审批，物理审批行 2 条。此结果支持最小权限 Broker + 原生平台适配器的限域架构方向；同时提示 Token/授权/调用日志当前在本机研究流程中，尚非生产高可用授权。

**G1 仍 NOT_PASSED**：真正 LLM 外部推理与工具自主选择仍 NOT_RUN；授权为可信研究程序模拟，不是真实人的同意；不是组织级 RBAC、多应用严格隔离或安全插件安装；原生 HTTP 跨表事务、并发幂等与人工 Web 审批 UI 未闭环；金额 TEXT ≠ decimal(12,2)，原生 HTTP 400/401 ≠ 冻结 TC04 的 403。原始 18 项合同任务依旧 0/18 完整通过。下一优先为工具调用的崩溃重放/未知结果防护和真实大模型工具选择，对照能力路由与代码扩展。

## 2026-11-21 第八轮 S1/G1 复审：AI 工具恢复语义不再只依赖进程内存

[报告 24](24-durable-agent-calls-evidence.md)、[CI #44881510363](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44881510363)：增加 SQLite 持久调用占位+唯一 call_id，29/29 安全与崩溃单元（较上轮 +8）、29/29 真实 Saltcorn 集成均通过。重点反证：仅靠进程内 self.calls 无法在重启后阻止同 ID 再次执行；本轮用持久唯一占位对该风险做了研究性修补，未知远端结果保留待核验，审批 POST 不自动重试。

**G1 仍 NOT_PASSED**，冻结 TC01—TC18 完整通过保持 0/18。不能把仅在本地 SQLite 账本中保证同 ID 不重试当作跨平台/多节点 exactly-once；相同业务的新 call_id 仍可能重复。真正 LLM 推理、正式委托同意、平台原生审批事务/幂等、企业 RBAC、金额 SQL decimal(12,2) 和完整应用自主开发仍是阻断项。

## 2026-11-21：真实 DeepSeek Function Calling 最小验证结果（修正此前模型 NOT_RUN 状态）

[报告 25](25-deepseek-real-tool-call.md)、[Actions #44882955824](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44882955824) completed/success，用户提供 GitHub Secret `DEEPSEEK_KEY`，使用 DeepSeek 官方 `deepseek-flash`（non-thinking）、单次 HTTPS Chat Completions 推理。真实模型返回 **contract.read 和 contract.route** 两个工具调用，均通过类型化 Broker 参数校验并在真实 Saltcorn 数据上执行；集成 30/30 PASS，原有安全单元 29/29 PASS。**“真实 LLM 只读工具调用”不再是未验证项。** 该结论只覆盖一次最小真实模型验证，不覆盖 AI 自主创建应用、配置/代码路径智能选择、多轮人机编辑或写操作的真实人工授权。G1 **仍 NOT_PASSED**，冻结合同完整 18 项仍 0/18 PASS。后续应从“真实模型连通性”转向**开发任务的正确工具选择和执行结果**，无需重复付费连通测试。
