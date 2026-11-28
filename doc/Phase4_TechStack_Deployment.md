> **2026-11-28 技术栈与部署补充：唯一基线要求**
>
> 评审报告指出 Express/NestJS、Temporal/Bull、租户隔离和流程执行职责冲突。整改期间以 `doc/Phase3_TechnicalArchitecture.md` 顶部架构补充为准，必须通过 ADR 固化组件职责、版本、部署拓扑、故障模式、升级策略和许可证。NestJS 是唯一平台 API 框架；PostgreSQL/Prisma 是统一业务数据基线；BPMN 引擎、LogicFlow 执行器、Agent 长任务和短任务队列职责分离。
>
> 部署交付必须覆盖单机开发、测试/预发/生产、多节点高可用、离线/私有化、升级回滚、备份恢复、监控日志追踪、密钥管理、SBOM 和灾备演练。多环境晋级复用同一不可变 Artifact，禁止在生产环境临时重新编译。
>
># OpenAILCAP 技术栈清单 & 部署方案
# MVP 完整技术规范

**版本：** v1.0  
**日期：** 2026-11-28  
**目标：** 生产就绪、国标达标、可维护

---

## 一、完整技术栈清单

### 1.1 前端技术栈

#### 核心框架

```
React 18.2+
├─ 核心库版本固定
├─ TypeScript 5.0+ (严格模式)
├─ ESM 模块支持
└─ 单文件组件推荐 (SFC)

依赖管理:
├─ pnpm (速度快、节省空间)
├─ npm workspace (单体仓库)
└─ 锁文件: pnpm-lock.yaml
```

#### UI 框架与组件库

```
推荐方案 (二选一):

方案 A: Ant Design (更成熟，更多组件)
├─ antd ^5.10.0
├─ @ant-design/icons ^5.2.0
├─ @ant-design/pro-layout ^7.0.0 (后台布局)
└─ 中英文支持完美

方案 B: Material-UI (国际化友好，轻量)
├─ @mui/material ^5.14.0
├─ @mui/icons-material ^5.14.0
├─ @mui/lab ^5.0.0
└─ 官方 i18n 支持好

选择: 推荐方案 A (Ant Design) - 国内生态更完善
```

#### 状态管理

```
Redux Toolkit (推荐) / Zustand (轻量)

选择 Redux Toolkit 原因:
✅ 中大型应用标准选择
✅ DevTools 调试能力强
✅ TypeScript 支持完美
✅ 中文社区完善

版本和依赖:
├─ @reduxjs/toolkit ^1.9.0
├─ react-redux ^8.1.0
├─ redux-persist ^6.0.0 (状态持久化)
├─ redux-logger ^3.0.6 (开发时日志)
└─ redux-thunk (异步操作)
```

#### 路由与导航

```
React Router v6+
├─ react-router-dom ^6.14.0
├─ 嵌套路由支持
├─ 权限路由 HOC 包装
└─ 路由权限管理集成
```

#### HTTP 客户端

```
Axios + 自定义拦截器

依赖:
├─ axios ^1.5.0
├─ 请求拦截 (添加 auth token)
├─ 响应拦截 (错误处理、国标错误码映射)
├─ 超时配置 (30s)
└─ 重试逻辑 (失败重试 3 次)
```

#### 表单管理

```
React Hook Form + Zod (推荐)

依赖:
├─ react-hook-form ^7.45.0
├─ zod ^3.22.0 (Schema 验证)
├─ @hookform/resolvers ^3.3.0
└─ 轻量高效，零 re-render 问题
```

#### 可视化编辑器

