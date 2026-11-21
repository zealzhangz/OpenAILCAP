# S1 实测：第一次成功运行真实第三方低代码平台（Saltcorn）

**实测日期**：2026-11-21。证据等级 S0（真实 Saltcorn 服务启动、真实数据库读取、真实 HTTP API/HTML 运行结果）；合同应用任务状态另行报告。

## 一、为何补充 Saltcorn

README 1.1 以 ToolJet、NocoBase、Appsmith、Budibase 为核心，允许补充少量具独特架构价值的项目。此前 NocoBase v3 官方创建器在下载默认模板时受到第三方包仓库 E530 阻断；ToolJet 的 Code Mode EE 实现存在源码不可见边界。Saltcorn 提供 MIT 许可的自托管 SQLite + Node 低代码引擎和可公开阅读的表/字段/视图、HTTP 路由实现，适合**研究真实低代码配置存储与运行态**。此项补充不替代对既定四平台的调研，也不表示将 Saltcorn fork 为 OpenAILCAP。

## 二、可复现版本和真实执行

| 参数 | 证据 |
|---|---|
| 上游源码 | [Saltcorn @ 515254bee5a98df70530cc59846b1df02d5db350](https://github.com/saltcorn/saltcorn/tree/515254bee5a98df70530cc59846b1df02d5db350) |
| 核心许可 | [上游仓库 LICENSE（MIT）](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/LICENSE)，另应逐包核查后才能商用集成 |
| CLI 版本 | 1.7.0-beta.5；CLI 输出 @saltcorn/cli/1.7.0-beta.5 linux-x64 node-v24.22.3 |
| 验证方式 | GitHub-hosted Ubuntu Runner；Node 24.22.3；内置 SQLite |
| 运行提交 | [f0c2947c4744a65e14d10d9e85073610d7d57ee9](https://github.com/zealzhangz/OpenAILCAP/commit/f0c2947c4744a65e14d10d9e85073610d7d57ee9) |
| CI | [Actions Run #44869777036](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44869777036) — completed / success |
| Artifact | GitHub Actions artifact ID 14693426822，名称 s1-saltcorn-real-platform-result |
| 自动化脚本 | [真正的数据库与 HTTP 验证](../../experiments/platform-saltcorn/smoke.py)，[可重跑 Workflow](../../.github/workflows/s1-saltcorn-runtime.yml) |

重要：实际 npm 依赖包版本由 @saltcorn/cli@1.7.0-beta.5 的发布版本及依赖解析决定；这次记录的是本次 CI 真正安装并输出的 CLI 版本，不自动等同固定源码 commit 的每个发布工件字节。未来产品依赖评价需进一步锁定 npm 包 integrity / 完整构建。

## 三、七项真实第三方平台验证

| 测试 | 真实观察结果 | 状态 |
|---|---|---|
| SC01 | SQLite 中存在 _sc_tables、_sc_fields、_sc_views | PASS |
| SC02 | 系统元数据登记 books、patients 表 | PASS |
| SC03 | books 元数据包含 author 字段 | PASS |
| SC04 | 系统元数据登记 authorlist 视图 | PASS |
| SC05 | 对 /api/books/ 的实际 HTTP GET 返回 200，并包含 Herman Melville fixture 行 | PASS |
| SC06 | 对 /view/authorlist 的实际 HTTP GET 返回 200，已渲染 HTML 包含 Tolstoy | PASS |
| SC07 | 未认证访问 /api/patients/ 实际返回 HTTP 401 | PASS |

证据不是本研究生成的“模拟平台”，而是实际下载官方 Saltcorn CLI、执行 reset-schema、fixtures、serve 后使用独立 Python 程序直连 SQLite 和本机端口进行检查。完整每条测试 JSON 位于运行 Artifact；CI job 日志逐条打印 SC01—SC07 PASS。

## 四、源码链路：从元数据到运行时

下面每一节点都能对应到真正上游源文件（上游 commit 固定），但是本次只直接运行了平台的 schema+fixture/REST/view 组合，**没有利用断点跟踪器逐函数证明下表所有调用发生的先后次序**。

~~~mermaid
flowchart LR
    A[Saltcorn CLI reset-schema/fixtures] --> B[Table.create/Field.create/View.create]
    B --> C[(SQLite _sc_tables/_sc_fields/_sc_views 和业务表)]
    C --> D[Saltcorn serve 加载模型]
    D --> E[HTTP REST /api/books]
    D --> F[HTTP 视图 /view/authorlist]
    E --> G[独立 Python 验收: HTTP 200 + 数据]
    F --> H[独立 Python 验收: HTML 页面]
~~~

- [CLI reset-schema](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/saltcorn-cli/src/commands/reset-schema.js) 和 [serve](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/saltcorn-cli/src/commands/serve.js)：真实执行入口。
- [上游官方 Fixtures](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/saltcorn-data/db/fixtures.ts)：Table.create、Field.create、View.create 的原生配置路径。
- [Table 模型](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/saltcorn-data/models/table.ts) 与 [Field 模型](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/saltcorn-data/models/field.ts)：包含元数据及实际表结构操作。
- [Saltcorn server API tests](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/server/tests/api.test.js)：公开数据、私有数据的请求预期。
- [Saltcorn server view tests](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/server/tests/view.test.js)：视图渲染预期。

**架构研究价值**：实际运行再次确认“模型元数据 → 真实数据库资源 → 运行态 API 和 UI”的链可由一套低资源开源平台完成，支持 OpenAILCAP 优先研究稳定领域命令/Schema，而不必马上创造完整低代码引擎。AI/人工协同编辑仍必须在独立版本和命令契约下验证。

## 五、明确未完成

- 当前 7 项 SC 检查来自 **Saltcorn 上游 fixture**，不是 OpenAILCAP 合同管理真实业务，README 的合同 TC01—TC18 均不得因此标 PASS。
- 没有运行任何 LLM、开发 Agent、插件能力发现、人机交替编辑、代码自动部署或生产级攻击验证。
- SC07 的 HTTP 401 仅证明一个实际未登录拒绝行为，不等于多角色/多租户安全合格。
- SQLite 是一份本机实验数据库，不能等同生产 HA/大规模数据隔离。

## 六、后续动作和 G1 判断

采用平台**原生 Pack**（不是直接插入元数据表）建立合同与审批主外键资源，实测真实渲染，并保留 Decimal 类型差异、金额审批引擎未实现、Agent 不具备真实能力发现等证据。随后回到 README 规定的四平台做双向编辑真实对照。

**中期结论**：真实第三方低代码平台已成功运行 **1 套**，这推进了 S1 的真实运行证据，但 G1 仍不通过：同一合同场景的工作流、人机双向编辑和 AI 能力边界尚未形成足够的原始实证。
