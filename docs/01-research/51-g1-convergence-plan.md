# G1 验收收敛任务单（2026-11-22）

## 门禁和口径

G1 **NOT_PASSED**。以 [W01—W24 冻结矩阵](31-g1-b01-acceptance-matrix.md) 和 [TC01—TC18 冻结合同](../../experiments/contract-benchmark/spec.json) 为验收源；两组目前分别为 **0/24 FULL PASS** 和 **0/18 FULL PASS**。此前 B1—B17 的成功计数是局部研究断言；B8 的同 UID 原生编辑器/CLI 旁路是真实失败反例，B17 原生标题保真失败也不能转成 PASS。只有独立 oracle、真实运行、完整用例和原始证据齐全才能改动状态。

[42 项逐项缺口账本](g1-convergence-ledger.json) 保存每项的责任任务包、局部证据入口和仍需完成的验收。`python3 scripts/check_g1_convergence.py` 校验冻结 ID、状态、证据文件及数量；该校验只保证账本完整，**不运行验收实验，也不证明这些证据满足 FULL PASS**。

## 收敛决策

停止按 B 序号继续堆积彼此独立的实验。当前优先候选是**独立 Domain Kernel 持有权威数据，人工编辑器、Agent 和插件仅调用受权命令；Native 仅为可重建的派生运行态或受控只读视图**。这只是待验候选；B17 的公开只读快照现已有同一 B2 SQLite 下真实人工表单写入、B11 事务性 Outbox、B14 对业务事件逐条 Ed25519 签名、B15 单文件原子 Publisher、B17 每请求最新发布与**业务 head/digest** 校验的实测证据，但尚未达到完整 G1 业务/代码/流程/外部补偿验收。Saltcorn 原生写入若仍能改权威库则立即 No-Go；若只写可丢弃副本，必须验证重新投影和运行时数据语义。

| 顺序 | 闭环任务与冻结用例 | 进入下一任务的实物证据 | 当前缺口 |
|---|---|---|---|
| P0-A | 一个权威进程/DB 边界，Web、Agent、真正沙箱插件均用可信身份/命令写；原生 Web/CLI/Pack 的所有越界写只能被拒绝或隔离在可丢弃派生库。W01—W16、W22；TC10、TC11、TC13、TC15 | 固定 SHA 的可重建环境、三种真实写入者、两进程竞争、原始 HTTP/Chromium、物理 DB/审计和权限负例；同 UID/root 能力、Pack 整包差异和缓存路径逐项记录 | **已得局部证据：**B2/B5/B6 Docker Plugin/B7 SQL/B9 Saltcorn 同一 authority.sqlite、Chromium/Agent、Pack 完整 JSON diff 默认拒绝/模拟高权限一次性审批与真实官方 Saltcorn 独立 staging 导入 **68/68**；**仍阻断：**生产级人工认证/Pack 审批与插件安装/撤销、Native owner UID 可操作自身可丢弃数据库、同 UID/root 旁路、签名新鲜度/原子运行态切换；B13/B14/B15 仍为单机限定路径 |
| P0-B | B2 权威源 → 签名发布 → B15/B17 只读消费贯通；先校验最新权威源和依赖闭包，再原子切换，错误保持旧 verified 版本；覆盖代码、配置、流程和外部副作用。W17—W20、W23、W24；TC12、TC16、TC18 | 一次版本发布/故障/回滚的 DB、REST、浏览器、签名、Manifest、构建哈希与回执全链对照；真实 timeout UNKNOWN 后按原 changeId 查证 | **已得限定局部证据：**[真实 B2 表单→B11 原子 Outbox→B14 逐事件 Ed25519→B15/B17 原子只读发布](57-g1-p0b-authoritative-business-outbox-signed-live-evidence.md) 同实例 **83/83**；真实 v1→v3→v1 加业务同版 1→2 条、B2 signed event/head/digest 新鲜度、Native 伪造行/错误签名/构建失败拒绝；**仍阻断：**B2 指针/Publisher 非共同事务（中间 HTTP 503）、可信 Controller 手工 Native CDC 补齐非可生产消费者、Form/Workflow/B4 Code 全依赖/回滚/外部 UNKNOWN 补偿未闭环，生产权限与 Native owner UID 旁路未关闭 |
| P1-C | 冻结合同业务端到端：1:N、金额边界、搜索、授权审批、状态机、合同号幂等、双应用隔离。TC01—TC05、TC08、TC15 | 从同一部署的人工创建到浏览器用户操作，独立 SQL/HTTP/DOM 验证 `spec.json` 全部 oracle | B2/B4 是若干业务切片，未逐项执行冻结的完整 TC 旅程 |
| P1-D | 最小一次真实 LLM 自主建模/表单/流程和超出配置能力的代码扩展；真正 Build Worker、隔离执行、失败保持旧发布；模型断开仍可人工维护。TC06、TC07、TC09、TC10、TC12、TC13 | 先零模型预检和成本边界，再仅在执行器全绿时一次受限 DeepSeek 请求；保存输入/工具轨迹/构建/独立 oracle | B3/B4 已验证片段，尚非冻结的完整自主开发和人工交接验收 |
| P1-E | 插件安装/发现/撤销和恶意工具输入、工作区/凭据攻击。W16、W21；TC14、TC17 | 真正插件 OS 边界、授权清单和独立拒绝/无副作用证据 | B6/B7 是研究插件，真实生产安装器与 Native 插件路径没有全部封闭 |
| P2-F | 路线和许可复审：Saltcorn 派生运行态与自有最小 Runtime 以等业务能力对照，记录复用成本；拟复制的代码逐文件许可核验。G1-B04/B05 | 运行证据、路线决策 ADR、许可边界与风险所有人签署 | NocoBase 创建器失败，平台对照和许可不能由 CI 成功自动解决 |

