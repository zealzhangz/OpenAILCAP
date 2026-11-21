# S1 真实 Saltcorn 原生 Trigger：合同金额路由与两级审批实证

**日期：2026-11-21。结果：35/35 独立断言符合预注册预期，G1 仍未通过。**

## 一、原始执行证据

| 项目 | 可复核记录 |
|---|---|
| GitHub Actions | [Run #44876882097](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44876882097)，completed / success |
| Job | 136763423876 |
| Artifact | s1-saltcorn-real-trigger-workflow-results，ID 14695849924 |
| 运行代码提交 | [8671d3091fbdd10d7b373a49757d66c53fe68fff](https://github.com/zealzhangz/OpenAILCAP/commit/8671d3091fbdd10d7b373a49757d66c53fe68fff) |
| 真实安装 | @saltcorn/cli 1.7.0-beta.5，Node 24.22.3，Ubuntu 24.04 |
| 上游研究源码 | [saltcorn/saltcorn @ 515254bee5a98df70530cc59846b1df02d5db350](https://github.com/saltcorn/saltcorn/tree/515254bee5a98df70530cc59846b1df02d5db350) |
| 业务输入 | [冻结合同 spec.json](../../experiments/contract-benchmark/spec.json) |
| 代码 | [真实平台 Pack、Trigger 与验收工程](../../experiments/platform-saltcorn/workflow/README.md) |

固定源码 SHA 说明研究调用链，不代表已证明 npm 发布包与该 Commit 字节级一致。

## 二、这次运行的是真正的低代码平台业务规则

通过 Saltcorn 原生 Pack 创建四张真实业务表：合同、路由、动作请求、审批明细，以及原生合同 List View。以下三条真实注册在 _sc_triggers 的内置 run_js_code Action 由 Saltcorn 模型执行：

1. 合同 Insert：按照金额整数分严格大于 100000000（人民币 1000000.00 元）分配 HIGH/NORMAL 路由，并写入真实路由表。
2. 动作请求 Validate：在 Saltcorn 真正插入动作前，根据当前合同状态和请求中声明的角色判断允许或 FORBIDDEN/INVALID_STATE。失败请求没有持久化。
3. 动作请求 Insert：通过真实 Saltcorn Table.updateRow 更新合同状态，调用 Table.insertRow 创建 1:N 审批明细。

业务逻辑由研究人员编写为原生 JS Code Action，**不是 LLM 自动生成**。CLI 测试 harness 以显式 SQLite BEGIN IMMEDIATE/COMMIT/ROLLBACK 包裹每次动作，不能把它当作 Saltcorn 官方 HTTP 动作默认具有事务保护的证据。

固定上游一手源码：
- [Table.insertRow：Validate 和 Insert 触发时机](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/saltcorn-data/models/table.ts)。
- [Trigger.runTableTriggers：Action 执行](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/saltcorn-data/models/trigger.ts)。
- [Pack 导入 Trigger](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/saltcorn-admin-models/models/pack.ts)。
- [内置 run_js_code](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/saltcorn-data/base-plugin/actions.ts)。

## 三、冻结金额与两级审批实际结果

| 金额输入 | 数据库实际值 | 原生路由 |
|---|---|---|
| 999999.99 | 99999999 分 | NORMAL |
| **1000000.00** | 100000000 分 | **NORMAL**（等于阈值不升级） |
| **1000000.01** | 100000001 分 | **HIGH**（严格大于才升级） |
| 0.00 | 0 分 | NORMAL |
| 9999999999.99 | 999999999999 分 | HIGH |
| 0000001.00 | 100 分，规范化显示 1.00 | NORMAL |

其余 6 个负金额、过度精度、科学计数法、NaN、超出范围及非数字输入，都被研究 JS 扩展的输入解析器拒绝，数据库没有生成对应合同。**AM01—AM12 共 12/12 PASS**。这些输入并未直接交给 Saltcorn 原生网页表单。

冻结状态迁移 **ST01—ST12 共 12/12 PASS**：
- Draft → Submitted；普通合同 Submitted → Approved。
- 高金额合同 Submitted → Level1Approved → Approved。
- 正确审批人声明批准/驳回后，真实合同状态和审批记录同步落库。
- ST05/ST06/ST11/ST12 的错误角色声明返回 FORBIDDEN，物理审批请求行和审批明细行均为零，合同状态不变。
- ST07/ST08 非法状态返回 INVALID_STATE，不产生无效动作和审批记录。

另有 **3 条完整连续路径全部 PASS**：普通审批 Submitted→Approved；超额两级审批 Submitted→Level1Approved→Approved；拒绝 Submitted→Rejected。实际数据库审批明细分别保留 approver1、approver2 等声明角色，并非测试人员虚构日志。

真实 HTTP GET /api/s1_bench_contracts/ 返回 200 并包含合同编号；Saltcorn 原生 /view/s1_bench_contract_list 返回 200，页面实际渲染合同编号。

## 四、35 项断言的组成和反向证据

| 独立验收类别 | 数量 |
|---|---:|
| 原生表、原生 Trigger、物理列 | 3 |
| 12 项金额边界 | 12 |
| 12 项状态转移 | 12 |
| 普通、高金额、驳回三条连续路径 | 3 |
| CLI 真实运行完成、原生 View、类型限制检测 | 3 |
| Saltcorn REST 和 HTML 运行时读回 | 2 |
| **合计** | **35/35** |

**重要负面证据：Saltcorn 物理 amount_decimal 字段实际类型为 TEXT，和冻结规范的 decimal(12,2) 不相同。** 该项检测的 PASS 是成功发现偏差，不代表达到金额字段合同。当前利用 canonical 十进制字符串和安全范围内整数分保存精度，属于实验替代，不得未经架构/业务评审直接改动冻结验收要求。

## 五、不能凭这轮实验宣布完成的能力

- **没有真正的登录身份授权**。actor_role 是动作表中调用方提交的字符串，可伪造；FORBIDDEN 是原生 Validate 业务错误而非真实 HTTP 403，不能计正式 TC04 安全通过。
- **没有完整金额字段契约**：TEXT/整数分不等于 decimal(12,2)，不能计 TC01/TC02 全项通过。
- **没有审批网页提交**：运行浏览器只用于 HTTP List View 读回，审批动作由有权限的研究 CLI 触发。
- **没有 AI Agent**：全部 Pack 和 Trigger 由研究员固定编写；没有自然语言生成、工具规划、真正 LLM、自动测试修复或发布。
- **事务能力仅针对这次研究 CLI 包装**：不能声称原生 Saltcorn SQLite HTTP 写入/触发器天然具备跨表原子性。先前已复现 SQLite withTransaction 包装的回滚限制。
- **没有重复审批/高并发/插件隔离安全验证**；原生 run_js_code 在平台环境执行任意 JS，不能无限授权给 Agent。

此次实证为冻结合同基准 TC01、TC02、TC03、TC05、TC18 提供**部分机制证据**，不把其中任一完整任务直接标 PASS。原始 spec.json 的 18 个任务仍为 NOT_RUN，完整通过率仍 0/18；应在独立执行台账中标示 PARTIAL，保留原始冻结规范不变。

## 六、架构结论与 G1

**可借鉴**：结构化 Pack、真正的 Validate/Insert Trigger、内置代码扩展，能够组合低代码模型和定制业务规则，且直接证明金额阈值触发的审批持久化是可实现的。不需要一开始就创造完全不同的 DSL 才能执行复杂规则。

**应避免**：将业务字符串角色当作认证权限；把原生代码 Action 无限制暴露给 Agent；在 SQLite 使用没有故障注入验证的事务包装；让自定义代码绕过审核、版本和应用隔离。

**阶段结论：S1 仍在推进，G1 NOT_PASSED。** 接下来应优先完成真实授权的审批 Web/HTTP 操作，再执行真正 LLM Agent 的类型化工具调用和最小权限委托，开展参考平台选择的 G1 正式复审，而不是继续反复测试字段标签。
