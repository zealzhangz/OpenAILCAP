# S1 真实数据上的受治理 HTTP 编辑闭环：正向协议与原生绕过检测

**研究日期：2026-11-21。状态：实验适配层的可复现正向验证成功；不是 Saltcorn 原生编辑器的修复，也不是 OpenAILCAP 生产级实现。G1 仍未通过。**

## 一、研究价值与上一轮的直接对照

此前的真实 Chromium 实验在 Saltcorn 原生 /field/:id 路由中，两个标签页同时持有旧字段配置，B 保存后 A 的旧表单可覆盖 B；另外，即使 Agent 自己使用事务性 CAS，如果人工绕过版本账本，Agent 仍会错判版本有效并覆盖人工改动。

本轮不只重复失败案例，而是构造一个**能够真实完成正向行为的最小写入协议**：在同一个真实 Saltcorn SQLite 文件上，研究网关自建的浏览器表单和模拟 Agent 的 Bearer HTTP 客户端都使用同一个资源版本/指纹/幂等协议；独立浏览器、HTTP、SQL、故障注入及真实 Saltcorn 重启读回均成为验收来源。

### 关键证据

| 证据 | 实测记录 |
|---|---|
| 可复现代码 | [experiments/platform-saltcorn/governed](../../experiments/platform-saltcorn/governed/README.md) |
| 首次提交 | [adcadeef3b836a4fcc7c95c4557f764524692d27](https://github.com/zealzhangz/OpenAILCAP/commit/adcadeef3b836a4fcc7c95c4557f764524692d27) |
| GitHub Actions | [Run #44874668928](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44874668928) — completed / **success** |
| CI Job | 136756624531 |
| Artifact | s1-governed-http-shared-editing，ID 14695407749，包含 main/drift 两份原始机器可读结果 |
| 数据底座 | 实际安装 @saltcorn/cli@1.7.0-beta.5，并用 Saltcorn 原生 Pack 创建合同数据、Field 元数据与视图 |
| 浏览器 | Ubuntu 24.04 + Playwright 1.56 Chromium，**操作研究网关的 HTML，而不是 Saltcorn 原生编辑器** |
| 模拟 Agent | HTTP Bearer 客户端，**没有调用 LLM** |
| 验收规模 | **主流程 22/22 + 外部绕过检测 4/4 = 26/26**，外加真实 Saltcorn REST/HTML 重新启动后读回 PASS |

## 二、真实验证结果（均由独立验收脚本打印）

| 验收范围 | 结果和 HTTP/DB 证据 | 解释 |
|---|---|---|
| 未登录 API | G02：401 AUTH_REQUIRED | 网关拒绝无身份请求 |
| 只读工具身份 | G03：可 GET revision=0；G04：POST 403 READ_ONLY | 模拟了读/写能力分离 |
| 其他应用 | G05：403 APP_FORBIDDEN | **单一固定 app_id** 的限域，不等于生产多租户隔离 |
| 非法输入 | G06：422 INVALID_LABEL | 服务端拒绝无效字段标签 |
| 真实浏览器会话 | G07 未登录跳转、G08 登录后进入研究编辑器、G09 两个标签页初始版本一致 | Chromium 真正操作网关页面 |
| 浏览器写入 | G10：保存后 _sc_fields 的 title.label = Browser Governed Title，HTTP 200 | 物理 Saltcorn 元数据变化，而非仅更新前端状态 |
| 旧标签页写入 | G11：HTTP **409**；数据库仍为 Browser Governed Title | 本实验网关中，过时表单不会覆盖新改动 |
| 有 Cookie 无 CSRF | G12：HTTP 403 | 基础 CSRF 检查 |
| Agent 同字段旧版本 | G13：GET 看到浏览器 revision=1；G14：旧 revision=0 返回 **409 VERSION_CONFLICT** | 人工与模拟 Agent 在实验网关共享版本账本 |
| Agent 不同字段编辑 | G15：status 更新为 Automated Status，title 保留 Browser Governed Title | 非冲突资源修改的正向结果 |
| 幂等行为 | G16：同 change_id 同请求返回 replayed=true；G17：同 ID 不同内容返回 **409 CHANGE_ID_REUSED** | 在当前版本仍匹配的条件下幂等 |
| 并发资源竞争 | G18：两个独立 HTTP 请求结果 **[200,409]**；G19：revision 最后为 2 | SQLite BEGIN IMMEDIATE 下，同一 resource 两请求仅接受一次 |
| 故障注入/原子回滚 | G20：物理字段更新后注入异常返回 500，字段与 revision 不变，成功 change_id 未入库 | 真实数据库回滚，不是只恢复内存对象 |
| 重新同步后修改 | G21：模拟 Agent 使用最新版本成功更新至 revision=2 | 正向的显式刷新后继续编辑 |
| 审计 | G22：4 个 APPLIED，3 个 VERSION_CONFLICT；记录 human 与 agent | **实验审计**，没有抗篡改/完整身份治理保证 |
| 原生 Saltcorn 绕过 | D01：Saltcorn 原生 Field.update 将标签改成 Native Outside Gateway | 真实证明旧入口**仍可绕过**研究网关 |
| 外部状态漂移 | D02：后续 GET 409 OUT_OF_BAND_DRIFT；D03：Agent POST 同样 409 | 一旦发现未登记的真实元数据变动，拒绝继续发布旧写入 |
| 变更结果完整性 | D04：资源账本仍为 revision=2，试图覆盖时未写成功回执 | 旧账本不会被错误推进 |

**独立运行态读回**：全部验证后重新启动 Saltcorn 本体，实际 GET /api/s1_contracts/ 和 /view/s1_contract_list 均能读回合同 HT-2026-000001；GitHub Job 输出 NATIVE_SALTCORN_REOPEN_REST_AND_HTML_PASS。

上述 26 项是**本次研究契约**的独立断言，而非冻结业务 Benchmark 的 26 个任务；正式 TC01—TC18 仍不能据此标记 PASS。

## 三、为何能正向拒绝旧版本：真实写入协议

实验网关仅监听 127.0.0.1:3200，将浏览器表单 POST /edit/title 和模拟 Agent JSON POST /api/apps/s1-contract/resources/title 收敛到同一个 Storage.update：

1. 从 Cookie+CSRF 或 Bearer Token 决定请求方身份及可写能力；不信任请求体内自称的 actor。
2. 进入真正 SQLite BEGIN IMMEDIATE 事务，对物理 _sc_fields 读取当前标签并计算服务端 SHA-256 指纹。
3. 将真实标签指纹与研究账本比较。若已经由 Saltcorn 其他编辑入口改变，返回 409 OUT_OF_BAND_DRIFT。
4. 同一事务中检查变更 ID 的幂等回执、客户端 expected revision 与 expected fingerprint；同字段旧上下文返回 409 VERSION_CONFLICT。
5. 同一事务依次更新 _sc_fields、研究修订表、成功回执、审计事件并 COMMIT。故障注入发生在 SQL 字段已更新而修订表尚未更新之间；真实回滚已经由 G20 验证。

这是一项**写入协议机制性验证**，不等于解决实际 Saltcorn 运行时模型/视图缓存、Field.update 钩子、其他模型引用和生产部署。研究适配器直接写 Saltcorn 内表只能用于一次性实验数据库，**不能当作推荐的正式集成代码**。

## 四、重要的否定与尚未证明

- **Saltcorn 原生浏览器编辑器没有被修复。** 本次安全的 Chromium 表单是我们创建的研究页面。D01 证明 Saltcorn 自身的 Field.update 仍可在不更新该研究账本的情况下改写真实元数据。
- **外部变更只能检测后失败关闭，不能防止发生。** 没有对原生插件、CLI、数据库管理员或所有网页路由强制统一写入；字段指纹检测也没有覆盖视图 Schema、流程、代码与部署工件。
- **模拟 Agent 不是真正的 LLM Agent。** 没有任务理解、能力发现、工具委托、模型随机性、自动修复或自主部署。
- **身份机制仅为 localhost 研究用途。** 没有 HTTPS、组织级 RBAC、SAML/OIDC、真实用户委托、持久会话安全、租户级权限、抗暴力破解或合规审计。
- **测试在单机 SQLite 和两个字段上完成。** 无生产负载、跨数据库事务、在线缓存热更新、跨多个资源/应用一致性和分布式发布。
- **配置数据类型与原合同 Benchmark 仍不完全一致。** 金额采用整数分而非原冻结规格 decimal(12,2)，多级审批没有真正运行。

## 五、对架构候选决策的影响

从以前的三类负例，推进到本轮**限定范围内的正向协议**，得出更精确的判断：

- 版本、服务端内容指纹、幂等键、权限和 SQL 原子事务组合，在一个固定 Saltcorn 元数据资源族上，能够让两种受控客户端的编辑相互兼容；这为 OpenAILCAP “统一可治理写入”方向提供实际证据。
- 仅在代理/Agent 路径加装该协议依然不足。原生编辑器写入或外部操作能够造成研究版本账本失配；在原生写入口不能改造的过渡期，**发现真实资源漂移并停止 Agent 后续写入**是有价值的防护，但不等于自动安全合并。
- 仍不能从此实验推出“统一 Application IR 必须存在”。这验证了写入协议的必要性，不是 IR 与分域 Schema 的端到端比较。
- 正式产品不应直接更新 Saltcorn 内部元数据表。更合理的后续研究是将命令协议下沉到**原生扩展/插件服务端**，真正让人工网页、Agent 工具和插件使用相同资源修订和缓存刷新机制。

## 六、S1/G1 决策和后续研究优先级

**S1 继续，G1 尚未通过。** 新增真实研究网关的 26/26 原始 CI 证据，但并没有完成真实 AI 开发、真实平台原生编辑器统一版本接入或完整合同业务审批/插件扩展。因此冻结的 18 项完整合同任务依旧 0/18 PASS。

下轮优先顺序应避免继续在同一字段标签上反复试验：**P0 真实 AI Agent 的类型化工具调用与权限委托；P0 合同金额阈值/审批的真实业务运行；P1 原生插件 API 或统一写入适配层；P1 继续核实四个重点参考平台的实现与许可证。** 完整的 G1 正式 Go/Conditional Go/No-Go 判定仍需对真实业务、Agent 工具与研究交付覆盖作独立复审。
