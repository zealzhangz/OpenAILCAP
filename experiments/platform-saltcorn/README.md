# S1：Saltcorn 真实运行时参考验证

本研究在 README 第一阶段原有四个平台之外增加 Saltcorn（MIT）作为第五个轻量级参考对象，目的是取得可运行的低代码表/字段/视图/REST 的可复现证据，而非直接选择最终平台内核。

- 上游源码固定版本：https://github.com/saltcorn/saltcorn/tree/515254bee5a98df70530cc59846b1df02d5db350
- CLI package.json 版本 1.7.0-beta.5，MIT 许可。
- 原始来源：[fixtures.ts](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/saltcorn-data/db/fixtures.ts)、[表模型](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/saltcorn-data/models/table.ts)、[HTTP API 测试](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/server/tests/api.test.js)、[视图测试](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/server/tests/view.test.js)。
- [CI 工作流](../../.github/workflows/s1-saltcorn-runtime.yml)：在隔离 Runner 安装 Saltcorn、真实创建 SQLite、加载上游 fixtures、启动实际 HTTP 服务。
- [独立验证脚本](smoke.py) 从 SQLite 系统表和 Saltcorn REST/HTML 路由读取，不凭 CLI“成功”文字判断功能可用。

## 七项明确验收

| ID | 必须通过的真实操作 |
|---|---|
| SC01 | SQLite 有 Saltcorn _sc_tables、_sc_fields、_sc_views |
| SC02 | 真实表模型记录 books/patients |
| SC03 | books 的 author 字段实际存在 |
| SC04 | authorlist 视图实际登记 |
| SC05 | /api/books/ 返回真实测试行 |
| SC06 | /view/authorlist 渲染包含 Tolstoy 的 HTML |
| SC07 | 未认证访问 /api/patients/ 返回 HTTP 401 |

**限制**：使用上游自带示例数据而非 OpenAILCAP 合同管理业务。即使七项全部通过，也只证明第三方低代码平台的真实基本运行时可以启动、持久化元数据、渲染视图并暴露 API，不能将 README 的合同 TC01—TC18 标记为通过。没有 AI/人工交错修改，也没有插件/部署/回滚。

## 本地复现

要求 Node.js 24、Python 3.13、可以访问公开 npm 仓库。请使用全新的临时数据库；reset-schema 删除已有数据库内容，不得在生产使用。

~~~bash
export SQLITE_FILEPATH=/tmp/s1-saltcorn.sqlite
export SALTCORN_SESSION_SECRET="$(openssl rand -hex 32)"
npm install -g @saltcorn/cli@1.7.0-beta.5
saltcorn reset-schema -f
saltcorn fixtures
saltcorn serve --port 3100 --noscheduler &
python3 experiments/platform-saltcorn/smoke.py --db "$SQLITE_FILEPATH" --output /tmp/s1-saltcorn-results.json
~~~

CI 只上传不含密钥或数据库文件的结构化结果。若安装失败，应保留真实 GitHub Actions 错误并标注阻断，而非夸大成平台能力缺失。

## 第二组：原生合同 Pack 真实平台验证（2026-11-21）

- [原生合同配置 contract-pack.json](contract-pack.json) 含 s1_contracts / s1_approvals（Key 指向 s1_contracts）和 s1_contract_list 视图。
- [原生 Table API 测试数据初始化脚本](seed-contract.js)：调用 Saltcorn CLI run-js，将 1000000.01 CNY 转为整数分 100000001 写入平台数据库。
- [独立验证 contract_verify.py](contract_verify.py)：检查实际 SQL、元数据、REST、HTML 和匿名审批数据读取拒绝。
- [GitHub Actions 工作流](../../.github/workflows/s1-saltcorn-contract.yml) 与 [运行 #44869926796](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44869926796)，全部 **9/9 PASS**。
- [研究报告](../../docs/01-research/15-native-contract-platform-evidence.md) 详细说明 9 个业务/技术断言与每一处证据。

本次不实现预注册 decimal(12,2) 类型、不执行真实审批和 AI/人工交替编辑。因此它是**真实第三方平台配置 + 数据 + 运行态的部分纵向切片**，不等于正式合同 TC 通过，更不等于 G1/G3 通过。 

## S1 实际资源多轮编辑试验

新增 [roundtrip/](roundtrip/README.md) 三阶段真实平台编辑实验，GitHub [Actions #44871169761](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44871169761)，18 次断言符合预注册预期。B 阶段**实测旧完整 Pack 会把人工/其他程序保存的无关字段标签改回旧值**，属于已识别的不安全集成路径。A 阶段验证局部字段修改的串行保留；C 阶段验证非原子前置冲突检查，不等于并发 CAS。测试全部通过不意味着人机协作产品通过；没有真实 AI Agent 或浏览器设计器会话。见 [研究报告](../../docs/01-research/16-saltcorn-roundtrip-evidence.md)。

## 真实 SQLite 事务语义、双进程并发与绕过版本账本负例

新增 [atomic/](atomic/README.md) 研究，Run [#44872093657](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44872093657) 成功执行。TX1 真实验证 Saltcorn SQLite withTransaction 的异常后写入不回滚；TX2/TX3 由两个独立 CLI 进程通过显式 SQLite BEGIN IMMEDIATE 和研究用 CAS 表实现本场景不同字段合并、同字段冲突拒绝；TX4 中途失败回滚；TX5 绕过版本表的人工原生字段修改又被 Agent CAS 错误覆盖；TX6 实际 HTTP 读回。**两项危险反例成功复现**，并非安全验收通过；尚无真实人工浏览器/LLM Agent，G1 未通过。

## 2026-11-21 真实浏览器字段编辑实测

新增 [browser/](browser/README.md) Playwright + Chromium 实验，GitHub [Actions Run #44873882208](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44873882208) 成功，9/9 实际人工 Web 字段向导与 5/5 后置模拟 Agent 检查符合预注册预期。**危险反例**：同一字段 B 页面先保存，A 旧页面后提交将 B 标签覆盖；随后基于独立旧版本账本的模拟 Agent 再次覆盖人工结果。真实登录/CSRF/匿名拒绝均有一手日志。Agent 是 CLI 确定性脚本，不是真正 LLM。CI 初次因 Ubuntu 26.04 与 Playwright 不兼容失败，改固定 Ubuntu 24.04 后通过。G1 未通过。

## 2026-11-21 真实 SQLite 的共享 HTTP 编辑协议正向研究

新增 [governed/](governed/README.md)，[CI #44874668928](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44874668928) completed/success，主流程 22/22、原生绕过漂移检测 4/4。研究网关自带的 Chromium HTML 页面和模拟 Agent Bearer HTTP 客户端共用真实 Saltcorn SQLite 的事务/版本/指纹/幂等/审计，旧页面 409、Agent 旧上下文 409、并发一胜一拒，失败可回滚。Saltcorn 原生 Field.update 绕过后，网关用指纹发现未登记变更并失败关闭。**研究页不是 Saltcorn 自带 /field 编辑器，Agent 不是真实 LLM；实验 direct SQL 内表更新不用于生产，G1 未通过。** 详见 [报告 20](../../docs/01-research/20-governed-http-evidence.md)。
