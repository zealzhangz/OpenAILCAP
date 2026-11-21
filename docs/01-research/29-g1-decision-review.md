# S1 G1 综合评审与门禁决策（2026-11-21）

> **决策：CONDITIONAL GO（仅允许准备 S2 的受限产品范围讨论，不等同 G1 正式通过）；G1 Gate Status = NOT_PASSED。** 本文是 S1 综合评审基线，不因文档数量增加自动改变门禁。正式开启 S2 完整需求设计仍需明确处理下述 P0 阻断并形成有责任人的复审决定。

## 1. 评审范围与证据

依据仓库 [README](../../README.md) 第一阶段 1.1—1.5 和 G1 五项门槛，[综合研究](28-s1-synthesis-and-architecture-comparison.md)、[ADR-002](28-adr-domain-schema-manifest.md)、[既有中期 G1 复审](12-g1-gap-review.md)。复审的基线为 `07cf929471f7f3bba9f93579916b7da4dea6ca33` 及其此前 GitHub CI 证据，不把本轮文字提交算成新的技术实验。

## 2. 证据状态和门槛

| G1 问题 | 目前可确认的答案 | 证据等级 | 评审 |
|---|---|---|---|
| 哪些现有机制可借鉴 | ToolJet MCP 的 typed plan/diff、Appsmith 的 registry/publish state、Budibase 的 binding/actions、NocoBase v3 plugin/runner 边界；Saltcorn Table/Trigger+真实应用运行机制 | 四平台 S1/S2；Saltcorn S0 | **满足研究性识别**；不是代码级可复用许可 |
| 哪些机制不能直接复用 | ToolJet CE Code Mode stub/EE 边界；NocoBase v3 LICENSE 附加条款；Saltcorn 无保护 Pack 和原生旧 Web 表单；业务 Agent≠开发 Agent | S1/S0 | **满足初步排除**，后续许可需审核 |
| 哪些问题需自主创新 | 全渠道强制写入、CAS/审计/幂等、跨 Schema 引用与发布快照、能力发现与安全工具代理 | 部分 S0 正反实验 | **明确研究方向，但工程仍未实现** |
| 最关键技术风险 | 原生设计器绕过事务门禁导致静默覆盖；外部调用未知结果重复副作用；代码执行/插件越权；许可证；混合应用跨域版本一致性 | S0/S1 | **已定位风险**，并未消除 |
| 下一阶段优先假设 | H03 全路径统一编辑；H01 IR vs Schema+Manifest；H02/H04 真正 AI 创建代码与自动验证；H05/H07 插件授权；H06 双应用隔离 | 已给可证伪 PoC | **可为 S2 做范围假设，不可据此过 G3** |

## 3. 实测审计（不要混用计数口径）

1. 真实 DeepSeek 只读工具协议 [25](25-deepseek-real-tool-call.md)，30/30 集成，模型曾实际返回工具调用；证据仅限一次小样本。
2. 真实模型配置/代码/混合路由 [26](26-deepseek-mode-route-evidence.md)，6/6 选择，20/20 实际 Saltcorn 平台断言；原生能力/JS Trigger 预装。
3. 真正 Chromium + DeepSeek + SQLite [27](27-real-deepseek-human-roundtrip-evidence.md)，8/8 单元、16/16 集成；仅顺序非冲突场景，Playwright 为模拟人工操作。
4. 旧浏览器并发编辑覆盖 [19](19-real-browser-edit-evidence.md) 是已复现的**失败行为**；研究网关 [20](20-governed-http-evidence.md) 的正确拒绝只对走网关的客户端有效。
5. 完整冻结合同 benchmark [10](10-contract-benchmark.md)：**0/18 FULL PASS**，不得由 35/35 Trigger、32/32 身份和 16/16 交接子断言推出合同业务全部验收成功。
6. NocoBase v3 官方模板 E530 导致安装未完成 [11](11-installation-trial.md)；其功能不能记为本阶段真实平台通过。

## 4. P0 阻断、性质及继续条件

| 编号 | 阻断 | S1 能否靠整理报告解决 | S2/S3 的硬要求 |
|---|---|---|---|
| G1-B01 | 完整原生编辑路径无统一强制修订/指纹/CAS，存在确定的旧表单覆盖 | **不能** | S2 明确不可绕过的写入契约，S3 PoC 必须让原生 Web、Agent、插件统一受控且独立负例回归 |
| G1-B02 | 未由 LLM 自主创建模型/页面/JS 代码，也未完成受限构建/自动测试/部署 | **不能** | S2 固定最小真实开发旅程；S3 PoC-A/B 必须真实执行 |
| G1-B03 | 冻结合同 18 项未达到完整平台验收 | **不能** | 将缺口拆分为精确金额、真实权限码、浏览器审批、代码生成、发布等，不准改低标准假冒通过 |
| G1-B04 | NocoBase v3 创建器不可复现、其他三平台主要仍是静态研究 | 部分可以做资料收口，但不能凭静态研究变运行证据 | 需要用现有 Saltcorn S0 明确限制进行路线决策；如要直接选他家平台为内核，必须补实际部署 |
| G1-B05 | NocoBase v3 与 ToolJet EE 许可/源码复用可行性未获授权性结论 | **不能靠工程测试解决** | 原则上只借鉴架构机制；拟复制源码前逐文件合规及必要法律审查 |

## 5. 裁决理由

G1 已能回答“值得借鉴什么、要避免什么、何处自主开发、风险先后和后续实验”。这足以**冻结 S1 研究方向，并允许有限地组织 S2 MVP 需求假设**，但还不足以宣称“目标平台已验证”或“完整 S1/G1 通过”。

两套 Application IR / 分域 Schema+Manifest 在模型级样本均成功；唯一稳固的负结论是**未经统一治理的全量或过时写入不可作为默认 AI 编辑模式**。ADR-S1-002 选择后者作为 S3 对照优先组，不意味着已选框架、数据库、Agent 产品或低代码内核。

## 6. S1 交付物清点

| README 1.5 交付物 | 对应资产 | 现状 |
|---|---|---|
| 开源低代码深度研究报告 | [综合研究 28](28-s1-synthesis-and-architecture-comparison.md) + 分项 04/07/14—27 | **已有综合版，部分平台缺真实部署** |
| 低代码/AI 对照矩阵 | [09](09-capability-matrix.md) + JSON | **已交付，四平台静态证据，Saltcorn S0 在报告中独立列示** |
| 核心技术源码证据 | [02](02-evidence.md) | **已交付，附固定 SHA 与断点** |
| 关键架构机制研究 | [综合 28](28-s1-synthesis-and-architecture-comparison.md) + 16/18/19/20/23/24/27 | **已交付研究与反例** |
| 可借鉴与应避免清单 | [综合 28 §5](28-s1-synthesis-and-architecture-comparison.md) | **已交付** |
| 核心假设与验证计划 | [H01—H08](../00-foundation/01-hypotheses.md)、[03](03-experiments.md)、[ADR-002](28-adr-domain-schema-manifest.md) | **已交付；假设并非全面 PASS** |

