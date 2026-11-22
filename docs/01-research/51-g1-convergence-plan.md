# G1 验收收敛任务单（2026-11-22）

## 门禁和口径

G1 **NOT_PASSED**。以 [W01—W24 冻结矩阵](31-g1-b01-acceptance-matrix.md) 和 [TC01—TC18 冻结合同](../../experiments/contract-benchmark/spec.json) 为验收源；两组目前分别为 **0/24 FULL PASS** 和 **0/18 FULL PASS**。此前 B1—B17 的成功计数是局部研究断言；B8 的同 UID 原生编辑器/CLI 旁路是真实失败反例，B17 原生标题保真失败也不能转成 PASS。只有独立 oracle、真实运行、完整用例和原始证据齐全才能改动状态。

[42 项逐项缺口账本](g1-convergence-ledger.json) 保存每项的责任任务包、局部证据入口和仍需完成的验收。`python3 scripts/check_g1_convergence.py` 校验冻结 ID、状态、证据文件及数量；该校验只保证账本完整，**不运行验收实验，也不证明这些证据满足 FULL PASS**。

## 收敛决策

停止按 B 序号继续堆积彼此独立的实验。当前优先候选是**独立 Domain Kernel 持有权威数据，人工编辑器、Agent 和插件仅调用受权命令；Native 仅为可重建的派生运行态或受控只读视图**。这只是待验候选；B17 的公开快照尚未接入 B15 签名发布与 B2 权威新鲜度核验，不能宣称已经封闭。Saltcorn 原生写入若仍能改权威库则立即 No-Go；若只写可丢弃副本，必须验证重新投影和运行时数据语义。

| 顺序 | 闭环任务与冻结用例 | 进入下一任务的实物证据 | 当前缺口 |
|---|---|---|---|
| P0-A | 一个权威进程/DB 边界，Web、Agent、真正沙箱插件均用可信身份/命令写；原生 Web/CLI/Pack 的所有越界写只能被拒绝或隔离在可丢弃派生库。W01—W16、W22；TC10、TC11、TC13、TC15 | 固定 SHA 的可重建环境、三种真实写入者、两进程竞争、原始 HTTP/Chromium、物理 DB/审计和权限负例；同 UID/root 能力、Pack 整包差异和缓存路径逐项记录 | **已得局部证据：**B2/B5/B6 Docker Plugin/B7 SQL/B9 Saltcorn 同一 authority.sqlite、Chromium/Agent、Pack 完整 JSON diff 默认拒绝/模拟高权限一次性审批与真实官方 Saltcorn 独立 staging 导入 **68/68**；**仍阻断：**生产级人工认证/Pack 审批与插件安装/撤销、Native owner UID 可操作自身可丢弃数据库、同 UID/root 旁路、签名新鲜度/原子运行态切换；B13/B14/B15 仍为单机限定路径 |
| P0-B | B2 权威源 → 签名发布 → B15/B17 只读消费贯通；先校验最新权威源和依赖闭包，再原子切换，错误保持旧 verified 版本；覆盖代码、配置、流程和外部副作用。W17—W20、W23、W24；TC12、TC16、TC18 | 一次版本发布/故障/回滚的 DB、REST、浏览器、签名、Manifest、构建哈希与回执全链对照；真实 timeout UNKNOWN 后按原 changeId 查证 | B17 未校验 B2 最新源；B15 签名快照和 B4 代码发布没有完整共同事务/回滚；UNKNOWN 补偿缺完整场景 |
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

## 下一次可改变决定的提交

**立即优先 P0-B 同实例贯通**：权威 B2 新版 Manifest/Release 与签名源事件，B14 Ed25519 独立审计，B15 不可变快照及可审计 Publisher，B17 read-only public/runtime，必须在**同一 authority.sqlite、同一已发布 v1→v3→rollback 和同一个浏览器会话**核验签名新鲜度、Manifest/Pack/代码/流程依赖闭包、原子指针、HTTP/DOM 与物理数据库；故障/过时/篡改拒绝并留旧 verified 版。现有 [Pack Gate 同实例局部证据](55-g1-p0a-pack-review-approved-stage-evidence.md) 只验证受权 staging，不等于生产审批、Native 原生任意 owner UID 路径已封闭，也不等于 P0-B 热切换；外部 UNKNOWN/补偿和全部冻结 W/TC 仍待正式核验。完成无模型预检前不新增模型调用。
