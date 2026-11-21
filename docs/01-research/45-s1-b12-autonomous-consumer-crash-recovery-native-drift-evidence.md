# S1 研究报告 45：B12 真实后台消费者、崩溃/HTTP 503 自动追赶与 Native 派生漂移巡检

**日期：2026-11-21。最终 B12 GitHub Actions #44910951780：completed / success；真实 E2E 79/79 PASS（B11 基线 62 项 + B12 新增 17 项）；B12 单元 22/22、B11 回归 28/28、B10 回归 34/34、B2 回归 18/18、B5 回归 40/40；0 次 DeepSeek 调用。** B12 是研究专项，并未使冻结 W01—W24 或 TC01—TC18 获得任何 FULL PASS。

## 一、与 B11 的实质差异

[B11 报告 44](44-s1-b11-authoritative-business-outbox-native-projection-evidence.md) 已验证真实 B2 `records` SQLite 事务 Trigger Outbox、真实 Saltcorn Native SQLite 物化、事件时点内容、原子 Cursor/Receipt、两套 Saltcorn HTTP/Chromium 在线业务数据增量显示。但每批业务事件仍由**受信 CI Controller 显式调用同步函数**，未验证长期运行、消费者进程意外退出、源 HTTP 失败后的恢复。

B12 在保留 B11 62 项完整真实 E2E 的基础上，新增**独立长期运行的消费者 OS 进程**，通过私有 Bearer Token 按源 Outbox 拉取、通过 Saltcorn UID 执行 B11 Native 原子事务应用；每次轮询先检查 Native 全量映射行与 Receipt 连续性，读取**Native SQLite 已提交的持久 cursor**，再请求源事件，绝不另存可能超前的 Consumer 本地 cursor。状态文件只记录状态/游标/延迟/失败次数，不写入 Token、源 DB、Native 私有环境或业务敏感值。

## 二、可追溯交付与原始证据

