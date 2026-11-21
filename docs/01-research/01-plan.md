# 第一阶段：深入调研执行计划

日期：2026-11-21。S1 进行中，G1 尚未通过。

## 研究范围与方法

不按 Star/功能数量排名；以同一个合同审批应用做对照，优先解剖五条调用链：自然语言到结构化计划；人工修改到 Agent 下一轮同步；平台能力不足到代码扩展；插件到工具注册及授权；不同应用之间的数据/代码/发布隔离。

**深挖 A：ToolJet + tooljet-mcp**。追踪 appPlanSchema、applyAppPhase、appVersionLifecycle、codeAppSync、codeAppIsolation，从校验入口追踪至持久化读回。

**深挖 B：NocoBase v3**。追踪 app-server 的插件声明与解析、agent-runner 的执行与凭据边界、插件加载/升级/数据库迁移，以及 Agent 与平台能力如何连接。

**横向校验**：Appsmith 的 widget registry、编辑器状态与持久化；Budibase 的 builder data binding、自动化与扩展。Astryx 仅为原型组件技术预研，不假定它是低代码编辑器。

## 原始材料规范

每个核心结论记录项目、默认分支、固定 commit、文件路径、函数、结论边界、证据等级。S0=实际运行可复现；S1=源码/测试静态检查；S2=官方文档；S3=二手描述。源码存在不能被记成“已成功执行”。许可证核对必须逐文件/模块，不能只看 GitHub 仓库的 license 元数据。

## 统一业务场景

合同表字段：编号、名称、金额（精确小数）、负责人、状态；审批记录 1:N；金额 **> 1000000** 触发两级审批（边界值等于阈值时不触发）；非授权人员不得批准或访问敏感数据。复杂代码扩展：合同编号生成器（唯一性、幂等）。连续迭代：人工修改按钮样式后 AI 修改文案，二者应保留。

## 工作包与顺序

1. WP1 冻结源码、许可证与版本：形成证据登记台账及许可待核清单。
2. WP2 追踪两项目关键调用链：工具输入 → 权限 → 校验 → 写入 → 读回 → 发布；断点明确。
3. WP3 同一合同场景可比较复现：记录人工步骤、代码量、AI 工具轨迹、测试和环境。
4. WP4 两套架构候选的风险/成本/扩展能力分析：用 ATAM 场景及 ADR 草案，而非主观排名。
5. WP5 微型 Spike：先做 C01/C02/C03/C07，再做 24 题路由测试和代码执行失败注入。
6. WP6 形成 G1 Go/Conditional Go/No-Go；不能靠文档完成率过门禁。

## 第一阶段交付清单

开源低代码深度研究报告；AI/传统能力矩阵；源码与许可证证据台账；架构调用链；可借鉴/应避免机制；八项假设；复现实验及门禁决策。每项对“已实现、部分实现、仅文档声明、源码可见、运行通过、未验证、不支持”作明确区分。

## 当前状态

已确认用户仓库 README 任务和初始空白目录；取得五个外部仓库固定 commit 并静态读取关键文件。**尚未完成**：实际部署运行、许可逐文件核实、端到端调用链、同场景复现、G1 决策。

## 2026-11-21 实施进展补充

WP2 已完成 ToolJet MCP Code mode 文件写入保护的首条源码调用链（[文档](04-tooljet-sync-trace.md)）；WP5 已完成 H01/H03 的可执行**模型层** A/B Spike（[报告](05-roundtrip-results.md)，[代码与结果](../../experiments/roundtrip/README.md)）。28 项 Python 单测通过，负对照覆盖缺陷复现。尚未部署任何第三方低代码系统、未执行其测试套件，**G1 尚未达到真实运行验证条件**。

## 2026-11-21 第二次推进

WP2 已深入检查 ToolJet/ToolJet 主服务端，确认 Code Mode 的 CE 控制器/服务为 stub，EE 子模块实际源码无法在本次取得；同时追踪了常规 AppVersion 持久化对象。NocoBase 方面读取插件定义、Agent Runner 的隔离/策略、凭据管理和 LICENSE.txt。WP5 已在真实 SQLite 文件数据库上执行 23 项回归与故障注入测试。见 [综合报告](07-persistence-and-license.md) 与 [实验代码](../../experiments/sqlite-roundtrip/README.md)。未完成真实第三方平台安装和场景复现，G1 尚未通过。

## 2026-11-21：统一对照与安装可行性验证

