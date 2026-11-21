# S1 B6：真正运行在 Docker 中的低权限插件——禁止直接访问数据库、Docker Socket、宿主密钥与网络

> **仅为研究验证，不是生产安全认证。** 本次围绕前序 B5-28 的实际 P0 负对照：带特权 SQLite 连接的宿主进程仍可越过 Tool Broker 直接篡改已验证 Code Artifact；本轮新增一个真正**无宿主写权限、无 DB 挂载、无 Docker Socket 挂载、无网络**的 untrusted Python Plugin Docker 运行场景，验证其实际进程无法读取或修改敏感宿主资源，但可以通过**宿主独占凭据的 Typed Tool Relay** 请求有限编辑。

## 1. 威胁模型

### 受保护资产

- 权威 B2 SQLite `authority.sqlite`（包含 DataModel、Form、View、Workflow、变更回执及审计事件）；
- B4 已审查/已发布的自定义代码 Artifact、B2 Manifest 与当前发布指针；
- Docker Engine Socket `/var/run/docker.sock`；
- 宿主上存储的临时明文测试 Secret 文件和环境变量；
- app-b 的独立资源、审计、数据记录；
- 只允许 B5 v3 tool Broker 作为插件**元数据写入入口**。

### 攻击者能力与限制

- 攻击者控制 Docker 容器内的 Python 代码和请求 JSON，可发起恶意 `sql.admin`、`code.stage`、`app.publish`、虚构 `actorId` 和 `app-b` 请求；
- 攻击者尝试以 Python sqlite3 打开真实宿主数据库、用 `O_RDWR` 打开宿主文件、连接 Docker Socket、连接互联网 1.1.1.1:443、读取宿主 secret 环境变量和写入自己的挂载文件；
- 攻击者**没有**宿主文件/数据库挂载、`--privileged`、网络、Docker socket、Broker bearer、宿主密钥、容器 Root/Capabilities；
- 有权限的宿主进程及 Docker 管理员**不在本次被成功隔离的攻击者范围内**；实验结尾保留可信宿主直接 `UPDATE extension_artifacts` 的反证并验证运行时 SHA 409。

## 2. 真实 Docker 约束

实验每次执行不受信插件进程，调用本次预先拉取并记录不可变 image ID 的 `python:3.13-alpine`：

```text
docker run --rm --pull=never
  --network=none --read-only --cap-drop=ALL
  --security-opt=no-new-privileges
  --pids-limit=32 --memory=192m --cpus=1
  --user=65534:65534
  --tmpfs /tmp:rw,nosuid,nodev,noexec,size=8m
  --mount type=bind,src=<临时仅含两份 JSON/Python 的目录>,dst=/workspace,readonly
  --workdir /workspace --entrypoint python3
  <本次镜像不可变 sha256 ID> -I -B /workspace/plugin_untrusted.py
```

**不得**挂载宿主源码、应用 SQLite、密钥、GitHub checkout、`/var/run/docker.sock` 或给 untrusted Plugin 自己的网络。容器中 untrusted Python 运行真实 `sqlite3.connect`、`os.open`、`socket(AF_UNIX)`、`socket(AF_INET)` 拒绝情况；独立可信进程从 SQLite 物理结果以及 Docker 参数两侧复核该结论。

## 3. 唯一受治理通道

`plugin_isolation.py` 是**宿主可信组件**，在 Docker 外暂时为每个插件注册随机 Token，持有实际 B5 `ToolBroker` 身份映射。插件 Docker 不可见 Token，只能向可信宿主标准输出提出**一次** schema 验证后的工具请求；可信宿主用自己的 Token 通过 `127.0.0.1` 的 B5 v3 HTTP Tool API 发送请求，**不把请求里的 app/actorId 作为真正身份**。Broker 再使用 B2 `SchemaStore.mutate` 内核执行授权、版本 CAS、幂等、SQLite 事务和 Audit。无授权命令或者跨 app 请求都被拒绝。

该 stdio → Host Relay → 受信 HTTP Tool Broker 只是**一次请求/一个容器**研究协议，不是完整的插件 SDK 或持续交互/调试服务。运行中的 Plugin stdout 内容仍是不可信数据；实际安全决定在 Broker 和独立物理数据库观察，不依赖插件自我报告“已隔离”。

## 4. 实际接受路径

