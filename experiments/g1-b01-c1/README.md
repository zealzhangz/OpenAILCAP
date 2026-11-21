# S1 / G1-B01 / C1 — 独立统一写入服务最小实验

> **研究性 PoC，非 Saltcorn 官方插件、非生产服务、非 G1 通过。**
> GitHub Actions 纯 Python/SQLite CI，不使用 DeepSeek Key。与冻结的 W01—W24 完整验收不是同一计分口径。

## 目标与边界

从 [统一写入契约](../../docs/01-research/30-g1-b01-unified-write-contract.md) 抽取最小 C1 实现：三类**研究测试身份**（浏览器 Session+CSRF、Agent Bearer、Plugin Bearer）通过同一 SQLite CAS 提交路径更改 app-a/field.title 的 label/status；过时提交拒绝、重放原始回执、跨进程竞争一胜一拒、事务故障回滚和绕过写入后失败关闭。

这不是原生 Saltcorn 浏览器：HTTP 的 browser_sessions 和 bearer_tokens 是测试宿主预置的 fixture 身份，没有密码登录/OIDC；Plugin Bearer 是**模拟插件客户端**，不是实际第三方插件加载/执行隔离；field.title 只是示例资源，不提供真实 UI 编辑器、workflow、runtime cache 或发布。

## 文件

- service.py：stdlib SQLite CAS/domain mutation path + HTTP ThreadingHTTPServer，绑定本机 127.0.0.1。
- test_service.py：临时文件 SQLite、HTTP Cookie/CSRF/Bearer、两个独立子进程竞争、事务注入失败、旁路直接 SQL 修改。
- run_suite.py：运行 unittest 并保存每个单测结构化结果，明确标记 not_a_g1_w01_w24_result=true。
- [CI workflow](../../.github/workflows/s1-g1-b01-c1.yml)：Ubuntu 24.04 + Python 3.13；无 Saltcorn/Chromium/LLM，无付费推理。

## 最小本地复现

在 Python 3.11+ 的终端，从项目根目录：

~~~bash
cd experiments/g1-b01-c1
python3 -m py_compile service.py test_service.py run_suite.py
python3 run_suite.py ./c1-observations.json
~~~

脚本成功退出码 0，失败非零。c1-observations.json 属于实验生成材料，由 CI Artifact 保存，不能在尚未运行时伪造为 PASS。unittest 使用 multiprocessing 的两个子进程进行 SQLite 并发竞争。

代码没有外部 Python 包依赖，**不是可直接部署互联网的服务**。身份是宿主内存映射，未实现 HTTPS/OIDC/密钥持久化、限流、生产 RBAC、插件沙箱、数据库备份、服务管理、实际缓存一致性或发布。C1 只更改单实体 JSON 的两个字段。

## 正向 / 负向行为

| 场景 | 本地 C1 设计预期 | 原 G1-B01 门槛 |
|---|---|---|
| 三类受控主体依次修改 | 一套 revision/hash/receipt/audit | W01 需要实际 Web + Agent 工具 + 插件，不因本测试通过而填 PASS |
| 过时同字段写入 | HTTP 409，资源保留 | W02 要求 Saltcorn **原生**设计器，未覆盖 |
| 独立进程竞争 | 同一 SQLite 资源只能一胜一拒 | W07 的 C1 分项，不是跨数据库证明 |
| 相同 changeId 重试 | 返回原回执，且无二次副作用 | W08 的 C1 分项 |
| SQL 中间故障 | 变更、修订和成功回执回滚 | W10 的 C1 分项 |
| 测试数据库旁路更新 | 指纹差异触发 QUARANTINED | W11 要求真正 Saltcorn Field.update 旁路，这里为 SQL 模拟 |
| 禁用模型/仅人工 | 不依赖模型 API | W22 的 C1 分项，不等于完整人工 UI |

## 安全与下一步

1. 资源 GET 亦检查漂移并可能持久隔离；没有生产监管审批与解隔离流程。
2. bootstrap_for_test 及直接 SQL 绕过只在测试中使用，公开 HTTP 不提供这些入口；数据库账号泄漏仍可绕过 C1。
3. 保留真实 [Saltcorn Web stale-form 负例](../../docs/01-research/19-real-browser-edit-evidence.md) 与 [研究网关正例](../../docs/01-research/20-governed-http-evidence.md)，不得误称本 C1 已修复原生路由。
4. 下一轮必须在 Saltcorn 原生 /field/:id、Field.update/Pack/插件的真实写入路径验证；若不能确保强制治理，则禁用自动编辑和发布。

完整 G1-B01 验收仍以 [W01—W24](../../docs/01-research/31-g1-b01-acceptance-matrix.md) 为准；本目录只提供**C1 机制级前置验证**。


## 2026-11-21：C1 CI 首次独立核查

