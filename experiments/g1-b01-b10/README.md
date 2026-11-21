# S1 B10 — 真实 Saltcorn 不可变版本运行实例、业务 Readiness、流量切换与回滚

> 本实验在 B9 的**唯一权威 B2 Domain Kernel → 可删除的 Saltcorn Model/View 投影**上增加一个独立 HTTP 只读流量路由器，真实运行 **两套同时存活的 Saltcorn 1.7.0-beta.5 实例**，测试先预热验证、原子路由指针 CAS、在途请求版本固定、故障显式失败与人工批准回滚。**只研究 GET 单个公开合同 View；没有生产鉴权、长连接、代理集群、正式 HA/无损发布证明。**

## 一、可证伪假设

- **H10.1 三层最小权限**：受信 B2 内核、Saltcorn Runtime 和流量路由器以不同的真实 Linux 非 root UID 运行。内核数据库目录 0700、DB/密钥 0600。Saltcorn Runtime 无内核 DB 权限和任何 Broker Token。路由器仅有 *app-a release.read* grant，不持有 Agent、Publisher、Form/Workflow 写入 grant。
- **H10.2 真实双活候选（不是双主写入）**：v1 实例 3158 和 v2 实例 3159 均通过真实官方 Saltcorn reset-schema、install-pack、run-js 和 serve，彼此有独立派生 SQLite；B2 Chrome 发布 v2 后，原有流量仍路由 v1，直到新实例通过真实 **HTTP 200 + 合同业务标记**及独立原生 SQL 列配置检查，才允许注册和切换。验证失败不能更改当前路由。
- **H10.3 流量指针**：router 接受可信管理员 Bearer 及 `changeId / expectedEpoch / expectedFromVersion / targetVersion / manifestHash`，并于 switch 期间重新调用真实 B2 `release.read` 验证当前不可变 Release 指针和 Manifest SHA，重新请求候选的实际原生业务页面；**一个锁内的路由指针变更**成功后 New GET 全部按 v2 路由，Old GET 捕获的旧 `(backend,release,epoch)` 继续按 v1 路由。相同 changeId 幂等，旧 epoch / 错误 hash / 错误源指针必须 409。此状态只在进程内存中存储，**不能声称重启恢复或多节点分布式原子更新已通过**。
- **H10.4 发布与真实故障**：切换到 v2 后杀死真正 Saltcorn v2 服务，代理对客户端 GET **显式 503，不擅自回退 v1**；真实 B2 审批数据不受 Saltcorn 的故障影响。可信 Publisher 先通过 B2 v3 app.rollback 真回滚 Release 版本指针，再通过 router 版本 CAS 切回仍在线 v1；真实浏览器恢复合同展示。
- **H10.5 真正的业务归属**：与 B9 仅投影页面不同，本轮 B2 Kernel 独立真实执行合同创建、金额阈值**两级审批**并持久化 `Approved`；Saltcorn 派生实例仍使用**自己独立 seed 生成的测试合同**，即使 Contract No 一样标题也不同，证明**本轮未实现业务数据从内核到派生库的同步**。不能把页面运行和内核审批成功简单相加，当成 Saltcorn 本身执行了 Workflow，也不代表审批外部副作用与代理切换是一个事务。

## 二、架构/原生数据边界

~~~text
Linux UID: ailcapb10kern（独立非 root）
  0700 authority-private / 0600 authority.sqlite + config
  B2 authoritative DomainSchema / releases / receipts / audit / records
  B5 v3 limited agent & publisher & business-runtime tools
     │
     │ router 只有 B2 v3 app-a release.read；无任意数据写
     ▼
Linux UID: ailcapb10route
  0700 route-private / 0600 admin config（仅 CI 研究）
  自主 ThreadingHTTPServer Read-only Router
  公开：GET /view/s1_contract_list
  禁止：POST /view、/field/:id、/admin 等 native 写入口
  管理：POST /_admin/register、POST /_admin/switch（随机 Bearer）
  内存：candidate versions、active pointer、epoch、changeId replay
      ┌───────────────────┴───────────────────┐
      ▼                                       ▼
Saltcorn v1 真实 Native 进程 3158          Saltcorn v2 真实 Native 进程 3159
真实 SQL projection-v1.sqlite             真实 SQL projection-v2.sqlite
View: contract_no / amount_minor / status View: +title
      └──────── 同一 Linux UID ailcapb10salt ────────────┘
            0700 runtime-private（与权威 DB 不同 UID）
~~~

### 安全与适用限制

这个 Router 故意**只暴露一个公开、只读的 Native View**，客户端不能通过该 Router 访问 Saltcorn 原生字段编辑、管理后台、登录和其他页面。但 GitHub CI 的原生 Saltcorn 服务直接绑定在 `127.0.0.1:3158/3159`，同一宿主上获准接入 loopback 的进程仍可能直接访问这些原生 URL；这是研究测试网络，不是生产网络隔离。若最终采用，需要业务网关/网络命名空间阻断 Native 服务直接被未授权用户访问，支持必要 Cookie/SSO/CSRF、TLS 和真正的授权转发。

Readiness 的业务标记来自真正的 Saltcorn HTTP 页面（`HT-2026-000001`）并独立查询原生 SQLite 的 View 列，但业务标记可被伪造、SQLite 不是外部签名的、没有验证所有页面/路由和健康依赖。这仅是当前测试合同的最小 readiness，不是综合真实生产业务就绪证明。

