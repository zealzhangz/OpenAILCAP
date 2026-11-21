# S1 模型实验 GitHub Actions 独立执行记录

验证日期：2026-11-21。此文档补记 **GitHub 上真实运行完成的 CI**，而不是本地模拟出的结果。

## 与代码版本绑定的运行

- 代码提交：[472d1d0e554b1965ecd93a6c9aa0a75adfe6dca5](https://github.com/zealzhangz/OpenAILCAP/commit/472d1d0e554b1965ecd93a6c9aa0a75adfe6dca5)
- Workflow：[S1 Roundtrip Spike](https://github.com/zealzhangz/OpenAILCAP/blob/472d1d0e554b1965ecd93a6c9aa0a75adfe6dca5/.github/workflows/stage1-roundtrip.yml)
- 远端运行：[GitHub Actions Run #44866343414](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44866343414)
- Job：[model-tests #136730763249](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44866343414/job/136730763249)
- 触发事件：push
- 工作流最终状态：**completed / success**
- 运行起止：2026-11-21 04:29:17Z ～ 04:29:32Z（GitHub API 返回值）
- 远端执行步骤：checkout、setup Python 3.13、独立场景及防御测试、生成实验 JSON、上传实验报告，均由 GitHub 返回 **success**。
- 生成的 Artifact：roundtrip-model-results，Artifact ID 14691678724，供 GitHub 页面查看及下载（有保留期限）。

## 本地与远端的不同证据

- 本地 Python 3.13.5：28/28 单元测试 PASS；A/B 分别 10/10 场景 PASS；负对照确实复现了人工样式丢失。原始测试输出和机器可读结果已随同 472d1d0 提交。
- GitHub CI：工作流状态成功，说明同一提交能在 GitHub 托管的独立环境完成配置的两个测试步骤并生成报告。此次已核对 Job 步骤成功和 Artifact 存在。
- 以上均属于 **OpenAILCAP 自主研发的受限内存模型实验**，不是第三方低代码项目的部署验证，也没有真实 AI 模型、数据库、租户隔离或应用运行时。

## 对阶段门禁的作用

这增加了模型级 Spike 的**可复现性与独立环境可信度**，但不足以满足 README 的 G1 全部要求；关键的真实平台源码到持久化调用链、安装复现及其他风险评估仍需继续。

**当前决策**：S1 进行中；G1 未通过，H01/H03 只完成模型层首轮验证。
