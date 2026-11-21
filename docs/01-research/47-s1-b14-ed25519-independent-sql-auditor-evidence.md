# S1 研究报告 47：B14 Kernel Ed25519 权威签名、Native 事件防伪与第五 Linux UID 独立物理 SQL 读前校验

**日期：2026-11-21（北京时间 2026-11-22 前夕）。最终 CI：[Actions #44926315233](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44926315233) completed/success，Job 136913068933，[Artifact #14716390392](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44926315233/artifacts/14716390392)。B14 24 + B13 22 + B12 22 + B11 28 + B10 34 + B2 18 + B5 40 = **188/188 单元/契约 PASS**；真实 B11 62 + B12 17 + B13 25 + B14 24 = **128/128 真实端到端 PASS**；0 次 DeepSeek。**

> **专项研究结论，不是生产安全认证或 G1 正式门禁通过。** B14 解决了 B13-104 已复现的“合法 Consumer UID 能自行伪造普通 SHA256 事件并被 Native IPC 接受”问题，且让 Router 的 Native SQLite 审计不再依赖与 Saltcorn 同 UID 的 Broker。但 Saltcorn 仍能直接改写派生数据库，原生 HTTP 直连仍能绕过守护入口。

## 一、问题来源：B13 的两个 P0

[报告 46：B13](46-s1-b13-four-uid-native-ipc-read-guard-negative-evidence.md) 已真实证明：

1. 合法 Consumer UID 通过已授权的 Native Apply Socket，自行伪造 `seq=29`、`eventHash=SHA256` 的合同插入事件，**Native 真正提交该伪造事件**，Cursor28→29；B2 权威 Head仍28。B13 Guard 能发现差异返回503，但派生数据已被污染。OS Peer UID 校验并不认证业务事件来自 B2 Kernel。
2. B13 Guard 通过与 Saltcorn **同一 Linux UID** 的 Native Broker 获取 SQL Snapshot；该 UID 一旦失陷，可直接改写数据库，也可能伪造 Guard 的 Snapshot 响应。原生 Saltcorn HTTP 直连仍不受保护。

B14 对上述问题分别引入：**Kernel 独占私钥的 Ed25519 签名**和**第五独立 Linux UID 直接只读物理 SQL 审计**。在一个真实 B2/Native/Chromium 测试夹具中，先复现 B13 104 项测试（包括旧伪造事件成功的负对照），然后由受信 CI Controller **关闭旧无签名 Broker**，清空**一次性派生 SQLite**，使用 B2 权威 Outbox 的 28 条原始事件进行**全量签名回放**，避免混合旧无签名回执。

## 二、实现的信任边界

| 真实 Linux 用户 | 本次 CI UID | 权限与安全职责 |
|---|---:|---|
| `ailcapb13kern` | 999 | B2 权威 SQLite/Trigger Outbox；独占 0600 Ed25519 原始私钥；提供只读、Bearer 认证的签名事件 API |
| `ailcapb13salt` | 997 | 真正 Saltcorn Native SQLite/HTTP；Native Apply Broker **只持固定公钥**，每条事件先验 Ed25519 后调用 B11 原子 Apply |
| `ailcapb13route` | 995 | B2 Release/签名 Outbox 校验；通过**第五 UID 的 Guard Socket**获取真实物理 SQL，前后两次核验后才返回 Saltcorn HTML |
| `ailcapb13cons` | 994 | 无 sudo、无权威/派生 SQLite 访问、无私钥；从签名源 API 获取事件并通过受限 Consumer Socket 转发 |
| **`ailcapb14audit`** | **993** | **第五独立只读 SQL 审计者**；Native SQLite 文件组读取权限 **0640**、目录遍历 **0710**；真实 `O_RDONLY` 成功、`O_WRONLY` PermissionError；只开放 SO_PEERCRED Router UID 的 Snapshot Socket |

### 2.1 Kernel UID 的真实 Ed25519 事件签名

- [signed_projection.py](../../experiments/g1-b01-b14/signed_projection.py) 使用 `cryptography` Ed25519，生成 32 字节私钥、32 字节公钥；私钥仅写入 Kernel UID 0700 权威目录中的 0600 文件。
- [signed_source.py](../../experiments/g1-b01-b14/signed_source.py) **以真实 Kernel UID 启动**，只调用已有 B11 `projection_source.pull` 读取 SQLite Trigger Outbox 的**真实事件时间快照**，不允许 Consumer 提供任意待签消息；签名消息是 **`OpenAILCAP/B14/authoritative-contract-event/v1\0` + canonical JSON（含原始 `eventHash`）**。输出原事件、`keyId`（公钥指纹）和 `eventSig`（Base64 Ed25519）。
- Consumer、Saltcorn、Router 的真实 OS `open` 私钥均 PermissionError；Saltcorn UID 亦不能读取签名服务配置或 Router 的 B2 Token。
- 该签名认证“事件确实由受信 Kernel UID 的签名服务对 B2 权威 Outbox 输出”，不防 Kernel UID/root 自身失陷；**没有** PKI/HSM/KMS、密钥轮换/吊销/过期、签名透明日志或长期密钥运维。

### 2.2 Native Apply 必须先验签

[signed_native_ipc.py](../../experiments/g1-b01-b14/signed_native_ipc.py) 运行于 Saltcorn UID，但仅持固定只读公钥；验证每条事件完整 Ed25519 签名、keyId、字段集合、作用域及版本化签名域，**先验签、后剥离签名并调用 B11 `apply`**。B11 既有 SQLite 事务/Cursor/Receipt/RecordMap、连续序号、记录版本、重放幂等与冲突拒绝机制保留。

本轮真实验证：先通过 B13-104 证明**旧 Native Broker 会接受**伪造事件；再关闭旧 Broker、重置一次性 Native 派生数据后：

- **B14-113**：同一条只有 SHA256、没有 Ed25519 签名的 B13 伪造事件，**Native IPC 拒绝**，Cursor 保持0。
- **B14-114**：拿到一条真实 Kernel 签名事件后，篡改合同标题并重新计算 SHA256，**复用旧 Ed25519 签名仍被 Native 拒绝**，Cursor 保持0。
- **B14-115**：从 B2 真实 Outbox 读取并签名 **28 条事件**，Native 真正事务提交全部28条，物理 SQLite 为 **7份合同、Cursor28**。
- **B14-116**：再次回放全部28条相同签名事件，**28条幂等重放、0条新增**。
- **B14-125**：真实 B2 Form 创建第八份合同，Workflow 三级操作产生4条权威事件，**无 sudo Consumer 自动取得签名并应用**，源 Head28→32，Native Cursor28→32，受控 Router HTTP200 显示第八份合同。
- **B14-126**：合法 Consumer UID 使用被窃取的旧签名、伪造 `seq=33` 新合同并自行重算普通 SHA256，**Native IPC 拒绝**；物理 SQLite Cursor保持32、仍只有8份合同，Guard HTTP200。**本次真正阻止了 B13-104 类来源伪造通过受控 Apply IPC 污染 Native DB。**

**明确边界**：签名不阻止 Saltcorn UID 绕过自己的 Apply Broker **直接改写 SQLite**。B11 回执保存的是事件哈希而非签名证明，不能视为不可篡改的长期密码学审计链。OS UID、文件组授权在生产环境中需要额外的配置与监控。

### 2.3 第五 UID 独立物理 SQLite 审计

[audit_reader.py](../../experiments/g1-b01-b14/audit_reader.py) **不是 Saltcorn UID 的子进程/Socket**：它以第五真实非 root UID993 运行，直接打开 Native SQLite 进行只读 SQL 查询，检查四列合同、RecordMap、Receipt、Cursor 与 SHA256 业务行哈希；其 Socket 目录由审计 UID 拥有，`guard.sock` 仅赋予 Router 所属 `ailcapb14guard` 组 **0660** 权限，`SO_PEERCRED` 再核验 Router UID；**只开放 snapshot，不开放 apply**。

- **B14-110/111**：真实 Linux `O_RDONLY` 打开 Saltcorn SQLite 成功、`O_WRONLY` 被 PermissionError 拒绝，Saltcorn UID仍是 SQLite 所有者。
- **B14-117—120**：第五 UID 独立启动，Router 经 Guard Socket 读到 **7份合同、28条回执**，Saltcorn UID 实际连接审计 Socket 被 DAC 拒绝，Router 通过该 Socket 发 Apply 请求被拒绝。
- **B14-121/122**：受控 Router 验证 B2 当前发布 Release、**全部 Ed25519 签名 Outbox** 与第五 UID 的**真实物理 SQL**，真实 Saltcorn HTTP200、Chromium 渲染七份合同。
- **B14-127**：Saltcorn UID **真实直接 UPDATE Native SQLite** 污染第八份合同标题，独立审计 UID 读出 `clean=false`，**受控 Router HTTP503，但原生 Saltcorn HTTP 直连仍200**；审计进程没有被 Saltcorn IPC 影响。
- **B14-128**：由受信 CI Controller 指挥 Saltcorn UID **人工修复**派生行，独立审计 `clean=true`、受控 Router 恢复 HTTP200。**不是自动修复**。

此设计提升了对 Native Broker 伪造 Snapshot 的抵抗力：Saltcorn UID **不能连接、改写第五 UID 的审计 Socket/代码**。但它仍能更改 Native SQLite 的真实内容、修改其文件权限或停止提供服务，导致受控入口 fail-closed；**并不实现 Native DB 不可篡改或恶意 Saltcorn UID 全面防御**。

## 三、完整可复核交付

| 项目 | GitHub 证据 |
|---|---|
| B14 工程及范围边界 | [experiments/g1-b01-b14/README.md](../../experiments/g1-b01-b14/README.md) |
| Kernel-only Ed25519 密钥、签名/验签 | [signed_projection.py](../../experiments/g1-b01-b14/signed_projection.py) |
| 真实 B2 权威签名事件 HTTP | [signed_source.py](../../experiments/g1-b01-b14/signed_source.py) |
| Native 验签 + B11 原子事务 | [signed_native_ipc.py](../../experiments/g1-b01-b14/signed_native_ipc.py) |
| 第五 UID 真实 SQLite 只读审计 | [audit_reader.py](../../experiments/g1-b01-b14/audit_reader.py) |
| 无 sudo Consumer 自动签名同步 | [consumer_daemon.py](../../experiments/g1-b01-b14/consumer_daemon.py) |
| Router 签名 Outbox/独立 SQL 双次核验 | [guard_router.py](../../experiments/g1-b01-b14/guard_router.py) |
| 128项真实 E2E / Linux UID / Chromium / SQL 攻击负对照 | [experiment.py](../../experiments/g1-b01-b14/experiment.py) |
| 24项 B14 Ed25519/IPC 单元契约 | [test_signed_security.py](../../experiments/g1-b01-b14/test_signed_security.py) |
| Ubuntu24.04/Node24/Saltcorn CLI1.7.0-beta.5/Python3.13/cryptography/Playwright1.56 | [s1-b14-ed25519-independent-sql-guard.yml](../../.github/workflows/s1-b14-ed25519-independent-sql-guard.yml) |
| **PR #16 已合并** | [PR #16](https://github.com/zealzhangz/OpenAILCAP/pull/16) |
| **main 合并 SHA** | [1dabeba18450adbd09196e6f21acb32cb7e080a2](https://github.com/zealzhangz/OpenAILCAP/commit/1dabeba18450adbd09196e6f21acb32cb7e080a2) |
| **最终 CI completed/success** | [Actions #44926315233](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44926315233)，Job **136913068933** |
| **真实 JSON 与全量测试日志** | [Artifact #14716390392](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44926315233/artifacts/14716390392) |

### 3.1 单元/契约与端到端实测统计

| 类别 | 最终 CI 通过 |
|---|---:|
| B14 Ed25519 / IPC 单测 | **24/24** |
| B13 四 UID/Guard 回归 | **22/22** |
| B12 Consumer 自动恢复回归 | **22/22** |
| B11 权威 Outbox/事务回归 | **28/28** |
| B10 Router 回归 | **34/34** |
| B2 Domain Kernel 回归 | **18/18** |
| B5 IR/Broker 回归 | **40/40** |
| **单元/契约合计** | **188/188** |
| **真实端到端 B11 62 + B12 17 + B13 25 + B14 24** | **128/128** |
| **付费模型调用** | **0** |

### 3.2 失败证据保留

- [首次 CI #44925890843](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44925890843)：**188项单元/契约全部通过**；Ubuntu `useradd` 发现已存在同名 `ailcapb14audit` Group，拒绝创建同名 User，尚未开始 E2E。改为独立 `ailcapb14readers` 补充组，同时保留 `ailcapb14audit` User。
- [第二次 CI #44926049128](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44926049128)：188项单元与真实 B13 104 项及 B14-105—120 **共120项 E2E 全部通过**，但 B14 Guard 配置校验遗留 B13 临时目录前缀，进程 fail-closed `GUARD_CONFIG_INVALID`，未执行 B14-121—128。修正为 B14 独立目录前缀。
- **[最终 CI #44926315233](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44926315233)**：**188/188 单元/契约 + 128/128 真实 E2E 全部通过**，Job completed/success，完整原始 Artifact 生成。不能将前两次失败当作最终通过证据。

## 四、B14 对 G1 的实际意义与尚未解决事项

**正向且经真实测试验证**：

1. 在本研究的 Kernel UID 私钥未泄露、固定公钥未被替换、受控 Native Broker 未被绕过的条件下，Consumer 无法自行伪造一条被 Native Apply 接受的 B2 事件；B13-104 的**受控 IPC 事件来源认证缺陷得到针对性修复**。
2. Router 的 Native SQL 物理快照不再依赖与 Saltcorn 同 UID 的 Broker；第五独立 UID 的读权限和 Socket 身份隔离已用真实 Linux `O_RDONLY/O_WRONLY`、`SO_PEERCRED`、Chromium、Native SQLite 证明。
3. 实际 B2 Form/Workflow → Trigger Outbox → Kernel Ed25519 → 无 sudo Consumer → Native 验签/事务 Apply → 独立 SQL 审计 → Router → 真正 Saltcorn Chromium 的完整链路已覆盖**八份真实合同、32条真实事件**；签名重放、伪造、SQL 污染与人工恢复均有正反证据。

**仍为 OPEN 的 P0/工程风险**：

- **Native 同 UID 直接写入**：Saltcorn 本身仍有派生 SQLite 写权限，Native Broker 的签名验真不能约束同 UID 直接 SQL。第五 UID 审计可对受保护入口的已验证异常返回503，但不能阻止污染。
- **Native HTTP 旁路**：原生 Saltcorn `/view/s1_contract_list` 直连在真实 Native SQL 污染时仍返回200，未验证生产网络层完全阻断直连。未实现全站 Gateway、SSO、TLS/mTLS、缓存与代理一致性。
- **生产密码学**：没有 HSM/KMS、密钥轮换/吊销、事件签名链持久审计、撤销后历史验证、可信时间、跨集群公钥分发/更换、Key ID 管理、长期证书管理。
- **数据一致性**：Router 每次 GET 全量扫描 B2 Outbox，最多1000条；单模型固定四列，双次读取仍有 TOCTOU；未验证多租户、敏感数据、删除、Schema Migration、生产吞吐、断电、跨节点故障或持久路由 Journal。
- **正式门禁**：冻结 W01—W24 和 TC01—TC18 未完成独立 FULL PASS 证据。专项测试通过不能自动升级正式门禁。

**正式冻结结论：S1 IN_PROGRESS / G1 NOT_PASSED / G1-B01 PARTIALLY VALIDATED / OPEN；W01—W24 0/24 FULL PASS、TC01—TC18 0/18 FULL PASS。**

**建议 B15 方向**：在保留 B14 可信签名/独立审计基础上，重点验证**Saltcorn 原生 HTTP 旁路的强制网络隔离**与**派生 SQLite 的不可写发布/可控快照替换**，并引入失败时拒绝服务、变更回滚与一致性负对照。优先保持最小必要验证，避免把研究原型直接宣称生产可用。
