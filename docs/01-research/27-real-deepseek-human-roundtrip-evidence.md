# S1 报告 27：真实 Chromium 人工编辑模拟 → DeepSeek 读取最新状态 → 守卫写入 → 人工继续编辑

**日期：2026-11-21。状态：顺序人机交替编辑的限域正向实验成功，原生编辑器全通道并发安全尚未通过；S1 IN_PROGRESS，G1 NOT_PASSED。**

## 一、研究问题

OpenAILCAP 核心三种开发模式要求人类在真实设计器编辑后能够交给 AI，AI 修改成果后又能交由人类继续维护。前序 [真实浏览器失效报告 19](19-real-browser-edit-evidence.md) 证明 Saltcorn 两个旧页面可以互相覆盖；独立 Agent 版本账本因普通 UI 不更新账本，亦会无意覆写人工编辑。

这轮验证的是比“模型能返回一个工具”更强的条件：**实际 Saltcorn 原生设计器先保存修改；DeepSeek 的工具提议必须引用该真实修改；可信执行器必须守卫人类字段并只写自己的目标；随后原生设计器能够继续编辑，而旧模型提议必须被拒绝。**

本次只覆盖 **Saltcorn title/status 两个字段元数据标签的顺序编辑**，并不修改官方的 Saltcorn Web 字段编辑路由本身。

## 二、成功运行的独立证据

