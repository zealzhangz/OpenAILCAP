# S1 真实人工浏览器 → Agent 受控修改 → 真实人工浏览器（安全边界实验）

## 核心实验问题

前序 [报告 19](../../../docs/01-research/19-real-browser-edit-evidence.md) 已通过真实 Saltcorn 1.7.0-beta.5 和 Chromium 证明：两个旧浏览器表单可以发生静默覆盖；只给 Agent 接一个外部版本账本，也无法检测原生浏览器变更。本轮在**相同真实第三方平台**上补充一个带 DeepSeek 参与的**Agent 正向受控写入**，并以人工第二次真实浏览器编辑检验增量变更是否保留。

这**不是**修改了 Saltcorn 官方原生编辑器。Saltcorn 的 Web 设计器写入仍不受研究 CAS 控制，本实验只能证明 Agent 侧保护机制及顺序协作中的有限安全性，不能宣称全通道写入已统一治理。

## 已预先固定的步骤

1. 生成一份一次性的 Saltcorn SQLite 数据库，安装项目既有 [合同 Pack](../contract-pack.json)，创建一名临时管理员、原始合同记录。真实 Chromium 登录后打开 Saltcorn 官方 `/field/:id` 编辑向导，通过正常 DOM 输入/CSRF/contextEnc 多步 POST 将 `title.label` 从 `Title` 保存为 `Human First Saved`。
2. **只有真实浏览器写入与物理 SQLite 读取一致后**，从真实字段记录中提取可公开的只读快照：`title=Human First Saved`，`status=Status`。
3. 默认离线预检生成一份固定、**非 AI** 的 Patch，用于发现 Saltcorn 原生测试环境和 CAS 机制问题。只有一次性 GitHub 提交标志 `[deepseek-collab-once]` 或显式手动启用工作流后，才使用已有 GitHub Secret **`DEEPSEEK_KEY`**，通过 DeepSeek 官方 HTTPS API 调用 `deepseek-flash` **一次**。模型只能提交固定工具 `propose_native_field_patch` 结构化参数：
   `{"field":"status","expected_title":"Human First Saved","expected_status":"Status","new_label":"AI Reviewed Status"}`。
4. 可信研究执行器拒绝任何多余参数、改动 title、旧 snapshot、其他目标值、输出代码或越权身份。它使用**预先审核的人写 Native Saltcorn CLI 代码**，通过 SQLite `BEGIN IMMEDIATE`，在同一事务中读取两个字段当前 `_sc_fields.label`，确认均与模型快照一致后调用 Saltcorn 原生 `Field.update` 修改 `status.label`，再 COMMIT。**只有 Agent 写入经过这条检查**。
5. 同一个实际 Saltcorn 应用中，真实 Chromium 管理员重新打开标题字段的原生设计器，把 `title.label` 从 `Human First Saved` 再次保存成 `Human Second Saved`；通过原生设计器再次打开 status 字段，核对 `AI Reviewed Status` 可见。
6. 将模型原始 Patch **保持不变**，通过受控 CLI 再尝试执行一次。两字段快照已经不匹配，必须输出 `STALE_REJECTED`，不得再调用 `Field.update`。
7. 独立 Python 只读核验原生 `_sc_fields`、合同业务记录、Web /api 和原生 List View，区分人工写入、真实模型提议、Agent 原生更新及旧 Patch 拒绝的各自证据。

## 研究对象与源码

- [human_browser.py](human_browser.py)：复用现有真实浏览器多步向导 `save_wizard`，读取并保存真实人类模拟 UI 操作前后的物理记录。这里的“人工”指**浏览器模仿真实管理人员操作界面**，并非真实人手动点击。
- [propose.py](propose.py)：可选真实 DeepSeek 单次工具规划；默认是显式标记的 deterministic preflight；只读真实快照不含 Cookie、CSRF、Key。
- [make_agent.py](make_agent.py)：静态模板+严格检查 JSON 参数，无模型生成的 JavaScript。
- [guarded-agent-template.js](guarded-agent-template.js)：原生 `Field.update` 与数据库条件检查，使用 SQLite 事务绑定 Agent 的快照判断；输出 `APPLIED` 或 `STALE_REJECTED`，不假冒真实 HTTP 409。
- [test_contract.py](test_contract.py)：无模型对抗单元测试。
- [verify.py](verify.py)：独立物理 SQL、Saltcorn HTTP、模型调用范围和真实浏览器读回共 16 项断言。
- [GitHub Actions](../../../.github/workflows/s1-collab-editor.yml)：默认**不发 DeepSeek 付费请求**，先跑纯平台预检；平台验收通过后才允许一次真实模型请求。

## 严格限制与 G1

- 该实验使用 Saltcorn **CLI 管理员上下文**执行受审查的 Agent Patch，不构成已经实现企业级身份委托与权限控制。模型本身没有 CLI 密钥、Shell、JS 执行能力，批准来自研究控制器，并非真实人工签署授权。
- Saltcorn **原生 UI 不具有 expectedRevision / CAS**。旧标签页的浏览器写入仍可能覆盖新改动，前序负对照已经证明危险。因此本轮即使正向顺序流程成功，也只提供 Agent 单写路径的部分安全证据，**不能把 H03 标记为完整通过**。
- 模型只提供受限的 Label Patch，不是自主设计完整应用，不覆盖可编辑 IR、业务代码、数据库 Schema、权限、多租户与发布回滚；不证明 AI 自动创建/修复。
- 不验证网络分区、跨数据库原子事务、并发运行中的所有数据争用与任意外部插件写入；研究仅在单机 SQLite 的标题与状态两个元数据字段上开展。
- 冻结合同 18 项完整 TC 未改变，G1 仍 NOT_PASSED。

研究通过**必须**同时满足真实平台、真实浏览器人工模拟、真实模型提议、真实 Native Field.update 和过时 Patch 拒绝；不得将仅离线预检的通过说成“真实 DeepSeek 人机协同已通过”。

## 2026-11-21 实际平台离线预检

[GitHub Actions #44885046889](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44885046889) completed/success，8/8 审查单元、16/16 浏览器/原生 Field.update/物理 SQLite/API/HTTP 验收。真实 Chromium 第一次保存 `Human First Saved`，由明确标注 `model_inference_executed=false` 的固定 Patch 将 status 改为 `AI Reviewed Status`，第二次原生浏览器将 title 改为 `Human Second Saved`，AI status 标签在原生设计器真实可见，旧 Agent Patch 再次执行输出 `STALE_REJECTED`，没有尝试写入。原始 Artifact **14699452051**。此结果只是**无模型平台预检**，并非 DeepSeek 的人机协同成功证据。

第一次 [Run #44884822563](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44884822563) 实际浏览器操作和 Native CAS 均已成功，但独立解析器误将 Saltcorn CLI 回显的 JavaScript 源码事件标记当成 JSON，造成 CI failure；后续修正为严格匹配日志行起始标记并增加单元测试，完整预检才成功。失败历史保留。
