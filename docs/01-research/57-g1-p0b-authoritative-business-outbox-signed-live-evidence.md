# G1 P0-B：真实 B2 业务数据 → B11 原子 Outbox → B14 Ed25519 → B15 原子发布 → B17 浏览器（同实例）

**2026-11-22 实测结果**：P0B-10—15 **6/6 PASS**，与既有 B9、P0-A、P0-B 同一权威实例叠加后 **83/83 PASS**；本文件只作 **partial_evidence**，G1 **NOT_PASSED**，冻结 W **0/24**、TC **0/18 FULL PASS**。

## 一、为什么本轮是 P0-B 剩余阻断，而非新分支

[上一轮 P0-B](56-g1-p0b-signed-atomic-readonly-live-evidence.md) 虽然证明 B14 签名 Model/View 发布与 B15 原子快照及 B17 同一浏览器热读取，但其一条业务数据来自 Saltcorn 本地 `seed-contract.js`，**没有真实 B2 表单创建与真实业务数据签名**。攻击者可以提供相同 Native View 列但虚构 `businessRows`。此外，B17 只检查 B2 **发布指针**，若合同内容在同一发布版本内变化，可能仍返回旧业务数据，属于 W17/W18 的实质阻断。

本轮只纠正这两条既知差距：**权威业务数据由 B2 真正产生，B14 签每一条 B11 event-time 记录，B15 必须校验行和当前出站 head，B17 每次请求还要检查 B2 当前业务 head/digest**；同版业务发生变动而 Native 尚未同步时应 fail-closed，而不是伪称已最新。

## 二、改动范围

全部在现有 `experiments/g1-b01-b9` 的同实例上下文完成，不新建其他权威实例。沿用真实官方 Saltcorn CLI、B2/B5、真实 Chromium 人工会话、Agent、Docker Plugin、B14 Ed25519、B15/B17 互不共用 OS UID。

1. `p0b_authority_business.py`：B9 Kernel 自己安装原 B11 的 `projection_source.install` SQLite `AFTER INSERT/UPDATE` 触发器。在与 `authority.sqlite` **相同数据库事务**中写 event-time outbox。只在 Kernel UID 内对 B2 实际 `records` 与所有连续 B11 事件进行**同一 SQLite 只读事务快照**核对（记录 ID、版本链、字段值、删除旁路、重复合同号），返回 head 与 rowsDigest；对事件序号、版本缺口或不符一律拒绝。
2. `kernel_service.py`：仅 B9 内部 `BusinessHeadKernelBroker` 拦截 `business.head`，**必须持有已有、仅 app-a 有效的 `release.read` 受限凭证**，不改全局 B5 Broker 工具权限列表。Agent/Plugin 无此权限，Native 不能读取 authority.sqlite；跨 app 不允许。
3. `p0b_signed_release.py`：由真实 Kernel UID 根据**实时 B2 权威库及原子 B11 outbox**生成同源的 `signedEvents`（使用原 B14 `sign_event`），并将 `outboxHead` 和 `rowsDigest` 纳入 Ed25519 发布签名的同一签名域。Publisher/Reader 只有公钥，任何角色无法提交任意数据要求 Kernel 签名。
4. `p0b_publisher.py`：在原已有当前发布指针、Pack/Native View 校验上，新增 **B11 全部签名事件连续性、每条事件 hash、每个 recordId 版本链、事件重建的最终业务行、B2 当前业务 head/digest、Native 真物理 Oracle 业务行内容**全量一致判断；故无法只靠正确的 View 列/Native 本地行伪造业务发布。前后两轮校验均成功后才 `fsync + os.replace`。
5. `p0b_readonly_web.py`：B17 每次真实 GET 前、后均调用 B2 当前 release 和受限 `business.head`，以 `outboxHead/rowsDigest` 与快照中 B14 Ed25519 可信源及 SQLite rows_digest 对照。**同一 Release 内新业务已写入而旧 Snapshot 尚未更换时 HTTP 503**，而不是返回过期数据。原 CSP、HTML escape、无写权限和同 FD 原子读取均保留。
6. 在 P0-A Pack v1→v3→v1 的**相同 Kernel/Browser/Native 实例**上运行真实 B2 CSRF 人工 `form.submit`，验证 B11 签名、Native 和公开浏览器；再添加第二条合同，验证失效、拒绝过期 Native、实际 Native CLI 派生数据补齐后 B15 替换与 B17 恢复。用真实 `p0b-seed-second-contract.js` 通过受控 Native UID CLI 补齐，**仍是手工受信 Controller 操作，不是 B11 自动 CDC 消费器**。

