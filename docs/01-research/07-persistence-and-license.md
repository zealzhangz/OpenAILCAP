# S1 深入研究：真实持久化链、Agent 执行隔离与许可证风险

研究日期：2026-11-21。状态：源码静态审查 + OpenAILCAP 自研 SQLite 可执行实验。**不是 ToolJet/NocoBase 真实平台部署。G1 尚未通过。**

## 一、对 OpenAILCAP 架构决策有实际影响的发现

1. **ToolJet 社区版 Code Mode 服务端存在证据断点**：公开 CE Controller 是没有路由的 stub；CE Service 显式拒绝非 visual 的 buildMode。真正实现由仓库的 server/ee 子模块提供，本次未能读取 EE 代码。不能仅凭 ToolJet MCP 已具有 AI 编辑工具就宣称 CE 有完整 AI 代码部署能力。
2. **ToolJet 常规 AppVersion 确实有基于 TypeORM 的持久化机制**：VersionRepository.createOne 通过 dbTransactionWrap 保存 AppVersion；但“版本持久化”不等于“Code Mode 源码存储、合并与发布”，需分别追踪。
3. **NocoBase 的插件声明和 Agent Runner 本地策略值得参考，但其隔离边界不能直接照搬**：确定性构建步骤的默认模式为 none，可选以其他用户运行，container 模式当前被拒绝；Agent 编码工具使用自己的适配器沙箱，属于另一个验证链。
4. **NocoBase v3 的许可证附加条款可能直接阻断作为 OpenAILCAP 平台内核的代码复用**：虽然社区版引用 Apache-2.0，但许可证有额外的品牌保留、平台 SaaS/PaaS 提供及再分发限制，和本项目的 AI 平台型产品定位有潜在冲突。
5. **本仓库真正执行了一个基于 SQLite 文件的数据库实验**：23/23 测试通过，覆盖真实 SQL 事务、重启、并发、错误引用、异常退出及按 app_id 分隔的测试 ACL。它仍不能证明生产级授权、AI 安全或低代码运行时正确。

## 二、ToolJet：公开源码可证到哪里？

