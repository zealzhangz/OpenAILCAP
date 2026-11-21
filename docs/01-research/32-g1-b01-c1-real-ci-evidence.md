# S1 报告 32：G1-B01 C1 最小统一写入服务真实 CI 证据（仅独立研究原型）

**日期：2026-11-21。G1 仍 NOT_PASSED。G1-B01 尚未关闭。**
本轮首次将 [统一写入契约](30-g1-b01-unified-write-contract.md) 的部分机制实现为真正可运行的 Python/SQLite/HTTP 服务并经独立 GitHub Actions 测试。和历史 Saltcorn 原生运行研究不同，C1 不依赖 Saltcorn，它是**OpenAILCAP 自研核心写入路径的最小独立原型**。

## 一、可回溯提交/原始证据

| 证据项 | 位置 |
|---|---|
| 主线初始 C1 引擎 | [Commit 8989d8b](https://github.com/zealzhangz/OpenAILCAP/commit/8989d8b4e8c2bcb45cae3527b3d32dd7262f69f8) |
| C1 单测 | [Commit f861105](https://github.com/zealzhangz/OpenAILCAP/commit/f8611057229202989f5da62dac860aa999366695) |
| 结构化结果生成脚本 | [Commit fa22bc3](https://github.com/zealzhangz/OpenAILCAP/commit/fa22bc3f9828847df8864216e5081866d7f3b683) |
| 离线 CI 工作流 | [Workflow](../../.github/workflows/s1-g1-b01-c1.yml) |
| 真实 PR 审查变更 | [PR #1](https://github.com/zealzhangz/OpenAILCAP/pull/1)：补充跨应用同 changeId 隔离测试 |
| 原始 GitHub Actions 运行 | [Run #44886944054](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44886944054)，**completed/success** |
| CI Job | 136794151797，standalone-c1-guarded-editing |
| 原始结果 Artifact | [Artifact #14699494263](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44886944054/artifacts/14699494263)：c1-observations.json + unittest.log |
| 评审后主线合并提交 | [Commit 8a037d1](https://github.com/zealzhangz/OpenAILCAP/commit/8a037d10787195de1e1f887eecbb8e0798457a60) |

原始成功日志明确记录：Python 3.13.18、ubuntu-24.04、脚本 compile success、**Ran 31 tests in 8.786s / OK**、**pass_count=31 fail_count=0 error_count=0**，Artifact 上传成功。

**计数说明**：31 是 unittest *执行实例*数，并不是 31 个彼此不同的核心场景；HttpPreflight 继承了 StorePreflight 的 13 项检查并在 HTTP 测试 fixture 下重复执行。共有 18 个独立测试方法定义（13 个 Store 原始方法 + 4 个 HTTP 额外方法 + 1 个跨应用键隔离方法）。不能将 31/31 直接转换成冻结 W01—W24 的任何 31 个验收点。

## 二、真实验证了什么

- 在一次性真实 SQLite 文件中存储资源内容、revision、content hash、幂等 Receipt 及审计；同一行的写入在 BEGIN IMMEDIATE 中比较并提交。
- 测试宿主提供三类身份：浏览器 Session+CSRF、Agent Bearer、Plugin Bearer。实际 loopback HTTP 通过同一服务提交，对同一资源三次修改，revision=3、最新内容正确，受控请求之间没有旧快照静默覆盖。
- 真实两个独立 Python 子进程针对相同 revision 竞争，结果恰好一个 APPLIED、另一个 VERSION_CONFLICT，物理库只增加一次 revision/审计。
- 同 changeId、同主体/原请求在后续资源已被其他主体编辑后重放，仍返回原回执，不重复副作用；同键不同摘要或主体返回 CHANGE_ID_REUSED；两应用相同键各自可以成功。
- 在资源写入与 receipt/audit 记录之间注入异常后，资源、revision、receipt/audit 均保持旧状态。
- 绕过服务用测试代码直接 SQL 修改字段但不修改 hash：HTTP/Store 检测到内容漂移，事务性标记 QUARANTINED，后续 Agent 写入失败关闭。
- 客户端携带自称 actorId/role/tenantId 被 Schema 拒绝；跨 app/只读/缺 CSRF/过期 Bearer Token 被拒绝。
- 完全离线运行，不使用真实 LLM、任何 DeepSeek API 费用，也未创建生产数据库。

## 三、不能外推到什么

| 范围 | 证据状态 | 为什么仍未达标 |
|---|---|---|
| 独立 C1 原型 CAS/HTTP/SQLite 小范围机制 | **S0 真实 CI 验证** | 单机 SQLite、两个字段、固定测试身份 |
| Saltcorn 原生 /field/:id 写入 | **NOT_RUN（本轮）** | C1 自建 HTTP，没有改造 Saltcorn 自带设计器；[历史负例](19-real-browser-edit-evidence.md) 仍成立 |
| 真正插件执行与供应链隔离 | **NOT_RUN** | Plugin Bearer 只是测试身份，未加载插件或受限代码 |
| 浏览器真实 DOM/密码登录 | **NOT_RUN** | 浏览器请求用测试 Cookie，没有真实 Chromium 操作或成熟登录 |
| 生产可信身份委托和组织权限 | **NOT_RUN** | 测试宿主预置密钥，无 HTTPS/OIDC/组织 RBAC |
| 多数据库/分布式写、真正运行时缓存和发布 | **NOT_RUN** | 未实现跨 DB 事务、完整 Manifest、发布/回滚 |
| AI 生成数据模型、代码、测试、自动部署 | **NOT_RUN** | 没有任何外部模型推理；只是后续开发的安全前提 |
| 冻结 W01—W24 原始完整验收 | **0/24 完整通过** | 要求实际 native Web + Agent + Plugin 等路径，C1 子机制通过不能替代原标准 |
| 冻结合同 TC01—TC18 | **0/18 完整通过** | 本实验并非完整合同应用闭环 |
| 第一阶段门禁 G1 | **NOT_PASSED** | 安全写入口覆盖范围与 AI 自主开发等核心风险仍未解决 |

## 四、ATAM 和架构选择影响

本实测证明：不依赖统一全局 IR，也能在受限资源上建立版本/哈希/身份/审计/幂等的强制命令入口，并在本地服务端提供人工/Agent/插件测试身份等价的写入协议。因此分域 Schema + Manifest + Typed Domain Command 仍适合进入 S3 更大对照。

它**没有证明**采用分域 Schema 作为完整应用模型优于全局 IR，或证明自建完整编辑器成本低于改造某第三方框架。此处在单机 SQLite 进行的安全正向实验与历史 Saltcorn 原生未治理覆盖反例没有矛盾：真正关键在于**所有实际写入口是否被强制收拢**。

## 五、下一批最小行动

1. **C2 原生强制写入**：在真实 Saltcorn CLI + Chromium 中，追踪字段 POST/fieldFlow/Field.update（含插件和 Pack），确认有无受支持、可拦截的服务端共用写入扩展点，并先做可否证原生旧表单测试。
2. **跨平台路径边界**：若原生界面无法在所有路径接入版本治理，不把其作为 OpenAILCAP 生产编辑器；选择自建最小 Web 设计器统一进入 C1 服务的原型演进。
3. **真正插件与独立安全身份**：下一阶段使 plugin handler 走工具 Manifest 授权和权限上下文，而不是测试 bearer 别名。
4. **建立运行/发布闭包**：加入 schema reference、构建 hash、发布 gate，不扩张为大而全 DSL。
5. **保留证据口径**：新 CI 每个测试均输出实际状态、失败对照和 Artifact；不可修改原冻结 24 项标准以获得好看的完成度。

**结论**：G1-B01 从 SPECIFIED / NOT IMPLEMENTED 前进至 **C1 STANDALONE PoC IMPLEMENTED + CI VERIFIED（31/31 test instances）**；全渠道原生写入仍未覆盖，G1-B01 **OPEN**，S1/G1 **NOT_PASSED**。
