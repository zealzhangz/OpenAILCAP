# S1 报告 37：B4 真实 DeepSeek 自定义代码 → 隔离构建测试 → B2 绑定发布与回滚

**日期：2026-11-21。实测结果：B4 狭窄自定义代码开发研究成功，S1 仍在进行，G1 NOT_PASSED，正式 G1-B01 门禁仍 OPEN。**

## 1. 研究问题及适用范围

前序 [B3 真实模型元数据应用生成实验](36-s1-b3-real-deepseek-typed-plan-evidence.md) 已在已知四种固定低代码资源类型的合同场景下证明模型可以提交合法 Schema；但是低代码既有 Workflow 仅支持**金额决定一/二级审批**，并不包含**合同金额、供应商信用分、合作月份三者联动的风险评分**。如果不能从配置能力缺口升级到自定义代码，OpenAILCAP 只能做固定元数据 DSL 的自动配置。

本轮冻结新场景：保持 B2 合同 Model/Form/View/Workflow 和已发布 v1 不变，新增 Python 纯函数 `score_contract(amount_minor,supplier_score,months_active)`。规定金额边界、供应商评分边界、合作月份、特殊高风险最低 90 分、最高 100 分；使用真实模型**仅提议源代码**，可信控制器执行 AST 限域、Docker 独立编译/432 种业务组合测试、由模拟受授权的人工发布扩展与读取真实合同数据。**不是不受限的 AI 自主编码 Agent**。

## 2. 可核查 GitHub 事实

