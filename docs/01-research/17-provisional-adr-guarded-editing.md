# 研究候选 ADR-S1-001：低代码资源的 Agent 写入接口不得使用无保护的全量恢复

- 状态：**S1 研究阶段候选决策（Provisional）；尚非 S3 正式架构/技术栈选型**
- 日期：2026-11-21
- 关联假设：H01、H03、H07、H08
- 关联事实：[Saltcorn 原生全量 Pack 真实覆盖实证](16-saltcorn-roundtrip-evidence.md)、[Saltcorn 真实合同 Pack 运行](15-native-contract-platform-evidence.md)、[SQLite 治理式变更实验](../../experiments/sqlite-roundtrip/README.md)

## 决策问题

OpenAILCAP 必须同时允许人工编辑、AI 通过配置工具修改、AI 创建代码工件，且多轮开发会话可能持有不同时间点的资源版本。是否应将开源平台的“应用整体导入/配置恢复接口”直接暴露给 Agent 作为默认写入工具？

**本阶段建议：不应。** 该结论与是否采用统一 Application IR 是两个相互独立的问题：即使资源模型统一，未经版本检查的全量覆盖同样不安全。

## 候选方案与实际证据

| 方案 | 主要代价 | 实际证据与判断 |
|---|---|---|
| A. Agent 将整个应用或 Pack 导回平台 | 简单；易于复用备份/迁移工具；所有附带旧字段都可能被重新写入 | 真实 Saltcorn 阶段 B 证实两处无关标签被还原。**排除作为默认 Agent 写入方式** |
| B. Agent 调用窄作用域的原生模型更新接口 | 一次只处理指定字段，初期复杂度较低；并发同字段仍可能竞争 | 真实 Saltcorn 阶段 A 证实顺序非冲突变更能够保留；但未验证并发或事务，**只能继续研究** |
| C. 可信领域命令 API + 原子 CAS / expectedRevision + 幂等 + 审计 + 引用检查 | 需要建设版本快照、变更历史、事务和兼容迁移；可治理人工/Agent 统一读写 | 自研真实 SQLite 实验 23/23 通过，Saltcorn 阶段 C 的非原子预检查展示失败时拒绝的意图，但尚无第三方真实编辑器接入和攻击验证。**目前优先验证该方向** |
| D. 全局事件日志或 OT/CRDT 多端实时合并 | 更适合高并发共同编辑，但同步协议、异常和跨资源业务规则复杂 | 没有足够同场景实证证明其优于 C；**不作为 MVP 的默认复杂度** |

## 最小建议命令契约（草案，未部署）

~~~json
{
  "applicationId": "app-A",
  "resourceId": "ui.contract.form",
  "changeId": "uuid-idempotency-key",
  "baseRevision": 28,
  "baseFingerprint": "sha256-of-server-snapshot",
  "operations": [
    {"op": "replace", "path": "/properties/submitButton/label", "value": "送审"}
  ],
  "dryRun": true
}
~~~

调用者身份来自可信认证会话或签发的 Agent 工具委托，**绝不从上述 JSON 任意 actor 字符串获得授权**。服务端必须从主体、应用、资源和操作类型四个维度授权，校验 Schema、引用、跨版本依赖和字段可写策略。

## 必须满足的安全与一致性契约

1. 同事务：检查当前 revision/内容指纹、应用级权限范围与变更基线，并提交资源内容、新 revision、幂等回执、审计记录；不能先“查询当前值”再无条件异步更新。
2. 限域：提交 payload 只包含资源/字段的意图 Patch，禁止将未提及资产当作默认同步目标。完整替换必须明示“replace-all”范围、影响评估和审批。
3. 交错：非冲突字段改变可通过三方比较合并；同字段冲突给机器可读取的冲突列表，返回显式 409，不得默认丢弃人工变更。
4. 代码：代码工件绑定源版本/哈希；Agent 变更源码必须走 Git/受限工作区与构建/测试审查，不得以低代码资产的整体导入暗中重置人工代码。
5. 失败：引用缺失、部分变更失败、外部数据库异常或运行时构建未通过时不能把半成品标记为已发布。配置草稿事务与生产部署事务的职责必须独立。
6. 权限：高权限 Pack 恢复、运行 Shell/JS、接触第三方凭据均不应直接授权给自然语言 Agent；需要代理能力和最小权限。
7. 可观测：记录 request/expectedRevision/实际 revision/受影响资源/冲突/回滚/测试证据，防泄漏采样。
8. 手工继续：在模型服务断开时，人工可用同一契约编辑并预览；模型恢复后通过服务器最新快照重新同步。

## 原始实证不支持的结论

