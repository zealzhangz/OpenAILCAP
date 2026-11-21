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
