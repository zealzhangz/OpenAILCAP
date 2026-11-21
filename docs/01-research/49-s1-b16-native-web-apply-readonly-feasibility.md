# S1 研究报告 49：B16 Native Web / Apply 身份分离与只读启动可行性

研究日期：2026-11-22（北京时间）。**真实研究检查 18/18 符合预期；但未经修改的
Saltcorn 只读 Web 启动方案被否定。** 关闭迁移并分离 Session 后仍以
`SQLITE_READONLY` 退出，不能称为可运行的只读 Native Web。

## 一、研究问题与控制变量

[B15](48-s1-b15-host-firewall-atomic-public-snapshot-evidence.md) 已验证固定 Native
端口的主机网络入口控制和独立 Publisher 的最小公开快照，但 Saltcorn Web 和
Native Apply 仍以同一 UID 操作实时 SQLite。Web 被攻破后可直接写自己的数据库，
因此“Web 和 Apply 分离 OS 身份”是下一项需要证伪的候选机制。

B16 固定 Saltcorn CLI **1.7.0-beta.5**、原生合同 Pack、单进程启动、关闭 Scheduler、
单台 Ubuntu24.04，比较 Apply 可写基线和独立 Web 只读场景。
数据目录是 Apply-owned **0750**，SQLite 是 Apply-owned **0640**；Web 只有共享组读取权限。
数据库连接始终在进程降权后打开，避免从初始化进程继承可写文件描述符。

本轮是**独立兼容性实验**，使用合成合同；不运行 B15 的累计 148 项 E2E，不接入
B2 签名事件、Router、Netfilter，不重新计数或外推前序结论。大模型调用 **0 次**。

## 二、预注册判据

| 场景 | 观察方法 | 通过研究检查的含义 |
|---|---|---|
| Apply 可写基线 | 真正 Saltcorn HTTP + Playwright Chromium | 原生组件与夹具能正常工作 |
| Web 只读 | 独立 UID 的 SQL SELECT/O_WRONLY/UPDATE/chmod/unlink/replace | 证明真实 OS 文件与目录权限，不能只检查配置值 |
| Native CLI 绕过 | Web UID 调用真正 `saltcorn run-js` 的 SQL UPDATE | 原生 CLI 也无法写保护文件 |
| 默认 Web 启动 | 原生日志、退出状态、HTTP、Chromium（如服务可用） | 明确区分可用、只读错误和不明超时 |
| Session 分离并关闭迁移 | `--nomigrate`；Session 链接指向 Web 自有目录 | 检验已准备好数据库后能否消除启动写入依赖 |
| Apply 更新与 Web 重启 | SQL 读回、文件哈希、原生启动 | 不把离线更新自动写成在线刷新成功 |
| 可写父目录负对照 | Web 替换 Apply-owned 0640 的一次性副本 | 若替换成功，表示错误部署可绕过文件只读，不能当作安全通过 |

检查总数预设 **18**。`results.json` 的研究检查计数与
`unmodifiedReadonlyWebFeasible` 分开记录。**启动失败被正确复现也可以是研究检查 PASS，
但技术可行性必须是失败**。只有原生 HTTP 和真正 Chromium 都显示合同，才可称该限定列表可用。

## 三、上游调用链与证据定位

实际运行版本的完整路径、文件 SHA256 和源码行锚点由
[inspect_upstream.py](../../experiments/g1-b01-b16/inspect_upstream.py) 写入 CI Artifact
的 `upstream/manifest.json`；对应文件副本一同保存，避免只引用随时间变化的分支。

| 包/路径 | 需核对的行为 |
|---|---|
| `@saltcorn/cli/src/commands/serve.js` | `--nomigrate` 只传 `disableMigrate`；`--noscheduler` 只关闭调度 |
| `@saltcorn/server/dist/serve.js` | 启动调用 `initOfflineStoreCfg`，更新 `pre_installed_module_infos`；其位置在后续 `initMaster` 迁移判断之前 |
| `@saltcorn/server/dist/routes/utils.js` | Session 中间件调用 `db.getExpressSessionStore` |
| `@saltcorn/sqlite/dist/sqlite.js` | 业务 SQLite 默认连接；Session 默认路径为业务文件路径加 `-sessions.sqlite` |

这些是代码路径，不能单独证明现场失败原因；最终结论必须结合真实日志及正反对照。
不修改上游已安装源码，不用 monkeypatch、模拟 HTML 或给 Web 恢复数据写权限来使结果通过。

## 四、实测与结论