```
关键编辑器需求:

1. 表单设计器:
   ├─ Formily (阿里开源，企业级)
   ├─ or react-json-schema-form
   └─ 或基于 React DnD 自研

2. 流程设计器 (BPM):
   ├─ bpmn-io / bpmn.js (标准 BPMN 编辑)
   ├─ or X6 (蚂蚁集团，图编辑库)
   └─ 推荐 X6 (更灵活，国内支持好)

3. ER 图/数据建模:
   ├─ Mxgraph (强大，学习曲线陡)
   ├─ or Cytoscape.js (图表库)
   ├─ or React Flow (轻量，推荐)
   └─ 推荐 React Flow (易用性最好)

4. 逻辑编排:
   ├─ React Flow (节点编排通用)
   └─ or X6

5. 代码编辑器:
   ├─ Monaco Editor (VS Code 同源)
   ├─ or Ace Editor
   └─ 推荐 Monaco (@monaco-editor/react)

6. 大屏数据可视化 (P1):
   ├─ ECharts (功能最全，学习成本高)
   ├─ or Recharts (React 友好，功能适中)
   ├─ or Chart.js (简单直观)
   └─ 推荐 ECharts (功能最全)
```

#### 多语言 (i18n)

```
i18next + react-i18next

依赖:
├─ i18next ^23.5.0
├─ react-i18next ^13.2.0
├─ i18next-browser-languagedetector ^7.1.0
├─ i18next-http-backend ^2.4.0
└─ 完整的多语言解决方案
```

#### 时间处理

```
Day.js (轻量) / Moment.js (功能全)

推荐 Day.js:
├─ dayjs ^1.11.9
├─ 体积小 (仅 2KB)
├─ Moment.js 兼容 API
├─ 支持时区 (dayjs-timezone)
└─ 中英文 locale 完整
```

#### 工具库

```
Lodash ES (树摇优化)
├─ lodash-es ^4.17.21
├─ 仅导入需要的函数
└─ 不会引入整个库

Classnames
├─ classnames ^2.3.2
├─ 条件 CSS 类名组合

Query String Parser
├─ qs ^6.11.2
├─ 复杂 query 参数解析
```

#### 开发工具

```
构建工具:
├─ Vite 5.0+ (推荐)
├─ or Webpack 5
└─ 配合 TypeScript

代码质量:
├─ ESLint ^8.49.0
├─ Prettier ^3.0.0
├─ husky + lint-staged (Pre-commit 钩子)
└─ StyleLint (样式检查)

测试框架:
├─ Vitest (Vite 原生，速度快)
├─ or Jest
├─ React Testing Library (@testing-library/react)
├─ Cypress (E2E 测试)
└─ 覆盖率目标: >80%
```

#### 版本固定清单 (package.json)

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.14.0",
    "axios": "^1.5.0",
    "@reduxjs/toolkit": "^1.9.0",
    "react-redux": "^8.1.0",
    "react-hook-form": "^7.45.0",
    "zod": "^3.22.0",
    "antd": "^5.10.0",
    "@ant-design/icons": "^5.2.0",
    "i18next": "^23.5.0",
    "react-i18next": "^13.2.0",
    "dayjs": "^1.11.9",
    "lodash-es": "^4.17.21",
    "classnames": "^2.3.2",
    "qs": "^6.11.2",
    "@monaco-editor/react": "^4.5.0",
    "xflow": "^0.9.0",
    "react-flow-renderer": "^10.3.17",
    "echarts": "^5.4.0"
  },
  "devDependencies": {
    "typescript": "^5.0.0",
    "vite": "^5.0.0",
    "@vitejs/plugin-react": "^4.0.0",
    "eslint": "^8.49.0",
    "prettier": "^3.0.0",
    "vitest": "^0.34.0",
    "@testing-library/react": "^14.0.0",
    "cypress": "^13.3.0",
    "husky": "^8.0.3",
    "lint-staged": "^14.0.1"
  }
}
```

---

### 1.2 后端技术栈

#### 运行时 & 框架

```
Node.js 18 LTS+ (长期支持版本)

框架: NestJS 10+
├─ @nestjs/core ^10.2.0
├─ @nestjs/common ^10.2.0
├─ TypeScript 5.0+ (严格模式)
└─ 企业级框架，完美 TypeScript 支持
```

#### 数据库 ORM

```
Prisma (推荐) / TypeORM

选择 Prisma 原因:
✅ 现代 ORM，类型安全
✅ 自动迁移生成
✅ 可视化数据浏览器
✅ 支持多数据源

