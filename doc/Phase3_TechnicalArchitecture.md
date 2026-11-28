> **2026-11-28 L3 整改架构补充（优先级高于本文历史描述）**
>
> 本项目目标调整为 GB/T 46900—2025 第 7 章**引领级**，即九个能力域全部适用 L1/L2/L3 要求。以下约束作为本阶段架构基线；旧文档中与其冲突的“可选/或”描述在 ADR 更新后必须清理。
>
> 1. **统一事实源：** 新增版本化 AppSpec/IR，覆盖 meta、dataModels、ui、forms、logic、workflows、security、integrations、i18n、deployment、extensions。设计器、Agent、编译器、运行时只能通过有版本的命令/事务修改它；Prisma/SQL、前端、BPMN、权限策略和制品由确定性编译器生成。
> 2. **前端基线：** 产品主工作台采用 React 18 + TypeScript；现有 Vanilla JS 原型仅作为可视化/交互兼容基线，完成逐页功能映射后再迁移，不得以迁移为由删减功能。
> 3. **后端基线：** NestJS + TypeScript 作为唯一平台 API 框架；不得同时维护 Express/NestJS 两套业务后端。静态原型服务器不再描述为业务 API。
> 4. **数据基线：** PostgreSQL + Prisma；统一 UUID 主键策略、关系/索引/约束生成。SaaS 共享库采用 tenant_id + PostgreSQL RLS；独立私有化部署允许独立数据库/Schema 配置。禁止动态租户表与 RLS/Schema-per-tenant 混搭形成多套事实源。
> 5. **执行边界：** LogicFlow 是短时、确定性 DAG/逻辑执行器；BPMN 由符合 BPMN 2.0 语义的流程引擎执行长周期人工流程；Temporal 用于可恢复的 Agent/后台长任务，不替代 BPMN 引擎。平台异步短任务由 Redis/BullMQ 承载，避免重复承担长流程语义。
> 6. **Agent：** AI Orchestrator 管理任务状态机、计划、工具注册、模型路由、权限、人工审批、检查点、重试/恢复、差异预览、测试验证和审计；模型不得直接持有数据库/部署凭据。
> 7. **安全：** PDP/PEP 默认拒绝、显式 deny 优先；租户、资源、行列字段和 API 权限统一策略；自定义代码/插件必须在非特权隔离沙箱运行，默认无网络，资源/时限配额与秘密代理受控。
> 8. **密码：** 删除固定 IV、进程内临时密钥和普通哈希充当完整性认证的示例。密钥由 KMS/HSM/Vault 生命周期管理；加密封装、算法模式、IV/nonce、认证标签、keyId、轮换和恢复需经密码专家评审。
> 9. **制品：** Artifact 不可变，必须含 AppSpec/schemaVersion、编译器/运行时版本、依赖锁、迁移、资源、权限、环境约束、SBOM、校验/签名和源版本；同一制品晋级各环境。
> 10. **扩展与 L3：** 架构必须支持平台级定制扩展、设备接入管理、国际化/多时区、应用市场、跨语言/跨平台开发、SDK/源码二次开发，并通过隔离、版本兼容和自动化测试验收。
>
> 具体字段、API、状态机和测试见 `doc/整改/2026-11-28_L3全量交付实施基线.md`。未完成 ADR/POC 的组件选型不得标注为生产已实现。
>
> ---
>
# OpenAILCAP 第 3 步：技术架构设计

## 3.1 技术栈最终确定（唯一基线）

> 本节取代历史版本中“Express/NestJS 可选”“Temporal 作为通用流程引擎”等互相冲突的描述。当前原型与目标生产架构分层：原型为原生 HTML/CSS/ES Modules + Node.js 内置 HTTP 静态服务器 + localStorage；生产平台目标为 React 18 + TypeScript + NestJS + PostgreSQL/Prisma。原型不是生产栈实现，不得据此推断生产后端已交付。

### 生产平台基线

