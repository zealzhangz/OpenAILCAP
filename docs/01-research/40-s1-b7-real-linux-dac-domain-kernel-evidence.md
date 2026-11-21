# S1 报告 40：B7 真正 Linux 宿主 UID 隔离、可信 Domain Kernel 服务及原生 SQLite CLI 权限边界

**日期：2026-11-21。实验判定：限定假设通过；S1 IN_PROGRESS；G1 NOT_PASSED；G1-B01 PARTIALLY VALIDATED / OPEN。**

## 一、研究起点与可证伪目标

[报告 38（B5）](38-s1-b5-ir-parity-tool-broker-evidence.md) 与 [报告 39（B6）](39-s1-b6-real-plugin-docker-isolation-evidence.md) 真实证明，**如果插件或其他宿主进程已具有 SQLite 文件权限，仅靠 B5 HTTP Tool Broker 或 B6 的额外 Docker 插件隔离，并不能阻止它直接 UPDATE 可信内核数据库**；运行时哈希拒绝和事故审计只能充当后续发现与阻断措施。

因此本轮不继续堆功能，而是提出一个强约束、可证伪的最小权限架构假设：

> 让独立 Linux 非 root UID `ailcapb7kern` 独占权威 SQLite 文件与启动凭据，通过本地可信 Domain Kernel 服务运行 B2/B4/B5；不同 UID 的本机原生 Plugin/Agent 即使能执行任意 Python/sqlite3 客户端，也不能直接连接、读取、修改该 SQLite，但持有限定 Token 时仍能通过受治理的 v3 Tool Broker 正常创建/编辑应用。root 或相同内核 UID 必须作为反例保留。

冻结失败条件：任何普通插件或 Agent UID 的文件 O_RDONLY/O_RDWR、SQLite ro/rw 连接/真正 SQL UPDATE、内核配置读取或跨 UID /proc 敏感环境访问成功，或者 Broker 能被绕过执行越权 Model/发布操作，或正常低代码业务无法继续运行，都视为失败。

## 二、可追溯一手证据

