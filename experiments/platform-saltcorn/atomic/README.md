# S1 Saltcorn 真实平台：SQLite 事务语义与双进程原子编辑研究

本研究使用 **真正安装并启动的 Saltcorn CLI（固定 1.7.0-beta.5）及其原生 Field.update**；数据库为独立 GitHub Runner 中的真实 SQLite 文件。研究人员编写的 CLI 脚本模拟“人工、自动化”编辑，**不是浏览器编辑器或真实 AI Agent**。

## 一、假设及正/负对照

| 编号 | 执行内容 | 应观察到的现象 | 风险解释 |
|---|---|---|---|
| TX1 | 调用 Saltcorn SQLite db.withTransaction 包装，在原生 Field.update 后故意抛异常 | 异常抛出，但更新实际保留 | **负面对照：包装器不能保证 SQLite 事务回滚** |
| TX2 | 两个不同 Saltcorn CLI 进程，各自使用显式 BEGIN IMMEDIATE 修改 title/status，基线 revision 均 0 | 不同字段均保存；各自版本变为 1 | 正向：独立连接+受控资源版本可保留非冲突变更 |
| TX3 | 两个独立进程都以旧 revision=1 竞争修改同一字段 title | 恰好一个 APPLIED、一个 STALE；版本只增加一次 | 正向：实际 SQLite 锁 + 同事务版本校验拒绝过时写入 |
| TX4 | 显式事务内已执行真实 Field.update 后注入失败 | ROLLBACK，字段和版本均保持原样 | 正向：真正数据库事务失败原子恢复 |
| TX5 | 人工使用原生 Field.update **绕过实验版本表**修改 status；版本表仍旧；之后带 expectedRevision 的自动化提交 | 自动化错误地判定旧版本有效并覆盖人工值 | **负面对照：只给 Agent 加 CAS 而人工不接入，仍会丢更新** |
| TX6 | 启动实际 Saltcorn HTTP 服务，重新访问合同 REST 与列表 HTML | 合同记录仍可读，渲染正常 | 避免只观察 SQL 而忽略最终应用 |

本实验的版本表 _openailcap_s1_guard 是**临时研究辅助表**，不属于 Saltcorn 官方应用版本机制。字段 label、物理合同记录来自真实 Saltcorn SQLite 数据库。TX2/TX3 是真正两个不同 CLI 进程并发访问同一物理文件，而不是在一个 Python 线程内模拟并发。

## 二、实现文件

- [transaction-negative.js](transaction-negative.js)：Saltcorn SQLite withTransaction 异常后是否留下真实物理写入。
- [prepare.js](prepare.js)：恢复字段基线，并建立研究用资源版本表。
- [work-template.js](work-template.js) + [generate.py](generate.py)：预注册六个实验命令，生成真实 Saltcorn CLI 可执行 JS。
- [bypass-human.js](bypass-human.js)：原生 Field.update 绕过实验版本表。
- [verify.py](verify.py)：**独立** Python 读取 SQLite 字段/业务数据/版本表，并核验不同进程日志和真实 HTTP。
- [GitHub Actions](../../../.github/workflows/s1-saltcorn-atomic.yml)：每次创建新数据库、故障注入、跨进程并发、上传结构化 JSON。

运行 CI 的成功条件是观察到了预注册预期，包括两个**负面**结果。**绿色 CI 不代表源平台安全，也不意味着 OpenAILCAP 已生产可用**。

## 三、事务源码依据

固定上游：[Saltcorn SHA 515254bee5a98df70530cc59846b1df02d5db350](https://github.com/saltcorn/saltcorn/tree/515254bee5a98df70530cc59846b1df02d5db350)。

- [SQLite withTransaction 源码](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/db-common/sqlite-commons.ts)：BEGIN、COMMIT、ROLLBACK 在包装实现中被注释，rollback 只是标记。
- [SQLite Adapter](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/sqlite/sqlite.ts)：原生 db.query 支持真正的 SQL BEGIN、COMMIT、ROLLBACK。
- [可视字段编辑服务端路由](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/server/routes/fields.ts)：字段保存通过鉴权路由、fieldFlow、db.withTransaction 和 Field.update。
- [Field.update](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/saltcorn-data/models/field.ts)：更新真实 _sc_fields。

**对浏览器设计器的限定**：路由存在并能静态追踪，不等于真实浏览器会话/表单已经运行；本次仍只运行高权限 CLI。

## 四、与 OpenAILCAP 的关系

**最关键的研究约束**：生产 Agent 工具要使用真正的数据库事务 + 版本治理；所有人工、AI、插件写入入口必须共享一致的版本历史，不能仅用外挂 sidecar 版本表保护 Agent。当有未经治理的写入路径时，CAS 的版本号会与真实字段发生漂移，后续 Agent 可能再次覆盖人工修改。

本实验**不是推荐通过直接 SQL 操作 Saltcorn 内部表来打造 OpenAILCAP**。显式事务在此仅验证真实底层机制的可能性。正式架构需要可信 API、用户会话授权、租户作用域、数据库迁移、审计、代码安全、运行时缓存和幂等协议；并须对配置编辑器、Agent 工具和插件实现统一管控。

不提供大模型调用，不涵盖 Saltcorn 浏览器可视设计器、第三方平台生产负载、完整合同审批及 README 四组 PoC。18 项完整合同业务验收仍为 NOT_RUN，G1 未通过。
