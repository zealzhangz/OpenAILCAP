# S1 Agent → Type-Safe Tool → Real Saltcorn（限域实验）

> **这是一组研究用工具边界实验，不是“已实现 AI 开发”或正式产品 Agent。** 默认 CI 的工具调用由确定性 Python 验收器驱动，**没有调用真实大模型**。可选真实模型探针必须手动选择 workflow_dispatch.live_model 并配置外部模型凭据；没有模型 API 证据时 `model_inference_executed=false`。

## 研究目的

此前 Saltcorn 原生触发器业务执行已通过 35 个研究断言，真实四用户 Session/CSRF/审批状态通过 32 个研究断言。但这些均由人工编写代码触发，不是 Agent。新的 S1 技术风险是：

1. 模型“想调用某个工具”**不能等于**“已获授权调用”；
2. 模型不能自行填写 user_id/role 或获得 Saltcorn Cookie、CSRF、服务端凭证；
3. 自然语言任务映射成类型化工具，必须有能力发现、参数验证、应用隔离、执行审计和外部真实读回；
4. 新增插件 Manifest 不允许加载任意 Python/JS/本机 shell；
5. 审批等高风险写入必须经**可信宿主另外颁发**的短时、限定合同与动作的一次性授权；
6. 测试成功必须同时验证原生 Saltcorn 真实 HTTP 和物理 SQLite 状态。

## 工程组件

- [broker.py](broker.py)：Python 标准库的 `Broker`、`SaltcornRest`、`TrustedSession`。工具定义包含**JSON Schema 风格契约**、scope 和 mutates 属性。不是 JSON Schema 完整通用解释器；仅支持本实验的固定字段和枚举。已实现 server-side 参数白名单、可信会话、一次性授予、失效时间、调用预算、变更调用不重试、SQLite 脱敏审计。
- [test_broker.py](test_broker.py)：纯 Python 单元对抗测试；确认即使没有外部平台，也能阻断未知命令、伪造角色、重放 ID、同键跨资源、过期授权、错误角色、恶意插件代码入口等。
- [seed.js](seed.js)：通过 Saltcorn 原生 Table.insertRow 创建合同，并由真实 Insert Trigger 自动派生路由。
- [integration.py](integration.py)：在真实 Saltcorn /auth/login 中运行 4 个 Chromium 用户登录；每个真实 Session 读取 CSRF 后调用官方 /api/s1_bench_contracts/ 及 /api/s1_bench_action_requests/；审批写入和拒绝场景由原生 Validate/Insert Trigger 完成。独立读 SQLite 审计及审批明细。
- [model_client.py](model_client.py)：**可选**真实外部模型 Chat Completions tool_calls 探针。仅把已授权只读 catalog 转换为 function tool；模型消息不包含 token、CSRF、Cookie 或人工授权；必须返回 JSON tool calls，经过相同 broker 验证后才能执行。模型输入是单个只读查询，不能用于审批。
- [GitHub Actions](../../.github/workflows/s1-agent-tools.yml)：Ubuntu 24.04 + 固定 Saltcorn 1.7.0-beta.5 + Playwright 1.56 + stdlib 单元测试 + 真实 Saltcorn HTTP + DB 验收。默认不调用模型。

## 核心工具协议

| 工具 | 参数 | 操作 | 默认权限 |
|---|---|---|---|
| `contract.read` | number | Saltcorn 原生 REST GET，返回已存真实合同 | contract.read |
| `contract.route` | number | **经 allowlist 插件 manifest 注册**，根据读到的真实合同金额推导 HIGH/NORMAL，另由独立 DB 核实物理路由 | contract.read |
| `contract.action` | number、action（submit/approve/reject）、base_status | 要求同一合同、同一动作、同一已认证用户、未过期、未使用的一次性宿主授权，再请求 Saltcorn 原生 POST | contract.action + Trusted Host Grant |

