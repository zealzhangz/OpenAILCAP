# S1 报告 26：DeepSeek 真实配置 / 代码 / 混合路径选择与 Saltcorn 原生执行

**研究日期：2026-11-21。结果：一次真实 DeepSeek Function Calling 选择 6 个需求的实现模式，6/6 与预登记标签一致；真实 Saltcorn native Table/Field/View/Trigger/SQLite/HTML 全部 20/20 独立验收通过。G1 仍 NOT_PASSED。**

## 一、核心假设与证据范围

检验在平台能力清单可用时，模型是否能区分：

- **CONFIG**：原生字段/列表能力已支持的低代码配置，不能无故生成自定义 JavaScript；
- **CODE**：数据模型无需修改，但已有基础字段校验不支持复杂校验码，须经受审核的 run_js_code Validate 扩展；
- **HYBRID**：需扩展持久字段并使用自定义 Insert 业务规则生成跨表关联审计记录。

测试集由研究人员预登记 **6 个需求（各路径 2 个）**、明确参考答案和固定业务数据，模型输入**只包含需求 id、描述和能力目录**，不包含 `expected_mode`、固定执行数据及验收结果。6 个任务集中在一个真正 DeepSeek Function Call 的 `submit_routes` 中完成选择。**代码、Schema、Trigger、Saltcorn Pack 均由研究人员预先编写和审核，模型只给出 CONFIG/CODE/HYBRID 枚举，不能执行 Shell/SQL，也没有写入权限。**

## 二、分层实验及固定来源