| 层次 | 唯一主选型 | 职责与边界 |
|---|---|---|
| Web 工作台 | React 18 + TypeScript 5 + Vite | 生产前端；按页面功能映射逐步迁移现有原型，不允许删减入口和交互 |
| UI 组件 | Ant Design 5 + 自研设计系统 | 通用表格、表单、弹窗、反馈；设计器画布使用专用组件 |
| 路由/状态 | React Router 6 + Redux Toolkit | 路由权限、共享 AppSpec 状态、异步状态 |
| API | NestJS 10 + TypeScript | 唯一平台业务 API；静态原型服务器不承载业务 API |
| API 契约 | REST + OpenAPI 3.1 + Zod/DTO | 统一请求、响应、错误码、版本和兼容策略 |
| 数据库/ORM | PostgreSQL 15+ + Prisma 5 | 统一 UUID 主键；迁移纳入版本控制 |
| 缓存/短任务 | Redis 7 + BullMQ | 缓存、短时异步任务和重试；不承载长周期业务流程语义 |
| Agent 长任务 | Temporal | Agent 规划、检查点、恢复和长任务编排；不替代 BPMN 引擎 |
| BPMN | BPMN 2.0 兼容流程引擎（独立 ADR/POC 选型门） | 长周期人工审批、定时器、事件、补偿和流程实例 |
| LogicFlow | 自研确定性 DAG 执行器 | 短时、无持久人工等待的逻辑计算；有界执行、幂等和确定性 |
| 文件/制品 | S3 兼容对象存储 + 不可变 Artifact Registry | 上传、版本、SBOM、签名、晋级和回滚 |
| 可观测性 | OpenTelemetry + Prometheus/Grafana + 集中日志 | Trace/Metric/Log 关联、告警与审计分离 |
| 测试 | Vitest/Jest + Playwright + API/DB 集成测试 | 单元、契约、集成、浏览器 E2E、安全和恢复测试 |

### 明确禁止的混用

1. 不得同时把 Express 和 NestJS 描述为平台业务 API 主框架。
2. 不得把 Temporal、BullMQ 和 BPMN 引擎当作可互换的流程引擎。
3. SaaS 共享库统一采用 `tenant_id + PostgreSQL RLS`；私有化独立部署可配置独立数据库。禁止动态租户表与上述方案并存。
4. 所有业务模型、表单、逻辑、BPMN、权限、集成和部署描述均以版本化 AppSpec 为源；SQL/Prisma、BPMN XML、前端和权限策略是可追溯生成物。
5. 组件版本在实施仓库锁文件与 SBOM 中固定；本文版本范围是架构基线，不代表当前原型已安装或生产已验证。

### 原型与生产实现的分层

| 项目 | 当前可运行原型 | 目标生产平台 |
|---|---|---|
| 前端 | Vanilla JS ES Modules、HTML、CSS | React + TypeScript |
| 服务端 | Node.js 内置 HTTP，仅静态资源 | NestJS 业务 API |
| 状态 | 浏览器 localStorage | PostgreSQL 持久化 + Redis 缓存 |
| AI | 本地规则/模板模拟，显式 LOCAL DEMO | 受控 Agent Orchestrator + Tool Registry |
| Logic/BPM | 图结构编辑/仿真，不产生真实业务副作用 | Logic DAG 执行器 / BPMN 2.0 引擎 |
| 交付物 | 原型 JSON 配置导出 | 不可变、可签名、可晋级 Artifact |

原型代码路径与设计映射以 `doc/整改/2026-11-28_设计-原型一致性契约.md` 为准。只有生产实现及其测试证据通过后，才能将相应设计能力标记为“已实现”。

---

## 3.2 系统架构设计（C4 Model）

### Level 1：系统上下文图

```
┌─────────────────────────────────────────────────────────────┐
│                          OpenAILCAP 平台                      │
│                                                               │
│  用户在浏览器中用 AI 一句话配置低代码应用                      │
│  - 表单设计 / 工作流 / 权限 / 自定义代码                      │
│  - AI 自动生成代码、测试、部署                               │
└─────────────────────────────────────────────────────────────┘
         ▲                        ▼                     ▲
         │                        │                     │
         │                        │                     │
    开发者/                   部署到              第三方
    业务人员                 Docker/K8s         服务
         │                        │             (支付/短信)
         │                        │                     │
    邮件告警                   Git 仓库            API 网关
```

### Level 2：容器图

