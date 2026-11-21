# S1 报告 38：B5 Domain Schema + Manifest vs Application IR 公平表示法对照与统一工具入口

**日期：2026-11-21。状态：B5 已完成可复现双应用 A/B 研究；第一阶段 S1 继续 IN_PROGRESS，G1 NOT_PASSED，G1-B01 PARTIALLY VALIDATED / OPEN。**

## 1. 关键研究问题与预冻结解释范围

前序 [报告 35：B2](35-s1-b2-schema-runtime-manifest-evidence.md)、[报告 36：B3](36-s1-b3-real-deepseek-typed-plan-evidence.md)、[报告 37：B4](37-s1-b4-real-deepseek-custom-code-sandbox-evidence.md) 已分别证明：

- 元数据驱动 DataModel/Form/View/Workflow + Manifest 可以在最小应用中创建、运行、编辑、发布和回滚；
- 真实 DeepSeek 可受限地生成四类 Schema 配置，通过服务端验证后执行；
- 真实 DeepSeek 可生成受限 Python 纯函数，在无网络 Docker 中通过 432 个独立业务边界组合测试，再与 B2 已发布版本绑定。

但已有证据**不能**解决核心架构分歧：由统一全局 Application IR 作为独立持久化和运行内核，还是 Domain Schema + 版本化 Manifest 承担权威内核？也未充分证明各种开发写入通道共享**无法绕过**的强制授权和版本治理。

B5 设计一个严格限界的实验，**控制运行引擎变量**：两套**设计态表示**生成完全相同的 B2/B4 运行资源，以同一 SQLite/Chromium/Docker 作独立裁判。该实验只能验证**表示法可转换性与工具入口的研究安全性**，不可能得出两个不同运行内核性能或架构胜负的结论。

## 2. GitHub 实际执行及交付