## 7. 下一步顺序及停止规则

**P0**：针对全渠道编辑一致性建立可证伪的接口契约和三写入者（原生 Web、Agent、插件）路径图；若不能收拢所有写入口，则拒绝自动提交。此为架构路线阻断，不能通过多跑一次模型任务解决。

**P1**：S2 只拟定支持合同纵向切片的最小产品范围和人工/AI 两条等价开发旅程，预注册 PoC-A/B/C/D；避免完整产品功能穷举。

**P2**：S3 对照“全局 IR vs 分域 Schema+Manifest”，并执行真实生成代码、独立构建/测试/隔离、发布回滚与跨应用权限测试。

**停止规则**：若无法使可视编辑器、工具和插件强制共享权威版本语义，禁止把任何 Agent 路径的 CAS 子测试通过视为平台 H03 通过；若无法封闭动态代码权限，限制自动代码开发为人工批准模式；若许可不允许，改为接口级观察而不复制源码。

## 8. 门禁记录

- **G1 当前正式状态：NOT_PASSED**
- **研究建议：CONDITIONAL GO，仅供 S2 范围预研/PoC 设计准备；不代表解锁正式 S2**
- **风险最严重项：G1-B01**
- **新运行/新的 DeepSeek 调用：本轮无**
- **下一次可改变门禁状态的证据**：至少全渠道强制写入 PoC 的正反验收，或正式书面接受 G1 将该风险作为 S3 强制解决项并定义退出条件。任何门禁放宽均须明示理由和风险所有者。


## 2026-11-21：C1 最小写入服务真正实现及 CI 复审