HTTP `X-B10-Test-Hold-Ms` 请求头**只为可重复验证在途请求**，在路由指针捕获后人为延迟指定时间，不能在生产实现中保留。代理并未验证断线重连、流式响应、大文件、WebSocket/长连接、SSE、TLS、Keep-Alive 连接重用或高并发滚动发布。

## 三、完整交付文件

| 文件 | 研究功能 |
|---|---|
| `router.py` | **实际多线程**只读 HTTP 转发，独立 Kernel Release SHA 检查、业务 GET 预热、注册、路由 CAS、幂等 changeId、在途请求快照及明确 503 |
| `kernel_service.py` | 基于 B9 真实 B2/B5 核心，增加独立 app-a release.read-only Router Token 和独立 B2 form.submit/workflow.advance Runtime 能力 |
| `native_env_launcher.py` | 切换真实 Linux UID 后只允许运行 B10 的派生数据库 `projection-*.sqlite`，Saltcorn session secret 经 stdin 而不是命令行传递 |
| `experiment.py` | 44 条真实 Linux OS/B2/B5/两套同时在线 Saltcorn/Chromium/独立 SQLite/流量切换/在途/故障/回滚检查 |
| `test_router.py` | 34 条 CAS、权限、参数结构、失败拒绝、Readiness、并发 changeId 测试；**不能替代真实 GitHub E2E** |
| `.github/workflows/s1-b10-real-runtime-route-switch.yml` | Ubuntu 24.04 / Node 24 / 官方 Saltcorn 1.7.0-beta.5 / Python 3.13 / Playwright Chromium 1.56，三个独立 Linux UID，零 DeepSeek |

## 四、测试过程与顺序

1. 创建可信 Kernel + Runtime + Router 不同 UID，核对 Authority SQLite 0700/0600、原生 Runtime 不能直接读取权威 DB，Router 启动后无活动版本时访问业务页面 503。
2. 通过 B5 Agent 创建 B2 Model/Form/View/Workflow，真实 Chromium 人工发布 v1；同时 B2 内核真实保存金额超阈值合同并处理 `Draft → PendingLevel1 → PendingLevel2 → Approved`，独立 SQLite 查询其持久化状态。
3. 用 B9 严格编译器从 `release.read` 经验证的 Manifest 物化真实 Saltcorn v1（Native SQL View.columns 三列）。原生合同来自固定 seed，明确不等同于 B2 业务合同源。
4. Router 的匿名 Register 401、断线端口注册 503、假冒 SHA 注册 409；正确真实业务 GET 验证后注册 v1、以 `expectedEpoch=0` 激活 v1。真正 Chromium 通过 Router 查看 View。公开写入/原生字段编辑均拒绝。
5. Agent 经 B2 CAS 修改 View.columns，人工 Chromium 发布 v2；在 v2 已经成为 B2 当前发布但没有切换之前，流量仍落 v1。物化第二个真正 Saltcorn 运行实例、检查 SQL 列从 3 变 4、业务页面 200。错误业务 Marker 503，正确预热后注册 v2，但客户端仍看到 v1。
6. 让已有一个真正 Router GET 请求捕获 v1，然后用研究专用 Hold-ms Header 人为保持请求不结束；此时带 `expectedEpoch=1,expectedFromVersion=1,targetVersion=2` 完成 B2 真实 Release 指针和新实例再次 Readiness 双检查，并原子切换内存路由到 v2。**新 HTTP GET 与真 Chromium 得到 v2；在途旧 GET 最终仍返回 v1 的 Header/HTML**。
7. 同一 changeId 重发得到 `replayed=true`，路由 epoch 未增；旧 epoch / 重复 changeId 但不同 body 均 HTTP 409。
8. 真实杀死 v2 Saltcorn 服务，Router GET **503**，仍维持 active v2、不静默 fallback。真实 B2 业务合同仍然 Approved。B2 指针还为 v2 时企图路由回 v1，被 409 拒；随后可信 Publisher 真执行 B2 app.rollback v2→v1，Router 再 CAS v2→v1，业务 GET 与真 Chromium 恢复。最后两个不可变 Release 仍存在，B2 草稿 revision 不被回退，App B 完全未变。

## 五、不应升级的门禁及下一问题

S1 IN_PROGRESS / G1 NOT_PASSED / G1-B01 OPEN。B10 不能据此宣称 W17/W20/W24 FULL PASS：这里只验证**同宿主临时 HTTP Router 的内存原子指针**，没有代理集群切换/配置持久化恢复/生产网关/K8s 无中断滚动升级、跨服务事务与幂等外部动作补偿。原生 Saltcorn 的工作流仍**未**投影；审批是 B2 Kernel 独立处理的，Saltcorn 只展示自有 seed 生成的副本，与权威业务数据**尚未建立可验证同步协议**。

后续研究应优先 B11：不再只拿同合同号的两个不同数据副本当成果；明确选择 **B2 Authority Business API + Saltcorn 只读业务视图** 或正式 CDC/outbox/物化数据投影的边界，验证真实合同新增/更新/审批后在 Saltcorn 页面跨版本可重放、幂等、脱敏、回滚不回退业务事实，并补全发布控制面崩溃恢复与故障切换行为。正式冻结 W01—W24、TC01—TC18 均不能直接按 B10 独立研究项数量升级。
