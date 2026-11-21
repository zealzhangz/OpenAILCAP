# S1 报告 41：B8 真实 Saltcorn 原生 Field.update、Pack、网页编辑器与 Linux DAC 的边界与反例

**日期：2026-11-21。结论：研究检查 24/24 PASS，其中危险反例被真实复现，不能作为原生安全合规通过。S1 IN_PROGRESS；G1 NOT_PASSED；G1-B01 PARTIALLY VALIDATED / OPEN。**

## 1. 原因：不能仅用外围 Broker 或操作系统目录权限宣称原生写入已经统一

[报告 19](19-real-browser-edit-evidence.md) 首次在实际 Saltcorn 原生浏览器的两张旧表单中复现了字段标签的覆盖；[C2 patch_native.py](../../experiments/g1-b01-c2/patch_native.py) 通过临时修改官方已编译 `/field` 路由实现特定旧上下文 409，但 `saltcorn run-js` 的真实 `Field.update` 绕过该路由仍然成功。

随后 B5 证明 HTTP Tool Broker 只能约束主动通过它调用的主体；B6 证明真正无 DB/Socket 挂载的 Docker 插件读写被拒；[报告 40（B7）](40-s1-b7-real-linux-dac-domain-kernel-evidence.md) 证明普通 Linux UID 不能访问独立 Domain Kernel 持有的 SQLite，但**相同 UID/root 的原生进程仍可物理写入**。

**B8 要求把反例放回同一个真正 Saltcorn 数据库、官方原生 Pack、真正 Native CLI 及未打补丁的官方 Native Web 编辑器里，而不是仅用模拟的 SQLite CLI 替代真实产品。**

### 冻结对照条件

- 固定实际 CLI `@saltcorn/cli@1.7.0-beta.5`、Node 24、Ubuntu 24.04、Python 3.13、Chromium + Playwright 1.56；
- 真正使用 `saltcorn reset-schema -f`、`saltcorn install-pack -f`、`saltcorn run-js -f` 和 `saltcorn serve`；
- 合同 Pack 为历史实验 `experiments/platform-saltcorn/contract-pack.json`，底层真实 `_sc_fields`、`s1_contracts` 有至少一条原生业务记录；
- 原生 SQLite 和服务配置在非 root `ailcapb8core` 私有目录，模式 **0700**；`ailcapb8plug` 为另一个真正独立 Linux UID；
- 受治理路径沿用此前实际测试过的 `experiments/platform-saltcorn/governed/gateway.py`，在同一真实 Saltcorn SQLite 中维护对 `title` 字段的修订、回执和审计。**该 Python Gateway 不是官方 Saltcorn 插件，不是 B7 Domain Kernel 的自动同步桥接；保留原生入口未覆盖的反例。**

## 2. GitHub 原始证据