依赖:
├─ @prisma/client ^5.3.0
├─ prisma ^5.3.0 (dev)
└─ 迁移文件版本控制
```

#### 数据库

```
PostgreSQL 15+ (主库)
├─ 完整 ACID 支持
├─ JSON 类型支持
├─ 权限管理完善
├─ 适合企业应用

Redis 7+ (缓存 & 会话)
├─ 分布式缓存
├─ 会话存储
├─ 任务队列 (Bull)
└─ 单机足以支撑 MVP
```

#### API & 通信

```
REST API (HTTP)
├─ 主要使用
├─ OpenAPI 3.0 Spec 文档
└─ 国际化错误码标准化

WebSocket (后续可选)
├─ 用于实时推送
├─ 流程实例监控
└─ P1 功能

依赖:
├─ @nestjs/websockets (后续)
├─ socket.io (后续)
└─ 现在暂不集成
```

#### 安全 & 认证

```
JWT (访问令牌)
├─ @nestjs/jwt ^11.0.0
├─ jsonwebtoken ^9.1.0
└─ 无状态认证

会话管理:
├─ express-session
├─ connect-redis (会话存储)
└─ 安全 cookie

国密支持:
├─ tongsuo (国密 SSL)
├─ or gmssl
├─ sm2/sm3/sm4 加解密
└─ 密钥轮换策略

其他:
├─ bcrypt (密码哈希)
├─ helmet (HTTP 安全头)
├─ cors (跨域管理)
└─ rate-limiting (限流)
```

#### 日志 & 监控

```
日志库:
├─ winston ^3.11.0 (主库)
├─ @nestjs/common Logger (适配器)
├─ pino (可选，更快)
└─ 分级日志 (debug/info/warn/error)

监控:
├─ OpenTelemetry (标准方案)
├─ jaeger (分布式追踪)
├─ prometheus (指标收集)
└─ 后续集成，MVP 先用简单日志

审计日志:
├─ 操作日志数据库表
├─ SM3 完整性校验
├─ 数据加密存储
└─ 查询与报告 API
```

#### 任务队列

```
Bull (基于 Redis)

依赖:
├─ bull ^4.11.0
├─ @nestjs/bull ^10.0.0
└─ 用于:
   ├─ 定时任务 (Cron)
   ├─ 异步任务
   ├─ 重试机制
   └─ 应用导出/生成

or Agenda / Bee-Queue 也可
```

#### 文件存储

```
对象存储 (MVP 推荐):

本地存储 (开发):
├─ 文件系统存储
├─ 适合开发测试
└─ 简单直接

云存储 (生产):
├─ AWS S3 / 兼容 (MinIO)
├─ 阿里云 OSS
├─ 腾讯云 COS
└─ 推荐 MinIO (自主部署) 或云厂商

依赖:
├─ aws-sdk (S3 兼容)
├─ or minio (开源)
└─ multer (文件上传中间件)
```

#### 验证 & 数据校验

```
class-validator (装饰器风格)
├─ class-validator ^0.14.0
├─ class-transformer ^0.5.1
├─ 配合 Prisma 或 TypeORM
└─ DTO 验证标准

or Zod (Schema 风格)
├─ zod ^3.22.0
├─ 类型推断能力强
└─ 轻量级
```

#### 版本固定清单 (package.json)

```json
{
  "dependencies": {
    "@nestjs/core": "^10.2.0",
    "@nestjs/common": "^10.2.0",
    "@nestjs/platform-express": "^10.2.0",
    "@nestjs/jwt": "^11.0.0",
    "@nestjs/passport": "^10.0.0",
    "@prisma/client": "^5.3.0",
    "typescript": "^5.0.0",
    "class-validator": "^0.14.0",
    "class-transformer": "^0.5.1",
    "bcrypt": "^5.1.0",
    "jsonwebtoken": "^9.1.0",
    "winston": "^3.11.0",
    "bull": "^4.11.0",
    "redis": "^4.6.0",
    "aws-sdk": "^2.1.0",
    "multer": "^1.4.5",
    "helmet": "^7.0.0",
    "cors": "^2.8.5",
    "dotenv": "^16.3.1"
  },
  "devDependencies": {
    "prisma": "^5.3.0",
    "@nestjs/testing": "^10.2.0",
    "jest": "^29.7.0",
    "@types/node": "^20.5.0",
    "@types/jest": "^29.5.0",
    "ts-node": "^10.9.1",
    "ts-jest": "^29.1.0"
  }
}
```

---

### 1.3 基础设施 & DevOps

#### 容器化

```
Docker (容器引擎)

