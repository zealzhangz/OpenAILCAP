# S1 研究报告 46：B13 四真实 Linux UID、受控 AF_UNIX IPC 与 B2/Native 读取前完整性防护

**日期：2026-11-21。最终 GitHub Actions #44917605505：completed / success；B13 独立单测 22/22、B12 回归 22/22、B11 回归 28/28、B10 回归 34/34、B2 回归 18/18、B5 回归 40/40，共 164/164 单元/契约回归；真实 Saltcorn/B2/Chromium/Linux UID 端到端 104/104 PASS（B11 62 + B12 17 + B13 25）；0 次 DeepSeek。** 本报告中“PASS”是**范围受限的专项检查**，不意味着所有安全目标已通过，特别是 B13-104 是**成功暴露漏洞的负对照**。

## 一、B12 之后仍必须解决的问题

[报告 45：B12 后台 Consumer 自动恢复](45-s1-b12-autonomous-consumer-crash-recovery-native-drift-evidence.md) 已证明：真实 B2 SQLite Trigger Outbox → Saltcorn Native SQLite 持久 Cursor/Receipt → 后台 Consumer 自动消费；消费者 SIGKILL、真实 HTTP503 后自动恢复；周期性检查 Native 派生行漂移。但 B12 Consumer 在具有 `sudo runuser` 能力的 CI Runner 身份运行；Native SQL 被同 UID 污染后，原生 HTTP 仍可返回200，后台巡检并非读取前 fail-closed。

B13 用四个真正不同的 Linux 非 root UID 验证新的职责边界：

| Linux 身份 | 权限与职责 | 禁止 |
|---|---|---|
| `ailcapb13kern` UID999 | B2 权威 Domain Kernel、SQLite、事务 Outbox、Release | Saltcorn 原生用户不允许读取权威 DB |
| `ailcapb13salt` UID997 | Saltcorn 两套真实 SQLite/HTTP、Native Unix IPC Broker | 不持有 B2 Projection/Release Token |
| `ailcapb13route` UID995 | Guarded Router，持独立 B2 Release Read 与 Projection Read Token | 无 Native Apply Socket 授权 |
| `ailcapb13cons` UID994 | 长期运行的独立 Consumer，持 B2 Projection Token；通过 Consumer Socket 仅 audit/checkpoint/apply | **无 sudo；不能直接读写权威 DB、Native DB 或 Router Token** |

两个真实 Unix Socket：`consumer.sock` **0660 / ailcapb13pipe**、`guard.sock` **0660 / ailcapb13guard**。Native Broker 使用 Linux `SO_PEERCRED` 校验实际连接 UID；Consumer 和 Router 只属于各自 IPC 授权组，且各自不能连接对方的 Socket。两个 Socket 运行在 Saltcorn UID 下，但角色和操作严格不同：

- **Consumer Socket**：`audit`、`checkpoint`、`apply`，Native SQLite 事务原子提交；输入 JSON 限定帧大小和操作形状。
- **Guard Socket**：只能 `snapshot`，返回固定四列合同业务数据、Native Cursor、Receipt 数量、Mapping 数量与内部哈希巡检结果；**不能调用 apply**。
- Consumer 读取 Native Cursor 和提交事件**不再执行任何 sudo/runuser**；CI Runner 仍负责在测试启动/终止四个 OS 进程，**不能把测试编排的 sudo 能力等同生产服务权限**。

## 二、Guarded Router 的真实 HTTP 读取前保护

新 `guard_router.py` 运行于独立 Router UID，仅公开 `GET /view/s1_contract_list`；不转发 Native 管理、写入、Cookie、会话、其他路径。每次业务 GET 在**返回 Saltcorn HTML 前**：

1. 向 B2 Kernel `release.read` 验证当前发布指针与 v1 Manifest SHA；
2. 用独立 B2 Projection Token 分页读取**权威源 Outbox**，逐条验证连续序号、单应用/单模型、固定四列与 SHA256 内容哈希，并还原最新业务行；
3. 经 **guard-only IPC** 请求 Saltcorn UID 对**真实 Native SQLite**执行只读物理快照：核验 record_map 行哈希、Receipt 连续性、Cursor 与源 Head 相同、实际业务行与 B2 权威最新行完全相同；
4. 真正请求 Saltcorn 原生 HTTP，检查预期合同编号存在；在**发送 HTTP 200/HTML 前再次执行**步骤 1—3。任何不匹配返回 HTTP503，不返回原生 HTML。

**重要安全边界**：Native Broker 与 Saltcorn **共享 UID**。本实验只证明“未被篡改的 Broker 如实读取 Native SQL”时可在 Router 入口检测真实 SQL 污染、数据延迟或未授权事件；如果 Saltcorn UID 完全失陷并修改 Broker/伪造 Snapshot，仍可能骗过 Router。双次校验不消除最后校验到 HTTP 响应之间的 TOCTOU，也不提供生产线性一致性。原生 Saltcorn 直连继续是未保护旁路。

## 三、原始交付与最终成功证据

