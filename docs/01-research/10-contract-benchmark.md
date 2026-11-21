# S1 统一合同场景：平台级 Benchmark 与验收协议

> 冻结日期：2026-11-21。数据：[机器可读 spec.json](../../experiments/contract-benchmark/spec.json)。
> **当前所有 18 项真实平台任务均为 NOT_RUN**。用例预注册和 oracle 正确仅证明验收规范自洽，不证明任何候选平台支持任务。

## 一、为何必须使用同一场景

四个平台的产品定位和许可不同：ToolJet 以可视应用与 MCP 见长，但 Code Mode 服务端存在 EE 边界；Appsmith 更偏向连接既有数据源的人工低代码应用；Budibase 的 AI Agent 大多是在业务自动化里执行操作；NocoBase v3 强调 code-first Core、Agent Runner 与插件，不能把 NocoBase v2 的可视配置功能直接计入 v3。

因此，必须先确定**同一个业务数据和可观察结果**，再在不同平台运行；不得将各种平台自己的演示任务拿来横向比较。模型/Agent 基线应固定，无法访问的商业功能按依赖条款记录而不是计“支持”。

## 二、合同示例的不可变业务规则

- 合同主表：contract_id UUID、number 唯一、title 非空、amount CNY decimal(12,2)、owner_id、status。
- 审批记录：approval_id、contract_id、approver_id、action、occurred_at、reason；合同与审批记录 1:N。
- 审批阈值：**amount > 1000000.00** 使用两级审批；**amount = 1000000.00** 只需一级审批。
- 金额输入严格为非负、最多 10 位整数及最多 2 位小数的十进制**字符串**；不接受科学计数法、负值、NaN 等非业务输入。
- Draft → Submitted（创建者提交）；Submitted → Approved（一般合同由 approver1 批准）；高金额 Submitted → Level1Approved → Approved（approver1、approver2 分别批准）；有权审批者可 Rejected。
- 代码扩展：HT-YYYY-000001 格式的编号生成器，按作用域唯一；重复 change_id 不重复分配编号。
- A/B 两个应用即使同名字段与组件，也不得跨应用读写、部署或泄漏密钥。
- 人工在编辑器改按钮背景后，Agent 下一轮改文案；最终两项改动均保留，运行时等同于设计态。

## 三、固定的边界值和状态机 oracle

预注册 12 项金额边界测试（包括 999999.99、1000000.00、1000000.01、最大值、非法负值、小数精度与科学计数法），12 项审批状态转移与拒绝用例。见 [spec.json](../../experiments/contract-benchmark/spec.json)。

[validate_spec.py](../../experiments/contract-benchmark/validate_spec.py) 通过 Python 标准库 Decimal、正则和独立状态机检验这些预注册**预期结果**，防止测试人员临时修改成功定义。这个脚本**不是用来判定平台已支持**，平台级验收还须 API、浏览器、数据库、审计等外部证据。

## 四、18 项合同任务与验收证据要求

| 任务 | 核心测试 | 主要独立证据 |
|---|---|---|
| TC01 | 合同表 + 审批明细真实创建 | DB schema/迁移 |
| TC02 | CRUD、查询和金额精度 | API、数据库数据 |
| TC03 | 等于/超过阈值的审批路径 | 真实工作流执行记录 |
| TC04 | 审批角色越权拒绝 | 403/审计/状态不变 |
| TC05 | 12 项审批状态机 | 状态转换轨迹 |
| TC06 | 自然语言生成低代码资源 | Agent 工具轨迹、编辑器/运行时读回 |
| TC07 | 配置能力不足转代码 | 机器可读能力目录和路由日志 |
| TC08 | 复杂代码编号器唯一性和幂等 | 源码、运行断言 |
| TC09 | AI 构建、测试、隔离安装 | CI/部署与失败阻断 |
| TC10 | 人工样式 + Agent 文字增量编辑 | 多版本快照与真实 UI |
| TC11 | 同字段冲突拒绝 | 服务端冲突响应 |
| TC12 | 人工代码资产保留 | 变更前后哈希 |
| TC13 | 完全断开 AI 后人工仍可维护 | 无模型编辑/运行记录 |
| TC14 | 新插件让 AI 自动发现并调用 | 插件 Manifest、能力工具列表 |
| TC15 | 应用 A/B 隔离与越权 | 跨应用读写/部署拒绝日志 |
| TC16 | 失败发布与回滚 | 历史版本、健康探针 |
| TC17 | 恶意工具调用、工作区/密钥测试 | 授权与隔离证据 |
| TC18 | 独立浏览器与 API 验收 | Playwright + API + DB |

