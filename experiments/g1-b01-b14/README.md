# S1 B14：权威 Ed25519 事件签名与独立第五 UID 的真实物理 SQL 读前校验

> **受限安全研究原型，非生产 PKI/HA 方案。** 在 B13 已验证的 104 项真实 Saltcorn/B2/Chromium/四 UID 端到端测试上，新增 **Kernel UID 私有 Ed25519 签名**、Native Apply 边界 **公钥验签**、独立于 Saltcorn UID 的 **第五 Linux UID 只读物理 SQLite 审计者**、以及读取前后同时核验 B2 Release、完整签名 Outbox、真实 SQL 的受控 Router。

## 权威签名路径

- **B2 权威**：B11 真实 SQLite Trigger Outbox 与 Form/Workflow 同事务。新增 `signed_source.py` 仅由 Kernel UID 启动，读取原始权威事件，使用 Kernel UID 独占 `0600` 的 Ed25519 原始私钥，对 **domain-separated + canonical JSON + 原始 eventHash** 进行签名。签名格式为 `eventSig`（Base64 Ed25519）+ `keyId`（固定公钥指纹）。
- **Consumer UID**：只有独立 B2 Signed Source 的短期 Bearer 和只读数据；不能读取私钥、权威 SQLite、Native SQLite，也没有 sudo；将签名事件通过 `consumer.sock` 送往 Native Broker。
- **Saltcorn UID**：只持有固定公钥（只读 staged file），`signed_native_ipc.py` 在触发任何 B11 事务 Apply **之前** 验证每个事件的 Ed25519 签名、keyId、作用域、版本及完整内容；通过后剥离签名，继续执行已验证的 B11 SQLite CAS/Receipt/Idempotency 原子事务。原 B13 仅 SHA256 的伪造事件与“修改字段并重新计算 SHA256、复用旧签名”的攻击均必须拒绝。
- **真实签名边界**：Kernel UID 独占签名私钥；Consumer、Native、Router 都只有公钥。**Native UID 仍可绕过自身 Broker 直接改写派生 SQLite**，签名仅认证通过受控 IPC 进入的事件，不是对 Saltcorn UID 的防篡改承诺。

## 独立物理 SQL 审计路径

- 新建 **第五个真实 Linux 非 root UID `ailcapb14audit`**，不同于 Kernel、Saltcorn、Consumer、Router。
- Native SQLite 仍由 Saltcorn UID 拥有；研究环境中 CI Controller 将文件组设置为 `ailcapb14audit`、权限 **0640**，目录为 **0710**；审计 UID 实际通过 `O_RDONLY` 读取真实 SQLite 成功，`O_WRONLY` **PermissionError**。
- `audit_reader.py` 在审计 UID 下启动，创建它**自己拥有**的 Unix Socket，0660、`ailcapb14guard` 组，`SO_PEERCRED` 只允许 Router UID 连接，**只开放 snapshot，不开放 apply**。Saltcorn UID 不在审计组内，不能连接审计 Socket，也不能写审计代码/Socket 目录。
- `guard_router.py` 在真实 Router UID 下运行，针对唯一公共合同列表 `GET /view/s1_contract_list` 在真实 Saltcorn HTTP 请求前后，校验 B2 当前 Release、签名 Outbox、独立审计 UID 的真实 Native SQLite 行/Receipt/Cursor；不一致返回503。
- **仍有边界**：Saltcorn UID 仍拥有 Native SQLite 写权限，可以污染数据或撤销审计者的文件读取权限（守护入口应 fail-closed）；原生 Saltcorn HTTP 直连仍绕过受控入口；不能宣称全局线性一致性、无 TOCTOU、恶意 Kernel/root 防护、生产 mTLS/HA 或完整 PKI/密钥轮换。

## 真实验证范围

- B13 **104/104** 真实 E2E 原样回归，在同一个真实 B2/Native/Chromium/四 UID 研究夹具中运行。先**复现 B13-104 旧 Broker 接受伪造事件**这一不安全基线，再由受信 CI Controller 停止旧无签名 Broker，清空**一次性 Native 派生库**，从 B2 **28 条真实权威事件重新签名回放**，避免混入旧无签名回执。
- B14-105—128 **新增 24 项真实 E2E**：关闭旧无签名 IPC；真实 Native 清理；Kernel UID 私钥 0600；签名权威事件28条；Consumer 无法读取/写私钥；第五 UID 实际只能读不能写 Native SQLite；Native 新 Broker 公钥验签；旧伪造 SHA256 事件拒绝；改字段/重算 SHA/复用旧签名拒绝；28条签名事件事务回放与28条幂等重放；第五 UID 独立 SQL 审计；Native UID 无法连接审计 Socket；Router 只能调用审计 snapshot；真实受控 HTTP/Chromium；Consumer 自动签名同步第八份 B2 合同（4事件，Cursor28→32）；伪造 `seq33` 事件拒绝且 Native Cursor不变；Native UID 真实 SQL 污染导致**受控 Router503、Native 原生直连200**；人工修复后 Router200。
- B14 Ed25519 单测 **24 项**，B13 **22** + B12 **22** + B11 **28** + B10 **34** + B2 **18** + B5 **40**，总计 **188 项**单元/契约回归；B13 104 + B14 24 = **128 项真实 E2E**。全部 GitHub Actions 实际执行，不调用 DeepSeek。

