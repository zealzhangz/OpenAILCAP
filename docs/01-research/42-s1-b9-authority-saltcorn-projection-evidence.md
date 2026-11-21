# S1 研究报告 42：B9 可信 Domain Kernel + 真实 Saltcorn 可删派生投影

**研究日期：2026-11-21。限定实验结论：36/36 PASS；G1 NOT_PASSED，G1-B01 OPEN。**

## 一、为什么要做 B9

此前 [报告 41：B8](41-s1-b8-real-saltcorn-native-write-path-evidence.md) 已使用真实 Saltcorn 1.7.0-beta.5、原生网页字段编辑向导和 Native CLI Field.update 证明：如果 Saltcorn 与权威 SQLite 共享 Linux UID，外围 Gateway 即使有 revision、CAS、Receipt 和审计，仍无法阻止 Saltcorn 原生写入直接修改权威数据。409 漂移检测只能事后拒绝其他操作。

本轮采用与 B8 完全不同的数据授权边界：**仅 B2 Domain Kernel 拥有权威 SQLite；从真正已发布的 B2 Release 严格生成 Saltcorn Model/View Pack，Saltcorn 只运行在另一 Linux 用户拥有的独立、可删 SQLite 副本上。** Saltcorn Native Web、CLI 和 Pack 可以修改副本，但副本不能反向修改权威 Schema、Manifest、Release 和 Audit。

这不是把 Saltcorn 变成生产级完整低代码内核，而是验证其能否作为可信 Kernel 的**有限 Model/View 派生展示组件**。

## 二、一手可复现材料

