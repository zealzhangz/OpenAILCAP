# OpenAILCAP 研究交付索引

原始任务以仓库根目录 [README.md](../README.md) 为准，原文不修改。日期：2026-11-21。当前为首轮研究启动包，**不是整个七阶段的完成成果**。

1. [八项可证伪假设](00-foundation/01-hypotheses.md)
2. [人机双向编辑与统一应用模型](00-foundation/02-consistency.md)
3. [七阶段门禁](00-foundation/03-roadmap.md)
4. [第一阶段深入调研计划](01-research/01-plan.md)
5. [一手源码证据台账](01-research/02-evidence.md)
6. [最小实验协议](01-research/03-experiments.md)

**当前状态**：已静态阅读核心源码并固定五个外部项目的 Commit；八项假设验证 0/8；完整 PoC 0/4；第三方运行复现 0；G1 未通过。

推荐后续目录：`docs/02-product`、`docs/03-architecture`、`docs/04-specification`、`prototype`、`platform`、`experiments`、`benchmarks`、`manual`；按实际进度增量建立，不制造空目录。

## 2026-11-21：第一组实测补充

- [ToolJet MCP 真实源码同步调用链](01-research/04-tooljet-sync-trace.md)
- [H01/H03 首轮模型实验结果](01-research/05-roundtrip-results.md)
- [可执行实验源码、28 项单测及结果 JSON](../experiments/roundtrip/README.md)
- [GitHub Actions 模型实验检查](../.github/workflows/stage1-roundtrip.yml)

**更新后的状态**：模型层对照 A/B 各通过 10/10 场景，防御测试总计 28/28 通过；旧快照覆盖负例已复现。仅完成模型层 Spike，尚无真实低代码平台复现；H01/H03 平台级仍未验证，G1 未通过。

- [GitHub Actions 独立运行验收记录](01-research/06-ci-validation.md)：运行 #44866343414，状态 success；仅确认模型实验通过，G1 未通过。

## 2026-11-21：S1 真实数据库实验与许可证核查

- [ToolJet CE/EE 持久化边界、NocoBase Agent/插件安全与许可证风险](01-research/07-persistence-and-license.md)
- [可运行 SQLite 事务实验（23 个独立测试）](../experiments/sqlite-roundtrip/README.md)
- [SQLite GitHub Actions 复现工作流](../.github/workflows/stage1-sqlite.yml)

本轮在文件级 SQLite 数据库完成事务、进程异常退出恢复、乐观冲突、版本回滚及应用分区模拟测试。23/23 本地测试通过（CI 状态另行核查）；**真实低代码平台与安全身份认证仍未验证，G1 仍未通过**。NocoBase v3 的额外许可证条款与 AI 开发平台型产品存在复用风险，详见研究报告。

- [SQLite GitHub Actions 独立验证记录](01-research/08-sqlite-ci-validation.md)：Run #44867849367，23 项测试与报告生成步骤均成功；仅证明 SQLite 持久化 Spike。

## 2026-11-21：S1 四平台对照与统一合同基准

- [四平台 22 项能力证据分级矩阵](01-research/09-capability-matrix.md)（[JSON 数据](01-research/capability-matrix.json)）
- [统一合同业务 Benchmark 与 18 项平台级验收标准](01-research/10-contract-benchmark.md)
- [NocoBase v3 官方 CLI 实际安装失败记录](01-research/11-installation-trial.md)：Run #44868550471，模板包下载 E530，**未成功创建应用**
- [G1 阶段中期证据复审](01-research/12-g1-gap-review.md)
- [合同规范与独立业务 oracle 工程](../experiments/contract-benchmark/README.md)

**状态**：已完成统一能力研究的首轮证据矩阵和合同场景预注册。真实平台试验被第三方模板包仓库阻断，18 项平台任务均 NOT_RUN；G1 未通过。必须区分合同 oracle 正确与真实平台验收成功。

- [合同 Benchmark 规范 GitHub Actions 检查记录](01-research/13-contract-oracle-ci.md)：Run #44868820335 success，12+12 oracle 自检通过，18 项平台任务仍 NOT_RUN。

## 2026-11-21：S1 首次真实第三方低代码平台运行与合同纵向切片

