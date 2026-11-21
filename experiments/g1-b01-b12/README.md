# S1 B12：真实后台投影消费者的崩溃恢复、源 HTTP 中断与 Native 派生漂移巡检

> **研究实验，不是生产方案。** B11 由受信 CI Controller 手动调用 `sync_native`，B12 增加**真实独立长期运行的 Python 消费者进程**，自动轮询 B2 权威 Outbox，读取**真正 Saltcorn SQLite 已提交的持久游标**，以独立 Saltcorn Linux UID 调用 B11 原子事务消费器。B12 复用 B11 的 62 项真实 E2E，新增 17 项，要求 **79/79**。不调用 DeepSeek。

## 架构与身份边界

```text
B2 Kernel UID 999: SQLite records + trigger Outbox seq1..N
  │  POST /v4/apps/app-a/projection/pull 只读，独立 projectionToken
  ▼
Trusted CI-runner Consumer daemon (单独真实进程)
  ├─ 私有 0600 config（Bearer token，不交给 Saltcorn）
  ├─ 每 180ms：
  │   ├─ sudo runuser -u Saltcorn UID → 只读 audit_native.py
  │   ├─ sudo runuser -u Saltcorn UID → 只读 native_checkpoint.py
  │   ├─ 从 B2 Outbox 按 cursor 拉取最多 20 条真实事件
  │   └─ sudo runuser -u Saltcorn UID → native_apply.py
  │       stdin ONLY 事件 JSON，真实 Saltcorn SQLite 一次事务提交
  └─ 私有 0600 status（cursor/head/lag/failures，无 token）
  ▼
Saltcorn UID 997: 可删派生 SQLite
  ├─ s1_contracts
  ├─ b11_record_map + receipts + durable cursor
  └─ 原生 Saltcorn HTTP / Chromium 只读列表
```

**必须明确**：消费者在 CI Runner 身份运行，该身份可 `sudo -n runuser` 到 Saltcorn UID，属于**实验编排权限**，不是经过正式 OS 最小权限授权的生产后台服务。生产需独立受信 Consumer UID + 受控 IPC/执行代理、持久认证和受限网络。Native SQLite 的 cursor 是唯一提交 checkpoint；消费者进程**不另存超前游标**，SIGKILL 后从 Native 已提交 cursor 恢复。

## 真实故障注入与证据范围

- B12-63—64：B11 两份已批准合同 Outbox seq1..8、Saltcorn v1 Native cursor8 时，启动独立后台 daemon，自动读取 Native cursor8 并处于 `CAUGHT_UP`。Native UID 尝试 `open(O_RDONLY)` 消费者 0600 Token 配置，必须 `PermissionError`；状态文件无 Token。
- B12-65—66：daemon 在线时，B2 真实创建并两级批准第三份合同，后台自动消费 seq9..12，无需 Controller 手动 sync，真实 Saltcorn HTTP 和 Router 显示第三份合同。
- B12-67—70：**真正 SIGKILL daemon**，Saltcorn 仍在线；B2 创建第四份已批准合同，源 Outbox 到 seq16，但 Native cursor 停在12；重启新的 daemon 进程，必须从 Native SQLite cursor12 自动追赶到16，合同4条、Receipt16条、无重复。
- B12-71—74：通过真实本机 HTTP proxy 向**消费者**返回 **503**（不停止 B2 Kernel），B2 同时真实创建第五份合同，源 Outbox seq20，Native cursor16；恢复 proxy 后 daemon 自动追赶到20，Native/Router HTTP 显示第五份合同。
- B12-75—77：Saltcorn UID **真实 SQL 篡改**第五份合同标题，后台即使没有新源事件也通过**全量 record_map hash/Receipt 连续性巡检**发现 `DERIVED_DRIFT`；此时 cursor 不变、Consumer 停止消费。**负对照**：直接访问 Native HTTP 仍可能看到篡改值，证明**尚未实现读取前拦截**；以 Saltcorn UID 手动恢复派生行后，后台恢复 `CAUGHT_UP`，但这**不是自动修复**。
- B12-78—79：独立 B2 SQL Oracle 仍有 **20 条事件、5 份 Approved 合同、App B 不变**；真实 Chromium 通过已回滚至 v1 的 Router 看到第五份合同。
- B11-01—62：仍在本轮 CI 中以 B12 三个真实 Linux UID 和 B12 独立临时目录重新执行，而非仅调用单元 mock。B12 单元 22 条，B11 Outbox 单元 28 条，B10 Router 34、B2 18、B5 40 回归。

## 明确尚未验证/尚未实现

1. 没有正式后台服务管理器（systemd/K8s）、多实例 Leader Election、持久 Consumer 状态服务、TLS/mTLS、跨主机签名或凭证轮换；实验 Consumer 由 sudo-capable CI runner 启动。
2. HTTP 503 模拟的是**真实 HTTP 请求失败**，不是 Linux 网络分区/断电/跨机故障。SIGKILL 测试的是消费者进程，不是数据库存储设备断电或 SQLite WAL 断电恢复。
3. 漂移检测是**定期巡检**，**未在原生 HTTP 读取前 fail-closed**；同一 Saltcorn UID 可以直接篡改派生 DB、暴露污染值，不能宣称业务数据完整性防护通过。
4. 投影只覆盖 `app-a/model.contracts` 的插入与更新、四列无 PII 合同数据，不具备多租户行级 ACL/脱敏、Delete、Schema Migration、通用 CDC、死信队列、跨版本字段映射。
5. Router 仍为 B10 单实例内存 CAS，Native v2 故障时仍返回 503；不是生产零停机/HA，也不是完整 Saltcorn Form/Workflow/Code 语义等价。
6. **正式门禁仍为 S1 IN_PROGRESS、G1 NOT_PASSED、G1-B01 OPEN；冻结 W01—W24 0/24 FULL PASS，TC01—TC18 0/18 FULL PASS**。即使本实验所有专项检查通过，也不能自动升级正式冻结验收。

## 复现

```bash
# GitHub Actions Ubuntu24.04 / Node24 / Saltcorn CLI1.7.0-beta.5
# Python3.13 / playwright1.56 Chromium + sudo-created 3 UIDs
python3 -m unittest discover -s experiments/g1-b01-b12 -p test_consumer.py -v
python3 experiments/g1-b01-b12/experiment.py --output /tmp/s1-b12-evidence.json
```

下一步 B13：优先**受信 Consumer 最小权限身份 + 受控 IPC**，并验证**真实 HTTP 读取前 fail-closed**，配合源签名/派生重建与完整审计，再讨论企业行级权限与多租户隔离。
