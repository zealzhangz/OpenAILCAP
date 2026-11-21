# S1 Saltcorn 真实平台：局部修改与旧完整 Pack 对照实验

此实验中的 human 是**人工预先编写的原生 Field.update 调用**，而不是平台可视设计器的实际用户操作。automation 是确定性脚本和完整 Pack 导入，**不是真实 LLM Agent**。两者均使用研究环境内的高权限 CLI。不得宣称 PoC-C 或生产权限验证完成。

## 三阶段固定实验

| 阶段 | 操作 | 独立 oracle | 研究意义 |
|---|---|---|---|
| A | 研究员用原生模型 API 修改 title.label = Human Reviewed Title；自动化仅通过 Field.update 修改 status.label = Automated Status | 两处改动都存在；合同数据与视图仍正确 | 局部修改正对照 |
| B | 根据人工修改前的基线生成旧 Pack；自动化只想删除列表中的 amount_minor 一列，但提交含所有旧字段的**完整 Pack** | amount_minor 列移除，同时 title/status 标签回到旧值 | 证实或证伪“旧全量快照会覆盖无关人工改动”的**负对照** |
| C | 人工再次修改 title.label；自动化以旧基线 Title 执行带基线比较的字段修改 | 出现 STALE_BASE，写入拒绝；人工标签不变 | 比较应用侧检查方向，不代表原子 CAS |
| C-HTTP | 通过真实 Saltcorn 服务读取 REST 和列表 HTML | 200，包含原合同记录 | 运行态读回 |

**重要：B 阶段出现 PASS 可能意味着不安全的静默覆盖被成功复现，不代表“产品没有风险”。** C 的读取检查与写入是两次操作，存在 TOCTOU 竞态，不得作为生产级乐观锁。

## 文件

- 原生研究基线：[contract-pack.json](../contract-pack.json)；测试合同数据：[seed-contract.js](../seed-contract.js)
- [human-edit.js](human-edit.js)：通过真实 Saltcorn Field.update 保存人工预先指定的更改
- [scoped-automation.js](scoped-automation.js)：只更新目标字段的程序化操作
- [make-stale-pack.py](make-stale-pack.py)：从旧基线生成旧完整 Pack，但仅更改 view 的一列
- [guarded-automation.js](guarded-automation.js)：拒绝旧基线冲突（应用层非原子检查）
- [verify.py](verify.py)：独立读取物理 SQLite、Saltcorn metadata 和 HTTP
- [GitHub Actions 工作流](../../../.github/workflows/s1-saltcorn-roundtrip.yml)：固定 Saltcorn 1.7.0-beta.5，独立执行全部场景

## 结论边界

本实验不测试真实用户会话、编辑器的浏览器 UI、LLM Agent 的需求理解、跨应用权限、真实并发争用，也不证明 Saltcorn Pack 的恢复接口应该提供并发编辑冲突保护。测试仅是对于“**将特权全量恢复接口误作 AI 修改工具**”的反例研究。

若要给 OpenAILCAP 生产系统设计安全的 AI/人工交替编辑，至少需要可信身份、版本化资源、原子 expectedRevision/ETag 比较、字段级冲突处理、审计、回滚，以及独立运行时验证。源代码对照入口：上游 Saltcorn 的 packages/saltcorn-admin-models/models/pack.ts、packages/saltcorn-data/models/field.ts 和 packages/saltcorn-data/models/view.ts，固定研究 commit 515254bee5a98df70530cc59846b1df02d5db350。
