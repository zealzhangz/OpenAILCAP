# S1 实证报告 23：类型化 Agent 工具协议、最小权限与真实 Saltcorn 执行

**日期：2026-11-21。状态：在确定性编排器驱动下的真实低代码工具安全机制通过；外部 LLM 实际推理 NOT_RUN；G1 NOT_PASSED。**

## 一、问题定义与对照方案

在 [报告 21](21-saltcorn-native-workflow-evidence.md) 中，Saltcorn 内置 Validate/Insert Trigger 真实执行了合同金额路由与两级审批；在 [报告 22](22-native-identity-approval-evidence.md) 中，4 个不同的登录 Session 可以通过原生 REST 操作审批，伪造 user_id/role 不能绕过服务端身份认证。但这些执行都由人工事先写好的脚本触发，尚未出现 AI Agent 的能力发现、类型化工具及执行控制。

本轮实际比较两种可执行方向：

| 方案 | 机制 | 实际证据 | 判断 |
|---|---|---|---|
| A：将 Saltcorn 原生 CRUD / run_js_code 直接暴露给 Agent | Agent 可任意提交代码、表名、角色及 API 参数 | 前序真实研究已发现原生 UI/CLI 可绕过独立账本、任意代码 Action 在平台权限内运行；本轮不执行危险 shell | 高风险，**不推荐直接采用** |
| B：Trusted Orchestrator + Typed Tool Broker + Saltcorn Native API | 模型只能发出固定工具名+JSON 参数，执行器绑定真实 Session、scope、资源、动作、有效期和人工授权；所有成功变更经原生 Saltcorn API 落库 | 本轮实际 **21/21 单元 + 29/29 真实 Saltcorn 验收**，包含服务端拒绝、原生审批操作和真实 SQLite 状态 | **限域可行**，但必须补充正式委托、并发安全和模型真实调用 |

不是通过固定 Prompt 告诉模型不要越权，而是即使收到未知工具名、伪造 actor_id、跨合同、过期与重复授权，实际工具执行器也拒绝请求。

## 二、独立原始证据

