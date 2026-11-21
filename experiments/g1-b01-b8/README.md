# S1 B8：真实 Saltcorn Native CLI / Field.update / Pack / Web Route 写入口与 Linux UID 隔离边界

> 这是第一阶段的 **C2 原生写入控制候选的实证反例研究**，不是生产 Saltcorn 插件，也不是已集成 B7 Domain Kernel 的完整原生 Saltcorn。只有在实际 Saltcorn、官方原生 CLI、真正 Chromium、真实 SQLite 中取得证据，才能对“数据库 OS 隔离可以统一原生写入”给出结论。**成功复现不安全入口的测试按预注册负对照为 PASS，但仍意味着 G1-B01 OPEN。**

## 0. 直接复用的可信一手基线

- [C2 实验源码](../g1-b01-c2/patch_native.py)、[C2 GitHub 工作流](../../.github/workflows/s1-g1-b01-c2.yml)：官方 `@saltcorn/cli@1.7.0-beta.5` 的 `/field` 编译路由做临时签名校验补丁后，真实浏览器旧表单能收到 409，但原生 `saltcorn run-js -f native-out-of-band.js` 调用实际 `Field.update` 仍可绕过路由，不能把 C2 插件式 UI 路由补丁叫做统一写入口。
- [Saltcorn governed gateway 研究源码](../platform-saltcorn/governed/gateway.py)：仅在研究 SQLite 中用原子 SQL 修改 `_sc_fields.label`，并维护 revision/receipt/audit，能在其他原生写入后检测指纹漂移但不能阻止物理写入。**本轮不修改该原型网关的 CAS 算法**。
- [B7 真实 OS DAC / Domain Kernel](../g1-b01-b7/README.md)：独立非 root 用户+0700 目录能阻止另一个 UID 的直接 SQLite 读写，但 root/同 UID 必须作为真正反例。

## 1. 研究假设与两组相互对照的真实原生入口

核心实验对象是同一个**真实 Saltcorn 原生 SQLite**，使用固定 `@saltcorn/cli@1.7.0-beta.5` + Node 24 + Chromium/Playwright 1.56 + Ubuntu 24.04，数据结构由仓库历史官方 CLI 创建的 `contract-pack.json` 建立，包含 `s1_contracts`、`_sc_fields`、原生 View、至少一条业务合同。所有凭据只用于 CI 一次性数据库。

- **A：非特权 Linux 原生 CLI**。与 DB Owner 真正不同的 `ailcapb8plug` 用户，拥有一般 Python、Node 和已安装的 `saltcorn` 命令权限，**故意知道本次 Saltcorn Session Secret 和 DB 路径**，但 DB 位于内核所有者 `ailcapb8core` 的 mode 0700 目录。它实际执行 `sqlite3` 的读写和 UPDATE、`saltcorn run-js -f native-out-of-band.js` 的真实 `Field.update`、`saltcorn install-pack -f contract-pack.json`。预期：操作系统拒绝 DB 访问；物理数据/字段/审计在这些进攻后不变。若 CLI 竟然成功更新权威字段，实验失败。
- **B：同 DB Owner UID 的真实 Saltcorn Server/CLI**。原生 Saltcorn `saltcorn serve` 持有数据库所有者权限，真正管理员通过 Chromium 访问官方 `/auth/login`、`/field/:id`，向导点击提交 `Field.update`。另一组正控制是同 owner UID 的实际 `saltcorn run-js -f native-out-of-band.js`。预期：它们**仍能绕过我们的受限 HTTP Gateway**写入 `_sc_fields`，未增加 CAS 版本/receipt；我们的研究网关发现 `OUT_OF_BAND_DRIFT` HTTP 409。即使此负对照「PASS」，它代表 C2 仍具有不安全的 Native Write 入口，不能声称 OS DAC 强制全部 Saltcorn Native 写操作受治理。

### 可信研究 Adapter 的使用边界

实验还以 owner UID 启动现有 `platform-saltcorn/governed/gateway.py`，在**同一个真正 Saltcorn SQLite**里维护研究版 `title` label 版本、变更回执和审计。不同 UID 的 Python 工具客户端借由**stdin 一次性获得本实验被授权的 Agent Token**（无 argv / Token 文件），向 gateway 提交实际 HTTP CAS 写入；同时未经授权、只读 Token 和跨 app 请求被拒绝，失效修改返回 409。**这不是 Saltcorn 官方插件 API，也不是 B5/B7 Kernel 生产整合**；Client 是普通 OS 进程，不是大模型，Gateway 是独立研究写入口，实际 Saltcorn Web 仍未封锁。

## 2. 安全测试与公平接受准则

