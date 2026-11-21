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
