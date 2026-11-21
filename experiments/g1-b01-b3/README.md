# S1 B3：真实 DeepSeek → 受限类型化工具计划 → B2 数据模型/页面/流程/发布

> 研究原型，不是完整 PoC-A，也不是生产级自主 Agent。**默认完全离线**；真实 DeepSeek 模型只在本仓库 PR 分支的最新 Commit 消息精确等于一次性授权标记、且此前全部确定性预检成功时执行一次调用。任何模型错误立即失败关闭，不使用静态预案冒充真实模型结果。

## 实验内容

自然语言合同需求：合同编号、名称/标题、金额（人民币分）、审批状态；金额严格超过100万元进入二级审批；登记表单和合同台账显示真实合同数据。模型仅通过一个 `propose_application_plan` **函数提议**四个受限元数据定义：

- `model.contracts`：`contract_no`、`title`、`amount_minor`、`status`。
- `form.contracts`：登记表单字段。
- `view.contracts`：台账视图列与标题。
- `workflow.approval`：阈值精确为100000000分的两级审批元数据。

大模型只提交候选 JSON，没有数据库、CLI、Shell、管理员或发布权限。严格验证工具名、唯一调用、JSON 结构、资源顺序、字段类型/必填、单位换算、引用图/Workflow 语义、安全字符；验证失败，**不执行任何模型计划**。

可信工具执行器作为**独立 OS 进程**运行，读取已验证的提议，只使用 B2 HTTP `/v2/apps/app-a/commands` 接口，逐步带 revision/hash 提交 4 个元数据变更，写入 SQL 不绕过服务端。任一步失败不发布。真实 Chromium 登录并再次编辑 AI 的 Form，Agent 尝试旧版本得到409、重新读取后修改 View，旧浏览器也被409拒绝；由测试模拟的授权人工会话点击发布，Agent 直接发布得到403。

发布后，通过真实 HTTP 表单写入，运行 100000001 分和 100000000 分审批，使用真实 Chromium 读取已发布 View；独立只读 SQLite 对照事务、审计与跨 App 隔离。模型输出接受**独立结构和业务行为验收**，不依据其文字自评。

## 文件

| 文件 | 用途 |
|---|---|
| plan.py | 官方 DeepSeek HTTPS Chat Completions 的可选**单次** Function Calling；否则人写静态参考计划；机器验证安全和业务语义。无模型写权限。 |
| test_plan.py | 离线恶意提议、越权字段、单位错误、伪造工具、两次函数调用、图引用等 18 项测试。 |
| apply_plan.py | 真实独立 Python 进程使用最小 Bearer，仅 HTTP 读取草稿并提交 typed commands；不用数据库直连、插件权限或发布权。 |
| experiment.py | 真正 Chromium 人工界面、真实提议或离线基线、Agent 工具子进程、互改、发布、业务运行和独立 SQLite/浏览器双证据。 |
| .github/workflows/s1-b3-deepseek-app.yml | **离线优先门禁**；B3+旧 B2 单元测试、Chromium 全流程离线通过才允许单次 live。Raw logs/JSON artifact 保留，失败也上传。 |

## 本地离线复现

预备 Python3.13、Playwright1.56 和 Chromium；在项目根目录：

~~~bash
python3 -m pip install playwright==1.56.0
python3 -m playwright install --with-deps chromium
cd experiments/g1-b01-b3
python3 -m unittest -v test_plan
python3 experiment.py --mode offline --output /tmp/s1-b3-offline.json
~~~

### 真正模型模式的防误调用设计

工作流只在 PR 的 HEAD Commit **消息完全等于** `research(s1): authorize exactly one DeepSeek B3 smoke [b3-deepseek-once]` 且**离线单测+浏览器场景全绿**后，注入 Actions Secret `DEEPSEEK_KEY` 并执行**单次**请求。普通 CI、合并到 main、人工 workflow_dispatch 不会调用模型。**切勿在未经授权的 CI 中复用该标记，也不要重复执行此旧提交**。

模型名称固定 `deepseek-flash`；HTTP 超时后不自动重试（结果可能 UNKNOWN），仅记录调用是否完整返回、是否通过工具参数审查、token 使用与安全的已验证定义。**不会上传 API Key、Authorization Header、Session Cookie、原始未校验的模型返回内容**。

## 限制与关口

该实验输入为固定领域合同需求，并给模型明确可用字段、资源 ID 和受限工具契约，因而只支持此狭窄案例；不是任意自然语言开发、自动需求消歧、Agent 自主决策、动态代码生成或失败自主修复。B2 实验只有 JSON 编辑器、固定合同执行器和 SQLite 快照发布，不是 Vue/React 低代码拖拽引擎、真正自定义代码构建、正式企业 RBAC 或插件隔离。

成功时可确认 **“真实 LLM 可以提出被安全审核并执行的受限低代码配置计划”**，而不能宣称完整 AI 自动创建企业应用、G1/W01–W24 或 TC01–TC18 全部 PASS。失败时保留原始运行/拒绝证据，不通过扩大允许范围来掩盖失败。