## 未解决的正式门禁

1. Ed25519 签名密钥轮换、吊销、历史事件重签、签名时间戳、PKI/HSM/KMS、审计与防重放跨系统策略未实现；使用 Kernel UID 原始密钥文件仅为研究验证。
2. Saltcorn Native UID 可以绕过自身受信 Broker 直接改写派生 DB；独立审计可以检测已验证的 SQL 漂移，但不能阻止或保证恶意 UID 无法修改文件、制造 DoS。
3. 原生 Saltcorn HTTP 直连依然未被强制网络隔离，Router 仅验证固定单模型合同列表的只读 GET；不是生产网关。
4. 多租户行级 ACL、PII、删除/Schema Migration、跨主机 mTLS/HA、长连接/故障切换、W17/W24 正式门禁没有通过。

**正式判定始终**：S1 IN_PROGRESS / G1 NOT_PASSED / G1-B01 PARTIALLY VALIDATED / OPEN；冻结 W01—W24 0/24 FULL PASS，TC01—TC18 0/18 FULL PASS。**测试通过不等于正式 G1 门禁通过。**


## 最终真实验证与合并结果（2026-11-22）

- [完整报告 47](../../docs/01-research/47-s1-b14-ed25519-independent-sql-auditor-evidence.md)、[最终 Actions #44926315233](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44926315233) **completed/success**，Job **136913068933**，[Artifact #14716390392](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44926315233/artifacts/14716390392)：B14 **24/24**、B13 **22/22**、B12 **22/22**、B11 **28/28**、B10 **34/34**、B2 **18/18**、B5 **40/40** 单元/契约，共 **188/188**；真实 B11 62 + B12 17 + B13 25 + B14 24 = **128/128 E2E PASS**；**0 次 DeepSeek**。
- **真实 Ed25519 修复 B13 受控 IPC 事件伪造 P0**：旧 B13 Broker 先实际接受伪造事件；受信 CI Controller 关闭旧无签名 Broker、清空**一次性 Native 派生库**，Kernel UID999 独占0600 Ed25519 私钥签名28条 B2 原始 Outbox 事件，Native UID997 固定公钥验签后原子提交28条/幂等回放28条；旧 SHA256 伪造事件及篡改重算哈希、复用旧签名均被拒绝。无 sudo Consumer UID994 自动同步第八份 B2 合同4条签名事件，Cursor28→32；Consumer 伪造 seq33 事件被 Native 拒绝，Cursor32不变。
- **第五独立 UID 物理 SQL 审计**：审计 UID993 与 Native UID997 不同；实际 `O_RDONLY` 读取 Native SQLite 成功、`O_WRONLY` PermissionError；审计 Socket 0660、SO_PEERCRED 仅 Router UID995；Native UID 连接拒绝。真实 Saltcorn/Chromium 受控入口200；Native UID 直接 SQL 污染后**独立审计 clean=false、Guard503、Native 原生直连200**；人工修复后 Guard200。**不等于 Native UID 无法直接改写派生库，原生 HTTP 直连仍是旁路。**
- [PR #16](https://github.com/zealzhangz/OpenAILCAP/pull/16) 已合并 main，SHA **1dabeba18450adbd09196e6f21acb32cb7e080a2**。保留 [首次 CI #44925890843](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44925890843) Ubuntu User/Group 同名冲突，以及 [第二次 #44926049128](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44926049128) Guard 临时目录 B13 前缀误用导致进程拒绝；最终 [#44926315233](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44926315233) 全绿。
- **正式门禁不变**：S1 IN_PROGRESS / G1 NOT_PASSED / G1-B01 PARTIALLY VALIDATED / OPEN；冻结 W01—W24 **0/24 FULL PASS**，TC01—TC18 **0/18 FULL PASS**。下一步 B15：强制网络入口、派生 SQLite 只读快照/受控发布，保留 Native 直连与直接 SQL 负对照。
