# S1 研究报告 50：B17 只读 Native 适配与公开快照渲染对照

日期：2026-11-22（北京时间）。状态：真实对照完成；原生文本保真失败保留，G1 未通过。

## 一、问题和候选路线

[B16](49-s1-b16-native-web-apply-readonly-feasibility.md) 已否定“仅分离 UID、只读整个
Native SQLite、关闭迁移并分离 Session，即可直接运行未修改 Saltcorn”的方案。
其直接阻断点是启动时写 `pre_installed_module_infos`。

B17 比较两条实际候选，不把一次局部运行成功当作完整架构选择。

| 维度 | A：有界 Native 只读适配 | B：最小公开快照渲染 |
|---|---|---|
| 运行代码 | Saltcorn 1.7.0-beta.5，仅跳过一处启动调用 | Python 标准库、一个固定合同 GET |
| 原生修改 | `server/dist/serve.js` 一文件、一调用；固定 SHA256，结束后恢复 | 不修改 Saltcorn |
| 业务来源 | 同一真实 Native 合同表 | 从该 Native 表复制相同四列，B15 两表格式 |
| Web 文件权限 | Native 数据库只读、父目录不可写、Session 单独可写 | 独立第三 UID 只读公开快照，不能读 Native 数据库 |
| 复用能力 | 原生 List 页面；其余表单/流程/插件不在本次证明范围 | 只有四列列表，无原生表单/编辑器/流程 |
| 数据暴露范围 | 完整 Native SQLite，含元数据/账号表 | 仅公开合同及 Head/Digest/Manifest 状态 |
| 来源与新鲜度 | 本轮使用合成数据，不接入权威源 | 本机 Publisher UID + 固定 Manifest；最后发布语义，无 B2 实时新鲜度保证 |
| 升级代价 | 上游文件变化即拒绝适配，需要维护只读运行模式 | 自主渲染、校验与后续能力实现成本 |

**A 的修改预算在执行前固定为一处调用**。若下一处只读启动失败出现，记录失败并停止，
不能连续打补丁直到成功。适配过程中不恢复数据库写权限，不修改上游 schema/数据模型。

## 二、真实实验和验证机制

先重新运行 B16 的 18 项真实负面/正面对照。B17 再建立同一 Native Pack 和合成合同，
用不同非 root UID 运行 Native Web 和 Snapshot Web。Apply UID 持有数据写权限。

- 原生可写基线必须经真正 Chromium 显示合同，否则对照无效。
- A 成功启动时，检查 Chromium、数据库 SHA256 不变、Web SQL 写拒绝；随后由 Apply
  写入受控恶意文本，重启原生 Web 检查是否转义。失败分支只记录真实错误，不算浏览器成功。
- B 把相同字段写到 B15 格式快照，真实 HTTP/Chromium 显示；网页 UID 不能读 Native
  SQLite，不能写、删除或替换发布文件。
- B 验证恶意文本 `<img ... onerror=...>` 作为文字显示，不形成注入图片、不执行脚本；
  未知路由 404、写方法 405、CSP 禁止脚本；这些仅覆盖本次公开列表。
- Native 更新但尚未发布时，B 仍展示最后发布版本；显式原子发布后，**不重启 B** 可见新值。
  此负对照公开记录，不能将该模式冒称为 B15 当前源校验。
- 快照丢失、摘要不符、Manifest 不符应返回503；恢复正确快照后返回200。

快照读取使用 `O_NOFOLLOW` 打开一个描述符，核对文件所有者、模式、大小和链接数，
读取至最多 1 MiB 的内存 SQLite，然后验证固定两张表、固定列、最多256行、字段类型及摘要。
发布者原子替换后旧描述符可继续读取完整旧代次（其链接数可为0），避免对路径重复打开造成混合。
**该保证依赖发布者只原子替换，不支持并发原地写快照。** 摘要不是数字签名。

本地验证：新增 **14** 项单元/契约、回归 B15 **22** 项单元通过；其中一项由 B15 原始
`read_published` 实际读取同一文件，验证格式兼容；另一项在文件已打开后注入原子替换，
验证先前请求读完整旧代次、后续请求读新代次。

## 三、执行证据和实测结论