| 来源 | 实际记录 |
|---|---|
| 实验代码 Commit | [c73b0319348070f670833310fb54cfa781cc17a4](https://github.com/zealzhangz/OpenAILCAP/commit/c73b0319348070f670833310fb54cfa781cc17a4) |
| 真正 DeepSeek + 真实浏览器 + 原生数据库 | [GitHub Actions Run #44885275152](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44885275152)，completed / **success** |
| 原始 Job | 136789099373 |
| 可复核原始 Artifact | s1-chromium-deepseek-collab-evidence，**14699991457**；包括两次真实浏览器观测、模型输出和独立验收 JSON |
| 真实模型 | DeepSeek **deepseek-flash**，官方 HTTPS Chat Completions，Function Calling，thinking disabled |
| 模型推理调用 | **1 次**，输入 **491 Tokens**、输出 **92 Tokens**、合计 **583 Tokens** |
| 受控代码与安全单元测试 | **8/8** 通过 |
| 实际浏览器、native Field.update、物理 SQLite、HTTP 与旧 Patch 拒绝 | **16/16** 独立断言通过 |
| 已成功的离线先决条件 | [Run #44885046889](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44885046889)，8/8 + 16/16 PASS，**model_inference_executed=false** |
| 平台版本 | 实际 npm @saltcorn/cli@1.7.0-beta.5、Playwright 1.56 Chromium、GitHub Ubuntu 24.04、SQLite |
| 工程源码 | [experiments/platform-saltcorn/collab](../../experiments/platform-saltcorn/collab/README.md) |

真实人工操作的技术含义：此处的“人工”由 **Playwright 在真实 Chromium 中模拟管理员操作 Saltcorn 原生可视化设计器**，不是某位自然人手工点击。模型所见数据来自浏览器保存后再独立读取的物理 Saltcorn 字段元数据，属于真实应用状态，不是仅在 Python 中伪造的编辑结果。

## 三、实际人机交替编辑结果

| 阶段 | 实际操作路径 | 真实状态与独立验收 |
|---|---|---|
| H1 初始 | Saltcorn 原生 /field/:id Web 向导，管理员认证、CSRF、contextEnc，真实浏览器提交三次 POST | title.label 从 **Title** 改为 **Human First Saved**；status.label 仍为 **Status**；真实 SQLite 读回 |
| M1 真正模型 | 将 H1 后 SQLite 只读快照发送至 DeepSeek，模型通过 **一次**受限 propose_native_field_patch 工具调用返回字段/快照/期望值 | 真实模型指定 field=status、expected_title=**Human First Saved**、expected_status=**Status**、new_label=**AI Reviewed Status**；本次没有给模型执行代码/数据库的权限 |
| A1 可信受控写入 | 预审核的 Saltcorn CLI Adapter，在 SQLite BEGIN IMMEDIATE 事务内重新检查 title 与 status 当前物理值，随后通过 Saltcorn 原生 Field.update 更改 status.label | 返回 **APPLIED**；title=Human First Saved，status=AI Reviewed Status；没有修改 title |
| H2 再次人工浏览器 | 相同真实 Saltcorn 环境，新的 Chromium 登录 Session，再通过原生字段编辑向导修改 title | title.label 变成 **Human Second Saved**，status.label 仍为 **AI Reviewed Status**；再次打开原生 status 编辑页面能真正看到 AI 修改 |
| A2 过时旧 Patch 负对照 | 再执行**同一份 M1 Patch**，没有重新读取、没有再调用模型，受控 Adapter 重新读取真实物理字段 | 返回 **STALE_REJECTED**，native_write_attempted=false；真实 title=Human Second Saved，status=AI Reviewed Status |
| V 独立验收 | 只读 SQLite 实际 _sc_fields / 合同业务行，以及真实 /api/s1_contracts/、/view/s1_contract_list HTTP | 最新人工与 AI 非冲突字段**同时保留**；既有 HT-2026-000001、金额 100000001 分仍在；真实 API 和 HTML 均 HTTP 200，可查合同 |

GitHub Actions stdout 可直接找到：

~~~text
S1_COLLAB_PROPOSAL|{"inference":true,"model":"deepseek-flash","field":"status","observed_human_title":"Human First Saved","observed_status":"Status","proposed_label":"AI Reviewed Status","tokens":{"prompt_tokens":491,"completion_tokens":92,"total_tokens":583}}
S1_COLLAB_NATIVE_CAS|{"decision":"APPLIED","title_observed":"Human First Saved","status_observed":"AI Reviewed Status","requested_target":"status","native_write_attempted":true}
S1_COLLAB_HUMAN|{"phase":"second","title":"Human Second Saved","status":"AI Reviewed Status","native_post_count":3,"ai_status_visible":true}
S1_COLLAB_NATIVE_CAS|{"decision":"STALE_REJECTED","title_observed":"Human Second Saved","status_observed":"AI Reviewed Status","requested_target":"status","native_write_attempted":false}
S1_COLLAB_RESULT|{"real_model":true,"passed":16,"total":16,"native_editor_side_protected":false}
~~~

## 四、可信执行边界与为何不把成功夸大为整个设计器的安全

模型**只拥有提议权**，没有管理员 Session、CSRF、SSH、SQL 或 Field.update API：

1. 模型只能调用单一工具名 propose_native_field_patch，且参数必须恰好是 field / expected_title / expected_status / new_label。
2. 只能选择 status；必须逐字引用 **真正 H1 保存后的 title/status 快照**；新的目标标签固定为 AI Reviewed Status，超出约束立即拒绝。
3. 实际 JavaScript 是实验前预装的人写原生 Adapter，不是大模型输出。执行控制层在读取时用 BEGIN IMMEDIATE + 双字段物理对照，冲突即 ROLLBACK，**不提交**。
4. 旧 Patch 被拒绝只代表受控 CLI **Agent 写入路径**有碰撞保护，不是 Saltcorn Web 原生编辑器能返回 HTTP 409。这里的 STALE_REJECTED 是研究 Adapter 的 CLI 结果，不是原生 HTTP 状态码。

**关键尚存风险：Saltcorn 原生浏览器 POST /field 不经 Agent 的版本守卫，因此浏览器旧表单仍可覆盖新值**。前序 [报告 19](19-real-browser-edit-evidence.md) 已在真实 Chromium 中复现了该危险失效，且并未在本轮改造原生浏览器 Handler。自然人和 Agent 的**安全并行编辑**、跨插件写入安全、事务与审计统一治理仍需在后续架构设计和第三阶段 PoC 中实现强一致写入入口。

本轮是顺序工作流中的**非冲突编辑保存及旧 Agent Patch 的拒绝**；不是任意顺序、任意字段及同时并发的完整无丢更新证明。

## 五、模型费用、失败历史和独立裁判

为了节省外部模型调用，先运行**无模型平台预检**：

- 初次 [Run #44884822563](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44884822563) 的真实浏览器两次保存、Native CAS APPLIED/STALE_REJECTED 均已发生，但 Python 独立验收误把 Saltcorn CLI 回显的源码标记当成 JSON 而失败。此为裁判解析器错误，不能视为研究能力已经全部通过。
- 修正日志为“事件必须以 S1_COLLAB_NATIVE_CAS 标记开头”并增加专门单元测试后，**无模型** [Run #44885046889](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44885046889) 的 8/8 + 16/16 全部成功，Artifact 14699452051。
- 预检通过后，才允许一次性提交标记 [deepseek-collab-once] 开启真正的 DeepSeek 任务。正式 [Run #44885275152](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44885275152) 实际发出**一次推理请求**、调用一个 Function Tool，16/16 全部通过；普通后续提交不会自动再次推理。

原始 Artifact 只包含可公开的原生字段标签、脱敏模型参数、已发生的 UI 观察和独立测试结果，没有保存 API Key、真实 Session Cookie、CSRF Token 或临时管理员密码。

## 六、阶段结论与下一优先工作

本轮为 S1 的“**真正模型感知人工修改并安全接手**”提供了首次**真实第三方低代码浏览器 → 真实 DeepSeek → 原生平台增量写入 → 浏览器再次编辑**的正向限域证据。此前真实浏览器负例和本次 Agent CAS 正例应**同时保留**，不能只保留成功运行。

但项目 README 的完整 AI 自主创建业务模型、自动生成配置及代码、发布回滚、插件扩展和真实安全并发协同仍有缺口；冻结合同 TC01—TC18 仍为**0/18 完整 PASS**，不能据此直接进入 S2 或 S3。

**S1 IN_PROGRESS，G1 NOT_PASSED。** 下个阶段性工作应基于现有研究，形成正式的综合平台架构取舍、能力可借鉴/不可复用清单、候选 ADR、剩余技术假设与可证伪标准，做一次正式 G1 Go / Conditional Go / No-Go 判定；统一浏览器+Agent+插件写入的生产级一致性应作为高优先的后续 PoC 风险。
