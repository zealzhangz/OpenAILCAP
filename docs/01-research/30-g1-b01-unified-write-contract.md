# G1-B01 — 全渠道强制写入契约与原生入口覆盖设计（研究规范 v0.1）

- 状态：**SPECIFIED / NOT IMPLEMENTED / NOT VERIFIED**
- 阶段：S1 假设 H01/H03/H05/H07/H08 的下一步验证输入；不可等同已修复 Saltcorn 原生编辑器
- 一手事实：[原生浏览器覆盖](19-real-browser-edit-evidence.md)、[研究网关 409/漂移](20-governed-http-evidence.md)、[真实 DeepSeek 顺序协作](27-real-deepseek-human-roundtrip-evidence.md)
- 提交目的：将 G1-B01 从宽泛风险转成**接口契约、写路径枚举、失败封闭规则、可自动判定的验收条件**；不引入新的模型费用

## 1. 必须保持的不变量

I01 **唯一事实源**：资源存在且只属于一个 applicationId；资源 ID 不得通过来自模型/客户端的任意 tenantId 决定授权范围。

I02 **所有可变更入口强制受治理**：人工浏览器、Agent Broker、插件 API、CLI、应用导入、迁移脚本和发布接口中，任何可修改正式资源的路径必须被拦截或明确禁止。只对 Agent 做 CAS 无效。

I03 **事务性比较和交换**：同资源的 expectedRevision + baseContentHash 必须同存储事务里与当前持久化内容比较；提交内容、新 revision、幂等结果、审计的存储边界必须一致。不同应用/资源有隔离的版本命名空间。

I04 **精确变更**：默认只接受有限操作集，明确资源 ID/字段 path；从旧 Pack 全量覆盖不可通过“局部更新”入口。全量迁移必须另设高权限事务+差异审查。

I05 **旧编辑不能静默成功**：同字段过时提交应返回 `409 VERSION_CONFLICT`；可自动三方合并的非冲突字段，必须在锁内比较 base/current/proposal 后产生新版本，不能绕过审计或引用校验。

I06 **外部写入漂移**：观察到正式资源内容与权威 ledger 指纹不一致时，必须将资源标记 `QUARANTINED`，拒绝所有自动写入和发布；人工管理员应在明确读取实际状态、审计差异和重新基线化后才可解禁。不能仅靠普通 GET 时偶然发现漂移；发布之前必须重新做全量闭包验证。漂移**不是**“自动提高 revision 即可继续”。

I07 **授权不会借模型伪造**：身份从可信认证会话或 Broker 颁发的有限委托获取；模型消息中的 actor、role、tenant、approval 不具备权力。浏览器 Cookie 路径执行 CSRF 防护；机器身份使用短期 scoped token，不复用 Web Cookie。

I08 **代码与配置并存**：代码工件以不可变 Git commit/内容哈希引用；Agent 改代码须经工作区、静态检查和独立构建测试；发布只绑定已验收的内容寻址快照。

I09 **失败结果明确**：写入远端结果未知，必须保留 UNKNOWN 并查真实资源/回执后再决定，不自动换 changeId 重放；失效授权不可通过重试恢复。

I10 **人工作业不断裂**：模型服务不可用时，人工仍可经相同强制入口编辑、验证和预览。

## 2. 写入口清单及控制点