```
┌────────────────────────────────────────────────────────────────┐
│                        用户浏览器                              │
│  ┌─────────────────────────────────────┐                      │
│  │  OpenAILCAP Web 应用                 │                     │
│  │  (React SPA)                         │                     │
│  │  - 应用编辑器                        │                     │
│  │  - 表单设计器                        │                     │
│  │  - 工作流设计器                      │                     │
│  │  - 代码编辑器                        │                     │
│  │  - 权限管理中心                      │                     │
│  └─────────────────────────────────────┘                      │
└────────────────────────────────────────────────────────────────┘
              ▲                              ▼
              │ HTTPS/WebSocket              │ HTTP/REST
              │ (gzip压缩)                   │
              │                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                      API 网关 / 负载均衡                          │
│                    (Nginx / HAProxy)                              │
└──────────────────────────────────────────────────────────────────┘
              │
              ▼
┌──────────────────────────────────────────────────────────────────┐
│                   OpenAILCAP 后端服务                             │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ BFF 层 (Business For Frontend)                             │  │
│  │  - 应用管理 API                                            │  │
│  │  - 表单元数据 API                                          │  │
│  │  - AI 对话 API (LangChain 集成)                           │  │
│  │  - 代码生成 API                                            │  │
│  │  - 权限和审计中间件                                        │  │
│  └────────────────────────────────────────────────────────────┘  │
│                              ▼                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 核心业务服务层                                             │  │
│  │  ├─ 应用管理服务                                           │  │
│  │  ├─ 表单元数据服务                                         │  │
│  │  ├─ 工作流引擎 (Temporal 集成)                            │  │
│  │  ├─ 代码生成引擎 (AST + 模板)                             │  │
│  │  ├─ 自动测试服务 (Jest)                                   │  │
│  │  ├─ 部署管理服务 (Docker)                                 │  │
│  │  └─ 权限和审计服务                                         │  │
│  └────────────────────────────────────────────────────────────┘  │
│                              ▼                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ AI 能力层                                                  │  │
│  │  ├─ LangChain + GPT-4 / Llama                             │  │
│  │  ├─ 提示词管理和优化                                       │  │
│  │  ├─ AI 输出验证和纠正                                      │  │
│  │  └─ 用户反馈学习                                           │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
              ▼                    ▼            ▼
        ┌─────────────┐    ┌───────────┐  ┌────────────┐
        │ PostgreSQL  │    │  Redis    │  │   Minio    │
        │ 应用配置    │    │ 缓存      │  │ 文件存储   │
        │ 数据        │    │ Session   │  │ 应用包     │
        │ 审计日志    │    │ 任务队列  │  │            │
        └─────────────┘    └───────────┘  └────────────┘

              ▼                    ▼
        ┌──────────────┐    ┌────────────────┐
        │ Temporal     │    │ Docker         │
        │ 工作流执行   │    │ 代码执行沙箱   │
        │ 任务管理     │    │ 资源隔离       │
        └──────────────┘    └────────────────┘

              ▼
        ┌──────────────┐
        │ Git 仓库     │
        │ 版本管理     │
        │ 代码审计     │
        └──────────────┘
```

### Level 3：组件图（后端）

```
API 网关层：
┌─────────────────────────────────────────────────┐
│ NestJS Application (唯一平台 API)                │
│  ├─ Controller / REST API (/api/v1/*)            │
│  ├─ Guard / Interceptor / Pipe                   │
│  │  ├─ 结构化日志 / Trace Context               │
│  │  ├─ Authentication Guard                     │
│  │  ├─ PDP/PEP Authorization Guard               │
│  │  ├─ Rate Limit Guard                          │
│  │  └─ Exception Filter                         │
│  └─ DTO Validation / Request Handling           │
└─────────────────────────────────────────────────┘

业务逻辑层：
┌─────────────────────────────────────────────────┐
│ 应用管理模块                                      │
│  ├─ ApplicationService                           │
│  ├─ ApplicationRepository (Prisma)              │
│  └─ ApplicationValidator                        │
└─────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────┐
│ 表单元数据模块                                    │
│  ├─ FormService                                  │
│  ├─ FormValidator                               │
│  └─ FormRepository                              │
└─────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────┐
│ AI 代码生成模块                                   │
│  ├─ CodeGenerationService                       │
│  ├─ PromptTemplateManager                       │
│  ├─ CodeValidator (ESLint + SonarQube)         │
│  └─ TestGenerationService (Jest)               │
└─────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────┐
│ 工作流引擎模块                                    │
│  ├─ AgentTaskService (Temporal client)          │
│  ├─ BPMNParser                                  │
│  ├─ TaskService                                 │
│  └─ WorkflowMonitor                            │
└─────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────┐
│ 权限和审计模块                                    │
│  ├─ PermissionService (Casbin)                  │
│  ├─ AuditLogger                                 │
│  ├─ UserService                                 │
│  └─ RoleService                                 │
└─────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────┐
│ 部署管理模块                                      │
│  ├─ DeploymentService                           │
│  ├─ DockerBuilder                               │
│  ├─ HealthChecker                               │
│  └─ GrayReleaseManager                          │
└─────────────────────────────────────────────────┘

数据访问层：
┌─────────────────────────────────────────────────┐
│ Prisma ORM (所有模块共用)                       │
│  ├─ 数据库连接管理                               │
│  ├─ 数据迁移                                     │
│  └─ 事务管理                                     │
└─────────────────────────────────────────────────┘

外部集成：
┌─────────────────────────────────────────────────┐
│ AI 模型集成                                      │
│  ├─ OpenAI GPT-4 (via LangChain)               │
│  ├─ Llama 本地部署                             │
│  └─ 模型切换路由                                │
└─────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────┐
│ 存储系统                                         │
│  ├─ PostgreSQL 连接 (Prisma)                    │
│  ├─ Redis 客户端                                │
│  ├─ Minio 客户端                                │
│  └─ Elasticsearch 客户端                        │
└─────────────────────────────────────────────────┘
```