前端 Dockerfile:
├─ Node 构建阶段 (Build)
├─ Nginx 运行阶段 (Runtime)
├─ 多阶段构建优化镜像大小
└─ 安全扫描 (Trivy)

后端 Dockerfile:
├─ Node 多阶段构建
├─ 健康检查配置
├─ 资源限制
└─ 安全最小权限运行

Docker Compose:
├─ 本地开发环境编排
├─ PostgreSQL + Redis + App
└─ 一键启动开发环境
```

#### 编排 & 部署

```
推荐方案 (二选一):

方案 A: Kubernetes (K8s)
├─ 生产级容器编排
├─ 自动扩缩容
├─ 高可用配置
├─ 推荐用于生产
└─ 学习曲线陡

方案 B: Docker Swarm / Docker Compose
├─ 轻量级编排
├─ MVP 推荐
├─ 易部署易维护
└─ 足以支撑 1-2 年

选择: MVP 用 Docker Compose，后续迁移 K8s

配置:
├─ Deployment (前端 + 后端)
├─ Service (负载均衡)
├─ ConfigMap (配置注入)
├─ Secret (敏感信息)
├─ PersistentVolume (数据持久化)
└─ Ingress (七层路由)
```

#### CI/CD 流程

```
代码仓库: GitHub / GitLab

推荐 GitHub Actions (内置免费):
├─ 触发条件: PR + Push to main
├─ 流程:
│  ├─ 1. 代码检查 (ESLint/TypeScript)
│  ├─ 2. 单元测试 (Jest/Vitest >80%)
│  ├─ 3. 构建镜像 (Docker)
│  ├─ 4. 推送镜像 (Docker Registry)
│  ├─ 5. 部署测试环境 (Staging)
│  └─ 6. 冒烟测试
│
└─ 工作流文件: .github/workflows/ci-cd.yml

or GitLab CI:
├─ .gitlab-ci.yml 配置
├─ Runner 管理
└─ 功能类似
```

#### 注册表 & 镜像管理

```
镜像仓库 (二选一):

选项 A: Docker Hub (公开免费)
├─ docker.io/yourname/openailcap
├─ 适合开源项目
└─ 推送速度依赖网络

选项 B: GitHub Container Registry (推荐)
├─ ghcr.io/yourname/openailcap
├─ 与 GitHub 集成
├─ 私有镜像支持
└─ 国内访问较慢

选项 C: 自建 Harbor 或 Nexus
├─ 企业级方案
├─ 完全自主控制
└─ MVP 暂不考虑

选择: 推荐 GitHub Container Registry
```

#### 监控 & 日志收集

```
日志:
├─ ELK Stack (Elasticsearch + Logstash + Kibana)
├─ or Loki + Grafana (轻量)
├─ 推荐 Loki (MVP 足够)
└─ 收集容器日志、应用日志

监控指标:
├─ Prometheus (指标收集)
├─ Grafana (可视化)
├─ 监控 CPU/内存/磁盘/网络
├─ 应用 QPS/错误率/响应时间
└─ 告警规则配置

分布式追踪 (后续):
├─ Jaeger (or Zipkin)
└─ OpenTelemetry 集成

现在 MVP 配置:
├─ 应用日志输出到 stdout
├─ Docker 日志驱动收集
└─ 简单监控告警即可
```

#### 密钥管理

```
环境变量管理:
├─ .env.local (开发，不提交)
├─ .env.example (模板，提交)
├─ GitHub Secrets (CI/CD 敏感信息)
└─ Docker Secrets (Swarm)

密钥存储 (后续):
├─ HashiCorp Vault (企业级)
├─ or AWS Secrets Manager
└─ 密钥轮换自动化

