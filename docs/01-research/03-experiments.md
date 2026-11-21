# 最小技术实验协议（模型层部分已执行；真实平台验证未执行）

日期：2026-11-21。所有用例先冻结输入、预期、版本和评价器，再运行生成器；AI 不能修改验收脚本。每次记录 commit、模型版本、工具/环境版本、操作轨迹、耗时、Token、状态快照、测试结果、回滚与失败原因。

## C：Round-trip 一致性

先用受限对象模型跑 C01/C02/C03/C07，再扩大到 10 个用例和真实低代码编辑器。基线按钮 label=提交、background=blue、金额阈值 >1000000、自定义代码哈希固定。对照：整页覆盖负例 / CAS+三方合并 / 操作日志。判据：非冲突全部保留；冲突拒绝；revision 相同内容不同时识别；多对象写入失败能回滚；无静默丢失。

## R：配置/代码/混合路径路由

固定 24 题，配置 8、代码 8、混合 8，独立人工标注后各重复 3 次。评价不止“分类对不对”，还要检查真正的业务验收。不可配置任务被伪装为纯配置并标记成功，容忍数为 0。

## B：AI 自定义开发闭环

合同编号生成插件：唯一性/幂等/权限。Agent 输出代码，运行独立构建、单测、集成、安全、健康探针及隔离部署。注入编译失败、权限越界、密钥泄漏、错误审批边界、健康检查失败。硬性门禁：失败不可发布；旧版本可用；可回滚；修复次数有预算。

## D：插件发现与多应用隔离

新增插件不改核心 Prompt，AI 从 Manifest/Schema 自动发现；升级时识别非兼容变化。创建 A/B 应用，同名组件，测试读/写/构建/部署的未授权跨应用调用。预期越权成功次数 0。

## 完成证据与报告结构

每条运行记录：test_case_id、repo_sha、environment、input、operations、expected、actual、test_report、rollback_report、result（PASS/FAIL/BLOCKED/NOT_RUN）、evidence_paths。

禁止把存在测试代码当成测试已执行；禁止只筛选成功样例；不得让生成 Agent 自行宣布验收通过。第一阶段最小模型试验成功只支持模型层可行性，第三阶段还需要真实运行时 PoC。

## 2026-11-21 实验执行回填

C 组（H01/H03）已完成模型级 C01—C10：Unified IR 10/10、分域 Schema + Manifest 10/10；含防御性单测共 28/28 通过。复现了旧快照整页覆盖导致人工样式丢失的负对照。具体命令、机器可读结果和暴露的可信基线问题见 [实验报告](05-roundtrip-results.md) 与 [实验工程](../../experiments/roundtrip/README.md)。

R（路由）、B（代码闭环）、D（插件/应用隔离）均未执行；C 的真实低代码运行时版本也未执行。不能宣称 G1 或 G3 通过。

## 2026-11-21 SQLite 持久化实验回填

新增了独立的 [SQLite 文件数据库与事务测试](../../experiments/sqlite-roundtrip/README.md)：23 项独立测试全部通过，覆盖并发写事务、异常退出后恢复、乐观冲突、重复命令、版本回退以及模拟的 app_id/ACL 拒绝。它不是平台级实验；真实用户认证、Agent 编码执行、部署及第三方平台安装尚未执行。G1/G3 未通过。参考 [研究报告](07-persistence-and-license.md)。

## 2026-11-21：正式业务场景基准预注册

为后续真实平台和自研平台的同条件实验固定了 [合同业务规范](../../experiments/contract-benchmark/spec.json)：12 项金额边界、12 项审批转移预期和 18 项平台级验收任务。Oracle 仅校验规范一致性，所有平台任务现为 NOT_RUN。参见 [验收协议](10-contract-benchmark.md)。真实平台安装被 NocoBase v3 默认模板仓库 E530 阻断，没有新增平台级通过项。

## 2026-11-21：真实 Saltcorn 多轮编辑协议对照（阶段 S1）

