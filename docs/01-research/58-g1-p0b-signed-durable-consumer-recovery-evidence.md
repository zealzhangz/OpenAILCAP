# G1 P0-B：同实例 B14 签名事件持久消费者及故障恢复（P0B-16—23）

> **验收属性：仅为冻结 G1 的局部 P0-B 证据**。在同一 B9 Domain Kernel、B2 `authority.sqlite`、B11 事务 outbox、B14 Ed25519、B15 Publisher 与 B17 已启动 Chromium 只读页面上开展，**不新建权威服务或平行研究路线**。保留 `G1 NOT_PASSED`、W 0/24、TC 0/18 FULL PASS 的正式门禁。

## 1. 上一轮实质阻断与修正

[报告 57](57-g1-p0b-authoritative-business-outbox-signed-live-evidence.md) 已证明真实 B2 人工提交合同经过 B11 同事务 outbox、B14 签名到 B15/B17 的数据真源性；但 **Native 的第二行仍由受信 CI Controller 用 Saltcorn CLI 手动补录**，未具备正式事件消费者的持久 cursor/receipt、自动重放、来源中断恢复与 OS 权限边界。即使 83/83 局部检查全绿，仍不可将其当成 W17/W18/W24/TC16 通过。

此次仅把这一手工消费缺口改为**实际非特权后台进程 + 受控本机 IPC + 同事务原生 SQLite 持久回执**：

1. **B14 来源**：专用 Kernel UID 在原 B2 `authority.sqlite` 内调用 B11 的 `projection_source.pull`，只对从同一不可由消费者写的 outbox 读取的每条真实事件调用原 B14 `sign_event`，用固定本地端口和随机 bearer 提供研究范围内的 HTTP `/v5/apps/app-a/projection/signed-pull`。私钥仍只有 Kernel UID，Source 可以独立关闭/重启，Kernel 主进程不重启。
2. **B13/B14 真 IPC**：在已用过的 Saltcorn Native Linux UID 下开启签名 Broker，复用原 `SignedBroker` 和 B13 `SO_PEERCRED`、Unix socket 目录 Linux group DAC（`0750`，socket `0660`）。Broker 对**每条事件**先验证 Ed25519、公钥和来源事件哈希，才调用 B11 的 `apply_worker.apply`。
3. **B11 原生持久游标与回执**：在**新建的无任何 seed 合同、用真实官方 Saltcorn CLI 从同一已发布 v1 Pack 安装的派生 SQLite**上，用原 B11 `ensure_tables/apply`。业务行、source record ID→原生行映射、签名事件 eventHash receipt 和 app cursor 在 **同一个 `BEGIN IMMEDIATE` SQLite 事务中提交**。消费者进程不保存超前 checkpoint，进程重启后每次从 Native durable cursor 继续；以前收到的签名批次可重放但不重复插入。
4. **第六个独立消费者 UID**：`ailcapb9cons` 无 sudo、无 B2 authority.sqlite、无 Native SQLite、无签名私钥，仅持源读取 bearer 与 Native signed IPC 能力；Plugin、Renderer 等 UID 不能连接 IPC。只读 Publisher UID 仍独立，B17 URL/Chrome 始终同一个进程。消费者错误时保留 Native 上次已提交游标，来源不可用时等待重试。
5. **B15/B17**：消费者完成并通过真实 Native SQL cursor、receipt、mapping、rows 的独立 Oracle 检查后，复用现有 B14 Release/B11 业务签名和 B15 Publisher 验证及 `fsync+os.replace` 单文件切换；B17 每请求对最新 B2 发布指针及业务 head/digest 前后检查，旧快照只可物理保留，不得在签名来源前进后继续返回伪最新页面。

## 2. 同一实例预注册 P0B-16—23

