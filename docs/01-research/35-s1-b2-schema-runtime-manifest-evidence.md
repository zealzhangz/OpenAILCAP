# S1 研究报告 35：B2 Domain Schema + Form/View/Workflow + 发布 Manifest 完整运行实验

**日期：2026-11-21。结论：B2 小范围实测成功，G1-B01 仍部分验证、G1 NOT_PASSED。**

## 1. 本次问题及明确实验范围

上一轮 [报告 34](34-g1-b01-b1-browser-agent-plugin-evidence.md) 已证明自有两字段 HTML 人工编辑器和确定性 Agent/Plugin 进程可以共享一个实际 CAS/审计写入入口，但无法说明一个**真实低代码应用模型**怎样在人工和 Agent 间安全交接，怎样保证 DataModel→Form/View→Workflow 的引用约束，以及如何发布并在失败时保护运行版。

本轮在已有 C1/B1 架构原则上新建 **受限的 SchemaStore V2 原型**，不再局限于 label/status 字符串，而是操作一套 DataModel / Form / View / Workflow 元数据资源：这些定义以每资源 hash/revision 和整应用 manifest hash/revision 实际写入 SQLite，人工与 Agent 走同一个 HTTP /v2/apps/{app}/commands 可信路径。运行态表单写入业务记录、视图查询数据、工作流改变业务状态，发布通过不可变 Manifest 快照与指针隔离草稿和运行版。

**重要事实边界**：B2 实现是**C1 机制的泛化、独立工程**，并没有在同一进程中直接调用之前 C1 的 Store.apply；它仍是研究代码，不是已经统一整合好的完整 OpenAILCAP 内核。

## 2. 实际代码、提交与 CI

