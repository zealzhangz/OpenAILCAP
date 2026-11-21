# S1 源码+实测：特权全量 Pack 恢复造成旧上下文覆盖人工修改

日期：2026-11-21。证据等级：**真实 Saltcorn 第三方低代码平台实际运行 S0 + 固定源码静态追踪**。

## 一、核心发现

**在本次研究的 Saltcorn 1.7.0-beta.5 中，将“基于旧版本的完整 Pack”直接通过管理员恢复接口再次导入，会把与本次自动化目的无关、但其 Pack 中带有旧值的字段属性也写回数据库。** 该事实是在真实 SQLite 文件与 Saltcorn 原生模型 API 中观察到的，并非依靠推测。

本次自动化目标是删除合同列表视图中的 amount_minor 列。旧 Pack 仍携带 title.label=Title、status.label=Status，因此它清除了此前分别保存的 Human Reviewed Title 和 Automated Status 两个标签。导入命令返回成功，未进行人工修改与旧基线间的冲突裁决。

**限定解释**：Saltcorn 的 Pack 是管理员导入/恢复工具；这不能证明 Saltcorn 的普通浏览器可视设计器没有冲突控制，更不能证明其官方 AI Agent 的编辑行为不安全。它证实的是 **“直接把传统平台的全量导入/恢复 API 当作 AI 编辑工具”这条集成路线存在丢失更新风险**。

## 二、正式实验证据

