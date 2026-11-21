# S1 B9｜**唯一权威 Domain Kernel + 真实 Saltcorn 可删派生运行副本**

> **实验性架构候选；不是生产级 Saltcorn 插件，不是完整低代码运行引擎。** 与 B8 不同，本轮两个 SQLite 文件/目录及 Linux UID 真正分离：B2 可信 Domain Kernel 的 **已发布 Release** 是唯一应用定义来源，Saltcorn 只能收到从经验证 Release 编译而来的有限 **Pack 投影**，它的 Native Web/CLI/Pack 任意修改不得回写权威数据库。

## 一、直接检验的假设

1. **H9.1**：可信 B2 Kernel 以不同真实非 root Linux UID 运行，独占 mode-0700 的权威 SQLite 与 mode-0600 配置；Saltcorn Runtime UID 具有自己独立的数据库，不能以 SQLite O_RDONLY/O_RDWR/SQL UPDATE 打开权威数据库，也未获任何 Kernel Bearer。
2. **H9.2**：可信 Publisher 只能从可信 B5 `release.read` 拉取**已发布** Manifest，严格验证 Manifest hash、Resource Schema 和依赖闭包；只投影 **Model + View** 到 Saltcorn 官方 `install-pack` 可接受的表和视图配置，其他 Code、Workflow、Form **明确不投影**，避免假装业务审批语义等价。
3. **H9.3**：真正 Saltcorn `reset-schema / install-pack / run-js / serve`、Chrome 原生 `/view/s1_contract_list` 和 `/field/:id`，运行于派生数据库所有者 UID，可显示业务记录；危险原生网页编辑/CLI `Field.update` **只写派生库**，无权威侧版本、资源、发布指针、审计或回执更改。
4. **H9.4**：污染可删：按同一已验证 v1 Release 再生成新 Saltcorn 原生 SQLite，原生字段/视图恢复一致、Pack SHA 完全一致；把被攻击的旧数据库实际删除不破坏权威。
5. **H9.5**：可信 B2 应用编辑、真实人工 Chromium 发布 v1→v2、Native View 列配置真实变化；由可信 Publisher 根据 expectedPublishedVersion 执行 B2 **v2→v1 回滚**，重建 Saltcorn v1 并用真实浏览器读回；旧发布版本仍不可变，跨 App B 不受影响。

## 二、具体最小可信边界

~~~text
可信 Linux UID: ailcapb9kern
  私有目录 /authority-private/ (0700)
    authority.sqlite (0600)  ← 唯一权威
    kernel-config.json (0600)
  B2 Domain Schema + 不可变 Releases + 审计 / 收据
  B5 Tool Broker + B2 人工浏览器会话
     │
     │ 可信 Publisher 从 v3 release.read 获取 RELEASE
     │ sha(definitions) 必须等于 release.manifestHash
     │ 只编译白名单 model.contracts / view.contracts
     ▼
  [严格确定性 Saltcorn Pack 编译器]
     │
     │ projectionPackHash（只用于研究重建一致性）
     │ 明确排除 Form / Workflow / B4 Code
     ▼
低权限 Linux UID: ailcapb9run
  /runtime-private/projection-v1.sqlite (0700 dir, 0600 db)
  Saltcorn 官方 install-pack / run-js / serve
  原生 /view、/field/:id、Native CLI / Pack
     │
     └─ 允许污染自有副本，但**不能直写/逆向同步权威 DB**
~~~

此实验将 Native Saltcorn 明确定位为**可派生的 Model/View 展示副本**，而不是当前可安全复用的企业全功能执行引擎。B2 Workflow 和 Form 的业务逻辑不应映射成看似相同但不执行审批的 Saltcorn 触发器；原始固定 Pack 中额外 `s1_approvals` 表特意不输出。

## 三、测试范围与真实组件

- GitHub CI Ubuntu **24.04** / Node **24** / 官方 `@saltcorn/cli@1.7.0-beta.5` / Python **3.13** / Playwright **1.56** + Chromium；
- 真实非 root Kernel 用户 **ailcapb9kern**、Saltcorn 派生副本用户 **ailcapb9run**；
- `kernel_service.py`：独立 Linux 进程，真实 B2 SchemaStore + B4 ExtensionRegistry（**不授权 Kernel 执行 Docker 构建**）+ B5 v3 Broker，人工 Web Session/CSRF；
- `projector.py`：可信控制器唯一可调用的**严格部分投影**；从实际 `release.read` 获取 Manifest、校验 sha 与引用、从固定 Saltcorn Pack 样板生成仅一个 `s1_contracts` Model 和一张 `s1_contract_list` View；拒绝任意隐藏插件/触发器插入和反向同步；
- `native_env_launcher.py`：经 sudo/runuser 切换 Runtime UID 后从 stdin 接收正式 Saltcorn CLI 所需的临时环境，且仅允许运行 `/tmp/s1-b9-derive-.../runtime-private/projection-*.sqlite`；**不是生产安全沙箱**；
- `native_oracle.py`：与 Projector 完全分离的真实 SQLite `_sc_fields`、`_sc_views.configuration` 与 `s1_contracts` 物理只读 Oracle；
- `experiment.py`：真实 Linux UIDs、B2/B5+Chromium、实际 Saltcorn Native Pack/浏览器、原生污染隔离、重建、版本变化、**真正 B2 rollback pointer**；
- `test_projector.py`：白名单、Semantic References、原始 Manifest/Pack SHA、源码污染和不支持的工作流能力拒绝等单测；
- `.github/workflows/s1-b9-authority-projection.yml`：完整真实 CI。**0 DeepSeek 调用**。

