# S1 实证报告：SQLite 事务包装、双进程原子编辑与绕过版本控制

**日期：2026-11-21。证据等级：真实 Saltcorn 平台 + 真实 SQLite 文件 + 独立 CLI 进程 + 物理库/HTTP 读回。**

- [GitHub Actions 实际运行 #44872093657](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44872093657)：completed / success。
- [代码固定提交 8c665961](https://github.com/zealzhangz/OpenAILCAP/commit/8c665961ce6f24be992387e1850540bf261cf4a1)。
- Job ID 136748667634；Artifact 名称 s1-saltcorn-real-transactions-and-bypass；Artifact ID **14694034903**，包含七份各阶段 JSON。
- 被测 Saltcorn CLI 发布版本 **1.7.0-beta.5**、Node **24.22.3**。研究源码版本 [515254bee5a98df70530cc59846b1df02d5db350](https://github.com/saltcorn/saltcorn/tree/515254bee5a98df70530cc59846b1df02d5db350)；源码 SHA 与 npm 版本不等于逐文件构建哈希相同。
- [全部实验源码与复现说明](../../experiments/platform-saltcorn/atomic/README.md)；[GitHub Actions workflow](../../.github/workflows/s1-saltcorn-atomic.yml)。

## 一、六组实际场景

| 组别 | 真正数据库或进程观察 | 技术判断 |
|---|---|---|
| TX1：Saltcorn SQLite withTransaction 注入异常 | 原生 Field.update 写入后抛出异常，字段最后仍是 Unrolled Back Label | **负例**：该包装器在 SQLite 模式下没有真正回滚 |
| TX2：两个独立 CLI 进程修改不同字段 | title=Human Checked、status=Automation Checked；独立资源版本均为 1 | 正例：研究用显式 SQL 事务和字段版本允许这次非冲突并发 |
| TX3：两个独立 CLI 进程争夺同字段 title、都用 revision=1 | c-alpha 实际 APPLIED，c-beta 读到 revision=2 返回 STALE；title 仅升至 2 | 正例：此场景中的真实 SQLite 写锁与基线检查拒绝了冲突 |
| TX4：显式事务内原生 Field.update 后注入失败 | 返回 ROLLED_BACK；真正字段保持 Writer Alpha，版本保持 2 | 正例：BEGIN IMMEDIATE 到 ROLLBACK 之间的此类更改具有原子恢复效果 |
| TX5：人工通过不受治理的原生 Field.update 直接改 status | status 变成 Ungoverned Human，但研究侧版本仍是 1 | **负例**：外部改动导致研究账本与真实资源不同步 |
| TX5：受治理自动化以 expectedRevision=1 继续写 status | CAS 命令仍返回 APPLIED，把人工值覆盖成 Unaware Agent，版本增至 2 | **负例**：只给 Agent 加 CAS 不保护人工编辑；会静默丢更新 |
| TX6：最终运行时独立检查 | /api/s1_contracts/、/view/s1_contract_list HTTP 200，确实返回合同记录 | 数据库测试后运行态仍正常 |

**本轮总计 36 次阶段断言全部符合预注册预期**，但有重复验证同一业务行、标签和版本，因此不是 36 个独立功能。特别是 TX1/TX5 **故意重现了不安全行为**，不允许把 CI 绿色理解为平台安全合格。

## 二、GitHub 日志中的关键片段

从 Run #44872093657 的实际 Job stdout 核对到：

~~~text
S1_WRAPPER_RESULT|{"error_was_raised":true,"observed_title":"Unrolled Back Label","unsafe_write_survived_exception":true}
S1_ATOMIC_APPLIED|{"id":"d-title","resource":"title","base":0,"actual_before":0}
S1_ATOMIC_APPLIED|{"id":"d-status","resource":"status","base":0,"actual_before":0}
S1_ATOMIC_APPLIED|{"id":"c-alpha","resource":"title","base":1,"actual_before":1}
S1_ATOMIC_STALE|{"id":"c-beta","resource":"title","base":1,"actual_before":2}
S1_ATOMIC_ROLLED_BACK|{"id":"f-title","resource":"title","base":2}
S1_BYPASS_HUMAN|{"label":"Ungoverned Human"}
S1_ATOMIC_APPLIED|{"id":"b-status","resource":"status","base":1,"actual_before":1}
~~~

本段是已核对字段的**节选**，省略了部分属性，非未经修改的原始 JSON 行。每阶段完整机器结果位于 GitHub Artifact，摘要记录见 [atomic-observations.json](atomic-observations.json)。

## 三、固定源码证据与实际运行关系

1. [db-common/sqlite-commons.ts](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/db-common/sqlite-commons.ts)：SQLite withTransaction 的 BEGIN/COMMIT/ROLLBACK 注释掉，回滚只标记本地布尔值；本次 TX1 由真实业务字段写入进一步验证。
2. [sqlite/sqlite.ts](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/sqlite/sqlite.ts)：数据库底层仍提供真正的 SQL BEGIN/COMMIT/ROLLBACK。本研究在一个运行中的 Saltcorn CLI 连接里显式执行 BEGIN IMMEDIATE、Field.update、研究用资源版本 UPDATE 与 COMMIT。
3. [server/routes/fields.ts](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/server/routes/fields.ts)：浏览器字段保存的服务端路径包含管理员/编辑权限检查、fieldFlow 配置处理、db.withTransaction、Field.update 和表元数据刷新。**该路由目前只做了静态源码阅读，没有实际登录浏览器提交表单**。
4. [saltcorn-data/models/field.ts](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/saltcorn-data/models/field.ts)：原生字段模型方法将更新持久化到 _sc_fields。

这并不意味着 Saltcorn 的 PostgreSQL 和 SQLite 包装器语义相同，也不意味着已证明浏览器字段编辑路由的所有错误处理路径均有部分提交。

## 四、实验 CAS 的严格使用限制

研究辅助表 _openailcap_s1_guard 不是 Saltcorn 原生应用版本系统。TX2/TX3 中的两个独立 Saltcorn CLI 进程共享 SQLite 文件，各自在一个显式事务中检查研究表版本、更新真实 Saltcorn 字段、递增资源版本、提交；这是**独立运行进程上的真实并发测试**，但不是经过安全审查的 OpenAILCAP Agent 编辑服务。

最重要的反证是：Saltcorn 原有 Field.update 可以不更新该实验版本表。因此 TX5 中应用层 CAS 的数字从未改变，自动化错误地接受旧请求，覆盖人工已保存的字段。简单在 AI 侧附加一张版本表**不足以**保证可靠性。

还缺少可信认证、租户/应用身份范围、浏览器设计器对版本的强制接入、命令幂等和审计、跨资源引用完整性、数据库迁移、模型缓存一致性、工作区代码安全以及独立发布/回滚。特别是此 CI 的所有变更通过研究用的高权限 CLI 执行，不存在真实 LLM Agent 或真实人工浏览器会话。

## 五、对 OpenAILCAP 核心假设的影响

- **H03 进一步得到负面约束**：即使 Agent 自己的事务+CAS 正确，人工编辑器或插件只要绕开同一版本历史，Agent 就可能以合法的旧 revision 静默覆盖人工成果。必须要求**人工、Agent、插件全部从可信单一治理入口写入，或可靠检测/登记所有外部变更并失败关闭**。
- **H01 暂不能选型**：资源版本与写入协议的实验没有证明统一 Application IR 比分域 Schema 更合理。
- **H07 机制研究**：独立 Python 从物理 SQLite、子进程日志和真实 HTTP 判定正/负对照，不能替代真正 AI 任务的独立验收。
- **H08 机制研究**：无需 LLM 的原生配置变更已可执行，但尚未验证真实可视人工开发旅程。

新增风险 R-H03-02：外部编辑不更新账本导致假 CAS 成功，阻断真实人机多轮编辑。新增风险 R-TX-01：不能依赖跨数据库通用事务包装器名称推断真实原子性，必须对每个适配器故障注入。

## 六、阶段门禁

当前 **S1 继续，G1 未通过**。用户冻结合同基准 18 项完整业务验收仍 0/18 PASS；本轮字段标签/资源版本实验不能计入审批、AI 开发、自定义代码发布等基准任务。S3 四组完整 PoC 仍未完成。

下一步重点：使用真实 HTTP 浏览器编辑器会话执行一次已授权字段修改；研究所有人工写入路径与插件路径是否可受治理。随后再建立可信服务端版本化命令 API，验证 HTTP 409、真正用户/Agent 授权、两个写入主体、冲突/回滚及部署草稿与运行态一致性。