[Run #44886944054](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44886944054) completed/success；Job 136794151797，**31/31 unittest 执行通过，零失败/零错误**；[Artifact #14699494263](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44886944054/artifacts/14699494263) 包含 JSON 观察和原始 unittest log。31 次执行来自 18 个不同测试方法定义（共享父类测试在 HttpPreflight 中再次运行），不能计为 31 个互异业务场景。PR #1 跨应用幂等键隔离测试已合并至 main。完整证据与限制见 [报告 32](../../docs/01-research/32-g1-b01-c1-real-ci-evidence.md)。没有使用 DeepSeek API。Saltcorn 原生 Web/插件仍 NOT_RUN，G1-B01 未关闭。

# S1 G1-B01 · B1：自有最小人工设计器与 C1 统一领域写入（真实浏览器验证）

> **研究原型，不是生产系统，也不是 Saltcorn 原生编辑器。** 这是对 [C2 报告](../../docs/01-research/33-g1-b01-c2-native-route-evidence.md) 所发现“修补第三方浏览器仍被 CLI 绕过”风险的一种对照替代：让自有 Web 编辑器、Agent 工具、Plugin 工具通过同一个受控 HTTP / Store.apply 写入。**B1 不测试生产插件沙箱、不调用真实 LLM。**

## 工程结构

- [service.py](service.py)：已实测的 C1 核心命令服务；额外在可信 Principal 上增加 `fields` 允许范围，让服务端（不是只在插件 manifest）执行字段级 403 授权。
- [web_editor.py](web_editor.py)：独立 localhost-only 真正 HTML 页面，实验密码登录后服务器签发随机 HttpOnly、SameSite Cookie 与 CSRF；页面通过 `GET /v1/apps/app-a/resources/field.title` 取得 revision、hash 和字段快照，并通过 `POST /v1/apps/app-a/changes` 发送精确 typed Patch。**没有另写数据库修改逻辑。** 两个浏览器标签页保留各自旧快照，409 冲突需要明确点击“重新加载”。
- [tool_client.py](tool_client.py)：受限 Agent/Plugin **确定性工具客户端**，在独立 Python 进程经 Bearer HTTP 读取并提交同构 Patch，无直接 SQL；本轮无模型调用。
- [plugin_manifest.json](plugin_manifest.json)：固定状态字段的实验 capability 宣告；服务器依该 manifest 创建 `Principal(name='status-helper', fields=('status',), resources=('field.title',))`，因此插件即使绕过自身 manifest 校验而直接发 HTTP，仍由服务端 403。
- [browser_acceptance.py](browser_acceptance.py)：真实 Chromium、密码登录、双标签页、Agent 子进程、Plugin 子进程、双工具子进程争抢同一 revision、独立只读 SQLite、跨应用隔离与撤销测试。
- [原始 C1 回归测试](test_service.py)：复跑原有独立 CAS/SQL/HTTP 机制；本轮不得降低通过标准。
- [Actions Workflow](../../.github/workflows/s1-g1-b01-b1.yml)：固定 Ubuntu 24.04、Python 3.13、Playwright 1.56/Chromium。无需 Saltcorn、DeepSeek、外部模型 API；Artifact 内保留逐条观察但不保存 Cookie、Token 或密码。

## 本地复现

在一次性隔离的 Linux 环境，安装 Python 3.13 + Playwright 1.56 及 Chromium：

~~~bash
python3 -m pip install 'playwright==1.56.0'
python3 -m playwright install --with-deps chromium
python3 -m py_compile experiments/g1-b01-c1/*.py
cd experiments/g1-b01-c1
python3 run_suite.py /tmp/s1-b1-c1-regression.json
python3 browser_acceptance.py --output /tmp/s1-b1-browser-agent-plugin.json
~~~

自动化脚本只在本地监听 `127.0.0.1`，创建一次性数据库及随机账号，执行完自动停止服务并清理数据库。脚本自动启动真实 Chromium 执行界面；无需手工设置密码，也**无需 DeepSeek Key**。不要将 `serve_b1` 服务暴露到公网。

## 预期安全证明（由真正 CI 结果决定是否 PASS）

浏览器真实会话 → B 保存 → A 用旧页面保存返回 409 → Agent 进程经 typed HTTP 修改 → B 旧页面 409 → A 显式刷新继续保存 → Plugin 进程修改状态 → 插件越权改 label 被服务端拒绝 → Agent 旧快照 409 → Agent/Plugin 两个 OS 子进程同 revision 争抢一胜一拒 → 物理 SQL 审计/回执/资源版本与最新浏览器 DOM 一致。负例拒绝用 403/409 等实际 HTTP 判断，不能把 200 HTML 登录重定向误认为成功。

**关键限制**：Web UI 是 OpenAILCAP 自研两字段研究表单，没有低代码页面 Schema 设计能力；“Agent”是确定性 typed tool 进程，不是自主规划 LLM；“Plugin”是带 manifest 的受限进程，没有运行时沙箱、数字签名、供应链约束和代码执行隔离；所有身份只用于 localhost 测试，不是生产 SSO/RBAC。C1 SQLite 存储仍可被数据库管理员直接改动，不能据此宣称全路径不可绕过。

冻结 [W01—W24](../../docs/01-research/31-g1-b01-acceptance-matrix.md) 与合同 TC01—TC18 原标准不变；任何完整 PASS 的认定必须由相应平台级验收独立决定。**G1 仍 NOT_PASSED**。
