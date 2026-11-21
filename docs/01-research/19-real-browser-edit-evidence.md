# S1 实测报告：真实 Chromium 设计器双标签页过时提交与 Agent 版本账本失效

**实测日期：2026-11-21。阶段：S1（第一阶段），G1 仍未通过。**

## 1. 与前几轮相比的新证据

之前的 Saltcorn 研究使用 CLI/Field.update 代替“人工”；本次**首次真正启动 Chromium 1.56 配套浏览器，使用真实 Saltcorn HTTP 登录、CSRF 表单、字段配置向导（/field/:id）并从物理 SQLite 独立读回人工界面产生的变更**。

- **最终成功运行**：[GitHub Actions Run #44873882208](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44873882208)，completed / success。
- 实验工作流对应提交：[c06838773f1c391c881fdb81b8fa95660f972639](https://github.com/zealzhangz/OpenAILCAP/commit/c06838773f1c391c881fdb81b8fa95660f972639)。
- 独立 Job：136754179909，Artifact 名称 `s1-real-chromium-saltcorn-editor`，ID **14694788713**，包含浏览器/模拟 Agent 两份结构化结果 JSON。
- 被测服务：Saltcorn CLI 1.7.0-beta.5、Node 24、一次性 SQLite、研究管理员身份；Chromium 由 Python Playwright 1.56.0 驱动。
- [脚本/复现说明](../../experiments/platform-saltcorn/browser/README.md)；[Workflow](../../.github/workflows/s1-saltcorn-browser.yml)。
- Saltcorn 固定研究源码：[515254bee5a98df70530cc59846b1df02d5db350](https://github.com/saltcorn/saltcorn/tree/515254bee5a98df70530cc59846b1df02d5db350)。此 SHA 为源码研究版本，npm 固定的是发布版本，**不能声称已校验二者构建字节同一**。

与“静态代码存在编辑路由”不同，这次有可复核的**真实用户表单提交行为及后续物理存储数据**。该管理员为 CI 内临时创建的研究账号，凭据和会话没有提交仓库。

## 2. 两个标签页的真实操作与数据库结果

预注册流程与实际证据：

| ID | 操作/验收 | 真实结果 | 状态 |
|---|---|---|---|
| UI01 | 新建合同应用的 title.label 初始值 | Title | PASS |
| UI02 | 浏览器登录研究管理员后打开真实字段编辑器 | /field/7，包含可编辑 label 输入框 | PASS |
| UI03 | 字段向导具备编辑上下文及 CSRF 输入 | contextEnc、_csrf 与其他普通字段均存在 | PASS |
| UI04 | 两个浏览器标签页 A、B 在变更前均打开旧字段 | A=Title，B=Title | PASS |
| UI05 | B 通过真实页面修改保存 | SQLite title.label = Browser B Saved | PASS |
| UI06 | A 随后用旧页面上下文保存同一字段 | SQLite title.label = Browser A Stale Save；**B 的更改被覆盖** | PASS（危险负例） |
| UI07 | 第三个页面重新打开字段编辑器 | 显示 Browser A Stale Save | PASS |
| UI08 | 匿名浏览器直接打开字段编辑页 | 重定向到 /auth/login?dest=%2Ffield%2F7 | PASS（单条匿名访问拒绝行为） |
| UI09 | 追踪正常浏览器向导提交 | 两次编辑总计 6 个真实 POST /field，每个请求均包含 contextEnc 和 _csrf | PASS |

浏览器实验本身 **9/9 检查通过**，但 UI06 的“PASS”指**预注册的危险覆盖确实发生**。它不表示多用户并行编辑有可靠冲突治理。

补充技术细节：两标签页是在**同一个认证浏览器上下文**打开，它们在同一字段内容的旧版本上分别编辑，但提交顺序是 B 后 A，并非网络请求同时发送。该实验研究的是**过时编辑上下文**，与前轮两个独立进程真实 SQLite 并发事务测试的研究问题不同。

## 3. 已发生的真实人工修改为什么没有让 Agent 侧账本变更？

在浏览器操作前，实验创建了一个**刻意独立于 Saltcorn 原生字段写入**的侧边版本表，记录 title revision=0。

B、A 两次正常 Web 编辑都通过 Saltcorn 自己的字段编辑流程成功保存。但由于该外部实验版本表**不在浏览器写入路径上**，其 revision 仍然是 0。接下来确定性 CLI 程序（**模拟** Agent，不是真正 LLM/工具调用）只检查研究账本 expectedRevision=0，就把 title.label 改成 Agent Overwrites Browser，并将其账本修订为 1。

后置独立 SQLite 与 HTTP 验收：

| ID | 实测条件 | 状态 |
|---|---|---|
| U10 | 真实浏览器曾保存的字段被模拟 Agent 改写为 Agent Overwrites Browser | PASS（危险负例） |
| U11 | 只由模拟 Agent 更新的外部版本账本最后为 1 | PASS |
| U12 | HT-2026-000001、amount_minor=100000001 的合同记录未丢失 | PASS |
| U13-REST | HTTP /api/s1_contracts/ 200，并能返回合同编号 | PASS |
| U13-HTML | HTTP /view/s1_contract_list 200，并能渲染合同编号 | PASS |

后置验证 **5/5 通过**。其技术意义是**真实浏览器的更新不是“模拟”，外部 Agent 账本却无法识别真实 Web 更改**。即使 Agent 自己的账本更新与资源写入都执行了原子 SQL，也无法补偿不受账本治理的人工入口。

不能将此结论不加限定地套用到 Saltcorn 的所有版本或全部 UI：本次仅在指定 CLI 版本的合同 title 字段编辑路由实测。

## 4. 上游一手源码的对应关系

- [认证路由](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/server/auth/routes.ts)：GET /auth/login、POST /auth/login 使用 Passport local，并处理 Session/跳转。
- [字段编辑路由](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/server/routes/fields.ts)：GET /field/:id 读取 Field.findOne，使用 fieldFlow 初始化向导，renderForm(...,req.csrfToken()) 返回真实页面；POST /field 通过 isAdminOrHasConfigMinRole 限权，在 fieldFlow.onDone 中调用 Field.update 并刷新。
- [工作流向导](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/saltcorn-data/models/workflow.ts)：将前一步的资源上下文序列化到 contextEnc 隐藏表单字段；POST 解析后继续向导步骤。
- [原生 Field 模型](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/saltcorn-data/models/field.ts)：更新真实数据库元数据并刷新模型状态。

**静态与动态证据一致**：本次请求确实携带 contextEnc、_csrf，并经字段编辑路由最终写入 SQLite。字段路由源码中没有发现 expectedRevision / If-Match / ETag 的处理；更关键的运行时事实是 B 修改已成功之后 A 的旧表单被接受，并且实际覆盖了 B 的值。因此，不需要凭“源码里搜索不到版本字段”就主观宣布它一定会失败：已有真实反例。

## 5. CI 自身发现的环境阻断与修复

第一次 [Run #44873783039](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44873783039) 状态 failure，失败在**安装 Chromium 前**：当时 GitHub 的 ubuntu-latest 指向 Ubuntu 26.04，固定 Playwright 1.56 不支持该 Linux 版本，返回 `ERROR: Playwright does not support chromium on ubuntu26.04-x64`。

研究工程改为**显式固定 ubuntu-24.04**，再次运行 [#44873882208](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44873882208) 后，浏览器安装、真实平台安装、创建管理员、浏览器 UI 和后置数据库/API 验证全部 success。应将第一次视为 CI 工具环境兼容失败，**不是低代码平台业务测试失败**。

## 6. 对 OpenAILCAP H01/H03/ADR 的约束

**H03 核心判断比上轮更强**：此前从高权限 CLI 证明“外部修改绕过账本会丢更新”，现由**真实人工浏览器页面**再次触发并验证了这个失效条件。OpenAILCAP 的三个开发模式（AI 配置、AI 代码、传统人工）必须采用统一可审计版本模型，所有编辑器、Agent 工具、插件和代码工作区都不得存在可绕过的生产编辑路径。

研究候选接口应提供：

1. 可信身份、应用/资源/操作级授权；CSRF 保护 Web 用户，与 Agent 工具凭据/委托机制分离。
2. 所有写入必须进入同一版本及指纹维护范围，原子比对 expectedRevision / content fingerprint，冲突返回明示 409。
3. 精确 Patch 并约束修改范围，不允许旧完整应用快照覆盖未触及资源。
4. 对同字段冲突失败关闭；非重叠变更可采用三方合并，但要验证引用、代码和业务行为。
5. 独立验收及失败回滚必须和草稿提交/生产部署分层。

**尚未验证**：在 Saltcorn 的真实浏览器中接入上述原子 CAS 服务；真正 LLM Agent 规划、授权工具调用与自动修复；不同真实用户/角色/多租户权限；真实合同审批、Decimal 规则；统一 Application IR vs 分域 Schema 的真实平台对照。

## 7. 对 README 第一阶段 G1 的影响

- 真实 Saltcorn 平台浏览器人工编辑，**首次取得独立成功运行证据**。
- 人工与模拟 Agent 交错编辑的失效机理已在真实 Web + SQL 平台上复现；**这不是 H03 正向通过**。
- 原冻结的合同 TC01—TC18 全面业务验收仍为 **0/18 完整 PASS**；本次针对 title.label 的实验不包括审批/真实 Agent 等强制场景。
- **G1 仍未通过**。下一步应优先实现和比较“真实浏览器写入通过统一安全 API”与“旧浏览器/外部更新经内容指纹同步失败关闭”两种路径，并加入真实用户角色和幂等/审计验证，而不是立即决定统一 IR 或正式 S2 功能树。
