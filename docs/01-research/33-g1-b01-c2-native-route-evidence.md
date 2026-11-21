# S1 报告 33 — C2 原生 Saltcorn 字段路由过时编辑保护的可证伪实验

- 日期：2026-11-21
- 阶段：S1 研究，G1 **NOT_PASSED**
- 主结论：**原生 Web 顺序旧编辑可由一次性路由插桩明确 409；但完整写入口保护仍然失败，真正原生 CLI 可绕过。**
- 实测源码： [C2 研究工程](../../experiments/g1-b01-c2/README.md)；[PR #2](https://github.com/zealzhangz/OpenAILCAP/pull/2)（已合并，主线提交 `a5a01907226f6362cfc585b69ce24d5784386737`）
- 真实 CI：[Run #44887680474](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44887680474) completed/success，Job **136796430685**，Artifact **14699859357**

## 1. 为什么需要做 C2

历史 [真实原生浏览器负例 19](19-real-browser-edit-evidence.md) 在未改造 Saltcorn 1.7.0-beta.5 上复现两个标签页持旧表单导致静默覆盖；[研究网关 20](20-governed-http-evidence.md) 只证明自建 Web 和模拟 Agent 在网关内能拒绝旧提交，不能说明 Saltcorn 自己的 /field 路由有保护；[真实模型交接 27](27-real-deepseek-human-roundtrip-evidence.md) 只让 Agent 路径经过 CAS，原生 Web 仍可绕过。

本轮直接以真正第三方平台安装版本、原生 `GET /field/:id`、`POST /field`、`fieldFlow.onDone`、`Field.update` 为对象，而不是再用自建模拟页面代替原生界面。

## 2. 版本、源码与调用链

上游源码研究参考 [Saltcorn fields.ts @ 515254bee](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/server/routes/fields.ts)。GitHub Runner 真正安装 `@saltcorn/cli@1.7.0-beta.5`，现场定位编译产物 `routes/fields.js` 并验证四个锚点：

~~~mermaid
sequenceDiagram
  participant H as Chromium native field editor
  participant GET as Saltcorn GET /field/:id
  participant WF as fieldFlow + contextEnc
  participant POST as Saltcorn POST /field
  participant FIELD as Field.update
  participant DB as SQLite _sc_fields
  H->>GET: 载入现存字段
  GET->>WF: field.toJson + 原生上下文
  Note over GET,WF: 研究插桩添加 HMAC 签名原始 label
  H->>POST: 原生向导多次 POST (Session/CSRF/contextEnc)
  POST->>WF: wf.run(context)
  WF->>FIELD: onDone 先做签名与旧值比较
  alt 字段值已由另一标签改变
    WF-->>POST: STALE_EDITOR
    POST-->>H: HTTP 409
  else 原始值仍相同
    WF->>FIELD: 原生 Field.update
    FIELD->>DB: metadata write
    POST-->>H: 原生成功重定向
  end
~~~

**重要技术边界**：上述比较和 `Field.update` **不是同一个跨写入者原子 CAS**。它不能消除检查之后、写入之前的竞态窗口，也不能保护插件、CLI、Pack 或其他元数据字段。此次修改通过一次性 patch 工具改写 Runner 已安装 npm 包的编译 JS，**不是 Saltcorn 官方扩展 API 或长期有效的修复**。

## 3. 实测结果

| 测试 | 独立观测 | 结果 | 正确含义 |
|---|---|---|---|
| C2-01 | 两个真实 Chromium 标签均从原生编辑器看到 `Title` | PASS | 顺序旧表单场景实际形成 |
| C2-02 | 原生编辑表单仍含 `contextEnc` 和 `_csrf` | PASS | 没有换成研究用假编辑器 |
| C2-03 | B 通过原生多步表单保存 `Browser B Protected`，物理 SQL 读回一致 | PASS | 受插桩路由下新编辑有效 |
| C2-04 | A 仍持旧基线提交，真实 POST 状态序列 `200,200,302,200,200,409`，最终明确 409 | PASS | **顺序旧提交被拒** |
| C2-05 | 409 后独立物理 SQLite 仍为 `Browser B Protected` | PASS | A 未静默覆盖 B |
| C2-06 | 新原生浏览器页面读到 B 值 | PASS | 新会话可读回 |
| C2-07 | 新鲜表单继续保存 `Browser C Fresh Edit` | PASS | 保护不是简单禁止所有编辑 |
| C2-08 | POST 链来自原生 `/field` | PASS | 是真正浏览器路由 |
| C2-09 | **Saltcorn CLI 的原生 `Field.update` 不经 Web 路由**，实际改为 `Native Outside Gateway` | PASS（危险负对照） | **全渠道强制治理没有达成** |

**正向浏览器 8/8 + 预注册危险负对照 1/1**，不能写成“系统安全 9/9 通过”。GitHub Actions completed/success 表示实验预期得到验证，包括预期的危险绕过行为。

### 运行失败历史

首次集成 [Run #44887534989](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44887534989) 在导入 Playwright 时失败：实验目录的 `inspect.py` 遮蔽 Python 标准库 `inspect`，触发 `AttributeError: module 'inspect' has no attribute 'FrameInfo'`。更名为 `inspect_route.py`，后续真实 CI 所有步骤成功。更早只读包检查 [Run #44887303753](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44887303753) 已证明安装包中编译路由与源码一致的关键写入锚点。

## 4. 对照实验与外推限制

| 对照 | Web 原生是否真能修改字段 | 能否拒绝顺序旧编辑 | CLI/插件/Pack 全渠道强制 CAS | 实验真实性 |
|---|---|---|---|---|
| C0：未改造 Saltcorn（报告 19） | 是 | **不能：旧 A 覆盖 B** | 无证据 | S0 真实 Chromium |
| C1：自研命令服务（报告 32） | 自建 HTTP 测试客户端，非 Saltcorn 原生 | 受控 HTTP 能 409 | 未集成 Saltcorn/真实插件 | S0 31/31 执行实例 |
| C2：本轮一次性原生编译路由插桩 | **是** | **能：旧 A 409** | **不能：真实 CLI 绕过已实证** | S0 真实 Chromium + Saltcorn 原生运行时 |
| C3：统一模型层强制写入（候选） | 仍需实现 | 未运行 | 待真正 PoC | NOT_RUN |

不能由 C2 结论断言“只改网页路由即可拥有强一致性”；也不能因 web 409 就说 W02 全部满足：W02 被冻结为强制治理的实际产品验收目标，真正多写入者、同事务/并发、插件调用与不可绕过入口仍缺失。原冻结 W01—W24 **0/24 FULL PASS**，合同 TC01—TC18 **0/18 FULL PASS**。

## 5. 形成的架构建议（含否定路线）

- **可以确认的机制**：为浏览器编辑载入服务端可信基线并在写入端拒绝旧内容，不必用大规模 Application IR 才能表达；返回明确 HTTP 409 是可以在真实原生向导上实现的。
- **已经失败的方案**：只修补浏览器字段路由，其它 `Field.update` / CLI / Pack 不统一；历史“只给 Agent 做 CAS”也失败。**两种局部防护都不应作为 OpenAILCAP 的目标架构**。
- **候选方向 B1（更小可控）**：自研最小人工设计器、Agent/插件都通过同一可信领域命令 API；保持分域 Schema + Manifest，之后做引用/发布闭包的真实测试。
- **候选方向 B2（第三方集成）**：必须寻找受支持的模型层 mutation interception，让 Web/CLI/Pack/Plugin 均无法绕过，并验证缓存刷新、事务和异常回滚；若第三方版本/许可不支持这一层，终止直接复用为生产内核。
- **成本与授权**：C2 实验式直接修改已编译 npm 包极其脆弱，并存在供应链/升级风险；生产不得采用；对上游开源源码复用还要独立检查许可。

## 6. G1 复审结论和下一最小实测

- 已新增真正第三方原生设计器**正向顺序冲突拒绝**证据，弥补此前只有原生负例/自建代理正例的空白。
- 更重要的是证明**真实原生 CLI 仍可绕过 Web 版本校验**，因此 G1-B01 的本质未解决，**G1 NOT_PASSED**。
- 下一实测优先对比两条路径的安全改造成本：B1 最小自建 Web 编辑器通过 C1 完整 domain command；B2 上游模型层/事务层是否有稳定强制扩展点。重点不是继续增加同一表单的成功断言，而是引入真正 Agent/Plugin、并发、依赖验证和发布状态。
- 本次没有 DeepSeek 推理，GitHub Secret `DEEPSEEK_KEY` 不参与此工作流。

**阶段状态：S1 继续；H03 有限定正向与清晰负面证据，未完全验证；G1-B01 OPEN。**