| 证据 | 结论 |
|---|---|
| 可复现完整工程 | [experiments/g1-b01-b7](../../experiments/g1-b01-b7/README.md) |
| CI 工作流 | [.github/workflows/s1-b7-os-dac-kernel.yml](../../.github/workflows/s1-b7-os-dac-kernel.yml) |
| GitHub PR | [#9](https://github.com/zealzhangz/OpenAILCAP/pull/9) 已合并 |
| main 提交 SHA | [8b4cd3e87135efe6744b9614e6673bcff439defb](https://github.com/zealzhangz/OpenAILCAP/commit/8b4cd3e87135efe6744b9614e6673bcff439defb) |
| **真正成功 GitHub CI** | [Actions #44897992713](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44897992713)，**completed / success** |
| 真实 Job | **136827642934** |
| 原始日志 + 结构化审计证据 | [Artifact #14704777950](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44897992713/artifacts/14704777950)，`s1-b7-real-linux-host-dac-domain-kernel-evidence` |
| B7 可信引导/OS 权限语义单元测试 | **16/16 PASS** |
| B2 typed Domain Kernel 回归 | **18/18 PASS** |
| B5 IR/Tool Broker 回归 | **40/40 PASS** |
| B7 真实 Linux UID + Native Agent/Plugin/CLI + Chromium + SQLite 物理检查 | **32/32 PASS** |
| 本轮外部大模型请求 | **0 次** |

**保留的失败过程**：[Actions #44897859852](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44897859852) 前三类单测均通过，但第一个内核进程在启动前被 GitHub Runner 的 checkout 父目录权限阻止读取源码（`Permission denied: .../kernel_service.py`）；同时首次拆分 UID 的临时目录清理被新文件属主权限阻止。修复方式不是放宽 DB 权限，而是把**可信、无密钥的最小研究源码副本**放到只读、可遍历的临时路径；**SQLite 与配置仍位于另外的专属 0700 目录**；实验结束后只由具有 sudo 的受信编排器清理内核属主目录。最终成功 Run #44897992713 验证了整个修订后的真实边界。

## 三、实际 OS 进程、文件和允许路径

~~~text
CI trusted controller (Ubuntu 24.04 / sudo-capable; laboratory ONLY)
  建立三名独立 Linux 非 root UID：
    ailcapb7kern UID 999：可信 Domain Kernel
    ailcapb7plug UID 997：不可信原生 Plugin/SQLite CLI
    ailcapb7agen UID 995：不可信原生 Agent/SQLite CLI

 kernel-only private directory (mode 0700, UID 999)
   authority.sqlite       (mode 0600, UID 999)
   service-config.json    (mode 0600, UID 999)
          │
          ▼
 kernel_service.py (真实 UID 999 独立进程)
   B2 SchemaStore + B4 ExtensionRegistry + B5 ToolBroker
   HTTP 127.0.0.1:ephemeral
         ▲                            ▲
         │                            │
     UID 995 Agent                UID 997 Plugin
     limited v3 token             only View tools
     no raw SQLite               no raw SQLite
         └──── API → Broker → typed mutation + CAS + Receipt + Audit ─────┘

 Human simulated via real Chromium browser + trusted same-site Session/CSRF.
 Independent physical_sql_oracle.py runs under permitted kernel UID.
~~~

没有让普通 Plugin 使用 root、Docker 权限或数据库路径；启动配置是受信测试控制器编写、随后 chown 为 kernel UID 的 0600 文件。用于实验的随机 Agent/Plugin/Runtime Bearer Token 从受信测试控制器经指定子进程的 **stdin** 输入，没有作为命令行参数、明文日志、公开 ready.json 或环境变量提供。Kernel 这轮不持有可执行构建的 Docker Socket，B4 Code Build 能力被显式 `NoBuildAccess` 禁用；**不能把 B4 独立构建的先前测试算作 B7 已在隔离内核运行 Docker 编译。**

## 四、真实 OS 与数据库负面访问测试

最终日志的 B7-03 显示私有目录 mode **0700**，SQLite 和服务配置 mode **0600**，文件和目录均属于内核 UID **999**。

| 真实执行的测试操作 | Plugin UID 997 | Agent UID 995 |
|---|---|---|
| `os.open(DB, O_RDONLY)` | **DENIED** | **DENIED** |
| `os.open(DB, O_RDWR)` | **DENIED** | **DENIED** |
| `sqlite3.connect(DB, mode=ro)` | **DENIED** | **DENIED** |
| `sqlite3.connect(DB, mode=rw)` 后真实 `UPDATE apps SET revision=revision` | **DENIED** | **DENIED** |
| 读取私有 kernel config / Token | **DENIED** | **DENIED** |
| 读取 `/proc/<kernelPID>/environ` | **DENIED** | **DENIED** |
| 遍历 `/proc/<kernelPID>/fd` | **DENIED** | **DENIED** |

这些不是根据提示词猜测的权限结果。GitHub Actions 直接以各自真实 Linux UID 调用了标准 Python 的 `os.open`、`sqlite3.connect` 和 `os.access`，随后由另一段**非 SchemaStore/非 Broker 的独立只读 SQL 程序**以受信 kernel UID 读取真实 DB，核查数据库的 app revision、定义、审计、Receipt 在攻击前后完全一致（B7-05—08）。

## 五、32 个端到端检查中的关键证据链

- **B7-01—09**：三个 UID 实际不同、内核服务器确实以 UID 999 运行、DB/配置 DAC 0700/0600、loopback HTTP 健康、物理双应用 DB 初始为空、普通 Plugin/Agent 原生 DB read/write/SQL UPDATE/私有配置和内核 /proc 访问全拒绝、物理 DB 未受攻击副作用影响、公开就绪文件无 Token。
- **B7-10—14**：原生 Plugin 在无法读 DB 的情况下仍通过受信 Kernel Broker 读取 Draft HTTP **200**；越权 `sql.admin` / `code.publish` **403**，伪造 `actorId` 422，跨 App 403，尝试绕过 v3 直接用 Bearer 读 v2 Draft 返回 **401**。
- **B7-15—18**：真正原生 Agent 通过受限工具创建 Model、Form、Workflow，Plugin 只能通过同一 Kernel Broker 创建 View，越权改 Model 被 **403 KIND_FORBIDDEN**；物理 SQLite 确认四类定义、哈希、App Manifest、角色审计一致。
- **B7-19—22**：真实 Chromium 浏览器需要登录；人工浏览器编辑旧 View 期间原生 Plugin 真实修改该 View，浏览器过时保存被 **409** 拒绝，Plugin 结果保留。持旧版本的原生 Agent 同样 409；真实浏览器重新加载后仍能继续编辑 Form。
- **B7-23—27**：Plugin 以同 `changeId` 发送相同命令，Broker 返回 `replayed=true`，真实 SQLite Audit/Receipt 不重复新增；模拟人类授权通过浏览器发布 B2 v1，真实表单保存一条合同，超阈值 Workflow 经 `PendingLevel1 → PendingLevel2 → Approved`，Chromium 实际读取已发布 View 和记录。
- **B7-28：关键同 UID 负对照**：同内核 UID 999 的另一个原生 CLI **实际能读取服务配置并用 sqlite3 直接 UPDATE 权威数据库**，说明“仅内核 UID 可访问”不能防止**同 UID 被攻陷的其他进程**。
- **B7-29：特权 root 负对照**：sudo-capable 受信实验控制器作为 root **实际写入**已受保护的 `definitions.spec`，且没有同步旧 `hash`；独立 SQL 清楚记录这项**成功的物理篡改**。
- **B7-30—31**：再次读 B2 Draft 时，可信内核发现 `RESOURCE_DRIFT`，返回 HTTP **409**，应用草稿状态 **QUARANTINED**；上一次验证的不可变 B2 Release **v1 仍能读取且哈希保持不变**。这是运行期检测和失败封闭，**不代表 root 不能写入**，也不能防御 root 同时修改内容和签名/哈希。
- **B7-32**：独立 SQL 确认 app-a revision 7、app-b revision 0、Agent/Plugin/Human 的真实 Actor Audit 全部存在，跨 App 未串写；本轮模型调用 0。

## 六、研究结论与架构决策

### 已证实的限定结论

> 针对**确实分离 Linux UID、且无 sudo、无共享 kernel UID、无额外组授权**的原生插件/CLI/Agent，在可信 Kernel 独占 SQLite 目录（0700）、文件（0600）时，普通进程确实不能直接读写权威 DB 或内核凭据，但仍可通过 Broker 受控执行经过授权与 CAS 校验的真实应用操作，且 Chromium 人工编辑和业务运行不受损。

这比 B6 对 Docker 插件的隔离更进一步：它验证了**非容器、原生宿主 OS 进程**的强制文件权限拒绝，从技术上支持“可信 Domain Kernel 独占写权限，其他开发执行者只有类型化工具权限”的架构候选。

### 并未关闭的 G1 阻断

1. **同 UID 和 root 仍可绕过**：B7-28/29 主动正面复现。要达到真正不可绕过，必须保证任何未审计的原生 Field/Pack/CLI、同 UID 动态插件和构建进程**都不能作为 Kernel UID 执行，也不能持有 root/sudo/Docker Socket**；生产级 DB 最好采用真正的独立数据库服务身份及服务端账号权限分离。
2. **未验证真实 Saltcorn 原生写入口**：B7 测的是研究型原生 Python + sqlite3 CLI，不是 Saltcorn `Field.update`、Pack 导入和原生扩展可达的全部路径；如果其 Node 原生进程与 Kernel 同 UID，仍存在直接写权。
3. **本轮未验证通用自定义代码构建**：可信 Kernel 显式没有 Docker Build 权限，未来需验证独立 Build Worker 与 Kernel 的不可伪造构建回执、制品供应链及人工发布授权。
4. **Loopback v3 Token 并非最终产品身份认证**：随机 Bearer token、研究浏览器密码和信任测试编排器均为临时工况。正式应对接企业 SSO/角色组织、插件签名与权限委托、Unix Socket ACL/mTLS、Token 轮换与撤销，控制所有平台原生入口的权限。
5. **发布仍是 B2 v1 资源快照与 B4 扩展分离的研究模型**，缺少跨代码、资源、插件依赖以及外部动作的统一原子 Release/补偿。

### 下一研究推荐

优先开展 **B8：真实原生写入口隔离与受信写入边界收敛**。需要将前序 C2 的实际 Saltcorn native `Field.update` / CLI 绕过，与本轮 Linux UID/专用 DB 服务模式结合，证明原生应用加载器和安装器无法绕过 Kernel 后再决定正式底层内核采用“自主 Domain Kernel + 可插拔成熟 Runtime”或修改上游。下一步再挑战冻结 W11/W16/W20/W24 的正式门禁及应用+代码统一 Release。

**最终门禁**：S1 **IN_PROGRESS**；G1 **NOT_PASSED**；G1-B01 **PARTIALLY VALIDATED / OPEN**；冻结 W01—W24 **0/24 FULL PASS**，冻结合同 TC01—TC18 **0/18 FULL PASS**。B7 的 **32/32** 研究项不能直接转成正式 W 或 TC。
