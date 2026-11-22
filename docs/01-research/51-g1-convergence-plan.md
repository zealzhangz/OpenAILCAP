# G1 验收收敛任务单（2026-11-22）

## 门禁和口径

G1 **NOT_PASSED**。以 [W01—W24 冻结矩阵](31-g1-b01-acceptance-matrix.md) 和 [TC01—TC18 冻结合同](../../experiments/contract-benchmark/spec.json) 为验收源；两组目前分别为 **1/24 FULL PASS（仅 W20）** 和 **0/18 FULL PASS**；其余 41 项仍 NOT_RUN。此前 B1—B17 的成功计数是局部研究断言；B8 的同 UID 原生编辑器/CLI 旁路是真实失败反例，B17 原生标题保真失败也不能转成 PASS。只有独立 oracle、真实运行、完整用例和原始证据齐全才能改动状态。

[42 项逐项缺口账本](g1-convergence-ledger.json) 保存每项的责任任务包、局部证据入口、独立验证的 W20 正式结果和仍需完成的验收。`python3 scripts/check_g1_convergence.py` 校验冻结 ID、状态、证据文件及数量；该校验只保证账本完整，**不运行验收实验，也不证明这些证据满足 FULL PASS**。

## 收敛决策

停止按 B 序号继续堆积彼此独立的实验。当前优先候选是**独立 Domain Kernel 持有权威数据，人工编辑器、Agent 和插件仅调用受权命令；Native 仅为可重建的派生运行态或受控只读视图**。这只是待验候选；B17 的公开只读快照现已有同一 B2 SQLite 下真实人工表单写入、B11 事务性 Outbox、B14 对业务事件逐条 Ed25519 签名、B15 fsync/内容寻址预发布与**B2 同数据库原子 CAS 激活指针及回执**、B17 每请求当前发布/业务 head/digest/已激活 epoch 双重校验的真实证据，但尚未达到完整 G1 业务/代码/流程/外部补偿验收。Saltcorn 原生写入若仍能改权威库则立即 No-Go；若只写可丢弃副本，必须验证重新投影和运行时数据语义。