模型/不可信工具调用只包含参数 JSON，**不能提交自称的 actor_id、actor_role、admin、Cookie、CSRF、Shell 命令或授权 Token**。真实审批 POST 的 actor_id/actor_role 由宿主绑定的 Saltcorn Session 生成，Saltcorn Validate Trigger 再以真正 user.id/email 校验。未授权用户的 direct contract/approval table 写入仍被 Saltcorn 自身拒绝。

`contract.action` 的主协议采取**先读当前状态、检查 base_status，再消费一次性授权，最后对真实 Saltcorn 发一次 POST**。协议明确不自动重试变更请求；当网络响应不明确时返回 UNKNOWN_REMOTE_OUTCOME，需先查询真实 DB 和审计重建结果。

## 关于“人工审批授权”的精确边界

当前的 `issue_human_grant(..., trusted_user_confirmed=True)` **由可信研究验收控制器显式调用**，模拟人工已经在独立渠道同意某个明确动作；**没有真实的人工审批按钮、签名授权存证或审查证明**。因此这一轮证明的是“经过独立受控许可后工具可执行，而模型参数不能自行获得许可”的协议机制，**不能证明现实中已经取得了某位审批人的授权**。

Token 在 Python 宿主内保管，不交给模型；`contract.route` Manifest 是**静态允许的 Handler ID**，并非真正可运行插件隔离/安装升级的端到端实验。对完整插件生命周期 TC14 仍然是部分证据。

## 对抗性验收

冻结以下场景，任何单项失败都应使 CI 红灯：

- 模型企图请求 `system.shell` 或请求参数里伪造 actor_id：拒绝；
- Viewer 的工具目录不出现写操作；无授权、跨用户、跨合同、过期、一凭据重复使用、状态过时必须拒绝；
- 未受信任 Manifest 企图注册 shell handler：拒绝，不触发本机执行；
- 真实 Saltcorn 合同读取与路由推断可追溯到原生 HTTP 和物理 SQLite；
- 由研究宿主模拟的“一次性人工授权”允许 creator 原生提交、approver1 一级审批、approver2 二级审批；查看人与错误级别审批不能绕过 Saltcorn 的业务 Trigger；
- 真正的动作请求与审批行持久化，Saltcorn HTTP 401/400/200 与物理 DB 状态相对应；
- SQLite 代理工具审计不含 Cookie、密码、CSRF、API Key，只保存参数摘要；每次变更不自动重发；
- `model_inference_executed=false`，除非确实配置模型、执行了至少一次外部 inference 且返回真实可验证的 tool_calls。

## 如何验证真实模型调用

GitHub Models 的旧推理接口**已在 2026-07-30 退役**；不要使用旧的 GITHUB_TOKEN+models:read 方案。若要运行真实模型实验，需由用户在 GitHub 仓库环境配置：

- Secret: `OPENAILCAP_LLM_API_KEY`（可信外部模型供应商 API Key）。
- Variables: `OPENAILCAP_LLM_CHAT_URL`（可用、可信 HTTPS Chat Completions Endpoint）、`OPENAILCAP_LLM_MODEL`（该服务的模型 ID）。
- 手动触发 workflow_dispatch，勾选 **live_model**。若缺少配置、模型未返回兼容的 function tool_calls、返回越权工具或资源，模型验收直接失败，不会假装成功。

**不要将密钥提交仓库、使用过期 GitHub Models 端点或在普通 CI 中自动执行写入工具。**

## 局限与 G1

这只是 S1 验证基础：应用 ID 固定、角色→邮箱为硬编码研究映射、模型默认未执行；直接模型自定义代码/插件安装/自动创建页面/自动测试修复未实现。真实 Saltcorn API 的事务原子性和重复审批请求幂等尚未验证；只在单机 SQLite 和两个合同上观察，存在状态先读后 POST 的 TOCTOU 风险。**目前不得声称 G1 或冻结 TC06/TC07/TC14/TC17 通过。** 只有原始 CI 成功且全部独立断言通过，才记录实测正向结果。

参考前序：[真实用户身份审批报告 22](../../docs/01-research/22-native-identity-approval-evidence.md)。
