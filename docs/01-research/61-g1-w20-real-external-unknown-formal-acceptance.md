# G1 冻结用例 W20：独立外部业务副作用 HTTP UNKNOWN / 按原 changeId 对账

## 结论（仅 W20）

**W20：PASS（冻结矩阵原定义）**。依据预注册标准，外部执行**真实发生**了 HTTP timeout，B2 先标记 UNKNOWN，并使用**原始 changeId** 查询外部业务副作用及其单事务回执；不换 changeId 盲目重试。该结果由独立验收器对运行中的 Chromium/B2 物理数据库/B11 Native 游标/额外 Linux UID 拥有的外部业务数据库/实际 HTTP 返回与副作用进行**逐项**校验。W20 PASS 不代表 W24 补偿、TC16 回滚、G1 整体通过。

**固定成功 CI**：[GitHub Actions #44988774947](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44988774947)，commit **`5a39591f6a3ce535d1f7f91ff548f7f2ab50146a`**, Job **137105048182**，[原始完整 Artifact #14740927216](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44988774947/artifacts/14740927216)。与本次全链同时运行了 [`scripts/verify_g1_w20.py`](../../scripts/verify_g1_w20.py) 对真实 `/tmp/s1-b9-evidence.json` 的**独立机器裁决**，原始日志包含 `G1_W20_FORMAL|{"status":"PASS","test_id":"W20",...}`，产物 `/tmp/s1-g1-w20-verdict.json` 可独立读取，CI 任一独立标准失效即非零退出。

冻结原定义（不修改）：[W20](31-g1-b01-acceptance-matrix.md) “外部执行返回 timeout，实际副作用结果未知”；Oracle “标记 UNKNOWN，按 changeId 查实际业务与 receipt；不换 ID 自动重放”；原始 [JSON](g1-b01-acceptance-cases.json) `expected: no new-ID blind replay`。冻结原测试仍是登记时的 `NOT_RUN` 历史基线，**实际运行结果通过收敛账本单独维护**；未回填、篡改冻结标准。

## 同一实例实际输入及独立 Oracle

1. 第 7 个独立真实 Linux UID **`ailcapb9external`** 启动隔离 localhost HTTP API 和只有其 OS 用户能直接打开的物理 `external-private/effects.sqlite`，不是 mock/内存结构。真实 Kernel/Publisher/Consumer/Plugin UID 直接打开该 DB 均 `DENIED`；外部服务独立持久化效果表与 receipt 表。
2. 同一个已登录的 B2 Chromium 在前序八条真实业务合同和自动 Publisher/B17 浏览器上，对第一条合同调用真实 `workflow.approval/records/<recordId>/advance`，原 B2 事务将 Draft→PendingLevel1、record version1→2，并触发**同一 B2 authority.sqlite** 的 B11 AFTER UPDATE 事件 seq9。受限 Consumer 真正自动追至 Native SQL cursor9、receipt9、8个物理 row maps；Publisher 自动切换 B2 激活 epoch7，原同一 B17 Chrome 8条记录更新状态。
3. Kernel UID 在原 B2 private DB 同事务核对真实 workflow record version2、B11 event/record 单快照一致，生成固定 `p0bnotify_<SHA256(recordId:2)[:40]>`；在发真实 HTTP POST 之前持久记录原始 command 的**hash + SUBMITTED + outbound attempts1**。
4. 远端第 7 UID HTTP Handler 在**另一个 OS UID 的 SQLite BEGIN IMMEDIATE 里先提交一条业务副作用及其 receipt**，然后延迟其 HTTP 响应超过 Kernel timeout。Kernel 真实网络客户端观察 `EXTERNAL_REPLY_UNKNOWN`，本地 B2 journal 状态 `UNKNOWN`；**实际外部物理 SQL 已有 1条 effect +1条 receipt**。通过真实另一个持有只读 bearer 的 `GET /v1/contract-effects/receipts/<same-changeId>` 返回 COMMITTED；这是双方独立业务/回执对照，不是单纯的 `publication.activate` HTTP timeout。
5. Kernel 根据**原 changeId** 执行 `--action reconcile`，校验外部 effect 的 B2 recordId、contractNo、workflowVersion、状态、action 与请求哈希及 receipt 均完全一致，B2 journal 更新为 CONFIRMED（attempts仍1）。对同一次原命令再次 send 直接读原 B2 journal，不向远端 POST：外部物理行/receipt 仍各1条。实际匿名 receipt 请求被 401 拒绝；相同 changeId 换另一请求体返回409、无新增副作用。
6. 原 B2 record SQL version2 状态 PendingLevel1、Native B11 seq9/receipt9 和外部独立 effect/receipt1 与已激活 B17 浏览器数据可互相核对；app-b 无变化、模型调用0。

**新运行检查**：P0B-44…P0B-48 五项均 PASS；既有 P0B-01…43 保持同实例全链 PASS，合计**116/116**；B9 49/49、B11 28/28、B12 22/22、B13 22/22、B14 24/24、B2 18/18、B5 40/40、B6 Docker 25/25 全通过；**0 大模型请求**。

## 与冻结其他用例的严格边界

本用例只证明**真实外部 effect COMMITTED 但 response LOST**的 UNKNOWN 正向对账与无重复 side effect。它**不测试真实外部完全未执行后怎样人工恢复或补偿已经不可逆执行的副作用**；外部未执行/外部补偿属于 W24 及完整 TC16 需要分别证明的业务语义。W02 原生 Saltcorn 编辑器 CAS、W19 自动代码构建失败、W23 全 Form/Workflow/Code 依赖、TC01–18 合同完整业务与 AI/插件旅程等未因 W20 被证明。

当前判定：**W20 1项正式 PASS，其余 W 的 23 项、TC 的 18 项仍 NOT_RUN；G1 `NOT_PASSED`。** 任何宣称 G1 整体通过或 116个局部集成测试=42个正式 PASS 都是错误的。