**[Actions #44930503580](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44930503580)
completed/success**，Job **136925849194**；
[原始 Artifact #14717746712](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44930503580/artifacts/14717746712)。
Artifact ZIP SHA256：`c757f68d6d110ddda4830a2b02c7d71dcbef2c8eaf56a2446182f405aa719117`。
代码提交 `3be426307c3de8736c9b0d04c5f8c552e4004c57`；Actions 实际检出的 PR merge
提交 `fba532a88d043ab5823aee2e7f61cd9b84b1b295`。报告及证据摘要是随后补充的文档，
没有重新执行或扩大前序 B15 结论。

仓库内保留 [ci-observations.json](../../experiments/g1-b01-b16/ci-observations.json)，
明确标记为从 Job 日志解析的摘要，包含全部 18 条观察、4 种运行结果及上游源码哈希；
完整 `results.json`、启动/CLI 日志和安装源码副本在原始 Artifact。

| 实测项目 | 结果 | 含义 |
|---|---|---|
| 两个非 root UID | Apply **999**，Web **997**，共享只读组 **986** | 身份确实分离 |
| Apply 可写基线 | 原生 HTTP **200**，真正 Chromium 显示合同 | 版本和夹具可正常运行 |
| Web 直接读 SQL | 成功读到 `S1 Platform Contract` | Web 有读权限 |
| Web O_WRONLY / SQL UPDATE | PermissionError / SQLITE_READONLY | 直接写被拒绝 |
| Web chmod / unlink / replace | errno **1 / 13 / 13** | 不能改权限、删除或替换受保护文件 |
| 真正 Saltcorn CLI SQL UPDATE | exit **1**，SQLITE_READONLY | 原生 CLI 同样不能绕过 OS 数据写限制 |
| 默认只读 Web 启动 | exit **1**，无可用 HTTP，SQLITE_READONLY | 未运行到可服务阶段 |
| 可写 Session + --nomigrate | exit **1**，无可用 HTTP，同一错误 | 此组合仍不能解决启动写入 |
| Apply 更新 | 独立 SQL 读回 `Apply UID controlled update` | Apply 保留合法写权限 |
| Web 更新后重启 | exit **1**，同一错误，数据库哈希不变 | 不存在可证明的只读网页刷新 |
| 故意放宽父目录权限 | Web 成功替换 Apply-owned 0640 副本 | **危险反例**：只保护文件不保护目录不够 |

Web 攻击和两次启动前后的完整数据库 SHA256 均为
`f37573ad2a690373fabc2aff80de18cf44b1ca5dcea8510a637397d9add248cc`。
这证明该顺序实验内没有写成功；不代表并发/WAL/生产所有攻击面已验证。

三次只读启动均保留以下真实错误，退出码均为 **1**：

```text
Unable to read pre_installed_module_infos: SQLITE_READONLY: attempt to write a readonly database
    Error: SQLITE_READONLY: attempt to write a readonly database
    Code: SQLITE_READONLY
```

失败定位与实际安装源码相符：`server/dist/serve.js:535` 在后续迁移判断前调用
`initOfflineStoreCfg()`；第359行更新配置，异常处理在第367行再次尝试写配置。
所以 `--nomigrate` 没有跳过这条启动写路径。该文件 SHA256 为
`8cac7fb41f671d831e3086ee2b481c92368350bd736bca9faae00fa0a626b0e0`。
**当前直接阻断点是启动配置写入；Session 路径只是另一个待验证依赖。** 本轮只证明
单独 Session 文件可写，没有运行到真正 Saltcorn Session 生命周期，不能声称 Session 集成通过。

首次专用 CI 即成功完成全部预注册观察，无夹具修复重跑。
其中包括 **3 次实际原生启动失败**和 **1 次危险目录配置反例**；这些失败事实被保留，
CI 绿色仅表示实验完成，**不是**“Saltcorn 只读运行通过”。

## 五、边界和后续决策

1. **UID 权限隔离与运行时兼容性是两个不同问题**。权限拒绝成立不意味着原生服务能够启动。
2. 共享组可读的是完整原生 SQLite，包含元数据；这不是 B15 最小公开快照，不能视作敏感信息隔离。
3. 不涵盖登录/完整 Session 生命周期、全站路由、插件、租户 ACL、并发/WAL、快照热替换、缓存更新、生产 HA。
4. 只读启动已失败，下一步应比较两条路线：维护明确的原生只读运行模式并剥离所有启动/Session/元数据写入；
   或由受控只读渲染器直接消费 B15 最小公开快照，将 Saltcorn 保留为设计/研究参考。
   这两条均是候选，不在缺少运行证据时直接确定技术栈。
5. 不再靠增加成功断言扩大结论。下一项应围绕失败根因、改造成本及冻结门禁映射开展。

**被否定的具体方案**：对该版本直接分离 UID、将整个 Native SQLite 设为 Web 只读，
再加 `--nomigrate` 和可写 Session，即可不改上游运行合同列表。不能将本结论扩大为
“Saltcorn 永远不能只读运行”，也不能凭这一次失败直接确定 OpenAILCAP 最终技术栈。

**建议 B17 的最小范围**：先比较“有明确维护成本的只读适配”与“直接读取 B15 公开快照的
最小受控渲染器”。使用同一四列公开合同、同一独立写入者/只读 Web 权限和浏览器验收，
同时验证原生代码/元数据写入是否真正被隔离；记录修改上游的数量、运行依赖和不能复用的能力。
任一路线仅显示静态页面都不算正式 G1 通过，需继续映射冻结验收项。

**正式状态不变：S1 IN_PROGRESS / G1 NOT_PASSED / G1-B01 PARTIALLY VALIDATED / OPEN；
W01—W24 0/24 FULL PASS，TC01—TC18 0/18 FULL PASS。**

工程：[B16 README](../../experiments/g1-b01-b16/README.md)；
[实验控制器](../../experiments/g1-b01-b16/experiment.py)；
[降权进程助手](../../experiments/g1-b01-b16/worker.py)；
[专用 CI](../../.github/workflows/s1-b16-readonly-native-web.yml)；
[PR #18](https://github.com/zealzhangz/OpenAILCAP/pull/18)。
