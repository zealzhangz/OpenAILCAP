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