MVP 方案:
├─ GitHub Secrets
├─ 环境变量注入
└─ 简单直接
```

---

## 二、完整部署拓扑图

### 2.1 MVP 部署架构

```
┌─────────────────────────────────────────────────────────┐
│                       用户浏览器                          │
└──────────────┬──────────────────────────────────────────┘
               │ HTTPS
┌──────────────▼──────────────────────────────────────────┐
│                      CDN / WAF                           │
│          (可选：Cloudflare / 国内 CDN)                  │
└──────────────┬──────────────────────────────────────────┘
               │ HTTPS
┌──────────────▼──────────────────────────────────────────┐
│                   Reverse Proxy                          │
│          (Nginx / Traefik / Caddy)                      │
├─────────────────┬──────────────────────────────────────┤
│                 │                                        │
│    ┌────────────▼─────────┐    ┌──────────────────┐    │
│    │  前端应用             │    │  后端 API        │    │
│    │  (React SPA)          │    │  (NestJS)        │    │
│    │  :3000               │    │  :8000           │    │
│    └────────────┬─────────┘    └────────┬─────────┘    │
└─────────────────┼────────────────────────┼──────────────┘
                  │                        │
                  │ Static Assets          │ API Requests
        ┌─────────▼─────────┐    ┌────────▼────────┐
        │  OSS / S3         │    │  PostgreSQL     │
        │  (镜像/文件)      │    │  (数据库)       │
        │  和 Nginx 缓存     │    │  :5432          │
        └───────────────────┘    └────────┬────────┘
                                          │
                                 ┌────────▼────────┐
                                 │   Redis         │
                                 │ (缓存/队列)     │
                                 │ :6379          │
                                 └─────────────────┘

监控告警:
├─ Prometheus scrape 后端 metrics
├─ Loki 收集容器日志
└─ Grafana 可视化
```

### 2.2 生产部署清单

```
服务器配置:

前端 Nginx 服务器:
├─ CPU: 2核
├─ 内存: 2GB
├─ 存储: 10GB
└─ 带宽: 1Mbps

后端 Node.js 应用:
├─ CPU: 4核 (可扩展)
├─ 内存: 4GB (可扩展)
├─ 存储: 20GB (日志)
└─ 带宽: 2Mbps

PostgreSQL 数据库:
├─ CPU: 4核
├─ 内存: 8GB
├─ 存储: 100GB+ (根据数据量)
└─ 备份: 自动每天备份

Redis 缓存:
├─ CPU: 2核
├─ 内存: 4GB
├─ 存储: 10GB (AOF 持久化)
└─ 备份: RDB 快照

总计预估:
├─ 阿里云: ≈ 3000-5000 元/月
├─ 腾讯云: ≈ 3000-5000 元/月
├─ AWS: ≈ $300-500/月
└─ 自建: 初期投入 2-3 万，月运维成本 1-2 万
```

---

## 三、开发环境本地部署

### 3.1 Docker Compose 配置

```yaml
# docker-compose.yml

version: '3.8'

services:
  # PostgreSQL 数据库
  postgres:
    image: postgres:15-alpine
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: openailcap
      POSTGRES_PASSWORD: dev_password
      POSTGRES_DB: openailcap_dev
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U openailcap"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis 缓存
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # 后端 API
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://openailcap:dev_password@postgres:5432/openailcap_dev
      REDIS_URL: redis://redis:6379
      NODE_ENV: development
      JWT_SECRET: dev_secret_key_do_not_use_in_production
    volumes:
      - ./backend/src:/app/src
      - ./backend/node_modules:/app/node_modules
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: npm run dev

  # 前端应用
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports:
      - "3000:3000"
    volumes:
      - ./frontend/src:/app/src
      - ./frontend/node_modules:/app/node_modules
    environment:
      REACT_APP_API_URL: http://localhost:8000
      REACT_APP_ENV: development
    command: npm run dev
    depends_on:
      - backend

volumes:
  postgres_data:
  redis_data:
```

### 3.2 快速启动命令

```bash
# 一键启动开发环境
docker-compose up -d

# 查看日志
docker-compose logs -f

# 执行数据库迁移
docker-compose exec backend npx prisma migrate dev

# 生成 Prisma 客户端
docker-compose exec backend npx prisma generate

