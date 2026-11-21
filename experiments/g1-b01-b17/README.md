# B17：有界 Native 只读适配与公开快照渲染对照

状态：真实 CI 完成。此实验承接 B16 的只读启动失败，不预先决定技术选型。

## 预注册范围

- **路线 A**：在一次性 CI 安装中，仅修改 `@saltcorn/server/dist/serve.js` 的
  `await initOfflineStoreCfg()` 一处调用，跳过已定位的启动配置写入。
  先核对 B16 记录的完整文件 SHA256，未知版本直接拒绝。
  保留真实 Web UID 只读数据库、不可写父目录、独立可写 Session、关闭迁移/调度。
  若仍有只读错误，记录新阻断点并停止适配，**不增加修改预算**。
  正常结束或异常时恢复原始文件并验证哈希。这不是上游支持的生产只读模式。
- **路线 B**：Python 标准库 HTTP 进程，只提供四列公开合同列表。
  Apply UID 从相同 Native 合同表生成 B15 格式的两表快照，独立 Renderer UID
  只读快照且不能读取 Native 数据库。文件必须由 Publisher 拥有，父目录不可组写，
  拒绝符号链接、多硬链接和异常文件。单个文件描述符读取至有大小上限的内存 SQLite，
  验证表/列、Manifest、Head 类型、行摘要及字段范围后转义 HTML。
  原子替换前已打开的描述符可读取完整旧版本，后续请求读取新版本。

**共同数据**：同一真实 Saltcorn Pack、合成合同、同一金额和恶意文本；真实 Chromium 验证。
只读 Native 能运行时再做真实浏览器和恶意文本测试，不能把未运行的分支算成 PASS。
重复运行 B16 的 18 项基线；B17 新增 14 项单元/契约，回归 B15 22 项单元。
真实检查数以实际分支执行结果为准，新增浏览器断言不能代替产品级门禁。

## 已知边界（在执行前固定）

1. `fixture_snapshot.py` 是**测试数据发布器**，不校验 B2 签名，不是 B15 Publisher。
   B15 真实读取器兼容通过契约测试核对，未声称完整签名发布链路已集成。
2. 路线 B 的 Head/摘要用于内部一致性；摘要不是来源签名。信任边界是独立本机 Publisher
   UID、目录权限和固定 Manifest。它展示**最后发布版本**，未调用权威源做实时新鲜度检查。
   测试专门记录 Native 更新但未发布时继续显示旧快照，不能等同于 B15 读前 Guard。
3. 无认证、无 Session、无表单/编辑器/流程/插件，无租户 ACL。只含公开合成数据；
   不是生产应用或完整低代码运行时。HTTP 固定 loopback，没有继承 B15 防火墙证明。
4. 固定上限：快照 1 MiB、256 行、文本字段 4096 字符、非负安全整数分；无生产并发/HA/SLA 结论。
5. 路线 A 需要上游源码维护；路线 B 需要自主渲染与业务能力接入。两者的复用范围和成本必须分开记录。
6. 不读取 DEEPSEEK_KEY，不调用大模型。G1 NOT_PASSED，W/TC FULL PASS 不变。

## 代码与复现

- `patch_native.py`：一处调用的哈希固定适配与恢复。
- `snapshot_web.py`：只读加载、严格公开格式验证及转义页面。
- `fixture_snapshot.py`：从同一 Native 表制作 B15 格式测试快照。
- `test_snapshot_web.py`：14 项边界/兼容/原子替换/转义验证。
- `compare.py`：真实三 UID、Saltcorn、Chromium、发布恢复与拒绝实验。
- [专用 Actions](../../.github/workflows/s1-b17-readonly-route-comparison.yml)。

```sh
cd experiments/g1-b01-b17
python3 -m unittest -v test_snapshot_web
# 真实 UID/E2E 请按专用 CI 安装依赖及用户后执行：
python3 -u compare.py --output /tmp/s1-b17-evidence/b17/results.json
```

## 最终验证

Actions #44958544226 成功：36项单元/契约、18项B16回归、26项B17修订后研究检查。原生文本保真仍失败（标题为空），未计作通过。两条路线的限定只读列表均可运行；快照路线仍缺权威源新鲜度保证。详见[报告50](../../docs/01-research/50-s1-b17-readonly-adaptation-snapshot-comparison.md)，包含两次失败和判据修订。
