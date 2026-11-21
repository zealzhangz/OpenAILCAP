# H01/H03 Round-trip：可执行微型实验

**范围**：这是 OpenAILCAP 第一阶段 S1 的内存模型级技术 Spike，不是可运行低代码平台，也不是第三阶段的四大真实 PoC。

## 运行

仅使用 Python 3.10+ 标准库，无第三方依赖：

~~~bash
cd experiments/roundtrip
python3 -m unittest discover -s tests -v
python3 run_experiment.py --output results.json
~~~

代码： [engine.py](engine.py) / [cases.py](cases.py) / [tests/test_roundtrip.py](tests/test_roundtrip.py) / [run_experiment.py](run_experiment.py)

原始实测证据：[results.json](results.json)，首次测试输出在 [unittest-output.txt](unittest-output.txt)。脚本以非零退出码报告失败。

## 两种候选表示法

A（A-unified-ir）：统一应用资源图，根节点包含 app_id 和 resources。

B（B-domain-manifest）：按 ui/workflow/code/plugin 分域保存 Schema，再用 Manifest 记录资源的归属和内容 SHA-256 指纹。

**对照边界**：两者共享一个受治理的增量编辑引擎（同样的校验、合并、回滚规则），只比较状态表示的可兼容性，不能从本实验得出其中一种完整架构更优秀。

## 十个业务断言

| ID | 必须验证的行为 |
|---|---|
| C01 | 人工改样式 + AI 改文案，非冲突修改全部保留 |
| C02 | 同字段竞争，旧写入被明确拒绝 |
| C03 | 版本号相同、内容不同，拒绝旧快照；经显式版本采纳后重试 |
| C04 | 已删除组件被流程引用，拒绝悬挂引用 |
| C05 | 审批阈值和布局并行修改，二者正确 |
| C06 | 不能理解的插件扩展字段保持无损 |
| C07 | 跨资源变更中途失败不部分提交，恢复旧快照 |
| C08 | 重复 change_id 幂等，不允许载荷篡改 |
| C09 | 人工代码在 AI 更改元数据后仍无损 |
| C10 | 无模型连接时人工仍可以执行受控编辑 |

另外有 8 项防御性单测：失信基线、错误引用、不可变 ID、Manifest 损坏、回滚版本单调、并行非冲突合并、并行同字段拒绝，以及旧整页覆写**预期丢失人工样式**的负对照。

## 关键失败与限制

首轮 C03 曾在两条路线中同时因 UNTRUSTED_BASELINE 失败。仅“重新读取”没有把 out-of-band 人工修改变成可信历史版本；后来加入仅供模拟的 reconcile_external_revision 显式登记人工状态，才完成闭环。因此生产编辑器应走同一受治理写入 API；兼容历史系统时需要有认证、审计的版本采纳流程。

本实验使用线程锁和内存 Copy-on-Write，没有真实数据库事务、断电恢复、权限验证、插件安装、业务运行时或 AI 模型。代码资产只作为字符串保存；缺少多应用隔离。**28/28 单测通过，只说明受限模型符合这些断言。**

详见：[源码追踪](../../docs/01-research/04-tooljet-sync-trace.md) 与 [实验报告](../../docs/01-research/05-roundtrip-results.md)。
