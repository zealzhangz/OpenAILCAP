# S1 研究报告 48：B15 双栈 Linux 主机强制受控入口与第六 UID 原子公开数据快照

**验证日期：2026-11-22（北京时间）。最终 [GitHub Actions #44928087963](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44928087963) completed/success，Job 136918499653，[原始 JSON 与全量日志 Artifact #14716058088](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44928087963/artifacts/14716058088)。B15 新增22项单元 + B14 24 + B13 22 + B12 22 + B11 28 + B10 34 + B2 18 + B5 40 = **210/210 单元/契约 PASS**；B11 62 + B12 17 + B13 25 + B14 24 + B15 20 = **148/148 真实 E2E PASS**；DeepSeek **0次**。**

> **研究原型，不是生产级全站隔离、只读 Saltcorn 或 G1 正式门禁通过。** B15 的正向证明范围：单台 Ubuntu24.04 测试机、固定 Saltcorn Native TCP端口3158、IPv4/IPv6 Netfilter 实际生效、一个合同列表 GET；第六 UID 拥有**只读供 Router 核验的最小公开数据快照**，**Saltcorn 自己的实时 SQLite 仍可被 Saltcorn UID 直接写入**。根用户、CAP_NET_ADMIN、其他主机/端口/容器网络及生产流量不在防护证明范围内。

## 一、B14 后遗留的两项 P0

[报告47：B14](47-s1-b14-ed25519-independent-sql-auditor-evidence.md) 已真实证明 B2 权威 Outbox 的 Kernel UID Ed25519 事件签名、Consumer 来源伪造拒绝，以及第五独立审计 UID 读取真实 Saltcorn SQLite 的读前校验。仍有两项需要解决的真实旁路：

1. **Native HTTP 直连**：Saltcorn UID 可以修改自己的派生 SQLite；B14 受控 Guard 识别 SQL 漂移返回503，但直接访问原生 Saltcorn `127.0.0.1:3158/view/s1_contract_list` 仍 HTTP200。
2. **没有独立受控发布的数据快照**：B14 Guard 只能从实时可写 Native SQLite 及 B2 权威源做逐次校验。需要将“公开可核验的已发布业务数据”与 Saltcorn UID 真实写权限分离，并在发布前后检查权威签名源与物理 Native 一致性。

B15 以最小必要方案完成**单主机双栈网络入口实验**和**第六 UID 的原子最小公开快照实验**，保留旧 B14 **128项真实 E2E 完整回归**。

## 二、真实 Linux 网络层强制入口

[network_policy.py](../../experiments/g1-b01-b15/network_policy.py) 由受信 CI Controller 以 root 调用，在测试机安装精确限定 Saltcorn Native TCP端口 **3158** 的4条 Netfilter 规则：

| 协议 | 链 | 实际限制 |
|---|---|---|
| IPv4 | OUTPUT | 发往 `127.0.0.1:3158` 的 TCP 连接，**仅 Router UID995** 可以建立；Runner、Saltcorn UID997、Consumer UID994 均被拒绝 |
| IPv4 | INPUT | 非 `lo` 入站 TCP 3158 拒绝 |
| IPv6 | OUTPUT | 发往 `::1:3158` 的 TCP 连接，**仅 Router UID995** 可以建立 |
| IPv6 | INPUT | 非 `lo` 入站 TCP 3158 拒绝 |

规则包含唯一注释 `OpenAILCAP-B15-NATIVE-ONLY-TRUSTED-ROUTER`，`-C` 精确检查、`-I` 安装、`-D` 反向移除。代码提供启用失败时回滚及 finally 清理，并在真实 E2E 最后显式移除4条规则，验证 Native 直连恢复。

**真实实测**：

- **B15-136**：`iptables/ip6tables` **4/4条规则实际安装**，Router UID995。
- **B15-137**：Runner 用户、Saltcorn UID997、Consumer UID994 **实际 TCP 连接 Native 端口被拒绝**。
- **B15-138**：Router UID995 真实 TCP连接 Native 端口成功，B15 Guard HTTP200。
- **B15-139**：**真正 Playwright Chromium** 直接访问 Native 端口被拒绝，但新浏览器页面访问 Guard HTTP200，合同正常显示。
- **B15-140**：B2 新事件使公开快照落后，受控 Guard503，同时 Native HTTP 直连仍被网络规则拒绝。
- **B15-148**：4条 Netfilter 规则全部移除后，Native 直连恢复 HTTP200，受控 Guard 仍 HTTP200。**规则移除是研究清理证据，不是推荐生产中放开 Native。**

**未证明**：容器/Kubernetes/CNI、跨主机、真实公网入口、IPv6 Native 监听时的独立远程攻击流量、Unix Socket/其他服务端口、root/CAP_NET_ADMIN 攻击者、重启后的防火墙持久化、多路由、多租户、全站授权/SSO/TLS/mTLS。不能将固定端口的单机 Netfilter 实验称为生产完整隔离。

## 三、第六独立 Publisher UID 与最小公开 SQLite 快照

新增真实非 root `ailcapb15pub` **UID992**，与 Kernel999、Saltcorn997、Router995、Consumer994、第五审计 UID993 均不同。

**实际 OS 权限**：Publisher UID 通过 B14 Native SQLite 的审计组只读打开 Native SQLite，`O_RDONLY` 成功、`O_WRONLY` PermissionError；不能读取 Kernel 权威 SQLite 或 Ed25519 私钥。它持有自己私有的签名源只读 Bearer/Kernel Release 只读 Token，但不持有权威写 Token 或 Native 写权限。

[publish_snapshot.py](../../experiments/g1-b01-b15/publish_snapshot.py) 发布过程：

1. 查询 B2 Kernel 当前 Release 指针，必须与固定目标 Version/Manifest Hash 一致。
2. 从 B14 Kernel Signed Source 拉取 B2 SQLite Trigger Outbox，逐条**验 Ed25519 签名**、事件哈希、连续序号、模型和业务字段，构造权威最新合同数据。
3. **直接只读真实 Native SQLite**，核验 `b11_projection_cursor`、Receipt、RecordMap、每份合同字段/行哈希与 B2 权威事件**完全一致**。
4. 在 Publisher 自有私有目录内创建全新 SQLite，**只创建 `published_contracts` 与 `published_state` 两张表**。前者只含 `contract_no,title,amount_minor,status` 四列；后者只含事件 Head、公开行 Digest、Manifest Hash。**绝不复制 Saltcorn 账号、会话、插件、原生元数据表**。
5. 完成 SQLite 事务、再次校验 B2签名源/Native物理SQL一致、重新打开暂存快照只读核验、fsync文件、`os.replace` **单文件原子替换** `published.sqlite`、fsync目录；校验不通过不替换已发布快照。

**真实 DAC**：`published-private` 目录归 Publisher UID992、`ailcapb15snap` 组、权限 **0750**；`published.sqlite` 文件归 Publisher UID992、权限 **0640**。Router UID995 属于快照读取组，只能读不能写；Saltcorn UID997 不属于该组，**不能读取或写入发布快照**；Publisher 私有配置和签名源凭据同样不能被 Saltcorn UID 读取。此机制保护的是**独立公开快照**，不是 Saltcorn 实时 SQLite。

[guard_router.py](../../experiments/g1-b01-b15/guard_router.py) 在唯一合同列表 GET 前后，核验三方：**B2 Ed25519 权威事件 + 第五 UID 真实物理 Native SQLite + 第六 UID 原子公开快照**，同时核验 B2 Release。若任一方数据、Cursor、行哈希、发布版本不一致，返回503，不回退为直接 Native HTTP。只有全部一致，才向真实 Saltcorn HTTP 取 HTML 并做限定范围的内容核验。

**真实业务与故障对照**：

- **B15-129—135**：第六 UID 权限隔离、签名源与 Native SQL 双次核验、Head32/八份真实合同的原子快照发布、仅两张公开表、Native 无法读取、Router 只能读取、真正 Chromium 通过 Guard200。
- **B15-140**：B2 真实创建第九份合同并通过工作流审批，签名源 Head32→36、Consumer 自动同步 Native Cursor32→36；Publisher 尚未发布，公开快照仍Head32，**B15 Guard503**，但 B14（无发布快照约束）Guard200。证明“未发布的最新数据不能经 B15 入口直接读取”。
- **B15-141/142**：Publisher 显式重验权威签名源/真实 Native SQL，原子发布 Head36/九份合同，**B15 Guard200**，真正 Chromium 可见第九份合同。
- **B15-143**：Saltcorn UID **真实直接 UPDATE Native SQLite** 污染第九份合同标题，Publisher 自有公开快照的 SHA256 **保持不变**，B15 Guard503，Native HTTP 直连仍被 Netfilter 阻断。
- **B15-144**：Publisher 再次尝试发布污染的 Native，因权威 B2 与 Native 真实 SQL 不一致而**拒绝发布**，最后一个正确快照不变。
- **B15-145**：受信 CI Controller 指挥 Saltcorn UID **人工修复** Native SQL，B15 Guard200，发布快照无需改变。
- **B15-146/147**：受信 Controller 指挥 Publisher UID 暂时移走已发布文件，B15 Guard503、Native 直连仍被阻断；再次从 B2签名源/Native 真实 SQL 重建并原子发布后 Guard200。

**关键边界**：Publisher 是受信 CI Controller **显式调用的一次性研究进程**，未实现自动触发/持续重发布、分布式发布 Journal、长时间并发读、快照 TTL/回收、密钥轮换、故障自动恢复或生产多主/HA。**Saltcorn 原生 SQLite 仍可写，原生 HTML 仍由 Saltcorn 生成**；发布快照用于受控 Router 核验，**不是将 Saltcorn 改造成直接读取不可写快照**。

## 四、可复核的代码、CI、失败记录

| 交付项 | 证据 |
|---|---|
| B15 工程设计与边界 | [experiments/g1-b01-b15/README.md](../../experiments/g1-b01-b15/README.md) |
| 第六 UID 签名源/Native 校验 + 最小公开 SQLite 原子发布 | [publish_snapshot.py](../../experiments/g1-b01-b15/publish_snapshot.py) |
| B2签名源 + 第五 UID物理SQL + 第六 UID快照读前后核验 | [guard_router.py](../../experiments/g1-b01-b15/guard_router.py) |
| IPv4/IPv6 Linux Netfilter 强制入口与清理 | [network_policy.py](../../experiments/g1-b01-b15/network_policy.py) |
| 148项真实 Linux UID/Saltcorn/Chromium E2E | [experiment.py](../../experiments/g1-b01-b15/experiment.py) |
| B15 22项公开快照/原子性/权限/Netfilter 单元测试 | [test_published_network.py](../../experiments/g1-b01-b15/test_published_network.py) |
| GitHub Actions Ubuntu24.04/Node24/Saltcorn CLI1.7.0-beta.5/Python3.13/Playwright/cryptography/六 UID/iptables/ip6tables | [s1-b15-host-firewall-published-snapshot.yml](../../.github/workflows/s1-b15-host-firewall-published-snapshot.yml) |
| **PR #17 已合并** | [PR #17](https://github.com/zealzhangz/OpenAILCAP/pull/17) |
| **main 合并 SHA** | [601e1bd201e673b82156d8aa59f6eca26619c783](https://github.com/zealzhangz/OpenAILCAP/commit/601e1bd201e673b82156d8aa59f6eca26619c783) |
| **最终成功 CI** | [Actions #44928087963](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44928087963)，Job **136918499653** |
| **真实 JSON 与全部日志 Artifact** | [Artifact #14716058088](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44928087963/artifacts/14716058088) |

**最终计数**：

| 项目 | PASS |
|---|---:|
| B15 原子快照/Netfilter 单元 | **22/22** |
| B14 Ed25519 单元 | **24/24** |
| B13 四 UID/Guard 单元 | **22/22** |
| B12 Consumer 单元 | **22/22** |
| B11 Outbox/事务单元 | **28/28** |
| B10 Router 单元 | **34/34** |
| B2 Kernel 单元 | **18/18** |
| B5 IR/Broker 单元 | **40/40** |
| **单元/契约合计** | **210/210** |
| **真实 B11 62+B12 17+B13 25+B14 24+B15 20** | **148/148** |
| **DeepSeek 模型调用** | **0** |

**失败与修复保留**：

1. [第一次 CI #44927546949](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44927546949)：**210项单元/契约通过，B14 128项 + B15-129/130 共130项真实 E2E通过**；Publisher 用户以 `ailcapb15snap` 为主组，不存在同名 `ailcapb15pub` 组，测试夹具 `chown pub_user:pub_user` 失败。修正为真实主组 `ailcapb15snap`。
2. [第二次 CI #44927817940](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44927817940)：**210项单元/契约通过，138项真实 E2E通过**；实际 Netfilter 拒绝 Chromium 原生 Native 导航后，旧 Chromium Page 的 `chrome-error://chromewebdata/` 导航与随后的 Guard 导航发生竞争。修正为拒绝后关闭旧 Page、**创建新 Page** 验证 Guard。
3. **[最终 CI #44928087963](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44928087963)**：**210/210单元/契约 + 148/148真实 E2E** 全部 PASS，Job completed/success，原始 Artifact #14716058088 已生成。前两次失败不能当作成功证据。

## 五、阶段结论与剩余工作

**本轮针对性证据支持**：

- 在受信 root 安装的单机 Netfilter 规则生效期间，Runner、Saltcorn UID、Consumer UID、真正 Chromium **无法直接访问固定 Native HTTP端口**；独立 Router UID仍能访问并向浏览器提供通过签名源、物理 SQL 与发布快照核验的页面。
- 独立第六 UID 能以真实 OS DAC 权限只读 Native SQLite，逐条验证 B2 Kernel Ed25519 事件并与 Native SQL 比对，生成仅含四列公开业务数据的**原子发布快照**；Saltcorn UID 无法读取或写入该快照。
- 真实 B2 新合同、Native 自动同步、发布滞后、发布恢复、Native 直接 SQL 篡改、发布拒绝、人工修复、快照丢失、重发和防火墙规则移除均已真实验证。

**仍为 OPEN 的关键事项**：

1. Saltcorn UID **仍能直接写自己的实时派生 SQLite**；B15 仅将**发布快照**的写权限隔离，不能宣称 Native Web 的数据库本身只读。要真正收敛写权限，后续需分离 Native Web 运行 UID 与派生数据 Apply UID，验证 Saltcorn 启动/运行是否必须写 SQLite 元数据/Session，并考虑专用只读数据文件、服务边界与受控发布。
2. 单机 Netfilter 不是生产 Kubernetes/多主机网络强制入口；Native 仍可能存在其他端口、IPv6/网络命名空间、Unix Socket、直连路由、代理和 root/CAP_NET_ADMIN 旁路。仅对本次实际验证的固定端口/UID/主机路径作结论。
3. Publisher 尚未自动化，发布延迟会使受控 Router **fail-closed 503**；没有生产级后台发布服务、重试/幂等 Journal、灰度发布、发布恢复 SLA、快照留存/删除与并发压测。
4. 固定单模型、四列合同列表；B14/B15 Guard 全量源 Outbox 最多1000事件且逐次校验，未验证全站业务路由、多租户 ACL/PII、删除/Schema Migration、恶意 HTML/插件、TOCTOU/高并发、跨主机 TLS/mTLS/HA、长期签名密钥运维。
5. 冻结 W01—W24、TC01—TC18 尚无正式 FULL PASS 验收证据，不能以专项研究 E2E 自动升级 G1。

**正式冻结结论保持：S1 IN_PROGRESS / G1 NOT_PASSED / G1-B01 PARTIALLY VALIDATED / OPEN；W01—W24 0/24 FULL PASS，TC01—TC18 0/18 FULL PASS。**

**建议 B16**：以 B15 真实单机网络入口/原子快照为基线，优先验证**Native Web 与 Native Apply 分离真实 OS UID**、Native SQLite 权限与启动写需求的正反实验；再决定是否能够真正将 Web 的业务数据访问限定到只读快照，同时保持受信 Kernel 唯一业务权威。
