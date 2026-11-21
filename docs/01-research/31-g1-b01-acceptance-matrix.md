# G1-B01 独立验收矩阵与执行计划（预注册 v0.1）

> 全部新测试 **NOT_RUN**。此文件为可证伪的测试规范，不把历史的 26/26、16/16、6/6 结果迁移为本计划 PASS。对应 [统一写入契约](30-g1-b01-unified-write-contract.md)。

## 1. 固定测试对象

- 对照应用：`contract-app-A`、`contract-app-B`，各有 `field.title`、`field.status`、`page.contracts`、`rule.approval`，同名资源不同 app 必须隔离。
- 三个身份：Web 用户 H（真实 Chromium+服务端 Session/CSRF）、Agent 执行主体 A（受限制的工具委托，模型可关闭）、插件 P（由 Manifest 注册、可撤销授权）。
- 未授权主体 X、只读主体 R，分别覆盖身份伪造、跨 app 和写权限拒绝。
- 标准持久化组件：独立权威 revision/hash、change ledger、资源/审计、不可变发布快照；具体 DB/框架暂不预设。
- Oracle：**独立**于命令处理器的直接物理数据库读回、页面 HTTP API、真实 Chromium DOM、事件/审计/回执、构建产物哈希。
- 环境：一次性隔离测试数据库，固定版本、固定 SHA、测试随机凭据不入仓；禁止连接真实生产库；使用零 LLM 预检，只有环境通过后才允许单次小额真实推理作补充，后者不能替代安全测试。

## 2. 测试清单与机器可判定结果

| ID | 固定场景 | 独立验收标准 | 状态 |
|---|---|---|---|
| W01 | H、A、P 各经认证创建/修改不同资源 | 三者写入生成同形态 revision + hash + receipt + audit | NOT_RUN |
| W02 | H 两个真实原生设计器标签页读同旧版本，B 先提交、A 后提交相同字段 | B APPLIED，A 明示 409，B 值在物理 DB 和浏览器保留 | NOT_RUN |
| W03 | H 先改 title，A 用旧 snapshot 改同 title | A 409，无任何 title 丢失 | NOT_RUN |
| W04 | A 先改 status，H 基于旧表单改同 status | H 409，无任何 status 丢失 | NOT_RUN |
| W05 | H 改 title，A 改 status（不同字段） | 使用显式重读或审核过的三方合并，二者内容均保留并版本化 | NOT_RUN |
| W06 | P 与 A 同时修改一个资源同一字段 | 物理事务恰好一胜一冲突；无双成功 | NOT_RUN |
| W07 | 2 独立进程并行 HTTP 提交同 revision | 仅 1 次实际写入、另 1 次 409，唯一 change ledger 正确 | NOT_RUN |
| W08 | 重放相同 changeId、同主体/请求，资源已经由他人再次更新 | 返回**首次已成功提交的原回执**；不新增 mutation/audit side effect | NOT_RUN |
| W09 | 同 changeId 换请求摘要或换主体/app | 不复用成功结果，拒绝新副作用 | NOT_RUN |
| W10 | SQL 更新中途注入故障 | 物理资源、revision、成功 receipt 原子回滚；独立错误审计仍可记录 | NOT_RUN |
| W11 | 原生 Field.update / CLI 故意绕过统一入口 | 若未拦截则独立 hash 漂移发现并隔离；A/P 不得继续写入/发布 | NOT_RUN |
| W12 | Pack 导入包含旧版本无关资源 | 必须展示完整 diff、需高权限审批；默认 Agent tool 拒绝整体覆盖 | NOT_RUN |
| W13 | 模型请求携带伪造 actorId/role/appId | 工具宿主忽略或拒绝越权字段；真实用户与资源不变 | NOT_RUN |
| W14 | 只读/无权限/跨 app 的 H、A、P 尝试写入 | 必须失败，业务资源/账本不变，不泄漏敏感资源内容 | NOT_RUN |
| W15 | Web POST 缺 CSRF，或 Agent token 过期/撤销 | 明确拒绝，不把重定向 HTML 200 当作写成功 | NOT_RUN |
| W16 | 插件直接申请 DB 管理员连接或执行未经声明工具 | 插件加载/操作拒绝；正式数据库无旁路写入 | NOT_RUN |
| W17 | 运行时不重启，变更字段/视图后立即读取 | 物理 DB、原生 REST、浏览器显示和缓存观察一致 | NOT_RUN |
| W18 | 发布前出现 DB 漂移或引用断裂 | 不能标记已发布，保留此前 verified snapshot | NOT_RUN |
| W19 | 代码工件修改后构建/测试失败 | 发布指针不变；人工代码和可运行旧版本均保留 | NOT_RUN |
| W20 | 外部执行返回 timeout，实际副作用结果未知 | 标记 UNKNOWN，按 changeId 查实际业务与 receipt；不换 ID 自动重放 | NOT_RUN |
| W21 | 两应用同名字段和插件并行操作 | app-A 不影响 app-B，数据库/审计/工具权限均隔离 | NOT_RUN |
| W22 | 模型服务不可用，H 继续设计并提交 | 经过同一强制 write contract，独立运行读回成功 | NOT_RUN |
| W23 | 删除/重命名数据字段被多个页面、Workflow、代码引用 | 依赖闭包校验拒绝悬挂引用或要求显式迁移 | NOT_RUN |
| W24 | 回滚到前一 verified snapshot | 应用/代码/流程/Manifest 一致，未回滚的外部业务副作用明确补偿处理 | NOT_RUN |