| 证据 | 结果 |
|---|---|
| PR | [#7](https://github.com/zealzhangz/OpenAILCAP/pull/7)，已合并 |
| main 合并提交 | [e8106e6214c0b75ad232c7d12a0a7a4aad794916](https://github.com/zealzhangz/OpenAILCAP/commit/e8106e6214c0b75ad232c7d12a0a7a4aad794916) |
| 完整工程/运行指南 | [experiments/g1-b01-b5](../../experiments/g1-b01-b5/README.md) |
| CI 配置 | [.github/workflows/s1-b5-ir-parity-gateway.yml](../../.github/workflows/s1-b5-ir-parity-gateway.yml) |
| **成功实际 CI** | [GitHub Actions #44895248552](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44895248552)：**completed/success** |
| Job | **136819389820** |
| 机器可读原始证据 | [Artifact #14703169788](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44895248552/artifacts/14703169788)，`s1-b5-ir-parity-tool-broker-evidence` |
| B5 IR + Broker 安全与语义单测 | **40/40 PASS** |
| B2 运行内核回归 | **18/18 PASS** |
| B4 源码 AST 安全回归 | **27/27 PASS** |
| B5 两应用、真实 Chromium/真实 Docker/Plugin 子进程端到端 | **29/29 PASS** |
| DeepSeek / 其他收费模型请求 | **0 次** |
| 实际代码 Oracle | 与 B4 相同的**432 组**合同金额/信用/合作月数边界；独立真实 Docker 运行。 |

本次 CI 第一次运行 [#44895201810](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44895201810) 在**单元测试加载**阶段被测试环境 Python 模块路径缺失阻断（`ModuleNotFoundError: schema_core`），尚未进入 Docker/业务验证。仅补充 B5 单测的研究依赖导入路径，**没有修改产品逻辑或放宽断言**。成功运行 #44895248552 保留了完整 40/18/27/29 的原始日志。

## 3. A/B 架构表示法的真实对照

**A：Domain Schema + Manifest**。作者直接维护四个 B2 资源：

- `model.contracts`：合同编号、标题、整数分金额、审批状态；
- `form.contracts`：登记字段；
- `view.contracts`：合同编号、标题、金额和状态；
- `workflow.approval`：超过 100 万元需要二级审批；
- 受 B2 Manifest 版本约束的 B4 扩展代码通过独立 Registry 绑定。

**B：统一 Application IR（设计态）**。作者维护单个结构化 `irVersion:1` 文档，内含 `entity/attributes`、`interfaces/bindings`、`processes`、`extensions`。编译器 [ir_bridge.py](../../experiments/g1-b01-b5/ir_bridge.py) 对 IR 严格检查字段类型、名称、引用闭包、审批参数、扩展接口，将其**编译为与 A 完全相同的四个 B2 资源**。反向投影必须无损，不能携带越权的 actorId、SQL、未注册扩展或非法业务引用。

**重要区别**：B 不是全新 IR-native 执行引擎；A、B 的运行逻辑、B2 SQLite 表、B4 Docker 沙箱和发布路径事实上相同。这个对照消除了运行内核的混杂因素，专门测**设计态表示与工具调用**，却**不能**证明 IR 或 Domain Native Kernel 的工程性能优劣。

| 已实测指标 | A 直接 Domain | B 编译后的统一 IR | 研究判断 |
|---|---:|---:|---|
| 同一合同基准 JSON（canonical UTF-8） | **693 字节** | **937 字节** | IR 该样本较大，但**单例字节数不能反推维护成本/效率** |
| 创建完整四类资源所需 B2 typed commands | **4** | **4** | 单文档 IR **不能自动赋予跨资源 ACID 事务** |
| 初始草稿 Manifest SHA-256 | `6f7cc7402b422fa564fc43e02eb7543645b21131ff25832aa243d4b24a83270e` | **相同** | 运行 Schema 语义相同 |
| 插件修改 View 标题后的有效资源 Diff | 仅 `view.contracts` | 仅 `view.contracts` | 已覆盖场景增量变更等价 |
| 用户修改 Form 标题后的有效资源 Diff | 仅 `form.contracts` | 仅 `form.contracts` | IR 单次属性编辑编译至一次 B2 指令 |
| 物理 appRevision 与最终 Draft Hash | 双方 revision=6 | revision=6、Hash 相同 | 真实 SQLite + app CAS 一致 |
| 发布版合同审批轨迹 | 金额超标 2 级，未超标 1 级 | **相同轨迹** | 因同一 B2 内核，只能证明编译保真 |
| 风险计算 | 高风险 95、低风险 0 | **相同评分** | 同一 B4 代码+Docker，不是两个独立 Kernel |
| B2 已发布 v2 与 B4 v1 绑定不匹配 | 旧扩展 409 | **相同 409** | 跨资源版本闭包正确拒绝 |
| B2 指针回滚至 v1 | 代码可重新运行 | **相同恢复** | 仅本研究双指针和同 SQLite 条件 |

这组对照支持一个**暂定偏好**：运行层优先使用有类型的 Domain Schema 资源 + 可验证 Manifest；统一 IR 可以作为自然语言需求规划、全局依赖图和编辑器设计态的投影与编辑协议。此偏好是**待独立 IR-native 引擎和更多领域样本证伪的 ADR 候选**，不是最终架构选型。

## 4. v3 统一工具入口的真实实验

本轮新建受信的 [tool_broker.py](../../experiments/g1-b01-b5/tool_broker.py)，在真正 loopback HTTP 上将随机 opaque token 映射至服务器端 `Actor + app + capabilities + 过期状态`。模型/Plugin/Agent 不可在请求 JSON 中构造自身权限或提升角色。

| 主体 | 实际受限权限 | 实际负对照 |
|---|---|---|
| 真实 Chromium 模拟管理员 | B2 浏览器 Cookie/CSRF 修改设计态；v3 受权主体可审批发布 | 持旧 appRevision 的 Agent 再写被 HTTP **409**，人工修改保留 |
| Agent OS 进程 | `draft.read`、`metadata.upsert`、`code.verify` | 实际 Docker 432 项测试**通过也不能** Stage/Publish；HTTP **403** |
| Plugin OS 进程 | `draft.read`、仅 `view` 元数据 `metadata.upsert` | 改 Model **403 KIND_FORBIDDEN**；申请未知 SQL 工具/代码 Stage **403 TOOL_NOT_GRANTED** |
| Runtime-only 主体 | `form.submit`、`workflow.advance`、`risk.score` | 不得写入设计态、发布或跨 App；跨 App **403** |
| 已撤销的 Plugin token | 无权限 | 撤销后再次从独立 OS 进程请求，立刻 **401** |
| 匿名 HTTP | 无权限 | **401** |
| 试图绕过 Broker 的 Bearer | 直接访问 B2 v2 API | **401**，仅向浏览器 Session 保留 B2 v2 入口 |

**代码构建重要差别**：Agent 请求 `code.verify` 时，可信 Broker 在真实只读、无网络 Docker 内按 B4 AST 与 432 项测试验收，仅返回代码摘要/测试数量，不向 Agent 传可伪造的构建签收对象；模拟人工调用 `code.stage` 时，Broker 会再次调用受信 Docker 测试，才送 B4 Registry 绑定发布指针。模型不能通过客户端声称“已构建”替代受信验证。B5 不再发起额外外部模型推理，因为 B4 已有真实 DeepSeek 源码生成证据，本次研究变量是架构表示与工具安全。

## 5. 29 项端到端结果及发现的未闭合风险

成功 CI 原始记录包括：

- B5-01—02：Schema↔IR 无损、4 条工具写入和两种 JSON 字节成本实测。
- B5-03—11：v3 实际权限发现、跨 App 拒绝、2 应用从空状态的真实 HTTP 元数据写入、插件独立进程写 View、未知 SQL/Model/Stage 权限拒绝、Bearer 不可绕过 v3。
- B5-12—14：真实两 App 发布同一 B2 v1、物理各 2 条合同业务记录、金额审批状态轨迹相同。
- B5-15—18：Agent 真 Docker 验证而无发布权，模拟人工分别重新测试、Stage 和发布两 App 的同一内容哈希风险代码。
- B5-19—24：真实 Chromium 登录/发布版 View/风险评分 95、IR App 评分 95、错误代码被独立 432 条 Oracle 拒绝，人工浏览器改 Form 后 Agent 持旧版本 **409**，IR 路径只改一个资源并得到同样 Draft Manifest；既有 B2 v1 的风险运行不受 Draft 编辑影响。
- B5-25—27：两路径都发布 B2 v2 后，绑定 B2 v1 的 Code 执行 **409**；双应用回滚 B2 v1 后恢复；独立插件 token 撤销后返回 **401**。
- **B5-28：刻意保留的负对照**。可信研究测试进程**直接使用特权 SQLite UPDATE 改写 app-b 已验证 Extension Artifact 的源码**，B2/B4 没有真正阻止该物理改写。此后实际风险接口检测 `ARTIFACT_HASH_DRIFT` 返回 **409**，app-a 的风险接口继续 **200**。这里的测试 PASS 指“危险旁路已被成功复现且运行时检测没有误放行”，**不是**“数据库旁路已禁止”或“W16/W11 完整通过”。
- B5-29：独立只读 SQLite 核查两 App 版本、资源/代码发布与角色事件审计；外部模型调用实际 0 次。

**最终关键失效事实**：只在 Broker 上增加权限控制并不能阻止已经获得 Docker Socket、宿主文件权限、原生 Saltcorn CLI 或数据库管理员连接的第三方程序绕过 Broker 修改真实存储；B5 的插件只是一个**独立 OS 子进程、未使用真正 OS 容器/沙箱隔离**。如果把已拥有 DB 文件/Socket 的任意插件视为可信，就无法证明全入口安全治理。**生产候选必须进行权限隔离、底层 DB 权限最小化与不可绕过的内核写入边界治理**；运行时哈希漂移检测只是失败封闭层，无法替代防止越权写入。

## 6. 阶段门禁评审与下一技术决策

**成功回答的窄问题**：

1. 在同一运行内核上，Domain Schema+Manifest 和统一 IR 对已冻结合同/Workflow/B4 风险能力可进行无损映射；
2. IR 编辑 Form/View 属性可以无损编译成单一 B2 资源级变更命令，且同一 B2 发布与业务验收一致；
3. Web、Agent 和实验 Plugin 的**受控** B2/B4 工具调用可受同一 v3 功能授权、应用隔离、Audit、revision 守卫和模拟人工发布控制；
4. 有特权 SQL 旁路确实仍能发生，现有研究内核只能检测 Drift 并拒绝后续运行。

**未完成、不得用本报告宣称已实现**：全局 IR 独立原生 Runtime 的工程对照、跨资源原子 IR 发布、真正插件容器沙箱、企业级身份委托、Saltcorn 原生路由统一治理、跨数据库事务、插件直接 DB/Socket 访问强制阻断、AI 自主自动修复、工程级多语言构建、生产部署。

**结论**：S1 IN_PROGRESS / G1 **NOT_PASSED**；G1-B01 **PARTIALLY VALIDATED / OPEN**；冻结 W01—W24 **0/24 FULL PASS**，冻结合同 TC01—TC18 **0/18 FULL PASS**。B5 额外 29 项测试**不取代**正式冻结 24 项验收。

**下一建议**：以报告 38 的真实特权 SQL 绕过为 P0，优先验证**宿主和真实插件系统级权限隔离**（DB 文件不可访问、Docker Socket 不挂载、只暴露可信受控 API）、同一事务的 Schema+Extension 发布一致性，并按 W11、W16、W20、W24 固定规范补齐真正不可绕过与外部副作用补偿。架构方向暂定“**Domain Schema 运行内核 + 派生 Manifest + 设计态统一 IR 投影**”，只作为后续验证假设，不提交为最终 ADR。