| 字段 | 固定记录 |
|---|---|
| 研究代码 Commit | [7dac04298955a52d04eb9a1a3ed29be50a12e626](https://github.com/zealzhangz/OpenAILCAP/commit/7dac04298955a52d04eb9a1a3ed29be50a12e626) |
| GitHub Actions | [Run #44871169761](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44871169761) — **completed / success** |
| Job ID | 136745819984 |
| Artifact | s1-real-saltcorn-human-automation-roundtrip，ID **14694023138**，含 A/B/C/C-HTTP 四份机器可读结果 |
| 实际 Saltcorn CLI | **1.7.0-beta.5**，Node **24.22.3** |
| 固定上游研究源码 | [saltcorn/saltcorn SHA 515254bee5a98df70530cc59846b1df02d5db350](https://github.com/saltcorn/saltcorn/tree/515254bee5a98df70530cc59846b1df02d5db350) |
| 测试来源 | [回归实验完整源码](../../experiments/platform-saltcorn/roundtrip/README.md) |
| 断言执行情况 | 阶段 A 四项、B 四项、C 四项、最终 C-HTTP 六项，**18/18 次通过**（C 的四个数据库断言被重复执行，非 18 个不同的测试类型） |

## 三、可独立复现的三条路径

### A：局部资源变更——非冲突改动保留

1. 使用前一次已经验证的 Saltcorn 原生合同 Pack 创建 s1_contracts、s1_approvals、s1_contract_list 和真实合同 HT-2026-000001。
2. 以研究人员事先编写的 CLI 脚本调用真实 Saltcorn Field.update，仅把 title.label 从 Title 改成 Human Reviewed Title。
3. 另一脚本模拟自动化调用同一原生 Field.update，但只修改 status.label 为 Automated Status。
4. 独立 Python 验证器读取 SQLite _sc_fields 与 _sc_views，并核查业务行。

**真实结果**：

- A1：title.label = Human Reviewed Title — PASS；
- A2：status.label = Automated Status — PASS；
- A3：视图仍包含 amount_minor 列 — PASS；
- A4：合同金额 100000001（分）与编号保持原值 — PASS。

这是单字段、顺序执行的非冲突操作保留证明，**没有验证真正并发写入**。

### B：旧全量快照恢复——非相关人工修改被覆盖

1. 在人工修改前的基础 Pack 上自动生成一份新配置，其**意图只是在 s1_contract_list 视图里删除 amount_minor 一列**。
2. 原 Pack 的其他字段列表没有同步人工变更，仍带 title.label=Title 与 status.label=Status。
3. 通过 Saltcorn 原生 CLI install-pack 导入完整旧快照；数据库读回。

**真实结果**：

- B1：title.label 恢复为 Title — PASS（**人工编辑丢失**）；
- B2：status.label 恢复为 Status — PASS（**前一轮自动化编辑也丢失**）；
- B3：列表视图已移除 amount_minor 一列 — PASS；
- B4：业务行没有被删除 — PASS。

原始 GitHub Job 日志逐条打印上述真实 SQLite 返回值，导入操作成功退出。本轮最重要的证伪结果由此形成：**无差异判定与并发版本检查的全量恢复接口，不能保障多轮无损编辑**。

### C：局部更新前置版本检查——明确拒绝过时基线

1. 人工再次把 title.label 修改为 Human Reviewed Title。
2. 自动化拟将同一字段改成 Automated Title，但持有的原基线是 Title。
3. 应用侧脚本在真正写入之前读取字段的当前值，发现 current!=expected 时抛出 STALE_BASE。
4. CI 要求程序以非零码退出且错误中包含 STALE_BASE；若反而成功即判失败。
5. 独立验证确认人工标签不变，启动真实 Saltcorn HTTP 服务并通过 API 与列表 HTML 读回合同编号。

**真实结果**：

- C1—C4：title=Human Reviewed Title、status=Status、视图无 amount_minor、合同业务行无损 — PASS；
- C5：HTTP GET /api/s1_contracts/ 返回 200、包含合同编号 — PASS；
- C6：HTTP GET /view/s1_contract_list 返回 200、实际渲染 HTML 包含合同编号 — PASS；
- CI 按预期捕获到 STALE_BASE 拒绝。

**严格边界**：这个防御脚本仅在应用层执行先读后写，两步没有数据库原子性，属于 **TOCTOU 不安全方案**。它仅证明“可识别某个旧基线冲突”，不证明两个真实并发写入会安全串行化，更不构成可上线的 CAS 实现。

## 四、与源代码的因果对应

所有上游地址均固定 SHA：

- [CLI install-pack](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/saltcorn-cli/src/commands/install-pack.js)：加载输入 JSON，调用后台 install_pack。
- [管理员 Pack 安装实现](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/saltcorn-admin-models/models/pack.ts)：对已经存在的字段调用 exfield.update(updrow)；对已有视图调用 View.update(viewNoTable, existing.id)。在此次公开调用路径中没有发现请求方基线版本比较；这一结论限定于该导入路径。
- [Field.update](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/saltcorn-data/models/field.ts)：将指定字段更新到 _sc_fields，并刷新模型缓存。
- [View.update](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/saltcorn-data/models/view.ts)：持久化配置并刷新视图缓存。
- [CLI run-js](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/saltcorn-cli/src/commands/run-js.js)：本实验通过高权限 CLI 注入 Table 模型，实现受控“人工编写”和“自动化编写”的确定性命令。

源代码静态追踪与真实 SQLite 编辑行为互相印证，但本实验**没有**观测 Web 编辑器的具体 PUT/POST 调用链、生产用户权限、跨应用工作区及真实 LLM 规划。

## 五、对 OpenAILCAP H01/H03 的影响

| 核心假设 | 本次证据 | 状态 |
|---|---|---|
| H01：应用状态可由人工/AI 操作共享模型 | 真实第三方 Table/Field/View/REST 已证明配置资源存在统一读写入口，但**没有**验证完整 Application IR 与编辑器 | 部分机制证明，平台级目标未完成 |
| H03：AI/人工多轮交替编辑无损 | 局部原生 API 修改非重叠字段无损；旧版全量恢复**真实丢失修改**；非原子冲突前置检查可阻止一个顺序冲突 | **已形成强证伪约束**：全量 Pack 直连 Agent 不可接受；H03 不通过 |
| H07：独立验收可识别失效 | 独立 Python 读物理 SQLite、API、HTML，可判定发生“危险但预期”的覆盖，并保持负面语义 | 机制级证据，AI 验收目标未完成 |
| H08：无需 LLM 也可更改模型 | 完整实验无需模型服务或 LLM，只使用真实开源平台管理/模型接口 | 说明人工可编程维护入口存在；不等于人工 UI 旅程验收 |

## 六、架构风险/建议

**结论 R-H03-01：阻断直接复用管理员导入工具作为 Agent 修改接口。** 只把导入 Pack 用于显式备份恢复、模板安装或受审计的全量替换，不将其直接暴露为默认的自然语言编辑工具。

**推荐研究路线（尚未成为最终 ADR）**：

1. 所有人工/Agent 变更都通过可信身份网关和受治理的领域命令；未经许可的直接 SQL/CLI 禁止。
2. Agent 使用精确资源/字段 Patch，不携带无关旧资源。
3. 请求含 expectedRevision/内容哈希与幂等变更 ID；服务端在同一数据库事务内比较基线并提交状态、版本、审计及指纹。冲突返回可机器读取的 409 和当前资源版本，不得静默重试全量替换。
4. 只在业务行为、引用、数据完整性及权限的独立验收通过后，允许把草稿变更升级为运行态版本。
5. 对跨资源更新、失败恢复与自动回滚单独设计。真实编辑器/Agent 的集成必须进行进一步实验。

## 七、不能误报的成绩与后续工作

- 本实验真实执行 **18 次断言全部符合预期**，但 B 路径明确是**失败的产品安全行为**，不能作为“人机协作已验证通过”的正向指标。
- 原先合同基准 18 项 TC01—TC18 的强制合同字段/阈值/真实审批/Agent/权限要求未由本次实验满足，结果保持 0/18 PASS。
- G1 仍未通过。下一个最小高价值研究是**真实浏览器可视设计器写入路径** + **可信带事务 CAS 的平台适配层**，然后再执行真正的 AI Agent 工具调用。
