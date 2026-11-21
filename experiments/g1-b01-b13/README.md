# S1 B13：四真实 Linux UID、受限 AF_UNIX IPC、B2/Native 读前双重核验

> **研究专项，非生产安全方案。** 在 B12 已验证的 B2 权威 Outbox、Saltcorn Native SQL/HTTP、Chromium 和后台自动恢复基础上，新增真正独立的 Consumer Linux UID，不再让 Consumer 本身具有 sudo 能力；使用两个分离 Unix Domain Socket 通过 Linux DAC 组授权及 `SO_PEERCRED` 验证对端 UID；新增独立 Router UID 的**守护式只读 HTTP 入口**，每次读取前后都比对 B2 当前 Release、权威 Outbox 全量业务事件、Native 物理 SQL 的行/回执/游标。**未关闭 Saltcorn 原生 HTTP 旁路**，未防范 Saltcorn UID 整体失陷。

## 真实运行边界

```text
B2 Kernel UID (authority.sqlite + Trigger Outbox)
      |   scoped projection token (never given to Saltcorn)
      +-------------------------+
      |                         |
Consumer UID                  Router UID
(no sudo / no DB)             (read-only public guarded GET)
      | consumer.sock 0660       | guard.sock 0660
      | group=ailcapb13pipe      | group=ailcapb13guard
      | SO_PEERCRED=consumer UID | SO_PEERCRED=router UID
      +------------+------------+
                   |
       Saltcorn UID native_ipc.py
       [consumer: audit/checkpoint/apply]
       [guard: snapshot ONLY, no apply]
                   |
          real derived Saltcorn SQLite
                   |
       real Saltcorn native HTTP (untrusted)
```

Router 在发送 HTML **之前**：

1. 使用独立 B2 Release Read Token 确认当前发布指针与 v1 Manifest SHA；
2. 使用只读 Projection Token 分页读取 B2 Outbox，逐条检查连续序号、限定四列、事件哈希，并重建最新合同业务行；
3. 经**只能调用 snapshot** 的 guard.sock 请求 Saltcorn UID 读取真实 Native SQLite，验证 record_map 行 SHA、Receipt 连续性、cursor=head、真实四列业务行与 B2 完全一致；
4. 再读取真正 Saltcorn HTTP 页面，之后**重复** 1—3 校验，并要求所有合同编号出现在 HTML 中；任一不匹配返回 HTTP503，绝不返回缓存的业务 HTML。

**关键保留问题**：Native IPC 服务与 Saltcorn 共享同一 UID，遭遇该 UID 完全失陷时可以伪造 snapshot 响应，不能宣称防御恶意 Saltcorn 进程。更严重的是 Consumer 可以经合法 apply IPC 发送任意**格式合法但来源伪造**的业务事件：B11 的 `eventHash` 是非认证哈希，不是 B2 权威数字签名。B13 最后专门通过 Consumer UID 注入有效伪造事件，验证 Native 真正接受，但独立 Router 通过 B2 source head/cursor 对照返回503。这是**真实 P0 负对照**，而不是通过验收的安全防护。原生 Saltcorn HTTP 直连仍绕过 Router。

## 预注册的真实验证

- B11 62 + B12 17 = **79 项完整真实回归**，使用新 B13 临时隔离目录及 B13 Kernel/Saltcorn/Router UID；
- **B13-80—104：新增 25 项真实集成验证**：四独立 UID；Consumer 无 sudo；无法读取 B2 Authority/Native SQLite/Router Token；Native UID 无法读取 Consumer/Router Token；两个组分离的 0660 Unix Socket + SO_PEERCRED；Consumer audit/checkpoint 允许但 guard socket 拒绝；Router guard snapshot 允许但 apply socket 拒绝；真实 Saltcorn HTTP 与 Chromium 在守护入口展示五份合同；Consumer 自动消费第六份合同；终止 Consumer 后第七份 B2 合同使守护入口503而原生 Native HTTP200；重启 Consumer 后自动追赶恢复守护入口200；Native SQL 污染导致守护入口503、原生直连仍200；人工恢复后守护入口200；最后**合法 Consumer UID 伪造源事件**被 Native 接受但守护入口拒绝。
- B13 IPC/Guard 单测 **22 项**，并保留 B12 22、B11 28、B10 34、B2 18、B5 40 回归。
- 不调用 DeepSeek。GitHub Actions 真实 Ubuntu24.04 + Node24 + Saltcorn CLI1.7.0-beta.5 + Python3.13 + Playwright1.56 Chromium。

## 尚未实现

- **源认证**：没有对 B2 Outbox 事件做可信签名或由 Kernel 直接认证应用命令；Consumer UID 可向 Native Broker 提交格式合法的伪造事件。
- **恶意 Native UID 防护**：Saltcorn 与 Native IPC 共享 UID，Snapshot 可被恶意服务欺骗。需要独立受信 SQL 校验/签名锚点/物理文件只读授权与受控数据面。
- **读取完整性**：只对单个 `GET /view/s1_contract_list` 的固定四列合同做两次校验；存在读取/提交间 TOCTOU、Native 直接访问、缓存与外部系统旁路；不证明全局线性一致性。
- **运维与租户**：没有跨主机 mTLS、签名密钥轮换、生产 HA、K8s Leader Election、Schema Migration、删除事件、租户行级 ACL/PII 保护、长期负载测试或 W17/W24 完整门禁。
- **正式状态**：S1 IN_PROGRESS / G1 NOT_PASSED / G1-B01 PARTIALLY VALIDATED / OPEN；冻结 W01—W24 **0/24 FULL PASS**，TC01—TC18 **0/18 FULL PASS**。专项全绿也不能升级冻结门禁。

下一步 B14：解决**Consumer 事件来源认证**与**Saltcorn UID 无法伪造读前校验结果**两项 P0，优先验证独立签名/验签与物理 SQL 受信读者，再考虑高可用和更多业务模型。