| 证据类型 | 可独立核验的真实证据 |
|---|---|
| 研究工程与六案例冻结输入 | [experiments/route-choice](../../experiments/route-choice/README.md)、[spec.json](../../experiments/route-choice/spec.json) |
| 离线平台预检 | [GitHub Actions #44883844751](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44883844751)：completed/success；**20/20**。使用冻结正确路由运行 Saltcorn，**不调用模型，不能算 AI 结果** |
| 真实模型被测 Commit | [4e9307b876db94c96ddc4f179353e7beccd40352](https://github.com/zealzhangz/OpenAILCAP/commit/4e9307b876db94c96ddc4f179353e7beccd40352) |
| 真实模型 + 原生运行 | [GitHub Actions #44884021495](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44884021495)：两个独立 Job 均 completed/success |
| 模型预测 Job | **136785281254**；prediction Artifact **14698694770**（s1-route-choice-prediction） |
| 原生 Saltcorn 执行 Job | **136785345227**；native Artifact **14699311128**（s1-route-choice-native-evidence） |
| 模型 | **deepseek-flash**、官方 HTTPS Chat Completions、Function Calling、thinking disabled |
| 调用与用量 | **实际外部模型 HTTP 请求 1 次、Function Call 1 次，Prompt 876 Tokens，Completion 118 Tokens，总计 994 Tokens** |
| 样本结果 | **6/6** 模型选择与预登记标签一致，另 **20/20** 独立运行验收断言全部通过 |
| 参考基线 | 故意简单的“全部选 CONFIG”固定规则只对 2/6，不可当作充分的竞争基准 |

**成本约束**：使用已经存在的 GitHub Actions Secret `DEEPSEEK_KEY`，未在仓库提交 Key；通过一次性提交标记 `[deepseek-route-once]` 触发，仅一次 API 推理，普通后续 push 不再自动调用模型。预测与平台执行分成两个 Job，若平台 Job 出现问题可仅复用已生成的预测 Artifact 重新进行平台验证，不必再次推理。

## 三、模型真实预测与物理执行

| 需求 | 冻结预期 | DeepSeek 实际选择 | 原生运行证据 |
|---|---|---|---|
| RC01 普通联系人备注字段 | CONFIG | **CONFIG** | 实际 `s1_route_cfg` 表字段和值落库，原生 List View 展示 |
| RC02 归档说明文本及列表展示 | CONFIG | **CONFIG** | 配置表实际持久化备注、状态，原生 View 存在且可读 |
| RC03 自定义模 7 校验码 | CODE | **CODE** | 真正 Saltcorn Validate `run_js_code` 拒绝 `K-14-5`，0 行错误数据，接受 `K-14-0` |
| RC04 相同算法的另一编号 | CODE | **CODE** | 触发器拒绝 `K-22-5`，0 行错误数据，接受 `K-22-1` |
| RC05 >100 万元写关联审计及备注快照 | HYBRID | **HYBRID** | `s1_route_hybrid` 业务字段真实落库，Insert Trigger 写出关联审计 HIGH，备注快照一致 |
| RC06 =100 万元仍按普通档位写跨表备注 | HYBRID | **HYBRID** | 混合字段与关联表真实落库，金额 100000000 分对应 NORMAL，备注快照一致 |

该执行使用真正的 `@saltcorn/cli@1.7.0-beta.5`、原生 Pack、4 张独立 Saltcorn 研究业务表、2 个 List View 和 2 个 Code Action Trigger。独立验收器查询 `_sc_tables`、`_sc_triggers`、`_sc_views`、物理 SQLite 业务行和真实 `/view/s1_route_cfg_view`、`/view/s1_route_hybrid_view` HTTP 页面，最终得到：

```text
S1_ROUTE_PREDICTION|{"inference":true,"model":"deepseek-flash","choices":[
  {"id":"RC01","mode":"CONFIG"},{"id":"RC02","mode":"CONFIG"},
  {"id":"RC03","mode":"CODE"},{"id":"RC04","mode":"CODE"},
  {"id":"RC05","mode":"HYBRID"},{"id":"RC06","mode":"HYBRID"}],
  "usage_tokens":{"prompt_tokens":876,"completion_tokens":118,"total_tokens":994}}
S1_ROUTE_RESULT|{"model_inference_executed":true,"correct":6,
  "cases":6,"baseline":2,"passed":20,"total":20}
```

完整未裁剪的真实结果存于两个 GitHub Actions Artifact。模型输出受严格白名单约束：6 个不同 case id 且必须属于三个枚举，原始 JSON 不得提交 JavaScript、代码工具或越权身份参数。

## 四、消除与保留的风险

**本次可以确认**：

1. 真正外部大模型能够基于明确能力清单调用一次类型化工具，选择这六个需求的开发路径；
2. 选择结果不只是文本分类，能通过限权执行层调度预审核的实际 Saltcorn 配置、代码扩展和混合组件；
3. 模型选择正确与真正平台可运行采用两个独立 Job/Artifact 和物理数据库判定，不依赖模型自评；
4. 不具备字段配置能力的模 7 校验不可仅凭记录字段成功就算验收；必须由实际 Trigger 拒绝无效数据；
5. 混合路径确实既有原生字段持久化又有跨表事件写入，对金额阈值存在真实边界负对照。

**本次不可以确认**：

- 六项样本是人工精心选取且能力描述明确的小样本，一次调用的 6/6 并不代表模型对陌生需求有 100% 准确率；
- **模型并未编写代码、字段、视图或插件**。所有被执行内容都由研究人员预装，模型只选择既有 Adapter，不能把这组实验解释为 AI 自主建模/代码生成；
- 没有评估当某个真实扩展能力缺失、代码执行失败时模型如何多轮重规划、自动修复或回退；
- 没有真实人工设计器与 AI 交替修改，也没有原生统一版本 API 的正向平台级证明；
- 非真实企业多应用/组织 RBAC、分布式事务隔离、SSO 和正式生产发布；
- 冻结完整合同 TC01—TC18 仍 0/18 全项 PASS，**G1 仍 NOT_PASSED**。

## 五、研究架构的阶段性决策

对于 S1 的“配置还是代码”研究，这次提供了一个**可运行、限域、可审计的模式选择机制**：声明平台现有的配置/代码/混合能力 → 受限模型只选择枚举 → 可信适配器检查工具权限并调用预批准的原生行为 → 独立验证实际业务结构与运行态。比仅提供一个分类 Prompt 有更强证据，但距离完整的 Agent 自主开发仍有显著差距。

下一项优先研究仍是 **真正人工浏览器设计器 → 真实模型接手 → 原子版本变更与保存 → 人工再次编辑的双向安全协同**。研究可复用此前 Saltcorn 原生旧表单覆盖、Pack 恢复覆盖和受限 HTTP 版本化网关的正反证据。必须限制新模型调用与编辑权限，并在不具备原生统一写入接口时明确失败关闭，不能因本次 6/6 而判定 G1 GO。