| 检查 | 必须验证的真实行为 | 独立停机 / 判据 |
|---|---|---|
| P0B-16 | 真实 Native `saltcorn reset-schema/install-pack` 在新 DB 初始化**零条业务行**，Source KERN UID 和 Native signed Broker RUNT UID 运行，新增 CONS 第六 UID。 | SQL cursor=0, rows=0；不同 Linux UID、Native Broker SO_PEERCRED；无 bearer 的 Source 返回 401。 |
| P0B-17 | 无任何手工 Saltcorn `insertRow`，持续运行的非特权消费者从真实 B11 读取 B14 已签的两条 B2 业务数据并**自动 apply**。 | Native SQLite 真 cursor=2、receipts=2、maps=2、rows=2；Native 数据逐字段等于 B2 独立权威 SQL。 |
| P0B-18 | **用同一个 Consumer UID 和 Native IPC**，把真实来源签名 seq1—2 重新发送一遍。 | Native `replayed=2`、`applied=0`、cursor2；原生整个 checkpoint/rows 完全未变。 |
| P0B-19 | 真实终止 Consumer PID，再以同 UID/原配置启动新的 Consumer 进程，Native 与 Kernel 不重启。 | 新旧 Consumer PID 不同；新进程从 Native cursor2 恢复，无重复 receipt/row，Native SQL snapshot 前后一致。 |
| P0B-20 | **终止 Kernel 签名来源 sidecar（非 Kernel 主进程）**，Consumer 不退出仍重试；在同一 B2 浏览器人工提交第 3 条合同。 | 真实 Consumer 状态 `SOURCE_UNAVAILABLE`、Native cursor 仍2；B2 outbox head3，原 B17 503 fail-closed，已验证旧 SQLite 快照字节哈希保持不变。 |
| P0B-21 | 恢复相同 Source 端口/公钥/随机 bearer，不重启 Consumer、Native Broker 或 B2 主进程。 | Native 自动消费新签名事件，cursor3/receipts3/maps3/rows3；B15 尚未上架时 B17 保持 503。 |
| P0B-22 | 同一 B15 Publisher 对已经真实消费的 3 条合同源签名、Native SQL、B2 head/digest 再比对后原子发布；浏览器同 URL reload。 | B17 HTTP 200、3 条真实合同、B2 发布仍 v1、原 B17 进程和 Chromium 不重启、app-b 不变。 |
| P0B-23 | 权限攻击：Consumer 直接打开 B2/Native 两种私有 SQLite；Plugin 和 ReadOnly UID 真正 `AF_UNIX socket.connect`；匿名访问 Kernel 签名来源。 | 前四者全部实际 DAC PermissionError，匿名 Source 401；Native B11 cursor/receipts 不丢，B17 仍可读已验证快照。 |

**注：**此处特意使用真正的 `socket.connect()` 来判定 Unix socket 权限，而不是将任意 Unix socket 的 `os.open()` 失败错误地当作 DAC 授权证据。

## 3. CI 执行与原始证据

目标：之前 **83 个真实同实例集成检查 + 8 个本轮检查 = 91**。B9 模块原 **49** 个单位测试、B2 **18**、B5 **40**、B6 Docker **25**，并补入实际依赖的 B11/B12/B13/B14 单元回归。**模型调用 0**，不触发真实 DeepSeek。**只有当前提交 SHA 的全部 CI 通过才记录为本轮已验收的局部证据**。

