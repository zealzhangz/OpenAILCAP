# S1 B15：真实 Linux IPv4/IPv6 受控入口 + 第六 UID 原子发布的最小公开 SQLite 快照

> **受限安全研究原型。** 在 B14 的 **128 项真实 E2E** 基础上，新增 Linux 主机级双栈 `iptables/ip6tables` Native TCP 访问隔离与独立 **第六非 root UID** 的只读校验、最小数据快照原子发布。目标是证明**受控入口**在已验证网络路径下不可被普通用户直接绕过，以及可信发布者可以生成 Saltcorn UID 无法写入的业务数据快照。**不等于 Saltcorn 的原生数据库变成只读，不等于生产跨主机网络隔离或完整网站网关。**

## B15 核心技术方案

### 1. Linux 主机强制 Native HTTP 访问入口

- 原生 Saltcorn Web 服务保持 `127.0.0.1:3158` 测试入口，可信 Router 以独立 UID `ailcapb13route` 运行。
- [network_policy.py](network_policy.py) 由 CI 受信 Controller 以 root 安装精确匹配的 **IPv4+IPv6 共4条** Netfilter 规则：
  1. `iptables OUTPUT`：发往 `127.0.0.1:3158` 的本地 TCP 连接，仅 Router UID 可以发起，其余 UID 拒绝。
  2. `iptables INPUT`：来自非 `lo` 的 TCP 3158 入站拒绝。
  3. `ip6tables OUTPUT`：发往 `::1:3158` 的本地 TCP 连接，仅 Router UID 可以发起，其余 UID 拒绝。
  4. `ip6tables INPUT`：来自非 `lo` 的 TCP 3158 入站拒绝。
- 真正 Linux UID/Chromium 网络连接验证：Runner、Saltcorn UID、Consumer UID 直接连接 Native HTTP 被拒绝；Router UID 可以连接；真正 Chromium 经受控 Router 可显示合同。规则以 `OpenAILCAP-B15-NATIVE-ONLY-TRUSTED-ROUTER` 精确匹配、支持重复启停，finally 尽力清理，最终显式删除全部4条规则后 Native HTTP 直连恢复。
- **限制**：仅验证单台 Ubuntu24.04 测试主机、一个固定 Native TCP 端口、Linux root 可控制的 Netfilter；未验证跨主机、容器网络、Kubernetes CNI、其他端口/路径、Unix Socket、VPN/代理、其他协议、持久重启规则、root/CAP_NET_ADMIN 攻击者。不是生产防火墙模板。

### 2. 第六独立 UID 的可信最小公开 SQLite 快照

- 新建非 root `ailcapb15pub`（与 Kernel、Saltcorn、Router、Consumer、审计 UID 全部不同）；它**只能读** Native 真实 SQLite（继承 B14 审计文件组读取能力），**不能写** Native SQLite，也不能读 Kernel 权威数据库或 Kernel Ed25519 私钥。
- [publish_snapshot.py](publish_snapshot.py) 的**发布前后两次**检查：
  - B2 当前 Release 指针与目标 Manifest Hash 一致；
  - B14 Kernel Ed25519 **每一条**签名 Outbox 事件的合法性、来源、连续序号与原始哈希；
  - 独立只读物理 Native SQLite 的 Cursor、Receipt、RecordMap、合同字段、行哈希与 B2 权威事件一致；
  - 在上述条件均满足时，**只复制公开的四个合同字段**到新 SQLite，外加 `head`、公开行 Digest 和 Release Hash。**绝不复制 Saltcorn 原生 SQLite 的账户、Session、插件或其他表**。
- 快照目录 `published-private` 为 Publisher UID 拥有，`0750`、`ailcapb15snap` 组；快照文件为 Publisher UID 拥有，`0640`。Router 仅有只读权限，Saltcorn UID 不在该组内、不能读/写快照或 Publisher 私有签名源凭据。快照写入私有临时 SQLite，事务提交、校验、fsync 后 `os.replace` **原子替换** `published.sqlite`；目录 fsync。
- [guard_router.py](guard_router.py) 对唯一合同列表 GET 在真实 Saltcorn HTTP 前后**同时核验** B2 签名源、第五 UID 独立物理 Native SQL、**第六 UID 公开快照**三者一致。源或 Native 进度超过快照、快照缺失/异常、真实 Native SQL 漂移等返回503，**不退化为直接 Native HTTP**。
- 新 B2 合同到达、Consumer 已同步 Native 但 Publisher 尚未更新快照时，Guard503；由受信 CI Controller 显式运行 Publisher 原子发布后 Guard200；Native 直接 SQL 污染不改变 Publisher 拥有的快照、Guard503，Publisher 拒绝将污染内容发布；人工修复后 Guard200。
- **限制**：Publisher 是**由受信 CI Controller 显式调用的研究进程**，不是生产后台自动发布服务。Saltcorn 仍能直接写**自己的实时派生 SQLite**，本轮仅证明它不能写 Publisher UID 拥有的**最小公开快照**。Native HTTP 内容仍由 Saltcorn 生成，Guard 对唯一四列列表做受限校验，不能声称消除所有 TOCTOU、HTML 注入或完整 Web 安全风险。

