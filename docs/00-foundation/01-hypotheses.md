# OpenAILCAP：八项可证伪的核心架构假设

日期：2026-11-21。状态：研究启动稿；所有假设均**尚未通过实验**。研究依据为用户仓库 README.md。不得将第三方源码存在等同于端到端执行成功。

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