---

## 3.3 数据流设计

### 核心流程 1：AI 一句话生成系统

```
时序图：

用户                浏览器              后端 BFF           AI 引擎        代码生成
 │                  │                   │                 │              │
 │─ 输入需求 ───────>│                   │                 │              │
 │  "订单管理"       │─ POST /api/      │                 │              │
 │                  │  generateApp    │                 │              │
 │                  │                 │─ 提取实体 ──────>│              │
 │                  │                 │  (NLU)         │              │
 │                  │                 │                │              │
 │◄─ 显示问卷 ──────│◄─ 返回问卷        │◄─ 澄清问题      │              │
 │  (3-5个)         │  JSON            │                │              │
 │                  │                 │                │              │
 │─ 填写问卷 ───────>│                 │                │              │
 │                  │─ POST /api/     │                │              │
 │                  │  generateApp    │                │              │
 │                  │  (answers)      │                │              │
 │                  │                 │─ 生成计划 ─────>│              │
 │                  │                 │                │─ 返回计划    │
 │                  │                 │◄─ 返回计划      │              │
 │                  │◄─ 返回计划       │                │              │
 │                  │  (预计字段数等)  │                │              │
 │                  │                 │                │              │
 │─ 点击确认生成 ───>│                 │                │              │
 │                  │─ POST /api/     │                │              │
 │                  │  generateApp    │                │              │
 │                  │  (confirm)      │                │              │
 │                  │                 │                │              │
 │◄─ 显示进度条 ────│                 │                │              │
 │  (50%, 75%...)   │                 │─ 生成表单元数据 ───────────────>│
 │                  │                 │  (AST + 模板)   │◄─ 代码      │
 │                  │                 │                │              │
 │                  │                 │─ 自动单测       │              │
 │                  │                 │  (Jest)         │              │
 │                  │                 │                │              │
 │                  │                 │─ 代码审查       │              │
 │                  │                 │  (ESLint)       │              │
 │                  │                 │                │              │
 │◄─ 生成完成 ──────│◄─ 返回应用 ID   │                │              │
 │  跳转应用详情    │  和详情          │                │              │
 │                  │                 │                │              │
```

**数据流详细步骤：**

```
Step 1: 需求理解
  输入：用户文本描述
  输出：结构化需求对象
  {
    appType: "Sales Order",
    description: "订单管理系统",
    estimatedFields: 20,
    estimatedUsers: 100
  }

Step 2: 澄清对话
  输入：结构化需求
  处理：生成澄清问卷
  输出：5 个结构化问题
  [
    { question: "这是什么行业的订单？", options: [...] },
    { question: "需要多少个用户？", options: [...] },
    ...
  ]

Step 3: 需求补齐
  输入：用户回答
  处理：补充隐含需求
  输出：完整需求规格
  {
    appType: "Sales Order",
    industry: "Electronics",
    userCount: 100,
    needsInventory: true,
    needsReporting: false,
    fields: [...],
    workflow: [...],
    roles: [...]
  }

Step 4: 代码生成
  输入：完整需求规格
  处理：AST + 模板系统
  输出：
    - TypeScript 类型定义
    - Prisma Schema
    - Express Routes
    - React 表单组件

Step 5: 测试生成
  输入：生成的代码
  处理：AI 生成 Jest 单元测试
  输出：测试代码 + 覆盖率报告

Step 6: 代码审查
  输入：生成的代码 + 测试
  处理：
    - ESLint 检查
    - SonarQube 安全扫描
    - 性能检查
  输出：问题列表 + 修复建议

Step 7: 部署
  输入：审查通过的代码
  处理：
    - 存储到 Git
    - Docker 打包
    - 本地启动
  输出：应用 URL
```

