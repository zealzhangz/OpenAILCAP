# OpenAILCAP

> **AI-Native Low-Code Application Platform**  
> 目标：以 AI Agent 驱动、人机协同的方式完成应用需求澄清、AppSpec 建模、生成、验证和交付。

## 项目状态（2026-11-28）

本仓库处于详细设计与交互原型整改阶段。目标对标 GB/T 46900—2025 第 7 章引领级，但**当前不宣称已达到引领级或已通过标准评估**。设计目标、原型交互、生产实现、自动化验证和独立复核分别统计；没有实现和证据的能力不计为已交付。

- 详细设计：持续整改，技术架构、模块设计和原型契约以 `doc/Phase3_TechnicalArchitecture.md`、`doc/Phase4_*` 和 `doc/整改/` 为准。
- 原型：可运行的原生 HTML/CSS/JavaScript 交互式 UI 演示，使用浏览器 `localStorage`；不是生产平台或 Phase 5 技术 POC。
- 生产目标架构：React + TypeScript、NestJS、PostgreSQL/Prisma；生产服务尚不能因设计文档存在而视为已实现。
- AppSpec：已有 1.0.0 JSON Schema 和浏览器端轻量校验器；服务端完整校验、持久化、迁移、编译器和生产运行时仍待实现。
- AI：原型中的 AI 功能以本地规则/模板模拟为主；真实 LLM、Agent Orchestrator、工具权限、检查点和恢复链路待实现。
- LogicFlow/BPMN：原型支持部分图编辑、结构校验和仿真；真实 DAG 执行器和 BPMN 2.0 流程引擎待实现。
- 测试：现有 CI 包含静态/语法检查；不等同于浏览器 E2E、数据库集成、安全、性能或国标独立评估。

## 设计与原型一致性

双向追踪基线：`doc/整改/2026-11-28_设计-原型一致性契约.md`。

该契约明确 18 个工作区的路由、模块脚本、演示状态、AppSpec 映射、目标 API、权限/审计要求和验收状态。任何设计或原型变更都必须同步更新对应映射和测试，不得出现“文档已设计、原型无入口”或“原型有操作、设计无规则”的单边变更。

## 核心文档

| 文档 | 内容 |
|---|---|
| `doc/Phase3_TechnicalArchitecture.md` | 生产目标架构与唯一技术基线 |
| `doc/Phase4_DetailedDesign_Enhanced.md` | 14 个模块及跨模块详细设计约束 |
| `doc/Phase4_DetailedFunctionalDesign.md` | 功能流程与业务规则 |
| `doc/Phase4_TechStack_Deployment.md` | 技术栈、部署、运维与恢复设计 |
| `doc/Phase4_TechnicalImplementation.md` | 生成器、服务和工程实现设计 |
| `doc/Phase5_Prototype_Design.md` | 原型交互目标、边界和验收标准 |
| `doc/architecture/ADR-0001-AppSpec-as-canonical-IR.md` | AppSpec 作为统一应用元模型的决策 |
| `doc/architecture/schemas/app-spec-1.0.0.schema.json` | AppSpec 1.0.0 JSON Schema |
| `doc/整改/2026-11-28_设计-原型一致性契约.md` | 设计—原型双向追踪契约 |
| `doc/整改/2026-11-28_功能保留与验收追踪矩阵.md` | 原有功能保留和验收矩阵 |
| `doc/整改/GB-T46900-2025_39子域追踪台账.md` | 标准能力域/子域追踪台账 |
| `doc/reviews/2026-11-28_详细设计与原型设计评审报告.md` | 评审问题及整改依据 |

## 运行交互式原型

要求 Node.js 18+，无需安装第三方依赖：

```bash
cd openailcap-prototype
node server.js
```

访问 `http://localhost:3000`。

原型会在每个工作区顶部显示“交互式原型 / localStorage / 非生产后端”提示。页面中的数据、AI 输出、流程仿真和部署状态均按其真实能力标识，不可作为生产能力或国标符合性证据。

运行静态检查：

```bash
npm test
```

## 交付原则

1. 原有 14 模块、18 工作区和 AI 入口全量保留；任何删减必须有明确批准和替代映射。
2. AppSpec 是设计器、Agent、编译器和运行时共享的统一应用定义；各模块不得维护互相矛盾的事实源。
3. 设计、原型、生产实现、自动化验证、独立复核分开记录，不用页面数量或静态检查替代功能验收。
4. 不将目标指标、演示数据、固定样例、Toast 或 localStorage 操作标记为生产完成。
5. PR 必须说明修改的设计章节、原型页面/脚本、映射契约、测试证据和剩余差距；未完成时保持 Draft。

## 许可证与标准

标准对标工作以适用条款原文及可复核证据为依据。仓库中的映射表和追踪台账不是认证结论，也不替代第三方或独立符合性评估。
