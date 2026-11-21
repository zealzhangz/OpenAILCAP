# 最小技术实验协议（模型层部分已执行；真实平台验证未执行）

日期：2026-11-21。所有用例先冻结输入、预期、版本和评价器，再运行生成器；AI 不能修改验收脚本。每次记录 commit、模型版本、工具/环境版本、操作轨迹、耗时、Token、状态快照、测试结果、回滚与失败原因。

## C：Round-trip 一致性

先用受限对象模型跑 C01/C02/C03/C07，再扩大到 10 个用例和真实低代码编辑器。基线按钮 label=提交、background=blue、金额阈值 >1000000、自定义代码哈希固定。对照：整页覆盖负例 / CAS+三方合并 / 操作日志。判据：非冲突全部保留；冲突拒绝；revision 相同内容不同时识别；多对象写入失败能回滚；无静默丢失。

## R：配置/代码/混合路径路由

固定 24 题，配置 8、代码 8、混合 8，独立人工标注后各重复 3 次。评价不止“分类对不对”，还要检查真正的业务验收。不可配置任务被伪装为纯配置并标记成功，容忍数为 0。

## B：AI 自定义开发闭环

合同编号生成插件：唯一性/幂等/权限。Agent 输出代码，运行独立构建、单测、集成、安全、健康探针及隔离部署。注入编译失败、权限越界、密钥泄漏、错误审批边界、健康检查失败。硬性门禁：失败不可发布；旧版本可用；可回滚；修复次数有预算。

## D：插件发现与多应用隔离

新增插件不改核心 Prompt，AI 从 Manifest/Schema 自动发现；升级时识别非兼容变化。创建 A/B 应用，同名组件，测试读/写/构建/部署的未授权跨应用调用。预期越权成功次数 0。

## 完成证据与报告结构

每条运行记录：test_case_id、repo_sha、environment、input、operations、expected、actual、test_report、rollback_report、result（PASS/FAIL/BLOCKED/NOT_RUN）、evidence_paths。

禁止把存在测试代码当成测试已执行；禁止只筛选成功样例；不得让生成 Agent 自行宣布验收通过。第一阶段最小模型试验成功只支持模型层可行性，第三阶段还需要真实运行时 PoC。

## 2026-11-21 实验执行回填

C 组（H01/H03）已完成模型级 C01—C10：Unified IR 10/10、分域 Schema + Manifest 10/10；含防御性单测共 28/28 通过。复现了旧快照整页覆盖导致人工样式丢失的负对照。具体命令、机器可读结果和暴露的可信基线问题见 [实验报告](05-roundtrip-results.md) 与 [实验工程](../../experiments/roundtrip/README.md)。

R（路由）、B（代码闭环）、D（插件/应用隔离）均未执行；C 的真实低代码运行时版本也未执行。不能宣称 G1 或 G3 通过。

## 2026-11-21 SQLite 持久化实验回填

新增了独立的 [SQLite 文件数据库与事务测试](../../experiments/sqlite-roundtrip/README.md)：23 项独立测试全部通过，覆盖并发写事务、异常退出后恢复、乐观冲突、重复命令、版本回退以及模拟的 app_id/ACL 拒绝。它不是平台级实验；真实用户认证、Agent 编码执行、部署及第三方平台安装尚未执行。G1/G3 未通过。参考 [研究报告](07-persistence-and-license.md)。

## 2026-11-21：正式业务场景基准预注册

为后续真实平台和自研平台的同条件实验固定了 [合同业务规范](../../experiments/contract-benchmark/spec.json)：12 项金额边界、12 项审批转移预期和 18 项平台级验收任务。Oracle 仅校验规范一致性，所有平台任务现为 NOT_RUN。参见 [验收协议](10-contract-benchmark.md)。真实平台安装被 NocoBase v3 默认模板仓库 E530 阻断，没有新增平台级通过项。

## 2026-11-21：真实 Saltcorn 多轮编辑协议对照（阶段 S1）

独立工作流 [#44871169761](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44871169761) 已实际执行 A/B/C 和 C-HTTP 四组验证，18/18 次断言符合预期，四份 JSON 作为 GitHub Artifact 14694023138 上传。最重要的是 B 路径：恢复基于旧上下文的完整 Pack 会覆盖人工已保存的 title.label，属于显著**负面证据**；A 仅证实不同字段的串行 Field.update 不相互影响；C 仅证实应用层旧基线检测能拒绝一例顺序冲突，**不是原子 CAS**。实验没有真正调用大模型或浏览器人工编辑。见 [实测报告](16-saltcorn-roundtrip-evidence.md) 和 [源码工程](../../experiments/platform-saltcorn/roundtrip/README.md)。