## 真实 CI 范围与门禁

- B14 原有真实 **128 项 E2E** 完整回归；新增 **B15-129—148 共20项**真实端到端：六 UID、Publisher OS 读写权限、签名事件与 Native SQL 双次核验、最小公开快照、文件权限、真正 Chromium、IPv4/IPv6 Netfilter 4规则、直接 HTTP 负对照、Router 唯一准入、真实 B2 第九份合同/四事件引起的快照滞后503、原子发布恢复200、Native 直接 SQL 污染拒绝与 Publisher fail-closed、人工修复、快照缺失503与重发、规则完整清理及 Native HTTP 恢复。
- 新增 [22项 B15 单元/契约测试](test_published_network.py)，回归 B14 24、B13 22、B12 22、B11 28、B10 34、B2 18、B5 40，总计 **210项**单元/契约；**148项真实 E2E**。所有计数以最终 GitHub Actions 实测为准，**不调用 DeepSeek**。
- CI：[s1-b15-host-firewall-published-snapshot.yml](../../.github/workflows/s1-b15-host-firewall-published-snapshot.yml)，Ubuntu24.04、Node24、Saltcorn CLI1.7.0-beta.5、Python3.13、cryptography、Playwright Chromium、六真实 Linux 非 root UID、Linux Netfilter。
- **正式冻结门禁仍然**：S1 IN_PROGRESS / G1 NOT_PASSED / G1-B01 PARTIALLY VALIDATED / OPEN；W01—W24 **0/24 FULL PASS**，TC01—TC18 **0/18 FULL PASS**。专项研究测试不能替代正式门禁验收。


## 最终真实验证与 GitHub 合并（2026-11-22）

- [完整报告48](../../docs/01-research/48-s1-b15-host-firewall-atomic-public-snapshot-evidence.md)、[最终 GitHub Actions #44928087963](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44928087963) **completed/success**，Job **136918499653**，[Artifact #14716058088](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44928087963/artifacts/14716058088)：B15 **22/22** + B14 **24/24** + B13 **22/22** + B12 **22/22** + B11 **28/28** + B10 **34/34** + B2 **18/18** + B5 **40/40** = **210/210 单元/契约**；真实 B11 62+B12 17+B13 25+B14 24+B15 20 = **148/148 E2E**；**0次 DeepSeek**。
- **Netfilter真实证据**：IPv4/IPv6 INPUT/OUTPUT **4条** Linux规则真实安装；Runner、Saltcorn UID、Consumer UID和真正 Chromium直接访问Native TCP3158 **被拒绝**，Router UID995 TCP连接成功、Guard HTTP200；规则完整删除后 Native HTTP直连恢复200。**仅验证单机固定端口，不代表生产跨主机/Kubernetes网络隔离。**
- **第六 UID 真实权限**：Publisher UID992与Kernel999、Saltcorn997、Router995、Consumer994、审计UID993均不同；Native SQLite实际只读可访问、写被PermissionError拒绝；B2权威DB/Kernel Ed25519私钥不可读；发布前后验证B2签名源与Native真实SQL；仅公开四列合同数据+Head/Digest/ManifestHash两张表，Publisher-owned **0750目录/0640快照**，Saltcorn不能读/写、Router只读；fsync+`os.replace`原子发布。
- **真实第九份合同与负对照**：B2签名源Head32→36、Consumer自动同步Native36、发布快照仍32，Guard503；显式发布36后Guard200/Chromium显示新合同；Saltcorn UID直接SQL篡改使Guard503，但快照SHA256不变、Publisher拒绝污染发布；人工修复Guard200；快照丢失Guard503、重发恢复200。**Saltcorn实时派生SQLite仍可被Saltcorn UID直接写**；Publisher是受信CI Controller显式调用，不是生产自动发布。
- [PR #17](https://github.com/zealzhangz/OpenAILCAP/pull/17) 已合并main，SHA **601e1bd201e673b82156d8aa59f6eca26619c783**。保留 [首次 CI #44927546949](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44927546949) Publisher主组配置错误（210单测+130 E2E已通过）和 [第二次 CI #44927817940](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44927817940) Chromium拒绝Native后的错误页异步导航竞争（210单测+138 E2E已通过），最终 [#44928087963](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44928087963) 全绿。
- **正式门禁不变**：S1 IN_PROGRESS / G1 NOT_PASSED / G1-B01 PARTIALLY VALIDATED / OPEN；W01—W24 **0/24 FULL PASS**，TC01—TC18 **0/18 FULL PASS**。下一步 B16 优先真实 Native Web 与 Apply UID 分离、SQLite只读业务数据可行性。
