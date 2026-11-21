# S1 报告 34：B1 自研最小人工 Web 编辑器 + Agent/Plugin 同一受控写入内核实测

- 研究日期：2026-11-21
- 状态：**B1 限域端到端 CI VERIFIED；G1-B01 部分机制已证实、全渠道目标 OPEN；G1 NOT_PASSED**
- 报告基线：真实 PR 合并提交 [a0eff9d](https://github.com/zealzhangz/OpenAILCAP/commit/a0eff9d11ce4c96a0fed8bb53aac8afa0364b82a)
- [工程源码/复现说明](../../experiments/g1-b01-c1/README.md) · [自动化工作流](../../.github/workflows/s1-g1-b01-b1.yml) · [PR #3](https://github.com/zealzhangz/OpenAILCAP/pull/3)

## 1. 研究目的

前轮 [C2 真实 Saltcorn 实验](33-g1-b01-c2-native-route-evidence.md) 已证明：可以在第三方原生浏览器字段向导中通过一次性路由补丁拒绝顺序旧表单，但 **Saltcorn 原生 CLI Field.update 仍然完全绕过**网页门禁。继续给第三方网页打补丁不会自然消除统一写入问题。

本轮转向 B1 对照路线：**在自己控制的最小 Web 编辑器、可信工具 API 和服务端资源存储之间只保留一条写入路径**，由原 [C1 Store.apply](../../experiments/g1-b01-c1/service.py) 统一控制同一 SQLite 资源的授权、版本比较、内容哈希、幂等回执、事务和审计。人工通过 Chromium；Agent 和 Plugin 使用真正独立 Python 子进程从 HTTP 调用；不借助 Saltcorn 的内部表，也不需要生成完整 Application IR。

这轮回答的是“最小人工 UI 能否与另外两个调用者共享权威 mutation path，并且不静默丢失修改”，**不是**“企业级完整低代码设计器/插件生态是否已经建成”。

## 2. 可复核的原始证据

| 项目 | 实际记录 |
|---|---|
| GitHub Actions 真实运行 | [Run #44888692681](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44888692681)：**completed / success** |
| Job | **136799528729**，`real-owned-editor-same-mutation-core` |
| 原始 Artifact | [#14701406504](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44888692681/artifacts/14701406504)，含逐项 JSON、原始 B1 与 C1 日志 |
| B1 独立端到端检查 | **18/18 PASS**：`S1_B1_RESULT {"passed":18,"total_attempted":18,"expected_total":18}` |
| 原 C1 回归 | **31/31 unittest 执行实例 PASS**，`fail_count=0, error_count=0`，31 次执行含继承类重复测试（18 个不同测试方法） |
| 本轮独立离线 C1 工作流 | [Run #44888692722](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44888692722)：completed / success |
| 代码合并 | [PR #3](https://github.com/zealzhangz/OpenAILCAP/pull/3)，已 squash 合并 `a0eff9d11ce4c96a0fed8bb53aac8afa0364b82a` |
| 运行环境 | Ubuntu 24.04、Python 3.13、Playwright 1.56 与真正 Chromium、一次性本机 SQLite，两个独立工具 OS 进程 |
| 模型调用 | **0**：没有使用 DeepSeek Secret，也没有由模型生成任何 Patch |

### 失败历史与修复

第一次 [Run #44888560840](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44888560840) 完成 Chromium 真实登录和两个旧标签页建档 3/3 后，测试脚本尝试通过 Playwright `wait_for_function("...")` 执行字符串表达式，触发 HTML 的严格 `Content-Security-Policy` **禁止 unsafe-eval**。这是验收脚本被安全策略拦截，不是业务 CAS 失败。

修正为通过 Playwright Locator 直接读取 DOM 文本并轮询，不放宽 CSP、不加 `unsafe-eval`，再执行 [#44888692681](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44888692681) 后全部端到端用例成功。保留首次失败记录，避免把 CI 偶然绿灯当作持续安全。

## 3. 真实测试细项

| 编号 | 验收观察 | 原始结果 |
|---|---|---|
| B1-01 | 未登录访问人工设计器强制进入登录页 | PASS |
| B1-02 | 真正浏览器通过 HTML 表单完成服务端 Session 登录 | PASS |
| B1-03 | 两个真实 Chromium 标签页均读取 revision=0 | PASS |
| B1-04 | B 浏览器通过统一领域命令 API 保存，物理 SQLite revision=1 | PASS |
| B1-05 | A 持旧版本保存得到 HTTP **409 VERSION_CONFLICT**，B 值保留 | PASS |
| B1-06 | 独立 Agent 工具进程 Bearer HTTP 写 status，revision=2，保留 B label | PASS |
| B1-07 | 旧浏览器页面在 Agent 写入后得到 **409**，Agent 的数据保留 | PASS |
| B1-08 | 人工点击“重新加载版本”，真实浏览器看到 Agent 状态 | PASS |
| B1-09 | 人工刷新后继续写 label，revision=3，Agent status 保留 | PASS |
| B1-10 | 独立 Plugin 进程按 Manifest 对 status 提交，revision=4，审计有 `status-helper` | PASS |
| B1-11 | Plugin 即使**绕过自身 Manifest 客户端判断、直接发 HTTP 改 label**，服务端仍返回 **403 FIELD_FORBIDDEN** | PASS |
| B1-12 | 插件 Manifest 字段拦截及跨 app HTTP 403，app-b revision 仍 0 | PASS |
| B1-13 | Agent 使用已失效资源 revision/hash 提交，HTTP **409** | PASS |
| B1-14 | 未认证 HTTP 写请求 401，物理资源不变 | PASS |
| B1-15 | 持真实 Chromium Session Cookie 但不含 CSRF 的写入得到 403 | PASS |
| B1-16 | **两个独立 OS 进程 Agent/Plugin 用同一旧 revision 竞争**，HTTP **[200,409]**；物理 DB revision=5，audit=5，receipt=5 | PASS |
| B1-17 | 撤销 Plugin Token 后访问 401 | PASS |
| B1-18 | 新浏览器 DOM 与独立物理 SQL 内容、版本一致；app-b 仍旧 0 | PASS |

上述 18 项是**本轮 B1 冻结的小范围集成验收**，不是正式冻结 G1-B01 W01—W24 的 FULL PASS 计数。

### 三写入者连接拓扑

~~~text
[真实 Chromium / 密码登录 + Cookie + CSRF] ───┐
                                                │
[独立 Agent typed-tool 子进程 / Bearer] ─────────┼── POST /v1/apps/{app}/changes
                                                │                 │
[独立 Plugin 进程 / Manifest + 限域 Bearer] ────┘                 ▼
                                                C1 Store.apply 可信服务端
                                                    │
                                      权限 ─→ revision/hash CAS
                                                    │
                                       SQLite 资源+回执+审计原子事务
~~~

B1 的人工页面是**实际可操作 HTML**，仅暴露固定 `field.title` 的 `label/status` 两个字段：服务端渲染登录、非自动刷新基线、旧表单明确 409、人工显式刷新；不存在另外一套绕过 C1 的页面写入代码。

## 4. 安全验证成立的范围

**得到更强证据的特性：**

- 同一资源的人工 UI、确定性 Agent 和限制字段的测试 Plugin **实际共用同一个权威事务性更新函数**，不同于 C2 仅在 Web 路由附加旧标签检查。
- 服务端根据**自身 principal** 实施字段/资源/application scope，不接受来自模型/插件 JSON 自述的高权限身份；插件尝试跨字段修改的真实 HTTP 403，支持未来 Manifest server-side authorization 的方向。
- 两个真正独立 OS 客户端竞争同一 revision，其中一个成功、一个 409；其他字段和应用不被静默改写。
- 真实浏览器兼具正常人工开发和模型完全离线情况下继续编辑的基本能力。

**尚未得到证明的特性：**

1. B1 的 `Plugin` 是研究中受限 token 的 Python 子进程，**不是在真正插件沙箱中运行**。未验证文件系统隔离、DB 凭据剥离的强制性、供应链签名、恶意插件代码执行、宿主插件生命周期、越权网络访问。不能把 B1-11 等同冻结 W16 完整通过。
2. B1 的 `Agent` 是确定性类型化工具客户端，**没有调用 LLM**。未验证自主需求理解、Schema/页面生成、代码生成、错误自修复、真实用户委托审批和生产部署。
3. B1 的 Browser 是自建**两字段 HTML 原型**，而非 Saltcorn 原生编辑器或可配置低代码页面设计器。旧原生入口仍可能绕过，不能据此说 Saltcorn H03 已通过。
4. C1 单机 SQLite 小样本，所有真正数据库管理员/迁移和额外直接写入口都未被强制禁用。真实企业用户账号、多租户、OIDC/SSO、HTTPS、缓存热更新、分布式部署、迁移与不可变发布/回滚均没有系统验收。
5. W01—W24 包含真实 Plugin Manifest 执行、原生参考平台或完整内置可视化设计器、跨资源依赖、部署和发布等；**仍按 0/24 FULL PASS 记录**，不得以本轮 18 项代替。合同 TC01—TC18 **0/18 FULL PASS**。

## 5. 对架构决策和下轮优先级的影响

三次实验的强弱对照现在较清楚：

- **C0** 未改造第三方原生 Web：顺序旧编辑会造成静默覆盖；
- **C2** 临时改造第三方 Web：旧表单 409，但 CLI Field.update 仍能旁路，且旧标签比对不是原子 CAS；
- **C1+B1** 自控最小 Web + 工具同一 Store.apply：真正浏览器/Agent/Plugin 研究调用者共享 revision、hash、幂等与审计，18/18 + 31/31 CI 通过；仍未提供真实可配置应用内核和强制插件隔离。

由此可把**领域命令 API + 受治理编辑器**列为 S2/S3 的优先技术比较方向，但不意味着放弃对其他低代码平台的架构借鉴，也不意味着已经从真实 PoC 决出“Domain Schema+Manifest 优于 Global IR”。

**下一轮最有价值的验证**：不再重复 label 的 409；为 B1 添加真实可编辑的最小 DataModel→Form/View→Workflow Schema/Manifest，接入同一 command 审核和引用闭包，验证从自然语言需求到最小业务页面的运行态生成，以及人工中途修改后 Agent 再接手。插件 sandbox/真实恶意代码对照和发布快照仍应保持 P0/P1。

## 6. G1 门禁

- B1：**C1 core + real own-Web browser + external Agent/Plugin processes = LIMITED CI VERIFIED**
- G1-B01：**PARTIALLY VALIDATED / OPEN**（全渠道强制写入和生产级权限未成立）
- 第一阶段：**S1 IN_PROGRESS，G1 NOT_PASSED**
- 冻结完整 G1-B01 W01—W24：**0/24 FULL PASS**
- 冻结合同 TC01—TC18：**0/18 FULL PASS**