- 宿主可访问该 SQLite 与 world-readable 测试密钥文件，但是无挂载容器不能读取同一路径。
- 插件用真实受限 Docker 实际请求 B2 Draft，宿主专属工具 Token 才能把请求送到 B5 Broker；独立 SQLite 无越权修改。
- 插件试图请求 SQL、代码发布或 App 发布以及跨 app/虚构 Actor 时拒绝，未产生 Audit/数据副作用。
- Agent 以正常 v3 tool 建 Model/Form/Workflow；容器插件凭 `kinds=("view",)` 只可建立/修改 `view.contracts`，非 `model` 类型写入返回 403。
- 同 changeId/revision 的插件请求重放返回首次回执 `replayed=true`，物理 Audit 与 Receipt 不增。
- 真 Chromium 模拟受权人工先读旧 View，再由隔离插件修改 View，网页后续用旧 context 保存返回 409，保留插件结果；网页重新加载后能够独立保存 Form。
- 故意丢弃一次已经提交成功的工具回复，再按**同一个 changeId 和同一请求**恢复回执，验证无新 DB 副作用。这只是本地回复丢失模拟，不等于外部系统超时未知结果或完整 W20。
- 浏览器人类模拟审核后真正发布 B2 Manifest；表单写入真实合同、Workflow 大额需要二级审批、实际 Chromium 看 View，说明系统隔离后可继续正常使用。
- Plugin 提交代码构建/发布请求仍 403；受信模拟人类才可以用 B4 Docker 通过 432 组 Oracle 后发布；合同风险评分 95。
- 插件 Token 撤销后插件容器无法继续请求工具，而人工已发布合同运行态不受影响。
- **负对照：拥有 DB 权限的可信宿主**仍能直接改写 Artifact，B4 仅在下次调用发现 SHA 错误并 409；不能以此称“所有实际写入口已统一”。

## 5. 目录

| 文件 | 内容 |
|---|---|
| `plugin_untrusted.py` | **不可信、真实在容器内执行**的攻击载荷：文件、SQLite、Unix Socket、TCP、Secret/挂载权限；只输出 JSON 工具请求 |
| `plugin_isolation.py` | 可信宿主侧 Docker 启动约束、最小挂载、精确 JSON 协议、App scope 检查、凭据不暴露和只通本地 B5 HTTP Typed Broker |
| `test_isolation.py` | 不运行 Docker 的受信启动参数、协议注入和隔离判定单元测试 |
| `experiment.py` | 真 SQLite、Chromium、Docker plugin、Host tool relay、B2/B4 业务与特权宿主负对照 |
| `.github/workflows/s1-b6-plugin-isolation.yml` | GitHub Ubuntu 24.04 + Python 3.13 + Docker + Playwright/Chromium；先 B6+B2+B4+B5 回归后跑真实隔离检查；**完全不需要 DeepSeek** |

## 6. 运行

本机需 Python 3.13、Docker、Playwright 1.56、可安装 Chromium。禁止在具有生产密钥/数据库访问权限的环境尝试第三方不可信插件：

```bash
cd experiments/g1-b01-b6
python3 -m unittest -v test_isolation
docker pull python:3.13-alpine
export S1_B4_IMAGE_ID="$(docker image inspect python:3.13-alpine --format '{{.Id}}')"
python3 -m playwright install --with-deps chromium
python3 experiment.py --output /tmp/s1-b6-evidence.json
```

## 7. 决策与尚未完成的范围

**本轮若通过，仅支持这样的窄结论**：对于测试中的受限制、无额外宿主挂载/网卡和未授予系统特权的 Docker 插件，源代码可执行但不能直接接触真实宿主 SQLite、Docker Socket、宿主密钥或外部网络；允许的元数据编辑通过可信 Host Relay 和 B5 Broker 原子写入，而非直接 DB 写入。

**尚无法称正式 G1 已通过**：攻击者可能有容器内核漏洞、供应链污染、容器逃逸、Docker 管理员、宿主代码被污染、插件安装阶段特权、Saltcorn 原生 Field/Pack/CLI 写通道、外部系统未知结果、生产多节点及实际业务授权等。尤其本试验中的 Python 插件载荷是专用研究 fixtures，并不是 Saltcorn/NocoBase/ToolJet 真正原生第三方插件生态。无需重复调用 DeepSeek。正式冻结 G1-B01 **W01—W24 仍 0/24 FULL PASS，TC01—TC18 仍 0/18 FULL PASS**；S1 **IN_PROGRESS**，G1 **NOT_PASSED**。