## 四、分阶段实证步骤

研究只使用一次性 SQLite、临时随机密码。CI 内执行的危险 Saltcorn 命令会**重置数据库**；不得把这份实验直接指向生产环境。

1. 专用 Kernel UID 真实建立两个 App，Agent 经 v3 Metadata Tool 将 Model/Form/View/Workflow 四个 typed Schema 写入 app-a；人类模拟登录 Chrome 真实发布 v1。独立 SQL 记录 Kernel schema/release hash、Audit 与 receipt。
2. 通过 `release.read` 取得 v1，Compiler 验证 SHA/引用闭包、只投影 Model+View 成 Saltcorn JSON Pack；**真正 Saltcorn CLI** 使用独立 SQLite `reset-schema`、`install-pack`、`run-js` 插入合同并以 Chrome 原生网页查看。真实 View 列配置与 v1 `view.contracts.columns` 对应。
3. Runtime 直接打开 Authority SQLite、执行 SQL UPDATE 均 DENIED；Runtime 对 B5 Kernel 没有 Token，未经授权请求和跨 App 请求 401/403。
4. 真 Chrome Saltcorn `/field/:id` 修改派生字段标签成功，真实 Native `saltcorn run-js Field.update` 再修改成功，甚至再次执行 Native Pack；这些行为**只能污染派生 SQLite**。独立 Kernel SQL 读取实际 Manifest/Release/Audit/Receipts，与攻击前逐字段相同。
5. 删掉污染的 Saltcorn 数据库，用相同已发布 Manifest 再执行 Saltcorn reset/install/seed；原生字段标签恢复，真实 View 配置与编译输出恢复，Pack SHA 完全相同。
6. Agent 修改合法 B2 View.columns，人工 Chrome 发布 **v2**；全新 Saltcorn Runtime 数据库真实 View.columns 增加 `title`，Native Web 展示真实合同。
7. 可信 Publisher v3 `app.rollback(expectedPublishedVersion=2,targetVersion=1)`，B2 release.read 恢复旧 verified v1，重新物化 Saltcorn v1 并以 Native Chrome 读取；前一 v2 不变、旧版本回滚 CAS 409、App B 和内核审计隔离。

## 五、重要未覆盖范围

- **不支持将真实 B2 Form、Workflow、阈值审批或 B4 自定义代码“翻译”为 Saltcorn 等价运行逻辑**。本轮仅保证基础 Model+View 的投影，并**不能保证软件应用业务功能的完整语义**。
- Saltcorn 数据库中合同记录由原生测试脚本在派生数据库插入，本轮并未实现和验收双向业务数据迁移、主数据同步、幂等消息与权限过滤、生产订单事务一致性。
- 版本切换采用隔离环境的**顺序停止旧 Runtime、建立/检查新 Runtime、再启动浏览器观察**，没有生产流量入口、负载均衡、蓝绿自动路由/无损迁移、并发请求排空或零宕机发布；不能把这次 B2 发布指针回滚冒充生产全域部署/外部副作用 W24 通过。
- Runtime 可读它自己的派生 SQLite，但不等于“所有非受控代码都被沙箱隔离”，Linux root 和受信管理员仍有高权限。Saltcorn Native Web/Pack 仍可自由修改**可删副本**，需进一步验证插件供应链、浏览器/多租户权限、缓存生命周期、数据脱敏。
- 只验证**App A 的 Saltcorn 投影**与 **App B 的权威数据完全未变**，不代表两个应用已经独立部署、同名实体权限隔离都在 Saltcorn 里验过。
- Manifest SHA 与 Pack SHA 是内容完整性验证，并不提供发布者的数字签名、远端分发不可抵赖能力或供应链防篡改认证；上游工具链需要真实可信签名策略。
- B9 的任何局部 PASS 不能替代冻结 W01—W24 FULL PASS、TC01—TC18 FULL PASS，也不意味着 G1/B01 已关闭。

下一步如果 B9 受限验证通过，将与 B8 的原生旁路对照一起比较“成熟平台做**权威内核**”和“成熟平台做**可删派生前端/运行组件**”的维护成本，优先扩展跨版本数据迁移、真实业务运行语义与自动发布切换，再评估正式 G1。
