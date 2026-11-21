# S1 研究报告 43：B10 两个真实 Saltcorn 在线实例、业务 Readiness、流量 CAS 切换与故障回滚

**日期：2026-11-21。实验判断：研究专项限定 44/44 PASS；S1 IN_PROGRESS，G1 NOT_PASSED，G1-B01 PARTIALLY VALIDATED / OPEN。**

## 一、为什么必须继续 B10

此前 [报告 41（B8）](41-s1-b8-real-saltcorn-native-write-path-evidence.md) 已在真实 Saltcorn Native Web/CLI 上发现权威数据同 UID 写入绕过；[报告 42（B9）](42-s1-b9-authority-saltcorn-projection-evidence.md) 则通过不同真实 Linux UID、独立 SQLite 数据库证明：如果 B2 Domain Schema/Manifest 才是唯一权威，Saltcorn 原生编辑和 Pack 只能污染可删除派生库，并可从 B2 发布 v1/v2 重建。**但 B9 每次切换均顺序停止旧 Saltcorn，再启动新进程**，没有在线多实例预热、持续处理请求、切换失败、在途请求版本隔离或者客户端浏览器真实走统一入口的证据。

B10 在这个狭义架构上增加**第三个独立 OS UID 的实际多线程 HTTP Router**，让两套**同时在线的真实 Saltcorn 1.7.0-beta.5** 通过真实业务 GET 先验证就绪，再用受控的 release/epoch CAS 切换。并且，不再只展示 Saltcorn 自带测试合同：本轮额外让 B2 权威内核真正执行一次**合同创建 + 超阈值两级审批**，检查切换与 Saltcorn 故障不会错误回滚该权威业务事实。

## 二、交付与真实 CI 一手证据

