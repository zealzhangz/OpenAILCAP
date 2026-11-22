# G1 P0-A：真正无网络 Docker Plugin 与人工/Agent/原生 Saltcorn 同实例联合验收（预注册）

**门禁预期：G1 NOT_PASSED；W01—W24 0/24 FULL PASS；TC01—TC18 0/18 FULL PASS。**

本次不将之前 B6 Docker 隔离证据与 B9 Saltcorn 证据相加，而是将 **B6 真正不可信 Python 插件容器的安全边界、B6 可信 stdout → Host Tool Relay** **直接嵌入 B9 已经运行的** B2 Domain Kernel + B5 Broker + authority.sqlite + 独立 Agent + 真实登录 Chromium + 已发布 Saltcorn v1 Native 实例。

## 真实实现

- 主程序：\`experiments/g1-b01-b9/experiment.py\`，**不重置现有 Kernel、不新增权威数据库/测试用户**；在前 51 项人工-Plugin-Agent 集成用例执行结束、权威 revision=12、Native 仍发布 v1 的前提下执行以下 9 项。
- 新测试：\`experiments/g1-b01-b9/p0a_docker_suite.py\` 直接复用 \`g1-b01-b6/plugin_isolation.py\` 的 \`DockerPlugin\`，容器内代码仍为 \`g1-b01-b6/plugin_untrusted.py\`。
- Ubuntu 24.04 GitHub Runner 真正 pull \`python:3.13-alpine\`，\`docker inspect\` 得到实际 \`sha256:…\` **image ID，单次工作流始终使用该 ID，\`--pull=never\`**。注意 registry tag 不是跨日期固定 digest；这只能保证本次运行锁定，不可宣称整个供应链已签名。
- 容器 \`--network=none --read-only --cap-drop=ALL --security-opt=no-new-privileges --pids-limit=32 --memory=192m --cpus=1 --user=65534:65534\`；只挂一份隔离 \`/workspace\` 的请求 JSON/Python。既不把权威 DB/Saltcorn runtime/源码树/Docker Socket 挂入，也不传入任何 B5 Token；只由可信宿主根据固定 Plugin Actor 身份向 B5 v3 命令入口提交工具操作。
- 仍然使用 B9 原有独立 **Kernel UID 下物理 SQLite SQL Oracle**、Native UID 下 SQLite Oracle、真实 Chrome DOM、Chrome POST HTTP、真实 B5 CAS/Receipt/Event；源码不能直接读取 0700 权威私有文件，且容器探测不代替物理审计。

## 冻结用例映射（全部只属于 partial_evidence）

| 局部 ID | 真实操作 | 可证伪条件 | 对应冻结缺口 |
|---|---|---|---|
| P0A-16 | 真实 Docker image ID/固定 SHA、CLI 安全选项校验 | no-network、read-only、非 root、no capabilities、无 secret/DB mount，失败时停止 | W16 |
| P0A-17 | 容器内 sqlite/open/docker.sock/TCP 旁路攻击 + app-a draft.read | 真容器的 UID 65534、实际拒绝，受权 B5 200 且权威物理数据库不变 | W01/W14/W16 |
| P0A-18 | 容器申请 app.publish、code.publish、sql.admin、Model 写入 | 四种 HTTP 403，独立 SQL 全量不变 | W14/W16/TC17 |
| P0A-19 | 容器声称操作 app-b，args 内伪造 actorId/role/appId | app-b 拒绝 403、注入参数拒绝 422，审计无新增 | W13/W21 |
| P0A-20 | Docker Plugin 真实修改 app-a View title | 单次 B5 CAS 成功 200，内核独立 SQL +1 revision/receipt/event，actor 来自宿主 Grant | W01/W16 |
| P0A-21 | 真 Docker Plugin OS 进程与 Agent 并行提交同 revision 不同 title | 恰有一 HTTP 200、一 409，独立 SQL 一笔成功、物理胜者保留 | W06/W07 |
| P0A-22 | 较新业务修改后 Docker 同 changeId 重放；Agent 冒用 / Docker 修改摘要 | Docker 重放 200/replayed，冒用各 409；物理 SQL 零增量 | W08/W09 |
| P0A-23 | 真 Chrome 持旧 Web 草稿，Docker 插件实际更改后 Web 保存 | Docker 200、真 Web POST 409，最终物理 title 是插件新值 | W02/W03/W14 |
| P0A-24 | 同 Kernel 物理全量审计、已发布 Native SQLite/Chrome HTML | 本轮 exactly 3 个有效 mutation，版本、receipt、event +3；Native v1 物理快照完全不变；app-b 无变化 | W11/W17 |

## 冻结口径、拒绝推断与退出条件

该集成能支撑**“真实沙箱 Plugin 可与 Human 和 Agent 经统一授权工具同实例写入”这一局部设计路线**，但容器隔离不等于真实插件安装/发现/撤销机制，不覆盖 Docker 宿主管理员、容器逃逸、镜像供应链，不证明生产多租户、OIDC/SSO 或超时 UNKNOWN 事务处理。Docker 不可信输出的每项探测必须连同宿主工具调用真实 HTTP 与**独立物理 SQL**核验，不能把它的自我报告当作安全证明。

同时 B9 Saltcorn 原生 **owner UID 可以自行修改可丢弃派生库**，本次无源权威写入；Native 未收到本轮未发布草稿。**这不是 Native 已完成发布原子热切换**，也未处理 Pack 全量差异审批、运行时同业务数据刷新、全量 Form/Workflow/B4 Code、签名新鲜度及外部补偿。

任何容器触及私有 DB/配置、未经授权写入权威 SQLite、跨 App 污染、两个同 revision 都成功或物理账本/Chrome 不一致均应直接失败/No-Go，不得自动重复生成新 changeId。预期 B9 36 + 第一轮 6 + 第二轮 9 + 本轮 9 = **60 个局部检查**，新增 B6 relay unit regression；无任何模型调用。

**只有真实 GitHub Actions 的成功运行及原始日志齐全后才可补写本文实测、追加冻结账本 partial_evidence。冻结的 42 个 case 状态不得因局部合格而自动改变。**


## 2026-11-22 真实 GitHub CI 结果

- **可重建代码 SHA：`ca3f8cf5db3c944a1a5fae8235b3a33e2ad0653b`**，[B9 同实例 Actions #44974547628](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44974547628) **completed/success**，Job **137061392720**，[原始 Artifact #14735390659](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44974547628/artifacts/14735390659)。原始 Artifact 同时保留所有 Docker/Chromium/CLI/物理 SQL 细节与新 B6 单测日志。
- **B9 36/36 + P0A-01—06 6/6 + P0A-07—15 9/9 + P0A-16—24 9/9 = 60/60 同一部署局部运行检查通过**；Saltcorn Pack 编译 25/25、B2 18/18、B5 40/40、B6 Docker Relay/Isolation Policy 25/25 单元回归通过。**模型调用 0 次。**
- **固定实际 Docker Image ID：**`sha256:67fd5f7b4b120eaa3308775fe87aff98a2492287576bd6656ef785d54a1b5605`。真实容器 `uid=65534`，尝试 host SQLite RW/read、宿主机密钥文件、Docker socket、互联网 1.1.1.1:443 全部拒绝；容器 read-only 不能写源文件；可信 Relay 持有且未向容器传递 Token。Plugin 对同一 authority.sqlite 的 B5 v3 draft.read 实际返回 200，**独立物理 SQL 不变**。
- **权限负例真实 HTTP：**Plugin 请求 app.publish、code.publish、sql.admin、model upsert 统一 403，跨 app-b 为 403，伪造 actor/role/app 由 Broker 拒绝 422；每项均以独立权威 SQL 数据/事件/回执无变化核对。
- **受限成功写入：**真正 Docker Plugin 的 View upsert 返回 200，**物理 revision 12→13，receipt/event +1，事件实际 actor=`p0a-native-plugin`**；不会调用 Saltcorn 的原生不可信写路由，也不会改动权威模型外的资源。
- **真实竞争：**同一旧 revision 下，真实 Docker Plugin 409、Agent 200，一条事务成功，物理 winner=`P0A-Agent-Race-Title`。第一次 Docker 成功的原 changeId 在更高 revision 后重放返回 200/replayed=true，Agent 冒用和不同哈希冒用各 409，物理无副作用。**只观察到本次 OS 调度顺序，不推断两种调度都覆盖。**
- **真实 Browser：**Chromium 登录设计器旧 revision，Docker 通过授权命令提交后浏览器 POST 409，独立 SQL 保留 Docker title。整个本轮恰有 3 个成功版本变更，revision 12→15，成功回执/事件各 +3；Saltcorn Native 已发布 v1 SQLite 原始物理快照相同，Chrome 合同仍可读取，app-b 未变化。
- **真实失败保留：**开发中的旧工作流 [Actions #44974537859](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44974537859) 因当时尚未添加 Docker 镜像固定注入，明确失败于 `P0A_DOCKER_IMAGE_ID_MISSING`；后续 commit 补全实际 Docker pull+inspect 和 `S1_B9_PINNED_DOCKER_IMAGE` 注入并重新执行通过。该历史失败是环境装配未完成，不能伪称首轮即成功。
- **门禁不变：G1 NOT_PASSED，W 0/24，TC 0/18 FULL PASS。** 真实 Docker 隔离已进入同实例证据，但插件生产安装/发现/撤销、系统级 Pack 差异批准、Native 真正无重启热发布与 B15/B17 新鲜度验证、全量 Code/Workflow/外部副作用回滚仍是实质阻断项。必须在同实例补齐，否则不能以此进入 G2。
