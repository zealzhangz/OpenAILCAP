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


## GitHub Actions 实际结果（2026-11-22）

- 在源代码 SHA **`ecbae9b9ed3f46a05d5c9929cd237e6be8557fa0`** 上，[完整 GitHub Actions #44975954231](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44975954231) **completed/success**，Job **137065809087**，[原始日志与可复核 SQL JSON Artifact #14735083303](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44975954231/artifacts/14735083303)。
- **B9 36 + 之前 P0A 24 + 本轮 P0A-25—32 8 = 68/68 真实同实例局部检查全部 PASS**。回归：原 Pack 编译 25 + 新 Pack 审批 14 = **39/39**；B2 **18/18**，B5 **40/40**，B6 真实 Docker host Relay 策略 **25/25**。**模型调用 0，G1 Passed=False。**
- **P0A-25**：真实已登录 Chromium 发布请求 HTTP 200，B2 v3 release.read 为 v3，草稿 revision=16，权威 SQLite 确认第三份 immutable release；Live Saltcorn v1 尚未切换。
- **P0A-26**：计算旧 Pack hash `ddb9823d07cf0051d3d01bcaf291c9f2bac04cec89dcd41633230d309d7bb259` 至批准的 v3 Pack hash `85466086185b481ba7759e5cd33af23429c579e2b12ac00db3c2adf123af7424` 的完整 JSON Pointer 差异，真实发现 `/views/0/configuration/columns/1/field_name`、`/views/0/configuration/columns/2/field_name`、`/views/0/configuration/columns/3` 三处；不存在无证据自动转成安全的字段。
- **P0A-27—29**：外部恶意包插入 `/customUnsafeDomain`、`/plugins/0`、`/roles/0`、`/tables/1`、`/triggers/0`，全部完整差异可见，拒绝导入；**真正 Docker Plugin** 请求 `pack.install` 返回 **HTTP 403**，Agent 同为 403。缺少批准、虚构高权限、伪造 HMAC、Pack 内容变更均在 Native CLI 执行前拒绝。
- **P0A-30**：**真正 Saltcorn 官方 install-pack** 在经过一次性模拟高权限人工批准后对**独立派生 staging SQLite** 返回 exit 0；独立 Native SQL 查到 v3 的四列 `contract_no,title,amount_minor,status` 及真实一条合同数据；同时线上 Native v1 文件及权威业务状态不变。
- **P0A-31—32**：批准重放和故障注入不能再次触发导入；在权威发布指针由 v3 回滚 v1 后，旧批准失效、stage SQLite 实际删除，权威草稿 revision 仍 16、release 保留 3 份不可变历史、Live Native Chrome 仍读 v1 合同、app-b 物理数据库未变。
- **保留失败过程证据**：开发期 [Actions #44975368809](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44975368809) 触发 OS 插件 client 对未注册 `pack.install` 的本地前置拒绝，修正为使用真正 Docker Host Relay 发送未授权请求；[Actions #44975747867](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44975747867) 证明 Native 私有目录 0700 和安全 Launcher 的 `projection-*` 白名单确实阻断错误装配路径，随后采用 Native UID 检查/白名单派生 staging 名称成功。本报告不省略这些失败，也不将失败当作目标功能安全通过证据。
- **严格判定：正式 G1 仍 NOT_PASSED，冻结 W 0/24、TC 0/18 FULL PASS**。本轮可支撑“受控 Pack 预审与隔离 staging”路径，但不能伪称高权限 SSO/企业审批、Native 本地 CLI 绕过已全面封闭、B15/B17 原子签名热发布和完整 Code/Workflow/外部副作用一致性完成。下一优先 **P0-B 同实例来源签名新鲜度—原子发布—浏览器/REST 消费—故障保持旧版**。