---

### 核心流程 2：用户操作与权限验证

```
认证流程：
用户 ──> 登录页 ──> 输入用户名密码 ──> 后端验证 ──> 生成 JWT Token
                                        ↓
                                    存储 Redis
                                        ↓
                      返回 Token 给浏览器 (HttpOnly Cookie)

权限验证流程（每个 API 请求）：
请求 ──> 提取 Token ──> 验证签名 ──> 获取用户信息 ──> RBAC 检查
                                        ↓
                      不通过 → 403 Forbidden
                                        ↓
                      通过 → 执行业务逻辑
                                        ↓
                      返回结果

RBAC 权限模型：
用户 ──belongs to──> 角色 ──has──> 权限
              ├─ Admin
              ├─ Developer
              ├─ Reviewer
              └─ Viewer

权限类型：
  ├─ 应用级 (create_app, edit_app, delete_app, deploy_app)
  ├─ 功能级 (edit_form, view_data, modify_workflow)
  └─ 数据级 (通过 WHERE 子句在 SQL 层实现)
```

---

## 3.4 API 网关与中间件设计

### 认证与授权中间件栈

```typescript
// 中间件执行顺序
app.use(express.json());                    // 1. 解析 JSON
app.use(morgan('combined'));                 // 2. 日志
app.use(expressRateLimit());                 // 3. 速率限制
app.use(authMiddleware);                     // 4. JWT 认证
app.use(permissionMiddleware);               // 5. 权限检查
app.use(auditMiddleware);                    // 6. 审计日志
app.use(errorHandler);                       // 7. 错误处理

// 认证中间件示例
export async function authMiddleware(req, res, next) {
  const token = req.headers.authorization?.split(' ')[1];
  
  if (!token) {
    return res.status(401).json({ error: 'Missing token' });
  }
  
  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    req.user = decoded;
    next();
  } catch (error) {
    res.status(401).json({ error: 'Invalid token' });
  }
}

// 权限检查中间件示例
export async function permissionMiddleware(req, res, next) {
  const { resource, action } = req.query; // 从路由提取
  
  const hasPermission = await permissionService.check(
    req.user.id,
    resource,
    action
  );
  
  if (!hasPermission) {
    return res.status(403).json({ error: 'Forbidden' });
  }
  
  next();
}

// 审计中间件示例
export async function auditMiddleware(req, res, next) {
  const originalSend = res.send;
  
  res.send = function(data) {
    // 记录请求和响应
    auditService.log({
      userId: req.user.id,
      method: req.method,
      path: req.path,
      statusCode: res.statusCode,
      timestamp: new Date(),
      details: req.body
    });
    
    originalSend.call(this, data);
  };
  
  next();
}
```

---

## 3.5 部署拓扑

### MVP 本地部署（docker-compose）

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: openailcap
      POSTGRES_PASSWORD: dev_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  minio:
    image: minio/minio:latest
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data
    command: server /data --console-address ":9001"

  temporal:
    image: temporalio/auto-setup:latest
    environment:
      TEMPORAL_PERSISTENCE_DEFAULT_SCHEMA: temporal
      TEMPORAL_PERSISTENCE_VISIBILITY_SCHEMA: temporal_visibility
    ports:
      - "7233:7233"
      - "6233:6233"
    depends_on:
      - postgres

  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    environment:
      NODE_ENV: development
      DATABASE_URL: postgresql://postgres:dev_password@postgres:5432/openailcap
      REDIS_URL: redis://redis:6379
      JWT_SECRET: your_jwt_secret_here
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    ports:
      - "3001:3001"
    depends_on:
      - postgres
      - redis
      - minio
      - temporal
    volumes:
      - ./src:/app/src

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend
    environment:
      REACT_APP_API_URL: http://localhost:3001

volumes:
  postgres_data:
  redis_data:
  minio_data:
```

---

## 3.6 可扩展性设计

### 多租户架构

```
Schema 级隔离（MVP 推荐）：

