# G1 P0-A：完整 Pack 差异审核、默认拒绝与受权 Native 分离预演（预注册）

**状态：提交时仅为预注册，实际通过与否必须以对应 GitHub Actions 原始运行结果为准。**

## 目标和同实例边界

在 **PR #23 已合并的 B9 同一个运行中的 B2 Kernel、单一 authority.sqlite、B5 Tool Broker、真实 Chromium 人工 Session、Agent、真实 Docker Plugin、Saltcorn Native v1** 上追加 **P0A-25—32 八项局部集成检查**。不创建新的权威库，不复用之前 B6/B9 的独立成功计数，不运行 DeepSeek。

重点针对冻结 **W12 原生 Pack 整包覆盖风险**：不得把 untrusted Pack 直接传给 Native 的 install-pack。新的 \`experiments/g1-b01-b9/pack_approval_gate.py\` 由可信 CI Controller 持有源头读取能力，并在**同一个实时 B2 v3 release.read** 上执行：

1. 按 **已实际运行且由独立 Native SQL 核验的 v1 基线**，将候选 Pack 的所有 JSON 路径递归比对，不省略 plugins/roles/pages/triggers/tables/extra fields、数组增删、字段类型变化；输出完整差异路径、变更前后值及散列，而非只展示批准过的字段。
2. 对每个候选重新读取 **当前 B2 release.read**，执行严格 \`compile_release\` + \`check_compiled\`；**只有候选 JSON 与最新受信编译结果完全相同**，才能获得待审批计划。凡有旧版代码、Pack 无关资源、附加插件/权限/表，默认拒绝、不调用 Native CLI。
3. 由**受信 Controller 模拟的专门高权限人工角色**对特定 Manifest、Source Release 版本、Pack SHA、完整 diff fingerprint 作一次性 HMAC 绑定授权；Agent/Plugin 无 pack.install 能力，缺少审批、伪造角色、签名或变更 Pack 都拒绝；批准后一律一次性消耗，失败/重试不得隐式重用。
4. 批准后仍再次检查 B2 最新版本/Manifest 和 Pack 字节，才允许**真正执行官方 Saltcorn 1.7.0-beta.5 CLI**，只安装在一份**新的、可删除、当前线上未使用的 Native staging SQLite**；用独立 Native SQLite Oracle 验证 View 列确实变化，**不把 staging 提升为线上**。过程中源头发生变化，产物视为不可信且不得发布。
5. 回滚 B2 发布指针到 v1 后，旧 v3 Pack 审批必须失效，staging 原生数据库删除；原先 Saltcorn 浏览器页面、物理 Native v1 不变。

## 预注册逐项场景

| 检查 | 真实运行路径 | 机器可判定结果 | 对应冻结 ID（仅局部） |
|---|---|---|---|
| P0A-25 | 前 60 项结束后，Agent 在同一 authority.sqlite 将 View 增加 title 列；已登录真 Chromium 人工提交 v3 发布 | Agent 200，真实浏览器发布 POST 200、v3 source/read 新鲜、物理 revision=16，v1 Native 原样 | W01、W17 |
| P0A-26 | 从 v1 真实已发布 Pack 到 B2 v3 当前 Pack 计算 **全 JSON 深度 diff** | diff 非空、包含 views/0/configuration/columns，全量 hash 稳定，Live Native 未变 | W12 |
| P0A-27 | 候选包伪造 unrelated table、admin role、arbitrary plugin、trigger、额外 Pack 顶级键 | 每个领域在完整 diff 都能看见；拟授权操作默认拒绝，Native CLI 未执行，物理权威/Native 均不变 | W12、W16 |
| P0A-28 | 不带人工批准直接执行；Plugin/Agent 请求不存在的 pack.install Tool | 批准拒绝，B5 403，Native CLI 计数=0 | W12、W14 |
| P0A-29 | 虚构批准者/没有高权限/伪造 HMAC/已批准后修改一字节 | 全部拒绝，Native CLI 计数=0，独立 SQL 零副作用 | W12、W13 |
| P0A-30 | 批准当前 B2 v3 对应的准确 Pack，实际官方 Saltcorn install-pack 启动新隔离 staging SQLite | 真 CLI exit 0、独立 Native SQL View 为 v3 四列、真实业务行可读；线上 v1 物理数据库与权威业务保持不变 | W11、W12、W17 |
| P0A-31 | 同一批准重复使用及故障注入、再次重放 | 同一批准只能用一次；失败时批准消耗、不覆盖线上/权威 DB，人工可另建新提案 | W10、W12 |
| P0A-32 | B2 v3→v1 回滚后尝试使用旧 v3 Pack 批准，并删除 staging | 拒绝旧批准，物理审计确认 v1 当前指针/Live Native/浏览器合同和 app-b 保持；staging 真删除 | W12、W18 |

## 严格限定、不可提前抬高 G1

- 此为**可信控制端模拟人工高权限批准**，不是生产身份服务、签章审计或可验证企业审批管理；B2 当前版本从受权 HTTP 读取并校验内核 Manifest，不是 Ed25519 签名事件的新鲜度证明。
- Saltcorn 原生 **Native owner UID 仍然拥有自己的派生库写权限**，任意持有该 UID/Native 管理员权限的用户仍能绕开此 **合法发布路径的 Pack Admission Gate**：本轮只验证**受控入站 Pack**，不能声称禁止 CLI/原生 Pack 直接操作整个派生库。必须另行证明 Native 强制隔离、出入口统一或只读对外。
- 真 Chrome 发布 v3 与 Native v3 staging **并非同一原子切换**；Live 端点保持 v1，之后 B2 发布指针回滚 v1。这种预演证明可经批准构造 v3 真实 Native 资源，不等于 W17 全通过，更不等于 P0-B Ed25519/B15/B17 正式热切换、运行时缓存、配置/Code/Workflow 的共同事务/回滚。
- 禁止将原本 60 个局部检查 + 本轮 8 项当作正式冻结 **W01—W24 或 TC01—TC18 FULL PASS**。本轮预期 **68 个集成检查**，加 Pack Gate 单元测试，原冻结 **42 项均 NOT_RUN、G1 NOT_PASSED**。
- 任一 untrusted Pack 在没有强审批的情况下进入 Native CLI、源头版本漂移仍被批准、未批准的 Plugin 工具能更新权威或 Native，立即 FAIL，保留 GitHub Actions 原始日志。

下一收敛阶段：真正的**同实例 B2 权威签名新鲜度 → B15 原子发布私有/公共只读快照 → B17 只读运行态 + 正式 HTTP / Chrome 新版本即时可见**，包含故障仍保留旧版本与业务/流程/代码的依赖闭包；不能以本轮 staging 流程取代。
