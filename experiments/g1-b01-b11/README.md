# S1 B11：B2 权威业务数据 → 两个真实 Saltcorn Native 运行副本的事务 Outbox 单向投影

> 这是研究范围严格受限的、**真正来自权威业务记录**的数据投影，不再使用 B9/B10 的 Saltcorn 独立 seed fixture。正式 S1/G1 未通过。只支持 `app-a / model.contracts / s1_contracts`，单向新增/审批更新，不支持删除、重命名、通用 CDC、企业级租户行权限或生产队列。

## 假设及其可证伪的机制

1. **唯一写入权威**：B2 `SchemaStore.submit_form`、`advance` 仍是合同创建和审批的唯一可信业务写入 API；在 **B2 同一 SQLite 事务**中，用 SQLite `AFTER INSERT/UPDATE` Trigger 自动将每次合同记录变更写入 `b11_outbox`。B2 本身的 `records`、`events`、Release/Manifest 不修改。Trigger 跟随源事务 commit/rollback；`app-a` 下序号连续，事件存储**事件发生当时**的完整 allowlisted 四列，而不是读取最新状态伪装历史。
2. **最小权限的只读拉取**：B11 Kernel 增加 `POST /v4/apps/app-a/projection/pull`，仅接受独立随机 `projectionToken`，不向 Saltcorn 运行 UID 发放该 Token。固定 app-a、单次 `limit <= 100`、`after` 非负，事件含 `seq,recordId,version,cells,eventHash`。该 Token 不可访问 B5 原有工具、不能发布/审批。仅允许 `contract_no,title,amount_minor,status` 四列；**此模型未提供敏感字段，尚未实现真实字段级脱敏或行级权限**。
3. **受信控制器转发，低权限原生写入**：受信 CI 控制器以 Token 拉取 B2 Outbox，将严格 JSON 事件通过 stdin 送给单独 Linux Saltcorn UID 的 `apply_worker.py`，不提供 Kernel DB、配置、Bearer 或 root 权限。Native Apply 在**真实 Saltcorn SQLite** 上以一个 `BEGIN IMMEDIATE` 事务更新 `s1_contracts`、`b11_record_map`、`b11_projection_receipts`、`b11_projection_cursor`；收到旧事件且 Hash 相同只重放 Receipt，改变 Hash 拒绝，缺失 seq 拒绝，record version 不连续拒绝；已有原生业务行被 Native UI/CLI 篡改时，下次对该行的事件应用**拒绝漂移**，不静默覆盖。
4. **真实运行时与版本**：v1/v2 两个独立 Saltcorn CLI/Native SQLite、HTTP 服务同时在线。两个 Native SQLite 不再执行 seed；初始 B2 合同两级审批产生 seq1..4，经 Outbox 投影后两实例业务行**与真实 B2 合同内容一致**。B2 发布 v2 后，原生 View.columns 仍是 v1 三列、v2 四列，但业务行一致。切换后创建第二份 B2 合同并批准，增量 seq5..8 应在**不重启两个 Saltcorn 进程**的情况下应用，两边原生 HTTP 与 Chromium 看到第二份合同。
5. **回滚业务事实不回退**：复用 B10 真实路由 CAS/在途请求隔离/Native v2 进程故障 503/受权 B2 Release 指针回滚 v1/Router 回滚 v1，最终 v1 页面仍显示**两份 Approved 合同**，源 Outbox 8 条不可变事件、B2 最新草稿和两个 Release 不变，App B 不受影响。

## 实验实际组件

| 文件 | 用途 |
|---|---|
| `projection_source.py` | **真实 B2 SQLite 原子 Trigger Outbox**、只读 cursor pull、事件时点 payload、固定 allowlist 和 hash |
| `kernel_service.py` | B2/B5 可信 Kernel + 独立 projectionToken 专用只读 HTTP API，不向 Saltcorn 暴露 |
| `apply_worker.py` | **真实 Saltcorn SQLite** 原子 upsert、记录版本映射、持久 cursor+receipt、缺口/重放/派生漂移拒绝 |
| `native_env_launcher.py` | 真实 Saltcorn CLI 只在 `s1-b11-project-*/runtime-private/projection-*.sqlite` 中启动 |
| `experiment.py` | 62 条真正 Linux UIDs、B2 Kernel/Trigger、Saltcorn v1/v2、SQLite、HTTP、Chromium、故障与回滚 E2E 检查 |
| `test_projection.py` | 28 条原子 Trigger、源 app scope、事件时点快照、回放、乱序、失败事务、漂移与冲突的单元级检查 |
| `.github/workflows/s1-b11-real-business-outbox-projection.yml` | Ubuntu24.04 / Node24 / Saltcorn CLI 1.7.0-beta.5 / Python3.13 / Playwright1.56 真正 CI |

B10 的 `router.py` 仍由源码只读复用，**不会因为 B11 数据同步实验重新声称 W17/W20/W24 通过**。

## 必须保留的限制和负对照

- 本轮只对**一个应用、一个业务模型、一个只读列表页面**验证数据投影。Outbox 由 SQLite Trigger 实现，并非 PostgreSQL 逻辑复制或 Kafka/CDC 通用框架；没有生产消息队列、异地故障恢复、多消费者管理或自动重试调度器。投影由**受信测试控制器主动调用**，并不是平台已具备后台自动持续同步任务。
- `eventHash` 是内容完整性摘要，**不是数字签名或不可抵赖证明**；Saltcorn UID 仍可修改自己的派生 SQLite，Source/Kernel UID 和 root 仍可能绕过约束。Native 改写既有业务行会在下一次该行事件被应用时被拒绝，但**不会自动在每次前端读取时发现**；真实 Saltcorn 原生端口仍监听本机 loopback，没有生产网络隔离。
- 本轮模型没有 PII，故只做固定列白名单；**不具备真正的行级 ACL、动态用户授权和敏感字段脱敏验收**。同一受信 Controller 拿到 Outbox 后会将四列交给 Native，不能声称企业多租户数据隔离。
- 只投影 `s1_contracts` 业务数据行，B2 Form/Workflow 的**执行逻辑仍在 Kernel**，Saltcorn 原生并不具备同等审批语义；审批状态是 B2 权威计算结果的只读物化。
- 两套 Native Runtime 仍为同一 Saltcorn Linux UID，不是每个版本不同容器/独立挂载。Native 的 SQL 读写是允许的，因为其数据库是**派生副本**，绝不能把 Saltcorn Native DB 作为权威写回 B2。
- 回滚指的是**UI/发布版本回滚**，不撤销已经真实审批的合同。Router 单实例、内存 CAS、无跨重启日志/多机 HA、故障期间真实返回 503。无法据此宣称 W17/W20/W24 FULL PASS。
- 冻结 W01—W24 **0/24 FULL PASS**，TC01—TC18 **0/18 FULL PASS**，G1-B01 仍 OPEN。B11 单项研究证据独立记录，不替代正式冻结验收。

## 下一步（若 B11 实测通过）

B12 应对**运行时派生数据防污染/发布源与业务事件不同步窗口**作明确权衡：为真正多租户加行级权限/脱敏和受信同步服务的身份边界，建立 Outbox 消费者**持久状态、后台自动运行、延迟指标与故障恢复**；验证断电重启/网络中断后两套 Native 视图从源 checkpoint 正确重放，并对路由和发布指针的持久化控制面设计正式 W17/W20/W24 验收。