[最终 Actions #44958544226](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44958544226) completed/success，Job **137011971972**，
[Artifact #14727973319](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44958544226/artifacts/14727973319)。
36/36 单元/契约、18/18 B16 回归、26/26 B17 修订后的研究检查完成。
[日志解析摘要](../../experiments/g1-b01-b17/ci-observations.json) 保留代码提交及逐项观察。

- A：跳过一处调用后，真实 HTTP200/Chromium 显示合同，数据库 SHA256 不变，Web SQL 写入仍被拒绝。上游源码已恢复原哈希。
- A 的恶意标题显示为空：没有注入图片和脚本执行，但 **literal text fidelity = false**。不得把26项研究检查通过解释为原生文本保真通过。
- B：真实第三 UID995 不能 O_RDONLY 打开 Native 数据库，也不能写/删除/替换公开快照；HTTP200，Chromium 原样显示经转义的恶意文本，无脚本执行。
- B：Native 更新但未发布时仍显示旧快照；原子发布后无需重启即可显示新标题。缺失、摘要篡改、错误 Manifest 均503，正确重发恢复200。

**失败历史与判据修订公开保留**：
首次 [#44943359854](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44943359854) 在原生恶意文本原样显示检查失败，快照路线未执行；随后增加 bodyText 证据，将保真失败独立记录，继续另一候选，不将失败改为成功。
第二次 [#44958331587](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44958331587) 证实标题为空，但夹具误要求 SQLite 读取拒绝必须带系统 errno13；实际是 SQLITE_CANTOPEN。增加独立真实 O_RDONLY 检查确认 PermissionError，最终完整执行。
因此，最终26/26是修订后研究断言计数，不等同于原始所有目标通过。

**决策**：两条路线的限定列表可运行。下一轮优先把 B 的最小公开数据读取接入可信发布与权威源新鲜度检查，验证过期快照拒绝及恢复；A 保留为可比较参考，不扩张临时上游补丁。此优先级不代表最终技术栈已经选定。

## 四、正式门禁映射

| 冻结项 | 本轮相关证据范围 | 仍缺少的验收 |
|---|---|---|
| W11 原生越界漂移 | 只读身份写拒绝、坏快照503 | 权威源漂移隔离、全入口 fail-closed；B 尚无最新源核验 |
| W16 插件数据库旁路 | 普通 Web UID 无文件写权限 | 真正插件执行与全部非托管写路径证明 |
| W17 同进程读回 | B 原子发布后不重启显示新值 | 正式同进程 DB/REST/浏览器及元数据一致性；A 本轮使用重启 |
| W18 发布漂移门禁 | B 拒绝摘要或 Manifest 不一致 | 发布前权威签名、引用依赖、源/运行版本完整门禁 |
| W24 验证快照回滚 | 正确快照重发后恢复读取 | Runtime/配置/自定义代码的统一回滚与实际业务一致性 |

其他 W、合同 TC 项未因本实验改变。**不能把本次检查计数累加为正式门禁通过率。**

## 五、后续研究决策与边界

依据真实结果再选择下一项最小实验，不继续扩张 Native 补丁预算。
无论选择哪条渲染路线，都需要将受信写入、权威签名发布和读取语义统一起来。
本次测试发布器是 `fixture_snapshot.py`，**不是 B15 签名 Publisher**，未复跑 B15 的
完整148项 E2E，也没有继承其防火墙、六 UID、签名验证的组合结论。

这是单机公开合成数据、固定列表的研究；无真实认证/用户授权、租户隔离、编辑、表单、
审批执行、插件、生产容量/HA 结论。两条路线不能因页面可见而升格为完整低代码 Runtime。
**DeepSeek 调用0次。S1 IN_PROGRESS / G1 NOT_PASSED / G1-B01 OPEN；
W01—W24 0/24 FULL PASS，TC01—TC18 0/18 FULL PASS。**

工程：[B17 README](../../experiments/g1-b01-b17/README.md)、
[对照控制器](../../experiments/g1-b01-b17/compare.py)、
[固定适配](../../experiments/g1-b01-b17/patch_native.py)、
[快照渲染](../../experiments/g1-b01-b17/snapshot_web.py)、
[专用 CI](../../.github/workflows/s1-b17-readonly-route-comparison.yml)、
[PR #19](https://github.com/zealzhangz/OpenAILCAP/pull/19)。
