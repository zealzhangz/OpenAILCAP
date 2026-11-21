# S1 真实合同配置模型与页面运行：Saltcorn 原生 Pack 实验

**日期**：2026-11-21；**结果**：平台原生合同配置及存储/REST/HTML 读回 **9/9 PASS**。这是一项真实第三方低代码运行时的最小纵向切片，不是 AI 自主开发 PoC，也未完成 README 合同基准的所有强制字段和审批规则。

## 1. 核心证据及版本冻结

| 项目 | 结果 |
|---|---|
| 验证提交 | [66dd75de52103f76ed3e3f46d6a59b0395591688](https://github.com/zealzhangz/OpenAILCAP/commit/66dd75de52103f76ed3e3f46d6a59b0395591688) |
| 实际 GitHub Actions | [Run #44869926796](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44869926796)，completed / success |
| GitHub job | #136741936555，Install、Native Pack、HTTP Server、Independent verify、Artifact 均 success |
| 原始结果 Artifact | s1-saltcorn-contract-native-pack，GitHub Artifact ID 14693482263 |
| 上游固定源码 | [Saltcorn SHA 515254b](https://github.com/saltcorn/saltcorn/tree/515254bee5a98df70530cc59846b1df02d5db350) |
| 实际 CLI 安装版本 | @saltcorn/cli/1.7.0-beta.5，Node 24.22.3 |
| 配置资产 | [contract-pack.json](../../experiments/platform-saltcorn/contract-pack.json) |
| 平台写入准备 | [seed-contract.js](../../experiments/platform-saltcorn/seed-contract.js)（以高权限 CLI 写入测试行，不是 AI 工具调用） |
| 独立验收 | [contract_verify.py](../../experiments/platform-saltcorn/contract_verify.py) |

## 2. 本次究竟创建了什么

通过 Saltcorn 官方原生命令执行：

~~~bash
saltcorn reset-schema -f
saltcorn install-pack -f experiments/platform-saltcorn/contract-pack.json
saltcorn run-js -f experiments/platform-saltcorn/seed-contract.js
saltcorn serve --port 3100 --noscheduler
~~~

Pack 声明两张业务表：
- s1_contracts：contract_no（唯一文本编号）、title（标题）、amount_minor（整数分，100000001 即人民币 1000000.01 元）、status（状态）；系统自动分配主键 id。
- s1_approvals：contract_ref（Saltcorn Key，引用 s1_contracts）、approver、action，表达合同与审批记录的 1:N 模型能力。
- s1_contract_list：基于 s1_contracts 的 Saltcorn List 视图，直接渲染合同编号/标题/金额分/状态。

原生 Table API 实际写入一条合同：
- contract_no = HT-2026-000001；
- title = S1 Platform Contract；
- amount_minor = 100000001；
- status = Draft。

独立 Python 验收器先检查 SQLite 真实元数据表、业务字段/关联定义、实际 SQL 行，再 HTTP GET Saltcorn REST API 与 List 视图，且验证未认证访问审批明细 API 的拒绝。

## 3. 原始 9 项 PASS 证据

| ID | GitHub Actions 实际输出 | 验收 |
|---|---|---|
| PK01 | s1_contracts、s1_approvals 两个模型已登记 | PASS |
| PK02 | 字段 id、contract_no、title、amount_minor、status 已登记 | PASS |
| PK03 | contract_ref，类型 Key，reftable_name = s1_contracts | PASS |
| PK04 | s1_contracts 物理 SQL 表实际包含对应列 | PASS |
| PK05 | SQLite 中实际存在合同号 HT-2026-000001、金额 100000001 的记录 | PASS |
| PK06 | s1_contract_list 作为真实视图已登记 | PASS |
| PK07 | HTTP /api/s1_contracts/ 200，返回预先写入的合同 | PASS |
| PK08 | HTTP /view/s1_contract_list 200，渲染 HTML 包含合同编号 | PASS |
| PK09 | 未认证访问 /api/s1_approvals/ 返回 401 | PASS |

以上来源为 [实际执行的 CI 日志](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44869926796) 和该 Run 上传的 JSON Artifact；非纸面设计或自行伪造的单元测试对象。若 Artifact 因保留期过期，可重新触发同一固定提交的 workflow。

## 4. 贯通的配置/运行时源码调用链

本研究在固定 Saltcorn 源码中定位以下实现节点：

1. [CLI install-pack](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/saltcorn-cli/src/commands/install-pack.js)：读取 JSON Pack、初始化插件/租户状态，调用 install_pack。
2. [admin-models/pack.ts](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/saltcorn-admin-models/models/pack.ts)：根据 Pack 依次创建/更新 Table、Field、View，刷新 State。
3. [Table.create/insertRow](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/saltcorn-data/models/table.ts)：创建业务表 DDL、记录 _sc_tables 元数据，执行真实业务记录写入。
4. [Field.create](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/saltcorn-data/models/field.ts)：增加物理 SQL 列并记录 _sc_fields 及 Key 的目标表元数据。
5. [View.create](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/saltcorn-data/models/view.ts)：持久化及注册视图。
6. [Serve 命令](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/saltcorn-cli/src/commands/serve.js)：启动真实运行时，并由验收器从本机 HTTP/SQLite 读回。

*链路性质*：关键节点有源代码路径和端到端可观察结果，不代表逐函数动态 trace 或生产级并发验证。特别是“原生 Pack 可导入且渲染”仍不能推断 AI 能通过安全工具契约执行同样的修改。

## 5. 对 OpenAILCAP 架构的启示

- **可以确证的事实**：设计态可以由稳定、版本可追踪的结构化 Pack 形式被平台的受控配置入口识别，创建真实资源，最终在运行时以 REST/HTML 使用。并非需要 AI 直接写数据库才能配置低代码应用。
- **实际观察到的架构界限**：业务 Pack 与应用运行态是不同层次；原生配置导入需考虑版本/事务及权限。此次未测试 Pack 二次导入后的冲突检测、字段删除与人工改动保留；不能类比 OpenAILCAP 的多轮 AI/人工协同能力。
- **货币语义存在刻意差异**：本实验采用 amount_minor 整数“分”以避免浮点舍入，原 README 冻结基准要求 amount decimal(12,2)。本次并未测试完整金额字段契约，仍需统一货币模型并验证等于/超过阈值的审批。
- **权限仅验证一次未经认证 GET 拒绝**：没有模拟两个真实角色的审批授权/禁止修改，也没有评估 API 调用与工具代理越权。

## 6. 与 README 1.4 / 合同 TC 的对应关系

| 目标 | 状态 |
|---|---|
| 合同和审批数据模型（配置、关联） | **部分已在真实平台证明**；字段及金额类型与冻结基准不完全一致 |
| 真实页面与合同列表 API | **部分已在真实平台证明**；使用平台原生 List 模板 |
| 金额阈值、两级审批运行 | **NOT_RUN** |
| AI 识别需求并自动配置 Pack | **NOT_RUN**（Pack 是研究预先编写的） |
| AI 自定义代码、自动测试与部署 | **NOT_RUN** |
| 人工修改后 AI 继续编辑 | **NOT_RUN** |
| 插件自动发现及多应用隔离 | **NOT_RUN** |

因此 contract-benchmark/spec.json 中 18 项平台验收任务仍不应填写 PASS。本次应作为阶段 S1 的“平台原生纵向切片”独立记录；后续必须补用户旅程、工作流、双向编辑和可信权限工具边界。

**阶段结论**：G1 仍未通过，但已从“第三方平台安装缺失”推进到“真实第三方平台安装、配置建模、持久化、API 和页面运行可复现”。下一步应以二次导入/局部更新和人工变更保留为主，形成 H01/H03 的真实平台级反例/对照证据。