## 执行顺序与停止条件

1. 固定候选代码 SHA、环境、`W`/`TC` 原始用例与每项独立 oracle；对 42 项建立逐项证据记录，不修改冻结预期以适配结果。
2. 先做 P0-A 的最小可运行纵向切片。任何同 UID 原生进程可改**权威**数据且没有回执时立即停用该路线的自动写入/发布；派生库的越界修改须证明不会进入权威发布并可重建。
3. P0-B 必须在同一个实例中跑通，不把独立签名、只读、代码构建子实验相加。然后执行 P1-C、D、E 的完整冻结合同。
4. P2-F 形成正式复审。若按 README 的研究门槛调整 G1、将工程整套 PoC 留给 G3，必须**单独书面改门禁**、列出风险所有人和 S3 退出条件；本文件不自行降低既有冻结 W/TC 标准。

## 已通过的最新局部 CI（P0-A，仍不代表冻结 W/TC）

GitHub Actions [#44975954231](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44975954231) 和 [报告 55](55-g1-p0a-pack-review-approved-stage-evidence.md)：**68/68 同实例研究测试成功**，39/39 Pack 编译及审批单元、18/18 B2、40/40 B5、25/25 B6；零模型调用。真实 B2 v3 Web 发布 → 全 Pack diff → 默认拒绝未授权 Plugin/Agent → 一次性受信宿主人工批准 → 官方 Saltcorn install-pack 仅到新 Native staging → Native SQL 四列读回 → v3→v1 回滚旧批准失效及 staging 删除。**没有 Native 原生 owner UID 全覆盖保证，也没有生产 SSO 或 P0-B 原子切换。**冻结用例仍全体 NOT_RUN。

## 之前同实例 P0-B 模型/视图局部证据（不代表 FULL PASS）

GitHub Actions [#44978453572](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44978453572)、[报告 56](56-g1-p0b-signed-atomic-readonly-live-evidence.md)：同一 B2 权威数据库、Chrome、Agent、真实 Docker Plugin、Saltcorn Native 实例下 **77/77 局部集成验证 PASS**，39/39 Pack、18/18 B2、40/40 B5、25/25 B6；0 模型调用。Kernel UID Ed25519 签当前 B2 v1/v3，独立 Publisher/Reader UID、B15 单 SQLite 原子替换、B17 同 URL Chrome 无重启 3→4→3 列；签名错误、Native 列漂移、Build 故障均拒绝，不覆盖旧 verified 快照；B2 源先改变时 HTTP 503 fail-closed。**这些不是生产全局原子发布或完整业务/代码/流程证据**，42 个冻结用例仍 NOT_RUN。

## 已通过的最新 P0-B 真实业务数据闭环（局部，不代表 FULL PASS）

GitHub Actions [#44979988516](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44979988516)、[报告 57](57-g1-p0b-authoritative-business-outbox-signed-live-evidence.md)：同一个 B2 `authority.sqlite` 的已认证 Chromium 真实 `form.submit` → SQLite 同事务 B11 事件 Outbox → Kernel UID B14 Ed25519 **逐条真实业务行签名** → B15 对每条数据与当前 B2 outbox head/digest 和独立 Native SQL 相互核验 → B17 同一浏览器按业务 head 每请求检查 freshness。**83/83 同实例集成 PASS**；**49/49** 单元、18/18 B2、40/40 B5、25/25 B6，0 模型调用。新 B2 业务第二条写入后**同版发布 v1**，因 Native 落后 B17 返回 503 而非旧业务，B15 默认拒绝伪造 Native 行/签名，可信 Controller 真实 Saltcorn CLI 补齐第二条并原子重发，B17 无重启显示 2 行。**此受信手动补齐不是生产自动消费者，跨组件原子发布仍未证明。**42 项冻结均为 NOT_RUN。

## 下一次可改变决定的提交

**继续且仅继续 P0-B 缺口，不新起研究样例**：在现有真实 B2/B11/B14/B15/B17 同实例中，将此次手工 Native 业务补齐替换为**最小真正 B11 签名事件消费者：顺序、幂等、持久化 cursor/receipt、重放/差异/断连恢复，已验证后才发 B15 快照**；验证 B2 发布指针与 Publisher 之间 503 非原子窗口的实际协议/用户可用性约束；随后才推进 Form/Workflow/B4 Code 依赖闭包与外部 timeout UNKNOWN / 同 changeId 补偿。冻结 W17—W24/TC16/TC18 的正式 Oracle 不允许被累计局部检查替代，**G1 NOT_PASSED**。无模型验证前不调用 DeepSeek。