- [Saltcorn 真实运行时：7/7 原生表/视图/REST/未授权拒绝实测](01-research/14-saltcorn-real-platform.md)，[Actions Run #44869777036](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44869777036)
- [Saltcorn 原生合同 Pack：9/9 配置模型、SQL 记录、REST 与页面实测](01-research/15-native-contract-platform-evidence.md)，[Actions Run #44869926796](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44869926796)
- [真实运行时源代码与实验脚本](../experiments/platform-saltcorn/README.md)
- [两次运行日志的结构化核查摘录（非原始 Artifact）](01-research/saltcorn-runtime-observations.json)

**重要更新**：第三方可运行低代码参考平台已从 0 增加到 1；总计 16/16 项平台运行时检查由独立 GitHub Actions 实际执行成功。合同原生 Pack 已实现模型/页面最小纵向切片，但金额类型与冻结合同基准存在差异，审批/AI/人机交互未执行，所以 18 项正式合同平台任务仍 0/18 PASS。**G1 仍未通过**。

## 2026-11-21：S1 真实平台多轮编辑负对照与候选 ADR

- [真实 Saltcorn 旧 Pack 覆盖人工编辑的实测源码报告](01-research/16-saltcorn-roundtrip-evidence.md)
- [A/B/C 实验的 GitHub Actions 机器可读证据摘录](01-research/saltcorn-roundtrip-observations.json)（原始 Run [#44871169761](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44871169761)，Artifact 14694023138）
- [候选 ADR：Agent 默认修改工具不得使用未经保护的全量恢复接口](01-research/17-provisional-adr-guarded-editing.md)
- [可重复运行的 Saltcorn A/B/C 对照测试代码](../experiments/platform-saltcorn/roundtrip/README.md)

**本轮事实**：18 次数据库/HTTP 断言均符合预注册预期，其中 B 路径证明了危险的静默覆盖，属于负面结果而非 H03 通过。程序化人工/自动化均由原生 CLI 脚本执行，尚未涉及真正可视编辑器或 LLM Agent。**G1 未通过**。

## 2026-11-21：S1 真实 SQLite 事务与双进程版本竞争

- [真实 Saltcorn SQLite 包装事务、原子事务与绕过治理研究报告](01-research/18-saltcorn-sqlite-atomic-evidence.md)
- [双进程测试执行结果机器可读摘录](01-research/atomic-observations.json)；原始 [GitHub Actions Run #44872093657](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44872093657)，Artifact 14694034903
- [可复现的原生事务与双进程实验工程](../experiments/platform-saltcorn/atomic/README.md)

**本轮 36 次阶段断言均符合预期，但同时复现两个危险问题**：Saltcorn SQLite withTransaction 异常后写入不回滚；人工绕过研究版本表后，Agent 侧 CAS 会错误接受旧版本并静默覆盖人工值。这是 H03 的强约束证据，**不是 H03/G1 通过**。冻结合同任务仍 0/18 完整 PASS。

## 2026-11-21：S1 首次真实 Chromium 人工设计器保存与旧页面覆盖实证

- [研究报告 19：真实浏览器登录、CSRF 字段向导、双标签页覆盖及模拟 Agent 版本失效](01-research/19-real-browser-edit-evidence.md)
- [机器可读的 9 项浏览器与 5 项后置测试证据](01-research/browser-edit-observations.json)
- [Playwright 浏览器真实 UI 复现工程](../experiments/platform-saltcorn/browser/README.md)
- [原始成功 GitHub Actions Run #44873882208](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44873882208)，Artifact 14694788713

**本轮重大突破**：真实 Chromium 管理员页面已实测字段提交，B 保存后 A 旧表单成功覆盖 B，之后外部 Agent 版本表没有记录人工编辑，再一次错误允许模拟 Agent 覆盖真实浏览器变更。9/9 浏览器与 5/5 后置断言通过，其中两次覆盖是**故意复现的负面结果**。此前 Run #44873783039 因 Ubuntu 26.04 与 Playwright 1.56 不兼容而在浏览器安装前失败，固定 ubuntu-24.04 后成功。**G1 未通过；合同完整 TC 仍 0/18。**

## 2026-11-21：S1 共享受治理 HTTP 编辑接口正向验证

- [真实 Saltcorn SQLite 上的共享编辑协议研究报告 20](01-research/20-governed-http-evidence.md)
- [22+4 项 GitHub CI 证据摘要](01-research/governed-http-observations.json)；原始 [Actions Run #44874668928](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44874668928)，Artifact 14695407749
- [研究用网关、浏览器及模拟 Agent 验收代码](../experiments/platform-saltcorn/governed/README.md)

**本轮明确的正向结果**：研究网关自建浏览器与模拟 Agent 共用真实 SQLite 的修订/指纹/幂等/审计后，过时 Web 表单与 Agent 请求均返回 HTTP 409，不覆盖最新值；两个 HTTP 并发仅一胜、故障注入能够回滚；Saltcorn 原生 Field.update 绕过网关后，网关能够以 OUT_OF_BAND_DRIFT 失败关闭。**但原生 Saltcorn 编辑器未接入这套网关，Agent 并非 LLM，仍不代表完整人机开发闭环。G1 未通过，合同 18 项完整任务依然 0/18。**

## 2026-11-21：S1 第一次真实 Saltcorn 原生 Trigger 执行冻结合同审批

- [研究报告 21：真正 Saltcorn Trigger 的金额阈值和两级审批执行](01-research/21-saltcorn-native-workflow-evidence.md)
- [35 项物理数据库/状态机/HTTP 验收证据摘要](01-research/workflow-observations.json)
- [可重复的原生 Pack、3 条 Code Action Trigger、冻结用例驱动和独立验证器](../experiments/platform-saltcorn/workflow/README.md)
- [GitHub Actions #44876882097](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44876882097)，completed/success，Artifact 14695849924

**实证结论**：12/12 金额边界（等于一百万不升级、超过升级）、12/12 状态迁移、3/3 连续普通/高额二级/驳回路径在真实 Saltcorn 表、Validate/Insert Trigger、审批记录和原生 List/REST 运行中得到物理验证。总 35/35 项测试符合预期。**限制**：角色是客户端可声明的业务字符串，没有真实身份授权/HTTP 403；amount_decimal SQL 类型为 TEXT，并非冻结 decimal(12,2)；动作事务由研究 CLI 显式 SQL 包裹；没有真实 LLM 或审批浏览器提交。冻结 18 项合同的完整通过仍为 0/18，**G1 继续 NOT_PASSED**。

## 2026-11-21：S1 Saltcorn 真实登录身份驱动的原生合同审批实验

- [实证报告 22：真正 Saltcorn 登录身份与原生审批 Trigger](01-research/22-native-identity-approval-evidence.md)
- [32 项机器可读 HTTP/SQLite 验收摘要](01-research/auth-approval-observations.json)
- [包含四用户登录、CSRF、身份伪造与业务数据验收的可复现源码](../experiments/platform-saltcorn/auth/README.md)
- [最终成功 GitHub Actions #44879041055](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44879041055)，**32/32 PASS，Artifact 14697420714**

**新突破**：四个真实 Saltcorn 用户各有独立 Session，通过当前会话 CSRF 令牌调用原生 /api/ 审批，Validate Trigger 用可信 user.id/email 确认用户与业务角色匹配；合法普通/超额两级审批及驳回真实落库，角色/用户 ID 伪造请求不能修改业务，直接修改合同/审批明细被原生表权限拒绝。**新反例**：带 Session Cookie 缺 CSRF 的请求可被重定向至首页，自动跟随重定向后看似 HTTP 200，却并没有业务更新；独立验收必须检查最终 URL、Content-Type、JSON 和物理 SQL。此研究只用固定邮箱→业务角色映射，Saltcorn 原生角色仍均为 80；HTTP 拒绝码为表级 401、业务级 400，**非冻结 TC04 规定的 403**；尚无真正浏览器审批表单、AI Agent 或生产 RBAC。**G1 仍未通过，完整合同任务 0/18。**

## 2026-11-21：S1 类型化 Agent 工具与可信执行层

- [报告 23：工具权限及真实 Saltcorn 运行证据](01-research/23-agent-tool-contract-evidence.md)
- [21 项安全单元 + 29 项真实集成的机器可读摘要](01-research/agent-tool-observations.json)
- [可复现的工具 Broker/独立验收与可选外部模型探针](../experiments/agent-tools/README.md)
- [GitHub Actions #44881082333](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44881082333)，completed/success，Artifact ID 14698057458。

**边界**：本轮 50 项独立断言通过，真实平台完成提交/一级/二级审批、阻止伪造/越权/过期/重复授权；调用由确定性测试控制器发起，**外部 LLM 推理没有运行**，人工确认也是可信测试宿主模拟。G1 尚未通过，冻结的 18 项完整合同任务仍为 0/18。

## 2026-11-21：S1 Agent 调用持久化防重放与故障未知结果实证

- [报告 24：进程重启、同 ID 重放、未知远端结果与持久审计](01-research/24-durable-agent-calls-evidence.md)
- [机器可读结论与原始 CI 信息](01-research/agent-tool-durability-observations.json)
- [Run #44881510363](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44881510363) completed/success，**29/29 安全/崩溃恢复单元 + 29/29 真实 Saltcorn 集成**，原始 Artifact 14698431130。已有工具测试 21 项，新加崩溃故障测试 8 项；真实平台审批链路仍为 29 项。

**边界**：持久化唯一 call_id 可以在同一 SQLite ledger 共享范围内拒绝进程重启后的重复执行；不保证不同调用 ID 的业务幂等，也不是 Broker/Saltcorn 双数据库的 exactly-once 事务。远端结果未知时须查真实业务数据，不得盲目重试审批。LLM 未推理，G1 仍未通过。

## 2026-11-21：S1 DeepSeek 真实选择配置 / 代码 / 混合开发路径

- [研究报告 26：真实 DeepSeek 选型与 Saltcorn 平台执行](01-research/26-deepseek-mode-route-evidence.md)
- [六项选择与两层 CI 结果 JSON](01-research/deepseek-mode-route-observations.json)
- [可复现六需求基准、固定原生能力与受限模型工具协议](../experiments/route-choice/README.md)
- [Actions #44884021495](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44884021495)：**真正 DeepSeek 1 次 Function Call，6/6 路由正确，Saltcorn 20/20 独立运行验证通过**；模型输入 876、输出 118、总计 994 Tokens。参照 [无模型平台预检 #44883844751](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44883844751) 同样 20/20，明确不将预检的 6/6 当作 AI 成果。

**严格边界**：模型只选择 CONFIG/CODE/HYBRID 枚举；Saltcorn 原生 Pack、字段和代码 Trigger 都是研究员预写，**没有 AI 自动生成代码/Schema 或人工—AI 双向编辑**。小样本单次成功不是泛化准确率证明。G1 NOT_PASSED，完整合同 18 项仍 0/18 PASS。

## 2026-11-21：S1 真实 DeepSeek × Saltcorn 原生浏览器人机交替编辑正向证据

- [报告 27：真实 Chromium → DeepSeek → 守卫式原生 Field.update → Chromium](01-research/27-real-deepseek-human-roundtrip-evidence.md)
- [机器可读 16 项实证结果与真实模型用量](01-research/deepseek-human-roundtrip-observations.json)
- [可运行的受限字段 Patch、浏览器操作与冲突负对照](../experiments/platform-saltcorn/collab/README.md)
- [最终真实模型 GitHub Actions #44885275152](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44885275152)：**8/8 单元 + 16/16 实际 Saltcorn/Chromium/LLM/SQLite/HTTP 验收**，仅 1 次 DeepSeek Function Calling，共 583 Tokens，Artifact ID 14699991457。另有 **零模型预检** [#44885046889](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44885046889)，同样 16/16，不能计为 AI 证据。

**已验证**：真实浏览器模拟人工先改 title，DeepSeek 从真实最新元数据提出 status-only Patch，可信执行器事务内检查旧快照并调用原生 Field.update，第二次浏览器编辑后 AI 字段不丢，旧 AI Patch 被拒。**未验证**：真实自然人手工授权、原生浏览器编辑路径的版本门禁、所有并发交错/插件写入、AI 自动建模/代码。S1 仍在进行，G1 NOT_PASSED，冻结 TC 完整 0/18。

## 2026-11-21：S1 综合研究、候选 ADR 与 G1 评审收口

- [综合深度研究与五平台架构比较](01-research/28-s1-synthesis-and-architecture-comparison.md)：对照 ToolJet、Appsmith、Budibase、NocoBase v3 与 Saltcorn，分别标识源码/官方文档/真实运行证据；整理可借鉴、不应直接复用和自主创新机制；比较全局 IR、分域 Schema+Manifest、原生系统外挂 Agent 三条路线。
- [ADR-S1-002：分域 Schema+Manifest 优先进行 S3 对照实验](01-research/28-adr-domain-schema-manifest.md)：仅选择后续优先验证路线，不冒充架构定稿。
- [G1 综合评审与条件性继续建议](01-research/29-g1-decision-review.md)：六类交付物逐项映射和五项 P0 阻断，明确 Gate Status **NOT_PASSED**、研究建议 **CONDITIONAL GO（只允许 S2 范围预研准备，不代表正式进入 S2）**。

**本轮没有新增 CI、外部模型调用或平台运行。** 前序真实证据的边界保持不变：模型路由 6/6、Saltcorn 20/20；真实 Chromium/DeepSeek 顺序编辑 8/8+16/16；原生 Web 编辑路径的 CAS 绕过风险未解除，完整合同冻结用例仍 0/18 FULL PASS。下一优先事项是全渠道强制治理写路径的可证伪设计和真实 PoC，不能通过增加文档绕过 G1。

## 2026-11-21：S1 G1-B01 全渠道强制写入机制的可证伪契约

- [统一写入命令/权限/CAS/幂等/漂移隔离/发布门禁规范](01-research/30-g1-b01-unified-write-contract.md)：逐一枚举 Saltcorn 原生浏览器、Field.update/CLI、Pack、Agent、插件和数据库维护路径；明确不能用仅限 Agent 的外部账本替代全渠道治理。
- [24 项独立验收场景与对照组](01-research/31-g1-b01-acceptance-matrix.md)：明确真实原生浏览器旧表单、真实 Plugin、真实两进程、跨应用、缓存热读回、远端未知结果和无模型人工模式的可证伪 PASS/FAIL 标准。
- [机器可读预注册用例基线](01-research/g1-b01-acceptance-cases.json)：W01—W24 全部标记 `NOT_RUN`，供后续 CI 在真实运行后生成独立 observations；不冒称已修复 Saltcorn 原生编辑器。

**严格限制**：本轮是设计规范与验收协议交付，**没有新增真正运行的全写入者 PoC 或 CI**，未使用 DeepSeek API。此前原生 Web stale-form 覆盖及直写漂移风险仍存在；G1-B01 **未关闭**，G1 继续 **NOT_PASSED**，冻结合同验收仍 **0/18 FULL PASS**。

 
## 2026-11-21：S1 G1-B01 C1 真正可执行的受控写入机制

- [C1 Python/SQLite/HTTP 可复现引擎与测试工程](../experiments/g1-b01-c1/README.md)：同一命令写入路径，服务端 CAS/revision/hash/幂等/审计，三类研究身份共用 HTTP 接口，真实双进程 SQLite 并发。
- [G1-B01 C1 真实 CI 研究报告 32](01-research/32-g1-b01-c1-real-ci-evidence.md)：[GitHub Actions #44886944054](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44886944054) **completed/success，31/31 unittest 执行实例通过**，18 个不同测试方法定义，Artifact [14699494263](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44886944054/artifacts/14699494263)，独立审查 PR #1 已合并。
- [离线工作流](../.github/workflows/s1-g1-b01-c1.yml)：无需 Saltcorn、Chromium 或 DeepSeek Key，避免额外 API 费用。

**限制**：C1 仅为自研独立服务，Browser/Plugin 仍为研究测试身份而非 Saltcorn 原生 UI/实际插件；旧原生编辑路径未治理。G1-B01 从“仅规范”发展为“独立 C1 验证”，但 **W01—W24 仍 0/24 完整 PASS；TC01—TC18 仍 0/18 完整 PASS；G1 NOT_PASSED**。


## 2026-11-21：S1 C2 真正 Saltcorn 原生编辑器 409 与旁路负对照

- [研究报告 33：真实 Chromium / Saltcorn 原生字段向导的带签名旧基线保护](01-research/33-g1-b01-c2-native-route-evidence.md)，[可运行 C2 工程](../experiments/g1-b01-c2/README.md)。
- [GitHub Actions #44887680474](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44887680474) **completed/success**；真实 Chromium 对改造后的 Saltcorn 原生字段向导执行 B 新保存、A 旧表单提交，A 收到 HTTP **409**，B 值未丢；新表单仍能继续编辑。浏览器正向证据 **8/8**。
- 同一个真实原生平台 [CLI Field.update 负对照](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44887680474)：**1/1** 危险绕过可发生；仅拦截 Web 路由无法实现全渠道强制保护。原始 Artifact [#14699859357](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44887680474/artifacts/14699859357)，实验 PR #2 已合并。
- **限制**：通过临时修改 Runner npm 编译路由实现的签名检查，不是 Saltcorn 官方支持的插件机制，更**不是原子 CAS**；模型、插件真实隔离和发布均未验收。冻结 G1-B01 W01—W24 仍 **0/24 FULL PASS**，完整合同 TC 仍 **0/18 FULL PASS**，G1 **NOT_PASSED**。


## 2026-11-21：S1 G1-B01 B1 真正人工设计器 + Agent/Plugin 统一命令入口

- [报告 34：真实 B1 Chromium + Agent/Plugin 子进程统一编辑证据](01-research/34-g1-b01-b1-browser-agent-plugin-evidence.md)；
  [源代码与运行说明](../experiments/g1-b01-c1/README.md)，[CI 工作流](../.github/workflows/s1-g1-b01-b1.yml)。
- [真实 GitHub Actions Run #44888692681](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44888692681) **completed/success**，**B1 18/18 独立端到端检查 PASS + C1 31/31 unittest 执行实例 PASS**；Job 136799528729，原始 [Artifact #14701406504](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44888692681/artifacts/14701406504)。
- [PR #3](https://github.com/zealzhangz/OpenAILCAP/pull/3) 已合并，主线提交 `a0eff9d11ce4c96a0fed8bb53aac8afa0364b82a`；另有 [独立 C1 回归运行 #44888692722](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44888692722) completed/success。
- 本轮在**自研最小 Web（不是 Saltcorn 原生）**的真实 Chromium 页面中验证多标签页旧版本 409；外部 Agent、Plugin 工具进程通过同一 C1 Store.apply 写入；Plugin 直接 HTTP 越权字段 403，两个独立 OS 进程竞争得到 [200,409]，真实 SQLite 最后 revision=5 / audit=5 / receipt=5，跨应用无串写。
- **边界**：Plugin 是受控 Manifest+Token 的实验进程，**没有真正沙箱**；Agent 无 LLM；Web 只编辑两个字段，非成熟低代码设计器；未强制治理 Saltcorn CLI、直接 DB 及发布路径。**G1-B01 仍 OPEN，W01—W24 0/24 FULL PASS，合同 TC01—TC18 0/18 FULL PASS，G1 NOT_PASSED**。


## 2026-11-21：S1 B2 领域 Schema + Manifest 真实业务运行闭环

- [研究报告 35：B2 DataModel / Form / View / Workflow / Manifest 实际运行证据](01-research/35-s1-b2-schema-runtime-manifest-evidence.md)，[可复现实验源码](../experiments/g1-b01-b2/README.md)，[CI 工作流](../.github/workflows/s1-b2-schema-runtime.yml)。
- [真实 GitHub Actions #44889712124](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44889712124) completed/success：**18/18 SQLite 模型单测 PASS + 27/27 真正 Chromium + 独立 Agent 子进程集成检查 PASS**，原始 [Artifact #14700803450](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44889712124/artifacts/14700803450)，Job 136802678273。
- [PR #4](https://github.com/zealzhangz/OpenAILCAP/pull/4) 已合并 main，SHA `3ed689c12ea2b466a25c0af6e38cb51bc8b4e2bf`。模型→表单→视图→审批 Workflow 四类真实资源经 app-level CAS、hash Manifest 与引用校验，Agent 旧草稿 409、人类旧标签页 409；真运行态数据完成 100000001 分二级和 100000000 分一级审批；v1/v2 不可变发布与回滚指针以及草稿 SQL 漂移隔离均有数据库/浏览器证据。
- **限制**：B2 是独立泛化机制实验，不直接复用 C1 Store.apply 代码；Agent 只是确定性工具而非大模型自主开发，界面只是 JSON Schema 编辑器；没有生产部署、插件沙箱和通用迁移。B2 27 项与冻结 W01—W24 不同口径。**S1/G1 NOT_PASSED，W01—W24 0/24 FULL PASS，合同 TC01—TC18 0/18 FULL PASS**。
