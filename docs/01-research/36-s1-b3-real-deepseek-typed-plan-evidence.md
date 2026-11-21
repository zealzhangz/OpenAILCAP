# S1 报告 36：一次真实 DeepSeek 计划生成 → 可信工具执行 → 人机交替 → 合同运行态验证

**日期：2026-11-21。结论：真实 DeepSeek 一次受限 Function Calling 提议已实际生成并写入可运行的 B2 元数据定义；真实 Chromium 与独立 SQLite Oracle 检查 24/24 PASS。属于固定合同领域的窄域正向证据，绝非完整 PoC-A、G1、正式生产平台或自主 AI 软件工程全流程完成。**

## 1. 问题与研究假设

前轮 [B1 真实三写入者研究](34-g1-b01-b1-browser-agent-plugin-evidence.md) 和 [B2 领域 Schema/Manifest/合同运行态研究](35-s1-b2-schema-runtime-manifest-evidence.md) 已获得零模型、类型化工具和应用运行态证据。但是 B2 的四类应用元数据定义均来自人类预写的 JSON 测试样例，**还不能证明模型能够从自然语言需求生成合法的应用模型**。

本轮只验证较窄、可明确裁判的假设：**在固定合同场景、确定允许的字段/资源能力和强制预检下，真实模型能否通过一个 Function Calling 提出四项元数据资源，且服务端能够在模型没有数据库/发布权限的情况下把提议转为运行中的合同应用，并安全允许人工接手。**

不能把此结果外推到未知复杂需求、自然语言自主多轮消歧、自定义代码生成、通用业务流程语言、生产发布和真正可视化拖拽。

## 2. 真实 GitHub 证据