## 三、原始 CI 证据与判定

**完整成功构建**：[GitHub Actions #44979988516](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44979988516)，Job **137078178179**，[原始日志、业务/发布/SQL 证据 Artifact #14737442629](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44979988516/artifacts/14737442629)，代码 SHA **`2a092f44cde3a6e2cf46813402bcf0f7a31fd2d1`**。

| 检查 | 实际场景 | 原始可验证观察 |
|---|---|---|
| **P0B-10** | **同一个 B2 Kernel** 的已登录 Chrome 人工以真实 CSRF 发送 `form.contracts` 创建合同，B11 事务性 outbox 自动写入，Kernel UID B14 逐事件 Ed25519 签名。 | 真正人工 POST HTTP **200**、B2 物理 `records` 一条、B11 head **1**、事件签名已独立公钥验真，Native 物理 SQL 一条同字段的合同，B2 head/hash 一致。 |
| **P0B-11** | Native View 列与签名发布一致，但篡改 `title` 试图通过 Publisher 发布假业务行。 | **`PUBLISH_NATIVE_ROWS_NOT_B2_SIGNED`**，Publisher exit 2，旧 verified SQLite 文件 hash 保持不变。 |
| **P0B-12** | 提交看似合规但修改一条 B11 已签事件内容的候选。 | **`PUBLISH_B11_EVENT_SIGNATURE_INVALID`**，未替换快照，B2 记录不变。 |
| **P0B-13** | 真实 Chrome 在**同一 B2 已发布 v1**再次通过 CSRF 表单写入第二条合同。 | POST **200**、B11 head **1→2**、B2 发布指针仍 **1**、B17 浏览器 **503**（无过期合同展示）、旧快照字节 hash 未变化、原 Renderer 未重启。 |
| **P0B-14** | 第二次写入后，Native 仍只有第一条；虽然 Kernel 重新签出 B11 当前事件，但业务落后。 | 拒绝 `PUBLISH_NATIVE_ROWS_NOT_B2_SIGNED`，旧 SQLite 快照不覆盖，HTTP 503 fail-closed。 |
| **P0B-15** | 可信 Controller 通过**真实官方 Saltcorn CLI** 将第二条由 B2 已创建的业务行写入既有派生 Native，再按 B14/B15 重新签名/核验并切换。 | 实际 B2 **2** 条、B11 **2** 条完整签名事件、Native 物理 SQL **2** 条、B17 同一浏览器 **HTTP 200 / 2** 行，发布版本仍 **v1**、路由和浏览器无需重启，app-b 不变。 |

**全链回归**：**83/83 同实例集成检查 PASS**；原有 Pack 编译/审批 **39** + 新 `test_p0b_business` **10** = **49/49** 单元测试；B2 **18/18**，B5 **40/40**，B6 真实 Docker Relay **25/25**；**模型调用 0**。保留此前失败构建与修复历史，不将中间失败视为成功。

## 四、正式 G1 剩余风险（未通过的不能写成 PASS）

- **B2 当前发布指针和 B15 文件替换不是一个原子跨数据库事务**：期间返回 503 的安全性路径是真实可测，但尚不能宣称生产零停机发布。W17/W18/W24 **仍 NOT_RUN**。
- 本次 B11 自动 Outbox 是真实事务性事件，**Native 派生行同步仍由可信 CI Controller 手动运行官方 Saltcorn CLI**；尚无完整自动 Consumer / durable receipts / gap 自动恢复 / 生产 OS 边界。B15 读取的 Native Oracle 仍由可信 Controller 传递，虽经过 B14 权威行逐字段约束，但需要验证消费者真实能力和动态对账。
- Model/View 以外的 **Form/Workflow/B4 Code 全依赖一致发布与真实业务运行、外部 timeout UNKNOWN / 原 changeId 对账及补偿**未闭环；当前新增数据只证明合同记录，不能冒充 TC01—TC18 的全部合同旅程。
- 生产用户身份/Pack 受权批准、Native owner UID 同权限绕过、强隔离/HA/PKI/key rotation 未覆盖。
- **G1 门禁冻结：NOT_PASSED，W 0/24、TC 0/18 FULL PASS，所有 42 项 `NOT_RUN` 不改变。**下一步继续 P0-B **真实消费者与发布指针一致性**，不扩展独立子项目，不消耗 DeepSeek。

