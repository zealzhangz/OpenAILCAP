# S1 实证报告 24：Agent 工具调用持久化防重放、崩溃未知结果与真实 Saltcorn 回归

**日期：2026-11-21。阶段：S1 IN_PROGRESS。结论：工具调用的同 ID 持久化防重放通过研究性故障注入测试，真实 Saltcorn 业务回归仍通过；不构成生产 exactly-once 或跨库分布式事务保证。G1 NOT_PASSED。**

## 一、研究问题

[报告 23](23-agent-tool-contract-evidence.md) 的 Broker 通过真实 Saltcorn API 执行了合同提交和两级审批，但原始 `self.calls` 仅是**进程内 set**。进程崩溃/重新启动后，同一个工具 `call_id` 可能被再次接受；如果第一次远端写入已成功、HTTP 应答丢失，再次发送会造成重复执行风险。AI Agent 的重试/恢复机制不能建立在只存在内存中的去重记录上。

本轮测试新假设：

> **H24：在调用任何 Saltcorn API 之前先将 call_id 持久化为唯一的 CLAIMED 记录，进程重启后对于相同 call_id 必须失败关闭；远端结果不确定时保留记录供对账，而不是自动再次发起批准动作。**

## 二、代码与完整执行证据

| 证据 | 固定标识 |
|---|---|
| 被测代码 Commit | [e15b36e845611170ddced1bc739bdd80b994d710](https://github.com/zealzhangz/OpenAILCAP/commit/e15b36e845611170ddced1bc739bdd80b994d710) |
| GitHub Actions | [Run #44881510363](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44881510363)，**completed / success** |
| CI Job | 136777608360 |
| 独立原始结果 Artifact | `s1-agent-tool-broker-acceptance`，ID **14698431130** |
| 工具防重放实现 | [experiments/agent-tools/broker.py](../../experiments/agent-tools/broker.py) |
| 新增 8 项故障单元测试 | [test_durable.py](../../experiments/agent-tools/test_durable.py) |
| 历史 21 项安全协议单元测试 | [test_broker.py](../../experiments/agent-tools/test_broker.py) |
| 真正的 Saltcorn 集成回归 | [integration.py](../../experiments/agent-tools/integration.py) |
| CI 固定运行底座 | Saltcorn CLI 1.7.0-beta.5、Ubuntu 24.04、Playwright 1.56、Python 3.13、SQLite |

**实际 CI 结果**：`Ran 29 tests in 0.245s / OK`（历史 21 + 新增 8），以及 `AT_RESULT {"total":29,"passed":29}`（真正 Saltcorn Session/REST/Trigger/SQLite）；共 58/58 断言通过。GitHub Actions 所有步骤（安装 Saltcorn、创建 4 位真实用户、运行实际 HTTP/审批、Artifact 上传）均成功。

## 三、事务前的持久调用占位

工具调用账本现在有两张研究表：

- `agent_tool_call_claims`：`call_id TEXT PRIMARY KEY`、受信用户、应用、工具、状态（`CLAIMED` / 最终结果）、创建与结束时间。每个新调用先向此表 **INSERT**，依靠 SQLite 唯一主键约束跨 Broker 实例拒绝相同 ID。
- `agent_tool_audit`：工具参数仅留 SHA-256 摘要、调用身份、工具与结果，不保存 Cookie、CSRF 或 API Key；正常返回时与更新 claim 状态在同一 SQLite 本地事务里执行。

调用顺序：**验证调用格式/预算与宿主身份 → INSERT 持久 CLAIMED → 能力/作用域与参数校验 → 查询 Saltcorn 当前状态 → 校验并消耗单次授权 → 发起一次真正 Saltcorn POST → 写入最终状态和审计**。若进程在 POST 之前或之后退出，CLAIMED 仍在，重启时相同 call_id 被拒绝；需要经外部事实核对再处理。

这里的 **CLAIMED 是“未知，需要对账”的安全状态**，不能因没有 COMMITTED 就推断前一个 Saltcorn 请求没有成功。唯一索引仅约束**同一 ledger 数据库内的 call_id**，不是对不同 call_id 的业务去重。

## 四、新增 8 项研究级故障实验及结果

| 对抗案例 | 已证实行为 |
|---|---|
| 已完成只读调用，重新构造 Broker | 同 call_id 拒绝，旧结果持久保留 |
| 已完成变更后“重启” Broker | 同 call_id 被拒，Fake Adapter 的实际写入计数仍为 1 |
| 已占位 CLAIMED 但尚未 I/O 即模拟崩溃 | 新 Broker 查询到 CLAIMED、相同 ID 不得再次调用 |
| Fake Adapter 模拟远端已写入后断连 | 原执行返回 UNKNOWN_REMOTE_OUTCOME，账本保留该状态；新 Broker 不得重新写 |
| 调用账本预留失败 | 拒绝执行，Fake Adapter 写入计数为 0 |
| 同 ID 换工具名称重放 | 唯一约束拒绝，不能靠换工具绕过 |
| 进程重启后沿用旧授权 token | 授权仅存在当前可信宿主实例，重启后拒绝 |
| 独立读取本地调用/审计账本 | call state 与 SHA-256 参数摘要真实落库，无参数原文 |

这 8 项是**确定性故障模拟**，未在真正 Saltcorn 网络途中执行 kill -9，不能宣称已覆盖生产规模的多节点故障窗口。它们只支撑调用去重机制及故障情况下的 fail-closed 行为。

## 五、真实 Saltcorn 回归验证并未退化

新增持久化占位后，原 29 项 Chromium + 原生 HTTP + 物理 SQLite 集成仍全部通过，包含真实四用户登录、受控 Manifest 增加只读路由工具、跨用户/资源/过时授权拒绝，以及宿主模拟授权后的**三次真正 Saltcorn 原生 POST**：

`Draft → Submitted → Level1Approved → Approved`，物理审批明细 **2 条**；工具审计仍为 **16 条**，其中授权调用 3 次、拒绝 10 次。此结果证明持久调用账本没有干扰研究用正常业务链路，但仍不能作为真实 Agent 模型完成开发的证据。

## 六、剩余高风险及否定条件

1. **同 ID 防重放 ≠ 业务 exactly-once**：新 call_id 可以对应同一业务动作。必须在 Saltcorn 原生业务服务端支持稳定请求幂等键和唯一约束，并验证插入请求、状态转移、审批记录在同一可靠事务内提交；不能只依赖客户端账本。
2. **Broker Ledger 与 Saltcorn 业务数据库不是一个分布式原子事务**：在第一次 Saltcorn 业务写入后、Broker 记录结果前断网/崩溃会产生不确定状态。当前策略是阻断重放并要求核对/人工补偿，不是自动事务恢复。
3. **跨机器高可用未验证**：实验为本机 SQLite，未验证 Broker 横向扩容、共享 PostgreSQL 账本/串行化读写、网络分区和真正多进程并发竞争。
4. **真实人工授权仍未实现**：`trusted_user_confirmed=True` 来自受信测试控制器，不是实际审批按钮/有签名的身份委托。不可暴露给模型。
5. **没有真实 LLM 推理**：GitHub CI 默认 `model_inference_executed=false`；没有证据说明模型做了工具选择或自然语言规划。
6. **固定角色映射/金额类型/HTTP 状态码的历史差距仍然存在**：研究邮箱映射、Saltcorn role_id=80、金额 TEXT+整数分、原生拒绝 400/401 不等于冻结 TC04 403。

## 七、对阶段门禁的影响

**S1 保持 IN_PROGRESS；G1 仍为 NOT_PASSED；冻结 TC01—TC18 完整 PASS 依然 0/18。** 本次进一步验证了“类型化工具 Broker + 持久调用账本 + 不重试未知写入 + 真实平台状态复核”的可实施机制，并列出正式产品仍须解决的业务幂等、强事务、真实模型选择、真实用户委托与多应用安全边界。

下一轮应优先用**受限真实模型**执行工具选择的对照测试（需受信 HTTPS 模型服务和密钥），并以原生插件/后端幂等控制和故障注入补足 G1 的关键技术风险，不应继续将研究模拟状态提升为完整产品验收。