| 顺序 | 闭环任务与冻结用例 | 进入下一任务的实物证据 | 当前缺口 |
|---|---|---|---|
| P0-A | 一个权威进程/DB 边界，Web、Agent、真正沙箱插件均用可信身份/命令写；原生 Web/CLI/Pack 的所有越界写只能被拒绝或隔离在可丢弃派生库。W01—W16、W22；TC10、TC11、TC13、TC15 | 固定 SHA 的可重建环境、三种真实写入者、两进程竞争、原始 HTTP/Chromium、物理 DB/审计和权限负例；同 UID/root 能力、Pack 整包差异和缓存路径逐项记录 | **已得局部证据：**B2/B5/B6 Docker Plugin/B7 SQL/B9 Saltcorn 同一 authority.sqlite、Chromium/Agent、Pack 完整 JSON diff 默认拒绝/模拟高权限一次性审批与真实官方 Saltcorn 独立 staging 导入 **68/68**；**仍阻断：**生产级人工认证/Pack 审批与插件安装/撤销、Native owner UID 可操作自身可丢弃数据库、同 UID/root 旁路、签名新鲜度/原子运行态切换；B13/B14/B15 仍为单机限定路径 |
| P0-B | B2 权威源 → 签名发布 → B15/B17 只读消费贯通；先校验最新权威源和依赖闭包，再原子切换，错误保持旧 verified 版本；覆盖代码、配置、流程和外部副作用。W17—W20、W23、W24；TC12、TC16、TC18 | 一次版本发布/故障/回滚的 DB、REST、浏览器、签名、Manifest、构建哈希与回执全链对照；真实 timeout UNKNOWN 后按原 changeId 查证 | **G1 冻结 W20 首项已形成正式独立 PASS 证据：**[真实外部业务 HTTP timeout/物理 SQL 副作用/同 changeId 对账（报告 61）](61-g1-w20-real-external-unknown-formal-acceptance.md)，[CI #44988774947](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44988774947) 真实外部第 7 Linux UID 的独立 effects.sqlite 和 receipt、原 B2 Chromium Workflow/B11 原生 Native 校验、独立 `scripts/verify_g1_w20.py` 裁决 `W20 PASS`；**这只满足 W20 本身，不替代 W24 补偿/TC16/其它 41 项**。此前**局部证据：**[真实 Publisher UID 自动编排、B14/Native 独立只读 IPC、HTTP UNKNOWN 回执对账](60-g1-p0b-autonomous-release-and-unknown-reconciliation-evidence.md) 同实例 **111/111 PASS**，[CI #44987613241](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44987613241)；沿用同一 B2 Domain/B11/B14 持久消费者，非 root Publisher 独立从 Native SO_PEERCRED 只读 SQL oracle 与 Kernel 受限来源签名能力自动执行 B15 prepare+内核原子 activation，故障后自动恢复头 5/6/7/8 条合同，真实 HTTP **提交后丢响应**经持久 changeId receipt 查证一次完成，**提交前丢响应**阻断自动重放须人工按原 ID 审核；B17 同 Chrome 8 行；**仍阻断：**领域发布与 B15 不同事务仍有 503 窗口、真正外部非事务业务副作用 UNKNOWN/W20 未闭环、Form/Workflow/B4 Code/插件安装和生产身份/多活未完整验证，Native owner UID 派生库旁路可造成 503。 |
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

## 最新同实例 P0-B 持久消费者局部证据（不代表 FULL PASS）

[CI 完整成功 #44982079396](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44982079396)：91/91 实际同实例集成检查、49 B9 单元、B11 28、B12 22、B13 22、B14 24、B2 18、B5 40、B6 25 均 PASS；0 模型调用。注意这是研究切片，非正式冻结 W/TC FULL PASS。

[报告 58](58-g1-p0b-signed-durable-consumer-recovery-evidence.md) 接续 [报告 57](57-g1-p0b-authoritative-business-outbox-signed-live-evidence.md)，新增**第六 Linux UID 的真实 B14 签名事件消费者**；通过 B13 AF_UNIX peer UID + 0750 目录/0660 socket DAC，只能签名调用、无 Kernel/Native DB 读取权限；B11 业务行/receipts/映射/游标在同一 Native SQLite 事务提交，重放前两条实际已签 B2 事件返回 replayed=2/applied=0，Consumer PID 真正重启恢复 cursor2。真实 Kernel 签名 Source 关闭，已登录 Chrome 第三次 B2 form.submit 后 B17 503 并保留旧 verified 文件，Source 使用同一本地端口/原密钥重启，原 Consumer 自动捕获 B11 事件第三条，无人工 Native seed，B15 原子替换后同一 B17 URL/浏览器显示三条。**91 项是局部集成检查，不是冻结 W/TC 完整测试**；B2/B15 仍存在 503 窗口、生产自动发布/多活/Workflow/代码/外部 UNKNOWN 尚待解决。

## 最新同实例 P0-B B2 原子激活 CAS 与内容寻址预发布证据（不代表 FULL PASS）

[CI #44983773857](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44983773857)、[报告 59](59-g1-p0b-kernel-atomic-activation-and-cas-evidence.md)：复用之前真实同一 B2 Kernel/B11/B14 Consumer/B15 Publisher/B17 Chrome，加 **P0B-24—33 十项真实验证，总 101/101 PASS**；同一 `authority.sqlite` 的 `BEGIN IMMEDIATE` 内检查 B2 当前 `apps.current_release`、真实 B11 Outbox 与 Records 并持久化 CAS active SHA/epoch/changeId receipt，B15 prepare-only 候选 fsync 后公开视图仍取旧已验证快照，唯 Kernel 可信 activation 可切换。测试已验证：欠权/缺失候选/过期 epoch 拒绝；按原 changeId 幂等重放；已激活候选字节篡改 B17 503、恢复字节 B17 200；真实 B2 人工第四条合同引起旧 active 与最新 B11 head 冲突 B17 503，Consumer 自动追平、过时候选无法激活；Kernel 事务**提交前注入异常** receipt/epoch 整体回滚；真实并发两请求 CAS **一个200一个409**，B17 同 URL/Chrome 四条合同正确呈现且旧 legacy 文件未替换。B9 49、B11 28、B12 22、B13 22、B14 24、B2 18、B5 40、B6 25 单元回归均通过、**0 模型调用**。这不是断电可靠性、跨 B2 领域发布与文件系统的全局原子事务或零中断切换；冻结 42 项状态仍 NOT_RUN。

## 最新 P0-B 自动发布编排与真实 UNKNOWN 对账局部证据（仍不代表 FULL PASS）

[CI #44987613241](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44987613241)、[报告 60](60-g1-p0b-autonomous-release-and-unknown-reconciliation-evidence.md) 在同一 B9 实例增加 **P0B-34—43 十项，共 111/111 PASS**。基于原 B11/B14 真实 Durable Consumer 增加**实际非 root Publisher UID 的自治持续编排**：独立权限范围只读 Native SQL socket（与 Consumer 写入 socket 不共享授权组）及 Kernel-only B14 signed-release bearer，自动对照 B2 release+业务 head、Native cursor+receipts+真实 Saltcorn SQL、签名 Manifest/Pack，再 B15 fsync prepare → B2 单事务 `publication.activate`。真实第 5、6 条合同及 B14 signer 真进程断源恢复不靠 Controller 逐次发布、同一 B17 浏览器从4行增加到6行；第7条**真实 HTTP 已向 B2 提交且获200但客户端没有收到响应**，Publisher durable journal记录 UNKNOWN 并通过 `publication.receipt` 依照原 changeId reconcile，不新增人工 ID/重复 side effect；第8条**请求转发前超时** Kernel receipt 确实 NOT_FOUND，Publisher 停止自动重试转为人工审核后以**原 changeId**发布，B17 恢复八行。实际 Publisher Linux PID 真重启，journal/权限和发布 epoch 仍连续。**缺口：真实外部非事务操作的 UNKNOWN 并未被模拟 Kernel 自身激活代替，自动出站仍属于 CI 单机本地实验。**

## 首项冻结 W20 正式验收结果（不等于 G1 整体验收）

[报告 61](61-g1-w20-real-external-unknown-formal-acceptance.md)、[机器裁决](g1-w20-formal-verdict.json)、[原始 CI #44988774947](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44988774947)：同一 B2 已登录真实 Chromium 提交第一条合同 `workflow.approval` Draft→PendingLevel1，B11 AFTER UPDATE seq9、Native 持久 cursor9 与 B15 自动激活 epoch7 同步；**完全独立第 7 OS UID 的真实业务 HTTP 服务**在另一 SQLite 同事务先提交业务通知 effect+receipt 各1条，延迟响应让 Kernel 实际收到 timeout/UNKNOWN；Kernel 在真实 B2 private SQLite 预先持久原 changeId 和出站1次，通过外部 HTTP GET/物理 SQL 审核原业务与 receipt 对照后标记 CONFIRMED，重复 dispatch 无 HTTP 重放，改变 payload 同一 ID 外部409、越权读取401。P0B-44—48 **5/5**、全 B9 **116/116**、**独立冻结 W20 机器裁决 PASS**。**G1 正式计数 W 1/24，TC 0/18，其余 41 NOT_RUN，仍 NOT_PASSED**。

## 下一次可改变决定的提交

**按照完整 G1 W/TC 门禁推进，不再延伸 P0-B 自循环验证计数**。已证实发布链上 Kernel 激活/网络响应 UNKNOWN 的局部机制，下一步必须进入**真正外部业务副作用的 timeout UNKNOWN/changeId 对账、同一实际合同 Form→Workflow→自定义 Code 扩展/依赖验证**，并逐项把冻结 W/TC 的原始 DB、REST、Browser、构建、身份和独立验收器证据落实。保留原生 Saltcorn C2 编辑器无法完整拦截、安全认证、生产多活/断电、插件安装/撤销和 AI 自动开发的真实 No-Go，不得以过去 111 条局部断言冒充 42 个正式 PASS；未完成前 G1 `NOT_PASSED`，最小必要范围内才运行真实模型请求。
