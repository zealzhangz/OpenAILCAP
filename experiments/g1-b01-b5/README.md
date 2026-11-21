# S1 B5：Domain Schema + Manifest 与统一 Application IR 的受控对照，以及共用 Tool Broker

> **研究目的**：用同一合同/审批/风险评分应用，在相同 B2/B4 Runtime、相同数据、相同身份/授权、相同部署条件下测试两类**设计态表示形式**，并通过一个显式能力与权限的 Tool Broker 同时接入元数据命令、代码验证、发布/回滚。**重要：这不是两个完全独立的低代码内核基准测试，不足以断言某种架构优于另一种。**

## 1. 固定对照契约

- A：Domain Schema + Manifest。按 B2 `model.contracts`、`form.contracts`、`view.contracts`、`workflow.approval` 维护四种直接可运行元数据资源。代码扩展使用 B4 独立 ExtensionRegistry，并绑定 B2 已发布版本/Manifest。
- B：统一 Application IR。单个 `irVersion:1` 文档含 `entity.attributes`、`interfaces`、`processes`、`extensions`，每个引用显式绑定；可信 IR Compiler 将文档转换成**同样的四种 B2 元数据命令**，并保留相同 B4 Extension 合同。
- 同一服务端 Python B2/B4 Engine、SQLite 事务和 manifest SHA-256、Chromium、Docker 432 组业务 Oracle、合同输入、审批/风险评分结果。这样把“**表示形式**”作为唯一变化的工程因素，但**不能评估不同 IR Kernel 的吞吐量、存储事务/迁移或生产可运维性**。
- 两个独立应用 app-a / app-b 分别代表 A 与 B，测试资源权限/隔离、初建 4 条 B2 typed commands、插件只改 View、模拟人工浏览器修改 Form、过时 Agent 409、B2 发布 v1/v2/回滚，以及绑定风险代码的发布一致性。

## 2. 实验问题和公平指标

| 指标 | A / B 预注册方法 | 能判定什么 |
|---|---|---|
| 语义保真 | Direct Schema→IR→Domain roundtrip 全量对象、B2 Manifest SHA、拓扑 refs 验证 | 已覆盖的四类元数据在结构和运行语义上等价 |
| 数据输入成本 | 两种表示法的 canonical UTF-8 JSON 字节数 | **仅**一个样例的序列化大小，不是生产效率/维护成本 |
| 单项变更影响面 | 只改 Form/View 标题，对照最终 B2 发生变更的资源 ID 集 | 该受限场景变更对运行内核的最小影响范围 |
| 开发工具写入数 | 每应用创建四种 B2 资源均需四次命令；人机后续修改一次只需一次 | IR 一份文件**不等于**原子发布/变更 |
| 运行行为同构 | 同一 B2 Form 的真实业务行、审批轨迹、B4 代码风险评分/回滚 | 生成的运行时表现同构——但因为用了相同引擎 |
| 版本和权限 | 独立进程 Plugin 仅能 View、Agent 代码只能 Verify、人工模拟主体才可发布，验证旧版本 409 | 受控研究 Broker 的安全入口有效 |
| 旁路控制 | 有权直连 SQLite 改写代码 Artifact，已发布风险运行检测 hash drift | **承认并呈现 DB 特权旁路仍存在**，不假装被 Broker 阻止 |

## 3. 源码布局

