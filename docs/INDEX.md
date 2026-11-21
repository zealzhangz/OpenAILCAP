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
