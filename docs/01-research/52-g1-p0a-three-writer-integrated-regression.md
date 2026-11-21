# G1 P0-A／首个同实例三写入者联合回归（预注册）

**状态：待 GitHub Actions 实际验收；不改变 G1 NOT_PASSED。**

本次不再把 B1、B7、B9 的独立成功数字相加，而是直接**扩展 B9 原有的单个临时 B2 权威实例**：同一次启动、同一个 authority.sqlite、同一个原生 Saltcorn 派生库与真实 Chromium 会话。原 B9 的 36 项检查顺序保留；在真实原生 Web/CLI/Pack 旁路、污染重建以及 v1→v2→v1 发布回滚后，在**仍然运行的相同实例上**新增六项 P0-A 负例与竞态核验。

## 证据链及最小边界

- **可信 Linux UID Kernel**：原 B9 B2/B5 Schema+Manifest、受权 Agent 工具、正式 Web Session/CSRF、独立 SQLite 权威审计和不可变 Release。
- **低权限 Linux UID Native**：真正 Saltcorn `@saltcorn/cli@1.7.0-beta.5`，真实字段编辑 / CLI Field.update / install-pack 都只对可删除的派生数据库产生影响；Native 用户无权读写权威 SQLite。
- **第三个低权限 Linux UID Plugin**：新的 `plugin_client.py` 真实 OS 进程；凭据只经切换 UID 后的标准输入发送；仅授权 `app-a` 的 View 类型 metadata.upsert 和 draft.read。不是生产插件管理器，也不是 Docker 沙箱。
- **Agent**：既有 B9 可信 `app-a` Agent 工具 Token，与第三 UID Plugin **共享同一个实际 SQLite 事务/修订冲突路径**。
- **独立 Oracle**：既有 B7 物理 SQL 检查器在 Kernel UID 下只读权威 SQLite；既有 B9 Native SQL Oracle 对派生 SQLite 的视图/字段/数据作真实读取。

## 预注册 P0A-01—06（全部属于局部证据）

| 检查 | 真正操作 | 成功标准 |
|---|---|---|
| P0A-01 | Plugin UID 直接 `open` 权威 DB/config、SQLite UPDATE | 全部 DENIED；不得因拥有工具 Token 获得 DB 读写 |
| P0A-02 | Plugin 独立进程实际通过 B5 scoped tool 读取草稿 | HTTP 200，来自该同一 B9 实例的 revision=5、active release v1 |
| P0A-03 | Plugin 假装更改 Model、直接发布和跨 app-b 读取 | 全部 403，权威物理快照严格不变 |
| P0A-04 | Agent 与独立 Plugin OS 进程依据**同一旧 revision**并发改变 View title | exactly one HTTP 200 + one 409，最终 title 恰为获胜写入的值 |
| P0A-05 | 在实际事务结束后，由独立 SQL Oracle 校验 | 只增加 1 条审计事件及 1 个成功回执；revision +1；当前已发布 v1、两份不可变 release、app-b 均不被污染 |
| P0A-06 | 获胜方用相同 changeId 重试并刷新真实 Saltcorn Chrome 页面 | 重放 HTTP 200/replayed=true，不额外产生回执；未经发布的 draft 不影响派生 Native 已发布 v1 |

真实 CI 使用 `s1-b9-authority-projection.yml`（固定 Node 24、Python 3.13、Saltcorn 1.7.0-beta.5、Playwright 1.56）。产物为原始 `/tmp/s1-b9-real-e2e.log` 与 `/tmp/s1-b9-evidence.json`。新增检查全部通过后只可以记录 **B9 36 + P0A 6 个局部实测通过**，**不允许直接推断 W 项或 TC 项 FULL PASS**。

## 预期停止 / 不冒充完成

1. 任一真实第三 UID 能打开权威 DB，或拒绝操作留下物理事件/回执，立即 FAIL；即便 Chromium 仍正常也不得忽略。
2. 两个旧 revision 提交若都成功、都失败、或赢家数据与物理记录不符，立即 FAIL；不得通过重试凑成功数。
3. Native 的独立派生数据库依旧可被自己的 owner UID 篡改；本研究路线依赖**权威/派生隔离与仅可信发布**，不可借此宣称原生 Pack 写入已被策略批准。
4. 三 UID 不是完整 Plugin Docker 隔离；OS root / 同 UID 恶意代码、外部副作用 UNKNOWN、业务权限 UI、全量 Pack diff、权威→Native 业务行更新、新鲜度签名只读渲染仍未在**本轮同实例**验收。
5. W01—W24、TC01—TC18 的冻结口径保持不变：**0/24 和 0/18 FULL PASS**，G1 **NOT_PASSED**；下次只可在严格对应单个冻结用例与独立 Oracle 后更新账本。

## 后续收敛，而非继续堆 B 编号

首先审阅此 CI 原始证据，再将**真正沙箱 Plugin、正式受权人工 Web 的过时编辑冲突、原生 Pack 差异审批/源约束**纳入同实例 P0-A 验收。其后才进行 P0-B 的 B2 最新权威源 → Ed25519 签名发布 → B15 原子快照 → B17 只读渲染的同实例贯通和旧快照拒绝；最后按 P1-C/D/E 逐项执行 TC01—TC18。未经证据不得抬高 G1。