| 源码 | 用途 |
|---|---|
| `ir_bridge.py` | 与 B2 契约严格对应的统一 IR 编译/逆向投影、Manifest 对照、无关字段/断引用拒绝 |
| `tool_broker.py` | 仅受信宿主持有 Actor 映射、capabilities/撤销和每个工具 allow-list，所有 Model/Plugin HTTP Bearer 只能走 v3 工具入口；B2 自有 Web Session/CSRF 保留 |
| `tool_client.py` | 单独 OS 子进程模拟插件与 Agent 调用，无法通过请求字段伪造 actor |
| `test_ir.py` | 表示法轮转、反例以及破坏图语义的拒绝 |
| `test_broker.py` | 无 Docker、无模型的授权、撤销、过期、注入、工具调用拦截单测 |
| `experiment.py` | 真正 A/B 两应用、HTTP 浏览器、Plugin 子进程、B4 Docker 构建及代码发布，物理 SQLite 只读 Oracle 和**主动特权写绕过的负对照** |
| `.github/workflows/s1-b5-ir-parity-gateway.yml` | 先跑 IR + Broker + B2 + B4 单元回归，再用真实 Chromium/Docker 检验，本实验**无外部模型调用** |

## 4. 权限与仍未解决的可信边界

- V3 工具以**服务器保存的随机 Bearer → Actor、应用、capability**决策，不读取模型给出的 actorId 或 role。普通 Agent 只能写允许的元数据、验证代码；插件被限制为 View 资源写入且不得验证/提交代码、发布 App 或读取其他应用。拥有明确授权的模拟人工身份才可 Stage/Publish/Rollback。
- `code.verify` 向外仅返回 hash、432 个测试通过数量，不向模型返回可伪造的 SandboxProof；`code.stage` 必须由可信 Broker 在真实 Docker **重新验证**后调用 B4 受权 Registry，不信任客户端的“我已测试通过”参数。
- 本研究 HTTP 服务不向非浏览器 Bearer 开放直接 v2 Store 路径，防止绕过 v3 per-tool allow-list；既有浏览器仍使用认证 Cookie 和 CSRF。
- **并不消除真正特权宿主代码、具有 Docker Socket/SQLite 路径的插件或上游 Saltcorn CLI 的旁路风险**。B5 特意由测试控制器直接修改 SQL 里的已签收代码 Source，以此证实后续运行 Hash 检查会拒绝，**但数据库写入本身仍可发生**。这直接保持正式 G1-B01 **OPEN**，不能把 29 个 B5 子项当作 24 项冻结 W 用例正式通过。
- B4 仍使用与 B2 同一个 SQLite 文件但**两个逻辑发布指针**。B2 应用发布版本变化与 Code artifact 的绑定不匹配时 fail-closed 返回 409；回滚后恢复。此正向观察不证明跨数据库事务或所有外部副作用有完整补偿。

## 5. 本地复现

环境：Python 3.13、Docker、Chromium 与 Playwright 1.56，独立研究 DB。

    cd experiments/g1-b01-b5
    python3 -m unittest -v test_ir test_broker
    cd ../g1-b01-b2 && python3 -m unittest -v test_schema
    cd ../g1-b01-b4 && python3 -m unittest -v test_policy
    cd ../g1-b01-b5
    docker pull python:3.13-alpine
    export S1_B4_IMAGE_ID="$(docker image inspect python:3.13-alpine --format '{{.Id}}')"
    python3 -m playwright install --with-deps chromium
    python3 experiment.py --output /tmp/s1-b5-evidence.json

单次真实 Docker 镜像 ID 在运行时固定，无外部 LLM Secret；`DEEPSEEK_KEY` 不作为本实验依赖。

## 6. 预期结论形式

若两条代表的 Manifest 和运行结果一致，只能得出：**在已覆盖的合同/Workflow/纯函数扩展领域，统一 IR 作为设计态源能够无损编译到 Domain Schema + Manifest 内核**。两者的真实差异主要在上游源文档、批量事务和引用管理的设计成本，需要更广泛业务/迁移/并发场景研究。**不能据此把统一 IR 提升为持久化唯一权威源，也不能认为“多个设计资源”在同一个文件中就具备跨资源 ACID。**

未来如需最终抉择，应补齐独立 IR-native Runtime、可编辑插件扩展、完整 Domain Kernel 强制写入的公平对照。S1 G1 **NOT_PASSED**，正式 W01—W24 和 TC01—TC18 仍维持完整通过 0 口径，除非有对应冻结用例的独立原始证据。