# 停止环境
docker-compose down

# 完全清理 (包括数据)
docker-compose down -v
```

---

## 四、版本号管理

### 4.1 语义化版本 (Semantic Versioning)

```
格式: MAJOR.MINOR.PATCH

示例: 2.0.0
      ↑    ↑   ↑
      │    │   └─ PATCH: 修复 bug（不影响 API）
      │    └────── MINOR: 新功能（向后兼容）
      └─────────── MAJOR: 大版本（可能不兼容）

MVP 版本: 2.0.0
├─ 2.0.0 MVP 发布
├─ 2.0.1 bugfix 版本
├─ 2.1.0 新功能版本 (Q1)
├─ 3.0.0 重大升级 (Q2+)
└─ 保持稳定版本供用户使用
```

### 4.2 发布流程

```
1. 增加版本号
   ├─ package.json version 字段
   ├─ backend/package.json
   └─ frontend/package.json

2. 生成 Changelog
   ├─ CHANGELOG.md 更新
   ├─ 记录新功能、修复、破坏性变更
   └─ 格式参考: Keep a Changelog

3. 创建 Git Tag
   ├─ git tag -a v2.0.0 -m "Release version 2.0.0"
   ├─ git push origin v2.0.0
   └─ GitHub Release 页面发布

4. 构建发布产物
   ├─ Docker 镜像打标签
   ├─ 推送镜像仓库
   └─ 生成发行说明

5. 通知用户
   ├─ 邮件通知
   ├─ 文档更新
   └─ 升级指南发布
```

---

## 五、依赖版本管理策略

### 5.1 更新策略

```
框架级依赖 (React, Node, PostgreSQL):
├─ 仅更新主版本 LTS
├─ 充分测试后升级
├─ 更新间隔: 半年-一年
└─ 示例: React 18 → 19 (明年考虑)

工具库依赖 (axios, lodash 等):
├─ Minor + Patch 自动更新
├─ 月度依赖审查
├─ 使用 Dependabot (GitHub) 自动化
└─ 重大变更 (Major) 手动评估

安全更新:
├─ 漏洞扫描: npm audit / snyk
├─ 立即修复高危漏洞
├─ 计划修复中危漏洞
└─ 自动化 CI 检查
```

### 5.2 锁定版本

```
使用 pnpm-lock.yaml / package-lock.json 锁定精确版本

示例 package.json:
{
  "dependencies": {
    "react": "18.2.0",           // 锁定小版本
    "axios": "^1.5.0",           // 允许 patch 更新
    "@nestjs/core": "~10.2.0"    // 允许 minor 更新
  }
}

建议:
├─ 框架: 锁定小版本 (18.2.0)
├─ 工具: 允许 patch 更新 (^1.5.0)
├─ 大版本: 显式锁定
└─ 避免意外兼容性问题
```

---

## 六、性能基准目标

### 6.1 前端性能指标

```
Lighthouse 评分:
├─ Performance: >85
├─ Accessibility: >90
├─ Best Practices: >90
└─ SEO: >90

页面加载时间:
├─ First Contentful Paint (FCP): <1.5s
├─ Largest Contentful Paint (LCP): <2.5s
├─ Cumulative Layout Shift (CLS): <0.1
└─ Time to Interactive (TTI): <3s

包体积:
├─ JS Bundle: <500KB (gzip)
├─ CSS: <100KB (gzip)
└─ 分离 Vendor 包，支持代码分割
```

### 6.2 后端性能指标

```
API 响应时间:
├─ P50: <100ms
├─ P95: <300ms
├─ P99: <1s
└─ 错误率: <0.1%

数据库性能:
├─ 查询平均耗时: <50ms
├─ 慢查询记录 (>500ms)
└─ 连接池大小: 20-50

吞吐量:
├─ QPS (Queries Per Second): >1000
├─ 并发用户: >500
└─ 长连接支持

缓存命中率:
├─ Redis 缓存: >80%
├─ CDN 缓存: >90%
└─ 浏览器缓存: 合理配置
```

---

**文档完成日期：** 2026-11-28  
**下一步：** 用户场景与端到端流程文档