| 证据 | 实际记录 |
|---|---|
| 源代码及可复现说明 | [experiments/g1-b01-b4](../../experiments/g1-b01-b4/README.md) |
| 工作流 | [.github/workflows/s1-b4-custom-code.yml](../../.github/workflows/s1-b4-custom-code.yml) |
| 已合并 PR | [PR #6](https://github.com/zealzhangz/OpenAILCAP/pull/6) |
| 合并提交 | [5dd3224893a87e1e7a77f91000c38fa023a98d07](https://github.com/zealzhangz/OpenAILCAP/commit/5dd3224893a87e1e7a77f91000c38fa023a98d07) |
| 第一条完全离线成功 | [Actions #44893945547](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44893945547)，已成功；真实模型 0 次 |
| **真正 DeepSeek 自定义代码生成** | [Actions #44894074280](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44894074280)，**completed / success** |
| 实际 Job | **136815855851** |
| 原始日志 + JSON Artifact | [#14702827817](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44894074280/artifacts/14702827817)，名称 `s1-b4-real-custom-code-sandbox` |
| B4 AST 与工具权限对抗单元测试 | **27/27 PASS** |
| 既有 B2 Domain Schema/发布内核回归 | **18/18 PASS** |
| B4 真 Docker + Chromium 离线基线 | **27/27 PASS**，`real_model=false,model_calls=0` |
| B4 真 DeepSeek + Docker + Chromium | **27/27 PASS**，`real_model=true,model_calls=1` |
| 业务隐藏组合测试 | **每个合格源码在真实容器中运行 432 种边界组合（9 金额 × 8 信用 × 6 合作月数）** |
| 实际模型次数 | **一次** DeepSeek `deepseek-flash` Function Calling，`submit_python_rule`，无自动重试 |
| 真实模型代码 SHA-256 | `a6743bd465930afb861302a6fc3bf191c7f2909e019fabad153b7969c77d1d5e` |
| 人工离线样例代码 SHA-256 | `2c866d1ecf6e4d8f2d5d9edebb30255668ce4b80811ffb116e464663bf4ac087` |

上述**两份 SHA-256 不同**，且真实模型运行时的日志直接显示 `S1_B4_LIVE_DEEPSEEK_ONE_FUNCTION_CALL` 与 `B4-09 realModel=true/modelRequests=1`，不允许将人工编写的离线代码冒充 AI 生成。

**失败历史必须保留**：[#44893732072](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44893732072) 初始静态测试 2 个拒绝代码名称期望错误；[#44893761678](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44893761678) 实际低代码 View 三列不含 title，而 Chromium 预期查看合同标题，测试按预注册验收失败；[#44893858760](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44893858760) 发现可信 sandbox worker 将成功的 SystemExit 错误当异常，导致容器退出非零。三处均按实际原因修正测试期望、View 样例字段或可信 Worker 异常处理，**没有关闭模型代码安全校验、缩减 432 条业务 Oracle、或放松 Docker 运行限制**。离线 [#44893945547](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44893945547) 完整成功后才使用一次性 Commit `1f782f90e9917d314050f0bd70b582072e506363` 开启在线验证。

## 3. 本轮真实运行的安全执行链

~~~text
B2 低代码能力目录：form / view / amount_threshold_approval
       |
       | 缺少 supplier_tenure_risk_scoring → CUSTOM_CODE
       v
DeepSeek（一次 Function Calling，仅源代码提议）
       |
       v
可信控制器：固定函数签名 + Python AST 允许清单
     [禁止 import、反射、属性/下标访问、循环、任意 API/DB/Shell]
       |
       v
可信 Docker executor：真实 python:3.13-alpine，本次 image SHA-256
  --network=none --read-only --cap-drop=ALL
  --security-opt=no-new-privileges --user=65534:65534
  --pids-limit=32 --memory=192m --cpus=1
       |
       v
真实编译 + 432 个独立金额/信用/月数边界样例
  不合格 → FAIL → 未 Stage、未发布，B2 v1 不变
  合格   → content-addressed artifact SHA-256
       |
       v
模拟授权人工审查 + 绑定 B2 已发布 Manifest v1
       |
       v
同一 SQLite 原子事务切换 Extension 发布指针
       |
       v
真实 Chromium Session → 已发布 B2 合同 Form/View
  → 认证 /runtime/extensions/risk/{recordId}
  → 按已发布规则独立 Docker 执行评分
~~~

**可信边界**：API Key 仅在最终 Actions 步骤注入；模型没有宿主 Docker Socket、Shell、数据库连接、B2 管理员 Cookie、发布角色和直接发布通道。模型输出只决定代码候选，不能选择构建镜像、修改测试 Oracle 或越权授予自己发布能力。容器执行被 Docker 限制；源代码还须通过单一纯函数 AST 约束。即使模型生成正确代码，代码 Stage/Publish 仍由受信控制器和模拟授权人工执行。

镜像按**本次 Run 拉取后实际 SHA-256 image ID**锁定 Docker 的运行调用，但尚未长期锁死 Docker Hub 上游 digest、执行 SLSA、SBOM 或独立签名校验。此处不宣称生产级恶意代码沙箱安全保证。

## 4. 27 项集成观测的关键链路

| 验证阶段 | 原始观测与测试 |
|---|---|
| 架构能力发现 | B2 原有金额审批命中 `LOW_CODE`；供应商信用与年限复合风险需要 `CUSTOM_CODE`（B4-02、03） |
| B2 真实合同基线 | 4 种元数据经可信 mutation API 写入、发布 B2 v1、表单写入 2 条真实 SQLite 合同记录、Chromium 浏览器看到合同标题与金额（B4-04—08） |
| 真模型/静态闸门 | 真模型 Function Calling 提议源码，明确 1 次；AST 通过后生成与人工基线不同的代码 SHA，模型没有直接代码执行权（B4-09） |
| 真实隔离编译/自动测试 | **真实 Docker** 内代码实际执行，432 项独立 Oracle 完整通过；未经授权的 import 不进入执行，正确语法但错误评分逻辑被真实运行测试拒绝（B4-10—12） |
| 失败不能发布 | 错误代码后的 Artifact=0、代码发布记录=0、指针=0、B2 v1 不变（B4-13） |
| 权限+验收绑定 | Agent 无权 Stage 或 Publish；不完整测试回执被拒绝；经人工审核的合格源代码 Stage 绑定 B2 Manifest/v1（B4-14—17） |
| 发布事务保护 | 注入故障抛错后扩展发布记录和当前指针都回滚，无已发布应用中断；之后正确发布 Extension v1（B4-18、19） |
| 真正合同运行态代码组合 | 真 Chromium 登录会话访问 B2 风险扩展 API，**高风险合同** 600000001 分、信用20、合作3月 → **risk=95/HIGH**；**低风险合同** 100000000 分、信用88、合作50月 → **risk=0/LOW**（B4-20、21） |
| 身份隔离 | 匿名 HTTP **401**；app-a 会话试图调用 app-b 扩展 **403**（B4-22） |
| 代码人工编辑与回滚 | 测试模拟人工在**模型生成的源码**中增加注释，重新真实 Docker 完成 432 条测试；发布独立代码 v2，再把代码指针回到 v1（B4-23） |
| 代码发布并发控制 | 旧代码发布预期版本不一致 → **409**，指针不变（B4-24） |
| 草稿与已发布版本隔离 | 人工修改 B2 Draft Form 后，B2 v1 已发布代码继续正常评分 95（B4-25） |
| 元数据版本一致性 | B2 正式发布 v2 后，旧代码绑定 B2 v1 的运行请求 **409 B2_RELEASE_CHANGED**；B2 发布指针回滚到 v1 后，代码执行恢复 HTTP 200（B4-26） |
| 独立 SQL 复核 | app-a **2 个不可变代码 Artifact、2 次代码发布记录、代码指针 v1**；app-b 仍 0 revision、0 Artifact；审计记录有代码 Publish/Rollback（B4-27） |

**研究中的“人工”操作**是 Chromium 驱动的管理员模拟会话，以及可信测试编排器显式以人工审核权限调用 Artifact Stage/Publish；**不是实际自然人的手工审核**。实际 AI 生成只是一次纯函数提议，后续代码注释由确定性代码模拟人工添加，**没有让模型再次调用修复或再开发**。

## 5. 适用性、反例与架构意义

**已证实（受限条件）**：B2 已发布低代码应用可以通过单独的版本/哈希绑定承载不可由既有 Workflow 表达的自定义 Python 业务规则；真实 DeepSeek 可以在固定 API 签名与严谨代码约束下生成可编译、通过 432 组隐藏边界测试的实际源码；隔离容器可真实执行；代码不合规/测试失败/发布故障/过时 B2 Schema 均不会隐式切换已发布代码版本。

**尚未证实**：模型自主发现未知平台能力、生成任意工程项目或完整前后端代码、代码仓库工作区/Git Worktree 管理、真实 AI 多轮定位失败与自动修复、第三方库依赖与供应链安全、真实插件沙箱、复杂多语言构建、通用 Schema 迁移、合同权限业务审批人的身份与组织关系、跨服务分布式事务、完整 Kubernetes/云生产部署，以及经过人工真正审核/批准。这里的“Build”指严格限域 Python **源代码通过真实容器编译并通过测试**，不是 npm/Maven 或容器镜像工程构建，也没有生成独立部署镜像。代码与 B2 的关系仍由**研究 Companion Registry** 实现，非正式统一内核。

**风险与下一研究**：纯函数 AST 白名单强约束使风险极小、结果可控，但显著降低编程表达范围。正式平台必须建立可信代码能力发现、工作区隔离、依赖升级与制品签名、代码修改差异审查、工程级自动构建与有限次失败修复。还应与“不使用统一 Application IR”的 Domain Schema + Manifest 方案做**公平的同业务对照实验**，并明确生产容器编排中多实例与版本迁移的原子边界。

## 6. G1 门禁复审

- **S1**：IN_PROGRESS；**G1 NOT_PASSED**。
- **G1-B01**：PARTIALLY VALIDATED / OPEN。B4 提供的是自研 B2+纯函数代码扩展的真实 PoC 正向证据，不意味着 Saltcorn 原生、CLI、任意插件或直接数据库所有修改路径都已通过同一强制治理门禁。
- **冻结 W01—W24**：**0/24 FULL PASS**（不能将 B4-01—27 误算为 W01—W24）。
- **冻结 TC01—TC18**：**0/18 FULL PASS**。
- **下一优先级**：统一 Kernel/Plugin 执行器安全、Domain Schema+Manifest 与全局 IR 受控对照，以及代码构建失败的有限次真实 AI 修复闭环；不为追求继续调用模型而无意义重复同一固定纯函数实验。