最初功能代码实际成功 [GitHub Actions #44981780941](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44981780941) 证实 `91/91`，但此运行还早于后续的更严格 AF_UNIX socket.connect 安全断言及 CI 本地依赖全量回归；故仍要求**最新头部 SHA 再跑一套全绿**后方可合并。

失败观察记录：既有 Saltcorn v1 首次浏览器加载存在偶发 `Page.goto Timeout`（[Actions #44981802034](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44981802034)，在本轮 P0-B 启动之前停于前序 B9-15）。本轮为**真实 Native HTML GET** 增加仅 3 次有界重试，并继续检查 HTTP 200 和合同实际内容；重试不应屏蔽真正的失败。一次 GitHub Actions YAML 拼接失误（#44982059137）已修正，保留失败历史。

## 4. 明确未达到 G1 的内容

尽管本轮验证了**实际长期运行的、持久化的、可自动追平的 B14 签名 B11 消费**，但它仍是单实例、单 app、单合同模型的研究系统；Native UID 仍有直接修改可丢弃派生 SQLite 的 OS owner 权限，且目前尚未验证生产多 Consumer 主备、生产密钥托管/轮换、跨进程 crash-consistency 全边界、外部服务 `UNKNOWN`/changeId 补偿。B15 发布仍由受信 Controller 在核验通过后调用，**尚不是自动协调的发布事务**；B2 pointer 与 B15 snapshot 的窗口继续通过 503 fail-closed，尚非无停机的一致提交。Form/Workflow/B4 Code 全依赖产物和冻结合同业务旅程尚未真正贯通。

**所有 42 项冻结 W/TC 仍 `NOT_RUN`，G1 `NOT_PASSED`。**下一步继续而且仅继续 P0-B：真实消费者之外的**发布一致性决策、工作流/代码/表单依赖闭包与不可知外部副作用**。不得拿 91 项局部集成断言冒充正式冻结矩阵 FULL PASS。


## 5. 最新完整原始 CI 实测（2026-11-22，合并前）

**最新完整成功**：[GitHub Actions #44982079396](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44982079396)，`completed/success`，运行代码 SHA **`6cf8676feb36358ec658a3c4d32e963eac123071`**，Job **137084552030**，[完整原始 Artifact #14737404471](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44982079396/artifacts/14737404471)。

实际命令与结果：
- **91/91** 同一 B2 authority.sqlite/真实 Saltcorn/独立 UID/B17 同 URL 的局部集成检查 **PASS**，`modelCalls=0`，`g1Passed=false`。
- B9 `test_projector test_pack_approval_gate test_p0b_business` **49/49**，依赖原工程真实回归 B11 **28/28**、B12 **22/22**、B13 **22/22**、B14 **24/24**；B2 **18/18**、B5 **40/40**、B6 真 Docker 隔离策略 **25/25**。各项均是真实 GitHub Actions 日志中的 `Ran … tests / OK`，未直接等同正式验收 W/TC。
- **P0B-16 PASS**：六独立 Linux UID `KERN=999`、`RUNT=997`、`PLUG=995`、`PUBL=994`、`READ=993`、`CONS=992`；新 Native 真实 `saltcorn reset-schema/install-pack` 后 **0** 条业务行，实际 B14 source bearer 验证。
- **P0B-17 PASS**：新的 Native 物理 SQLite **cursor=2、receipts=2、mappings=2、records=2**，签名消费者自动提交、**从未手工 seed 该数据库**。
- **P0B-18 PASS**：以真实 Consumer UID 将来源 1、2 两条签名事件原样通过 Native SignedBroker 重放，返回 **replayed=2, applied=0**，数据库完整内容与 cursor/receipt 不变。
- **P0B-19 PASS**：终止真实 Consumer 进程 PID `6302`，由 PID `6370` 重新从 Native SQL **cursor=2** 恢复；无重复映射/回执，Kernel/Broker 均未重启。
- **P0B-20 PASS**：实际关闭独立 Kernel 签名 Source，Consumer 状态 `SOURCE_UNAVAILABLE` 且 `failures=2`；同一 B2 Chrome 人工创建第三条合同时 **B11 head=3、Native cursor=2**，B17 返回 **503**，之前 verified 快照文件 **SHA 未改变**。
- **P0B-21 PASS**：恢复同一固定端口、同一 Ed25519 私钥和 bearer，不重启 Consumer；**Native cursor/receipts/mappings=3** 自动追平；Publisher 尚未切换之前 B17 仍正确返回 503。
- **P0B-22 PASS**：对 B2 真实三条、B14 三个已签事件和自动消费的 Native SQL 三条执行 B15 原子发布；原 B17 浏览器 **HTTP 200，三行，Release 仍 v1，Router 未重启**；不涉及第三条的手工 Native seed。
- **P0B-23 PASS**：Consumer UID 直接打开 B2 及 Native SQL 分别获 `DENIED`；Plugin 和 Reader 两种非授权 UID **实际 `socket.connect(AF_UNIX)`** 都返回 `DENIED`；未授权 B14 来源请求 **401**，Native checkpoint 仍 3，B17 发布页面仍可用。

前述最初功能跑绿但尚未覆盖真正 AF_UNIX connect 的 [#44981780941](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44981780941) 仅作为早期过程记录；**以上 #44982079396 才是本轮严格测试和完整依赖单元回归的有效证据**。此结果不证明跨 B2/B15 数据库全局原子发布、生产高可用、Form/Workflow/B4 Code 全依赖闭包、外部 UNKNOWN/补偿、Native UID 直接修改派生 DB 的消除；不改动 G1 门禁。
