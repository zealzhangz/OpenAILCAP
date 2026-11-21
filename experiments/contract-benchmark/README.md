# 第一阶段统一合同任务：预注册 Benchmark

该目录只固定第三方平台真实复现时的**输入、业务边界和验收预期**。不含任何平台“已通过”的结果。

## 运行

Python 3.10+（标准库）：

~~~bash
python3 -m unittest discover -s experiments/contract-benchmark -p 'validate_spec.py' -v
python3 experiments/contract-benchmark/validate_spec.py --summary
~~~

这会检查 spec.json 中 12 项金额规则、12 项审批状态机期望结果、18 项平台任务是否齐全，以及这些任务尚未运行的事实。**通过这些规范自检，不能说明任何低代码平台已完成了任务。**

## 文件

- [spec.json](spec.json)：冻结的业务模型、金额边界、审批状态机和 18 项平台验收任务，平台任务全部 NOT_RUN。
- [validate_spec.py](validate_spec.py)：独立的金额 Decimal 及状态机参考判定函数、规范校验。
- [研究说明与平台证据要求](../../docs/01-research/10-contract-benchmark.md)。

## 执行平台测试时的报告格式

为每项 TCxx 建立独立结果，字段至少包括：platform / edition / source_commit / version_digest / deployment_environment / test_case_id / input / expected / actual / verdict / evidence_uris / limitations。

在拿到运行日志之前一律标 NOT_RUN；有安装、授权、产品版本等阻断时标 BLOCKED 并附真实错误。AI 调用轨迹不等于运行验证，截图不等于业务正确。