- **不能据此选择统一 IR 或领域 Schema**：上轮两种内存模型各自通过核心场景，真实 Saltcorn 编辑反例属于“写入协议”而非“资源表示能力”的比较。
- **不能据此宣称 Saltcorn 可视编辑器有缺陷**：被验证的是管理员 Pack 导入和脚本化 Field.update。
- **不能宣称 C 已在真实 Saltcorn 中生产验证**：Saltcorn 阶段 C 只是非原子应用侧检查；本仓库 SQLite CAS 实验也没有完整会话鉴权和实际插件/编辑器集成。
- **不能将 18/18 的断言符合预期解释为 H03 成功**：B 路径恰是无保护全量配置的失败行为。

## 推动候选 ADR 成为正式决策的门槛

- 真实浏览器编辑器手动修改一次，并通过 HTTP 真实平台服务端 API 读出正确 revision 和资源内容。
- Agent 持有旧 base，对真实服务端尝试精确 Patch；同字段冲突 100% 明确拒绝，非冲突变更无损，至少包含人工代码资产。
- 使用不同连接/进程对同一资源真正同时修改，并在物理数据库事务层验证无静默覆盖。
- 原始协议接口有认证、应用隔离、命令权限、审计、幂等、失败回退的独立测试与故障注入。
- 同样合同业务分别以统一 IR 与分域 Schema 实现，比较引用更新、版本迁移成本和完整性；形成最终架构 ADR。

目前状态：**排除风险路径 A；保留 C 作为优先验证方案，而非已经完成的选型**。

## 2026-11-21 真实并发与绕过治理负例后的候选 ADR 更新

[GitHub Actions 实证 #44872093657](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44872093657) 将证据从单进程模拟提升到真正两个独立 Saltcorn CLI 进程：显式 SQLite 事务内比较资源版本与原生 Field.update 可使同资源一胜一拒，故障注入回滚有效。**但是**：Saltcorn SQLite withTransaction 包装本身没有 SQL 事务（先前代码无法作原子性依据）；人工通过 native Field.update 绕过实验版本表后，Agent CAS 即使“原子正确”也会覆盖人工内容。

**决策候选约束进一步收紧**：不接受“人工设计器继续原生写库，只有 Agent 工具通过 CAS sidecar”的过渡方案。应统一所有写入口，或者在 Agent 发布前完成经授权的外部版本采纳+内容指纹一致性检查并失败关闭；否则中止 AI 自动提交。这只是候选 ADR 修订，不等于最终决定元数据 IR 或技术栈。完整原始记录见 [报告 18](18-saltcorn-sqlite-atomic-evidence.md)。

## 2026-11-21 ADR-S1-001 依据真实 Web 两标签页继续收紧

[Saltcorn Chromium 实际编辑证据](19-real-browser-edit-evidence.md)（[Run #44873882208](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44873882208)）：本次首次采用真正的管理员浏览器页面而不是 CLI 模拟人工。两标签页打开同一旧 title 编辑向导，B 正常保存后 A 持旧表单提交，数据库静默变成 A 的值；模拟 Agent 仅维护自己的版本账本，仍按旧 revision=0 接受写入并再次覆盖人工值。

**候选 ADR 的技术结论提升为必须满足的强约束**：统一受治理写入并非仅 AI Agent 侧的功能。真实 Web 设计器必须以相同 revision/指纹令牌提交变更，并在服务端通过原子事务校验；对于旧版本即使是管理员，也需返回明确冲突，而非仅检查角色与 CSRF。已验证 Saltcorn 字段编辑路由有真实权限与 CSRF，但不能把它们误认为并发一致性机制。该 ADR 仍是 S1 候选，**不是已经建成的 OpenAILCAP 统一写入 API**。还需通过带真实登录会话的安全版 API、插件路径与开发 Agent 的独立验收后才能决策。

## 2026-11-21 ADR-S1-001 正向机制补充

最新 [真实 HTTP 治理研究](20-governed-http-evidence.md)、[Actions #44874668928](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44874668928)：一个**仅限研究网关自己的浏览器和模拟 Agent 客户端**的统一原子版本/指纹写入协议，已完成旧 Web/Agent 409、非冲突保留、独立并发一胜一拒、幂等审计、事务回滚，22/22。原生 Saltcorn Field.update 仍可绕开网关，但外部指纹漂移可触发网关 409 失败关闭，4/4。

**候选 ADR 判断不变，但已有正向可复现性证据**：优先验证共享领域命令与事务性版本控制，不允许将实验 direct SQL 写 Saltcorn _sc_fields 的办法作为生产实现。正式接入必须在 Saltcorn/候选内核的受支持扩展点完成缓存/钩子/Schema 一致性，并纳入真实原生 Web、Agent 与插件全部写入口；G1 和正式 ADR 选型仍待完成。