[报告 32](32-g1-b01-c1-real-ci-evidence.md) 与 [Actions #44886944054](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44886944054) 已确认：独立 Python 3.13 / SQLite / localhost HTTP C1 受治理写入服务的 **31/31 unittest 实际执行通过**，包含同一数据库真实双进程版本竞争、幂等回执、三类测试身份的共用 HTTP 路径、物理回滚、旁路 SQL 漂移隔离、CSRF/只读/跨应用拒绝。CI Artifact 14699494263，PR #1 已合并。31 次测试执行包括继承测试重复运行，只有 18 个独立测试方法定义，不能直接折算为原生平台 24 项验收。

**阻断项 G1-B01 仍 OPEN**：C1 不使用 Saltcorn 原生 Field.update/原生浏览器设计器，不包含真正插件运行，不修复此前原生 stale-form 覆盖事实。冻结 W01—W24 **0/24 完整 PASS**、TC01—TC18 **0/18 完整 PASS**。正式门禁仍 **NOT_PASSED**。下一次应进入 C2 原生真实写入接入的正反测试；不可用付费模型成功调用代替编辑安全性证明。


## 2026-11-21：C2 原生字段编辑器正向保护与 CLI 旁路负对照

新增 [报告 33](33-g1-b01-c2-native-route-evidence.md)，[真实 Actions #44887680474](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44887680474)，Artifact 14699859357。经一次性修改已安装 Saltcorn 1.7.0-beta.5 编译后的原生 /field 路由，在真正 Chromium 管理员两标签页的**顺序旧表单场景**中，B 成功保存原生字段，A 使用旧表单第三次 POST 得到明确 HTTP **409**，物理标签保留 B；新标签页仍可继续保存。浏览器 8/8 符合预期。然而真正原生 `saltcorn run-js` 的 `Field.update` **依然绕过浏览器保护**，独立 SQLite 物理读回确认 1/1 危险负对照。该临时补丁只做写前比较，不具备同事务 compare-and-swap，严禁视为生产修复。

结论：**G1-B01 OPEN / G1 NOT_PASSED**。 C2 已确认原生顺序 409 在研究版本可实现，同时反证“只修补浏览器路由”能满足全渠道强制一致性。W01—W24 原冻结验收仍 0/24 FULL PASS，不把带漏洞的通过当系统安全。后续优先真正统一模型层强制写入，或 C1 自研最小人工设计器，必须包含插件/CLI/Pack/Agent 等路径。


## 2026-11-21：B1 真实人工编辑器 + Agent/Plugin 统一命令实验复审

新增 [实测报告 34](34-g1-b01-b1-browser-agent-plugin-evidence.md) 与 [真实 GitHub Actions #44888692681](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44888692681)，completed/success；B1 自研两字段浏览器的 18/18 独立端到端断言通过，既有 C1 31/31 执行实例回归通过。真实 HTML/Session/CSRF、两个 Chromium 持旧页面、双向 Web↔Agent 409、Plugin 独立工具进程服务器端字段级 403、Agent/Plugin 双 OS 进程同版本竞争一胜一拒、应用隔离及独立物理 SQLite/审计/回执核验都取得证据。PR #3 已合并（`a0eff9d11ce4c96a0fed8bb53aac8afa0364b82a`），Artifact 14701406504。第一次 Run #44888560840 的 CSP/Playwright unsafe-eval 测试脚本失败修复时**没有放宽 CSP**。

**评审决策不改变**：B1 是**我们控制的最小两字段研究 Web**，不是第三方 Saltcorn 原生设计器、成熟低代码 Designer 或真实插件沙箱；Agent 为无 LLM 的固定 tool 客户端。生产动态插件隔离、DB 旁路治理、跨域 Schema/Manifest 引用、版本发布、自动代码生成与回滚等未完成。**G1-B01 PARTIALLY VALIDATED / OPEN；G1 继续 NOT_PASSED；W01—W24 0/24 FULL PASS；TC01—TC18 0/18 FULL PASS**。下一 PoC 重点应由 label 编辑扩展至真实 DataModel/Form/View/Workflow 与不可变发布闭包，而不是重复狭窄 CAS 断言。


## 2026-11-21：B2 Schema + Manifest 真实运行证据与 G1 再复审

[研究报告 35](35-s1-b2-schema-runtime-manifest-evidence.md) 与 [Actions #44889712124](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44889712124) confirmed completed/success：**18 项 SQLite 引擎单测 + 27 项真正 Chromium/独立 Agent 工具进程的业务端到端检查全部通过**，Artifact 14700803450。PR #4 已合并 main。新验证包含 4 类受限元数据资源 DataModel/Form/View/Workflow、全应用 Manifest hash/revision、真实 HTTP 人工↔Agent 旧草稿双向 409、跨资源删除与断引用 422、Agent 发布 403、物理表单记录、100000001 分二级与 100000000 分一级审批、版本 v1/v2 发布/rollback、旁路 SQL 后草稿 QUARANTINED 同时旧已验证运行态可读。未使用 DeepSeek API。

**新的研究判断**：Domain Schema + 派生 Manifest 并非只能停留在概念模型，可以在 4 类最小对象上保持可执行的引用/运行/发布闭环。这是可证伪的**候选正向证据**，不等于已经与完整 Application IR 进行等能力工程对照并确认胜出。

**G1 仍 NOT_PASSED，G1-B01 OPEN**：B2 是对 C1 机制的独立泛化原型，不是已归并的单内核；Agent 不是 LLM 自主需求理解，UI 只编辑受限 JSON，工作流不具备真实审批人的组织权限，插件沙箱/代码生成/多 DB/生产发布/迁移/上游平台全路径拦截仍缺失。冻结 W01—W24 仍 **0/24 FULL PASS**，TC01—TC18 **0/18 FULL PASS**。下一阶段优先对真实 LLM 生成受 Schema 审核的安全工具操作做一次受限实测，并以运行态 Oracle 决定是否通过，而非只看模型输出格式。


## 2026-11-21：B3 真实大模型狭窄低代码创建闭环及 G1 再复审

新增 [报告 36](36-s1-b3-real-deepseek-typed-plan-evidence.md)。[Actions #44891826332](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44891826332) completed/success，**DEEPSEEK_KEY 真正发起一次模型 Function Calling 请求**，`actual_model_requests=1`，非离线假冒；B3 在线 24/24、离线 24/24，B3 18 项提议审查与 B2 18 项回归也全部通过；原始 Artifact 14702700418。模型提议的四类合同 Schema 由严格服务器端引用/类型/金额语义验证，实际独立 Agent HTTP 工具提交，物理 SQLite app revision/hash 正确；真 Chromium 与 Agent 交替编辑双向 409，Agent 发布被 403，模拟受权人工发布 v1，金额 100000001 分二级/100000000 分一级审批与运行 View 验证。PR #5 squash 合并 SHA `8e7951eadfd634bc2334995d4d49256b6938bd3e`，并保留首次离线拒绝旧 B2 三列 View 基线的 [负对照 #44891660938](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44891660938)。

**正向判断**：AI 模型与 Schema/Manifest 低代码元数据内核可以通过“模型仅提议→独立验证→可信工具执行→真实运行结果独立裁判”融合，固定合同资源的最小闭环已有真实模型证据。**但是**提示词已提供固定资源 ID、字段和类型、阈值/单位等强约束，模型不需要自主发现平台能力；后续 Agent View 再修改由确定性执行器生成，人工发布由测试 Chromium 模拟而非真正授权审批。没有自主需求消歧、多轮自动规划、生成自定义代码/构建测试、生产部署、插件沙箱或完整成熟可视化设计器。B2/B3 是研究用独立内核，未与上游低代码平台合并。

**门禁维持**：S1 IN_PROGRESS / G1 **NOT_PASSED**，G1-B01 **PARTIALLY VALIDATED / OPEN**；原冻结 W01—W24 **0/24 FULL PASS**，TC01—TC18 **0/18 FULL PASS**。下一必要试验转向能力缺口触发的受限代码开发闭环（能构建/测试/失败不发布），并进行 Domain Schema + Manifest 与 Global Application IR 的等能力对照，而不再重复固定合同的模型规划调用。


## 2026-11-21：B4 真模型自定义代码 / 沙箱构建 / B2 绑定发布再评审

新增 [报告 37](37-s1-b4-real-deepseek-custom-code-sandbox-evidence.md)，[真实 Actions #44894074280](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44894074280) **completed/success**，Job 136815855851 / Artifact 14702827817；首次完全离线 CI [#44893945547](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44893945547) 已通过，随后**只进行一次真实 DeepSeek Function Calling**，生成了与人写离线样例不同 SHA 的单纯函数 Python 风险评分源码。B4 安全/提议单测 **27/27**，B2 回归 **18/18**，真实 Docker/Chromium 离线 **27/27** 和真正 DeepSeek 在线 **27/27** 全通过；每份合格源码在 `--network=none` 等受限 Docker 内接受 **432** 项业务 Oracle。

新工程观察：B2 原有低代码只能表达金额阈值审批，当缺少供应商信用/合作年限风险评分能力时，模型提出自定义源码，可信 Controller AST 检验并在 Docker 实测，错误代码不会 Stage/Publish。实际 SQLite 基于 B2 已发布 Manifest v1 内容哈希绑定独立 Code Artifact/Release；真实 Chromium 合同高风险 95、低风险 0；Agent Stage/Publish 403；可信发布故障原子回滚；模拟人工增加代码注释形成 v2 并可回滚；修改 B2 已发布 v2 后旧代码执行 **409 B2_RELEASE_CHANGED**，回滚 B2 v1 后恢复。PR #6 已合并 `main`：`5dd3224893a87e1e7a77f91000c38fa023a98d07`。

**架构价值**：固定合同领域 **低代码 + 受限真实 AI 代码生成 + 隔离构建/测试 + 引用一致性运行与回滚** 已有可复现的正向证据。但该自定义代码仅一种纯函数，模型没有自主工程工作区、一般第三方依赖、Maven/npm 编译、无限扩展 API、生产插件隔离、真实人类审批或多轮失败自动修复。B4 仍在 B2 的研究 Companion Registry 旁工作，尚未整合为任意低代码平台底层不可绕过的单一 Domain Kernel，更不是 B2 与全局 IR 的严格等能力架构优劣对照。

**正式门禁维持**：S1 IN_PROGRESS，G1 **NOT_PASSED**，G1-B01 **PARTIALLY VALIDATED / OPEN**；冻结 G1-B01 W01—W24 **0/24 FULL PASS**，合同 TC01—TC18 **0/18 FULL PASS**。下一步优先在等能力条件对照 Domain Schema + Manifest 与统一 Application IR，并设计真实插件权限/代码扩展的跨入口强制治理；不建议再次为了重复相同固定纯函数验证而付费调用模型。


## 2026-11-21：B5 同内核 IR/Domain 表示法对照与权限工具入口复审

[报告 38](38-s1-b5-ir-parity-tool-broker-evidence.md) / [实际 GitHub Actions #44895248552](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44895248552)：completed/success，B5 **40/40 IR/Broker 单测**、B2 **18/18 回归**、B4 **27/27 回归**、B5 实际 Chromium/Plugin 子进程/Docker/双 App 业务 **29/29** 全绿，原始 Artifact 14703169788，0 次外部模型。PR #7 已合并 `main`，commit `e8106e6214c0b75ad232c7d12a0a7a4aad794916`。

**控制变量后的研究结论**：固定合同 DataModel/Form/View/Workflow + B4 风险扩展用两个独立 App，分别经直接 Domain Schema 和严格统一 IR 投影编译写入完全同一 B2/B4 Runtime；初建及之后受控 View/Form 编辑均得到相同 B2 Manifest hash、业务记录、审批轨迹、风险评分与发布版回滚。Domain 与 IR 的单样例 canonical JSON 分别 **693/937 字节**，创建四种资源都仍需 **4 次 B2 typed commands**；IR 仅作为一份设计态文档**不会自动实现跨资源 ACID 原子更新**。因双方实际上**共用运行内核**，此实验不能作为独立 Domain-native vs IR-native Kernel 的性能、复杂度和工程治理优劣比较。暂定研究设计倾向：Domain Schema 作为可信可执行领域内核、Manifest 发布闭包、统一 IR 作为可选设计态投影/规划协议，待多领域及独立运行引擎试验证伪。

**统一工具入口安全边界**：新 v3 Broker 能真实控制 Browser Session/Agent/Plugin OS 进程的类型化开发工具权限、旧版本 CAS、跨应用与代码构建/模拟发布；Agent 验证真实 Docker 432 用例成功不代表获得发布权，Plugin 只许 View，未授权工具/直通 v2 Bearer 被阻止。然而**B5-28 特权 SQL 负对照验证 G1-B01 未关闭**：可信试验进程直接 SQLite UPDATE 已验收 Code Artifact 源码后，写入本身成功；受信运行接口能够在调用时检出 `ARTIFACT_HASH_DRIFT` 并返回 409，但并未阻止数据库管理员级别旁路。缺少真正的插件 OS 权限隔离和底层受治理内核所有入口覆盖。

**G1 正式决定不变**：S1 IN_PROGRESS；**G1 NOT_PASSED，G1-B01 PARTIALLY VALIDATED / OPEN**，冻结 W01—W24 **0/24 FULL PASS**，TC01—TC18 **0/18 FULL PASS**。下一 P0：最小权限插件容器/宿主 DB 与 Docker Socket 隔离 + 原生 CLI/Pack 旁路治理；对 W11/W16/W20/W24 运行原冻结验收口径（不以 B5 子用例替代），并单独设计真正 IR-native vs Domain-native 的等能力执行内核基准（而非只比较 IR→Domain 编译）。


## 2026-11-21：B6 真正 OS 沙箱插件与宿主写边界 P0 再评审

[报告 39](39-s1-b6-real-plugin-docker-isolation-evidence.md)、[最终 CI #44896786049](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44896786049) completed/success，Job 136824055360 / Artifact 14704775846；B6 插件隔离安全单测 **25/25**，既有 B2 **18/18**、B4 **27/27**、B5 **40/40** 回归，真实 Docker/HTTP Broker/Chromium/SQLite **32/32**，0 次外部模型。PR #8 已合并 `main`，SHA `f18e9341be4af086bb1b1d69341e8789ecfdad58`。

**正向实证的新信息**：此前 B5 的插件虽作为单独进程运行，但真正的宿主 SQLite 权限可绕过。B6 改为**真实无网络、非 root、禁止特权、只读、只挂载两份插件请求/源码的 Docker OS 容器**，执行一般 Python/SQLite/socket 进攻性测试，实际结果：宿主 DB 既不能 `sqlite3 mode=rw` 连接，也不能 `os.open(O_RDONLY/O_RDWR)`；宿主 Secret world-readable 文件 `O_RDONLY`、Docker Socket、外部 TCP、容器工作目录写入一律 DENIED；独立可信 SQL 表明没有未经授权的资源/审计副作用。插件不接触 HTTP Bearer，只能通过宿主 JSON 提议，由可信 Host Relay 以随机受权主体调现有 B5 v3 Broker。合法 View 变更可成功、Agent/浏览器交替编辑旧版 409、发布 Manifest 后合同实测与 B4 独立 Docker 432 Oracle 仍可工作。特意模拟丢失一次 HTTP 回执后同 changeId 重放，真实审计/收据无双写，但不等同正式 W20 远端未知副作用验收。

**仍然存在同一阻断风险**：B6-32 再次让**具 DB 文件权限的可信宿主**直接 `UPDATE extension_artifacts.source`，物理写入确实成功，随后已发布风险运行只在 hash drift 时 409；因此不存在无条件“所有主体都无法直写 DB”的证据。Docker 内的研究插件尚非 Saltcorn/NocoBase/ToolJet 的真实原生插件，宿主原生 Field/CLI/Pack 与任何多节点写路径未被强制接入 OS 沙箱。仍需基于系统权限实际验证 DB 仅被可信核心进程持有、其他插件/本机 CLI 无权直接访问，并覆盖原生编辑器/导入、应用+代码统一快照与回滚、外部未知结果。

**正式决策不变**：S1 IN_PROGRESS，G1 **NOT_PASSED**，G1-B01 **PARTIALLY VALIDATED / OPEN**；冻结 W01—W24 **0/24 FULL PASS**、TC01—TC18 **0/18 FULL PASS**。本轮 32/32 实验项不替代正式门禁。下一个 P0 是真正隔离**宿主低代码原生写路径**和证明最终权威数据库只可由不可绕过的 Domain Kernel 访问，不能再仅增加外围 HTTP 拦截。


## 2026-11-21：B7 非容器原生 Linux CLI/插件独立 UID 与可信 Domain Kernel 持久化边界复审

[报告 40](40-s1-b7-real-linux-dac-domain-kernel-evidence.md) / [真实 GitHub CI #44897992713](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44897992713) completed/success，Job 136827642934 / Artifact 14704777950；B7 可信 OS/配置单测 **16/16**，B2 **18/18** 回归、B5 **40/40** 回归、B7 实际非 root 多 UID/原生 SQLite/HTTP/真实 Chromium/物理审计 **32/32**，0 次模型。PR #9 已合并 `main`，SHA `8b4cd3e87135efe6744b9614e6673bcff439defb`。

**新的可复现实证**：用真正不同的 Linux 宿主 UID 运行可信 B2/B4 Domain Kernel（UID 999）、原生 Plugin（UID 997）和 Agent（UID 995），前者独占 mode `0700` 目录和 mode `0600` 的 SQLite/配置文件，后两者尝试原生 `os.open` 读写、sqlite3 read/UPDATE、读取 Kernel 私有配置和 /proc 凭据实际被操作系统拒绝。合法 Agent/Plugin 只能经 B5 v3 类型化工具写入 Model/View/Workflow；本机插件请求非法 SQL/发布/跨 app 返回 403，真实 Chromium 与原生 Plugin 并发修改时 B2 CAS 返回 409，独立 SQL 验证审计、不可变发布和实际合同审批结果。此项相比 B5 子进程及 B6 Docker 插件，为“**非特权宿主原生代码的 DB 权限可被真实 OS DAC 限制**”提供了直接正向证据，而不是仅靠 Broker 逻辑判断。

**必须保留的反例**：B7-28 再次实际运行与 Kernel **相同 UID** 的 native SQLite 程序，直接读配置并成功 SQL UPDATE；B7-29 则让受信 root 控制器直接篡改已存储资源，物理写入真实成功。B2 读草稿时能识别资源 Hash drift、HTTP 409 和 QUARANTINED，已发布最后有效 v1 可读，但**同 UID/root 写入本身没有被阻止**，而且 root 可同时修改 Hash/版本指针避开此检测。B7 没有运行真正 Saltcorn Field.update、原生 CLI/Pack，也没有隔离业务应用 installer 与 Kernel 同 UID，生产级全入口强制治理仍未收口。B4 独立 Build Worker/制品可信回执与统一发布快照同样未在本轮测试。

**G1 审核保持**：S1 **IN_PROGRESS**；G1 **NOT_PASSED**；G1-B01 **PARTIALLY VALIDATED / OPEN**；冻结 W01—W24 **0/24 FULL PASS**、TC01—TC18 **0/18 FULL PASS**。下一 P0：结合真实 Saltcorn C2 原生 CLI/Field/Pack 写入的证据和宿主 Unix 用户、实际 DB 身份边界，证明普通生产插件/代码安装器没有任何同 UID/root/DB 直写通道；再审查强制 Kernel 变更、镜像/制品和 B2/B4 统一发布快照，以及远端动作的未知结果与补偿协议。32 项研究实验不替代正式冻结门禁。


## 2026-11-21：B8 真正 Saltcorn 原生 Field.update、Pack 导入和浏览器写入的权限边界复审

[报告 41](41-s1-b8-real-saltcorn-native-write-path-evidence.md)，[最终 GitHub Actions #44899334319](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44899334319) completed/success；Job 136831743808，Artifact 14704953422：B8 **15/15** 单测、B2 **18/18** 与 B5 **40/40** 回归、**24/24** 真实官方 Saltcorn CLI/Pack/Chromium/Linux OS/物理 SQLite 对照。PR #10 已合并 `main`，SHA `92a06863c91d8a59c80ca93ef95b2a87c4ca4f4e`。零模型费用。

**本轮比 C2/B7 更关键的真实结论**：在同一个官方 `@saltcorn/cli@1.7.0-beta.5` 实例及真正合同 Pack/SQLite 下，两个不同 Linux 非 root UID 的进程实际对照。不同于 DB owner 的 UID 997 执行官方 `saltcorn run-js -f native-out-of-band.js`（真实 `Field.update`）和 `saltcorn install-pack` 均以操作系统权限错误失败，物理字段和合同记录不变；该低权限 OS 进程仍能通过历史研究 Gateway 的受控 HTTP CAS 修改原生字段，合法修改有 revision+receipt，冲突 HTTP409。但是**以 DB owner UID 999 运行的真实 Saltcorn 原生 Server /field/:id 浏览器编辑器**成功直接修改 `_sc_fields`，Gateway revision/receipt 均不变；**同 owner UID 的官方 Saltcorn Native CLI Field.update**也真实成功直接改字段，整个外围 CAS 只能事后 `OUT_OF_BAND_DRIFT 409` fail-closed。此结果实际否定了“**只靠 DB OS DAC + 外围 Gateway 就能强制 Saltcorn 原生所有写入口经同一权限/版本内核**”的架构假设，并与早前 C2 Patch 绕行证据独立对应。

**不能升级的正式门禁**：B8 的 24 个 PASS 是研究情景独立观察，其中 B8-20/23 分别明确为不安全 Native Web 和同 UID CLI 旁路**成功复现**，绝不说明 W11/W16 已安全通过。原生 Pack 仅在不同 UID 被 OS 拒绝，不代表 owner UID Pack 导入已经受 CAS 管控；真实 Saltcorn Native UI 编辑/CLI 仍然可越过版本账本完成**已发生的物理修改**。尚未关闭实际插件安装器权限、Native Field/Pack 全量路径、热更新缓存、生产身份、跨代码发布事务及外部副作用补偿。

**候选架构与下一 P0**：不继续以“给 `/field` 加一个临时签名检查”当作完整安全方案。优先 B9 对照**由独立 Domain Schema + Manifest Kernel 单独拥有权威数据库，Saltcorn 仅可编辑可删除的派生副本**；在该场景以真实 Saltcorn Native Web/CLI/Pack 再次试图攻击，必须证明**权威 Kernel 的 Manifest/receipt/audit 完全不变**、派生 Runtime 可丢弃重建且发布后重放一致。成熟平台复用仍可作为 UI/runtime，前提是权威写边界确实强制隔离。另一个候选是深改 Saltcorn 上游 Field/Pack/CLI 的全部写入 Hook，但当前未做等效覆盖证据与维护成本量化，不能声明已经可行。

正式判定继续：S1 **IN_PROGRESS**；G1 **NOT_PASSED**；G1-B01 **PARTIALLY VALIDATED / OPEN**；冻结 W01—W24 **0/24 FULL PASS**，TC01—TC18 **0/18 FULL PASS**。

undefined

## 2026-11-21：B10 真实双 Saltcorn Runtime 在线版本切换、Readiness/故障回滚复审

[完整报告 43](43-s1-b10-real-saltcorn-traffic-cutover-evidence.md) / [最终 GitHub Actions #44906374299](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44906374299) completed/success，Job **136852721607**，[Artifact #14708420037](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44906374299/artifacts/14708420037)：B10 **34/34 Router 策略单测**，B2 **18/18** 回归、B5 **40/40** 回归，**44/44** 实际 Ubuntu24/三 Linux UID/官方 Saltcorn CLI 1.7.0-beta.5/双进程 Native/Chromium/权威 B2 SQL 审核。PR #12 已合并 main，SHA **d1b498699065de460ed1a3763aa0914066828fa0**，本轮 0 次 DeepSeek。

**新的有限正向架构证据**：将 B9 唯一权威 B2 Kernel（UID999）与 Saltcorn 可删派生 Runtime（UID997）之间新增单独 Router（UID995），Router 只有真正限制为 app-a `release.read` 的 Token 而无任何权威写权限；只公开匿名 GET 合同列表，实际 Native /field 和 POST 不通过。真正不同 SQLite 的 Saltcorn v1/v2 **同时在线**，Native view 列 3/4；新版本通过真实原生业务 HTML/预期合同号 Readiness 与 B2 当前已发布 Release/Manifest SHA 验证后才注册/切换。真实已有 GET 捕获 v1 路由时受实验 Header 延迟，v1→v2 CAS 切换后仍按旧 v1/epoch1 返回，新 GET v2/epoch2；重复 changeId 不重复推进 epoch、过时 epoch 409。故意终止真正 Native v2 进程后，前端明确返回 503，不伪造成功或静默回退；B2 发布指针尚为 v2 时主动路由回滚被 409 拒，只有受权 B2 Publisher 真回滚 v1 后 Router 再 CAS 回退才恢复业务前端 GET 和 Chromium。B2 同时独立真实执行合同创建和金额两级 Workflow 到 Approved，业务事实在 Saltcorn 故障/发布回滚期间保持正确。

**关键未过门禁**：这个“可切换”是**单个研究 Python Router 进程内锁保护的版本指针**，未持久化变更账本、未做跨 Router 多副本一致性、重启故障恢复、网络路由/Ingress 多节点、页面/身份/长连接转发、零停机部署或自动健康故障切换；实际 v2 故障产生 **503**。本轮 B2 业务 Approved 合同与 Saltcorn 展示的独立 fixture **合同号相同但标题不相同**，刻意证明尚未实现权威数据复制/增量投影和脱敏。Router 的 H10 Readiness 是局部业务页面标记可被伪造，并未复核所有页面逻辑。Saltcorn 原生数据库仍可由 Runtime UID 修改且 Native Port 暴露 localhost，Form/Workflow/B4 Code 未做 Native 语义等价。B2 Release 与 Router Route 是**顺序更新的两个指针**，故意可观察“源已发布 v2、客户端仍服务 v1”的部署滞后，**不是 W24 全域原子事务、W20 外部未知结果补偿或 W17 生产热缓存/无损切流**。

**阶段判定继续不变**：S1 **IN_PROGRESS**，G1 **NOT_PASSED**，G1-B01 **PARTIALLY VALIDATED / OPEN**，冻结 W01—W24 **0/24 FULL PASS**、冻结 TC01—TC18 **0/18 FULL PASS**。B10 44/44 PASS 仅为独立研究证据，不能冒充正式 W/TC。下一优先 B11 **真实 B2 审批业务事实 → Saltcorn 只读物化数据层**的单向同步、幂等重放、冲突/乱序/停机恢复与跨 UI 版本数据一致性；同时补齐发布控制面持久化/原子状态切换和路由实例故障恢复以逐步挑战 W17/W20/W24。


## 2026-11-21：B11 B2 权威事务 Outbox → 真实双 Saltcorn Native 业务数据增量投影复审

[报告 44](44-s1-b11-authoritative-business-outbox-native-projection-evidence.md) / [最终 Actions #44908563537](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44908563537) **completed/success**，Job **136859260383**，[Artifact #14708123689](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44908563537/artifacts/14708123689)：B11 Outbox/Native Consumer **28/28** 单测、B10 Router **34/34**、B2 **18/18**、B5 **40/40** 回归，**62/62** 实际 Ubuntu24/三 Linux UID/真实 B2 表单和两级审批/SQLite Trigger/双 Saltcorn CLI 1.7.0-beta.5/真实 SQL/Chromium/故障与回滚 E2E。PR #13 已合并 main，SHA **68da2ce8cf5cd1312866f68c22314636354ab26b**，**0 次 DeepSeek**。

**新增限定正向证据**：B10 的最大剩余真实性缺口是 Native 展示的是独立 seed fixture。B11 已**移除全部 Native seed**，B2 唯一权威 `records` 插入/更新触发器在相同真实 SQLite 事务中写 `b11_outbox`，每次合同创建/金额两级审批状态变更的事件时点 payload 不被后续状态覆盖。Kernel 新增独立随机 token、仅 app-a/固定四列/受限 cursor 的只读投影拉取接口，Saltcorn UID 未获 token/DB 权限；Native UID 对权威 DB/配置的真实 O_RDONLY 均 DENIED。可信测试控制器将真实 B2 Outbox seq1..4 通过 stdin 交给 Native UID Worker，在真正 Saltcorn SQLite 上一次事务写业务行、记录映射、持久 Receipt 和 cursor，重放 0 新写、Hash 冲突拒绝、事务 COMMIT 前注入故障无部分提交、重试成功。两套真正同时在线的 Saltcorn v1/v2 Native View 列 3/4 不同，但业务行相同且等于 B2 源合同；**两个 Native 服务运行期间**再从 B2 真创建并两级批准第二份合同，源 Outbox seq5..8，两个 Native 不重启仅消费增量四条即显示两份 Approved 合同，真正 Native HTTP/Router HTTP/Chromium 均读到第二份合同。真实 v2 进程故障 503，先 B2 app.rollback 后 Router CAS 恢复 v1，**两份业务合同仍 Approved、8 条源事件与 Native cursor8 不回退、App B 不变**。这是从静态页面投影进入**真正单向业务数据投影**的实证，但不代表完整 Saltcorn Native 工作流语义等价。

**继续阻断正式门禁**：B11 Outbox 只针对 app-a/model.contracts 的 INSERT/UPDATE，尚无删除、Schema 迁移、通用 CDC、真实后台常驻消费者、持久跨进程队列/断电追赶、死信/延迟指标和网络分区恢复；测试由受信 CI Controller 主动同步而非生产服务自动持续运行。四列 allowlist 不是多租户行权限或敏感数据脱敏；Native 原生列表是公开测试 View，不能生产部署。Event SHA 不是签名，Saltcorn Runtime UID 仍可物理污染自己的派生 DB（下一事件更新该行时才拒绝），Router 仍为单实例内存 CAS，Native localhost 端口未做正式生产网络隔离，真实故障返回 503 而非零停机。B2 的 Form/Workflow 逻辑仅在可信 Kernel 执行，Saltcorn 只是只读业务数据/Model/View 的可删投影，B4 Code/插件/全量流程未实现。正式 W17（完整 Native REST/缓存一致性）、W20（外部未知结果补偿）、W24（完整应用/代码/流程/外部副作用回滚）仍未满足。

**正式结论不变**：S1 **IN_PROGRESS**；G1 **NOT_PASSED**；G1-B01 **PARTIALLY VALIDATED / OPEN**；冻结 W01—W24 **0/24 FULL PASS**、TC01—TC18 **0/18 FULL PASS**。B11 62/62 只是独立范围受限研究，不能直接升级冻结 W/TC。下一 B12 优先真实后台 Consumer checkpoint/断线/崩溃恢复、Native 读取前防污染与重建，再考虑用户行级权限/脱敏和发布/路由控制面持久化。


## 2026-11-21：B12 真实后台 Consumer SIGKILL / HTTP 503 恢复 / Native SQL 漂移复审

[完整报告 45](45-s1-b12-autonomous-consumer-crash-recovery-native-drift-evidence.md)、[最终 Actions #44910951780](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44910951780) **completed/success**，Job **136866440843**，[Artifact #14709752514](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44910951780/artifacts/14709752514)：B12 单元 **22/22**、B11 **28/28**、B10 **34/34**、B2 **18/18**、B5 **40/40** 回归，真实 Ubuntu24.04/三独立 Linux UID/B2 Kernel/SQLite Trigger/两套 Saltcorn Native/HTTP/Chromium **79/79** E2E（B11 基线 62 + B12 新增 17），**0 次 DeepSeek**。PR #14 已合并 main，SHA **8ce7324d85aa1d06a8269bc6351d43a95678b06d**。

**新增严格正向证据**：B11 真实 B2 Outbox 到 Saltcorn SQLite 的每批同步由受信 CI Controller 手动调用，B12 首次使用真正长期运行的独立 Consumer OS 进程，持续从 Saltcorn SQLite 已提交的 `b11_projection_cursor` 读取 checkpoint，经独立随机 projectionToken 只读拉取 B2 事件，向 Saltcorn UID 的 Native Apply Worker 仅通过 stdin 发送 JSON 事件，保持业务行、record_map、Receipt、cursor 原子提交。Native UID 真实 O_RDONLY 访问私有 Consumer Token 配置 **DENIED**。真实 B2 新建批准第三份合同后 Consumer 自动 cursor8→12、原生 HTTP 展示；真实 SIGKILL Consumer 时 B2 继续写入第四份合同，源 seq16、Native cursor12，重启新 Consumer 进程自动从已提交 Native cursor 追赶至16、4行16回执、无重复；源 HTTP 代理实际返回503期间 B2 继续新建批准第五份合同，源 seq20、Native cursor16，解除503后自动追赶至20、Native 5行20回执，真实 HTTP 与 Chromium 展示第五份合同。独立 SQL Oracle 验证源 B2 **5 份 Approved 合同、20 条 Outbox 事件、App B 未变**。

**特别重要的负对照**：Saltcorn UID 真实 SQL 改写第五份派生合同标题后，后台 Consumer **即使无新源事件**仍在周期性全量 record_map/Receipt 检查中检测 `DERIVED_DRIFT` 并停止后续消费，但 Native HTTP **仍返回 200**；真实 HTTP 本次显示的是**缓存旧标题**，不是篡改标题（`httpShowsTamper=false`）。**既不能宣称已验证读取前 fail-closed，也不能把偶然缓存旧值当作安全保证**。Saltcorn UID 人工修复派生 SQL 后 Consumer 恢复 CAUGHT_UP，不是自动重建。初次 CI 失败为 B11 模块导入路径缺失；第二次 CI 失败是误假设 Saltcorn HTTP 立即反映 Native SQL 篡改，现均基于真实行为修正并保留失败记录。

**继续阻断正式门禁**：Consumer 仍由 **sudo-capable CI Runner** 启动并通过 sudo runuser 启动 Native Worker，尚无正式独立 Consumer UID、受控 IPC/跨机 TLS、持久 HA/Leader Election/系统服务；503 是同机代理真实 HTTP 故障，非断电/跨机网络分区。Native SQL 可被同 UID 改写且 HTTP 读取未做 fail-closed，缓存与权限绕过仍存在；没有自动修复/派生重建、生产延迟 SLA、真实行级 ACL/PII 脱敏、Delete/Schema Migration、完整 Native Form/Workflow/Code 语义。B10 Router 仍单实例内存 CAS、故障返回503，不具备生产零停机/外部副作用补偿/跨服务原子发布。

**正式判定保持**：S1 **IN_PROGRESS**；G1 **NOT_PASSED**；G1-B01 **PARTIALLY VALIDATED / OPEN**；冻结 W01—W24 **0/24 FULL PASS**、TC01—TC18 **0/18 FULL PASS**。B12 79/79 为范围受限专项证据，不得自动转正式验收。下一 B13 P0：**可信 Consumer 独立 OS 身份 + 受控 Native Apply IPC**，**Router 读取前物理 SQL 完整性校验并 fail-closed**，进一步做权威重建/缓存旁路/签名验证。


## 2026-11-21：B13 四真实 OS UID、受限 Unix IPC、读前 Guard 与源事件伪造 P0 负对照复审

[完整报告 46](46-s1-b13-four-uid-native-ipc-read-guard-negative-evidence.md)、[最终 GitHub Actions #44917605505](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44917605505) **completed/success**，Job **136886465940**，[Artifact #14711934942](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44917605505/artifacts/14711934942)：B13/B12/B11/B10/B2/B5 单元/契约回归 **22+22+28+34+18+40 = 164/164 PASS**；真实 Ubuntu24.04、Saltcorn CLI1.7.0-beta.5、两套 Native HTTP、四不同 Linux UID、SO_PEERCRED Unix IPC、B2 SQLite/Outbox、Chromium E2E **104/104 PASS**（B11 62 + B12 17 + B13 25），**0 次 DeepSeek**。PR #15 已合并 main，SHA **712ab9cc3dcf1ef2f94745c9f4aa75fca238eee0**。

**正向真实边界**：新增独立 `ailcapb13cons` Consumer UID994，真正 `sudo -n true` 失败，实际 O_RDONLY 权威 B2 SQLite、Saltcorn Native SQLite、Router Token 配置全部 PermissionError；Saltcorn UID997 读取 Consumer/Router B2 Token 配置均拒绝。Saltcorn UID Native Broker 创建**两个不同 Linux Group 的 0660 Unix Socket**，SO_PEERCRED 校验 Consumer/Router UID；Consumer Socket 仅 audit/checkpoint/apply，Guard Socket 仅返回固定四列 Native 业务行、Cursor、Receipt、Mapping 的物理 SQL 快照，Consumer/Router 相互无法连接对方 Socket。**Consumer 自身不再有 sudo 权限**，但 CI Runner 仍使用 sudo 创建用户和启动实验进程，不能视为生产服务授权方案。

**受限读前守护实证**：独立 Router UID995 持 B2 Release Read 与 Projection Read Token（Saltcorn UID 无此 Token），对单个公开 `GET /view/s1_contract_list` 在 Native HTTP 前后两次核验当前 B2 Release/Manifest、权威 Outbox 事件序列/哈希与 Native SQL 物理行/Receipt/Cursor，任一不匹配 HTTP503。真实 Chromium 在 Guard 入口展示5份合同；Consumer 无 sudo 经 IPC 自动同步第六份合同、Guard HTTP200；终止 Consumer 后 B2 创建第七份合同，B2 Head28/Native Cursor24，**Guard503 / Native 直连200**；新 Consumer 自动追赶至28后 Guard200；Saltcorn UID 真实 SQL 污染第七份合同标题后**Guard503 / Native 直连200**，人工修复后 Guard200。Guard 是单个只读入口的受限验证，不等于原生 Saltcorn 全面强制隔离、无 TOCTOU 或生产线性一致性。

**P0 负对照——不得误报安全通过**：B13-104 使用**合法 Consumer UID**经 Consumer Apply Socket 提交**自行伪造、B2 Outbox 不存在**的 `seq=29` 合同插入事件及其合法 SHA256 `eventHash`。真实 Native Apply **接受并提交**该伪造合同，Native Cursor28→29，B2 权威 Head仍28；Guard 独立对照后真实返回 HTTP503。**Native 数据完整性已被污染**，Consumer OS 身份验证与普通 eventHash **不是权威事件来源认证**。B13-104 专项 PASS 是成功暴露危险能力，**源签名/Native 防伪造目标 FAIL/OPEN**。Native Broker 与 Saltcorn 同 UID 可被同 UID 失陷伪造 Snapshot，Native 原生 HTTP 直连仍不受 Guard 保护。每次 Guard 全量重扫源 Outbox，最大1000事件，未测吞吐与延迟，未实现企业多租户 ACL/PII、Delete/Schema Migration、HA/跨机网络安全或全量 Native Form/Workflow/Code。

**保留失败**：[初次 CI #44917208014](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44917208014) Python 缩进错误；[第二次 CI #44917393338](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44917393338) 164单元与104 E2E 已通过，但四 UID 临时目录清理权限错误使 Job 失败；[最终 #44917605505](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44917605505) 完整清理与所有测试均 success。原失败记录不删。

**正式冻结结论仍然**：S1 **IN_PROGRESS**、G1 **NOT_PASSED**、G1-B01 **PARTIALLY VALIDATED / OPEN**、冻结 W01—W24 **0/24 FULL PASS**、TC01—TC18 **0/18 FULL PASS**。B13 104/104 为专项范围内结果，不转正式门禁。下一 B14 P0：**B2 权威签名事件 + Native Apply 验签**，以及**独立于 Saltcorn UID 的物理 SQL 读前证明/只读快照**；保留恶意 Consumer 伪造、恶意 Native Snapshot 和原生 HTTP 旁路负对照。


## 2026-11-22：B14 Kernel Ed25519 权威事件来源认证与第五独立 UID SQL 读前审计复审

[完整报告 47](47-s1-b14-ed25519-independent-sql-auditor-evidence.md)、[最终 Actions #44926315233](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44926315233) **completed/success**，Job **136913068933**，[Artifact #14716390392](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44926315233/artifacts/14716390392)：B14/B13/B12/B11/B10/B2/B5 单元/契约 **24+22+22+28+34+18+40 = 188/188 PASS**；真实 Ubuntu24.04/Node24/Saltcorn CLI1.7.0-beta.5/Python3.13/cryptography/Chromium、五个不同非 root Linux UID、B2 真实 Form/Workflow/SQLite Trigger Outbox、Ed25519 签名/验签、无 sudo Consumer、真实 Native SQLite/HTTP、独立 SQL 审计 **128/128 E2E PASS**；**0 次 DeepSeek**。PR #16 已合并 main，SHA **1dabeba18450adbd09196e6f21acb32cb7e080a2**。

**B13-104 P0 的受控路径修复**：B14 先在同一真实测试环境完整复现 B13-104“合法 Consumer UID 自行伪造 SHA256 事件，旧 Native Broker 接受、Cursor28→29”负对照；受信 CI Controller 停止旧无签名 Broker、重置一次性 Native 派生库，再由 Kernel UID999 以**0600 私钥**对 B2 权威 Outbox 的28条真实事件做**domain-separated Ed25519 签名**。Consumer UID994 无 sudo、不能读/写私钥；Saltcorn UID997 只持固定只读公钥。Native 新 Broker 在调用 B11 事务 Apply 前验签，**原 B13 SHA256 伪造事件被拒绝、修改字段并重算 SHA256 复用旧签名被拒绝**，Cursor保持0；28条真实签名事件原子回放、28条幂等重放均通过。B2 新建第八份合同的4条事件由无 sudo Consumer 自动取得签名、应用，Native Cursor28→32；合法 Consumer 再伪造 `seq33` 并盗用旧签名，Native **拒绝**、Cursor32不变，受控 Guard HTTP200。**因此 B13-104 的受控 Apply IPC 事件来源认证缺陷得到有边界的实测修复**，但 Saltcorn UID 仍可绕过自身 Broker 直接写派生 SQLite。

**B13 同 UID Snapshot P0 的受限修复**：新增第五独立 Linux 非 root `ailcapb14audit` UID993，Saltcorn UID997 仍拥有 Native SQLite；通过文件组只读 **0640** 与目录 **0710**，审计 UID 真实 `O_RDONLY` 成功、`O_WRONLY` PermissionError。审计 UID 自己拥有 `guard.sock` **0660**、SO_PEERCRED 仅 Router UID995、只读 snapshot；Saltcorn UID 连接被 DAC 拒绝。Router 在真实 Saltcorn HTTP 前后核验 B2 当前 Release、**全部 Ed25519 签名 Outbox**与独立审计 UID 的物理 SQL；真正 Chromium/HTTP200 展示7份和自动新增的第8份合同。Saltcorn UID 直接 SQL UPDATE 污染第8份合同标题，**独立审计 clean=false、受控 Router HTTP503、Native 原生直连 HTTP200**；人工修复后 Guard200。该设计降低“Saltcorn 同 UID 伪造 Guard Snapshot”的风险，但**不能阻止 Saltcorn UID 直接修改真实派生 SQLite 或使审计不可用**。

**保留失败与最终证据**：[初次 CI #44925890843](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44925890843) 188项单测全过但 Ubuntu useradd 与同名 group 冲突，未执行 E2E；[第二次 CI #44926049128](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44926049128) 188项单测、B13 104项和 B14-105—120 共120项真实 E2E 已通过，但 B14 Guard 误用 B13 临时目录前缀 fail-closed，未完成余下8项；[最终 #44926315233](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44926315233) **188/188 + 128/128、Job success、Artifact 完整**。失败记录不删除，也不把前两次当作成功证据。

**仍 OPEN 的 P0/工程限制**：Saltcorn UID 可直接改写派生 SQLite；Native 原生 HTTP 直连可绕过 Router；Ed25519 密钥没有生产 KMS/HSM/轮换/吊销/可信时间/长期签名审计；Router 单一固定四列合同 GET 全量扫描源 Outbox 最多1000事件、双次校验仍有 TOCTOU；未覆盖多租户行级 ACL/PII、删除/Schema Migration、生产吞吐/断电/跨节点故障/HA、持久 Route Journal、Native Form/Workflow/Code 完整一致性。B15 优先验证**网络层强制受控入口**及**派生 SQLite 受控只读快照/原子发布**，保留 Native 直连、SQL 直写、断链/重放负对照。

**正式冻结判定保持：S1 IN_PROGRESS、G1 NOT_PASSED、G1-B01 PARTIALLY VALIDATED / OPEN；冻结 W01—W24 0/24 FULL PASS，TC01—TC18 0/18 FULL PASS。** B14 的128/128为专项研究通过，不等于 G1 正式 FULL PASS。
