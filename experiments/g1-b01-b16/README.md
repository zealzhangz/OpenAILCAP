# S1 B16：Native Web / Apply 真实 UID 分离与只读运行可证伪实验

## 问题与预注册判据

B15 已隔离独立发布快照的写权限，但 Saltcorn Web 仍拥有自己的派生数据库。
本轮只回答一个问题：**不修改 Saltcorn 1.7.0-beta.5 源码，能否让独立 Web UID
只读真实 Native SQLite，且仍能启动和显示合同列表？**

实验独立于 B15 累计夹具：使用同一版本及原生合同 Pack，但合同是合成 fixture，
没有接入 B2 权威签名事件、B15 Router 或 Netfilter，不宣称组合方案已验证。
不调用大模型，不读 DEEPSEEK_KEY。未修改前序实验或门禁标准。

| 对照 | 身份/数据权限 | 预先固定的判断 |
|---|---|---|
| 可写基线 | Apply UID 拥有 Native SQLite | HTTP 与真正 Chromium 必须显示合同，否则实验无效 |
| 默认只读 | Web UID 只有组读权限，目录不可写 | 记录启动/HTTP；失败须有 SQLITE_READONLY/CANTOPEN 证据，不能将任意超时算作负面结论 |
| Session 分离 | 同上，--nomigrate；Session 符号链接指向 Web 自有目录 | 记录是否解决启动；若仍失败必须有 SQLITE_READONLY；不修改上游源文件 |
| Apply 后重启 | Apply UID 更新合同，Web UID 重启 | 独立 SQL 读回新值；记录 HTTP 或明确只读启动失败，不能宣称已实现在线更新 |
| 故意错误目录权限 | Apply-owned 0640 文件放入 Web-owned 目录 | 实测 Web 替换成功是**危险负对照**，不是安全通过 |

18 项检查包括：真实非 root UID、原生表创建、可写 Chromium 基线、Web SQL 读取、
真实 O_WRONLY/SQL UPDATE/chmod/unlink/replace 拒绝、原生 Saltcorn CLI SQL 写入拒绝、
默认只读启动、独立文件 SHA256 不变、Session 写入、关闭迁移后启动、Apply 写入及重启、
可写父目录负对照。**18/18 即使成立，也不等于只读 Web 可用**：必须另外读取
`unmodifiedReadonlyWebFeasible` 与各 variant 的 HTTP/Chromium 结果。

## 权限和边界

- Apply 和 Web 两个不同系统用户，均非 root，共享只读组。
- 数据目录 Apply-owned 0750、Native SQLite Apply-owned 0640。
- Web 自有 0750 HOME 可写；Session 链接由受信 Controller 建立，Native 数据目录始终不可写。
- Apply 在初始化/基线阶段拥有正常 Native 写权限；所有服务都在降权之后才打开 SQLite，
  不继承初始化阶段的可写数据库句柄。
- 实验仅含合成公开合同，不涉及真实用户/业务信息。SQLite 全库包含原生元数据，
  **不是 B15 的最小公开快照，不证明敏感列保密、多租户或用户 ACL**。
- 不涵盖 root、同 UID 进程、可写代码目录、其他网络入口、插件隔离、WAL/高并发、
  热替换/缓存一致性、生产全站运行及 B15 端到端集成。
- 只读启动失败时保留失败事实，不能为使检查变绿给 Web 恢复数据写权限。

## 复现

见 [专用 Actions](../../.github/workflows/s1-b16-readonly-native-web.yml)：Ubuntu24.04、
Node24、Saltcorn CLI1.7.0-beta.5、Python3.13、Playwright1.56.0 Chromium。
需要受信控制器具备 sudo，普通 Web/Apply 进程没有 sudo 权限。

```sh
python3 experiments/g1-b01-b16/inspect_upstream.py /tmp/s1-b16-evidence/upstream
python3 -u experiments/g1-b01-b16/experiment.py --output /tmp/s1-b16-evidence/results.json
```

`inspect_upstream.py` 保存实际安装版本、上游文件 SHA256、定位行号及文件副本。
`results.json` 保存每一检查、HTTP/Chromium、退出状态、日志哈希及技术可行性判定；
`b16-logs/` 保存原生启动失败与 CLI 写入拒绝日志。临时研究进程组会终止并清理。

**执行状态：待真实 CI；不能把已编写的检查称为通过。**

正式门禁保持：S1 IN_PROGRESS / G1 NOT_PASSED / G1-B01 PARTIALLY VALIDATED / OPEN；
W01—W24 0/24 FULL PASS，TC01—TC18 0/18 FULL PASS。