| 对象 | 确认情况 |
|---|---|
| 实验源码和完整限制 | [experiments/g1-b01-b8](../../experiments/g1-b01-b8/README.md) |
| GitHub PR | [#10](https://github.com/zealzhangz/OpenAILCAP/pull/10)，已合并 |
| 合并 main SHA | [92a06863c91d8a59c80ca93ef95b2a87c4ca4f4e](https://github.com/zealzhangz/OpenAILCAP/commit/92a06863c91d8a59c80ca93ef95b2a87c4ca4f4e) |
| **最终成功的实际 CI** | [GitHub Actions #44899334319](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44899334319)：**completed / success** |
| CI Job | **136831743808** |
| 原始运行日志及机器可读 JSON | [Artifact #14704953422](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44899334319/artifacts/14704953422)，`s1-b8-real-saltcorn-native-write-path-dac-evidence` |
| B8 Saltcorn 原生路径与 Gateway 合同单测 | **15/15 PASS** |
| B2 可信 Domain Kernel 元数据回归 | **18/18 PASS** |
| B5 IR + 统一工具入口回归 | **40/40 PASS** |
| B8 实际 OS UID / 真 Saltcorn CLI/Pack / 真 Chromium / 物理 SQL | **24/24 PASS** |
| 外部大模型推理与费用 | **0 次** |

**务必注明**：B8-20、B8-23 的 PASS 是“官方 Saltcorn 存在绕过 CAS 的原生写入已被独立真实复现”，**不是**“已成功阻断所有原生写入”或“正式 W11/W16 已通过”。

### 保留 CI 工程失败（不得掩盖）

在最终成功前，有三类真实 CI 运行问题：早期 [#44898945763](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44898945763) 和 [#44899004955](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44899004955) 由可信测试 Runner 直接调用 `Path.exists()` 判断 mode 0700 内核私有数据库，实际得到 `PermissionError`。该行为说明 OS DAC 生效，修复是**让所有数据库存在性和物理 SQL 读取均以 owner UID 运行**，没有开放数据库。随后 [#44899061214](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44899061214) 与 [#44899216538](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44899216538) 揭示 `sudo/runuser` 会重置 PATH 及 Saltcorn 的 SQLite/Session 环境变量：存在 native CLI 返回非预期状态，甚至命令返回成功却未创建指定真实 SQLite 的情况。因此增加 [native_env_launcher.py](../../experiments/g1-b01-b8/native_env_launcher.py)，由可信编排器通过**stdin 一次性传送研究所需环境**，在切换到相应真实 Linux UID 后执行官方 Saltcorn CLI，不将环境里的 Session Secret 作为 `env KEY=value` 的公开命令行参数；原生 Plugin 也有可写的独立 HOME，避免把缺少缓存写权限误判为 SQLite 权限防护。最终成功 run 使用这一完整修正版。

## 3. 24 项观察：系统级隔离有效，但同数据库所有者的原生写入依然越过 CAS

### A. 真实 Native CLI 跨 Linux UID 拒绝：B8-01—08

在 Saltcorn 数据库所有者非 root UID **999** 下，官方 CLI 成功执行 `reset-schema`、`install-pack` 和原生 `Table.insertRow`，独立物理 SQLite 初始 `title.label="Title"`、业务合同 1 条。

另一真实 Native Plugin/CLI UID **997** 即使知道**测试数据库路径和临时 Saltcorn Session Secret**，仍无法通过普通 `os.open(O_RDONLY/O_RDWR)`、`sqlite3 UPDATE _sc_fields`、读取内核配置来访问 SQLite。实际用这个 UID 执行：

- `saltcorn run-js -f native-out-of-band.js`：真实 CLI **exit 1 / permissionError=true**；
- `saltcorn install-pack -f contract-pack.json`：真实 CLI **exit 1 / permissionError=true**。

独立只读 SQL Oracle 在两次尝试后确认字段仍是 `Title`、合同数据保持 1 条、相关数据库快照未变。**这说明“原生 CLI 可被 OS 权限阻止”这个有严格前提的命题成立，但该条件要求其进程不得与 Saltcorn 权威 DB 所有者共享 UID。**

### B. 低权限客户端的受控工具操作：B8-09—16

原版研究 `gateway.py` 以 UID 999 作为独立进程访问**同一个 Saltcorn 原生数据库**。另一个 UID 997 的客户端只凭测试分配的受限 Agent Token 经 HTTP 操作：

- 未认证 GET → HTTP **401**，readonly Token 写入 → HTTP **403**，跨 App GET → **403**。
- 带正确 expectedRevision/fingerprint 的原生 Field 标签修改：HTTP **200**；物理 `_sc_fields.title.label="Governed by Native Client"`，研究 Gateway revision **1**、持久化唯一回执 **1**，原生业务合同数据仍在。
- 用旧 expectedRevision 的另一次写入 → **409**，原生字段保持已批准的新值。
- 原请求、原主体、原 changeId 的相同再次提交 → HTTP **200、replayed=true**，物理回执计数仍为 1。

此处证明的是**研究 Gateway 自己的单资源版本账本/受权工具有效**，不是 Saltcorn 官方原生 Web/Pack 路由已受它控制。

### C. 未打补丁的真实 Native Web 仍然绕过：B8-17—22

官方 CLI 真正创建研究管理员，随后以**同一个 SQLite 数据库所有者 UID 999** 执行 `saltcorn serve --port 3108 --noscheduler`，Playwright/Chromium 使用真实 `/auth/login` 和 `/field/:id`、`contextEnc`、原生字段向导完整提交操作。网页读取 `Governed by Native Client` 后将原生 Field 标签改为 `Native Web Outside Gateway`，并且：

- 真实物理 `_sc_fields.title.label` **已经变更**；
- Gateway 受控账本 `revision` 依然是 **1**、成功变更回执仍 **1**；
- 原生向导实际走了 **3 步**；
- Gateway 随后的 GET → **HTTP 409 OUT_OF_BAND_DRIFT**；
- Agent 正常工具继续尝试写入 → **HTTP 409**，原生非法写入并未被工具覆盖；研究 CAS Ledger 没有错误地向前推进。

**核心结论**：Linux DAC 没有能力在同 UID Saltcorn Native Server 内部限制它自己的官方 `/field/:id` 路由调用 `Field.update`。这条原生网页入口实际仍然可以绕过外围版本账本。即便 Gateway 检测失败并拒绝后续修改，它无法撤销已经发生的原生网页数据修改。

### D. 同 UID 的官方 Native CLI 仍可绕过：B8-23—24

再以 UID 999 执行真正的官方 `saltcorn run-js -f native-out-of-band.js`：**exit 0**，`_sc_fields.title.label` 实际变为 `Native Outside Gateway`，但研究 Gateway revision 仍为 1、receipt 仍为 1。该状态下 Gateway 保持 **409 OUT_OF_BAND_DRIFT**，真实合同业务记录仍 1 条。证实第二条**未受强制治理的原生写入口**不仅存在于 Web `/field`，也存在于原生 CLI `Field.update`。

## 4. 架构权衡：此轮应否继续把 Saltcorn 原生数据模型作为 OpenAILCAP 唯一权威内核？

**研究结果否定的窄假设**：“只要给 Saltcorn 数据库增加 0700/0600 OS 权限，再外挂受控 HTTP CAS Gateway，Saltcorn 自带 Native Web、Pack、CLI 这些入口就会自然受到统一 CAS 和审计约束。”

理由不是主观推断，而是**同一正式 Saltcorn 数据库上真正发生的两次旁路写入，且研究版本账本和回执不增**。从强制策略看，这足以使该组合目前不满足 G1-B01 中要求的原生统一写入、权限回收、原子审计和正式发布门槛。

还不能否定的更广泛假设：通过深入改造上游 Saltcorn 模型/Field/Pack/CLI 全部写入 API、可强制 Hook、受控安装器和热更新机制，也许可以获得统一写入闭包，但需验证上游改造范围、插件兼容性、长期维护成本与性能；**当前没有原始证据支持已完成此事**。

因此形成**候选 ADR 优先方向，不立即宣称最终架构定案**：

> **独立可信 Domain Schema + Manifest Kernel** 作为唯一权威持久化和版本发布写入者；成熟低代码组件可复用作为**无写入特权的设计器、展示层或受治理的可派生 Runtime**，必须强制禁用任何对权威元数据的 Native Field/Pack/CLI 修改。业务数据同步、读模型/缓存、插件生命周期、原生安装/升级和运行态热更新仍需通过真实实验；无法做到强制隔离则拒绝将 Saltcorn 作为可修改的权威核心。

作为下一阶段进一步研究的可证伪 B9：让 B7 Kernel 独占真正权威 DB，Saltcorn 原生数据/页面只能读取它**发布出的不可变经校验投影**，Native 网页直接编辑和 Pack/CLI 修改只能影响**可删除的派生副本**，绝不写到权威 Schema/Manifest；投影差异更新/回滚/热缓存刷新与跨 App 语义必须由独立 Oracle 验证。若原生运行时对 metadata 热更无法保证可靠性，应考虑重启部署/物化应用版本，而非把 Gateway 强行更新 `_sc_fields` 的内部 SQL 当成生产补丁。

## 5. 对正式 G1 门禁的影响

S1 **IN_PROGRESS**；G1 **NOT_PASSED**；G1-B01 **PARTIALLY VALIDATED / OPEN**；冻结 W01—W24 仍 **0/24 FULL PASS**，冻结 TC01—TC18 **0/18 FULL PASS**。B8-01—24 是**专门用于可证伪研究的 24 个子观察**，不能凭数量与冻结 W01—W24 恰好相同就把它们混淆，更不能把两次危险绕过的 PASS 当成 W11/W16 安全通过。

- W11：本次 Native Web + CLI 真实绕过被发现并隔离后续工具，但**真实物理写入既成事实，且整个 Native 字段/Pack 体系未全部强制入核**，正式 W11 不能升级 FULL PASS。
- W16：两个不同 UID 的 Native CLI 受到 Linux DAC 真正拒绝，但同 UID Native CLI 仍可写，不能证明生产插件/安装器/Field 系统中不存在同 UID/特权旁路，正式 W16 不升级 FULL PASS。
- W17：Gateway 直接改原生 `_sc_fields` 不触发 Saltcorn Field.update 官方缓存/事件，未验证热运行态全量一致。
- W20/W24：真实外部副作用未知结果与统一应用/代码/流程跨域快照/补偿仍需单独验收。

**研究优先级**：停止继续仅修补 C2 单一 Native route 便宣称解决；将 B9 **“唯一权威 Kernel + 可删派生 Saltcorn 投影”** 作为下一轮实际架构验证，不再增加额外 DeepSeek 推理费用。
