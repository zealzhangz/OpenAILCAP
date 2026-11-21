# S1 报告 39：B6 不可信插件真实 Docker OS 隔离与宿主专属工具网关实测

**研究日期：2026-11-21。实际结果：B6 本轮全部已预设的限定研究用例通过；S1 IN_PROGRESS，G1 NOT_PASSED，G1-B01 PARTIALLY VALIDATED / OPEN。**

## 1. 对应的真实反例和本轮任务

[报告 38：B5](38-s1-b5-ir-parity-tool-broker-evidence.md) 中，B5-28 实际证明了：**已经拥有 SQLite 文件写权限的宿主程序可以绕过 Tool Broker 直接 UPDATE 已经验证的 Code Artifact**，即便后续运行态能够发现哈希漂移并拒绝使用，物理变更仍已发生。此前 B5 的“插件”只是运行在同一个可信操作系统用户权限下的独立进程，无法将 Broker API 授权等同于操作系统隔离。

本次 B6 不额外调用大模型，也不重复静态 Broker 权限单测，而是运行**真正的非 root、无网络、只读、禁止特权的 Docker 容器内恶意 Python 插件**，让它主动尝试打开真实宿主数据库、Docker Socket、宿主 Secret 以及外网；并让它真正通过**由可信宿主保管 Token 的工具代理**修改 B2 View，在浏览器、业务记录、审计与代码运行中验证结果。

这是对一个更强、更窄的系统安全假设的测试：**如果插件在实际 OS 层面无法访问数据库和宿主秘密，修改应用资源的唯一允许通道能否由可信 Host Relay + B5 Typed Broker 强制授权？**

## 2. 可重复验证的一手证据