| 证据 | 实测数据 |
|---|---|
| 源码目录 | [experiments/g1-b01-b3](../../experiments/g1-b01-b3/README.md) |
| CI 工作流 | [.github/workflows/s1-b3-deepseek-app.yml](../../.github/workflows/s1-b3-deepseek-app.yml) |
| PR | [#5](https://github.com/zealzhangz/OpenAILCAP/pull/5)，已合并 |
| Squash 合并 SHA | [8e7951eadfd634bc2334995d4d49256b6938bd3e](https://github.com/zealzhangz/OpenAILCAP/commit/8e7951eadfd634bc2334995d4d49256b6938bd3e) |
| **真正 DeepSeek 实验 CI** | [Run #44891826332](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44891826332)，**completed / success** |
| 真实 Job | **136809104025** |
| 原始 JSON + 日志 Artifact | [#14702700418](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44891826332/artifacts/14702700418)，`s1-b3-deepseek-typed-plan-evidence` |
| 首次完全离线成功 | [Run #44891709859](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44891709859)，**18 B3 adversarial + 18 B2 regression + 24 E2E / 0 外部调用** |
| 真实模型试验当次离线预检 | **B3 18/18、B2 18/18、Chromium Offline 24/24**；`real_model=false` |
| 真实模型试验 | **Chromium Live 24/24**，`real_model=true`，B3-04 原始日志 `actual_model_requests=1` |
| 外部 DeepSeek 调用 | **一次 HTTPS POST**，`deepseek-flash`，Function Calling **一个 `propose_application_plan`**，无重试；实际 Token 统计如原始 Artifact |
| GitHub Secret | 使用已有 Actions Secret `DEEPSEEK_KEY`，只注入运行真实模型的独立步骤；Secret、Cookie、Bearer 均未写入 Git 或验收 Artifact |

注意：虽然整次成功 CI 包含 18+18+24+24 组检查，但它们是不同层面、部分复用的研究断言，**不能把 84 次检查当成 84 个独立企业级产品功能**。

### 失败历史透明记录

第一次新设计方案 [Run #44891660938](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44891660938) 在 **B3 离线安全校验**阶段失败：人写的旧 B2 合同 View 基线没有 title 列，但本轮要求模型生成“编号、标题、金额、状态”四列，因此语义 Oracle 正确拒绝旧参考样例（`SEMANTIC_VIEW_MISMATCH`）。仅修正**明确标注为非 AI 的 B3 离线预检样例**，补全 View title 列；不降低 Oracle、不修改真实模型回答。随后 [#44891709859](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44891709859) 离线全部成功，**才**提交唯一带标记的 Commit `781dd0c407ac47671d45762591a6d7e26fb91189` 触发一次真实模型验证。后续 PR #5 squash 合并不继承此 HEAD 标记，降低意外重复调用风险。

## 3. 实际模型请求和受限制执行

用户需求是中文合同管理：合同编号、标题、金额（万元阈值转换为人民币整数分）、审批状态；登记表单、台账列表；金额**严格大于 100 万元**必须二级审批，**等于或小于**走一级。

出于节约模型调用和隔离风险，系统提示词明确允许的资源 ID、字段标准名、数据类型、模型引用、单位和阈值；**没有把原始完整四份 JSON 元数据定义当作模型工具响应复制**。模型需要按受限契约组装 4 项 `operations`：

1. DataModel `model.contracts`：四个强类型字段，金额 `amount_minor` 为非负整数分；
2. Form `form.contracts`：`contract_no,title,amount_minor`；
3. View `view.contracts`：编号、标题、金额、状态四列；
4. Workflow `workflow.approval`：固定 `thresholdMinor=100000000`，金额/状态字段必须引用实际模型。

模型只调用 `propose_application_plan`；真实 `choices[].message.tool_calls` 包含**唯一一个**正确工具名。验证器 [plan.py](../../experiments/g1-b01-b3/plan.py) 逐条检查：顶层只有 operations、四类资源顺序与数量固定、每项正确定义与类型/字段/引用闭包、正确金额单位及阈值、不出现额外 actor/schema/SQL 或危险 HTML。任何错误均由服务端拒绝且不执行，绝不能因为 LLM 自称成功而放行。18 项安全与格式负对照均成功。

**执行边界**：模型完全不知道且拿不到 Agent Bearer、管理员 Cookie/CSRF、SQLite 文件路径或发布权限。独立 Python 工具进程 [apply_plan.py](../../experiments/g1-b01-b3/apply_plan.py) 只接收可信控制器通过校验后的 JSON，用受限 Bearer 访问 `GET /v2/apps/app-a/draft` 和 `POST /v2/apps/app-a/commands`，按权威快照的 `appRevision/resourceRevision/contentHash` 顺序提交；真实独立物理 SQL 校验 4 次 Agent 元数据变更，并匹配 Manifest SHA-256。没有模型生成 Python/JS、没有任意 Shell 工具、没有自动授权发布。

## 4. 真正端到端 24 项验收的核心现象

| 真实场景 | 独立观察 | CI |
|---|---|---|
| 真实 Chromium 登录研究人工设计器 | 无登录跳转；实际 Session 后看到空草稿 | B3-01—03 PASS |
| 一次**真实模型**生成四项合法 typed schema | `inference=true`，`actual_model_requests=1`，四种资源均在可信 Oracle 中验证 | B3-04 PASS |
| 独立 Agent 工具进程真实 HTTP 写入 | **4 次**成功写入；物理 app revision=4、审计主体为 Agent、Manifest hash 一致 | B3-05—07 PASS |
| 浏览器查看 AI 创建的资源 | 真 DOM 显示 4 个资源、revision=4，两标签页都持旧基线 | B3-08—09 PASS |
| AI→人工→Agent 交替编辑 | 人工调整 Form 标题，rev5；Agent 旧基线 HTTP 409；受控重新读取后修改 View，rev6，人工 Form 不丢 | B3-10—12 PASS |
| 旧人工标签页尝试覆盖、重新加载 | 旧浏览器 HTTP **409 APP_REVISION_CONFLICT**；重新加载后可看到 Agent 修改 | B3-13—14 PASS |
| 发布权限与不可变 Snapshot | Agent 发布 HTTP **403 PUBLISH_FORBIDDEN**；研究中由 Chromium 模拟的受权人工会话点击发布，Release v1 hash 与物理 SQL 匹配 | B3-15—16 PASS |
| 真实低代码 Form 校验与合同落库 | 文本金额被 **422 TYPE_MISMATCH**；真实写入 100000001 分与 100000000 分两条合同数据 | B3-17—18 PASS |
| 金额阈值真实 Workflow | 超阈值 Draft→PendingLevel1→PendingLevel2→Approved；恰好阈值 Draft→PendingLevel1→Approved | B3-19 PASS |
| 真实 Chromium 已发布 View | 发布版 View 通过 HTTP 读取两条合同和四列 Schema，并在 DOM 渲染 | B3-20 PASS |
| 引用完整性、身份边界 | 已有 Form/View 引用时删除 Model 被 **422**；真实浏览器 Session Cookie 缺 CSRF 被 **403** | B3-21—22 PASS |
| 物理 SQL 与多应用隔离 | app-a revision=6、receipt=7、已发布 v1；app-b revision=0；Agent/人工审计均存在 | B3-23 PASS |
| AI 真实调用不能被离线替代 | `real_model=true` 与 `actual_external_model_calls=1` 均独立检查，模型提议最终有运行态 Oracle | B3-24 PASS |

**明确说明**：从人工在真实 Chromium 继续编辑后的第二次 View 改名，是可信研究控制器依据**最初已验证模型计划**派生的确定性变更，用来验证持旧版本拒绝和重新加载，**不是第二次调用 DeepSeek 或另一次自主 AI 规划**。发布操作是 Playwright 模拟受权人工会话点击，**不是自然人实际审批或生产发布授权**。这里的 Workflow 是 B2 固定状态机的运行，不是 DeepSeek 生成任意动态 BPMN 或代码引擎。

## 5. 研究证据意味着什么、不意味着什么

已经取得直接证据的是：

- 真实 DeepSeek 能在给定受限能力目录、资源 ID 和业务规则的条件下提出**完整可运行的四类元数据配置**；
- 可信命令服务能够对模型的输出独立检查并逐步应用，模型没有直接写库/发布权限；
- 真正 Chromium 人工修改后，Agent 经版本/哈希约束安全接手，并最终通过真实 Form/View/Workflow 和独立 SQL Oracle 验证，研究发布快照成功。

**没有取得证据**的是：任意自然语言自主规划开发、复杂实体关系/主从数据/真实组织审批、代码生成→编译→测试→修复→部署、真实插件沙箱、生产数据库/SSO/安全治理、多实例分布式部署、不可逆外部副作用补偿、开放插件调用、成熟可视低代码设计器。Schema contract 对模型限制较多，不能据此证明模型在**没有**能力说明时也会自行发现平台 API 或正确设计复杂应用。

虽然本轮已包含真正 LLM，它仍只是 [B2](35-s1-b2-schema-runtime-manifest-evidence.md) 上“固定领域受治理元数据生成与执行”这一**窄域的 PoC-A 子实验**；完整 PoC-A/B/C/D、G1 和 G3 标准不因此变成 PASS。

## 6. G1 复审与下一研究风险

- **S1 当前**：继续进行；**G1 NOT_PASSED**。
- **G1-B01 写入治理**：C1/B1/B2/B3 相继得到机制和真实模型侧证据，仍有真实插件沙箱、生产 DB 旁路、领域元数据动态 Schema/迁移与正式身份等缺口，状态 **PARTIALLY VALIDATED / OPEN**。
- **原冻结 W01—W24**：仍然 **0/24 FULL PASS**，不以 B3 24 项等量替换正式 W 测试。
- **原冻结合同 TC01—TC18**：仍然 **0/18 FULL PASS**。
- **本轮成本**：外部 DeepSeek 推理恰好**一次请求**；详细 Token 见 Artifact，不做重复付费调用。

**下一研究最小可验证假设**：在固定低代码能力不满足某项复杂业务计算时，Agent 能否在**无任意 Shell/DB 权限**的隔离工作区生成受限自定义代码，完成真实编译/测试与构建产物治理，并在构建失败时保持当前发布指针不变。与“元数据配置就能满足所有业务”做真正 A/B 对照。此项完成前不应开启生产自动发布。
