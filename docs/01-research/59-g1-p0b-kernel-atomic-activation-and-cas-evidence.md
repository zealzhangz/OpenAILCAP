# G1 P0-B：B2 内核原子激活指针、内容寻址预发布与并发/故障回滚（P0B-24—33）

**2026-11-22 同实例实测**：[GitHub Actions #44983773857](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44983773857) **completed/success**；代码 SHA **`2e0fb3eb2b4866e310dbe79bf588f9923d119b86`**，Job **137089766978**；[包含原始全链日志与 JSON 验收证据的 Artifact #14738418046](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44983773857/artifacts/14738418046)。

**101/101 B9 同实例局部集成检查 PASS**，附 B9 **49/49**、B11 **28/28**、B12 **22/22**、B13 **22/22**、B14 **24/24**、B2 **18/18**、B5 **40/40**、B6 真 Docker **25/25** 回归。模型调用 **0**。**G1 NOT_PASSED；冻结 W 0/24、TC 0/18 FULL PASS，42 个用例仍 `NOT_RUN`。**

## 一、本轮唯一目标和架构决策

接续 [报告 58](58-g1-p0b-signed-durable-consumer-recovery-evidence.md)。前一轮已经在**同一个 B2 `authority.sqlite`**上贯通真实 Chromium 人工 B2 表单 → B11 事务性 Outbox → B14 Ed25519 签名事件 → 第六个 Linux UID 的自动 Native 消费者（同事务 cursor/receipt/record-map）→ B15 独立 Publisher → B17 同 URL 浏览器，并覆盖 source 断连、重启和业务行追平。然而 B15 发布只是对单个 `published.sqlite` 用 `os.replace` 原子替换，没有在 B2 里保存**权威的运行态激活决策**；B2 Domain 发布指针、B11 head 和已验签的物理快照之间仍缺少**同一个可线性化的激活 CAS**。

本轮只补这个缺失，避免另起子项目。分清以下三个不同概念：

- **B2 Domain 当前发布指针**：原 `apps.current_release` 和不可变 `releases`，用于需求/资源的领域发布；不能因为有 Native 派生物就绕过。
- **B15 已准备（PREPARED）候选**：Publisher UID 校验实际 B2 最新 Release/Manifest/Pack、B11 逐条签名事件、当前 B2 rowsDigest 和真实 Native SQL 物理数据，生成 fsync 后不可变**内容寻址** SQLite `candidates/<sha256>.sqlite`。在 Kernel 明确授权之前，该候选只占据磁盘，**不会改变浏览器路由**。
- **B2 核心激活（ACTIVATED）指针**：原来同一个权威 `authority.sqlite` 里增加 `p0b_public_activations`、`p0b_activation_receipts` 两张**B9 局部表**；受限 `publication.activate` 要求模拟受信 Publisher 的 `app.publish` grant、合法 changeId、`expectedEpoch` CAS、期望版本及 B11 head。Kernel UID 自己读取 Publisher 只读组可见的准备候选，使用与 B17 完全相同的单 FD 解析、独立 B14 Ed25519 验签、全行 rowsDigest、物理 SHA-256 文件名校验，然后在**一个 SQLite `BEGIN IMMEDIATE` 事务里检查 `apps.current_release`、`releases` 以及 B11 outbox/records 的单快照一致性，CAS 写入 epoch/候选 SHA/真实业务 digest 与幂等回执**。

B17 Reader UID 只拿受限 `publication.read`：Kernel **单事务**返回领域当前发布/当前 B11 业务 head 与**已提交的 active SHA + epoch**。Reader 只按固定 Publisher 私有派生目录内的 SHA 文件名读取，独立核验快照完整签名及内容哈希；每个 GET 在渲染**前后各查询一次 Kernel 原子指针**，若 Domain 来源、B11 head 或激活 epoch 不一致，则 HTTP **503**，绝不提供过期 HTML。原激活前的读取行为保留 fail-closed 以兼容前序的真实 B9/P0-A/P0-B 同实例实验。**未声称**跨数据库/文件系统分布式事务、生产 HA 或零 503 停机时间。

内核对 Publisher candidates 目录只加入**只读组访问**，Consumer/Plugin/Native 无 Kernel 业务 DB 能力；即使 Publisher 本地 owner UID 擅自改写已激活候选，Reader 也会按 SHA 检出并 503。生产服务应把不可变产物移到更强的受控只读/对象存储权限域；本次仅限 Linux 单机。

## 二、10 项 P0B-24—33 同实例真实 Oracle

| 新编号 | 已执行真实输入 / 故障 | 物理 SQL、REST、Chromium 与文件判据 |
|---|---|---|
| **P0B-24** | B11 自动消费者已有**三条真正 B2 合同**；Publisher 在同一真实 Native 数据上单独执行 `--prepare`，fsync 内容寻址候选。 | `prepared=True`、`snapshotSha256=3be297…601d`，B2 SQL active NULL/epoch 0/receipt 空；既有 `published.sqlite` SHA 不变，浏览器仍 200；**未提前激活**。 |
| **P0B-25** | Reader token、无 token、跨应用 publisher token、缺失 SHA 文件、错误 expectedEpoch 分别尝试激活。 | 依次真实 HTTP **403/401/403/409/409**；Kernel 物理 active/receipts 零变化，浏览器 200。 |
| **P0B-26** | Publisher 准备阶段注入构建失败（尚未进入 Kernel）。 | `PUBLISH_BUILD_FAILURE_INJECTED`，无活跃指针改写、原文件 hash 不变、B17 200。 |
| **P0B-27** | 经合法受限高权 `publication.activate` 提交已验签/已 fsync 候选。 | 同一 B2 `BEGIN IMMEDIATE` 激活 CAS **epoch 0→1**、真实 SQL `p0b_public_activations` 和 receipt 1 条、当前 B2 Release v1/B11 head3 全匹配；**B17 同 Router/Chrome HTTP200、3 行、旧 legacy 文件完全未替换**。 |
| **P0B-28** | 原 `changeId` 原样重放、相同 ID 改变参数、另一个 ID 试图使用过时 epoch。 | 原样 200/`replayed=True`、其余均 409；B2 active/receipts/epoch 未变化，B17 继续 200。 |
| **P0B-29** | Publisher UID 在成功激活后真地**篡改已激活候选 SQLite 文件字节**，随后恢复原字节并 fsync。 | 篡改 B17 HTTP **503**；恢复后 **200/3 行**；B2 激活 epoch 仍 1、原 legacy 文件不变、Router/Chrome 均未重启。 |
| **P0B-30** | 已登录 B2 Chromium 在发布版本仍 v1 下真正提交第四条合同；B11 outbox 自动产生 seq4，B14 第六 UID 自动消费者追至 Native cursor4。 | B2 真 HTTP200/outbox head4、Native SQLite receipts4、原 B2 active epoch1 **未自动变化**；Reader 检测 active 的 head3≠Domain head4，返回 **503** 而不是伪最新合同；旧物理文件仍保留。 |
| **P0B-31** | 恶意/过时控制端尝试激活 head3 旧候选；随后 B15 重新生成 head4 内容寻址候选，**暂不激活**。 | 旧候选 **409 `ACTIVATION_B2_SOURCE_MOVED`**；新候选生成成功但 B2 active epoch 仍 1，B17 继续 **503**，无未经授权切换。 |
| **P0B-32** | Kernel UID 直接在真正 B2 `BEGIN IMMEDIATE` 激活事务内模拟**写入后、提交前异常**。 | `ACTIVATION_FAILURE_INJECTED`，物理查询 active epoch1 和 receipts 依旧不变；同 changeId 不被烧毁，Browser 仍 fail-closed 503。**这是可控异常注入，不冒称断电恢复**。 |
| **P0B-33** | 用两个真实并行 HTTP 请求、相同 `expectedEpoch=1`、不同 changeId，争抢已准备的 head4 候选。 | **恰好一个 HTTP200 ACTIVATED/epoch2、一个 HTTP409 CAS conflict**；B2 物理 receipts 只新增赢家；Reader 从 B2 已激活 SHA 加载已验签文件，原 B17 Chrome **HTTP200/4条真实合同**，Router 和旧 legacy 物理文件均不变、app-b 不变。 |

P0B-24—33 原始 `PASS`、每条真实 SQL/HTTP/DOM/文件 SHA 记录在 CI #44983773857 Job 137089766978 的完整日志和 Artifact #14738418046 中。此前 91 项保持同实例全绿；**本轮增加 10 项，总共 101/101**。未新增任何其他独立 Kernel、数据库或 Docker 研究服务。

## 三、实质推进及仍无法宣称的保证

**本轮补齐了一个原先缺失的“持久权威激活决策”**：先 prepare 一份物理已验证的不可变候选，后由 B2 Domain Kernel 在其**同一 SQLite DB 事务**下依照当前真实 Release 和 B11 head 原子推进唯一 active SHA/epoch 和 changeId receipt。Reader 不会因 Publisher 文件预先准备或随意替换而变更公开运行态；并发激活恰有一方获准、失败注入不会留下半个权威指针、原 changeId 可对账重放，候选坏字节直接 503。

**但 G1 仍不通过**，理由必须保留：

1. 原始 B2 `apps.current_release` 发布/回滚、B11 业务事务与 B15 文件 fsync 不构成一个跨阶段**单一原子提交**。内核的**激活指针**是原子 SQLite 写入，而 B2 领域发布指针可能先于候选准备变化；期间会 **503 fail-closed**，不是零停机发布。即使业务新纪录自动消费，B15 prepare/Kernel activate 仍由可信 Controller 受限触发，尚非健壮的自动审批/部署状态机。
2. 虽已用真实 Kernel 受控事务**提交前异常注入**、并行 CAS、活动文件篡改证明确定性行为，尚未验证真实宿主**断电 + fsync 持久性**、多进程/多节点主备、跨文件系统事务补偿或生产签名 PKI/轮换；单机 Publisher owner UID 仍能制造只读服务 503 DoS。
3. **Form/Workflow/B4 Code 全量版本一致部署和真实业务接口运行**仍未完成，不能把受控合同 CRUD/投影等同于 G1 完整应用。外部调用 timeout UNKNOWN、同 changeId 查证/副作用补偿、生产身份/审批、插件安装撤销与 Native owner UID 绕过仍未关闭。
4. README/冻结矩阵是门禁唯一来源：W01—W24 **0/24 FULL PASS**、TC01—TC18 **0/18 FULL PASS**，42 条依旧 **`NOT_RUN`**。本报告只进入对应案例 `partial_evidence`，不自动把某些 W/TC 标为 PASS。

**下一步仅继续同一 P0-B**：在上述原子激活基础上检验**自动部署协调器/发布决策与真正 Crash/UNKNOWN 对账**（尤其领域指针先变→旧活跃失效→修复/回滚时的服务语义），然后按同一真实 B2/B11/B14/B15/B17 链逐项补齐 Form/Workflow/B4 Code 依赖闭包、外部 side effects；只有正式完整冻结 Oracle 全绿后才可变更 G1 门禁。DeepSeek 继续按必要最小验证，不为计数调用。
