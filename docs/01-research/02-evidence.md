# 源码一手证据台账（2026-11-21）

这些证据是本次通过 GitHub 连接读取到的**静态源码与仓库文档**，不是实际运行验证。完整结果须在后续阶段加上运行环境、命令及原始日志。

| 代码库 | 默认分支 | 固定 Commit |
|---|---|---|
| NocoBase | v3 | 0894734040c3d30d4f4f3d7a6da98ae22f365f80 |
| ToolJet MCP | main | 8a178ad34f6e3326b6957503ca4ed4f555d23096 |
| Appsmith | release | 0a6f6934fb33c06ee0a132c5baba78e006611621 |
| Budibase | master | 724cb529d7b32fde84ae537e4b44673cf0618dad |
| Meta Astryx | main | 35bda7f8f11c2c0b076ba07f24bb171207ce85e3 |

## E01 — 受限结构化应用计划

[ToolJet MCP appPlanSchema.ts](https://github.com/ToolJet/tooljet-mcp/blob/8a178ad34f6e3326b6957503ca4ed4f555d23096/src/appPlanSchema.ts)：可见表、查询、页面、事件、生命周期以及原位更新等字段，页面替换标注非原子性。**可证明**：存在受约束的计划 Schema。**不能证明**：完整通用 Application IR。

## E02 — 计划校验及对象引用解析

[ToolJet MCP applyAppPhase.ts](https://github.com/ToolJet/tooljet-mcp/blob/8a178ad34f6e3326b6957503ca4ed4f555d23096/src/tools/applyAppPhase.ts)：源码导入 lint、plan、diff、readback、ref 解析；rename 逻辑先校验再 apply。**不能证明**所有写入链路均已具备强事务或高质量验收。

## E03 — 人工修改可能被旧 Agent 快照覆盖

[ToolJet MCP codeAppSync.test.ts](https://github.com/ToolJet/tooljet-mcp/blob/8a178ad34f6e3326b6957503ca4ed4f555d23096/tests/codeAppSync.test.ts)：测试明确描述人工改 Style inspector 后 Agent 用旧代码修改按钮的冲突，以及 revision 相同但内容不同场景。应以此研究双向同步指纹与三方合并。**本次未执行该测试**。

## E04 — 执行器环境白名单与工作区

[ToolJet MCP codeAppIsolation.test.ts](https://github.com/ToolJet/tooljet-mcp/blob/8a178ad34f6e3326b6957503ca4ed4f555d23096/tests/codeAppIsolation.test.ts)：测试涵盖并发工作区、凭据作用域、敏感环境变量隔离。**不能证明**容器/内核沙箱完全安全。

## E05 — 插件体系的有边界定义

[NocoBase define.ts](https://github.com/nocobase/nocobase/blob/0894734040c3d30d4f4f3d7a6da98ae22f365f80/packages/app/app-server/src/plugins/define.ts) 与 [resolve.ts](https://github.com/nocobase/nocobase/blob/0894734040c3d30d4f4f3d7a6da98ae22f365f80/packages/app/app-server/src/plugins/resolve.ts)：插件有 scoped package name、service providers、路由、数据库迁移贡献；明确了插件声明与资源加载责任。**不能证明**插件被 AI 自动安全调用。

## E06 — Agent 执行器与业务系统解耦

[NocoBase agent-runner README](https://github.com/nocobase/nocobase/blob/0894734040c3d30d4f4f3d7a6da98ae22f365f80/packages/app/agent-runner/README.md)：官方源码仓库文档描述 Runner 注册、工作目录、应用 CLI、任务领取和 Agent 执行。这是**官方文档级证据（S2）**，仍需阅读 Runner 的权限和安全实现。

## E07 — 组件按类型注册与动态加载

[Appsmith widget registry](https://github.com/appsmithorg/appsmith/blob/0a6f6934fb33c06ee0a132c5baba78e006611621/app/client/src/widgets/registry.ts)：按 widget type 注册 loader，动态加载并缓存。不能据此证明 AI 可访问组件能力 Schema。

## E08 — 数据绑定与组件引用

[Budibase builder dataBinding.ts](https://github.com/Budibase/budibase/blob/724cb529d7b32fde84ae537e4b44673cf0618dad/packages/builder/src/dataBinding.ts)：涉及组件、上下文、表、角色、屏幕和 JS binding。强烈提示“引用完整性”应纳入 IR/Manifest 验证。

## E09 — Astryx 真实定位

[Meta Astryx core README](https://github.com/meta/astryx/blob/35bda7f8f11c2c0b076ba07f24bb171207ce85e3/packages/core/README.md)：Core 为 React UI 组件及主题，CLI 提供组件文档与模板，文档明确 React 19+ 依赖；它不是现成完整低代码设计器。

## 证据边界和后续行动

本次未部署或运行上述第三方项目；未逐文件核查许可证；缺乏编译日志、测试报告、业务场景复现。**已验证假设数 0/8，G1 未通过。** 后续必须补齐源码调用链、官方许可、可复现实测及独立断言。

## E10 — ToolJet MCP Code mode 实际调用链进一步追踪（静态）

固定版本 [src/tools/codeApp.ts](https://github.com/ToolJet/tooljet-mcp/blob/8a178ad34f6e3326b6957503ca4ed4f555d23096/src/tools/codeApp.ts) 中，约第 713 行 syncEditorEdits 调用 CLI source-pull；约第 1006—1030 行读取文件及更新 readHashes；约第 1074—1114 行写入前重新同步并检查文件哈希及文本修改定位，冲突则拒绝。证据等级仍为 S1，不代表已运行第三方测试。详细解读见 [ToolJet 调用链](04-tooljet-sync-trace.md)。

## E11 — OpenAILCAP 自主模型级实测（S0，但范围受限）

运行了 [内存模拟对照实验](../../experiments/roundtrip/README.md)，A/B 各 10/10 场景通过，28 项单元测试通过；[机器可读结果](../../experiments/roundtrip/results.json)。实验证明的是本仓库**模拟模型**，不是 ToolJet/NocoBase 运行时，也不是实际 AI Agent。见 [实验报告](05-roundtrip-results.md)。

## E12 — ToolJet CE/EE Code Mode 证据断点（S1）

[Code Mode CE Controller](https://github.com/ToolJet/ToolJet/blob/d2f09ed9ab6c6cf289abfc8aa7ee77c1264aaeb0/server/src/modules/code-mode-source/controller.ts) 无真实路由；[CE Service](https://github.com/ToolJet/ToolJet/blob/d2f09ed9ab6c6cf289abfc8aa7ee77c1264aaeb0/server/src/modules/code-mode-source/service.ts) 对非 visual buildMode 拒绝。server/ee 在固定 commit 是指向 ToolJet/ee-server 的子模块，未能获取其完整源码。因此不得宣称公开 CE 包含 Code Mode 闭环。

## E13 — NocoBase Runner 隔离策略和许可证（S1）

[runner isolation.ts](https://github.com/nocobase/nocobase/blob/0894734040c3d30d4f4f3d7a6da98ae22f365f80/packages/app/agent-runner/src/core/isolation.ts) 明确仅对确定性构建步骤进行 none/user 隔离，container 暂不支持；Agent 编码沙箱由适配器负责。[LICENSE.txt](https://github.com/nocobase/nocobase/blob/0894734040c3d30d4f4f3d7a6da98ae22f365f80/LICENSE.txt) 第 4.2、5.4 与 7.3—7.5 条存在平台型产品的额外限制，不能仅用 Apache-2.0 摘要作为复用依据。

## E14 — OpenAILCAP SQLite 文件数据库试验（S0，范围受限）

[实验代码与 23 项测试](../../experiments/sqlite-roundtrip/README.md) 在 Python 3.13.5 / SQLite 3.46.1 实际运行，文件持久化、事务回滚、另起进程不提交退出、模拟 A/B 应用分区等 23/23 通过。[结果 JSON](../../experiments/sqlite-roundtrip/results.json) 与 [原始测试日志](../../experiments/sqlite-roundtrip/test-output.txt) 同库保存。没有真正鉴权、平台运行时和 AI Agent；不得把逻辑隔离测试误认为生产安全验证。详见 [深度报告](07-persistence-and-license.md)。

## E15 — 四平台功能证据矩阵（S1/S2）

新增 [22 项静态源码与官方文档能力对照](09-capability-matrix.md)（[JSON](capability-matrix.json)），覆盖 ToolJet、Appsmith、Budibase、NocoBase v3。Appsmith [widget registry](https://github.com/appsmithorg/appsmith/blob/0a6f6934fb33c06ee0a132c5baba78e006611621/app/client/src/widgets/registry.ts)、[NewPage unpublished/published 对象](https://github.com/appsmithorg/appsmith/blob/0a6f6934fb33c06ee0a132c5baba78e006611621/app/server/appsmith-server/src/main/java/com/appsmith/server/domains/NewPage.java)，Budibase [Automation actions](https://github.com/Budibase/budibase/blob/724cb529d7b32fde84ae537e4b44673cf0618dad/packages/server/src/automations/actions.ts) 均为具体源码线索。无产品级能力测试 PASS。

## E16 — NocoBase v3 官方创建器真实失败（S0：安装前置实验）

[GitHub Actions Run #44868550471](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44868550471)，Node24.22.3、pnpm11.11.0 成功，但 `npm.nocobase.ai/@nocobase/app-template-default` 返回 npm E530，创建器报 `TEMPLATE_DOWNLOAD_FAILED`，projectCreated=false。后续安装/业务测试没有执行。详见 [原始错误与分析](11-installation-trial.md)。

## E17 — Saltcorn 真实平台独立运行时实证（S0）

固定上游研究源码 SHA [515254bee5a98df70530cc59846b1df02d5db350](https://github.com/saltcorn/saltcorn/tree/515254bee5a98df70530cc59846b1df02d5db350)，MIT 许可。[@saltcorn/cli 1.7.0-beta.5 GitHub Actions #44869777036](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44869777036) 实际安装并运行，7/7 真正 SQLite/REST/HTML/匿名读取拒绝测试通过，Artifact ID 14693426822。见 [源码-运行态报告](14-saltcorn-real-platform.md)。

## E18 — Saltcorn 原生 Pack 配置合同资源（S0）

[GitHub Actions #44869926796](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44869926796) 执行本仓库原生 Pack、CLI Table.insertRow 和真实服务端 HTTP 断言，9/9 独立检查通过，Artifact ID 14693482263。其数据库真实持久化 s1_contracts、s1_approvals Key 关系、合同业务行与 List View，并经 REST/HTML 读回。**该测试使用预编写配置，没有 AI Agent；金额采用整数分，不是冻结基准的 decimal(12,2)**。见 [详细合同纵向切片](15-native-contract-platform-evidence.md)。

## E19 — 实际第三方平台“旧 Pack 覆盖人工改动”负对照（S0）

[GitHub Actions #44871169761](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44871169761)，Saltcorn CLI 1.7.0-beta.5，Job #136745819984，Artifact 14694023138，真实 SQLite/HTTP 下三组对照 + 运行态读回 18 次断言全部符合预注册预期。A：原生 Field.update 不同字段改变均保留；B：旧完整 Pack 只希望调整视图，但同步把人工 title.label 和前轮 status.label 还原旧值；C：非原子应用层旧基线检查抛出 STALE_BASE 并保留人工修改；HTTP 200 页面/REST 读回仍正常。**B 是已复现的不安全覆盖，不可被 green CI 误认为 H03 正面通过**。证据/源码索引见 [研究报告 16](16-saltcorn-roundtrip-evidence.md) 和 [候选 ADR](17-provisional-adr-guarded-editing.md)。

## E20 — Saltcorn SQLite 事务包装器与真实并发实验（S0 + 固定源码）

固定上游 [db-common/sqlite-commons.ts](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/db-common/sqlite-commons.ts) 的 SQLite withTransaction 实现没有真实 BEGIN/COMMIT/ROLLBACK；[sqlite/sqlite.ts](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/sqlite/sqlite.ts) 则有实际 SQL 事务原语。[字段编辑路由](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/server/routes/fields.ts) 调用 withTransaction/Field.update（目前只静态追踪该路由）。GitHub [Run #44872093657](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44872093657) 真正执行 SQLite 桩事务故障注入、独立进程资源级 CAS 冲突、原子回滚，以及不受控人工编辑绕过版本表的真实丢失。**36 次断言符合预期但含两类危险负对照**。详见 [研究报告 18](18-saltcorn-sqlite-atomic-evidence.md)、[机器摘要](atomic-observations.json)。

## E21 — 实际浏览器人工字段编辑与旧页面覆盖（S0）

[GitHub Actions #44873882208](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44873882208) 真正运行 Saltcorn HTTP、Python Playwright+Chromium，创建临时管理员登录、使用 /field/7 表单正常 POST（_csrf/contextEnc 均在请求体内），B 标签页保存 Browser B Saved 后，持旧上下文的 A 再保存 Browser A Stale Save，物理 SQLite 证实 B 的变更丢失。匿名直接访问字段编辑被重定向 /auth/login。共 9 项浏览器断言 PASS，**其中 UI06 是静默覆盖的危险负面证据**。同一平台中浏览器写入未维护研究外部版本账本，下一步模拟 Agent 以过期 revision=0 再次 APPLIED 并覆盖浏览器结果（后置 5/5 PASS，但覆盖危险）。固定上游 [字段路由](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/server/routes/fields.ts) 和 [向导模型](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/saltcorn-data/models/workflow.ts)，研究报告 [19](19-real-browser-edit-evidence.md)。

## E22 — 研究网关对真实低代码元数据的统一版本化 HTTP 写入正向证据（S0，限域）

真实 [GitHub Actions #44874668928](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44874668928) completed/success，Job #136756624531，Artifact #14695407749。22 项受控写入断言与 4 项绕过检测通过：网关自己的真实 Chromium 浏览器和模拟 Bearer Agent 客户端使用同一原子修订/指纹接口，旧浏览器表单、旧 Agent 均得到 HTTP 409；两 HTTP 请求竞争同资源一胜一拒；SQL 错误注入回滚；审计/幂等行为可读回。Saltcorn 原生 Field.update 特意绕过研究接口后，网关识别 OUT_OF_BAND_DRIFT 并拒绝后续读写，真正 Saltcorn REST/HTML 重启读回成功。**限域**：浏览器为自建网关页面，不是 Saltcorn 官方 /field 编辑器；原生编辑器仍可绕过；HTTP Agent 无大模型；直接写 _sc_fields 不可用于生产。详见 [完整报告](20-governed-http-evidence.md) 与 [结果 JSON](governed-http-observations.json)。

## E23 — Saltcorn 原生 Trigger、状态机、金额路由真实运行（S0）

[GitHub Actions #44876882097](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44876882097) completed/success，真正的 Saltcorn `@saltcorn/cli 1.7.0-beta.5`，Job 136763423876，Artifact 14695849924。通过 Pack 导入 3 条原生 run_js_code Validate/Insert Trigger、4 个业务表，创建真实路由/审批行。金额 AM01—AM12 **12/12**、状态机 ST01—ST12 **12/12**、三条完整审批/驳回轨迹 **3/3**、原生 SQL 元数据及 REST/HTML 等总计 **35/35** 项独立断言。对比实测物理金额列类型 **TEXT** vs 冻结 decimal(12,2) 是负面偏差，测试 PASS 指成功识别偏差。**角色来自可伪造的 actor_role 字段，FORBIDDEN 不是已认证 HTTP 403；没有真实 LLM Agent。** 一手代码依据：[Table.ts](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/saltcorn-data/models/table.ts)、[Trigger.ts](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/saltcorn-data/models/trigger.ts)、[Pack.ts](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/saltcorn-admin-models/models/pack.ts)。具体见 [研究报告 21](21-saltcorn-native-workflow-evidence.md)。

## E24 — 实际 Saltcorn 登录用户与原生 REST 审批权限（S0，限域）

真实 [Actions #44879041055](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44879041055) completed/success，32/32 独立断言，Job 136770054918，Artifact 14697420714。Chrome 浏览器四个真实 role_id=80 用户登录并取得当前 Session CSRF；原生 [api.ts](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/server/routes/api.ts) 将认证用户传给 Table.tryInsertRow，研究 [Validate Trigger](../../experiments/platform-saltcorn/auth/trusted-validate.js) 不相信客户端 actor_id/actor_role 而基于真正 user.id/email 检查：伪造身份 HTTP 400 IDENTITY_MISMATCH，错误业务级别 HTTP 400 FORBIDDEN；原生受限合同/审批表直接 POST 为 HTTP 401；有效一级/二级审批实际改变物理合同状态和审批行。重要实测缺令牌负对照：Session Cookie 请求缺 CSRF 经重定向后得到 HTML 200，但不写入；依据上游 [app.js](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/server/app.js) 的 CSRF middleware 边界。**同一原生角色 80 + 硬编码邮箱映射，不是正式组织 RBAC，也不是冻结 TC04 要求的 HTTP 403**。报告及失败历史：[22](22-native-identity-approval-evidence.md)。

## E25 — 受限工具协议的真实 Saltcorn 实证（S0，限域）

[Actions #44881082333](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44881082333) completed/success，代码 Commit 109dd420e48f2cd545f120ede450c47d5c82917e，Job 136776285247、Artifact 14698057458。**21 个工具对抗性单元测试 + 29 个原生 Saltcorn/Chromium/物理 SQLite 验收**全部通过：manifest 白名单新增只读路由工具，未知系统命令、额外身份参数、权限范围外、跨用户/合同、过期及重复授权被拒；独立授权后经真实 Saltcorn Session+CSRF 的原生 API 完成三次合同状态写入，最终 Approved/2 审批行，工具审计 16 条（10 次拒绝）。**模型推理 NOT_RUN；人工授权由研究控制器模拟，不等于真实签名授权；生产并发/事务、组织 RBAC、应用隔离均未证明。** 见 [报告 23](23-agent-tool-contract-evidence.md)。

## E26 — 进程重启后的调用占位与未知结果 fail-closed（S0 单元故障注入 + Saltcorn 回归）

[报告 24](24-durable-agent-calls-evidence.md)、[GitHub Actions #44881510363](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44881510363) completed/success，代码 e15b36e845611170ddced1bc739bdd80b994d710。原有工具调用的进程内 set 去重升级为 SQLite PRIMARY KEY 唯一调用账本，先占位 CLAIMED，再调用 Saltcorn；结果未知不自动重发。**29/29 单元**（新增 8 项跨 Broker 重启、已占位崩溃、远端先写后断、账本失效、授权重启失效等）+ **29/29 真实 Saltcorn 集成**成功，Artifact 14698431130。**并非真实 Saltcorn 网络 kill -9，也不证明分布式 exactly-once / 不同 call_id 的业务幂等**。无模型推理、实际人工授权与组织安全证明；G1 NOT_PASSED。

## E27 — DeepSeek 真实 CONFIG/CODE/HYBRID 分类与 Saltcorn 原生运行（S0 单次小样本实证）

[Actions #44884021495](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44884021495) completed/success，被测 Commit 4e9307b876db94c96ddc4f179353e7beccd40352，模型 Job 136785281254 / Artifact 14698694770，真实 Saltcorn Job 136785345227 / Artifact 14699311128。DeepSeek `deepseek-flash` 一次真实 HTTPS Function Call，6 个固定合同需求中 CONFIG/CODE/HYBRID **各 2/2，共 6/6 分类正确**，876 输入 +118 输出 = **994 Tokens**。受限路由确实驱动预装原生 Table、Field、List View、Validate/Insert Code Action Trigger，独立 SQL/HTML 检查 **20/20 PASS**：模 7 不合法校验码被真实平台拒绝，超过 100 万与恰好 100 万分别产生 HIGH/NORMAL 跨表审计。**仅预装能力选择，未由 AI 创建任何字段或代码**。单次六样本不足以推断泛化准确率，人机双向编辑未验收；G1 仍未通过。[完整报告](26-deepseek-mode-route-evidence.md)。

## E28 — 真正 DeepSeek 在实际人工浏览器编辑后接手并执行增量 Patch（S0，限定路径）

[GitHub Actions #44885275152](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44885275152) completed/success，被测 Commit c73b0319348070f670833310fb54cfa781cc17a4，Job 136789099373，Artifact 14699991457。**8/8 安全 Schema 单元 + 16/16 真实 Saltcorn/Chromium/DeepSeek/SQLite/HTTP 验收通过**。真实浏览器原生设计器保存 Human First Saved 之后，真正 deepseek-flash 根据最新物理元数据通过一次类型化 Tool Call 提议 status=AI Reviewed Status（491 输入 + 92 输出 = 583 Tokens）；守卫执行器在 SQLite BEGIN IMMEDIATE 中比对 title/status，再通过原生 Field.update 保存；第二次真实浏览器把 title 改为 Human Second Saved，原生字段页同时仍可见 AI status，旧 Patch 重放输出 STALE_REJECTED 且未写入。先做无模型 [平台预检 #44885046889](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44885046889) 16/16 以免重复模型付费。[完整报告 27](27-real-deepseek-human-roundtrip-evidence.md)。

**严格限定**：Playwright 在真正浏览器模拟人工操作，不是真实人员亲自点击；模型只提议而不生成代码/Schema；CAS 只覆盖研究 Agent CLI，不包括 Saltcorn 原生表单，旧浏览器继续可能覆盖新值。不得宣称全通道编辑安全、正式人工授权、完整 G1/TC 通过。
