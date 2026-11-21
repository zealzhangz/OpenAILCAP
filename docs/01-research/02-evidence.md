# 源码一手证据台账（2026-11-21）

这些证据是本次通过 GitHub 连接读取到的**静态源码与仓库文档**，不是实际运行验证。完整结果须在后续阶段加上运行环境、命令及原始日志。

| 代码库 | 默认分支 | 固定 Commit |
|---|---|---|
| NocoBase | v3 | 0894734040c3d30d4f4f3d7a6da98ae22f365f80 |
| ToolJet MCP | main | 8a178ad34f6e3326b6957503ca4ed4f555d23096 |
| Appsmith | release | 0a6f6934fb33c06ee0a132c5baba78e006611621 |
| Budibase | master | 724cb529d7b32fde84ae537e4b44673cf0618dad |
| Meta Astryx | main | 35bda7f8f11c2c0b076ba07f24bb171207ce85e3 |

## E01 — 受限结构化应用计划

[ToolJet MCP appPlanSchema.ts](https://github.com/ToolJet/tooljet-mcp/blob/8a178ad34f6e3326b6957503ca4ed4f555d23096/src/appPlanSchema.ts)：可见表、查询、页面、事件、生命周期以及原位更新等字段，页面替换标注非原子性。**可证明**：存在受约束的计划 Schema。**不能证明**：完整通用 Application IR。

## E02 — 计划校验及对象引用解析

[ToolJet MCP applyAppPhase.ts](https://github.com/ToolJet/tooljet-mcp/blob/8a178ad34f6e3326b6957503ca4ed4f555d23096/src/tools/applyAppPhase.ts)：源码导入 lint、plan、diff、readback、ref 解析；rename 逻辑先校验再 apply。**不能证明**所有写入链路均已具备强事务或高质量验收。

## E03 — 人工修改可能被旧 Agent 快照覆盖

[ToolJet MCP codeAppSync.test.ts](https://github.com/ToolJet/tooljet-mcp/blob/8a178ad34f6e3326b6957503ca4ed4f555d23096/tests/codeAppSync.test.ts)：测试明确描述人工改 Style inspector 后 Agent 用旧代码修改按钮的冲突，以及 revision 相同但内容不同场景。应以此研究双向同步指纹与三方合并。**本次未执行该测试**。

## E04 — 执行器环境白名单与工作区

[ToolJet MCP codeAppIsolation.test.ts](https://github.com/ToolJet/tooljet-mcp/blob/8a178ad34f6e3326b6957503ca4ed4f555d23096/tests/codeAppIsolation.test.ts)：测试涵盖并发工作区、凭据作用域、敏感环境变量隔离。**不能证明**容器/内核沙箱完全安全。

## E05 — 插件体系的有边界定义

[NocoBase define.ts](https://github.com/nocobase/nocobase/blob/0894734040c3d30d4f4f3d7a6da98ae22f365f80/packages/app/app-server/src/plugins/define.ts) 与 [resolve.ts](https://github.com/nocobase/nocobase/blob/0894734040c3d30d4f4f3d7a6da98ae22f365f80/packages/app/app-server/src/plugins/resolve.ts)：插件有 scoped package name、service providers、路由、数据库迁移贡献；明确了插件声明与资源加载责任。**不能证明**插件被 AI 自动安全调用。

## E06 — Agent 执行器与业务系统解耦

[NocoBase agent-runner README](https://github.com/nocobase/nocobase/blob/0894734040c3d30d4f4f3d7a6da98ae22f365f80/packages/app/agent-runner/README.md)：官方源码仓库文档描述 Runner 注册、工作目录、应用 CLI、任务领取和 Agent 执行。这是**官方文档级证据（S2）**，仍需阅读 Runner 的权限和安全实现。

## E07 — 组件按类型注册与动态加载

[Appsmith widget registry](https://github.com/appsmithorg/appsmith/blob/0a6f6934fb33c06ee0a132c5baba78e006611621/app/client/src/widgets/registry.ts)：按 widget type 注册 loader，动态加载并缓存。不能据此证明 AI 可访问组件能力 Schema。

## E08 — 数据绑定与组件引用

[Budibase builder dataBinding.ts](https://github.com/Budibase/budibase/blob/724cb529d7b32fde84ae537e4b44673cf0618dad/packages/builder/src/dataBinding.ts)：涉及组件、上下文、表、角色、屏幕和 JS binding。强烈提示“引用完整性”应纳入 IR/Manifest 验证。

## E09 — Astryx 真实定位

[Meta Astryx core README](https://github.com/meta/astryx/blob/35bda7f8f11c2c0b076ba07f24bb171207ce85e3/packages/core/README.md)：Core 为 React UI 组件及主题，CLI 提供组件文档与模板，文档明确 React 19+ 依赖；它不是现成完整低代码设计器。

## 证据边界和后续行动

本次未部署或运行上述第三方项目；未逐文件核查许可证；缺乏编译日志、测试报告、业务场景复现。**已验证假设数 0/8，G1 未通过。** 后续必须补齐源码调用链、官方许可、可复现实测及独立断言。

## E10 — ToolJet MCP Code mode 实际调用链进一步追踪（静态）

固定版本 [src/tools/codeApp.ts](https://github.com/ToolJet/tooljet-mcp/blob/8a178ad34f6e3326b6957503ca4ed4f555d23096/src/tools/codeApp.ts) 中，约第 713 行 syncEditorEdits 调用 CLI source-pull；约第 1006—1030 行读取文件及更新 readHashes；约第 1074—1114 行写入前重新同步并检查文件哈希及文本修改定位，冲突则拒绝。证据等级仍为 S1，不代表已运行第三方测试。详细解读见 [ToolJet 调用链](04-tooljet-sync-trace.md)。

## E11 — OpenAILCAP 自主模型级实测（S0，但范围受限）

运行了 [内存模拟对照实验](../../experiments/roundtrip/README.md)，A/B 各 10/10 场景通过，28 项单元测试通过；[机器可读结果](../../experiments/roundtrip/results.json)。实验证明的是本仓库**模拟模型**，不是 ToolJet/NocoBase 运行时，也不是实际 AI Agent。见 [实验报告](05-roundtrip-results.md)。

## E12 — ToolJet CE/EE Code Mode 证据断点（S1）

[Code Mode CE Controller](https://github.com/ToolJet/ToolJet/blob/d2f09ed9ab6c6cf289abfc8aa7ee77c1264aaeb0/server/src/modules/code-mode-source/controller.ts) 无真实路由；[CE Service](https://github.com/ToolJet/ToolJet/blob/d2f09ed9ab6c6cf289abfc8aa7ee77c1264aaeb0/server/src/modules/code-mode-source/service.ts) 对非 visual buildMode 拒绝。server/ee 在固定 commit 是指向 ToolJet/ee-server 的子模块，未能获取其完整源码。因此不得宣称公开 CE 包含 Code Mode 闭环。

## E13 — NocoBase Runner 隔离策略和许可证（S1）

[runner isolation.ts](https://github.com/nocobase/nocobase/blob/0894734040c3d30d4f4f3d7a6da98ae22f365f80/packages/app/agent-runner/src/core/isolation.ts) 明确仅对确定性构建步骤进行 none/user 隔离，container 暂不支持；Agent 编码沙箱由适配器负责。[LICENSE.txt](https://github.com/nocobase/nocobase/blob/0894734040c3d30d4f4f3d7a6da98ae22f365f80/LICENSE.txt) 第 4.2、5.4 与 7.3—7.5 条存在平台型产品的额外限制，不能仅用 Apache-2.0 摘要作为复用依据。

## E14 — OpenAILCAP SQLite 文件数据库试验（S0，范围受限）

[实验代码与 23 项测试](../../experiments/sqlite-roundtrip/README.md) 在 Python 3.13.5 / SQLite 3.46.1 实际运行，文件持久化、事务回滚、另起进程不提交退出、模拟 A/B 应用分区等 23/23 通过。[结果 JSON](../../experiments/sqlite-roundtrip/results.json) 与 [原始测试日志](../../experiments/sqlite-roundtrip/test-output.txt) 同库保存。没有真正鉴权、平台运行时和 AI Agent；不得把逻辑隔离测试误认为生产安全验证。详见 [深度报告](07-persistence-and-license.md)。