| 证据项 | 固定标识 |
|---|---|
| GitHub Actions | [Run #44881082333](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44881082333)，completed / **success** |
| Tested HEAD | [109dd420e48f2cd545f120ede450c47d5c82917e](https://github.com/zealzhangz/OpenAILCAP/commit/109dd420e48f2cd545f120ede450c47d5c82917e) |
| CI Job | 136776285247 |
| 原始结构化结果 | Artifact `s1-agent-tool-broker-acceptance`，ID **14698057458** |
| 安全单元测试 | `python3 -m unittest discover -s experiments/agent-tools -p test_broker.py -v`，**Ran 21 tests / OK** |
| 真实平台集成 | `experiments/agent-tools/integration.py`，**AT_RESULT total=29 / passed=29** |
| 实际低代码平台 | @saltcorn/cli 1.7.0-beta.5、Ubuntu 24.04、Playwright 1.56、SQLite |
| 研究代码 | [broker.py](../../experiments/agent-tools/broker.py)、[model_client.py](../../experiments/agent-tools/model_client.py)、[unit tests](../../experiments/agent-tools/test_broker.py)、[integration](../../experiments/agent-tools/integration.py) |
| 冻结测试场景 | [spec.json](../../experiments/contract-benchmark/spec.json)，未修改；18 项完整合同验收仍 0/18 |

## 三、真实测试中的工具协议与结果

浏览器侧实际登录 4 位不同的 Saltcorn 用户：Creator、Approver1、Approver2、Viewer。经标准 Session/CSRF 得到只在执行器内部绑定的 TrustedSession。模型/不可信调用不能提供或覆盖 user.id、Cookie、CSRF 或审批授权。

| 测试 | 实际结果 |
|---|---|
| AT01 ×4 | 4 个 Chromium 原生登录、CSRF 页面均成功，Saltcorn users.role_id=80 |
| AT02/04 | Viewer 初始工具目录只读；加入允许的 `route-inspector` Manifest 后新增 `contract.route`，未修改核心 Broker |
| AT03/07/08 | Shell handler、未知 `system.shell`、额外 actor_id/role 参数实际拒绝；没有运行 shell |
| AT05 | 真正 Saltcorn REST 返回 S1-AGENT-HIGH-1，金额 100000001 分、状态 Draft，与物理 SQLite 一致 |
| AT06 | 动态声明的 route 工具根据真实合同金额给出 HIGH；独立 SQLite 读取真实平台路由表也得到 HIGH |
| AT09—13 | 无明确授权的写入、Viewer 写入、Agent 企图索取授权、审批人企图提交、另一应用伪造 Session 均拒绝 |
| AT15—18 | 授权超过 TTL、跨用户、跨合同、客户端持有过时状态，全部拒绝，物理合同没有被错误修改 |
| AT19 | 可信研究宿主显式模拟人工许可，Creator 通过代理调用 Saltcorn **原生 POST**，物理合同状态 Draft→Submitted |
| AT20 | 同一授权 Token 再次使用被拒绝，没有重复业务调用 |
| AT21 | 普通 Creator 企图绕开动作 API 直接改合同主表：Saltcorn 返回 HTTP 401，物理状态保留 Submitted |
| AT22 | Approver1 有单独一次性授权后，原生审批实际更新为 Level1Approved |
| AT23 | Approver1 企图再次终审被 Saltcorn 原生业务 Trigger 拒绝，数据库仍是 Level1Approved |
| AT24 | Approver2 有单独一次性授权后，Saltcorn 原生业务状态 Approved，物理审批明细恰好 **2 条** |
| AT25 | Viewer 再经原生 REST 查询，状态 Approved，与独立物理 DB 一致 |
| AT26 | SQLite Agent 工具审计共 **16 条**，其中执行器接受原生写入 **3 次**、拒绝 **10 次**；日志存参数 SHA-256 摘要，不存 Saltcorn Cookie/CSRF/密码 |
| AT27 | 明确验证 `model_inference_executed=false`，未把确定性工具调用伪称真实 LLM 推理 |

**全部 29/29 条真实 Saltcorn 集成断言通过，全部 21/21 条 stdlib 安全单元测试通过。** GitHub Actions 运行完成并上传原始独立结果。

特别说明：本轮脚本中的“真实审批”是 Saltcorn 物理表真实修改，但授权由**可信研究控制器传入的 trusted_user_confirmed 布尔值模拟**，没有实际人工弹窗、审批签名或银行级二次确认。因此只能证明“授权被独立提供之后，执行器能拦截不受许可的请求”，不能声称取得真实人的授权。

## 四、能力发现及“配置还是代码”的实验边界

本轮允许加载 `route-inspector v1.0.0` 的声明式 Manifest，Handler ID 只能是 allowlist 中的 `route_inspector_v1`；任何任意代码/外部 URL/命令的 Handler 注册均失败。由此验证“**工具目录可受控扩展而不修改核心编排器**”这一最小机制，但并未安装真实第三方运行插件、验证沙箱或插件升级兼容；TC14 仍不是完整 PASS。

此工具探针同时区分了只读能力、危险的状态变更能力和 Native API：只读工具直接查询 Saltcorn，写工具必须拿到独立授权。**模型尚未真实选择工具**，因此本轮不构成 AI 自行判断配置还是代码、自动安装扩展、自动发布等 TC06/07/09 的端到端证明。

## 五、外部大模型执行通道的实证限制

[GitHub 官方文档：GitHub Models retired](https://docs.github.com/en/github-models) 已在 2026-07-30 终止 playground、catalog、inference API 以及 BYOK。旧版 GitHub Actions `models: read` 和 GITHUB_TOKEN 方案在 2026-11 不可再用于模型推理。

本研究因此提供 **可选、不在自动 CI 中默认运行**的 [model_client.py](../../experiments/agent-tools/model_client.py)：采用受信 HTTPS OpenAI-compatible Chat Completions，必须人为配置 `OPENAILCAP_LLM_CHAT_URL`、`OPENAILCAP_LLM_MODEL`、GitHub Secret `OPENAILCAP_LLM_API_KEY`，并手动 workflow_dispatch.live_model=true。运行时只将**只读工具**提供给模型，需有真实模型返回的 function tool_calls，执行器验证名称、参数及资源后，才能把真实 Saltcorn 读回记录为 AI 调用证据。

**本次成功 CI 未启用该选项、没有外部模型推理响应。真实 LLM 工具选择与独立推理评估仍是 NOT_RUN。** 在没有凭据和实测响应前不能标记已成功调用模型。

## 六、剩余的高风险与必须反对的过度结论

1. **不是多租户/组织授权**。APP_ID 固定，4 位用户均为 Saltcorn role_id=80；业务 role 由研究固定邮箱映射和受信上下文构造，尚未对实际 SSO、委托审批、调岗、行级权限和跨真实应用运行做安全审计。
2. **不是可靠的生产级人工授权**。trusted_user_confirmed 由宿主控制器提供，是研究假设；未来需与真实交互页面、签名授权、时间窗、CSRF、可信组织身份与审计关联，不能让模型触达授予 API。
3. **不是原子并发写入证明**。先读 current.status、消费授权、调用 Saltcorn 原生 API 的过程存在 TOCTOU。原生 SQLite HTTP 路径的跨表故障注入与幂等未证明，不允许自动重发 POST。网络断连可能处于 UNKNOWN_REMOTE_OUTCOME，需做状态核对。
4. **不是插件安装/隔离能力**。Manifest 只声明一个已允许的纯只读 Handler，并未执行任意插件代码或证明异常隔离。
5. **没有真正 LLM Agent，也未自主创建应用**。工具由研究人员手工实现，数据模型、Page、Trigger 也是前序实验预装；本轮的独立工具调用测试不能计为 TC06、TC07、TC09、TC14、TC17 的完整通过。
6. **字段类型/HTTP 拒绝语义缺口仍在**。合同金额仍不是数据库 decimal(12,2)；Saltcorn 原生角色拒绝 401、业务不准 400，与冻结 TC04 明确要求的 HTTP 403 不同。不得擅改验收标准。

## 七、阶段与架构建议

**阶段依旧 S1 IN_PROGRESS，G1 NOT_PASSED；冻结 TC01—TC18 完整 PASS 0/18。**

对 S2/S3 的有条件推荐是：采用**可信编排器（模型不可访问密钥）+ Manifest 能力注册 + 最小 JSON 工具契约 + 服务端权限判定 + 一次性受限写授权 + 原生平台适配器 + 独立审计与回读**。优先以受限工具命令操作而不是把 Shell、数据库连接或低代码引擎内的任意代码 API 全权交给 Agent。

下一步应优先取得真实模型调用的外部证据，再实现“LLM 根据能力目录选择配置或代码路径”的定量对照与负例；另外必须验证真实组织 RBAC、后端 CAS/事务、一致性和真正原生插件生命周期。不要把本轮成功夸大为 OpenAILCAP 已有自主开发产品能力。