| 项目 | 已验证位置/结果 |
|---|---|
| 研究工程与限制 | [experiments/g1-b01-b12/README.md](../../experiments/g1-b01-b12/README.md) |
| 真正长期运行的消费者 | [consumer_daemon.py](../../experiments/g1-b01-b12/consumer_daemon.py) |
| Native 全量映射/Receipt 巡检 | [audit_native.py](../../experiments/g1-b01-b12/audit_native.py) |
| Saltcorn UID 已提交 checkpoint | [native_checkpoint.py](../../experiments/g1-b01-b12/native_checkpoint.py) |
| 真实 Saltcorn SQLite 原子应用 | [native_apply.py](../../experiments/g1-b01-b12/native_apply.py) |
| 全量真实场景（B11 62 + B12 17） | [experiment.py](../../experiments/g1-b01-b12/experiment.py) |
| B12 消费者单元契约 | [test_consumer.py](../../experiments/g1-b01-b12/test_consumer.py) |
| Ubuntu24.04、Node24、Saltcorn CLI 1.7.0-beta.5、Python3.13、Chromium1.56 CI | [s1-b12-background-consumer-recovery.yml](../../.github/workflows/s1-b12-background-consumer-recovery.yml) |
| **PR 已合并** | [#14](https://github.com/zealzhangz/OpenAILCAP/pull/14) |
| **main 合并 SHA** | [8ce7324d85aa1d06a8269bc6351d43a95678b06d](https://github.com/zealzhangz/OpenAILCAP/commit/8ce7324d85aa1d06a8269bc6351d43a95678b06d) |
| **最终 GitHub CI** | [Actions #44910951780](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44910951780)，**completed / success** |
| **CI Job** | **136866440843** |
| **机器可读 JSON + 完整日志** | [Artifact #14709752514](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44910951780/artifacts/14709752514) |
| B12 Consumer 单元 | **22/22 PASS** |
| B11 原子 Outbox / Native Consumer 回归 | **28/28 PASS** |
| B10 Router / B2 Kernel / B5 Broker 回归 | **34/34 + 18/18 + 40/40 PASS** |
| **B11 原生集成 62 项 + B12 故障/恢复 17 项** | **79/79 PASS** |
| 付费模型调用 | **0 次** |

**真实失败记录（未隐藏）**：

- [第一次 CI #44910619739](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44910619739)：单测全部通过，真实 E2E 在模块导入时失败（B12 脚本复用 B11 `projection_source` 时遗漏 Python 模块搜索路径）。补上明确 `g1-b01-b11` 路径，未跳过任何测试。
- [第二次 CI #44910775406](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44910775406)：真实 B11 62 项和 B12-63—75 均 PASS，在 **B12-76** 发现真实 Saltcorn Native SQL 物理行被篡改，但原生 HTTP 页面**仍显示缓存的旧标题**，因此原先要求“HTTP 必须立即显示篡改标题”的断言不符合真实 Native 缓存行为。保留独立 SQL Oracle 的篡改证据，将负对照精确调整为**Native SQL 真实存在污染、Consumer 报 DRIFT，但原生 HTTP 仍返回 200、并未执行读取前完整性拦截**，同时在 JSON 中明确记录 `httpShowsTamper=false`，不宣称缓存是防护机制。
- [最终 CI #44910951780](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44910951780)：全部 **79/79** PASS。前两次失败记录仍保留；**只有最终 CI 是本轮完成证据**。

## 三、真实测试：自动消费、崩溃恢复、网络故障

### 3.1 B12-63—66：独立进程自动运行

- 先在真正 B2 Domain Kernel 中创建并两级批准两份合同，源 Outbox seq1..8；两个真正 Saltcorn Native v1/v2 的 SQLite 通过 B11 原子投影持有两份 Approved 合同，UI/Release 已真实回滚至 v1。
- 启动**独立 Python daemon OS 进程**，真实从 Native SQLite `b11_projection_cursor` 读取 8，向 B2 专用只读接口轮询，自动进入 `CAUGHT_UP`，`lag=0`。Saltcorn UID 尝试 O_RDONLY 打开 Controller 私有 0600 Token 配置，**DENIED**；状态文件无 Token。
- daemon 正在运行时，B2 **真正创建第三份合同**、真实两级审批，源 Outbox seq9..12。daemon **无需任何 Controller 手动同步调用**，Native SQLite 自动 cursor8→12，原生 HTTP 和 Router HTTP 都显示第三份合同。

### 3.2 B12-67—70：真实 SIGKILL / 新进程重启

- 真实 `SIGKILL` 终止 Consumer OS 进程，Saltcorn v1 进程仍在线且 HTTP200。
- B2 Kernel 在 Consumer 宕机期间继续真实创建并两级批准第四份合同，源 Outbox 到 seq16，Native SQLite **仍为 cursor12 / 3 行**；业务权威写入不被下游故障阻断。
- 重新启动**新的 daemon 进程**，它不依赖旧进程内存/私有 offset，从 Native 已提交 cursor12 读取源 seq13..16，自动推进 cursor16。独立 SQL Oracle 验证 Native **4 份合同、16 条 Receipt、无重复**。

### 3.3 B12-71—74：真正 HTTP 503 后追赶

- 通过真实 `ThreadingHTTPServer` 源代理使 Consumer 的实际 HTTP POST 返回 **503**，但 B2 Kernel 原业务 API 仍正常。
- 在 Consumer 源 HTTP 503 期间，B2 **真实创建并批准第五份合同**，源 Outbox seq20；daemon 报 `SOURCE_UNAVAILABLE` 且失败次数增加，Native cursor **停留16**，未虚构消费成功。
- 解除代理故障后，daemon **自动追赶 cursor16→20**，Native 5 行、Receipt20、Mapping5。两个真实 HTTP 页面均展示第五份合同，**无手动同步调用**。

### 3.4 B12-75—77：真实派生行污染与原生 HTTP 负对照

- Saltcorn UID 直接对自己拥有的**真实派生 SQLite**执行 `UPDATE s1_contracts SET title='B12_TAMPERED'`，**未生成任何 B2 源事件**。
- daemon 每轮在拉取前巡检所有 Native `b11_record_map` 的 hash、实际 `s1_contracts` 行和 `b11_projection_receipts` 连续性。即使无新事件，仍检测到 `DERIVED_DRIFT`，并**停止继续消费**；cursor20 不动。
- **重要负面结果**：真实 Native HTTP **仍返回 200**，没有读取前 fail-closed；本次真实 HTTP **没有展示篡改标题**（`httpShowsTamper=false`），而是显示缓存的旧标题。**缓存旧值不是已验证的安全隔离或一致性保证**。真实 SQLite SQL Oracle 已独立证明物理行污染，消费者已发现漂移；不能据此声称 Native 读取安全。
- Saltcorn UID **手动**将标题恢复为权威值，daemon 后续巡检恢复 `CAUGHT_UP`、cursor20、Receipt20。**这不是自动修复，也不是数据库重建**。

### 3.5 B12-78—79：最终独立 Oracle + 真实 Chromium

- 独立 B2 SQL Oracle：**5 份 Approved 合同、20 条事件、App B 完全不变**。
- Native v1 业务 SQLite：5 行、20 Receipt、cursor20。
- 真实 Chromium 通过 Router v1 页面看到第五份 B2 权威合同；UI/Release 仍 v1，业务事实没有被回滚。

## 四、P0 限制与下一步

**B12 只证明受限的、可复现的后台消费者自动运行与故障恢复**，不能等同生产可用：

1. **Consumer 身份仍是可 sudo 的 CI Runner**。它可以以 `runuser` 启动 Native UID Worker，持 B2 专用投影 Token；这不是经过生产安全验证的独立 Consumer UID/受控 IPC、最小权限授权或跨主机认证。Native 进程自身没有 Token，但 CI Controller 仍有特权。
2. 真实 HTTP 503 是同机代理故障，不是跨机网络分区、机房断电、存储断电、内核故障；真实 SIGKILL 是 Consumer 进程故障，不等于 SQLite 断电耐久性已验收。
3. Native **真实污染后 HTTP200**；定期巡检会报 DRIFT，但没有**读取前 fail-closed**，且 HTTP 可能返回缓存的旧值或污染值；没有签名验证、自动重建或基于可信 Manifest 的读时证明。**这是下一阶段 P0**。
4. 没有 systemd/K8s、Leader Election、多个消费者互斥租约、死信队列/告警系统、跨机 TLS/mTLS、凭证轮换、企业 SLA、生产可观测性。状态文件是实验私有 JSON，并非生产控制面。
5. 仅 `app-a/model.contracts` 的固定四列 INSERT/UPDATE 事件；无 Delete/Schema Migration、PII 脱敏、租户行级 ACL、跨版本兼容、多模型/全量业务工作流和外部副作用一致性。
6. Saltcorn Native 的同 UID 写入权限仍存在；Router 仍是单实例内存 CAS、Native 故障 503，无生产 HA/零停机。B2 Form/Workflow 在可信 Kernel 执行，Saltcorn 只物化结果，不代表原生流程等价。

**正式结论不变：S1 IN_PROGRESS、G1 NOT_PASSED、G1-B01 PARTIALLY VALIDATED / OPEN，冻结 W01—W24 0/24 FULL PASS，TC01—TC18 0/18 FULL PASS。** B12 79/79 是**专项研究**，不能转为冻结门禁 FULL PASS。

**建议 B13**：用真正独立的 Consumer OS UID 与受控 Native Apply IPC 消除 CI sudo 的生产授权缺口；在可信 Router 上加入**读前可信 SQL 完整性校验与拒绝污染**（包括 Native HTTP 缓存与旁路的真实负对照），然后验证授权重建派生数据库和消费追赶；逐步实现跨实例授权与租户行权限，而不是直接扩大业务模型数量。
