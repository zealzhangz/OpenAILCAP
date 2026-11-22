# G1 P0-B：同实例 B2 权威发布 → B14 签名 → B15 原子快照 → B17 只读浏览器（预注册）

> **判定口径**：本工作属于 G1-B01 P0-B 的纵向贯通，不新开研究分支方向，也不调整冻结用例。仅可在相同 CI 实例中复现真实签名、文件替换、浏览器版本变化之后记录局部成功；**G1 仍 NOT_PASSED，W01—24 0/24、TC01—18 0/18 FULL PASS**。

## 一、验证拓扑与边界

从 PR #24 的 **同一个** B9 B2 `authority.sqlite`、单一 Domain Kernel、真实 Chromium 人工操作、Agent、B5、Docker 插件、原生 Saltcorn v1、Pack 受权 v3 staging 与 B2 v3→v1 rollback 继续运行：

1. **B14 Ed25519 签名源**：`p0b_signed_release.py` 只在专用 Kernel Linux UID 下读取 0700 的实际 B2 SQLite 当前发布指针，调用 B2 `SchemaStore.release`、严格 `compile_release` 验证模型/视图/引用闭包；只签 `app/version/draftRevision/manifestHash/projectionPackHash/viewColumns`。使用独立 domain separation，复用 B14 的 `make_keypair/key_id`；Kernel 私钥 0600，Publisher/Reader/Native/Plugin 只有固定公钥、无签名权，不允许客户端提供任意版本内容签名。
2. **B15 原子 Publisher**：额外非 root UID `ailcapb9pub` 对签名和当前 `release.read`/Manifest/编译结果双重比对，核验由真实 Native UID 独立物理 SQL 读回的 staging View/合同样例。把**公开四个业务字段及已验证签名源**放入**同一个**单次使用的 SQLite 快照，在 2750 Publisher 专属目录里以 `fsync + os.replace + directory fsync` 原子更换。构建失败、无效签名、当前发布指针改变或物理 Native View 不符，不得替换线上快照。
3. **B17 只读 Renderer**：又一个非 root UID `ailcapb9ro`，只有 Publisher 快照的 group read 与专用 B2 release.read 凭证；按 B17 方式用单 FD、`O_NOFOLLOW`、文件/目录归属和大小约束、只读内存 SQLite、确切 schema、行 digest 和 Ed25519 签名校验。**每次** HTTP 读取前后检查最新 B2 发布指针；未更新快照时返回 HTTP 503，不将旧版伪称当前版。只暴露 `GET /view/s1_contract_list`，拒绝所有写入；强制 no-store、HTML escape、禁 script CSP。
4. **真实浏览器不重启**：在**同一个只读 HTTP URL、相同 Chromium 浏览器与同一个服务进程**，观察 v1 三列 → B2 v3 指针升级且快照未更新时 503 → Publisher 原子替换后 v3 四列 → B2 rollback v1 前沿 503 → 签名 v1 重新发布后恢复三列。操作过程保留原 Saltcorn Native v1 已启动实例，**不**修改其派生 DB。

## 二、P0B-01—09 预注册结果

| ID | 必须真实执行的场景 | 独立 Oracle / 停止条件 | 对应冻结（仅 partial） |
|---|---|---|---|
| P0B-01 | Kernel UID 从实时 B2 SQLite 生成 B14 Ed25519 v1 签名，Native/Plugin/Publisher/Reader UID 尝试读取私钥 | 4 UID 全部 DAC DENIED、公钥独立验证成功、source v1 与当前列一致 | W14/W16 |
| P0B-02 | Publisher 独立 UID 原子发布 B15 兼容只读 SQLite，Reader UID 相同 URL 真 Chromium 读取 v1 三列 | 发布进程退出 0、Router UID != Publisher UID、HTTP 200 / X-Release 1、DOM 合同与三个表头 | W17 |
| P0B-03 | 已登录 Chromium 把同一 Kernel 人工发布源推进 v3，Publisher 尚为 v1 | B2 真版本 3，Router HTTP 503、v1 原始快照字节 hash 无变化、原 ReadOnly 进程仍在 | W17/W18 |
| P0B-04 | 恶意修改 B14 签名与伪造 Native SQL 列配置 | 两种发布均非 0 并提供拒绝码，已验证 v1 快照 hash 未变 | W18/W23 |
| P0B-05 | 在正确签名的 v3 写 staging 后模拟构建失败 | 明确拒绝、`os.replace` 未执行、已验证旧快照 hash 不变、当前版本未就绪只读 503 | W19 |
| P0B-06 | B15 真正原子切换已签 v3 单文件，Chrome 原页面 reload | 真实 HTTP 200/X-Release 3、四列表头+合同、无 Router/浏览器/Native 进程重启 | W17/TC16 |
| P0B-07 | 对新 ReadOnly URL 发 POST/PUT/PATCH/DELETE | 全部 405，快照字节和权威写账本不变 | W14/W16 |
| P0B-08 | 之前真实 B2 审批发布指针 v3→v1，Publisher 还保留 v3 | HTTP 503，旧 v3 不被伪称当前版本，v3 快照字节未被损坏 | W18/W24 |
| P0B-09 | Kernel UID 重新签当前 v1，Publisher 原子切换，Chrome 同网址 reload | 真实 HTTP 200/X-Release 1、三列和合同、同一个 Router 进程/URL、其他 app 完全不变 | W17/W24/TC16 |

## 三、明确未覆盖与正式验收

**本轮不改变 B2 与 Publisher 的跨数据库原子性**：B2 发布指针变动与快照切换之间存在明确的 503 拒绝服务窗口；故障会物理保留前一个 verified 快照，但在 B2 已变更时不会错误服务旧页面。这是安全性优先、尚需 G1 审视的限制，不得宣称完整生产零停机 SLA。

**本轮只投影 B9 模型/视图和一个真实 Saltcorn seed 合同**。Native Business Rows 没有得到 B2 权威业务数据事件的逐行签名；真实 Native/Publisher 隔离仍信任 CI Controller 传递的独立 Native SQL oracle。未覆盖 Form/Workflow/B4 代码、发布事件 B14 原有 B11 业务 outbox、跨资源依赖闭包所有类型、外部副作用 UNKNOWN/补偿、生产 HA、多租户、同 UID/root 旁路与插件生产安装/撤销。不得以局部通过判定冻结 W17/W18/W24 FULL PASS，更不得自动进入 G2。

本次预期增加 **9 项局部集成检查**，合计 **77 项**，DeepSeek **0 次**。只有对应 GitHub Actions 新 SHA 的原始日志和证据全部为绿色，才在本报告追加实测结果，并将关联冻结账本的 `partial_evidence` 更新；冻结状态不变。