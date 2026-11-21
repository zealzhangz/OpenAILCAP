# S1 最小真实 DeepSeek Function Calling 验证

**日期：2026-11-21。结果：真实模型只读工具调用 PASS；完整 AI 自主开发 NOT_RUN；G1 NOT_PASSED。**

## 配置与实际执行

- 使用用户已配置的 GitHub Actions Secret **DEEPSEEK_KEY**，只通过环境变量传给 Python 客户端，未写入 Git 历史或公开日志。
- DeepSeek 官方 Chat Completions：`https://api.deepseek.com/chat/completions`，模型 **deepseek-flash**，`thinking.type=disabled`，`tool_choice=required`，`max_tokens=256`。
- 仅一次外部模型 HTTP 推理请求；开放的两个工具均为 **只读**：`contract.read` 和 `contract.route`。审批写入 `contract.action` 不在模型工具列表中。
- 受控执行器复用真实 Saltcorn Session、只读 REST 及物理 SQLite 测试环境，没有把 Saltcorn Cookie、CSRF、用户口令、API Key 或人工授权交给模型。
- 这次使用 GitHub 提交消息中的一次性 `[deepseek-smoke]` 标识启用；**未来普通 push 不会自动产生模型调用费用**。保留手动 `workflow_dispatch.live_model` 验证选项。

## 可独立复核的真实证据

| 证据 | 结果 |
|---|---|
| 被测代码 | [Commit 9f2ca18f25855d29f49d05a915eb430096f9f51e](https://github.com/zealzhangz/OpenAILCAP/commit/9f2ca18f25855d29f49d05a915eb430096f9f51e) |
| CI | [GitHub Actions #44882955824](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44882955824)，**completed/success** |
| Job | 136782023565 |
| 结构化结果 | Artifact `s1-agent-tool-broker-acceptance`，ID **14697764457** |
| 原有安全回归 | **29/29** Python 单元测试 PASS |
| 真实 Saltcorn 集成（含外部模型） | **30/30** 断言 PASS，`AT_RESULT total=30 passed=30` |
| 外部真实模型检查 | `AT28-true-external-LLM-tool-call-real-native-read PASS` |
| 模型实际选择的工具 | **contract.read、contract.route** |
| 模型身份 | **deepseek-flash** |
| 工具最终验证 | Broker 对工具名、参数、合同编号验证，通过实际 Saltcorn 只读结果核对 |

CI stdout 中可复核原文：

```text
S1_LIVE_MODEL_ONCE: true
S1_LIVE_MODEL_EXPLICIT_OPT_IN
AT28-true-external-LLM-tool-call-real-native-read PASS {"model_id":"deepseek-flash","executed_read_only_tools":["contract.read","contract.route"]}
AT_RESULT|{"total": 30, "passed": 30}
```

## 本轮技术结论与边界

- **已验证**：真正 DeepSeek 推理返回了函数工具调用；执行器能识别、验证并运行两个只读工具；结果来自真实 Saltcorn，而非模型自行编造。
- **尚未验证**：多轮任务规划、配置路径/代码路径智能选择、AI 生成 Table/Field/View/Trigger、AI 与真实设计器交替编辑、真正人工签署授权、部署和自动修复。
- **不能声称**：“完整 AI Agent 已开发完成”“G1 已通过”“冻结合同 TC01—TC18 已完整验收”。本轮仅把 S1 的**真实模型只读工具调用**从 NOT_RUN 更新为已实测。
- 单次成功调用是**连通性和协议可行性实验**，不是统计学准确率/安全性结论。

DeepSeek 参考：[官方模型和价格](https://api-docs.deepseek.com/quick_start/pricing/)、[官方 Tool Calls](https://api-docs.deepseek.com/guides/tool_calls/)。
