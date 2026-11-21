# S1：Saltcorn 真实登录身份绑定原生审批触发器（研究实验）

## 验证目标

在上一轮通过 Saltcorn 原生 3 条 Code Action Trigger 验证 **12 项金额边界 + 12 项审批状态 + 3 条连续审批**后，继续排除最重要的安全缺口：**之前的 actor_role 只是调用方填写的字符串，而不是真正的登录身份**。

本实验继续使用真正的 Saltcorn CLI 1.7.0-beta.5、Table、Trigger、SQLite 和原生 REST API，使用 Playwright Chromium 登录四个独立 Saltcorn 账户。审批请求从登录 Cookie 的 HTTP 客户端发送到 Saltcorn **原生** POST /api/s1_bench_action_requests/；原生 API 的 req.user 进入 Table.tryInsertRow 的 Validate/Insert 触发链，并核对 user.id / user.email / user.role_id 与业务请求声称的 actor_role / actor_id。

这不是自建 HTTP 业务审批网关，也没有使用 LLM Agent。研究触发器是手工编写的固定角色演示规则，不是企业组织 RBAC 或生产可用工作流。

## 真实执行路径

1. 复用 [原生审批 Trigger Pack 基线](../workflow/README.md)，通过 [harden_pack.py](harden_pack.py) 为 action_requests 表授权 Saltcorn 注册普通用户 role_id=80 的 API 写入，并将 Validate Trigger 替换为 [trusted-validate.js](trusted-validate.js)。
2. 在一次性 Saltcorn SQLite 中创建 4 个不同登录用户（creator、approver1、approver2、viewer），每人有独立随机密码。
3. 使用 [seed.js](seed.js) 经原生 Table.insertRow 创建正常金额、高金额、高金额驳回及专门攻击用的 4 个独立测试合同，路由 Trigger 自动写入对应 HIGH/NORMAL 路由。
4. Playwright **真实 Chromium** 登录各用户的 /auth/login。通过各自浏览器上下文持有的 Saltcorn Session Cookie 调用原生 /api/s1_bench_action_requests/。
5. 原生 API 决定表级访问权限；原生 Validate Trigger 从可信 user 读取登录身份，校验所宣称的 role/id 是否属于该用户以及能否做本状态的审批；原生 Insert Trigger 实际更新合同并记录审批明细。
6. 独立 Python 从 SQLite 只读检验每次角色操作后的实际业务状态、审批请求/记录数和真实 DB 中的 approver_id。

## 预注册检查

27 条断言涵盖真实用户身份/角色、4 次真实 Chromium 登录、匿名 REST 写入拒绝、Viewer 与 Creator 伪造 approver1/approver2 身份、Creator 提交、Approver1 普通合同终审、Approver1/Approver2 高金额合同分级审批、合法驳回、错误级别拒绝、限制普通用户直接更新合同状态/直接伪造审批记录、实际 4 组合同的请求和审批记录数量、3 条原生 Trigger 与表级权限元数据。

**注：原生 Saltcorn API 在当前版本的表级权限不足时返回 HTTP 401（不是 403）。** 合法登录但业务角色不足时，通过原生 Validate Trigger 返回业务错误，一般为 HTTP 400。测试必须记录实际状态码，不把 401/400 包装为 HTTP 403。状态与数据库都不变是独立验收条件。

## 严格限制

- 客户端直接调用 Saltcorn REST，登录使用真正 Chromium，**没有通过平台原生审批按钮/表单页面操作**；“浏览器登录 + 会话 HTTP 调用”不能简写为“网页可视审批界面验收通过”。
- 用户邮箱到业务角色的映射**硬编码在实验 Trigger 中**，不是 Saltcorn 管理角色/组织树级 RBAC；所有用户当前 Saltcorn role_id=80，表级别只能区分注册用户/管理员，具体审批人校验依赖定制触发器。
- Saltcorn /api 表写入调用 Table.tryInsertRow 时经过官方 SQLite withTransaction 包装器。此前实验已证明 Saltcorn SQLite 包装器的异常回滚不可靠；因此**本次不声称审批跨表原子性或高并发幂等已通过**。
- 角色/ID 的攻击性请求及审计证据不应包含 Session Cookie、密码或 CSRF 值。GitHub CI 的凭证仅在临时 Runner 中生成。
- 没有真正 AI Agent、代码隔离、自动生成流程、分布式部署或多应用隔离，金额仍是 TEXT canonical + Integer 分而非冻结 decimal(12,2)。
- G1 仍须按照 README 的全部门禁单独评审，不因实验通过自动转为通过；原始冻结 spec.json 18 项不允许篡改结果。

## 源码参考

- [Saltcorn API 路由 api.ts](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/server/routes/api.ts)：在原生 POST /api/:tableName/ 通过 potentiallyAccessAllowedWrite 进行表权限检查，调用 Table.tryInsertRow(row, req.user || user)，身份传给模型。
- [Saltcorn Table.ts](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/saltcorn-data/models/table.ts)：Table.insertRow/tryInsertRow 的用户/Validate/Insert 行为。
- [Saltcorn Trigger.ts](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/saltcorn-data/models/trigger.ts)：Validate/Insert 调度与 user 传递。
- [Saltcorn Auth routes.ts](https://github.com/saltcorn/saltcorn/blob/515254bee5a98df70530cc59846b1df02d5db350/packages/server/auth/routes.ts)：原生用户登录 Session/Passport。
