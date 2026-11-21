# OpenAILCAP：八项可证伪的核心架构假设

日期：2026-11-21。状态：平台级所有假设仍**未验证**；H01/H03 已完成受限模型层首轮实验（参见 [实验报告](../01-research/05-roundtrip-results.md)），不能等同平台级通过。研究依据为用户仓库 README.md。不得将第三方源码存在等同于端到端执行成功。

## H01 应用状态表示与 AI/人工共享

**重要性**：如果低代码配置、代码工件和人工改动各自存在相互隔离的“真相来源”，版本管理、引用检查、人机协作都不可靠。

**一手线索**：[ToolJet MCP appPlanSchema.ts](https://github.com/ToolJet/tooljet-mcp/blob/8a178ad34f6e3326b6957503ca4ed4f555d23096/src/appPlanSchema.ts) 在应用计划中表达 tables、queries、pages、events、lifecycles，并为已有资源定义更新语义；[Budibase Builder dataBinding.ts](https://github.com/Budibase/budibase/blob/724cb529d7b32fde84ae537e4b44673cf0618dad/packages/builder/src/dataBinding.ts) 明确维护组件、上下文与绑定引用。这证明存在可研究的结构化资产，**并不证明它们已构成通用 IR**。

**候选 A**：统一版本化 Application IR，数据、页面、流程、权限、代码均引用稳定对象 ID。**候选 B**：领域 Schema 各自独立，用 Application Manifest、版本引用及受治理 API 聚合。

**实验**：以合同表单 + 审批规则 + 自定义编号生成器实现 A/B；导出、导入、人工编辑、AI 追加、运行行为回归。**通过**：预注册的 12 项引用及业务断言全部正确；无未知字段静默丢失；任何非预期覆盖均使试验失败。**失败退路**：缩减统一 IR 边界，退回分域 Schema + Manifest，并限制 MVP 支持的业务类型。

## H02 AI 能正确选择配置、代码或混合实现

**重要性**：配置不了的业务被伪装为配置成功，或者简单 CRUD 全部变成代码，均违背核心价值。

**一手线索**：ToolJet 的 [appPlanSchema](https://github.com/ToolJet/tooljet-mcp/blob/8a178ad34f6e3326b6957503ca4ed4f555d23096/src/appPlanSchema.ts) 与 [applyAppPhase](https://github.com/ToolJet/tooljet-mcp/blob/8a178ad34f6e3326b6957503ca4ed4f555d23096/src/tools/applyAppPhase.ts) 体现受限计划及校验链，未证明自然语言路由能力。

**候选 A**：模型根据能力目录直接判断。**候选 B**：类型化能力目录 + 确定性适用性检查 + AI 规划 + 运行结果校验。

**实验**：24 道冻结任务：8 配置、8 代码、8 混合；独立标注，每组重复三次。**通过**：不得出现“无法配置的任务被认定纯配置且通过验收”，决策有工具/约束依据。**失败退路**：保守转混合路径或明确拒绝，限制自动配置范围。

## H03 AI 与人工修改能够无损往返

**重要性**：AI 下一轮利用旧上下文覆盖人工样式/代码，会直接摧毁平台长期维护价值。

**一手线索**：[ToolJet MCP codeAppSync.test.ts](https://github.com/ToolJet/tooljet-mcp/blob/8a178ad34f6e3326b6957503ca4ed4f555d23096/tests/codeAppSync.test.ts) 存在 Style inspector 修改后下一轮 Agent 旧代码覆盖场景，还测试 revision 相等但内容不同。静态测试存在不代表已运行通过。

**候选 A**：服务端指纹 + 乐观并发 CAS + 字段/节点 Patch + 三方合并。**候选 B**：集中操作日志/事件模型（必要时研究 OT/CRDT）。

**实验**：非冲突字段同时修改；同一字段冲突；相同 revision 不同内容；被删除对象的引用；跨资源部分失败；幂等重试；回滚。**通过**：非冲突变更全部保留，冲突全部拒绝或显式仲裁，静默丢失 0，回滚后所有断言相同。**失败退路**：强制资源所有权、每次 Agent 操作重新同步；禁止对重叠资源自动写入。

## H04 AI 可以安全完成自定义代码闭环

**重要性**：代码生成不等于可安全部署的业务扩展。

**一手线索**：[NocoBase agent-runner README](https://github.com/nocobase/nocobase/blob/0894734040c3d30d4f4f3d7a6da98ae22f365f80/packages/app/agent-runner/README.md) 描述工作目录和 Agent CLI；[ToolJet codeAppIsolation.test.ts](https://github.com/ToolJet/tooljet-mcp/blob/8a178ad34f6e3326b6957503ca4ed4f555d23096/tests/codeAppIsolation.test.ts) 对执行器变量白名单与工作区做静态测试。

**候选 A**：受限 SDK 扩展点 + 隔离工作区 + 构建/验收/发布门禁。**候选 B**：每应用独立服务和源码仓库，经受控 API 集成。

**实验**：AI 创建合同编号函数，测试唯一性、幂等、授权；注入编译、依赖、测试、健康检查失败与恶意访问。**通过**：测试未通过不得部署；可回滚；未泄漏密钥。**失败退路**：允许自动部署到隔离开发环境但生产发布需要审批。

## H05 插件能力可自动发现并授权使用

**重要性**：每新增插件都要改内核或修改系统 Prompt，则扩展机制不可持续。

**一手线索**：[NocoBase define.ts](https://github.com/nocobase/nocobase/blob/0894734040c3d30d4f4f3d7a6da98ae22f365f80/packages/app/app-server/src/plugins/define.ts) 提供插件定义、包名约束、服务、路由等注册能力；[resolve.ts](https://github.com/nocobase/nocobase/blob/0894734040c3d30d4f4f3d7a6da98ae22f365f80/packages/app/app-server/src/plugins/resolve.ts) 聚合版本和迁移目录。

**候选 A**：插件 Manifest + 能力 Schema + 权限代理。**候选 B**：SDK/源码约定 + Agent 代码检索。

**实验**：新增合同编号插件，无需改内核/Agent 全局 Prompt，AI 发现调用；升级不兼容版本和未授权调用。**通过**：功能发现正确，越权 0，升级变更可识别。**失败退路**：缩减为经审核的受限插件能力。

## H06 多应用与代码执行真正隔离

**重要性**：AI 和插件增加跨应用数据、凭据、文件与部署串扰风险。

**一手线索**：[ToolJet codeAppIsolation.test.ts](https://github.com/ToolJet/tooljet-mcp/blob/8a178ad34f6e3326b6957503ca4ed4f555d23096/tests/codeAppIsolation.test.ts) 具有不同 workspace 并发及凭据环境隔离测试。

**候选 A**：共享运行时 + 应用 ACL/命名空间 + 独立构建沙箱。**候选 B**：每应用独立运行/数据单元。

**实验**：同名资源 A/B，尝试跨应用读写数据/代码、访问密钥和部署。**通过**：0 次未授权访问，日志可回溯主体与目标。**失败退路**：MVP 使用每应用独立部署单元。

## H07 可由独立验证器判定 AI 任务成功且失败可恢复

**重要性**：模型的“完成”不是验收证明。

**一手线索**：[ToolJet applyAppPhase.ts](https://github.com/ToolJet/tooljet-mcp/blob/8a178ad34f6e3326b6957503ca4ed4f555d23096/src/tools/applyAppPhase.ts) 包含计划校验、引用解析、读回验证逻辑线索。

**候选 A**：确定性 Schema、API、权限、E2E、部署探针门禁。**候选 B**：另一个评审 Agent 作为主要判据。

**实验**：固定 10 类错误，含业务阈值、越权、引用丢失、构建失败、服务探针失败。**通过**：所有阻断级故障均被检测或拒绝，发布失败可恢复旧版本。**失败退路**：限制自动发布范围并增加人工审核。

## H08 禁用 AI 后，人工仍可完成关键开发生命周期

**重要性**：否则项目是 AI 编码工具而非兼容人工开发的低代码平台。

**一手线索**：[Appsmith widget registry](https://github.com/appsmithorg/appsmith/blob/0a6f6934fb33c06ee0a132c5baba78e006611621/app/client/src/widgets/registry.ts) 是 widget 注册/动态加载实现；[Budibase Builder dataBinding](https://github.com/Budibase/budibase/blob/724cb529d7b32fde84ae537e4b44673cf0618dad/packages/builder/src/dataBinding.ts) 的组件与数据绑定代码提供传统编辑器对照，但不能代表 OpenAILCAP 实验已成功。

**候选 A**：人工和 AI 都使用统一受治理的领域 API。**候选 B**：AI 维持专用模型，人工导出外部代码编辑。

**实验**：关闭模型服务，人工创建、编辑、预览、发布业务应用，再由 AI 接手。**通过**：全程不依赖 LLM，复接无损。**失败退路**：提前建设人工编辑基础 API，推迟 AI 专用资产。

## 优先级和初始裁定

H01+H03 为 P0，H02/H04/H07 为 P0，H05/H06/H08 为 P1。已验证假设 0/8。所有阈值为实验预注册建议值，不是行业标准。**不得据此直接宣布统一 IR、技术栈、Agent 框架选型。**

## 2026-11-21 模型级实测更新

H01/H03 的受限内存模型分别以 Unified IR 和分域 Schema + Manifest 通过 10/10 条核心业务场景。新发现：同版本内容漂移后，仅重新读快照不足以允许再次写入；必须把人工变更纳入可信历史版本或保证它原本就经受治理 API 写入。当前不作最终架构选型，也不把此结果记为通过 G1/G3。见 [首轮实测报告](../01-research/05-roundtrip-results.md)。

## 2026-11-21 数据库实验与许可证新证据

H01/H03 在 SQLite 文件型持久化层完成 23 项受限事务及隔离逻辑测试，重启、并发冲突、失败回滚、强制读状态漂移检查均通过；这仍不等同真实低代码平台的 AI/人工协作闭环。H06 中的隔离断言只验证假设 actor 来源可信时的 SQL app_id/ACL 范围，**不能标记 H06 安全验证通过**。

新的重大外部证据：ToolJet CE Code Mode 服务端是 stub，真正服务端属于 EE 子模块，本次无法审查；NocoBase v3 LICENSE.txt 存在与平台型产品潜在冲突的附加授权条款。见 [深度研究与风险报告](../01-research/07-persistence-and-license.md)。

## 2026-11-21 真正第三方低代码资源多轮编辑研究（H01/H03 更新）

[Saltcorn @ 1.7.0-beta.5 实际运行研究](../01-research/16-saltcorn-roundtrip-evidence.md)，[GitHub Actions #44871169761](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44871169761) 在实际第三方 SQLite 资源上复现了三种路径。A）人工预编写的 Field.update 和独立程序化 Field.update 串行修改不同标签都保留；B）使用人工变更前的完整 Pack 作为自动化写入时，目标仅修改视图列，却把人工标签和先前自动化标签恢复旧值，**真实证伪了“无保护全量恢复可作默认 AI 编辑工具”的集成假设**；C）非原子先读后写可在顺序冲突时抛出 STALE_BASE，但不具备并发 CAS 保证。

**H01/H03 仍不能判定平台级通过**：没有真实可视设计器会话、真实模型规划及 Agent 工具调用、原子事务 CAS 或真实并发修改。优先排除默认全量导入方案，研究精确 Patch + 服务端原子基线验证。不能预先决定统一 Application IR 是否必要。[候选 ADR](../01-research/17-provisional-adr-guarded-editing.md) 记录证据、风险和迁移门槛。

## 2026-11-21 H03：两进程原子比较与“版本表可被绕过”反例

在真正 Saltcorn 1.7.0-beta.5 + 真实 SQLite 数据库上运行 [TX1—TX6](../01-research/18-saltcorn-sqlite-atomic-evidence.md)。[GitHub Actions #44872093657](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44872093657) 确认：不同资源两个独立进程都能提交；同一资源同旧 revision 两个进程只能一个提交；显式事务里的原生字段更新可因故障回滚。但 **Saltcorn SQLite withTransaction 只是包装回调，没有事务 SQL，故障后单字段写入保留**；并且**绕过研究用 CAS 版本表的人工原生 Field.update 会让 Agent 下一轮错误接受旧 revision 并覆盖人工编辑**。

新增 H03 验收硬约束：不能只对 Agent 写入做版本检查，所有人工/Agent/插件写入必须共享强制治理 API 或可靠处理外部写入漂移；事务语义必须跨真实数据库适配层进行故障注入。实验仍没有浏览器真实会话、LLM Agent、生产鉴权/应用隔离。H03 仍未通过，G1 仍未通过。

## 2026-11-21 H03 真实 Chromium 浏览器编辑负例

[GitHub Actions #44873882208](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44873882208) 取得首次**真正浏览器人工操作**（登录、CSRF、字段向导）的一手证据：同一会话两标签页 A/B 同时打开旧 Title，B 先保存 Browser B Saved，A 后提交过时上下文，数据库最终 Browser A Stale Save，B 的改动丢失。随后模拟 Agent 使用未被浏览器修改的实验 CAS 版本表，再将字段覆盖成 Agent Overwrites Browser，数据库与 HTTP 读回证实。**H03 已真实证伪“未经治理的旧页面/Agent 侧版本表足以保障多轮编辑”**，但并未完成可靠人机协作的正向证明；真实 LLM Agent、可信共享写入 API、租户、审计和原子 CAS 对 Web 路由仍待验证。H03 和 G1 都保持未通过。

## 2026-11-21 H03 正向受治理写入证据（但 H03 未完成）

[Run #44874668928](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44874668928) 确认真正 Saltcorn SQLite 中两类**自愿接入研究网关**的编辑客户端（自建 Chromium 页面、确定性模拟 Agent HTTP）能够共用原子 revision/内容指纹/幂等与实验审计：旧 Web 表单、旧 Agent 均得到 409，非冲突修改保留，并发同资源一胜一拒，错误注入无部分提交。**D01—D04 负对照**：Saltcorn 自身 Field.update 能绕过研究网关，但内容指纹漂移会触发网关失败关闭，避免继续用旧账本误写。

这为“受治理领域命令接口”提供**有限正向可行性证据**，并不证明“所有人工/Agent/插件实际写入口已统一”；网关页面是研究 UI，非原生 Saltcorn 编辑器；模拟 Agent 不是模型。**H03 平台级及真实 AI/人工交替目标仍未通过**，H01 的 Application IR vs 分域模型没有因本实验得到最终结论。G1 未通过。完整 [源码/报告](../01-research/20-governed-http-evidence.md)。

## 2026-11-21 H02/H04/H05 相关的原生业务 Trigger 实证

[真实 Saltcorn 冻结合同审批运行报告](../01-research/21-saltcorn-native-workflow-evidence.md)、[Run #44876882097](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44876882097)：3 条真正 Pack 导入的 Validate/Insert run_js_code Trigger，12 项金额规则、12 项状态机、3 条连续审批路径均通过独立物理 SQL 与运行时 API 验证，说明**低代码元数据可以与代码扩展组合实现复杂业务**。这为“配置/代码混合执行模型”提供了真实机制证据，**没有验证 AI 能识别能力缺口并选择写代码**；没有编译隔离/代码自动生成/工具权限/插件发现，故 H02/H04/H05 的 AI 目标都未通过。可伪造 actor_role 是重大身份授权缺口；内置 run_js_code 是平台高权限脚本，不能直接给不受信 Agent。G1 未通过。

## 2026-11-21 真实登录身份与原生领域 Trigger 证明了受限授权链条可行

[真实身份合同审批报告 22](../01-research/22-native-identity-approval-evidence.md)（[GitHub Actions #44879041055](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44879041055)，32/32 PASS）证实 Saltcorn 的原生 Session 用户能沿 /api/→Table.tryInsertRow→Validate/Insert Trigger 进入真正业务状态更新：如果 Trigger 用服务端 user.id/email 而不是信任请求的 actor_id/role，伪造审批人被拒绝，一级/二级审批和驳回可持久化，非管理员无法直接写审批明细及合同表。进一步证明 H05/H07 所需的**有身份上下文的类型化业务命令入口**具有原生平台机制基础，但没有实现 AI 自动规划/工具委托、企业 RBAC、强隔离或跨表原子性，因此相关平台级假设仍未验证通过。**新失败对照**：Session Cookie API 缺 CSRF 经重定向看似 200 但无业务修改，独立裁判不能仅检查 HTTP 200。G1 不通过。
