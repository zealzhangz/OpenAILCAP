# G1 P0-B：真实自动发布协调器、断连恢复与 UNKNOWN 回执对账（P0B-34—43）

> **验收属性：冻结 G1 局部证据，不是 W/TC FULL PASS**。继续且只继续同一个 B9 Domain Kernel、同一个 B2 `authority.sqlite`、真实 B11 事务事件、B14 Ed25519、B13 peer-UID IPC、B15 Publisher 和 B17 Chrome；不新增第二份权威内核，**模型请求 0**。

## 一、可复现实测与真实主链

- **成功 CI**：[GitHub Actions #44987613241](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44987613241)，SHA **`e635d1d8f17c23b097f5dcb9dd21cb89d2ddf331`**，Job **137101516570**，[原始全日志与 JSON Artifact #14740548029](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44987613241/artifacts/14740548029)。
- **同实例 111/111 PASS**（此前 101 + 本轮 10）。各模块单元回归：B9 **49/49**、B11 **28/28**、B12 **22/22**、B13 **22/22**、B14 **24/24**、B2 **18/18**、B5 **40/40**、B6 Docker **25/25**。
- 真实六 UID：Kernel、Native、Plugin、Publisher、ReadOnly、Consumer。发布协调器在**非 root 的 Publisher Linux UID** 下持续运行，无 sudo、无 Kernel DB、无 B14 私钥、无 Native SQLite 直连和 Docker socket；它只持有 B2 最小发布/读取 grant、单独的 B14 **Publisher-only** 来源签名能力、通过 **SO_PEERCRED + 独立 UNIX group 0660 socket** 读取 Native owner UID 导出的**只读物理 SQL Oracle**。Consumer/Plugin 甚至不能连接此 socket。
- Publisher **真正自动**循环：B2 `publication.read` 当前 Release+业务 head+激活 epoch → Native 官方 Saltcorn 物理 `_sc_views`/表和 B11 cursor/receipt/map 检查 → Kernel UID B14 对真实 B2 Outbox 逐事件与 Release 签名 → B15 原生 Publisher 独立校验 B2、Native、Pack 并 fsync **内容寻址 PREPARED SQLite** → B2 `publication.activate` 在**同一 B2 事务**中 CAS 激活 SHA/epoch 与持久 receipt → B17 每请求双次检查 active/source，按签名 SHA 读同一张公开页面。**可信 CI Controller 不再逐行补录 Native，也不手工触发每次 B15/Kernel 激活**。
- Publisher 单独有本地持久化部署 journal，**精确保存原始 changeId、候选 SHA、expectedEpoch 和出站尝试次数**。实际 POST 前先 durable 标记 SUBMITTED。对 HTTP response timeout **先标记 UNKNOWN，再通过 B2 同事务查询 `publication.receipt` 对账**；不能判定副作用时**停止自动重发，不发明新 changeId**。若 B2 已提交则精确核对原 receipt 并标记 COMMITTED，若 receipt NOT_FOUND 则标记 OPERATOR_REQUIRED，要求明确查证/人工批准才重新投递**原 changeId**。没有把回执缺失当成外部副作用一定未发生。

## 二、独立真实检查 P0B-34—43

| 编号 | 真正执行的操作 | CI 原始证据 |
|---|---|---|
| P0B-34 | 六 UID 原系统中的 Native Publisher-only SO_PEERCRED oracle 读取 cursor/receipt/真实 Saltcorn view/row；B14 独立受限 Publisher-token 签名 Release；Plugin/Consumer 尝试 `AF_UNIX connect` | PASS：Native cursor4/receipts4，合法签名 Release HTTP200，原 Consumer token 不可访问 Publisher 签名源 HTTP401，Plugin/Consumer IPC 访问均 PermissionError 13。 |
| P0B-35 | 启动真实 Publisher Linux 进程后台自动循环，当前权威 source=head4/epoch2 已匹配；不应生成新版本 | PASS：Daemon PID 6900，`CAUGHT_UP`，B2 epoch2，原 B17 Chrome 4 行，未运行手工发布命令。 |
| P0B-36 | **B2 浏览器真实表单提交第五条**，B11→B14→Consumer→Native 自动追到 cursor5，Publisher 自动 B15 prepare 并 B2 activate | PASS：真实 B2 source/head5，Kernel epoch3，Publisher durable job 唯一 `COMMITTED/attempts=1`，原 B17 Chrome 5 行。 |
| P0B-37 | 真正关闭 Kernel UID B14 signer 来源，继续由 B2 人工创建第六条合同；Native & Publisher 不退出 | PASS：Native cursor5、Domain head6，Publisher `WAIT_NATIVE_CURSOR`，B2 active epoch3仍 head5，B17 HTTP503，未发明新 changeId。 |
| P0B-38 | 原有 B14 signer 同端口/原密钥恢复，Consumer/Publisher 均**不重启** | PASS：Native cursor6，Publisher 自动 prepare+activate 至 B2 epoch4；原 B17 Chrome 无重启呈现 6 行。 |
| P0B-39 | 第七条 B2 合同，受信**真实本地 HTTP 故障代理**先转发 Kernel `publication.activate`、观察实际 Kernel HTTP200 已提交，随后**故意丢弃响应**直至 Publisher 客户端 timeout | PASS：Publisher `unknown_count=1`、`attempts=1`、真实 B2 epoch5，随后按同一个 `changeId` 检索 committed receipt 并自动对账；原 B17 Chrome 7 行。代理仅 CI 研究环境可用，不代表生产网络。 |
| P0B-40 | 对同一已超时的 changeId 直接查询真实 B2 receipt 并执行完全相同命令重放 | PASS：`publication.receipt=COMMITTED`、Kernel 激活回执 `replayed=true`、epoch5，Publisher journal 原始出站次数仍为 1。 |
| P0B-41 | 真终止 Publisher Linux PID 6900，保留其独立 journal 和 B2 receipt，重启为 PID 7169 | PASS：无重复发布和回执、原 B2 epoch5，journal 三个已提交操作全部恢复，B17 Chrome 7 行。 |
| P0B-42 | 第八条 B2 合同，故障代理在激活 HTTP **转发前断开/无响应**，客户端看到 timeout 但 B2 并未提交 | PASS：B2 active epoch5/head7，当前 source head8，B17 HTTP503；Publisher journal `UNKNOWN→OPERATOR_REQUIRED` 且 `attempts=1`，**永不自动换 ID 重试**。 |
| P0B-43 | 查询同一 changeId 的真实 B2 持久 receipt 为 NOT_FOUND；**受信人工显式批准**用完全相同 changeId/参数提交，Publisher 持续循环检测原 receipt 完成对账 | PASS：B2 epoch6、B11/Native cursor8、Browser 8 行、app-b 完全不变，Publisher journal `attempts=1/unknown_count=1`，无新的自动重放。 |

**注**：W20 原文关注**外部**非事务副作用 UNKNOWN。本轮 P0B-39—43 验证的是**真实 B2 内核激活 HTTP**的 response-loss 与持久 receipt，对外部系统交易/发信/审批真正副作用**不构成 W20 FULL PASS**，不可把两者等同。

## 三、仍需补齐才能正式 G1 验收的真实阻断

1. W20 要求外部业务端点实际已执行/未执行时的 UNKNOWN、原始 changeId、独立业务记录与回执双 Oracle 及对账；本轮只验证 Kernel 已提交激活后的 HTTP timeout。
2. 原 B2 `apps.current_release` 领域发布/回滚和 B11 数据实时变更依然**先于** Publisher prepare+Kernel activate；Reader 会在候选准备窗口 **503 fail-closed**。本轮有自动恢复和持久决策，但不是**零停机/全局跨库事务**。
3. 真实业务的 Form/Workflow/B4 Code 扩展完整运行及多引用依赖闭包、发布回滚的副作用补偿、自动开发和人机协同、原生 Saltcorn 入口硬拦截/生产认证/插件安装撤销、真实断电/HA/PKI 未通过冻结 42 项全面验证。
4. **G1 状态：`NOT_PASSED`，W `0/24 FULL PASS`、TC `0/18 FULL PASS`，42 项全部 `NOT_RUN`**。本报告只能挂接 `partial_evidence`；`111/111` 是真实同实例局部集成检查数，不是冻结矩阵的验收通过率。
