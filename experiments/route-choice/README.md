# S1：DeepSeek 选择 CONFIG / CODE / HYBRID 的最小真实平台实验

## 核心问题

验证真实模型能否根据受限的 Saltcorn 能力目录，将六项冻结合同需求选择为纯配置 CONFIG、原生 JavaScript Code Action 扩展 CODE 或字段加触发器 HYBRID。**模型只返回任务 ID 和模式枚举，不生成代码，不拥有 Shell/SQL/浏览器操作权限。**

- [spec.json](spec.json)：六个预登记案例，每种模式两个；包含独立裁判使用的 expected_mode 和可运行的固定 fixtures。传给 DeepSeek 的数据严格只取 `platform_capabilities` 和 `{id,requirement}`，不包含 expected_mode 或 fixtures。
- [predict.py](predict.py)：固定 `deepseek-flash`，一次 HTTPS Chat Completions 请求、一个 `submit_routes` Function Call，`thinking=disabled`，`max_tokens=650`；全量检查恰好六个不同 ID、只允许三个模式，保存脱敏结果和 Token 用量。
- [generate_pack.py](generate_pack.py)：在实际 Saltcorn Pack 中建立四个研究表（配置、代码、混合、混合关联审计），两个原生 List View 和两个原生 `run_js_code` Trigger（checksum Validate、跨表 Insert）。
- [make_executor.py](make_executor.py)、[native-executor-template.js](native-executor-template.js)：可信代码根据模型选择枚举，**只执行预先人工审核和安装的原生 Saltcorn Table/Trigger 能力**；不会从模型动态生成源代码。
- [verify.py](verify.py)：独立比较 6 个冻结标签，从真实 Saltcorn SQLite `_sc_tables`、`_sc_triggers`、物理记录、Checksum 拒绝/写入、跨表审计和两个原生 HTML List View 做验证。另报告无智能的 all-CONFIG 对照（2/6），不把它包装成真实算法基线。
- [test_routes.py](test_routes.py)：不联网的测试集完整性与工具参数白名单测试。
- [workflow](../../.github/workflows/s1-route-choice.yml)：两个 GitHub Actions Job。第一步单次模型预测和独立 Artifact；第二步实际安装 Saltcorn、原生执行、物理验收。若第二步失败，**只重跑失败的 Job 即可复用第一次预测 Artifact，避免为环境修复再次付费**。

## 严格成本与结果边界

首次自动 push 无特殊提交标记时，`predict.py` 用冻结参考标签进行**仅平台原生运行预检**，`model_inference_executed=false`；该预检的 6/6 不能宣称模型选型准确。待预检平台安装/数据/HTML 整体通过后，单独一次 push 提交 `[deepseek-route-once]` 启动**仅一次 DeepSeek 推理**。其他普通 push 或手动默认工作流都不发生付费模型请求；用户可以明确手动选择 `workflow_dispatch.live_model=true` 才再次调用。

模式评估分离：① 6 个模型预测与预登记参考标签比较；② 选出的固定能力是否真正通过 Saltcorn 原生平台运行验证。研究仅衡量一个小样本批次的可行性，不声称统计推广、Prompt 鲁棒性、模型自主创建应用、生成 JavaScript、自动测试修复或人工/AI 双向编辑。

**G1 仍 NOT_PASSED。** 冻结合同 18 项完整任务仍由原来的独立 TC01—TC18 验收评定，不能因这六项机制案例通过而修改。
