# S1 Saltcorn 真实 Web 编辑器：登录/CSRF/两标签页/Agent 版本漂移

此工程是第一阶段 H01/H03 核心风险的浏览器级实验。与此前 CLI 模拟人工操作不同，**使用 Playwright + 真实 Chromium，运行真实 Saltcorn Web 服务，登录真实研究管理员，直接操作字段编辑向导的 DOM 输入和提交按钮**，最后独立从 Saltcorn SQLite 读取结果。

## 冻结的原始证据路径

- Saltcorn 上游固定研究源码：`515254bee5a98df70530cc59846b1df02d5db350`；实际被测 CLI 发布包：`@saltcorn/cli@1.7.0-beta.5`。
- [浏览器脚本](browser_roundtrip.py) 不会修改数据库，它仅从 SQLite **只读**观测结果，用户修改只通过真实 Web DOM 和 CSRF 表单提交。
- [建立外部研究版本账本](create-ledger.js)、[模拟的 Agent CLI 写入](agent-sidecar.js)、[独立后置验证](verify_agent.py) 均不是 Saltcorn 官方 Agent 或生产级 HTTP API。
- [GitHub Actions 工作流](../../../.github/workflows/s1-saltcorn-browser.yml) 每次自动创建一次性数据库、一次性管理员密码与真实浏览器，不使用外部账号。

## 预注册验收

| ID | 必须从真实执行观察的结果 | 风险解释 |
|---|---|---|
| UI01 | Saltcorn 物理数据库最初 title.label=Title | 固定起点 |
| UI02 | 真实 Chromium 完成管理员登录，能打开 /field/:id | 鉴权及真实界面入口 |
| UI03 | 编辑表单具有 contextEnc 和 _csrf 等表单字段 | 正常浏览器提交保护 |
| UI04 | 两标签页 A/B 同时加载旧 title.label=Title | 确认存在持旧编辑页 |
| UI05 | B 在真实 DOM 输入新标题，完成向导提交，数据库 title.label=Browser B Saved | **真实人工 Web 写入** |
| UI06 | A 继续提交过时表单，数据库变成 Browser A Stale Save | **若观察到，代表浏览器本身的静默丢更新负例** |
| UI07 | 新标签页重新打开字段向导，展示数据库中的最新 title.label | 真实运行态重新读取 |
| UI08 | 未登录访问同一字段编辑页面无法进入，跳转 /auth/login | 一个真实授权拒绝行为（不能等同多租户安全） |
| UI09 | 两次 Web POST 均由浏览器正常提交（包含 contextEnc、CSRF） | 保留正常路由证据 |
| U10—U13 | 因浏览器写入没有递增外部版本表，模拟 Agent 以旧 revision=0 判断成功并覆盖浏览器修改，合同 API/页面仍可用 | **负例：只给 Agent 接 CAS 不够，Web 编辑器也必须接入同一版本治理** |

## 重要限制

- 真实浏览器登录、保存行为不等于所有 Saltcorn UI/浏览器都有相同问题。本实验只限定这条字段编辑路由。
- B/A 同时**打开页面**，但按顺序提交，属于真实两标签页持旧页面的交错编辑，不是网络/线程同时写入竞争；后者已在 [atomic 实验](../atomic/README.md) 中通过独立 CLI 进程验证。
- 如果 UI06 实际出现静默覆盖，工作流通过表示**危险负例成功复现**，不表示功能安全。
- Agent 在 U10—U13 由确定性 CLI 脚本模拟，没有大模型、Agent 授权或工具规划，也没有完整生产级认证/审计/版本发布。
- 所有管理员密码、会话密钥仅在 GitHub Runner 内生成；日志不得记录敏感值；Artifact 只保存简化的路径、状态及测试断言，不保存 session cookie、CSRF token 或完整浏览器 DOM。
- 任何失败均须按真实 GitHub Actions 日志归因，不得伪造通过报告。完整合同 TC01—TC18 仍未完成，G1 仍未通过。

## 本地运行

需要 Node.js 24、Python 3.13、Saltcorn CLI 1.7.0-beta.5、Python playwright 1.56.0 及其 Chromium 浏览器。**只使用全新测试数据库**；reset-schema 会删除原数据。

~~~bash
export SQLITE_FILEPATH=/tmp/s1-browser-saltcorn.sqlite
export SALTCORN_SESSION_SECRET="$(openssl rand -hex 32)"
export S1_ADMIN_PASSWORD="$(openssl rand -hex 28)"
saltcorn reset-schema -f
saltcorn install-pack -f experiments/platform-saltcorn/contract-pack.json
saltcorn run-js -f experiments/platform-saltcorn/seed-contract.js
saltcorn run-js -f experiments/platform-saltcorn/browser/create-ledger.js
saltcorn create-user --admin --email s1-research-admin@example.invalid --password "$S1_ADMIN_PASSWORD"
saltcorn serve --port 3100 --noscheduler &
python3 experiments/platform-saltcorn/browser/browser_roundtrip.py --db "$SQLITE_FILEPATH" --output /tmp/s1-browser-ui-result.json
saltcorn run-js -f experiments/platform-saltcorn/browser/agent-sidecar.js
python3 experiments/platform-saltcorn/browser/verify_agent.py --db "$SQLITE_FILEPATH" --output /tmp/s1-browser-agent-result.json
~~~