1. 正向：Saltcorn Owner 用户确实 `reset-schema`、`install-pack`、`run-js Table.insertRow` 成功，物理 `_sc_fields.title.label=Title`、合同记录 1 条。防止误用不真实的假 DB 或空表。
2. OS DAC：DB 私有目录 owner 0700；另一 Linux UID 对真实 DB 的 `os.open(O_RDONLY/O_RDWR)`、`sqlite3 UPDATE _sc_fields` 与服务 Token 私有配置的读访问全部拒绝。
3. **官方 Saltcorn Native CLI 真执行**：不同 UID 直接执行 `saltcorn run-js` 与 `saltcorn install-pack`，确实失败，且独立 SQLite Oracle 确认原生 metadata/业务行没有发生变更；同 UID 官方 CLI `Field.update` 能写，形成公平的真正控制组。
4. 受治理人机接入：不同 UID native-client 使用 HTTP Agent Token 成功修改物理 Saltcorn `title.label`，并维护 revision/receipt；旧 revision 409，同 changeId 重放成功且收据不重复。
5. **原生 Native Web 攻击**：真实 `saltcorn serve` 在 owner UID 启动，Playwright 实际登录原生 `/auth/login`，修改原生 `/field/:id` 字段标签。检查真实字段 label 新值已写入，但研究 CAS revision 未变化，证明同 UID Web 路由绕过；Gateway GET 和后续工具写入实际 409 `OUT_OF_BAND_DRIFT`。
6. 最后同 UID CLI `Field.update` 再次直接成功，受治理 HTTP 依然隔离，原生业务合同仍在。**不要把“发现越权写入的 409”描述为物理阻止该越权写入。**

## 3. 文件

| 路径 | 作用 |
|---|---|
| `gateway_service.py` | 在真正 Saltcorn Owner UID 下启动不作改动的研究 Gateway，与 Saltcorn 原生 Web 同时连接真实 SQLite |
| `native_http_client.py` | 另一个 Linux UID 进程，stdin 获取最低权限 HTTP Bearer，发出测试用 GET/POST 原子变更 |
| `physical_native_oracle.py` | 独立 SQLite 只读：`_sc_fields`、`s1_contracts`、研究 Gateway revision/receipt/audit（不依赖 Gateway 返回值） |
| `experiment.py` | 实际官方 Saltcorn Schema/Pack/JS、跨 OS UID CLI 负面操作、真实 Chromium Native Editor、Gateway 409 和同 UID 绕过检查 |
| `test_native_contracts.py` | 预冻结测试源、Pack/Field.update 源头、真实 SQL 攻击行为与网关合同的单元检查 |
| `.github/workflows/s1-b8-native-saltcorn-dac.yml` | Ubuntu 24.04 + Node 24 + Saltcorn `1.7.0-beta.5` + Python 3.13 + Playwright 1.56 + 独立 Linux UIDs；**无需 DeepSeek** |

## 4. 环境与限制

实验会运行真实 `saltcorn reset-schema -f`、`install-pack -f` 等原生高风险操作。因此**只允许 CI 的一次性 VM 环境，不得在生产主机或者已有 Saltcorn SQLite 上直接执行**。GitHub Actions 工作流完整配置了环境；本地运行必须先创建两个同名但 UID 不同的专用系统账号，安装上述固定版本 Node、Python、Saltcorn CLI 与 Chromium。

研究限制：

- 本轮原生平台固定 Saltcorn CLI 发布版，不把适配器包装为受上游官方支持的插件或事务性扩展。
- 真正 Saltcorn Native UI/CLI 同数据库 UID 的入口**预计仍然可越过 CAS**：该反例若成功，并不是我们研究后认为“应允许”的功能，而是**表明 C2 对全路径强制治理并不成立**。技术路线应考虑原生编辑/Pack/import 禁用或 upstream 原子 Hook；若无法确保，优先选择自主可信 Domain Kernel 为**唯一权威写入者**、Saltcorn 仅作派生运行/呈现侧，先验证运行时缓存/热更新语义再作最终决定。
- 真实 SQLite Schema 的研究 Gateway `_sc_fields` 更新不调用官方 `Field.update`，其模型缓存、事件与表约束副作用并不等价于 Saltcorn Native Update，不能用于生产。
- Linux DAC 对 root、同 UID、`sudo`、Docker Socket 没有保护；B7 已独立证实。
- 未验证所有原生 Pack 转换、Web 路由、真实第三方 Plugin 安装和企业授权；未达到冻结 W01—W24 或 TC01—TC18 的全套验收，G1-B01 **OPEN**，S1 **IN_PROGRESS / G1 NOT_PASSED**。
