# S1 B4：AI 自定义代码开发——静态规则、真实 Docker 沙箱、绑定 B2 发布

> **限定研究实验，非生产级 Agent、自定义组件生态或完全自主软件工程**。目标是回答：当 B2 低代码没有供应商信用/合作年限风险评分能力时，能否通过 AI 生成受审查的纯函数，完成独立实际代码执行与自动测试，并保证失败不影响 B2 已发布应用？

## 实验组成

| 文件 | 作用 |
|---|---|
| policy.py | 最小能力路由 LOW_CODE/CUSTOM_CODE、DeepSeek 官方单次 Function Calling、Python AST 白名单、静态编译及固定业务语义参考 |
| reviewed_rule.py | **人工写的离线样例，不是 AI 输出**，用于在模型调用前独立验证工具链 |
| worker.py | 可信 Docker 内执行器；在 432 个独立金额/信用/年限边界组合上验证业务评分，调用实际纯函数 |
| sandbox.py | 可信宿主 Docker 调用：固定不可变镜像 ID、network=none、read-only、non-root、drop caps、no-new-privileges、限制 CPU/RAM/PID、readonly bind；超时失败关闭 |
| registry.py | B2 **同一 SQLite DB** 下的可信扩展 Artifact、不可变发布、原子指针和版本回滚；绑定 B2 已发布 Manifest hash，未经测试或变更发布版拒绝 |
| extension_http.py | B2 认证 Session 上的只读风险评分运行接口，无上传任意代码/镜像/发布功能 |
| test_policy.py | 不调用模型/Docker 的对抗测试，拒绝 import、Shell、attribute、subscript、loop、错误函数名等 |
| experiment.py | 真 Chromium 登录、真实 B2 Form/View/合同数据、独立 Docker 编译/432 个用例、代码发布/负例、代码人工改动、v2 回滚和跨应用隔离 |
| .github/workflows/s1-b4-custom-code.yml | 强制先 AST/B2 单元测试与 Docker+Chromium 离线实测全成功，再用精确 commit 标志允许一次模型调用 |

## 业务能力差异

既有 B2 低代码只有“金额阈值决定一/二级审批”，不能表达“金额 + 供应商信用 + 合作月份联动风险评分”。受限扩展定义单个纯函数：

- 签名：score_contract(amount_minor, supplier_score, months_active) -> 整数风险 0..100。
- 金额分段：<=100万元加0分，(100万元,500万元]加20分，>500万元加35分。
- 信用分：<30 加35分；30..59 加20分；>=60 加0分。
- 合作月份：<6 加25分；6..23 加10分；>=24 加0分。
- 特例：金额**严格超过200万元**且信用**严格低于45分**，总风险至少90；最终最高100。

业务 Oracle 不接受模型自评；Docker 运行 9 金额边界 × 8 信用边界 × 6 合作年限边界 = **432** 组调用，并核查整数类型、准确业务结果和代码 SHA-256。一旦失败，不会将代码加入可信 Artifact，更不会切换已发布代码。

## 最小信任链

1. 用户需求对应 B2 已声明的缺失能力，可信 Controller 选择 CUSTOM_CODE（不是已经证明大模型能在未知平台自主选择）。
2. 真实 DeepSeek 仅提议单个 source 字符串。模型没有 DB、Docker Socket、Cookie、Bearer 或发布权限。
3. 可信 Controller 严格检查 **只有一个 Python 函数**、规定参数、允许 AST（无 import/循环/任意函数调用/反射/文件/网络/复杂对象），再在真实 Docker 中编译与执行独立测试。
4. 合格代码生成带 SHA-256 的内容地址 Artifact，绑定**当前 B2 已发布 v1 的 Manifest**；模拟受授权人工审查才可以发布代码指针。模型或 Agent 直接请求发布被拒绝。
5. B2 运行态表单保存合同数据，认证浏览器 GET 风险接口触发已发布代码在沙箱运行；不同应用的记录/Artifact 不可越权访问。
6. 人工在已校验源代码中追加注释，再重新通过 432 项测试，可生成代码 v2；回滚指针至 v1。
7. 人工修改 B2 Draft 不影响已发布 v1 的代码运行；**B2 发布 v2 后绑定不同 Manifest 的旧代码拒绝运行**，回滚 B2 v1 后恢复。

## 运行与 CI

仅在**受控研究隔离环境**执行，必须安装 Python 3.13、Docker、Playwright 1.56 和 Chromium。GitHub CI 固定 Ubuntu 24.04，先 Docker pull python:3.13-alpine，再记录镜像不可变本地 image ID；所有 Docker 运行采用该 ID、禁止 runtime 在线拉取。

本地可参考：

    cd experiments/g1-b01-b4
    python3 -m unittest -v test_policy
    docker pull python:3.13-alpine
    export S1_B4_IMAGE_ID="$(docker image inspect python:3.13-alpine --format '{{.Id}}')"
    python3 experiment.py --mode offline --output /tmp/s1-b4-offline.json

CI 默认**完全离线**，不能因为模型响应失败就静默替代为 reviewed_rule.py。只有同仓库 PR HEAD Commit 消息完整匹配 `research(s1): authorize exactly one B4 DeepSeek code [b4-deepseek-once]`，且所有离线检查通过后，才注入 GitHub Secret `DEEPSEEK_KEY` 并发起**一次**真实模型请求；未知网络结果不自动重试。

## 局限与诚实边界

这是一套**纯函数代码扩展 Spike**。模型不具备通用项目目录写入、Maven/npm 构建、代码仓库提交、浏览器可视代码编辑、复杂函数调用、真实人类审批、自动修复、容器镜像构建/镜像签名、生产隔离/供应链治理。Docker 镜像每次运行以本次解析的不可变 image ID 绑定，但基础标签尚未做长期固定 digest 供应链验证。人工开发和代码审查由测试执行器模拟，不是真实自然人。Artifact 验证回执是受信 Controller 的本地对象，不是跨组织加密签名。

**B4 的所有 PASS 都不自动变成正式第一阶段 G1-B01 W01—W24 / TC01—TC18 的 FULL PASS。G1 保持 NOT_PASSED，除非正式冻结验收和重大架构风险关闭。**
