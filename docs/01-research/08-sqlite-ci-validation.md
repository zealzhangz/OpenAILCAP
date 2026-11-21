# S1 SQLite 持久化实验：GitHub Actions 独立执行验收

**执行日期**：2026-11-21。**结果：GitHub CI 已成功，限定为 SQLite 模型级实验。**

## 1. 真实运行记录

- 源码版本：[9fa2a2ca6cbd602758492e2a7e3f59310211c9b9](https://github.com/zealzhangz/OpenAILCAP/commit/9fa2a2ca6cbd602758492e2a7e3f59310211c9b9)。
- Workflow：[S1 SQLite Persistence Spike](https://github.com/zealzhangz/OpenAILCAP/blob/9fa2a2ca6cbd602758492e2a7e3f59310211c9b9/.github/workflows/stage1-sqlite.yml)。
- [GitHub Actions Run #44867849367](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44867849367)：completed / success。
- Job：[sqlite-tests #136735451358](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44867849367/job/136735451358)：success。
- GitHub 返回开始：2026-11-21 04:48:08Z，完成更新：04:48:17Z。
- 已验证成功的步骤：Checkout、Python 3.13 Setup、Execute SQLite and multiprocessing regression cases、Generate independent machine-readable results、Upload Artifact。
- Artifact：sqlite-roundtrip-results，GitHub Artifact ID 14691868974，文件存在、未过期（随 GitHub 保留期清理）。

## 2. 证据等级与限制

- 本地：Python 3.13.5、SQLite 3.46.1，23/23 测试通过；日志和每项用例结果与代码一同提交。见 [结果 JSON](../../experiments/sqlite-roundtrip/results.json)、[原始日志](../../experiments/sqlite-roundtrip/test-output.txt)。
- CI：GitHub 官方 API 确认同一源码提交的工作流状态为 success，测试执行及报告上传步骤也均成功；这是与本地机器不同的独立运行环境证据。
- 测试涵盖 SQLite 文件持久化、数据库关闭后重新读取、独立连接并发、进程未提交退出、事务回滚、模拟 app_id/ACL 的拒绝逻辑。

**不允许扩大的结论**：此成功与 ToolJet/NocoBase 真实部署、AI 代码开发、安全认证、生产多租户隔离、完整应用运行时、G3 PoC 都不是一回事。测试的 actor 由受信任调用方假设提供，仍未建立对恶意调用者的身份认证。

## 3. G1 决策

增加了 SQLite 持久化机制的可复现和失败注入证据，但真实第三方平台安装验证、服务端调用链及全部许可评审仍不完备，**G1 未通过**。下一步优先是基于真正可运行、许可允许的低代码平台/组件验证编辑持久化路径，并补独立身份认证测试。
