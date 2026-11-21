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
