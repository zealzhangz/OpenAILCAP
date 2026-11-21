# S1 H01/H03：SQLite 持久化与人机编辑事务实验

> 本工程是可执行的数据持久化 Spike，不是生产级平台、ToolJet/NocoBase 部署或 Agent 自主开发 PoC。

## 运行要求

Python 3.10+，仅用标准库 sqlite3、unittest，无需安装数据库服务：

~~~bash
cd experiments/sqlite-roundtrip
python3 -m unittest discover -s tests -v
python3 run_experiment.py --output results.json
~~~

GitHub Actions 会从干净仓库检出并独立执行测试，然后上传 JSON 结果，不采用 AI 自评。

## 实现边界

| SQLite 表 | 作用 |
|---|---|
| apps | 应用 ID、单调版本号、内容指纹 |
| resources | (app_id, resource_id) 复合主键，存放 domain/data/refs |
| versions | 已提交版本快照、SHA-256 指纹 |
| grants | 实验用应用级 read/write ACL（actor 仅为可信调用者传入的模拟身份） |
| changes | (app_id, change_id) 幂等键、请求指纹、回执 |

使用 BEGIN IMMEDIATE 数据库写事务，写前验证基线的历史快照；允许非冲突的字段合并；拒绝同字段冲突、坏引用、跨应用基线；更新资源、版本和幂等回执在同一事务中完成。回滚使用新的单调版本恢复历史快照，不覆盖旧历史。

本次持久化对象采用分域资源与版本快照模型，并未证明它优于统一 IR。A/B 内存对照实验见 ../roundtrip/README.md。

## 实际验证

- 数据库关闭再重启后版本及状态保留。
- 两个独立 SQLite 连接竞争写入不同字段时都保留，同时改相同字段仅一个成功。
- SQL 写入中途注入失败或独立进程提交前直接退出时，数据库保持原状态。
- 同一 revision 的非授权原始数据修改触发 SNAPSHOT_DRIFT，幂等重放也不得伪装成功。
- A/B 两个应用即使有同名资源，也按 app_id 分隔查询和写入。
- 只读用户、跨应用访问及伪造基线被拒绝。
- 插件未知字段、人工源代码和跨域引用得到保护；失败回退与幂等性有独立断言。

## 不得越界解读的限制

没有真实 API 身份验证。actor 由调用方指定，伪造该字符串能够冒充有权主体，因此 grants 表仅证明模拟 ACL 行为，不证明生产多租户安全。bootstrap_app 和 grant_for_fixture 是特权实验准备接口，不得作为产品 API 发布。没有真实设计器、AI 模型、代码沙箱、插件运行或生产发布测试。

SNAPSHOT_DRIFT 目前拒绝继续，不能自动恢复未经版本化的人工修改。生产方案必须统一受治理写入 API，或通过经审计的版本采纳流程。上线前必须补真实身份认证、应用作用域、审计和恶意执行对抗验证。

## 原始成果

- 机器可读运行记录：[results.json](results.json)
- 本地原始输出：[test-output.txt](test-output.txt)
- [数据库实验源码](store.py) / [23 项自动化测试](tests/test_store.py) / [结果生成器](run_experiment.py)
- [源码与许可研究报告](../../docs/01-research/07-persistence-and-license.md)