| 项目 | 确认的结果或链接 |
|---|---|
| B9 工程 | [源码与复现说明](../../experiments/g1-b01-b9/README.md) |
| GitHub PR | [PR #11](https://github.com/zealzhangz/OpenAILCAP/pull/11)，已合并 main |
| main 合并 SHA | [aeca8cdd126c58023de77451a5abd3cc6b776e0a](https://github.com/zealzhangz/OpenAILCAP/commit/aeca8cdd126c58023de77451a5abd3cc6b776e0a) |
| GitHub Workflow | [.github/workflows/s1-b9-authority-projection.yml](../../.github/workflows/s1-b9-authority-projection.yml) |
| **最终真实 CI** | [Actions #44904386856](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44904386856)，**completed/success** |
| CI Job | **136846739065** |
| 原始证据 | [Artifact #14707840201](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44904386856/artifacts/14707840201)，含结构化 JSON、真实 E2E 与回归日志 |
| B9 严格投影编译器单测 | **25/25 PASS** |
| B2 Domain Schema/SQLite 回归 | **18/18 PASS** |
| B5 IR 与 Tool Broker 回归 | **40/40 PASS** |
| B9 真实 Linux UID + Chromium + Saltcorn CLI/Pack/SQLite E2E | **36/36 PASS** |
| DeepSeek/其他大模型调用 | **0 次** |

**失败过程也保留**：[CI #44903561121](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44903561121) 发现控制器先把 0700 目录交给内核 UID 后无法再写配置；已改为**先写配置、再移交独占权限**，不放宽 DB 权限。[CI #44903688768](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44903688768) 发现“无 Token”测试工具错误拼接空 Bearer；已改为真正不发送 Authorization。[CI #44903845397](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44903845397) 和 [CI #44904104659](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44904104659) 对 Saltcorn Serve 的启动路径暴露未复制的脚本引用；已添加脱敏日志并统一为 B9 自己的 Native Launcher。**上述失败不能作为完整验证成功，最终以 #44904386856 为准。**

## 三、实际运行的架构

- **权威内核：** 真正 Linux UID **999**，数据库与启动密钥位于独占 0700 目录、0600 文件；真实 B2 SchemaStore + 不可变 Releases + B5 Tool Broker + 人工 Chromium 登录/CSRF。
- **派生运行时：** 真正 Linux UID **997**，拥有自己的 0700 目录和独立 SQLite。实际官方 Saltcorn CLI 1.7.0-beta.5 执行 reset-schema、install-pack、run-js、create-user、serve；数据来自可再生 Pack 和测试合同。
- **严格单向编译：** Publisher 通过真实 B5 release.read 获取 v1/v2，校验发布版本、Manifest SHA、Schema/引用闭包，固定白名单仅将 model.contracts 和 view.contracts 映射到 Saltcorn s1_contracts 表和 s1_contract_list View。插件、Trigger 等未授权对象全部排除，禁止把 Runtime 副本逆向提升为权威。
- **明确未投影：** form.contracts、workflow.approval 和 B4 Code；不声称 Saltcorn 在这一实验里执行了完整合同审批、自定义代码或表单业务语义。

## 四、真实数据库、浏览器、Native CLI 的独立 Oracle

### 4.1 OS 权限与版本 1

B9-01—07：Linux Kernel UID=999、Saltcorn Runtime UID=997，真正私有文件权限符合 0700/0600。Runtime 用户尝试直接读取、写入或执行 SQL UPDATE 访问权威 SQLite，**全部 DENIED**；无权威 Broker Token 时工具访问 401，使用跨 App Token 时 403。独立 B2 SQLite Oracle 显示 app-a/app-b 初始状态为空。

B9-08—16：Agent 经受控 B5 工具创建四类 B2 typed Schema，真实 Chromium 模拟人工发布不可变 v1。v1 Manifest SHA：

**43f433ea987988d6a832420180ed29baee79b090c235790b7c7a328adc07ffc2**

严格编译器校验 hash、schema 和依赖，故意改变已验证定义但不更新 hash 被拒。v1 派生 Pack SHA：

**ddb9823d07cf0051d3d01bcaf291c9f2bac04cec89dcd41633230d309d7bb259**

Saltcorn 真正安装派生 Pack 后，独立 SQLite 读出 Native View 列为 **contract_no、amount_minor、status**；真实 Saltcorn 浏览器查看原生 View HTTP 200，能够显示合同 HT-2026-000001。

### 4.2 B8 的危险原生写入在 B9 中被限制到派生副本

B9-17：未打补丁的真实 Saltcorn Chromium 原生 Field 编辑向导走完 **3 步**，成功把派生 SQLite 字段标签改为 **POLLUTED NATIVE RUNTIME FIELD**。这条 Native Web 仍可以绕过 Saltcorn 自身的外围 CAS，属于故意保留的攻击对照。

B9-18：受信内核的**独立物理 SQL 读取**证明，B2 实际 Manifest、草稿、已发布版本、回执、Audit 与 Native Web 攻击前**完全一致**。

B9-19：Saltcorn Runtime 自己的原生 CLI 再次真实执行 Field.update，exit 0，派生标签被改为 **Native Outside Gateway**。B9-20：权威 B2 SQLite 的 Manifest、所有定义、版本、事件与回执仍与攻击前完全一致，而且资源/发布哈希仍有效。

B9-21：Saltcorn Runtime 用户再次执行官方 install-pack，实际 **exit 0**；独立 Authority SQL 状态保持不变。这说明 Native Pack 仍能操纵派生副本，**不是证明 Pack 的业务升级语义已经正确**。

B9-22—23：控制器从同一 v1 已验证 Release 生成**全新** Saltcorn SQLite，Pack 内容 SHA 与初版**完全一致**；新 Native 字段标签恢复为 **Title**、View 列恢复 v1。随后通过 Runtime UID **实际删除污染过的旧 SQLite 文件**，而权威内核数据库与审计完全未变。

### 4.3 真正 v1→v2 发布及 v2→v1 回滚

B9-24—27：Agent 修改 B2 View.columns，真实 Chromium 发布新 v2。B2 Authority App 草稿 revision 从 **4→5**，v2 Release SHA：

**6f7cc7402b422fa564fc43e02eb7543645b21131ff25832aa243d4b24a83270e**

由 v2 真正生成的全新 Saltcorn 数据库，其独立 SQL View columns 变为 **contract_no、title、amount_minor、status**（比 v1 多 title）；真实原生浏览器仍能显示合同。

B9-28—36：受权 Publisher 经真实 B5 app.rollback、带 expectedPublishedVersion=2 及 targetVersion=1，将 B2 Authority 已发布版本指针**实际回退 v1**。再次执行 release.read 获得的 SHA 与原 v1 完全一致；从此 v1 新建的 Saltcorn SQLite 重新展示原 3 列 View，原生浏览器 HTTP 200。旧发布指针版本的重复回滚被 **409** 拒绝。最终 B2 Authority 保留**两份哈希正确的不可变发布快照**，当前发布 v1，最新草稿 revision 仍为 **5**（这是设计行为，不应把指针回滚误解为草稿也被撤回）；app-b 始终 revision **0**。

## 五、架构结论与严格限制

**本轮有限正向证据支持的候选架构：**

> **独立可信 Domain Schema + Manifest Kernel 为唯一应用定义权威写入和发布服务；Saltcorn 官方 Model/View 作为受限、可物化、可重新生成、可删除的派生运行组件。**

它实际解决了 B8 的一个具体威胁：**即使 Saltcorn Native Web/CLI/Pack 能越过自己的版本管控，它们也没有系统权限去修改 B2 权威 SQLite**，从而只污染可删副本，而不是毁掉权威版本账本。不是通过劝插件遵守 API，而是由真正不同 Linux UID 和数据库文件进行强制隔离。

**不代表已经解决的范围：**

1. **W17：运行时缓存与热更新。** 每个 Saltcorn 版本均从独立全新 SQLite 创建，未验证同一在线进程不重启时刷新全部 Native 模型/插件缓存。生产候选需要支持不可变实例加流量切换，或真实原生刷新协议。
2. **W24：发布、回滚与外部副作用一致性。** 本轮验证了 B2 发布指针 CAS 和新 Saltcorn 实例重建，但**没有**实现统一的代码/流程/Manifest/外部副作用原子事务、生产负载均衡器流量无损切换和业务补偿。
3. **业务数据迁移。** 各派生数据库中的合同来自一次性 native seed 脚本，不存在生产多版本交易数据迁移、行级权限、主数据同步或跨服务最终一致性保证。
4. **功能语义。** 编译器明确只投影 Model 和 View；B2 Form、Workflow、B4 Code **未被 Saltcorn 等价执行**。不能把已验证的静态展示投影冒充完整 AI 自主开发应用运行。
5. **特权与供应链。** root、拥有 Kernel UID 的其他进程仍可越过物理 SQLite 文件边界（B7 真实反例）；Manifest SHA 是内容 hash，不是发布者数字签名，未证明插件供应链、防内核进程入侵、企业身份授权或真正多节点部署。

**G1 结论保持不变**：S1 **IN_PROGRESS**；G1 **NOT_PASSED**；G1-B01 **PARTIALLY VALIDATED / OPEN**；冻结 W01—W24 **0/24 FULL PASS**，冻结合同 TC01—TC18 **0/18 FULL PASS**。B9 的 **36/36 研究检查**不替代冻结门禁，也不使 H03 自动完成。

**下一项建议 B10：** 在 B9 的不可变派生 Saltcorn 版本基础上，实测预热、Native Readiness、旧/新版本流量原子切换与回滚、已在途请求隔离；同时选择一条真正业务状态/审批工作流，明确数据归属、写入与补偿边界，以避免一直只验证静态 Model/View 显示。
