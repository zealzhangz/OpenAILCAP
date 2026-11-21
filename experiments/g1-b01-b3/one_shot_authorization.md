# B3 单次真实 DeepSeek 实验授权记录

本文件变更仅用于触发一次已获用户许可的必要研究验证，不包含任何密钥。

前置条件：[PR #5 离线 CI #44891709859](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44891709859) 已通过：B3 18 项模型提议安全测试、B2 18 项运行内核回归、B3 24 项真实 Chromium/Agent 离线 E2E。

此次 HEAD commit 的精确标记让 `.github/workflows/s1-b3-deepseek-app.yml` 在 **同一次 CI 的全部离线检查再次成功后**使用 GitHub Actions Secret `DEEPSEEK_KEY` 调用 DeepSeek 官方 Chat Completions **仅一次**，提出四个 Schema 元数据资源，严格校验后才执行受治理工具调用与人工模拟发布。模型不得直接写 SQL、Shell 或发布。

禁止自动重试失败或未知结果。后续新的提交不应重复使用该标记。完整成功与失败证据以新 GitHub Actions 运行及其 Artifact 为准，不能事先宣称模型正确生成。
