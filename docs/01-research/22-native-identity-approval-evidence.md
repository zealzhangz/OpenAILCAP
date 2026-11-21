# S1 实证报告：真实 Saltcorn 登录身份绑定原生审批 Trigger

**实验日期：2026-11-21。阶段：S1。结论：真实浏览器登录 + Saltcorn 原生 REST + Saltcorn 原生 Validate/Insert Trigger + 真实 SQLite 业务结果在研究场景通过 32/32 独立断言；G1 尚未通过。**

## 一、执行证据及版本

| 项目 | 一手证据 |
|---|---|
| 最终成功 GitHub Actions | [Run #44879041055](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44879041055)，状态 completed / **success** |
| 被测实验 Commit | [748b39239ba001a6fbf496f42d5bfcfcd98685ac](https://github.com/zealzhangz/OpenAILCAP/commit/748b39239ba001a6fbf496f42d5bfcfcd98685ac) |
| 实际 Job | 136770054918 |
| GitHub Actions Artifact | s1-native-authenticated-approval，ID **14697420714**，含原始结构化结果 JSON |
| 真实平台安装 | @saltcorn/cli 1.7.0-beta.5；Saltcorn SQLite；Ubuntu 24.04；Playwright 1.56 Chromium |
| 一手源代码研究固定 SHA | [saltcorn/saltcorn@515254bee5a98df70530cc59846b1df02d5db350](https://github.com/saltcorn/saltcorn/tree/515254bee5a98df70530cc59846b1df02d5db350)；源码 SHA 不等于已验证 npm 包字节级构建指纹 |
| 完整可复现实验 | [experiments/platform-saltcorn/auth](../../experiments/platform-saltcorn/auth/README.md) |
| 冻结场景 | [合同 Benchmark spec.json](../../experiments/contract-benchmark/spec.json)；原始 18 项结果保持 NOT_RUN |

这是前一轮 [真实原生合同金额、审批业务 Trigger 运行](21-saltcorn-native-workflow-evidence.md) 后的**真实身份授权深化**。上轮 actor_role 为任意客户端字段，不能证明任何真正登录权限；本轮真正把身份带入 Saltcorn 平台原生业务 Trigger。

## 二、真实平台调用链

1. 使用 Saltcorn 官方 create-user CLI 创建四个互不相同、各有随机密码的真实用户：creator / approver1 / approver2 / viewer。**Saltcorn 原生 role_id 均为 80**，即“已登录普通用户”；没有创建四个真实 Saltcorn 组织 RBAC 角色。
2. Playwright Chromium 实际打开 /auth/login 并逐人提交原生登录表单，四个不同浏览器上下文各自持有真实 Session Cookie。每个表单含 _csrf 字段。
3. 对各浏览器登录上下文，用 Playwright APIRequestContext 携带 Cookie 和**从当前认证会话 Saltcorn 页面重新读取的 CSRF 令牌**调用平台官方 POST /api/s1_bench_action_requests/。
4. [Saltcorn api.ts](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/server/routes/api.ts) 检查表级 min_role_write，然后将 req.user 或经过鉴权的 user 传给 Table.tryInsertRow；普通用户仅对审批动作请求表开放写权限，合同主表和审批明细表仍仅管理员可直接写。
5. 原生 [Saltcorn Table.ts](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/saltcorn-data/models/table.ts) 执行 Validate Trigger。研究 [trusted-validate.js](../../experiments/platform-saltcorn/auth/trusted-validate.js) 取服务端认证用户 user.id、user.email、user.role_id，**而不是相信客户端声称的 actor_role / actor_id**；该研究 Trigger 采用硬编码 email→业务审批角色映射，随后检查合同当前状态、金额级别与需要的审批级次。
6. 成功后，原生 Insert Trigger 真正修改合同并插入审批明细；独立 Python **只读物理 SQLite** 验证持久化的实际状态、审批请求数量与审批人 ID。这些操作不是研究网关直接执行的业务更新。

**特别说明**：本实验“浏览器操作”指真正的网页登录和认证会话发起 REST 请求，**没有创建可视化审批按钮或通过原生 Edit View 提交审批表单**。所以不能标记“人工可视审批 UI 已验收”。

## 三、真实结果

| 验证类别 | 实际响应/数据库结果 |
|---|---|
| AUTH01—03 | 四个真实 Saltcorn 用户的物理 users 表角色均为 80；四次 Chromium 真正登录成功 |
| AUTH04 | 未登录直接 POST 动作请求：**HTTP 401**，不产生数据库请求 |
| AUTH04b | 已登录但缺 CSRF 令牌：重定向到首页，自动跟随重定向后可能看见 **HTTP 200 HTML**，但数据库不产生任何动作 |
| AUTH05/06/19 | 伪造 actor_role、伪造 actor_id、伪造其他审批人身份：**HTTP 400 IDENTITY_MISMATCH**，不改变合同/审批记录 |
| AUTH07/09 | Creator 正常提交普通合同，Approver1 实际批准：最终 Approved，审批记录 1 条 |
| AUTH08 | Approver2 企图越级审批普通合同：**HTTP 400 FORBIDDEN**，状态保留 Submitted |
| AUTH10/12/14 | 超过 100 万元合同：Creator 提交、Approver1 批准至 Level1Approved、Approver2 二次批准至 Approved；两条审批记录 actor_id 与**真正登录用户 ID**相同 |
| AUTH11/13 | Viewer 无审批资格，或 Approver1 企图执行第二级审批：**HTTP 400 FORBIDDEN**，合同状态不变 |
| AUTH15/16 | Creator 提交另一高金额合同，Approver1 驳回：最终 Rejected，真实审批记录 1 条 |
| AUTH17 | Viewer 直接 POST 修改受保护合同主表：**HTTP 401**，业务状态不变 |
| AUTH18 | Creator 绕过业务动作表，直接 POST 插入审批明细：**HTTP 401**，审批数保持 2 |
| AUTH20 | 独立 SQL 验收普通合同 2 个合法动作请求/1 条审批；高额合同 3 个请求/2 条审批；驳回路径 2 个请求/1 条审批；攻击专用合同 0 个请求/0 条审批 |
| AUTH21/22 | 真正 _sc_triggers 中 3 条原生 Code Action 注册存在；动作表 min_role_write=80 与表权限安排符合预期 |

**Run #44879041055：32/32 项检查 PASS，0 项 FAIL，GitHub Actions Completed / Success。** GitHub 结构化 Artifact 为完整原始数据。本目录的 [机器可读摘要](auth-approval-observations.json) 为经 Job stdout 核实的审慎摘录。

这组实验验证“认证身份确实进入业务 Trigger 并影响可持久化审批结果”；不是向用户显示一个 Python 状态机结果。

## 四、本轮发现的 CSRF / 200 假成功风险

首次 CI [Run #44878238956](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44878238956) 证明用户登录成功、匿名写入 401，但带 Session Cookie 的所有审批 POST **表现为 HTTP 200，数据库 0 条更新**。第二次 [Run #44878430497](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44878430497) 添加脱敏诊断后，核实 API 请求最终被引导至路径 /，content-type 为 text/html，而不是预期 application/json。

原因经 [Saltcorn app.js](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/server/app.js) 反向追踪：当 /api 请求**没有** connect.sid Session Cookie 时可跳过 CSRF；**有 Cookie 的网页登录 API 请求必须携带相应 CSRF 令牌**。缺令牌的客户端自动跟随重定向后，拿到 HTML 200 却无业务执行。因此 OpenAILCAP 独立验收必须检查**最终 URL、Content-Type、JSON success、真实资源状态**，而不是仅检查最终 HTTP 200。

修正后 [Run #44878664510](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44878664510) 的 **32 个业务与安全断言均已 PASS**，但 CI 仍显示 failure，原因是测试脚本末尾错误地要求 28 项；修正总数后 [Run #44878807173](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44878807173) 又遇到 Chromium 第四次只读页面访问的偶发超时。将有限重试**仅加在 GET 页面导航**、不重试任何审批 POST 后，最终 Run #44879041055 稳定完成 32/32 和 Artifact 上传。所有失败记录保留，不以绿色最终运行掩盖前两类问题。

## 五、是否达到冻结合同 G1/TC04？

**尚未达到。** 需要准确区分：

- 本次**已验证**：真实 Saltcorn 登录会话、真实 user.id/email 进入平台原生 Trigger，伪造 actor_role/actor_id 无法执行审批，普通角色不能绕过业务触发器直接写受保护合同/审批表，合法审批在数据库中形成正确状态与责任人记录。
- **尚未验证**：与企业真实组织机构/RBAC 绑定的审批人授权。四个用户都是同一个 Saltcorn role_id=80；业务审批身份通过研究代码硬编码邮箱映射，不能代表实际多级组织、人员变更、岗位权限或行级/多租户授权。
- **与冻结 TC04 不一致**：TC04 要求 HTTP 403 + DB unchanged；Saltcorn 原生表级权限返回 **401**，业务角色不匹配返回 **400**，而不是 403。必须在未来正式 API 适配层实现经批准的语义，或者正式评审修改规范，不能默默把 400/401 当成 403 PASS。
- **原生 HTTP 事务尚缺故障注入**：本次 API 调用内部使用 Saltcorn 的 withTransaction，在此前研究已复现 SQLite 分支不具备可靠的 SQL 回滚。测试过程中成功写入合同和审批明细不等于原子性、重复审批/并发幂等都合格。
- 金额字段依然使用 canonical TEXT + 整数分，不等于冻结的 decimal(12,2)。没有真实 LLM Agent、自然语言创建规则、插件发现、跨应用授权、自动发布和回滚。

因此本轮给 TC03/04/05/18 提供更强的**部分真实平台证据**，但**冻结 18 项完整任务仍 0/18 完整 PASS，G1 仍 NOT_PASSED，不能进入完整 S2**。

## 六、对 OpenAILCAP 的直接架构启示

1. **授权必须由服务器确定身份**，客户端 actor_role、actor_id、owner_id 等只可作为待校验字段。将用户签名会话/委托主体与具体资源、动作和审批级次关联，拒绝伪造。
2. **分离身份认证、业务授权、CSRF、原子事务**。Saltcorn 原生表权限负责“谁能写请求表”，领域 Trigger 负责“谁可以在什么状态批准哪个合同”；HTTP 401/400/403 应当有明确、稳定的产品契约。
3. **以真实资源为测试裁判**。独立验收同时核对 Cookie 登录、CSRF、响应类型与最终 URL、请求/审批表、状态迁移、审批人主键，不信任客户端 200 或模型自述。
4. **不要直接将通用高权限 run_js_code 暴露给 Agent**。应通过权限受限的类型化能力 API 执行合法领域命令，并对危险编辑有人工审批和发布门禁。
5. **下一工作包 P0**：真实 LLM Agent 在明确工具权限下完成最小合同配置/审批能力的发现与调用；P0：独立于 Saltcorn 内置 SQLite 包装层的正式事务/幂等机制；P1：专业组织 RBAC 与真实审批 UI、与同一冻结 Benchmark 的真实其他平台对比。

本轮研究明确支持“通过平台原生认证 + 原生领域能力接口可以承载受限人机协同”的机制方向，但尚不足以做最终技术选型或通过 G1。