| 项目 | 结果与原始链接 |
|---|---|
| 本轮已合并代码 | [experiments/g1-b01-b6](../../experiments/g1-b01-b6/README.md) |
| 工作流 | [.github/workflows/s1-b6-plugin-isolation.yml](../../.github/workflows/s1-b6-plugin-isolation.yml) |
| GitHub PR | [PR #8](https://github.com/zealzhangz/OpenAILCAP/pull/8)，已合并 main |
| main 合并提交 | [f18e9341be4af086bb1b1d69341e8789ecfdad58](https://github.com/zealzhangz/OpenAILCAP/commit/f18e9341be4af086bb1b1d69341e8789ecfdad58) |
| **最终真实 CI** | [GitHub Actions #44896786049](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44896786049) **completed/success** |
| 实际 Job | **136824055360** |
| 原始日志与结构化实验数据 | [Artifact #14704775846](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44896786049/artifacts/14704775846)，`s1-b6-real-plugin-os-isolation-evidence` |
| B6 Host Plugin Isolation 单元测试 | **25/25 PASS** |
| B2 Domain Schema/SQLite 回归 | **18/18 PASS** |
| B4 自定义代码 AST/权限回归 | **27/27 PASS** |
| B5 IR + Typed Broker 回归 | **40/40 PASS** |
| B6 真实 Docker/Chromium/SQLite/受信工具桥接端到端 | **32/32 PASS** |
| DeepSeek / 其他外部收费模型 | **0 次模型调用** |
| 补强前第一轮完整成功记录 | [CI #44896682720](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44896682720)，24 单测 + 32 E2E 全通过；后来发现初版仅尝试密钥文件 O_RDWR，因此**不能证明禁止读**，随后明确补上 O_RDONLY DB/Secret 两项检测，以上述最终成功 #44896786049 为准。 |

本轮不应把 **25/25 + 18/18 + 27/27 + 40/40 + 32/32** 误称为正式 W01—W24 或 TC01—TC18 已通过；这些都属于本独立 B6 实验及历史回归的受限范围。

## 3. 确实执行了什么 OS 隔离

可信宿主首先在真正的 GitHub Ubuntu 24.04 Runner 上拉取 Docker `python:3.13-alpine`，在本次运行时查验镜像的**不可变本地 Image ID（sha256）**，其后每个不可信插件任务全部以该 image ID 调用 Docker，不允许 runtime 再拉取。

插件的实际 Docker 启动约束：

~~~text
docker run --rm --pull=never
  --network=none --read-only --cap-drop=ALL
  --security-opt=no-new-privileges
  --pids-limit=32 --memory=192m --cpus=1
  --user=65534:65534
  --tmpfs /tmp:rw,nosuid,nodev,noexec,size=8m
  --mount type=bind,src=<仅有 plugin_untrusted.py/request.json 的临时目录>,
                   dst=/workspace,readonly
  --entrypoint python3 <本次不可变 sha256 image ID>
    -I -B /workspace/plugin_untrusted.py
~~~

**没有**宿主 DB、源代码仓库、API 密钥、Docker Socket、宿主 `/run`、网络、授权 Token 的挂载或环境透传。受信 Docker CLI 本身也通过最小化的环境字典启动，而不是继承全部宿主环境。

在容器内实际运行的 [plugin_untrusted.py](../../experiments/g1-b01-b6/plugin_untrusted.py) 不受 B4 Python AST 白名单约束，即按插件威胁模型拥有执行一般 Python/SQLite/Socket 文件操作的自由度，但这些操作只能对容器自身环境生效。

**最终真实 E2E 记录的 OS 探针**：

| 实际进程中的动作 | 观察 |
|---|---|
| `os.getuid()` | **65534**（非 root） |
| `sqlite3.connect(host DB, mode=rw)` | **DENIED** |
| `os.open(host DB, O_RDWR)` | **DENIED** |
| `os.open(host DB, O_RDONLY)` | **DENIED** |
| `os.open(host Secret, O_RDONLY)` | **DENIED** |
| `socket(AF_UNIX).connect('/var/run/docker.sock')` | **DENIED** |
| `socket(AF_INET).connect('1.1.1.1',443)` | **DENIED** |
| `os.open('/workspace/plugin_untrusted.py', O_RDWR)` | **DENIED** |
| `os.environ.get('S1_B6_HOST_SENTINEL')` | **未继承** |

特别说明：宿主事先**确实**有可访问的 SQLite 文件，也创建了 world-readable 的 Secret 哨兵文件。最后一次修订后使用 **O_RDONLY** 单独检查数据库和密钥不可读，不再把“只读文件不允许 O_RDWR”误报告成“完全无法读取”。同时用可信宿主 SQL 只读检查 DB、Receipts、Events、资源哈希及 app-b 无副作用作为独立观察。

Docker 参数与测试插件的观测都是受控实验的证据；并不等于对任意恶意插件实现、Linux 内核漏洞、逃逸攻击或生产多租户强隔离做了形式化安全证明。

## 4. 真正可以继续工作的插件写入通道

[plugin_isolation.py](../../experiments/g1-b01-b6/plugin_isolation.py) 运行于**容器外可信进程**，持有随机 Bearer Token，将某个固定 app-a/plugin ID 映射到 B5 Tool Broker 中实际 Actor：

~~~text
容器内部一般 Python 插件：
  可以访问自己的临时只读 /workspace、计算和输出 JSON
  不可访问 host DB / Docker Socket / 网络 / Token
           │
           │ JSON 一次提议；不可信 request 中的 app/actor/tool/args
           ▼
可信宿主 Tool Relay（Token 仅此处可见）
  校验协议 envelope、字节限制、应用归属、路径和工具名
           │
           │ 携宿主保存的短时 Plugin 专属 Token
           ▼
B5 HTTP v3 /apps/app-a/tools/<allowlisted>
  服务器端 Actor=SandboxedViewPlugin, kinds=(view,)
           │
           ├─ 非 view Model / 代码 stage / 发布 / SQL：admin → 403/422
           │
           └─ view metadata.upsert → B2 SchemaStore.mutate
                     │
                     └─ 单一 SQLite 事务：CAS + Receipt + Audit
~~~

容器不是直接访问监听在宿主本地环回口的 Broker（它无网络）；宿主 Relay 是一次 JSON 负载出站调停，而不是向不可信插件转发 HTTP Token、管理员凭据或 Docker socket。这个方案强调**跨 OS 信任边界**，而不是仅靠 prompt/工具 SDK 声称插件遵从权限。

## 5. 32 个真实端到端检查的证据要点

- **B6-01—05**：本次 Docker 参数正向核查、可信宿主真实 SQLite/世界可读 Secret 存在、容器内 DB（读/写）、Socket、外网、密钥等全部拒绝，插件仍能提出由宿主转发的 `draft.read`，实际 HTTP 200。
- **B6-06—11**：容器向 Host Relay 请求 `sql.admin`/代码 Stage/App Publish 被拒绝 **403**；请求中声明 `app-b` 被独立跨应用边界 **403**；虚构 actorId 字段或破坏协议字段被 **422 或宿主协议拒绝**，两应用物理 revision 无越权变更。
- **B6-12—17**：Agent 以既有 B5 Broker 创建 Model；恶意容器请求 Model 元数据更新收到 **403 KIND_FORBIDDEN**；容器插件实际通过可信 Host Relay 创建 View **HTTP 200**；同 changeId 二次请求返回 `replayed:true`，审计和收据数量均不增加；Agent 继续创建 Form/Workflow 后 B2 四个资源完整，app-b 保持 0 资源、0 Audit。
- **B6-18—21**：真实 Chromium 浏览器未经登录跳转，登录后用旧草稿编辑 View；此时 Docker 插件成功修改该 View，浏览器旧版本 POST 得到 **409**，物理 SQL 保留插件结果；人类模拟操作重新加载并正常修改 Form。
- **B6-22**：故意把第一次成功的工具回复当作丢失，不使用新 changeId 自动重试，而是用相同 Actor、同一命令和 changeId 再请求；B2 返回原回执 `replayed:true`，物理 Audit/Receipt 不增长。这**只是本地响应丢失模拟**，不是已经验证真实远端 API 超时或外部副作用补偿，正式 W20 仍未通过。
- **B6-23—26**：模拟授权人工通过实际 Chromium 发布 B2 v1，真实表单创建 2 条 SQLite 合同记录，Workflow 超阈值合同经 `PendingLevel1 → PendingLevel2 → Approved`，浏览器实际展示插件最终 View 标题及 2 条记录。
- **B6-27—30**：不可信 Docker 插件依然不能 Stage 自定义代码（403）；可信宿主人工模拟主体重新在真正 B4 Docker 中运行完整 **432 组**业务 Oracle，Stage/发布后真实风险评分 95；撤销插件 Token 再启动容器访问工具收到 **401**，正常受权 Runtime 评分仍 95。
- **B6-31**：独立 SQLite 证明 app-a 有与插件身份匹配的审计、Schema/Code 哈希真实一致、app-b revision 仍为 0；未出现伪造管理员的 Audit。
- **B6-32：危险负对照，必须保留**。另一个确实拥有宿主 DB 权限的**受信测试进程**通过原生 SQLite 直接改写已验证的 Code Artifact `source`，该**物理篡改真实成功**；之后受权 Runtime 检测 `ARTIFACT_HASH_DRIFT` 返回 HTTP **409**。说明 Docker 插件受限并不代表整个宿主系统已经阻止所有旁路写入。

## 6. 研究判断、风险与下一任务

### 本轮正向结论（限定）

**在禁止 Docker Socket/宿主数据库挂载、关闭网络、使用非 root/只读/丢弃 capabilities 的固定 Python 容器条件下，不可信测试插件确实无法直接打开真实宿主 SQLite、Secret 和 Docker Socket，而受治理的 View 变更仍能够通过独立 Host Relay + v3 Broker 完成，并通过浏览器、审计和物理数据库一致性验证。**

相比 B5 的“仅进程隔离 + API 授权”，B6 提供了**真正 OS 隔离的正向、可复现证据**。用户软件平台能把插件从能够直接触及数据库的主体，降级为只能发出有限命令的主体，这是可落地架构线索。

### 尚未解决的关键风险

1. **宿主特权进程**仍能直接操作 B2/B4 SQLite，不能消除 Saltcorn 原生 Field.update、Pack 导入/CLI、扩展进程有权连接数据库的独立写通道；B6-32 主动复现此缺陷。
2. Docker Engine 安全依赖宿主系统、容器 runtime 默认 seccomp、镜像供应链，B6 只固定本次运行的 image ID，尚未做可信签名/digest 永久锁定、容器逃逸安全审计、AppArmor/SELinux、gVisor/Firecracker 或 Kubernetes Pod Security。
3. **真实第三方插件系统**（Saltcorn/NocoBase/ToolJet）的原生安装入口、插件声明与依赖、热加载、进程生命周期、扩展接口及插件代码替换机制未在本研究中强制接入该 Docker Host Relay。B6 是自有框架中的研究型 untrusted Python fixture。
4. 单次 stdout → Host Tool Relay 不是持续交互 SDK；没有通用流式 IPC、超时后的未知提交判定/去重协议、独立插件容器可用性、镜像发布与变更审计闭环。
5. 插件可能利用服务端 API 合法但权限过宽而取得比应有范围多的业务数据；当前 `draft.read` 允许查看同一 App 的全部 Draft，仍需更细粒度读权限与数据脱敏。
6. B2 元数据发布与 B4 Code 发布当前仍是两个版本指针：错误绑定会 fail-closed 409，但尚未实现应用+代码+流程一体化事务快照和已发生外部业务副作用的补偿。

### 最终 G1 门禁判断

- S1 仍为 **IN_PROGRESS**，正式 G1 **NOT_PASSED**。
- G1-B01 仍为 **PARTIALLY VALIDATED / OPEN**。
- 冻结 W01—W24 **0/24 FULL PASS**；冻结合同 TC01—TC18 **0/18 FULL PASS**。本轮 B6-01—32 **32/32 PASS 不替代正式验收**。
- 下一优先事项：**真正的宿主写边界收敛**。研究把数据库访问集中至独立服务进程，把第三方原生 Field/Pack/CLI 的 DB 访问全部禁用或隔离，并基于“原生 CLI 仍可绕过”的真实 C2 负对照衡量维护代价；随后补齐 W11、W16、W20、W24 的冻结测试及应用+代码发布快照跨域一致性。若任何真实低代码平台不能提供可强制拦截的写入口，应研究自建受控 Domain Kernel 而不是继续扩展外围 Broker。