PostgreSQL:
  public schema
    ├─ users (全局用户)
    ├─ tenants (租户信息)
    └─ tenant_configs (租户配置)
  
  schema: tenant_001
    ├─ applications
    ├─ forms
    ├─ form_data
    ├─ workflows
    ├─ audit_logs
    └─ ...
  
  schema: tenant_002
    ├─ applications
    ├─ forms
    ├─ ...
    
查询自动加租户过滤：
  SELECT * FROM tenant_001.forms WHERE app_id = ?

Redis:
  tenant_001:session:* (用户 session)
  tenant_001:cache:forms:* (表单缓存)
  tenant_002:session:*
  ...

隔离优势：
  ✓ 数据完全隔离
  ✓ 性能良好
  ✓ 易于备份恢复
  ✓ 安全性高
```

### 水平扩展策略

```
后端扩展：
  1 个后端 → N 个后端（Kubernetes + HPA）
  负载均衡：Nginx / HAProxy
  
缓存扩展：
  Redis Sentinel (高可用)
  Redis Cluster (大数据量)
  
数据库扩展：
  Read 副本（查询扩展）
  Sharding（写扩展）
  
任务处理扩展：
  Bull 队列自动分布式
  Temporal 分布式工作流
```

---

## 3.7 安全架构

```
分层安全模型：

┌─ 传输层安全 ────────────┐
│ ✓ TLS 1.3                │
│ ✓ HSTS                   │
│ ✓ CORS 白名单            │
└──────────────────────────┘
         ↓
┌─ 认证层 ────────────────┐
│ ✓ JWT + HttpOnly Cookie  │
│ ✓ 密码加密 (bcrypt)      │
│ ✓ 多因素认证 (MFA)       │
└──────────────────────────┘
         ↓
┌─ 授权层 ────────────────┐
│ ✓ RBAC 基础模型          │
│ ✓ ABAC 属性条件          │
│ ✓ 细粒度权限             │
└──────────────────────────┘
         ↓
┌─ 应用层安全 ────────────┐
│ ✓ 输入验证               │
│ ✓ SQL 参数化查询         │
│ ✓ XSS 防护               │
│ ✓ CSRF 令牌              │
│ ✓ 速率限制               │
│ ✓ WAF 规则               │
└──────────────────────────┘
         ↓
┌─ 数据安全 ────────────────┐
│ ✓ 存储加密 (AES-256)       │
│ ✓ 敏感字段掩盖            │
│ ✓ 备份加密                │
│ ✓ 数据隐私 (GDPR)         │
└────────────────────────────┘
         ↓
┌─ 审计与监控 ────────────┐
│ ✓ 完整审计日志           │
│ ✓ 不可篡改日志           │
│ ✓ 实时告警               │
│ ✓ 安全事件记录           │
└──────────────────────────┘
```

---

## 3.8 性能指标与 SLA

```
性能目标：

指标                      | MVP 目标    | 生产目标   | 测试方法
---|---|---|---
API 响应时间 (95分位)      | <500ms      | <300ms    | 压测
首屏加载时间               | <2s         | <1s       | 灯塔审计
并发用户数                 | 100+        | 1000+     | JMeter
吞吐量 (req/sec)           | 1000+       | 5000+     | 压测
可用性 (SLA)               | 99%         | 99.5%     | 监控
错误率                     | <0.1%       | <0.01%    | 监控

SLA 承诺：
  ✓ 生产：99.5% 可用性
  ✓ RTO (恢复时间目标) ≤ 5 分钟
  ✓ RPO (恢复点目标) ≤ 15 分钟
  ✓ 周期性备份：每 4 小时一次
```

---

## 3.9 交付物清单

```
架构设计：
[✓] C4 Model (System Context / Container / Component / Code)
[✓] 数据流设计 (核心 2 个流程)
[✓] API 网关设计
[✓] 中间件栈设计
[✓] 部署拓扑 (docker-compose)
[✓] 多租户隔离方案
[✓] 水平扩展策略
[✓] 安全架构
[✓] 性能指标和 SLA

技术规范：
[✓] 技术栈确定
[✓] 开源库选择 (前端 15+ 库, 后端 10+ 库)
[✓] 数据库设计初稿
[✓] API 设计规范

运维设计：
[✓] 本地开发环境 (docker-compose)
[✓] 监控和告警策略
[✓] 日志聚合方案
[✓] 灾难恢复方案
```

---

**第 3 步完成时间：1-1.5 周**

**下一步：第 4 步 - 细化功能设计**
  - 7 个核心模块的详细需求
  - 页面设计（粒度到按钮）
  - 数据库设计详稿