| 证据 | 可回溯位置 |
|---|---|
| 主线代码 | [experiments/g1-b01-b2](../../experiments/g1-b01-b2/README.md) |
| 真实 PR 审查与合并 | [PR #4](https://github.com/zealzhangz/OpenAILCAP/pull/4)，已 Squash 到 main |
| 合并提交 | [3ed689c](https://github.com/zealzhangz/OpenAILCAP/commit/3ed689c12ea2b466a25c0af6e38cb51bc8b4e2bf) |
| 固定 CI 工作流 | [.github/workflows/s1-b2-schema-runtime.yml](../../.github/workflows/s1-b2-schema-runtime.yml) |
| 原始 GitHub Actions 运行 | [#44889712124](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44889712124)：**completed / success** |
| Job | **136802678273**，schema-graph-and-runtime |
| 原始自动上传 Artifact | [#14700803450](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44889712124/artifacts/14700803450)（18 项 unittest 日志 + 27 项浏览器/Agent 逐条 JSON 和日志） |
| 18 项引擎层单测 | **Ran 18 tests in 0.315s, OK，18/18 PASS** |
| 27 项真实端到端检查 | **S1_B2_RESULT {passed: 27, attempted: 27, expected: 27}** |
| 运行环境 | Ubuntu 24.04；Python 3.13；Playwright 1.56；真 Chromium；临时 SQLite；Agent 独立 Python 子进程 |
| 模型调用与费用 | **0 次**外部推理；没读取 DEEPSEEK_KEY |

这里的“27 项真实端到端”是本实验 B2-01—B2-27 的小范围预定断言，**不是**冻结 G1-B01 W01—W24 的 24 项完整验收。

## 3. 已实测成立的工程机制

### 3.1 元数据图、真实写入与引用闭包

- Agent 独立进程通过 typed HTTP 命令依次创建四种资源：model.contracts、form.contracts、view.contracts、workflow.approval，应用草稿 revision 从 0 变为 4；物理 SQLite 的 Manifest SHA-256 与服务读取一致（B2-02—06）。
- 真 Chromium 管理员登录后打开两个旧草稿标签（revision 4）；人工将表单标题改为“合同登记 · 人工维护”，revision 5；Agent 持旧 appRevision=4 修改 View，被服务端 **409 APP_REVISION_CONFLICT** 拒绝。Agent 显式重新获取草稿后修改列表列清单，revision 6，人工 Form 标题被保留；未刷新的人类标签再提交同一 Form 同样 **409**，重新加载后能看到 Agent 更改（B2-07—14）。
- Schema 完整性由可信服务端在 SQLite 单事务中验证：删除被 Form/View/Workflow 引用的 Model → **422 BROKEN_MODEL_REFERENCE**；在 View 添加不存在字段 → **422 BROKEN_FIELD_REFERENCE**。单元层还确认已有业务记录时更改字段类型/删除原字段必须先显式迁移（MIGRATION_REQUIRED），禁止默默改坏老数据（B2-21、22）。

### 3.2 真正业务运行（不是只校验 Schema）

- 人工发布有效元数据图产生不可变 Release v1；普通 Agent Token 尝试发布收到 **403 PUBLISH_FORBIDDEN**（B2-15、16）。
- 已发布 Form 对合同数据做 required/string/integer 验证；字符串金额被 **422 TYPE_MISMATCH** 拒绝。成功创建 2 条真实 SQLite 业务记录，自动 Draft 状态（B2-17、18）。
- 原生受限 Workflow 依金额（整数分）驱动状态：**100000001 分**需要 PendingLevel1→PendingLevel2→Approved；**100000000 分**恰好阈值只需 PendingLevel1→Approved。重复审批被 **409** 拒绝，均可在物理记录核验（B2-19）。
- 真 Chromium 点击运行态 View，调用发布快照下的 HTTP 视图 API，实际读取两条已审批记录及 Agent 新增的“title”列（B2-20）。

### 3.3 发布一致性与旁路变化

- Release v1 后，人工修改 Draft Form 生成 appRevision 7，但运行版的 Form 标题和 Manifest 仍是旧值；使用旧草稿版本尝试发布被 **409 PUBLISH_STALE** 拒绝（B2-23、24）。
- 人工正式发布 v2，然后把发布指针审计性回滚至 v1；SQLite releases 中 v1/v2 文档 hash 未被覆盖，当前指针是 v1（B2-25）。
- 故意绕过命令服务直接 SQL 改写草稿的 view JSON（不更新其 hash），下次 GET Draft 得到 **409 RESOURCE_DRIFT** 并将草稿应用标记 QUARANTINED；再试 Publish 得到 **423**。**此前已验证的 v1 不受草稿损坏影响，运行态 View 仍 HTTP 200**（B2-26）。
- app-b 的资源和 revision 均未发生变化；外部独立只读 SQL 验证发布版、记录数和人/Agent 审计主体（B2-27）。

## 4. 架构影响与不能外推的内容

证据现在足以说明：**不先设计一个巨大、固定结构的全局 Application IR，也可以用领域分区 Schema + 计算 Manifest 建立跨资源引用、统一命令、运行与版本发布的小型自洽闭环**。

但**尚不能证明它在真实复杂企业场景优于全局 IR**：Form 目前只能编辑 JSON 文本而非拖拽组件；Model 类型只支持 string/integer；Workflow 是固定状态机，既没有真正人工审批角色隔离，也没有流程图/表达式引擎和动态插件；没有低代码多表关系、大规模迁移或生成代码；Agent 仍是确定性 CLI 任务驱动，**没有真正使用大模型理解“一句话需求”生成应用**。本轮发布是 SQLite 定义快照与指针，并非把生产应用构建部署到容器/云环境。发布/回滚与数据库行变迁之间没有实现通用 Schema Migration，因此也不能宣称跨任意版本回滚业务数据安全。

另外，本轮 B2 不等同于之前 C1 的统一生产内核：两个实验模块尚未融合；新 B2 的发布指针虽然在 SQL 事务中更新，但没有完整生产级的多发布者相互竞争协议/审批流程；Plugin 是前轮 B1 的限定 token 实验，本轮没有新增真正插件执行器。真实 LLM Agent、代码构建、发布工件、热更新缓存、恶意插件沙箱、企业身份、多数据库、部署和数据迁移仍 **NOT_RUN**。

## 5. 下一步建议与门禁

建议将 B2 的 SchemaStore 作为 **S3 Domain Schema + Manifest 的可证伪候选**，并和全局 IR 候选继续做等功能对照，不直接宣布胜出。下一实测优先使用 DEEPSEEK_KEY **一次必要请求**，把固定自然语言合同需求真正转换为**受 Schema 验证的 typed Agent 工具序列**，让模型输出被严格校验、全量审计、预算控制和故障恢复保护；由独立运行态 Oracle 验证而非靠模型自评。随后研究最小自定义代码生成、构建/测试/隔离发布闭环。

**阶段门禁仍保持**：
- S1 在研，G1 **NOT_PASSED**。
- G1-B01：B2 机制级验证成功，但全渠道强制治理与真实插件/大模型/部署尚未关闭，**OPEN**。
- 冻结 G1-B01 W01—W24：**0/24 FULL PASS**（B2-01—27 不自动折算）。
- 冻结合同 TC01—TC18：**0/18 FULL PASS**。
