# S1 研究报告 44：B11 权威合同事务 Outbox → 双 Saltcorn Native 实例单向数据投影

**日期：2026-11-21。最终证据：B11 真实 E2E 62/62 PASS、B11 单测 28/28、B10 路由回归 34/34、B2 回归 18/18、B5 回归 40/40；0 次 DeepSeek 调用。** 本轮仍属**受限研究专项**：S1 **IN_PROGRESS**、G1 **NOT_PASSED**、G1-B01 **PARTIALLY VALIDATED / OPEN**；冻结 W01—W24 **0/24 FULL PASS**，冻结 TC01—TC18 **0/18 FULL PASS**。

## 一、相较 B10 新增的可证伪研究目标

[B10 报告 43](43-s1-b10-real-saltcorn-traffic-cutover-evidence.md) 已在真实双 Saltcorn 实例、真实 HTTP Router、真实 Chromium 和 B2 发布版本上验证原子内存路由指针、在途请求固定、故障 503 与受权回滚，但 Saltcorn Native 中的合同数据来自**独立 seed fixture**。即使页面合同号与 B2 相同，标题仍不同，不能证明真正的业务数据一致性。

B11 不再向 Native 执行独立 seed，而是用**真实 B2 合同表单和两级审批产生的业务数据**作为唯一可信来源，在 SQLite 同一业务事务中写出 Outbox，严格单向投影到两个真实 Saltcorn SQLite 运行副本。B11 特别检验：事件时点数据、重复事件幂等、错序拒绝、注入事务故障后无部分提交、第二份合同在两套 Native 运行期间实时增量出现、UI 版本回滚后审批事实不回退。

## 二、交付、可复现 CI 和真实原始证据