1. 已形成 [22 项能力证据分级矩阵](09-capability-matrix.md)，逐平台区分 SRC/DOC/BND/UNK，并保留固定 SHA 与源码入口。
2. 以 [合同基准](10-contract-benchmark.md) 冻结 12 项金额规则、12 项审批状态机及 18 项真实平台验收任务；这些任务尚未在平台执行。
3. 以 [GitHub Actions #44868550471](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44868550471) 实际尝试 NocoBase v3 官方 CLI 安装：Node24/pnpm11 成功，下载 app-template-default 时返回 E530/TEMPLATE_DOWNLOAD_FAILED。**属于安装阻断，不是业务用例失败**。
4. [G1 中期复审](12-g1-gap-review.md) 继续限定为 S1 受控研究，不进入正式 S2。

## 2026-11-21：真实低代码参考平台纵向切片

新增 Saltcorn MIT 作为第五个低资源、便于研究真实元数据到运行态的参考平台，并在 GitHub Actions 上实际运行：[Run #44869777036](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44869777036) 7/7，原生 fixture 表/视图/REST；[Run #44869926796](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44869926796) 9/9，以 Pack 配置合同/审批关联和列表、真实 SQLite 插入、REST 与页面渲染。详细见 [报告 14](14-saltcorn-real-platform.md)、[报告 15](15-native-contract-platform-evidence.md)。这一进展确证了真实第三方运行时可复现，但尚不满足原始合同 decimal(12,2)、审批、AI 自动配置及双向编辑，18 项正式业务验收保持 NOT_RUN。后续必须深测二次变更、版本冲突和真实 Agent 接手。

## 2026-11-21：针对 H01/H03 的原生编辑写入协议对照

已从 [Saltcorn 真实合同 Pack](15-native-contract-platform-evidence.md) 进一步执行同一合同资源上的三阶段研究：[GitHub Actions #44871169761](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44871169761) completed/success。非冲突局部 Field.update 能保留双方修改；旧完整 Pack 在仅需修改视图时却把无关人工标签和另一轮自动化标签还原，形成真实负对照；非原子旧基线检查可拒绝顺序冲突但不能支持真实并发。已生成 [源码+实测报告](16-saltcorn-roundtrip-evidence.md) 与 [候选 ADR](17-provisional-adr-guarded-editing.md)。**浏览器 UI 人工编辑、真实 LLM Agent、原子 CAS 和真实并发仍待验证，G1 未通过。**

## 2026-11-21 S1 SQLite 适配器事务与双进程写入的实证深化

已运行 [真正 Saltcorn + SQLite 两个独立 CLI 进程的原生 Field.update 实验](18-saltcorn-sqlite-atomic-evidence.md)：[GitHub Actions #44872093657](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44872093657)，completed/success。TX1 真实复现 Saltcorn SQLite withTransaction 抛异常但已更新字段未回滚；TX2/TX3 显式 BEGIN IMMEDIATE + 受控资源版本表支持不同字段并行和同字段旧版本拒绝；TX4 SQL 事务内原生写入后故障注入回滚；TX5 人工不走版本账本时后续自动化 CAS 误判成功并覆盖人工字段；TX6 真实 HTTP 读回。**七阶段 36 次断言符合预期，但 TX1/TX5 是危险负对照**。继续评估真实浏览器路由授权/保存和统一强制治理入口，G1 未通过。

## 2026-11-21：Web 人工设计器实证推进

新增 [真实 Chromium 两标签页字段编辑](19-real-browser-edit-evidence.md)，Run [#44873882208](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44873882208) completed/success。Playwright 在真实 Web 登录会话下打开两个持旧上下文的字段向导，分别提交，SQLite 显示 B 先保存后 A 旧页面覆盖 B；一次性 Web 管理员、CSRF、6 次真实 POST 及未认证跳转均有日志。模拟 Agent 再依据未更新的研究账本改写同一字段，真实数据库再次发生覆盖。**人工部分已是真实浏览器操作**，Agent 仍是确定性 CLI，不能误称 AI 协作验证通过。原 Run [#44873783039](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44873783039) 因 Playwright 不支持 GitHub ubuntu-latest 26.04 在安装阶段失败，修订 ubuntu-24.04 后完成，已归档失败根因。

## 2026-11-21：受治理 HTTP 编辑接口的正向研究闭环

在此前真实 Saltcorn 浏览器旧表单丢更新、外部版本表被绕过两类负例之后，本轮新增共享 HTTP 命令原型：[源码](../../experiments/platform-saltcorn/governed/README.md)，[GitHub CI #44874668928](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44874668928) completed/success。研究网关自建 Chromium 页面与确定性 Bearer Agent 共用 Saltcorn 真实 SQLite 修订及指纹，在独立数据库上 **G01—G22 22/22**，原生绕过时 **D01—D04 4/4**。数据库事务回滚、并发一胜一拒、409 版本冲突、审计/幂等和原生环境重启读回已有证据。具体 HTTP 结果以 [报告 20](20-governed-http-evidence.md) 为准；研究直接更新 _sc_fields 只可用于实验，不是生产适配方案。下一步优先真实 Agent 工具/合同审批，不再重复单字段版控小试。**G1 仍未通过。**

## 2026-11-21：S1 冻结合同业务实际运行而非继续字段标签测试

[Run #44876882097](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44876882097) 实际安装了含 4 个业务表、1 个原生视图和 3 个真正 Saltcorn Validate/Insert JS Action Trigger 的原生 Pack，并通过 Table.insertRow/updateRow 执行金额阈值及审批；独立 Oracle 在物理 SQL、CLI 日志、运行时 REST/HTML 验收 **35/35**，包括 12 金额边界、12 状态机、3 连续审批轨迹，证实超额合同需要二级审批。完整报告见 [21](21-saltcorn-native-workflow-evidence.md)。这比单纯比较 API Schema 更直接满足 README 1.4，但**角色仍为可伪造的请求字段、金额为 TEXT+分、没有 LLM**，不标正式 TC 通过。下一阶段 S1 工作重点：真实审批身份/HTTP 和真实 Agent 类型化工具；G1 不通过。

## 2026-11-21：真实登录身份/CSRF/原生业务审批写入的 S1 强化

[Run #44879041055](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44879041055) 真实 Saltcorn 登录与 REST 32/32 PASS；四个不同用户 Chromium 登录，在当前 Session Cookie+CSRF 下通过原生 API 触发 Validate/Insert 审批，伪造角色/用户 ID 返回业务 400，原生表级拒绝 401，正确审批写入物理状态与审批人记录。[报告 22](22-native-identity-approval-evidence.md)。前两次失败挖出了真实 CSRF/200 假成功问题；第三次虽 32 条逐条 PASS 但退出校验数误写为 28；第四次浏览器 GET 偶发超时；最终通过仅对非变更 GET 做重试，审批 POST 不自动重试。保留失败历史，仍不可宣称审批 SQL 原子性、企业角色/组织 RBAC、可视审批表单或 LLM Agent。下一 P0 转向**类型化 AI 工具授权与真实模型调用**，G1 不通过。

## 2026-11-21：Agent 工具执行契约阶段性实证

新增 [报告 23](23-agent-tool-contract-evidence.md)、[Run #44881082333](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44881082333)：类型化 Broker 的 **21/21 安全单元 + 29/29 真实平台集成**成功。固定只读工具/Manifest 能力发现，参数白名单、可信四用户 Saltcorn Session、跨主体与跨资源拒绝、短时单次授权、审计和真实状态读回；宿主模拟人工签发后的 3 次 Saltcorn 原生变更最终得到 Approved/2 审批行。无实际外部 LLM 选择或自主开发，下一工作继续验证持久化幂等、未知远端结果和真正模型接口。G1 不通过。

## 2026-11-21：S1 配置 / 代码 / 混合模式的真实模型选择最小实验完成

在真实只读 Function Calling 之后，新增六项预冻结模式分类研究：[真实 DeepSeek CI #44884021495](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44884021495) completed/success，**1 次调用/994 Tokens，六个模型选择 6/6 正确；真正 Saltcorn 执行验证 20/20**。代码仅预装允许的原生字段、List View、校验触发器和跨表审计，模型只选择受限枚举；此结果是 S1“能否做开发模式路由”的小样本正向证据，**不是 AI 自动开发应用**。离线预检先取得 [20/20](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44883844751)，避免一次推理中的平台失败产生额外费用。下一优先投入**真实人工编辑器和 AI 接手的安全正向闭环**，再整合 G1 正式选型，不再重复模式分类连通性收费测试。

## 2026-11-21：三项核心 S1 AI 机制均取得真实平台限域证据

工具选择：[报告 25](25-deepseek-real-tool-call.md)；模式选择：[报告 26](26-deepseek-mode-route-evidence.md)；真实浏览器/AI 交替编辑：[报告 27](27-real-deepseek-human-roundtrip-evidence.md)。最新 [Actions #44885275152](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44885275152) 8/8 单元 + 16/16 真实平台，通过一次 583 Tokens DeepSeek 调用读取 H1 的真实元数据并生成受限 status Patch，H2 浏览器继续修改后仍保留 AI 状态，旧 Patch 拒绝。三项虽都有**小范围正向实验**，但现有低代码功能、代码触发器和 CAS 都由研究人员预写；并未证明 AI 自主生成应用/代码，原生编辑器仍绕过版本门禁。后续优先集中剩余 S1 1.1—1.5 综合交付、候选 ADR 与正式 G1 决策，谨慎将完整 PoC 留到 S3。G1 NOT_PASSED。


## 2026-11-21：C2 第三方原生浏览器安全路径第一次真实插桩

C1 之后新增 [C2 真实 Saltcorn 字段路由研究](33-g1-b01-c2-native-route-evidence.md) 与 [Run #44887680474](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44887680474)：依托真实 Chromium、受签名的字段初始 label 上下文和研究修改后的原生 `fieldFlow.onDone` 检查，B 先保存，A 旧表单最终 POST 409，8/8 浏览器断言通过；但是另一个真正原生 CLI Field.update 绕过了 Web 补丁（危险负对照 1/1）。临时修改 npm 编译路由并不原子，不是平台可维护方案。因此 S1 的架构结论进一步收敛：**不能只治理 Agent 或浏览器，需要所有实际写入口强制经过同一可信核心**。G1-B01 仍 OPEN。