固定版本：[ToolJet/ToolJet @ d2f09ed9ab6c6cf289abfc8aa7ee77c1264aaeb0](https://github.com/ToolJet/ToolJet/tree/d2f09ed9ab6c6cf289abfc8aa7ee77c1264aaeb0)。

| 原始位置 | 本次证实的事实 | 不得推断 |
|---|---|---|
| [Code Mode Controller](https://github.com/ToolJet/ToolJet/blob/d2f09ed9ab6c6cf289abfc8aa7ee77c1264aaeb0/server/src/modules/code-mode-source/controller.ts) | 注释写明 CE stub，无实际业务路由 | 社区版已完整支持 Code Mode API |
| [Code Mode Service](https://github.com/ToolJet/ToolJet/blob/d2f09ed9ab6c6cf289abfc8aa7ee77c1264aaeb0/server/src/modules/code-mode-source/service.ts) | 非 visual buildMode 被拒绝；部分发布/版本钩子为空操作 | Code Mode 服务端存储和回滚已公开、已验证 |
| [CLI Controller](https://github.com/ToolJet/ToolJet/blob/d2f09ed9ab6c6cf289abfc8aa7ee77c1264aaeb0/server/src/modules/code-mode-source/cli.controller.ts) | 注释明确 CLI 下载位于 EE | CE 自带相同下载接口 |
| [server/ee 子模块](https://github.com/ToolJet/ToolJet/tree/d2f09ed9ab6c6cf289abfc8aa7ee77c1264aaeb0/server/ee) | Contents API 显示 type=submodule，指向 ToolJet/ee-server，固定指针 519dec4675ee65ec482a559a88019ffc34144d56 | 该子模块可公开获取或可以任意商用 |
| [VersionRepository](https://github.com/ToolJet/ToolJet/blob/d2f09ed9ab6c6cf289abfc8aa7ee77c1264aaeb0/server/src/modules/versions/repository.ts) | 常规版本使用 dbTransactionWrap + EntityManager.save(AppVersion)，查询约束 appId | Code Mode 的源码保存机制等同于普通 AppVersion |
| [VersionService](https://github.com/ToolJet/ToolJet/blob/d2f09ed9ab6c6cf289abfc8aa7ee77c1264aaeb0/server/src/modules/versions/service.ts) | 存在 CodeModeSourceService 注入与 EE 版本历史 Hook 的扩展点 | 所有 EE 历史功能已在 CE 实现 |
| [app-data-revision](https://github.com/ToolJet/ToolJet/blob/d2f09ed9ab6c6cf289abfc8aa7ee77c1264aaeb0/server/src/modules/apps/app-data-revision.ts) | 发布 Viewer 的缓存指纹包含版本、权限、迁移 epoch 与许可证条件 | 此哈希是编辑并发控制的 CAS 令牌 |

另外，ToolJet MCP 的 [Code App 工具](https://github.com/ToolJet/tooljet-mcp/blob/8a178ad34f6e3326b6957503ca4ed4f555d23096/src/tools/codeApp.ts) 的 AI 文件变更链，已在 [上一份研究报告](04-tooljet-sync-trace.md) 定位到 source-pull、readHashes 与 write-preflight。当前完整数据流应表述为：

~~~mermaid
flowchart LR
    A[人工 Code Panel] --> B[EE 服务端源码持久化 未取得源码]
    B -.CLI 同步.-> C[ToolJet MCP source-pull]
    D[Agent] --> E[MCP 读取/哈希/增量修改]
    C --> E
    E --> F[MCP 写前检查/构建/安装]
    F -.EE 侧接口.-> B
    G[CE 常规版本接口] --> H[TypeORM AppVersion 持久化]
    B -.不可直接等同.-> H
~~~

**阶段性判断**：ToolJet 是机器可调用能力与人机变更保护的有价值参考，但其 EE 子模块的不可审查状态是关键架构复用阻断点。下一步若要复现 Code Mode 必须先核实其实际部署版的许可和可测条件。

## 三、NocoBase：插件/Agent Runner 的真实边界

固定版本：[nocobase/nocobase @ 0894734040c3d30d4f4f3d7a6da98ae22f365f80](https://github.com/nocobase/nocobase/tree/0894734040c3d30d4f4f3d7a6da98ae22f365f80)，默认分支 v3。

| 源码证据 | 确定事实 | 对 OpenAILCAP 的启示 |
|---|---|---|
| [插件 define.ts](https://github.com/nocobase/nocobase/blob/0894734040c3d30d4f4f3d7a6da98ae22f365f80/packages/app/app-server/src/plugins/define.ts) | Scoped package name、baseDir、service providers、routes、DB 等插件声明和校验 | 插件 Manifest 有参考价值，但要自己验证工具授权、动态发现和插件故障隔离 |
| [实际 agents plugin.ts](https://github.com/nocobase/nocobase/blob/0894734040c3d30d4f4f3d7a6da98ae22f365f80/packages/plugins/app-plugin-agents/server/plugin.ts) | 注册服务、路由、迁移、seed 和任务队列 | 插件实际按声明贡献能力，不等于 Agent 无条件能使用 |
| [Runner local-policy.ts](https://github.com/nocobase/nocobase/blob/0894734040c3d30d4f4f3d7a6da98ae22f365f80/packages/app/agent-runner/src/core/local-policy.ts) | 宿主可限制 agent、subject、repo、build、app；缺省无隔离为 none；坏配置采取拒绝策略 | 授权/调度策略必须与系统执行隔离分开验收 |
| [Runner isolation.ts](https://github.com/nocobase/nocobase/blob/0894734040c3d30d4f4f3d7a6da98ae22f365f80/packages/app/agent-runner/src/core/isolation.ts) | 仅针对确定性步骤：none / user；container 当前不支持 | 不能把选中 user 的策略称为全套容器隔离；Agent 编码沙箱由适配器另行负责 |
| [Runner credentials.ts](https://github.com/nocobase/nocobase/blob/0894734040c3d30d4f4f3d7a6da98ae22f365f80/packages/app/agent-runner/src/agent/credentials.ts) | 限制凭据文件路径；目录 0700、文件 0600，提供清理 | 需要恶意路径、符号链接、异常恢复与工作区串扰测试 |
| [local-policy.test.ts](https://github.com/nocobase/nocobase/blob/0894734040c3d30d4f4f3d7a6da98ae22f365f80/packages/app/agent-runner/tests/local-policy.test.ts) | 存在 local-policy 和隔离策略的单测 | 仅有测试源码，尚未由本研究实际运行 |

本次只静态阅读，未执行 NocoBase 测试。

## 四、许可证：阻断级的复用风险

本段为**阅读许可证后的风险提示，不是法律意见**。复用或商业发行前需结合产品交付模式取得专业法律结论。

- [ToolJet 根目录 LICENSE](https://github.com/ToolJet/ToolJet/blob/d2f09ed9ab6c6cf289abfc8aa7ee77c1264aaeb0/LICENSE)：GNU AGPL-3.0。若修改或集成其代码提供网络服务，须评估强 copyleft 和源码提供义务；EE 子模块另需核查。
- [NocoBase v3 LICENSE.txt](https://github.com/nocobase/nocobase/blob/0894734040c3d30d4f4f3d7a6da98ae22f365f80/LICENSE.txt)（文档更新日期 2026-11-16）：第 4.2 条规定社区版使用 Apache-2.0 **及额外条款，并声明发生冲突时附加条款优先**；第 5.2 条要求保留指定品牌声明；第 5.4 条禁止基于原始/修改软件向公众提供 AI 应用开发平台 SaaS/PaaS；第 5.5 条对部分商用版等价扩展的公开发布有限制；第 7.3—7.5 条还限制商业授权下的平台再分发/公开提供。可阅读其 [LICENSE-APACHE.txt](https://github.com/nocobase/nocobase/blob/0894734040c3d30d4f4f3d7a6da98ae22f365f80/LICENSE-APACHE.txt)，但不能用单独 Apache 文本覆盖前述补充条件。

**OpenAILCAP 的实际措施**：本阶段只借鉴接口边界、插件贡献及运行器权限设计**思想**，不把 NocoBase v3 代码复制进 OpenAILCAP 平台，也不在未核实授权前采用其代码作为自研 AI 开发平台内核。许可证限制与项目定位存在直接冲突，优先级高于技术栈喜好。

## 五、本项目实际运行的 SQLite Spike

完整源码及复现步骤：[experiments/sqlite-roundtrip](../../experiments/sqlite-roundtrip/README.md)。本次在 Python 3.13.5 / SQLite 3.46.1 / Linux x86_64 上运行；23/23 单元测试通过，[结果 JSON](../../experiments/sqlite-roundtrip/results.json) 和 [原始测试输出](../../experiments/sqlite-roundtrip/test-output.txt) 一同提交。

| 验证对象 | 本项目本地结果 |
|---|---|
| 真实文件数据库关闭/重启后版本状态 | PASS |
| 两个 SQLite 连接并发同字段冲突、异字段合并 | PASS |
| 单事务内 SQL 写入后模拟失败以及子进程提交前异常退出 | PASS |
| app_id 复合主键和模拟 ACL 拒绝跨应用、只读写入 | PASS（只证明受信调用者前提下的逻辑） |
| 相同 revision 的物理数据漂移、幂等重放时的错误成功 | FAIL CLOSED（按预期拒绝） |
| 引用关系、源代码保留、插件未知字段、回滚和幂等 | PASS |
| 所有独立测试 | **23/23 PASS** |

实验首轮发现 Python ResourceWarning，之后调整数据库连接生命周期和读取事务，再运行 23/23，ResourceWarning 为 0；增加了“已损坏状态不可凭旧幂等回执声称成功”的防御测试。

**绝不能夸大**：actor 当前是被调用方信任的字符串，不是真实用户认证。SQLite ACL 测试不等价于对恶意租户的生产隔离；没有低代码运行时、AI 工具调用、真正的插件执行、数据库 schema 迁移或生产环境部署。

## 六、风险登记与实际下一步

| 编号 | 风险等级 | 发现 | 下一动作 |
|---|---|---|---|
| R-01 | 高 | ToolJet Code Mode EE 服务端实现不可审阅 | 查可公开部署的 Visual 路径，确认 EE 授权后才尝试 Code Mode |
| R-02 | **阻断代码复用** | NocoBase v3 补充许可限制平台型产品 | 法律核查前仅研究思想、不直接复制集成其实现 |
| R-03 | 高 | Runner 默认 none 且 container 不支持确定性步骤 | 安全模型明确分离调度授权/构建隔离/Agent 适配器/部署授权 |
| R-04 | **阻断上线** | 本项目测试 actor 可被调用者伪造 | 下一次设计可信身份验证与会话作用域，不把 Python Store 直接开放为 API |
| R-05 | 中高 | 外部绕过 API 变更导致数据库拒绝继续 | 统一编辑 API；历史数据迁移建立受控版本采纳与审计 |
| R-06 | 高 | IR vs 分域模型在真实低代码环境未比较 | 补数据库迁移、插件升级及平台级编辑测试后形成 ADR |

**G1 决策**：已有第三方一手源码和本仓库的可复现实验，但仍缺真实低代码平台复现、真实数据与运行时端到端调用链和完整许可审查。本轮不宣称 G1/G3 通过。