| 写入口 | 目前已有实验 | 必须迁移到的控制点 | 绕过时策略 |
|---|---|---|---|
| Saltcorn 原生 /field/:id + POST /field | [19](19-real-browser-edit-evidence.md) 旧表单可成功覆盖 | 服务端 fieldFlow.onDone → mutation command；提交前在同事务 CAS，刷新模型缓存 | 未完成原生改造前不允许此入口与自动编辑同时开放 |
| Saltcorn Field.update / CLI | [18](18-saltcorn-sqlite-atomic-evidence.md) 绕过外部账本 | 受支持模型层拦截或强制只经命令服务；事务与缓存语义共同处理 | 非受控调用禁止或检测漂移后隔离 |
| Pack import / restore | [16](16-saltcorn-roundtrip-evidence.md) 覆盖无关字段 | 独立 `planImport` → dependency diff → 授权 → 锁内受控写 → 读回 | 不提供给普通 Agent tool |
| 研究网关 Web/Agent | [20](20-governed-http-evidence.md) 受控入口可 409 | 仅复用契约/测试，不复用直写 _sc_fields 的生产实现 | 研究用本地网关无生产权限 |
| DeepSeek patch + Field.update | [27](27-real-deepseek-human-roundtrip-evidence.md) 单路径 CAS 正例 | 模型只给 typed intent，可信 Host 同源认证，调用受治理 domain command | Agent 不可自行绕过使用 Field.update |
| 插件后台/定时任务 | 尚无真实 Saltcorn 插件写入验收 | 插件能力 Manifest 声明 resource scope、操作和副作用，服务端共享命令执行器 | 无 Manifest/不可拦截：不可启用编辑权限 |
| 数据库管理员/离线迁移 | 研究中可直写 SQLite 内表；不是生产建议 | 受控维护窗口、凭据分离、维护后扫描指纹+重建投影，保留审计 | 退出维护前阻止自动发布 |
| 应用部署/回滚 | 未完成全路径实测 | 发布只使用 verified immutable snapshot + 构建/迁移状态一致性 | 无法验证时终止且恢复最后已确认版本 |

**本表是要实现的写路径审计，不是声称已在 Saltcorn 每条路径实际完成拦截。**

## 3. 最小领域 API（候选，不是现成路由）

### 读取
`GET /v1/apps/{appId}/resources/{resourceId}`

响应：
~~~json
{
  "resourceId": "field.contract.title",
  "applicationId": "contracts-demo",
  "revision": 42,
  "contentHash": "sha256:placeholder",
  "schemaVersion": 1,
  "content": {"label": "合同名称"},
  "state": "ACTIVE",
  "permissions": ["resource.read", "resource.patch"]
}
~~~

`permissions` 为**由服务端根据认证上下文计算的结果**，客户端不得写入该字段。

### 计划/验证
`POST /v1/apps/{appId}/changes/validate`：验证 typed Patch、资源引用和用户权限，返回无副作用的影响计划和可供提交的 scope；validate 通过**不预留全局锁**，提交仍须重新检查。

### 原子变更
`POST /v1/apps/{appId}/changes`

~~~json
{
  "changeId": "uuid-v4-example",
  "resourceId": "field.contract.title",
  "expectedRevision": 42,
  "baseContentHash": "sha256:placeholder",
  "operations": [
    {"op":"replace","path":"/label","value":"合同标题"}
  ],
  "mergeMode": "REJECT_ON_CONFLICT",
  "dryRun": false
}
~~~

API 应从登录凭据解析主体，不接受 `actorId`、`role`、`tenantId` 等具有授权意义的任意用户输入。变更成功时返回 `200 APPLIED` + `previousRevision`/`revision`/`newContentHash`/`receiptId`；保留相同 changeId 的幂等回执。审计失败时不得标记成功。

**提交前的顺序（逻辑规范）**：

1. 校验身份、委托、资源/字段权限、请求限额和 Schema；拒绝未经授权的资源访问，且不泄露存在性。
2. 开始受支持的数据库写事务，锁定 resource revision/实体行和 changeId 唯一键。
3. 检查幂等 ledger。相同主体/应用/操作绑定的相同 `changeId` 与请求摘要返回**原完成回执**，即使当前资源 revision 已因后来写入变化；同键不同摘要返回 409。未经确认的 `UNKNOWN` 返回待核实状态，绝不再次写入。
4. 读取**实际资源内容**并重算 hash，比较权威 ledger hash；存在漂移则隔离资源、终止当前更改（隔离记录应在独立故障事务中持久化，不能因主事务回滚丢失）。
5. 比较 expectedRevision / base hash；仅对可证明的非冲突字段进行受限三方合并；否则 409。
6. 校验引用依赖、写入域模型所支持的原生 API，并确保相关副作用在同事务边界内一致；若平台内部 API 会在数据库事务外发布不可回滚副作用，拆为待确认 outbox 事件，绝不可提前报告完全提交。
7. 写入新 revision、hash、受影响资源清单、幂等回执、审计 outbox，提交事务。
8. 提交后刷新 ORM/视图缓存，独立回读新模型及 HTTP；若缓存失效或读回异常，应标记 `COMMITTED_UNVERIFIED`，停止发布而不是重复写入。
9. 发布前再次验证 Manifest 引用闭包、签名/哈希、构建和测试。