| 证据类型 | 原始链接 / 实际结果 |
|---|---|
| 完整源码、部署边界及复现 | [experiments/g1-b01-b10](../../experiments/g1-b01-b10/README.md) |
| 受控只读流量 Router | [router.py](../../experiments/g1-b01-b10/router.py) |
| 真正多进程集成实验 | [experiment.py](../../experiments/g1-b01-b10/experiment.py) |
| GitHub 工作流 | [.github/workflows/s1-b10-real-runtime-route-switch.yml](../../.github/workflows/s1-b10-real-runtime-route-switch.yml) |
| **已合并 PR** | [#12](https://github.com/zealzhangz/OpenAILCAP/pull/12) |
| **main 合并 SHA** | [d1b498699065de460ed1a3763aa0914066828fa0](https://github.com/zealzhangz/OpenAILCAP/commit/d1b498699065de460ed1a3763aa0914066828fa0) |
| **最终成功 GitHub CI** | [Actions #44906374299](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44906374299)：**completed / success** |
| CI Job | **136852721607** |
| 原始机器可读 JSON、单测及实际 E2E 日志 | [Artifact #14708420037](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44906374299/artifacts/14708420037)，`s1-b10-real-two-saltcorn-traffic-cas-failclosed-evidence` |
| B10 Router CAS/鉴权/失败拒绝单元测试 | **34/34 PASS** |
| B2 Domain Kernel 回归 | **18/18 PASS** |
| B5 Tool Broker/IR 回归 | **40/40 PASS** |
| **B10 三 Linux UID、真实双实例 Saltcorn/浏览器/SQL/路由/合同业务 E2E** | **44/44 PASS** |
| 外部大模型调用 | **0 次** |

失败验证同样保留：[初始 CI #44906169071](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44906169071) 的 B10 **44/44 业务检查本身全 PASS**，但实验结束后，由于测试控制器无法删除第三个 Router UID 创建的就绪目录文件，`TemporaryDirectory.cleanup()` 遇到真实 Linux DAC PermissionError，导致整体 CI 被正确标记为 failure。修复后只有可信的 sudo-capable CI 控制器在退出时回收 Router-owned 就绪目录，**没有放宽内核 Authority DB/密钥目录权限、没有赋予 Saltcorn 多余权限**。整套 44 项与三个回归组重新执行，在 [#44906374299](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44906374299) 真正全部成功。因此不把初始失败 Run 当作完成证据。

## 三、实际运行的信任模型：三个 Linux UID

```text
ailcapb10kern / UID 999
  B2 Domain Kernel / B5 v3 tools / Human Chrome approval
  authority.sqlite（专有 mode 0700 目录，DB/配置 mode 0600）
  四类 Domain Schema + immutable v1/v2 Release
  权威合同数据 / 两级金额审批 / Receipt + Audit
       ▲
       │ Router 仅持 app-a release.read-only token
       │ 不持 Agent/Publisher/Form/Workflow 变更 token
       │
ailcapb10route / UID 995
  独立 localhost HTTP Router
  GET /view/s1_contract_list       （唯一本轮公开业务路由）
  POST /_admin/register           （随机 Admin bearer）
  POST /_admin/switch             （Admin bearer + epoch CAS + release SHA）
  不暴露 /field /admin /auth、业务 POST
       ├── Saltcorn v1 / 127.0.0.1:3158
       └── Saltcorn v2 / 127.0.0.1:3159
                 │
ailcapb10salt / UID 997
  独占自己的派生 SQLite 文件；对 Kernel SQLite 无读写权限
  两套同时运行官方 Saltcorn CLI 1.7.0-beta.5 / Native Web
  v1 View 实体 3 列，v2 View 实体 4 列
```

**重要运行权限事实**：Saltcorn v1/v2 是两个不同数据库/进程，但位于**同一个派生 Runtime OS UID** 下。它们并不是生产级“每版本完全隔离的不可变容器”；有权访问派生目录的 Saltcorn 原生代码仍能物理修改自己的派生 SQLite。所谓不可变发布指的是**已验证来源的 B2 Release 以及 Router 中一个版本号到具体候选后端的锁定绑定**，不表示 Saltcorn 数据库已被只读挂载。

Router 配置仅含随机 Admin Token 与 B2 **release.read-only** Token，两者与持有业务提交/审批/发布权限的 Credential 分离；一条独立 live v3 `release.read` 请求在每次 register/switch 中读取**当前 B2 发布版本与 hash**，并再次执行实际 Saltcorn Native GET、HTTP 200 + 合同标记预热。只有通过检查，受信部署 Controller 才能注册或切换；Router 不掌握 B2 物理数据库文件和任何可信内核写入口。

## 四、44 条真实端到端检查中的关键结论

### 4.1 最小权限、未发布拒绝与真实权威业务（B10-01—10）

- Ubuntu 24.04 / Python 3.13 / Node 24 创建真实不同非 root UIDs：Kernel **999**、Saltcorn **997**、Router **995**。B2 核心真实启动、双应用初始无数据，独立 SQL 与目录模式确认权威隔离。未激活候选路由前，对前端 GET 请求为 **503 NO_ACTIVE_VERSION**，不冒充已就绪。
- Agent 经 B5 受限工具创建四类 B2 typed 资源，**真实 Chromium 人工发布 B2 v1**，验证发布 SHA。
- **与 B9 的关键不同**：使用真实 B2 `form.submit` 提交合同 `HT-2026-000001`，金额超过 100000000 分阈值（测试提交为 200000001 分）；调用 B2 `workflow.advance`，真实数据库中验证 `Draft → PendingLevel1 → PendingLevel2 → Approved`，独立 SQL 确认批准记录属于**权威 B2 Kernel**。这项试验并未把 WorkFlow 自动运行给 Saltcorn。
- 真正 Saltcorn v1 `reset-schema/install-pack/run-js/create-user/serve` 成功，其派生 Native SQL View.columns 为 `contract_no, amount_minor, status`，Native HTTP 页面包含合同号。**Saltcorn 的合同内容由原生 seed fixture 单独生成**，并非业务真实同步；即使合同号相同，标题与 B2 权威合同刻意不同，严禁把它当作 B2 完整合同数据投影。

### 4.2 预热、校验与一个始终单值的流量指针（B10-11—24）

- 未携授权 Admin Token 注册候选 → HTTP **401**；指向真实无人监听端口注册 v1 → **503 BACKEND_READINESS_FAILED**，候选列表仍为空；伪造的发布 Manifest SHA → **409 NOT_CURRENT_VERIFIED_RELEASE**。
- 真正 Native v1 业务 GET **200 且包含合同号 HT-2026-000001** 后，允许登记并用 `expectedEpoch=0,expectedFromVersion=null` CAS 激活 v1，前台 GET Header 返回 Release **1**；真实 Chromium 经 Router 加载 Native 合同页面成功。
- **Router 公开只读**：向该 View POST → **405**，试图经前台访问原生 `/field/:id` → **404**。但 Native 原生服务仍单独绑定 localhost:3158/3159，本轮**未测试生产网络策略阻止本机主体绕开 Router 直连原生后端**。
- Agent 在 B2 更新 View.columns，真实人工 Chromium 发布 v2，此时**权威 Release 已经是 v2，而客户端仍持续通过代理读取 v1**（可观察的部署滞后，而不是“原子跨系统发布”）。真正 Saltcorn 第二套 Native 实例在 3159 运行，独立 SQLite 显示 v2 的 View.column 四列 `contract_no, title, amount_minor, status`，与 v1 三列不同。无效业务标记（页面未出现预期合同号）→ **503 BACKEND_BUSINESS_READINESS_FAILED**；正确预热注册 v2 后，Proxy 尚未切换，客户端仍返回 v1。

### 4.3 真实在途请求不会因切换变成“半 v1 半 v2”（B10-25—32）

- 一个真实 HTTP GET 在 Router 中先抓取 `(v1 backend, route epoch=1)` 快照，并通过**实验专用 `X-B10-Test-Hold-Ms: 1600`** 延迟完成该请求；独立 Router Health 检查实际 `inflight=1`。
- 受信管理员发送 `changeId`、`expectedEpoch=1,expectedFromVersion=1,targetVersion=2,manifestHash=v2`，Router **在锁内再次读取真实 B2 当前 published v2/manifest SHA 并探测真实 Native v2 页面**，原子地将当前 epoch 从 1 更新到 2。
- 新的 HTTP GET 和真实 Chromium 立即看到 v2；原本已经抓取 v1 的在途请求最终仍返回 **X-OpenAILCAP-Release: 1 / X-OpenAILCAP-Route-Epoch: 1**，新请求返回 v2/epoch2。证明了**在这一条真实短 GET 请求下的版本固定**，没有宣称真实分布式反向代理所有长连接/流式事务已验。
- 完全相同的 `changeId` 再提交，返回 `replayed=true` 且路由 epoch 仍为 2；旧 expectedEpoch 或复用 changeId 修改内容均 **409**。**这是同一临时 Router 进程的内存 Receipt，未模拟真实丢包后的跨重启结果恢复，不能把它计入冻结 W20 FULL PASS。**

### 4.4 真实运行实例故障、明确失败与授权回滚（B10-33—44）

- 将真正正在服务的 Native v2 Saltcorn 进程**以 OS 信号结束**，确认退出。此前 front activeVersion=2，这次真实 Native 端口不存在，Router GET **503 BACKEND_READINESS_FAILED**、active 仍为 v2，**不擅自把客户端重定向到 v1**。这是经过明确设计的失败封闭，**不是服务连续可用的零停机切换**。
- Native v2 故障期间，B2 权威数据库中合同审批状态仍为 **Approved**，两级审批业务事实没有因为 Saltcorn Runtime 故障回退。
- 在 B2 当前发布指针仍为 v2 时试图让 Router 回滚到 v1 → **409 KERNEL_PUBLISH_POINTER_MISMATCH**。随后真正受权的 B2 Publisher 通过 v3 `app.rollback(expectedPublishedVersion=2,targetVersion=1)`，**原子回退 B2 发布指针**；Router 重新验证该 Release 并执行 `expectedEpoch=2,fromVersion=2,targetVersion=1`，epoch **3**。
- 真实前端 HTTP 重新返回 v1 + 合同，Chromium 通过 Router 可显示合同页面。独立 SQLite Oracle 最终确认 B2 app-a **两份 immutable Releases 均有效、当前发布 v1、最新草稿 revision=5**，B2 合同仍 **Approved**；app-b 始终与初始状态相同。Saltcorn v1 和 v2 派生数据库中的业务记录仍是各自独立的测试 fixture，**没有验证跨版本业务记录同步/恢复机制**。

## 五、B9→B10 架构推进的结论

本轮提供的新**限定正向证据**：在**B2 Domain Schema + immutable Release 是唯一权威**的前提下，两个同时在线的真实 Saltcorn 派生进程可以被独立 Router 的单值版本指针管理；业务就绪失败时不应注册，发布指针与 Version/Hash 不符时不能切换；一次真实在途请求有确定版本；新实例故障时安全失败封闭；人工批准回滚和 Router 的 CAS 指针回退后，仍活着的旧 Native Runtime 能重新对外服务；权威业务审批不被派生运行时的发布故障误回滚。

**必须保留的 P0 与正式门禁：**

1. **没有生产级路由 HA/无损停机切换证明（W17/W24）**。Router 仅为单个 Python 进程、状态/Receipts 存于内存；未持久化切换日志/候选注册、未重启恢复、未多副本锁定、未对接 Ingress/K8s/负载均衡器，也未验证全业务路由、Cookie、WebSocket、SSE、长连接和高并发。真正 v2 故障时观测到的是 **503**，因此尤其不能声称零停机。
2. **Saltcorn 派生实例依然能写自己的 DB，未做不可变只读挂载**；Router 禁止公开 POST 和原生编辑，但当前 Saltcorn 服务监听本机端口并未由网络命名空间/ACL 阻止直连；真实生产需强化网络、身份与发布制品签名。
3. **业务数据仍未投影或同步**。B2 有真实的表单创建/两级审批，Saltcorn 有独立 fixture，相同合同号也不能证明 CDC/outbox/跨版本业务数据一致、行级权限、数据脱敏和生产交易不回退。**下一 P0 是选定真正业务数据唯一写入者并验证基于事件的只读物化投影及幂等重建**。
4. **Form、Workflow、B4 Code 仍未由 Saltcorn 正式执行**，B10 不代表完整 AI 应用功能和自动化测试已闭环；B2 业务审批是单独的可信 Domain Kernel 逻辑。
5. **跨代码/应用/流程/外部副作用的统一事务和未知结果补偿未做**。B2 发布指针与本轮代理切换发生在两个服务的先后步骤，能发生已发布 v2 但仍服务 v1 的部署滞后。正式 W20/W24 不能因为研究 Router 内存 CAS 而判通过。
6. **本轮研究不包括真实远端密码/身份管理、企业多租户与发布审批**。Token 是 CI 随机测试凭据，Saltcorn 仅匿名公开 View。root/Kernel 同 UID 绕过仍如 B7。

**最终状态**：S1 **IN_PROGRESS**；G1 **NOT_PASSED**；G1-B01 **PARTIALLY VALIDATED / OPEN**；冻结 W01—W24 **0/24 FULL PASS**，冻结 TC01—TC18 **0/18 FULL PASS**。B10 44/44 独立子实验不能直接晋升正式冻结门禁。

**下一轮建议 B11**：用 B2 权威 Records 与审批状态作为真实数据来源，不再向 Saltcorn 原生实例 seed 独立合同；实现有限、脱敏、单向的业务数据投影协议，验证新增/审批后的事件重放、重复消息幂等、跨 v1/v2 无数据丢失、回滚只回退 UI 版本不撤销业务事实。同时设计 Router 状态持久化和跨重启切换的负对照，独立评估是否足以开始正式 W17/W20/W24 验收。