## 五、平台试验执行标准

1. 在真实可部署平台记录：仓库固定 SHA、产品 edition/许可证、镜像 tag + digest（或包 lockfile）、环境、资源/端口、启动命令。
2. 先按平台的**人工开发方式**构建合同 CRUD/审批；保持相同角色、金额与可观察业务结果。
3. 尝试 AI 自动修改同一资源；如果该平台没有公开授权的 AI 开发工具，标记 **BLOCKED_EDITION** 或 **NOT_SUPPORTED_BY_TESTED_EDITION**，不得手工代替 AI 并将它标成成功。
4. 所有执行结果必须附原始证据路径，并区分 PASS/FAIL/BLOCKED/NOT_RUN。静态源码/文档不能直接给 PASS。
5. 测试还必须记录人工操作次数、代码行数、全量耗时、模型与 token 成本；比较过程需固定环境和外部服务。
6. 没有明确授权不得测试第三方私有服务，不得在测试报告存放凭据。

## 六、实际状态（2026-11-21）

- **24 项 oracle（金额 12 + 状态机 12）**：预注册规范；由 CI 检查规范与预期的一致性。
- **18 项平台验收**：全部 **NOT_RUN**，尚无真实合同业务平台结果。
- NocoBase v3 官方创建器试验在依赖模板下载阶段失败，见 [真实失败记录](11-installation-trial.md)。
- OpenAILCAP 自研 SQLite Spike 的 23/23 测试是**平台前置模型实验**，不能放入上述 18 项平台验收的 PASS 栏。

## 七、完成本场景的关键依赖

优先建立一个在许可范围内、可在 CI 或独立测试环境实际启动的参考平台。对于大型平台，不以单独拉起容器成功代替“表/表单/审批/人机编辑”真实业务验收。只有至少一个平台的完整基础链路可复现后，G1 的同一业务复现条件才有可评审的事实依据。

## 八、真实平台纵向切片的补充进展

已通过 [Saltcorn 原生 Pack 试验](15-native-contract-platform-evidence.md) 创建真实合同和审批关联模型，在真实 SQLite、API 和 HTML 中完成 9 项独立测试（[CI #44869926796](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44869926796)）。此实测**并未覆盖**本规范完整 TC01 的 decimal(12,2) 与系统业务/关系强约束；没有执行两级审批、AI 开发、人工接管及插件/应用隔离。因此原本冻结的 18 项正式验收仍均为 NOT_RUN，本规范原始 JSON 结果不应被提前改为 PASS。后续可把 Saltcorn 的原生配置部分作为同任务的可用性证据，但完整通过必须执行冻结契约。

## 九、2026-11-21 原生 Saltcorn 业务规则实际复现：部分证据但不改冻结判定

[Run #44876882097](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44876882097)、[报告 21](21-saltcorn-native-workflow-evidence.md) 与 [结果摘录](workflow-observations.json) 表明真正 Saltcorn 原生 Validate/Insert Trigger 及 Code Action 已运行原规范 AM01—AM12 12/12、ST01—ST12 12/12、正常/高额二级/拒绝连续路径 3/3（总 35/35 项独立验证）。这给 TC01、TC02、TC03、TC05、TC18 提供**部分机制性证据**，不是正式验收 PASS：金额实际存储为 TEXT canonical 字符串+Integer 分，并非要求的 decimal(12,2)；请求中的 actor_role 可伪造，不是 HTTP 403 身份授权；没有真实用户在网页提交审批动作，也没有真实 AI 开发。**原冻结 spec.json 中 18 个平台任务仍为 NOT_RUN，完整通过 0/18，G1 未通过。**