| 交付物 | GitHub 位置 |
|---|---|
| 完整研究范围与未通过项目 | [B13 README](../../experiments/g1-b01-b13/README.md) |
| 四 UID + 真正 Native/Chromium E2E 104 项 | [experiment.py](../../experiments/g1-b01-b13/experiment.py) |
| Saltcorn UID Native AF_UNIX Broker | [native_ipc.py](../../experiments/g1-b01-b13/native_ipc.py) |
| 独立无 sudo Consumer | [consumer_daemon.py](../../experiments/g1-b01-b13/consumer_daemon.py) |
| Router UID B2/Native 双次读前核验 | [guard_router.py](../../experiments/g1-b01-b13/guard_router.py) |
| B13 22 项单元/契约测试 | [test_ipc_guard.py](../../experiments/g1-b01-b13/test_ipc_guard.py) |
| 完整 Ubuntu24.04/Node24/Saltcorn CLI1.7.0-beta.5/Python3.13/Chromium CI | [s1-b13-least-privilege-ipc-read-guard.yml](../../.github/workflows/s1-b13-least-privilege-ipc-read-guard.yml) |
| **PR #15 已合并** | [PR #15](https://github.com/zealzhangz/OpenAILCAP/pull/15) |
| **main 合并 SHA** | [712ab9cc3dcf1ef2f94745c9f4aa75fca238eee0](https://github.com/zealzhangz/OpenAILCAP/commit/712ab9cc3dcf1ef2f94745c9f4aa75fca238eee0) |
| **最终 CI completed/success** | [Actions #44917605505](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44917605505)，Job **136886465940** |
| **真实 JSON 及全量测试日志** | [Artifact #14711934942](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44917605505/artifacts/14711934942) |
| B13/B12/B11/B10/B2/B5 单元/契约 | **22+22+28+34+18+40 = 164/164 PASS** |
| B11 基线 62 + B12 新增 17 + B13 新增 25 | **104/104 真实 E2E PASS** |
| 付费模型调用 | **0 次** |

### 3.1 保留真实失败及修复记录

- [初次 CI #44917208014](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44917208014)：E2E 合并脚本中保留了 B12 旧 `data["final"]` 字典尾部，导致 Python `IndentationError`，**未执行任何 E2E**；修复源代码结构。
- [第二次 CI #44917393338](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44917393338)：**164 项单测及全部 104 项真实 E2E 已 PASS**，并输出 `S1_B13_RESULT passed=104`，但测试临时目录在退出时由普通 CI Runner 删除，遇到 Saltcorn/Router/Consumer UID 拥有的私有 Socket/Ready/Status 文件，`TemporaryDirectory.cleanup()` 报 **PermissionError**，导致 Job 最终失败。修复为**所有进程终止后**再由受信 CI Runner `sudo chown -R` 回收临时目录所有权；测试运行期间仍维持原 0700/0600/0660 权限隔离。
- [最终 CI #44917605505](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44917605505)：**164/164 + 104/104 全部通过、Job success、Artifact 已生成**。不能把前两次失败当作最终通过证据。

## 四、真实 B13-80—104 检查与独立负对照

### 4.1 B13-80—93：四 UID 最小权限与 Peer-Cred IPC

- 真正四个非 root Linux UID（本次 CI：Kernel999 / Native997 / Router995 / Consumer994）；Consumer 运行 `sudo -n true` **失败**。
- Consumer 实际 `open(O_RDONLY)` B2 Authority SQLite、Saltcorn Native SQLite、Router Token 配置均 **PermissionError**；Saltcorn UID 读取 Consumer/Router Projection Token 配置亦被拒绝。
- Native Broker 真实创建两条 Unix Socket，均 **0660**、不同 Linux Group；Consumer 实际通过 `consumer.sock` 调用 `audit`、`checkpoint` 获得真实 Native Cursor20，连接 `guard.sock` 被 DAC 拒绝；Router 通过 `guard.sock` 获得真实 Native 5 行/20 Receipt 的只读 Snapshot，但连接 Consumer 写 Socket 被 DAC 拒绝。
- Guarded Router 真实在 Router UID 进程中启动，与 Native UID 不同。

### 4.2 B13-94—98：真实受保护业务读取与无 sudo 自动消费

- Guarded Router 在 B2 Outbox20 条、Native5份 Approved 合同且已回滚到发布 v1 时，通过两次真实 B2/Native 校验返回 HTTP200、标头 `X-OpenAILCAP-Guard: B13-VERIFIED`；真正 Chromium 渲染合同列表。公共 POST 返回405。
- 启动**无 sudo 的 Consumer UID 独立进程**，从 Native Cursor20 读取 checkpoint。B2 真正创建、提交并两级批准第六份合同，Consumer 通过真实 AF_UNIX Apply Socket 自动推进 Native Cursor20→24、Receipt24；Guarded Router HTTP200 显示第六份合同。

### 4.3 B13-99—103：真实 Consumer 故障、Native SQL 污染与读取前拒绝

- 终止无 sudo Consumer，B2 继续创建、审批第七份合同，源 Outbox28，Native Cursor24。**Guarded Router HTTP503，Saltcorn 原生直连 HTTP200**，证明入口对数据延迟 fail-closed，未把旧业务页面当作最新数据返回。
- 重启 Consumer，新进程自动从 Native Cursor24 追赶至28，Guarded Router 恢复 HTTP200、显示第七份合同。
- Saltcorn UID 真正直接执行 `UPDATE s1_contracts` 污染第七份合同标题；Native SQL Oracle 独立证明污染存在。**Guarded Router HTTP503，原生 Saltcorn HTTP200**，证明本研究入口能够拒绝该类真实 Native SQL 漂移，而原生旁路仍危险。
- 由 Saltcorn UID **人工恢复**标题后，Guarded Router 才恢复 HTTP200。**没有自动修复/重建**。

### 4.4 B13-104：成功暴露重大 P0 漏洞——Consumer 可以伪造业务事件

本实验最后使用**合法的 Consumer UID**，经它被授权的 `consumer.sock` 提交**一条 B2 权威 Outbox 中根本不存在**、但字段/序号/普通 SHA256 `eventHash` 全部合法的合同插入事件：

- 原 B2 权威 Head = **28**；Native 已提交 Cursor = **28**。
- Consumer 伪造 `seq=29`、`contract_no=HT-2026-999999`、`title=FORGED_CONSUMER_EVENT`、`status=Approved`，自行计算 `eventHash`。
- **真实 Native Apply Broker 接受事件，SQLite 原子提交，Native Cursor28→29。** 这证明当前 IPC DAC + peer UID **只认证发送者的 OS 身份，不认证事件确实由 B2 Kernel 产生**。
- **Guarded Router 对比 B2 Head28 与 Native Cursor29，真实返回 HTTP503**，拒绝向守护入口提供该伪造后的页面；但是**原生 Saltcorn 数据库已经被 Consumer 伪造事件污染**，且 Native 直连没有强制经过 Router。
- **判定：B13-104 专项测试 PASS = 成功验证“Native 接受伪造事件”这一不安全负对照；“可信来源认证/Native 防污染”目标明确 FAIL / OPEN。** 普通 SHA256 内容哈希不是权威签名。不得宣称 Consumer 被攻破后仍能保护 Native 数据完整性。

## 五、架构结论与仍未解决的 P0

1. **正向**：真实四 UID、分组 Unix Socket、SO_PEERCRED 和只读/写入操作分离能够降低普通 Consumer/Router 对 Saltcorn 与 B2 私有文件的直接访问权限；与 B12 sudo-capable Consumer 相比，这是**真实 OS 权限收敛**。
2. **正向但有限**：B2 当前 Release + 完整 Outbox 与 Native SQL 快照的双次校验，可在**受限单模型、可信 Broker**前提下对已验证的滞后、SQL 污染和伪造事件返回 HTTP503；但只保护研究 Router 的单个 GET 路径。
3. **P0 未解决**：Consumer 拥有 Apply Socket 的合法访问权，**仍可伪造源事件**。需在 Native Apply 边界实现**由 B2 Kernel 生成、Consumer 无法伪造的签名/认证凭证**，或让独立受信 Broker 从 B2 直接拉取并验真；并验证重放、撤销、乱序、密钥轮换与密钥泄露。
4. **P0 未解决**：Native IPC 与 Saltcorn 同 UID，恶意 Native UID 可改写数据库、替换服务或伪造 Snapshot；必须验证**不同于 Saltcorn UID 的受信物理 SQL 读者/签名锚点**，或将派生 DB 变为不可写的版本化只读快照并由受信控制面原子发布。
5. **P0 未解决**：Native 原生 HTTP 直连继续绕过 Guard；未在网络/反向代理策略上禁止所有未守护入口。Guard 两次校验仍有 TOCTOU；源 Outbox 每 GET 全量重扫（上限1000条），没有生产吞吐/延迟/并发负载证据。
6. **工程未覆盖**：真实 TLS/mTLS、systemd/K8s、Leader Election、持久 Router Journal、HA、Schema Migration/Delete、全量 Native Form/Workflow/Code、租户行级 ACL/PII、跨服务副作用补偿、断电/跨机故障与 W17/W24 正式门禁。

**正式判定不变：S1 IN_PROGRESS / G1 NOT_PASSED / G1-B01 PARTIALLY VALIDATED / OPEN；冻结 W01—W24 0/24 FULL PASS，TC01—TC18 0/18 FULL PASS。** B13 104/104 是**专项研究证据**，不是正式门禁 FULL PASS。

**B14 建议优先**：对真实 B2 Outbox 实施权威**不可由 Consumer 伪造的事件签名**，由受信 Native Apply 验签（严格序号/版本/幂等），并引入独立于 Saltcorn UID 的物理 SQL 读前验证或只读快照；保留故意伪造签名、同 UID Snapshot 欺骗、Native HTTP 直连三组负对照，再决定是否进入生产化设计。