独立工作流 [#44871169761](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44871169761) 已实际执行 A/B/C 和 C-HTTP 四组验证，18/18 次断言符合预期，四份 JSON 作为 GitHub Artifact 14694023138 上传。最重要的是 B 路径：恢复基于旧上下文的完整 Pack 会覆盖人工已保存的 title.label，属于显著**负面证据**；A 仅证实不同字段的串行 Field.update 不相互影响；C 仅证实应用层旧基线检测能拒绝一例顺序冲突，**不是原子 CAS**。实验没有真正调用大模型或浏览器人工编辑。见 [实测报告](16-saltcorn-roundtrip-evidence.md) 和 [源码工程](../../experiments/platform-saltcorn/roundtrip/README.md)。

## 2026-11-21 SQLite 真实原生事务与并发回填

[Run #44872093657](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44872093657) 实测七组 36 次断言，包含两个不同 CLI 进程并发写入相同/不同 Saltcorn Field、真正 SQLite BEGIN IMMEDIATE 和 Field.update 同事务、事务内注入失败后 ROLLBACK、浏览器编辑器类似的直接原生更新绕过研究版本账本。实际同字段竞争一胜一旧版本拒绝；但 sidecar 账本被绕过时后续 CAS 仍错误接受覆盖。Saltcorn SQLite withTransaction 内真实事务语句被注释，异常后修改保留。**实验代码/审计报告**见 [atomic/README](../../experiments/platform-saltcorn/atomic/README.md)、[报告](18-saltcorn-sqlite-atomic-evidence.md)。没有真实认证浏览器会话或 LLM Agent。**G1 未通过**。

## 2026-11-21：S1 真正人工 Chromium 浏览器实验完成

成功 GitHub [Run #44873882208](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44873882208)（Commit c0683877）运行了一次性 Saltcorn+SQLite、Chromium 真实管理员登录、正常 CSRF 字段向导、两个持旧上下文的浏览器标签页。UI01—UI09 **9/9 PASS**；B 保存字段标签后 A 旧页面保存将 B 变更覆盖，为真实 UI 失效反例。随后 CLI 确定性自动化以错误滞后的外部版本表覆盖浏览器变更，U10—U13 共 **5/5 PASS（含危险负例）**。交付 [浏览器脚本](../../experiments/platform-saltcorn/browser/README.md)、[完整研究报告](19-real-browser-edit-evidence.md)、[独立证据摘要](browser-edit-observations.json)。首次环境失败 Run #44873783039 归因为 Playwright 1.56 不支持 GitHub ubuntu-latest Ubuntu 26.04，固定 Ubuntu 24.04 后通过。未运行真实 LLM/跨应用/审批，G1 不通过。

## 2026-11-21 H03 正向写入协议实验

GitHub [Run #44874668928](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44874668928) 真实 Saltcorn SQLite + Chromium + 统一研究 HTTP 接口：**G01—G22 22/22**（鉴权/CSRF、422、409、内容指纹、跨应用拒绝、重放幂等、两独立 HTTP 并发、故障回滚、审计）及 **D01—D04 4/4**（Saltcorn 原生 Field.update 绕过研究账本，网关实际识别漂移并失败关闭），最后 Saltcorn REST/HTML 重启可用。原始 Artifact 14695407749。仅证明研究接口内的受控写入，不等于生产级原生设计器改造、真实 LLM Agent 或原合同业务全面验收；G1 仍未通过。证据见 [报告 20](20-governed-http-evidence.md)。

## 2026-11-21：Saltcorn 原生业务 Trigger 首次完整金额/审批轨迹

[Run #44876882097](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44876882097) 已对冻结 spec.json 的 12 金额输入、12 状态迁移在真实 Saltcorn Table.insertRow/Validate/Insert Trigger/run_js_code 上执行，对三条持续状态路线完成独立物理 SQLite 验收，并核对原生 REST 和 List View。**35/35 断言符合预期**。其中 WF05 证实金额物理列是 TEXT 并非冻结 decimal(12,2)，属于负面差异证据。研究 CLI 强制 SQL 事务，不代表 Saltcorn 原生 HTTP 动作的默认原子性。模拟审批角色是调用方声明字段，不是真实用户身份。没有模型 Agent、浏览器审批提交，完整 TC 仍 0/18。详见 [报告 21](21-saltcorn-native-workflow-evidence.md)、[源码](../../experiments/platform-saltcorn/workflow/README.md)。

## 2026-11-21 实际 Saltcorn 用户会话与合同原生审批 API

[最终 Run #44879041055](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44879041055) 实测 32/32 PASS：4 位真实 Saltcorn 用户通过 Chromium 原生登录表单，实际认证 Session Cookie + 从同一会话读取的 CSRF Token 请求原生 /api/s1_bench_action_requests/；Saltcorn Validate/Insert Trigger 将原生 req.user 绑定审批动作，伪造 ID/角色无法修改状态，普通与高金额两级审批、驳回均持久化；普通用户不能直接改合同/审批明细。前两次真实失败验证缺 CSRF 的请求经 HTTP 重定向最终出现**HTML 200 假成功**且数据库不变；应将最终 URL、Content-Type 和物理记录作为统一验收条件。代码 [auth](../../experiments/platform-saltcorn/auth/README.md)、[报告 22](22-native-identity-approval-evidence.md)。Saltcorn 原生只区分已登录 role 80 与管理员，业务审批角色由研究硬编码邮箱判定，HTTP 400/401 不满足冻结业务 TC04 要求的 403；没有正式审批 UI/真实 LLM/完整事务及多租户授权，G1 继续 NOT_PASSED。

## 2026-11-21 类型化 Agent 工具 Broker、权限和真实 Saltcorn 适配

[Run #44881082333](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44881082333) 中 21/21 stdlib 单元与 29/29 原生 Saltcorn 集成均成功；并非 Prompt 自我声明：实际 Browser Session/CSRF 和 SQL 主表/审批明细/工具审计共同裁判。白名单 Handler Manifest 能增加只读能力，危险 handler 被拒绝；宿主单独模拟授权后，真实 Saltcorn 原生触发器完成 Draft→Submitted→Level1Approved→Approved。**实际模型推理 NOT_RUN，人工确认仍属实验模拟**。代码见 [实验工程](../../experiments/agent-tools/README.md) 和 [报告 23](23-agent-tool-contract-evidence.md)；G1 不通过。

## 2026-11-21：单次 DeepSeek 模式路由 + 原生执行端到端证据

[Actions #44884021495](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44884021495)：DeepSeek `deepseek-flash` 1 次 Function Calling 推理批量选择 6 个固定需求的 CONFIG/CODE/HYBRID 模式，**6/6 预登记参考标签匹配**，实际 Saltcorn Native Pack/Model/Trigger/View/SQLite/HTML **20/20 PASS**，只消耗 994 Tokens；原始预测与平台验收分开保存在两个 Artifact 中。独立 [离线无模型平台预检 #44883844751](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44883844751) 20/20，不计模型分数。禁区：这不是模型生成代码/Schema、不涉及真实人工设计器，也没有多次任务的可靠性/准确率验证。[报告 26](26-deepseek-mode-route-evidence.md)。

## 2026-11-21 真正 Saltcorn 人工浏览器 → DeepSeek → 受限字段修改 → 人工浏览器

[实测 Run #44885275152](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44885275152) completed/success，**1 次真实 deepseek-flash Function Calling（583 Tokens）、8/8 单元 + 16/16 真实浏览器/原生平台数据校验**。首个 Chromium 原生向导通过 CSRF 与 contextEnc 修改标题；模型观察真实 _sc_fields 后只提议 status 标签；可信控制器以 BEGIN IMMEDIATE 双字段快照检查、原生 Field.update 更新；第二次浏览器编辑 title 后在原生 status 编辑器核对 AI 字段，旧提议再次执行为 STALE_REJECTED、未写。独立从 SQLite 及 HTTP 业务页面验收。对照 [无模型预检 #44885046889](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44885046889) 完整 16/16。仍未对**原生浏览器写入**实现 CAS，先前危险覆盖真实负例保留。源码 [collab](../../experiments/platform-saltcorn/collab/README.md)、[报告 27](27-real-deepseek-human-roundtrip-evidence.md)。G1 NOT_PASSED。