| 交付/证据 | 实际位置与结论 |
|---|---|
| B11 实验源码与限制 | [experiments/g1-b01-b11/README.md](../../experiments/g1-b01-b11/README.md) |
| 权威 SQLite Trigger + Outbox Cursor | [projection_source.py](../../experiments/g1-b01-b11/projection_source.py) |
| 可信 Kernel 最小权限拉取接口 | [kernel_service.py](../../experiments/g1-b01-b11/kernel_service.py) |
| 真实 Saltcorn SQLite 事务消费器 | [apply_worker.py](../../experiments/g1-b01-b11/apply_worker.py) |
| 真实 B2 / 两 Saltcorn / Chromium / SQL 集成 | [experiment.py](../../experiments/g1-b01-b11/experiment.py) |
| 单测及 CI 工作流 | [test_projection.py](../../experiments/g1-b01-b11/test_projection.py)、[s1-b11-real-business-outbox-projection.yml](../../.github/workflows/s1-b11-real-business-outbox-projection.yml) |
| **已合并 PR** | [#13](https://github.com/zealzhangz/OpenAILCAP/pull/13) |
| **main 合并 SHA** | [68da2ce8cf5cd1312866f68c22314636354ab26b](https://github.com/zealzhangz/OpenAILCAP/commit/68da2ce8cf5cd1312866f68c22314636354ab26b) |
| **最终全绿 CI** | [Actions #44908563537](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44908563537)，**completed / success** |
| CI Job | **136859260383** |
| 原始 E2E JSON、单测与 CI 日志 | [Artifact #14708123689](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44908563537/artifacts/14708123689)，`s1-b11-real-b2-outbox-two-live-saltcorn-native-evidence` |
| B11 专项 SQLite Trigger/投影消费者单测 | **28/28 PASS** |
| B10 Router CAS/Readiness 回归 | **34/34 PASS** |
| B2 Domain Kernel 回归 | **18/18 PASS** |
| B5 Tool Broker/IR 回归 | **40/40 PASS** |
| **真实 B11 三 UID、B2 两级审批、双 Native SQL、真实 HTTP/Chromium/故障回滚** | **62/62 PASS** |
| 真实付费模型调用 | **0 次** |

**失败与修复记录**：初始 [CI #44908199814](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44908199814) 仅完成前 3 项真实检查，发现 B11 源码复用 B10 Router 时启动脚本仍指向 B11 目录中的不存在的 `router.py`；修正为从受信 B10 源码目录启动。第二次 [CI #44908364712](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44908364712) **真实通过 58/59 已执行项**，在原 B10 复用检查 B11-43 中，错误地按物理 SQLite 查询返回的第一个 record 对比第一份合同，而在创建第二份合同后物理记录顺序未定义，导致断言误判。修正为**以 B2 实际返回的 recordId 精确定位源合同**，不降低预期值、不跳过测试。最终第三次 [#44908563537](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44908563537) 全部 62/62 通过。三个 Run 的失败/成功原始记录均保留，不能把前两次失败称为通过。

## 三、实际数据与身份架构

~~~text
[真实 B2 权威 Kernel UID 999]
  /authority-private/authority.sqlite （0700 dir / 0600 file）
  B2 form.submit / workflow.advance
  records 表
    └─ AFTER INSERT / UPDATE Trigger（与源记录同一 SQL 事务）
          └─ b11_outbox(app, seq, model, recordId, version, event-time content)
                seq1..4：合同 A Draft→PendingLevel1→PendingLevel2→Approved
                seq5..8：合同 B Draft→PendingLevel1→PendingLevel2→Approved
  v4 POST /apps/app-a/projection/pull
    └─ 仅独立随机 projectionToken，固定 app-a、allowlist 四列、cursor limit<=100
                │
                ▼
[受信实验控制器] 仅拉取、校验、传递事件 JSON（持 token）
                │
                ├─ stdin event batch → [Native Saltcorn UID 997 / v1 DB]
                │                     SQLite BEGIN IMMEDIATE
                │                     s1_contracts + b11_record_map
                │                     + b11_projection_receipts + b11_projection_cursor
                │
                └─ stdin event batch → [Native Saltcorn UID 997 / v2 DB]
                                      相同的原子消费事务与独立持久 cursor
                       ▲                    ▲
                       └── 两个真正在线的 Saltcorn 1.7.0-beta.5 Native Web
                           v1 View 3 列 / v2 View 4 列
                                │
[独立 Router UID 995] ───────────┘
  只读 GET View + B2 release.read-only token + epoch CAS
  真实 Chrome：v1→v2、在途请求固定、v2 故障 503、授权回滚 v1
~~~

**特别强调身份与数据流**：Kernel 的 `projectionToken` **不**授予 B5 现有 `release.read/form.submit/workflow.advance/app.publish` 等工具。Native Saltcorn 进程收到的只有单向业务事件 JSON，没有 Token、Kernel DB 路径、Kernel 配置或数据库管理员账号。真实 Native UID 使用 OS `open(O_RDONLY)` 尝试读取 Authority SQLite 和密钥配置，均因 DAC 被拒绝。受信 CI Controller 有 sudo 权限，仅属于研究测试编排，不能等同于正式生产投影服务的身份管理。

## 四、B11 实际 62 项 E2E 中新增的 18 项

### 4.1 源端事务、事件时点与最小权限（B11-45—48）

- 真实 B2 `form.submit` 插入合同 A 后，依次真实调用 `workflow.advance` 完成两级审批；源 SQLite `b11_outbox` **seq1..4** 事件时点状态精确为 `Draft, PendingLevel1, PendingLevel2, Approved`，每个事件携带真实 recordId/version/四列数据/内容 Hash。**没有把最终 Approved 状态伪装成四个不同历史事件**。
- 未授权拉取 → HTTP **401**；独立 `projectionToken` 试图访问原有 B5 `release.read` → **401**；非法 `after/limit` → **422**。源端只投影 `app-a/model.contracts`，未对其他 App 开放。
- 28 条独立单测另直接证明：在 B2 records 插入/更新的 SQLite 事务回滚时，Trigger 生成的 Outbox 同样回滚；事件时点 payload 不随以后状态变更而重写；非白名单 app/model 不投影。

### 4.2 原生真实 SQLite 投影、幂等与失败事务（B11-49—56）

- 两套 Saltcorn Native 数据库均先真实 `reset-schema/install-pack/create-user`，**未执行 B9/B10 的 seed-contract.js**，独立 Oracle 先确认原生合同表为空。
- Native v1 通过 Saltcorn UID 的 `apply_worker.py` 从 B2 Outbox seq1..4 逐条物化，实际 Native `s1_contracts` 仅一份合同 A、标题与 B2 权威完全相同、状态 **Approved**；Native cursor=4、receipts=4、record mapping=1。
- 将同样四条事件重复送入 Native v1：`applied=0,replayed=4`、无重复合同。改变旧事件 payload 并重算 Hash 后重放：**REPLAY_HASH_CONFLICT**，原生 cursor 不变。
- Native v2 在一个真正 SQLite `BEGIN IMMEDIATE` 事务处理四条事件，**故意在 COMMIT 前抛错**：确认 Native rows=0、receipts=0、cursor=0，未出现半提交；同一批原事件再次重试后 `applied=4,cursor=4`，物理 SQL 业务行与 Native v1 相同。
- 真实 Saltcorn UID 对权威 SQLite/配置的 `open(O_RDONLY)` 访问均被拒绝。两个真正在线的 Saltcorn v1/v2 原生页面业务行一致，而 View 列分别为 3 和 4；这不等于两版本执行逻辑/缓存全语义等价。

### 4.3 第二份真实 B2 合同在线增量投影（B11-57—60）

- 两个真实 Saltcorn Web 服务**已经同时在线**、B2 发布指针已是 v2、Router 已完成 v1→v2 CAS 且 Chromium 实际看到 v2 后，再由 B2 `form.submit` 创建合同 B `HT-2026-000002`，经两级审批到 **Approved**，源 Outbox 追加 **seq5..8**。
- 只传递 `after=4` 的四个新增事件，v1、v2 两份独立原生 SQLite 均从 cursor4 增量推进到 cursor8，均有**两份 Approved 合同**，receipts=8；没有重置 Native DB，也没有重启 Saltcorn 服务。
- 两个真实 Native HTTP GET、Router 当前 v2 HTTP GET 和真正 Chromium 页面均看见**第二份由 B2 真正创建的合同号**。因此本轮首次获得“**权威 B2 业务新增/审批 → Saltcorn 原生页面在运行中显示**”的有限真实证据，不再是同合同号的独立 fixture。

### 4.4 真故障、发布回滚与不撤销业务事实（B11-61—62）

- 保留 B10 已真实验证的 v1→v2 预热/Manifest 校验/Router CAS/在途旧请求版本固定、重复 changeId 幂等、错误回滚 409。真实结束 v2 Saltcorn 进程，前端**503**，不伪装为自动零停机；B2 权威合同仍然 Approved。
- 受权 B2 Publisher 真执行 `app.rollback` v2→v1，再由 Router epoch CAS 回滚前端 v2→v1；真实 Chromium 与 HTTP 恢复 v1。
- **UI/Release 回滚后 Native v1 cursor 仍为 8、两份合同仍 Approved，页面仍显示第二份合同**。独立 B2 SQL Oracle 验证权威数据库**2 份 Approved 记录、8 条源 Outbox 事件、2 份不可变 Release、最新草稿 revision5**；App B 完全不变。**业务事实没有随 UI 版本回滚而被撤销。**

## 五、严格限定的技术结论及下一轮 P0

B11 提供了**真正业务数据**从权威内核到可删除 Saltcorn 派生实例的最小单向协议，并验证源端记录/Outbox 原子性、事件时点内容、Consumer 事务、持久 cursor+receipt、重复/错序/哈希冲突拒绝、真实 Native 增量展示、失败事务重试、发布回滚不回退业务事实。这显著推进了 B9/B10 的静态页面原型。

**但以下缺口仍阻止 G1 和生产上线：**

1. **并非通用或后台自动 CDC**：Trigger 只覆盖 app-a 的一个 Model，只有插入/审批更新，不含 Delete/Schema Migration/跨服务业务操作。投影由可信测试控制器主动拉取并送入 Native Worker，**未实现持续后台 Worker、队列/延迟指标/死信、重启自动追赶、网络中断后的自动恢复**。
2. **业务行权限和脱敏尚未实现**：只对固定四列做 allowlist；当前测试合同不含 PII，因此没有真实 PII 脱敏、动态用户行权限、租户隔离或权限撤销同步。Native 视图是匿名公开测试页面，**不可当作企业业务生产权限方案**。
3. **Saltcorn Native 派生数据库仍可由 Saltcorn UID 改写**：Consumer 对将要更新的记录检测已有行漂移并拒绝，但旧数据被直接改写后、尚无新事件时，原生前端可能读到污染数据。没有只读挂载、完整性持续巡检或基于发布物签名的生产保证。
4. **Event Hash 不是数字签名**：Hash 检查错误/误重放，不防拥有 Consumer 写权限的恶意主体伪造业务事件。Consumer 仅有受信 Controller 在测试中调度，**没有正式跨主机认证/消息签名/传输加密**。
5. **两套 Saltcorn v1/v2 同一 Runtime OS UID**，Router 仍是单实例内存状态，原生端口可由本机其他主体直连，故障时实际返回 503；没有跨 Router 节点日志/切换持久化、K8s/Ingress、长连接、生产零停机或跨系统原子发布。B2 发布指针与 Router 指针仍是顺序操作。
6. **B2 Form/Workflow 在 Kernel 真实执行**，Saltcorn 仅是数据行和 View 的可删除物化展示，未验证 Native 业务表单、审批流、B4 Code、插件/Agent 的完整语义等价。不能把“审批结果显示在 Saltcorn”误写为“Saltcorn 原生审批引擎已实现”。

**阶段判断**：S1 **IN_PROGRESS** / G1 **NOT_PASSED** / G1-B01 **PARTIALLY VALIDATED / OPEN**；正式冻结 W01—W24 **0/24 FULL PASS**，TC01—TC18 **0/18 FULL PASS**。B11 **62/62** 只代表本次独立、范围受限的真实研究 E2E，不自动计入冻结门禁。

**建议下一步 B12**：优先建设**可信后台消费者与恢复控制面**（持久 checkpoint、源事件范围审计、消费者重启/宕机/网络分区后追赶、Native 派生数据漂移/重建与读取前防污染）；随后引入真正的租户/用户授权和字段脱敏、跨 Release Schema 兼容迁移，并为 W17/W20/W24 设计对应的完整正式测试，而不是仅增加 UI 功能。
