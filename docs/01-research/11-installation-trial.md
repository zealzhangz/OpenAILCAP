# S1 真实平台安装可行性试验（包含失败证据）

> 研究日期：2026-11-21。结果：**BLOCKED，平台未成功安装，合同业务场景未执行**。这是一项独立试验的真实失败，不应计为通过。

## 一、为什么选择 NocoBase v3 先试

四项目中，NocoBase v3 官方文档给出了以 Node.js 24、pnpm 11 和 SQLite 初始化应用的路径，不需要预先部署 PostgreSQL/Redis/Docker。官方 [CLI 参考](https://docs.nocobase.com/core/reference/cli/) 定义了 `config init`、`config check`、`commands --json` 等机器可读入口，可验证 OpenAILCAP 所关心的应用能力发现。

但由于 v3 LICENSE.txt 对 AI 平台 SaaS/PaaS、代码再分发附带限制，本试验仅为**短时、隔离的第三方安装调研**；不拷贝其源码到 OpenAILCAP，不将其当作产品内核。

## 二、真实执行信息

| 字段 | 值 |
|---|---|
| GitHub Commit | [567395ae](https://github.com/zealzhangz/OpenAILCAP/commit/567395ae695b5780d7f6a1071c0ea5d0214acaa4) |
| Workflow | [s1-nocobase-smoke.yml](../../.github/workflows/s1-nocobase-smoke.yml) |
| 真实运行记录 | [Actions Run #44868550471](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44868550471) |
| Job ID | 136737649054 |
| 运行环境 | GitHub-hosted Ubuntu runner |
| Node 版本 | **24.22.3** |
| pnpm 版本 | **11.11.0** |
| 运行结论 | **completed / failure** |
| 失败步骤 | Create isolated research app using NocoBase official CLI |
| 创建器返回状态 | `create-app: failure` |
| 创建器错误码 | **TEMPLATE_DOWNLOAD_FAILED** |
| npm 诊断 | **E530**，GET `https://npm.nocobase.ai/@nocobase%2fapp-template-default` |
| 安装结果 | projectCreated=false，dependenciesInstalled=false |

使用官方文档给出的非交互创建命令，以单独环境设置 npm 包源，计划执行：

~~~bash
PNPM_CONFIG_MINIMUM_RELEASE_AGE=0 \
npm_config_registry=https://npm.nocobase.ai \
pnpm create @nocobase/app contract-probe --json

# 只有成功创建工程后才运行：
pnpm nocobase config init --dialect sqlite --json
pnpm nocobase config check --no-connect --json
pnpm nocobase commands --json
~~~

实际在下载默认模板阶段停止，之后的配置验证和 CLI 查询**均未运行**。本次程序输出不包含实际业务接口、页面或数据库状态。CI 的 Artifact 未产生，因为创建项目尚未成功。

## 三、故障归因和不应推断的内容

**已证实事实**：CI 能下载并安装 Node 24、pnpm 11，调用创建器成功进入模板下载阶段；获取默认模板时 registry 响应 npm E530；因此应用没有成功生成。

**当前无法证实**：是包仓库暂时不可用、特定网络出口被拒绝、仓库鉴权策略、包版本/标签变化、还是上游发布故障。本研究未使用第三方凭据，不尝试绕过权限或猜测内部包仓库地址。

**不能宣称** NocoBase v3 一般不可安装、没有低代码能力，或 OpenAILCAP 的合同应用在该产品上测试失败。**业务场景根本没有开始**。

## 四、下一步可复现路径

| 路径 | 先决条件 | 当前处置 |
|---|---|---|
| A. NocoBase v3 官方渠道 | 验证 registry 和模板包实际可公开获取，确认项目/标签/许可 | 保留 E530 证据并向官方核实，暂不重复无意义重试 |
| B. Appsmith CE | GitHub 以 Apache-2.0 授权；按[官方 Docker 文档](https://docs.appsmith.com/getting-started/setup/installation-guides/docker) 使用适当版本的 CE 镜像；官方建议 all-in-one 至少 8 GB RAM | **未执行**；需要足够资源的 Docker 主机并固定镜像 digest |
| C. Budibase 自托管 | 按 [官方 Compose 文档](https://docs.budibase.com/docs/docker-compose) 安装 Docker/Compose、附属服务，核查各包的许可 | **未执行**；需多个容器和服务可用 |
| D. ToolJet CE | 可以研究可视化低代码链路；其 Code Mode 服务端 CE 实现为 stub | **未执行**；不得用 EE AI/Code Mode 结果当作 CE 功能 |

不宜在资源不满足条件的 GitHub runner 上强行运行大型生产级镜像，然后用 OOM 错误推断平台不可用。

## 五、G1 的影响

第一阶段最重要的缺口仍是**一套真实部署的参考平台，产生可以独立读回的业务对象与界面运行行为**。此试验只把“安装与包仓库可达性”作为明确风险暴露出来，并提供可复核失败证据。

对应 [能力矩阵](09-capability-matrix.md)、[统一合同场景协议](10-contract-benchmark.md) 和 [G1 阶段复审](12-g1-gap-review.md)。