## 3. 试验对照组

- **Control C0（旧 Saltcorn 原生）**：复现 [报告 19](19-real-browser-edit-evidence.md) 的 stale form 覆盖，标为**预期负例**而非产品安全 PASS；不可将当前 C0 结果冒充新测试已运行。
- **Candidate C1（统一领域 API，自建最小 Web 编辑器）**：H/A/P 全部经同一可信 mutation path，禁止任意 DB 写入口；优先实现 W01—W10、W13—W15、W22。
- **Candidate C2（Saltcorn 原生设计器强制接入）**：需要真实服务端 Field/Pack/Plugin 扩展点和缓存一致性；首要 W02、W04、W11、W17。
- **Fallback C3（不支持原生统一写入）**：禁用自动提交和发布，检测到外部漂移强制隔离；可作为受限研究模式，但**不能过 G1-B01 目标验收**。

## 4. 最小迭代顺序（不提前支付模型调用）

1. 固定运行器版本与资源样例、失败/成功 oracle；将表中 24 项机器可读导出至 JSON。
2. 用零模型手工固定工具请求跑 C1；先通过 W01—W10、W13—W15，再进入浏览器原生/插件整合；任何失败保留原始 Artifact，不能只报告最终成功。
3. 通过真实 Chromium、真实 HTTP、真实 Plugin、两进程/事务和 DB 验收 W01—W24；不得以 mock 替代路径。
4. 评估 C2 原生改造能否覆盖所有写入路径及维护成本。若高成本且绕过无法关闭，则回到自建最小人工编辑器路线。
5. 如需验证 LLM，只允许依据已通过的确定性执行器追加**一次**受限请求，且由独立 oracle 判定结果。
6. G1 复审根据原预注册 W01—W24 的通过率、失败反例和原生写路径覆盖清单，不接受单项子断言替代整套验收。

## 5. 门禁和停止条件

- **G1-B01 Go 候选**：W01—W24 **全部 PASS** 且无已知未受控正式写入口；服务端事务、权限、幂等、真实 Web/Agent/插件均有原始证据。
- **Conditional Go 候选**：只限明确的研究或离线原型；未覆盖的原生写入必须在系统层禁用，默认停止 Agent 自动写入和生产发布。此类受限演示不应被宣称平台 H03 通过。
- **No-Go**：有任一无法禁用的编辑入口可无条件覆盖，或插件/Agent 可绕过身份/版本/事务门禁。
- **S3 与 G3 分界**：即使 W01—W24 通过，也**不等于** AI 自动生成应用、代码编译、插件隔离、全量 PoC-A/B/C/D 已通过；这些按 G3 单独判定。

## 6. 收集证据字段

每个测试必须形成单条 JSON 记录：
~~~json
{
  "test_id": "W02",
  "status": "NOT_RUN",
  "candidate": "C2",
  "code_commit": null,
  "platform_version": null,
  "ci_run_url": null,
  "artifact_id": null,
  "expected": "old native form -> HTTP 409, latest persisted",
  "observed_http_status": null,
  "db_snapshot_digest": null,
  "browser_dom_digest": null,
  "audit_receipt_id": null,
  "failure_category": null
}
~~~

禁止出现“设计完成即 PASS”、把正向测试中的预期拒绝当作系统失败，或把负对照的危险覆盖当作安全通过。
