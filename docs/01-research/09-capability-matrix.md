# S1 四平台低代码与 AI 能力对照矩阵（证据分级版）

> 核对日期：2026-11-21。基准：README.md 第一阶段 1.2/1.3。**无任何一格表示“真实平台验收通过”。** 状态只对本次已读取的一手文件/官方说明负责，不为产品全部功能下结论。机器可读源见 [capability-matrix.json](capability-matrix.json)。

## 研究方法与状态说明

- **SRC**：本次静态读取或定位了实现/测试源码；只能证明存在相关实现位置，不能证明端到端可用。
- **DOC**：官方文档描述；不能把功能宣传等同实现。
- **BND**：真实能力涉及未公开 EE 服务端、许可证或 edition 门槛，不能把 CE 视为已经具备。
- **?**：未验证，不等于不支持，也不计为缺失。

特别注意：NocoBase **v3 Core** 是以源码与 Agent 开发为主要路径，不应直接把 NocoBase 2 的无代码设计器功能移植到 v3 评价里；Budibase 的**业务 Agent**不等于 AI 自主开发 Agent；Appsmith 的 **Ask AI** 不等于“从需求到测试发布”完整自主链。

## 22 项统一能力矩阵

| ID | 能力 | ToolJet | Appsmith | Budibase | NocoBase v3 |
|---|---|---|---|---|---|
| F01 | 多应用创建与管理 | SRC [TJ-version](#tj-version) | SRC [AS-app](#as-app) | DOC [BD-agent-doc](#bd-agent-doc) | DOC [NB-core-doc](#nb-core-doc) |
| F02 | 业务数据与数据模型 | SRC [TJ-plan](#tj-plan) | SRC [AS-plugin](#as-plugin) | SRC [BD-bind](#bd-bind) | DOC [NB-core-doc](#nb-core-doc) |
| F03 | 页面与组件配置 | SRC [TJ-page](#tj-page) | SRC [AS-widget](#as-widget) | SRC [BD-bind](#bd-bind) | DOC [NB-core-doc](#nb-core-doc) |
| F04 | 表单和数据绑定 | SRC [TJ-page](#tj-page) | SRC [AS-widget](#as-widget) | SRC [BD-bind](#bd-bind) | DOC [NB-core-doc](#nb-core-doc) |
| F05 | 工作流/审批 | SRC [TJ-event](#tj-event) | DOC [AS-js-doc](#as-js-doc) | SRC [BD-autom](#bd-autom) | DOC [NB-workflow-doc](#nb-workflow-doc) |
| F06 | API/数据源连接 | SRC [TJ-plan](#tj-plan) | SRC [AS-plugin](#as-plugin) | SRC [BD-autom](#bd-autom) | DOC [NB-core-doc](#nb-core-doc) |
| F07 | 权限模型 | SRC [TJ-version](#tj-version) | SRC [AS-app](#as-app) | DOC [BD-agent-doc](#bd-agent-doc) | DOC [NB-core-doc](#nb-core-doc) |
| F08 | 人工可视化/代码开发 | SRC [TJ-page](#tj-page) | SRC [AS-widget](#as-widget) | SRC [BD-bind](#bd-bind) | DOC [NB-core-doc](#nb-core-doc) |
| F09 | 自定义代码与扩展点 | BND [TJ-codeCE](#tj-codece) | DOC [AS-js-doc](#as-js-doc) | SRC [BD-autom](#bd-autom) | SRC [NB-define](#nb-define) |
| F10 | 插件注册及扩展 | DOC [TJ-ai-doc](#tj-ai-doc) | SRC [AS-plugin](#as-plugin) | SRC [BD-autom](#bd-autom) | SRC [NB-define](#nb-define) |
| F11 | 版本/发布/回滚 | SRC [TJ-version](#tj-version) | SRC [AS-page](#as-page) | ? | DOC [NB-cli-doc](#nb-cli-doc) |
| F12 | AI 自然语言理解/辅助 | DOC [TJ-ai-doc](#tj-ai-doc) | DOC [AS-ai-doc](#as-ai-doc) | DOC [BD-agent-doc](#bd-agent-doc) | SRC [NB-agent](#nb-agent) |
| F13 | AI 自动创建数据模型 | BND [TJ-plan](#tj-plan) | ? | ? | DOC [NB-core-doc](#nb-core-doc) |
| F14 | AI 自动生成/修改页面 | BND [TJ-plan](#tj-plan) | ? | ? | DOC [NB-core-doc](#nb-core-doc) |
| F15 | AI 自动编排审批流程 | BND [TJ-plan](#tj-plan) | ? | ? | ? |
| F16 | AI 自动编码、构建、集成 | BND [TJ-codeCE](#tj-codece) | ? | ? | SRC [NB-runner](#nb-runner) |
| F17 | AI 自主测试/修复/部署 | BND [TJ-codeCE](#tj-codece) | ? | ? | SRC [NB-runner](#nb-runner) |
| F18 | AI/人工多轮双向编辑 | SRC [TJ-sync](#tj-sync) | ? | ? | DOC [NB-core-doc](#nb-core-doc) |
| F19 | 插件能力自动被 AI 发现 | BND [TJ-plan](#tj-plan) | ? | ? | DOC [NB-cli-doc](#nb-cli-doc) |
| F20 | 多应用安全隔离 | SRC [TJ-isolation](#tj-isolation) | SRC [AS-app](#as-app) | ? | SRC [NB-isol](#nb-isol) |
| F21 | 机器可读平台能力契约 | SRC [TJ-plan](#tj-plan) | ? | ? | DOC [NB-cli-doc](#nb-cli-doc) |
| F22 | 隔离执行不可信代码 | BND [TJ-codeCE](#tj-codece) | DOC [AS-js-doc](#as-js-doc) | ? | SRC [NB-isol](#nb-isol) |

各格的主证据索引见下文链接；逐格状态、来源 ID、限制文字和版本信息可由 JSON 自动读取。

## 关键差异与应避免的类比

1. **ToolJet：可视配置与 MCP 的连接思路**。有页面/事件/版本的服务端 TypeORM 源码与 MCP 结构化计划、编辑同步测试；但 Code Mode 服务端的 CE 文件是 stub，真正实现需要 EE。不能把 MCP 客户端测试自动推论为可免费独立部署的 Code Mode。
2. **Appsmith：传统人工低代码及其发布状态**。Widget registry、ApplicationServiceCEImpl 与 NewPage 的 unpublishedPage/publishedPage 都有源码；适合作为人工作业基线。其数据源插件侧重连接外部系统；Ask AI 的功能边界以官方说明为准，**未验证端到端 AI 自动开发**。
3. **Budibase：表单/数据绑定和自动化**。Svelte Builder 的 dataBinding 和 server automations/actions.ts 有清晰位置，包括 AI/Agent Automation Step。该 Agent 主要用于业务操作，不等于可修改平台工程源码、自动构建并部署的开发 Agent。
4. **NocoBase v3：代码优先 Core + Agent Runner + 插件契约**。server definePlugin、Agent Plugin、Runner 具有分层设计；**与 v2 无代码产品应分开比较**。v3 LICENSE.txt 具有附加平台发布限制，代码复用风险需独立法律核查。

## 源码版本（固定 SHA）

- ToolJet/ToolJet：`d2f09ed9ab6c6cf289abfc8aa7ee77c1264aaeb0`
- ToolJet/tooljet-mcp：`8a178ad34f6e3326b6957503ca4ed4f555d23096`
- Appsmith：`0a6f6934fb33c06ee0a132c5baba78e006611621`
- Budibase：`724cb529d7b32fde84ae537e4b44673cf0618dad`
- NocoBase v3：`0894734040c3d30d4f4f3d7a6da98ae22f365f80`

### 一手证据与官方文档索引

<a id="tj-page"></a>
- **TJ-page**：https://github.com/ToolJet/ToolJet/blob/d2f09ed9ab6c6cf289abfc8aa7ee77c1264aaeb0/server/src/modules/apps/services/page.service.ts
<a id="tj-event"></a>
- **TJ-event**：https://github.com/ToolJet/ToolJet/blob/d2f09ed9ab6c6cf289abfc8aa7ee77c1264aaeb0/server/src/modules/apps/services/event.service.ts
<a id="tj-version"></a>
- **TJ-version**：https://github.com/ToolJet/ToolJet/blob/d2f09ed9ab6c6cf289abfc8aa7ee77c1264aaeb0/server/src/modules/versions/repository.ts
<a id="tj-codece"></a>
- **TJ-codeCE**：https://github.com/ToolJet/ToolJet/blob/d2f09ed9ab6c6cf289abfc8aa7ee77c1264aaeb0/server/src/modules/code-mode-source/service.ts
<a id="tj-plan"></a>
- **TJ-plan**：https://github.com/ToolJet/tooljet-mcp/blob/8a178ad34f6e3326b6957503ca4ed4f555d23096/src/appPlanSchema.ts
<a id="tj-sync"></a>
- **TJ-sync**：https://github.com/ToolJet/tooljet-mcp/blob/8a178ad34f6e3326b6957503ca4ed4f555d23096/tests/codeAppSync.test.ts
<a id="tj-isolation"></a>
- **TJ-isolation**：https://github.com/ToolJet/tooljet-mcp/blob/8a178ad34f6e3326b6957503ca4ed4f555d23096/tests/codeAppIsolation.test.ts
<a id="tj-license"></a>
- **TJ-license**：https://github.com/ToolJet/ToolJet/blob/d2f09ed9ab6c6cf289abfc8aa7ee77c1264aaeb0/LICENSE
<a id="tj-ai-doc"></a>
- **TJ-ai-doc**：https://docs.tooljet.ai/docs/build-with-ai/generate-applications/
<a id="as-widget"></a>
- **AS-widget**：https://github.com/appsmithorg/appsmith/blob/0a6f6934fb33c06ee0a132c5baba78e006611621/app/client/src/widgets/registry.ts
<a id="as-app"></a>
- **AS-app**：https://github.com/appsmithorg/appsmith/blob/0a6f6934fb33c06ee0a132c5baba78e006611621/app/server/appsmith-server/src/main/java/com/appsmith/server/applications/base/ApplicationServiceCEImpl.java
<a id="as-page"></a>
- **AS-page**：https://github.com/appsmithorg/appsmith/blob/0a6f6934fb33c06ee0a132c5baba78e006611621/app/server/appsmith-server/src/main/java/com/appsmith/server/domains/NewPage.java
<a id="as-plugin"></a>
- **AS-plugin**：https://github.com/appsmithorg/appsmith/tree/0a6f6934fb33c06ee0a132c5baba78e006611621/app/server/appsmith-plugins
<a id="as-license"></a>
- **AS-license**：https://github.com/appsmithorg/appsmith/blob/0a6f6934fb33c06ee0a132c5baba78e006611621/LICENSE
<a id="as-ai-doc"></a>
- **AS-ai-doc**：https://docs.appsmith.com/build-apps/how-to-guides/use-ask-ai
<a id="as-js-doc"></a>
- **AS-js-doc**：https://docs.appsmith.com/write-code/overview
<a id="bd-bind"></a>
- **BD-bind**：https://github.com/Budibase/budibase/blob/724cb529d7b32fde84ae537e4b44673cf0618dad/packages/builder/src/dataBinding.ts
<a id="bd-autom"></a>
- **BD-autom**：https://github.com/Budibase/budibase/blob/724cb529d7b32fde84ae537e4b44673cf0618dad/packages/server/src/automations/actions.ts
<a id="bd-license"></a>
- **BD-license**：https://github.com/Budibase/budibase/blob/724cb529d7b32fde84ae537e4b44673cf0618dad/LICENSE
<a id="bd-agent-doc"></a>
- **BD-agent-doc**：https://docs.budibase.com/docs/agent-building-101
<a id="bd-install-doc"></a>
- **BD-install-doc**：https://docs.budibase.com/docs/docker-compose
<a id="nb-define"></a>
- **NB-define**：https://github.com/nocobase/nocobase/blob/0894734040c3d30d4f4f3d7a6da98ae22f365f80/packages/app/app-server/src/plugins/define.ts
<a id="nb-agent"></a>
- **NB-agent**：https://github.com/nocobase/nocobase/blob/0894734040c3d30d4f4f3d7a6da98ae22f365f80/packages/plugins/app-plugin-agents/server/plugin.ts
<a id="nb-runner"></a>
- **NB-runner**：https://github.com/nocobase/nocobase/blob/0894734040c3d30d4f4f3d7a6da98ae22f365f80/packages/app/agent-runner/src/core/job-worker.ts
<a id="nb-isol"></a>
- **NB-isol**：https://github.com/nocobase/nocobase/blob/0894734040c3d30d4f4f3d7a6da98ae22f365f80/packages/app/agent-runner/src/core/isolation.ts
<a id="nb-license"></a>
- **NB-license**：https://github.com/nocobase/nocobase/blob/0894734040c3d30d4f4f3d7a6da98ae22f365f80/LICENSE.txt
<a id="nb-core-doc"></a>
- **NB-core-doc**：https://docs.nocobase.com/core/getting-started/what-is-core/
<a id="nb-workflow-doc"></a>
- **NB-workflow-doc**：https://docs.nocobase.com/core/developing-apps/business-workflows/
<a id="nb-cli-doc"></a>
- **NB-cli-doc**：https://docs.nocobase.com/core/reference/cli/
<a id="nb-approval-doc"></a>
- **NB-approval-doc**：https://docs.nocobase.com/core/using-plugins/collaboration/approval/

## 现在能得出的结论

**可以**：四平台都有对某一类基础能力有价值的实现/说明；ToolJet MCP、Appsmith 组件与发布对象、Budibase Automation、NocoBase Runner/Plugin 是不同维度的参考。

**不能**：依据本表给四平台产品功能完整度打分、宣布某项目实现了 OpenAILCAP 三模式全部能力、断定性能/安全/成本优劣，也不能据此选择 OpenAILCAP 最终架构。

## 为通过 G1 还需要的真实证据

1. 至少一个可复现的实际平台安装、版本与运行服务证据；
2. 在该平台实现同一合同管理任务，附截图/配置/API/代码工件与独立断言；
3. 针对 AI 与人工多轮修改记录实际状态读回及失败；
4. 许可可用范围确认（优先区分纯调研与平台代码复用）。

参见 [统一合同业务验收协议](10-contract-benchmark.md)。**本表属于 S1 研究交付，不构成 G1 通过。**
