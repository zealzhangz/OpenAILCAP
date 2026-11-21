# S1：在真实 Saltcorn 内核执行合同金额路由与两级审批触发器

本工作包优先验证 README 第一阶段统一合同场景 1.4 的**金额边界/审批状态机**，与此前的元数据编辑版本实验区分。本试验使用 Saltcorn 原生 Table/Field/View、Pack 里的 **Validate/Insert Trigger** 和官方 built-in **run_js_code Action**，实际运行 SQLite 数据和 HTTP API/HTML 视图；不把 Python 状态机模拟视为真实低代码平台实现。

## 一手实现依据

- 固定研究源码 [Saltcorn @ 515254bee5a98df70530cc59846b1df02d5db350](https://github.com/saltcorn/saltcorn/tree/515254bee5a98df70530cc59846b1df02d5db350)，实际安装 @saltcorn/cli@1.7.0-beta.5。
- [原生 Trigger.ts](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/saltcorn-data/models/trigger.ts)：包括 Validate/Insert 调用、action.run、结果合并。
- [原生 Table.ts](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/saltcorn-data/models/table.ts)：insertRow 校验触发器在写入前运行，Insert 触发器在真实持久化后执行，updateRow 更新物理行。
- [原生 Pack.ts](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/saltcorn-admin-models/models/pack.ts)：导入 Trigger.create/Trigger.update 与字段、页面配置。
- [内置 run_js_code](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/saltcorn-data/base-plugin/actions.ts)：平台原生 Code Action 提供受控的 Table/row 等执行上下文。

## 原生配置模型与实现范围

[generate.py](generate.py) 从**未修改的冻结 Benchmark** [spec.json](../../contract-benchmark/spec.json) 以及历史合同 Pack 生成研究用配置：

- s1_bench_contracts：编号唯一、标题、金额规范化字符串、整数分、所有者字符串、状态。
- s1_bench_routes：Key→合同、一条高/普通审批路由记录。
- s1_bench_action_requests：Key→合同、动作/角色声明/操作者/时间/原因，带唯一 request_id。
- s1_bench_approvals：Key→合同、实际审批人/动作/时间/原因。
- s1_bench_contract_list：Saltcorn 原生 List 视图。
- 三条导入的**原生触发器**：合同 Insert 自动生成 HIGH/NORMAL 路由；动作请求 Validate 在插入前校验状态+角色规则；动作 Insert 更新真实合同状态、持久化审批记录。

[triggers/](triggers/) 中包含三个真实安装的 Code Action body，而不是纯 Python 业务模拟。研究驱动程序 [drive-template.js](drive-template.js) 通过原生 Saltcorn CLI 的 Table.insertRow/trigger 实际执行业务流，交易 harness 对动作请求使用 SQLite BEGIN IMMEDIATE 与 COMMIT/ROLLBACK（正式网关事务仍需另行实现）。

## 实验场景与独立证据

[verify.py](verify.py) 从冻结 spec.json、Saltcorn CLI 实际动作日志、物理 SQLite 中的 _sc_tables/_sc_triggers/业务行/关联表、真实 Saltcorn REST/HTML 检查：

- 12 项金额边界 AM01—AM12：999999.99、1000000.00、1000000.01，以及最高允许金额、负数、科学计数法、超精度等。
- 12 项状态迁移 ST01—ST12：合法提交/一级/二级批准/驳回，以及不合法角色与状态不应持久化请求。
- 3 条真正连续的业务链：普通两步、超阈值三级、拒绝路径。
- 原生 Trigger/物理表、原生列表/API 的实际运行。
- 显式观察**金额存储与冻结 decimal(12,2) 契约不等价**，不能把整数分 + canonical 字符串与完整数据库精度要求等同。

## 不能提前声称的能力

1. 业务角色来自 insertRow 调用中的 actor_role **测试字段**，不是 Saltcorn 真实登录用户、授权角色或会话，不能声称完成 HTTP 403/身份不可伪造的验收 TC04。
2. 只有研究 CLI 的显式 SQL 事务包住动作请求，不能据此宣称 Saltcorn 所有普通 API/页面触发器的原子性与防重能力；SQLite 平台封装在此前实验中有已知失败模式。
3. 金额解析在自定义 JS 研究代码发生，不是 Saltcorn 官方表单的内建 Decimal 约束；金额数据以 canonical 字符串 + Integer 分保存，**不是 decimal(12,2)**。
4. Saltcorn Run JS 的工作流逻辑为研究人员编写，**不是 LLM Agent 自动创建**，没有 AI 规划、代码生成/修复/发布的证据。
5. 本次真实 Trigger/审批流程可作为 TC03/TC05 的**部分机制证据**，但不能在完整合同验收缺少真实授权、Web 操作和数据契约时把 TC01—TC18 标 PASS。

**门禁 G1 不会因为实验用例 CI 通过自动转为 GO。** 下一项应优先接入真实身份与审批调用，再验证真实 Agent 类型化工具与插件能力，而不是继续编写没有运行证据的方案。
