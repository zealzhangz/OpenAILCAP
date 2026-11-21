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
