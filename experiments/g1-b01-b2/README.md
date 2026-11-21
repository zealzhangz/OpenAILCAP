# S1 B2：Domain Schema → Form → View → Workflow → Manifest 可运行原型

**实验性质**：独立研究原型，不是正式 OpenAILCAP 平台，也不是 AI 自主生成应用。本轮测试人工 JSON 编辑器、独立 Agent HTTP 工具、模型引用闭包、业务运行和发布快照，**不调用 DeepSeek 或其他模型 API**。

## 组成

- schema_core.py：受限类型的 DataModel/Form/View/Workflow、资源 revision/hash、全应用 Manifest/hash、统一 command/CAS、权限、幂等 Receipt、审计、引用校验、SQLite 事务、不可变发布及指针回滚。
- schema_http.py：真实 HTML Schema 编辑器 + 测试 Session/Cookie/CSRF；与独立 Agent 都通过相同 /v2/apps/{app}/commands 提交；运行态表单、视图与工作流 API。
- tool_client.py：独立 Python 子进程运行的确定性 Agent typed-tool，凭测试宿主签发的 Bearer 请求，禁止直接修改数据库。
- contract_spec.json：合同 DataModel（contract_no/title/amount_minor/status）、Form、View 和金额阈值二级审批 Workflow。
- test_schema.py：数据库层图引用、权限、幂等、冲突、事务回滚、发布、迁移门禁和漂移隔离检查。
- browser_acceptance.py：真实 Chromium 人工与 Agent 交替编辑、发布版运行、二级审批、发布回滚及物理 SQL oracle。
- GitHub Actions：.github/workflows/s1-b2-schema-runtime.yml（ubuntu-24.04、Python 3.13、Playwright 1.56/Chromium，无模型调用）。

## 本地执行

安装 Python 3.13、Playwright 1.56 和 Chromium 后，在项目根目录：

1. python3 -m py_compile experiments/g1-b01-b2/*.py
2. cd experiments/g1-b01-b2
3. python3 -m unittest -v test_schema
4. python3 browser_acceptance.py --output /tmp/s1-b2-browser.json

安装浏览器依赖：python3 -m pip install playwright==1.56.0；python3 -m playwright install --with-deps chromium。脚本在本机临时端口运行，数据库和身份凭据临时生成并清理，严禁在生产环境运行或公开监听。

## 运行范围

- **模型**：强类型 string/integer（金额单位整数分），固定字段属性；表单校验必填/类型并真正写入 SQLite。
- **视图**：引用模型字段，读取发布版本并渲染真实业务记录；人工和 Agent 交替改草稿不会静默改变生产版。
- **流程**：Draft→PendingLevel1→(PendingLevel2 或 Approved)→Approved；金额大于 100000000 分进入二级，等于阈值直接一级通过；记录版本竞争拒绝。
- **Manifest**：全部草稿资源的内容 hash 和应用级 revision，单 SQLite 事务统一提交；模型字段删改如果影响引用/既有数据则拒绝。
- **发布/回滚**：仅授权人工发布当前有效资源图，保存不可变 release manifest；可把发布指针回滚至历史版本，但不假称撤销已发生的外部业务动作。
- **失败关闭**：直接 SQL 修改草稿而不修改 hash 后隔离草稿，拒绝后续变更与发布；最后已验证发布快照仍可用于业务读取。

## 明确未覆盖

没有真实 LLM 自主开发、自动生成代码、插件沙箱、可视化拖拽、组织 RBAC、外部生产部署、多数据库分布式事务或数据库管理员旁路隔离。它是 S1 阶段 **Domain Schema + Manifest 候选方案的限定验证**，不能作为 G1 全部通过的依据。原正式冻结 W01—W24 和 TC01—TC18 不因本原型自动更新。
