# S1 真实执行记录：H01/H03 双向编辑微型实验

执行日期：2026-11-21。状态：**模型层已完成首轮实验，平台级仍未验证；G1 未通过**。

## 实验对象与环境

在用户 README 明确要求的“统一 Application IR vs 替代架构”之间，构建：

- A：Unified IR，统一应用资源图；
- B：Domain Schema + Manifest，分域资源加引用索引和哈希。

两条路线共享相同的并发写入与校验算法，以隔离表示结构差异。业务基线为合同页面、按钮、审批阈值、事件引用、自定义代码与一个包含未知字段的插件模拟资产。

环境：Linux x86_64，Python **3.13.5**，Python 标准库，无第三方包、无大模型调用。可用下列命令重现：

~~~bash
cd experiments/roundtrip
python3 -m unittest discover -s tests -v
python3 run_experiment.py --output results.json
~~~

原始结果：[results.json](../../experiments/roundtrip/results.json)；[unittest-output.txt](../../experiments/roundtrip/unittest-output.txt)；源码及说明：[experiments/roundtrip](../../experiments/roundtrip/README.md)。

## 实际结果

| 指标 | A：Unified IR | B：Domain + Manifest |
|---|---:|---:|
| C01—C10 预注册业务模拟场景 | **10/10 PASS** | **10/10 PASS** |
| 并发非冲突合并 | PASS | PASS |
| 重叠编辑显式拒绝 | PASS | PASS |
| 同版本不同内容检测 | PASS | PASS |
| 坏引用拒绝 | PASS | PASS |
| 失败时部分写入阻断及回滚 | PASS | PASS |
| C01 后序列化大小（本模拟样例） | 882 字节 | 1633 字节 |

另外 8 项防御性单元测试通过，**共 28/28 单测成功**。负对照“旧整页覆盖”复现了人工改动丢失这一**期望失败**。

字节数仅描述这个很小的 JSON 模拟对象，不能据此选定架构或推断生产性能。JSON 记录的纳秒级单次耗时也不能作为工程性能比较。

## 发现并处理的失败

第一版 C03 在 A/B 同时报错 UNTRUSTED_BASELINE。系统能发现同一 revision 下内容指纹发生变化并拒绝旧写入，但 Agent 重新读取仍不是可信历史状态——**最新人工内容并未写入受控版本历史**。

后续引入测试用 reconcile_external_revision，将外部变更明确采纳为新的审计版本，再提交后续 Patch，才解决该用例。此函数只是模拟兼容机制，没有身份授权功能，不得视为可直接生产使用。

**重要结论**：人机协作不仅需要哈希检测和重新读取，还需要**可信版本的连续性**；最佳路径是人工和 AI 从入口就使用同一受治理写入 API。

## 当前可以与不可以下的结论

**可以**：在受限内存模型中，两种资源组织形式都能实现本次 10 个预注册变更场景；没有证据表明统一 IR 在这些场景中必不可少。

**不可以**：宣称 A/B 实现了生产级数据库事务、运行时隔离、Agent 工具安全、真实人工编辑器一致性、插件执行或真实代码编译；也不能宣称 H01/H03 已平台级验证成功或 G1/G3 通过。当前 actor 仅为测试标签，代码工件仅作为字符串保留。

## 下一步门禁动作

1. 在 ToolJet 真实 Code mode 上复现“用户改样式 → Agent 修改文本”，保存源代码、命令和读回/运行证据。
2. 追踪 ToolJet MCP 到 CLI、服务端存储、发布与回滚的边界，记录断点。
3. 对 NocoBase 插件和 Runner 做同等深度的源码/实际运行核查。
4. 将真实数据持久化、权限控制、Schema 升级、插件扩展纳入 A/B 再比较，才能形成 ADR 决策。

**阶段判定**：当前只是 S1 的可复现模型级 Spike；全套阶段 G1 **仍未通过**。
