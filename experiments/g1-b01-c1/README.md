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