### 错误契约

| HTTP | code | 语义 |
|---|---|---|
| 400/422 | INVALID_CHANGE | Schema/字段 Patch 不合法 |
| 401 | AUTH_REQUIRED | 未认证 |
| 403 或不泄露存在性的 404 | FORBIDDEN | 服务端身份无权限 |
| 409 | VERSION_CONFLICT | 与真实当前字段/版本冲突 |
| 409 | CHANGE_ID_REUSED | 同一个幂等键绑定了不同操作 |
| 409 | OUT_OF_BAND_DRIFT | 实际内容与可信账本不一致；资源隔离 |
| 412 | PRECONDITION_REQUIRED | 未提供 base revision/hash（如以条件请求实现，可用 428） |
| 423 | RESOURCE_QUARANTINED | 资源处于漂移隔离或维护锁 |
| 202 | OUTCOME_UNKNOWN | 后台/远端动作结果未知，须显式对账 |
| 503 | WRITE_UNAVAILABLE | 无法获得权威存储/事务/审计支持，失败关闭 |

拒绝码是**OpenAILCAP 新接口的期望行为**，不是 Saltcorn 当前 REST 的既有返回码；例如历史 Saltcorn 业务拒绝曾返回 400/401。

## 4. 缓存、引用、应用边界

- 原生 ORM 写入即使正确提交 SQL，也要验证在**同进程不重启**时原生页面、API、触发器读取最新内容，避免“数据库已改但运行态仍旧”。
- 每项资源修改计算跨域影响闭包：DataModel → Field → Form → View → Workflow → Permission → CodeArtifact；无效引用拒绝，旧版本与新版本的运行快照不可混合发布。
- 多资源修改要有 Application 级提交批次/事务边界；不能保证同事务时应使用显式 staged draft 和独立 publish 指针。
- `appId` 必须参与所有唯一键、授权与读写 SQL 条件；在同进程运行两个应用时验证插件访问其它 app 被拒绝。
- 插件不能注入绕过写入门禁的直连数据库凭据；需要维护操作的插件只能在特殊受控事务和审计范围运行。

## 5. 阶段性工程选择

**近期最高性价比方案**：在 S3 先实现独立可控的领域 command service 和内置人工编辑器，两者与 Agent 工具、测试插件使用同一强制服务端 mutation path；Saltcorn 保留作为对照系统和数据/工作流实验底座。若确实要改造 Saltcorn 原生设计器，必须在受支持的原生服务端扩展边界统一拦截 Field.update、fieldFlow 和 Pack，而不是靠客户端覆盖菜单或直接写内部 SQLite 表。

优点：避免改造全部第三方原生设计器写路径的早期巨大成本。代价：早期需自行实现最小人工编辑器，而不是复用其全部 UI；此为待验证的架构取舍。

## 6. 已知失败反例及评审结论

- [16](16-saltcorn-roundtrip-evidence.md)：旧 Pack 只想改视图，却重置其他标签。
- [18](18-saltcorn-sqlite-atomic-evidence.md)：`withTransaction` 名称不能证明真实 SQL 回滚；旁路写入使 Agent CAS 失效。
- [19](19-real-browser-edit-evidence.md)：原生 Web 旧表单覆盖确实发生。
- [20](20-governed-http-evidence.md)：研究双客户端受控写入正例，但 Saltcorn 原生路径依然可绕过。
- [27](27-real-deepseek-human-roundtrip-evidence.md)：真实模型参与小范围顺序编辑，但原生 Web CAS 仍缺失。

因此 **G1-B01: SPECIFIED / IMPLEMENTATION_PENDING / VERIFICATION_NOT_RUN**。接口设计和已存在的 S0 证据不应被当成此新契约已部署或 G1 通过。以 [验收矩阵](31-g1-b01-acceptance-matrix.md) 作为下一次真正实现的唯一判据。
