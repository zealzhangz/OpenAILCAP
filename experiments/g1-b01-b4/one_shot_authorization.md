# B4：一次实际 DeepSeek 自定义代码生成的授权记录

依据用户“继续”并要求尽量少调用外部模型的研究约束，已先行完成整套零模型预检，并允许在本文件对应的**单个 PR Head Commit** 精确触发一次受限 DeepSeek Function Calling，不自动重试。

前置成功：[B4 离线 CI #44893945547](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44893945547)：**27 个 B4 静态安全/模型工具测试 + 18 个 B2 内核回归 + 27 个真实 Chromium / Docker 集成断言全部通过**；人工编写代码在实际 --network=none 等隔离 Docker 中经过 **432 组业务边界 Oracle**，错误逻辑失败不发布。

一次模型请求将要求生成**单个受限 Python 纯函数源码**；AI 只拥有代码建议权，不持有 Docker、数据库和发布凭据；真实模型原始回答不能绕过 AST 静态校验、独立 432 项运行验收与人工模拟发布。若模型生成不合规或业务结果错误，记录失败、不拿离线基线充当真实 AI 通过、不自动补发请求。

模型调用需要 PR 来自原仓库，并且最新 Commit 消息精确等于预先约定的字符串。合并到 main 后 squash 不延续此标志。
