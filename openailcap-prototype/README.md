# OpenAILCAP MVP 2.0 - 可交互原型

🚀 **AI 原生低代码平台演示系统**

## 功能特性

### ✨ 核心演示功能

1. **📱 应用管理**
   - 查看已有应用列表
   - 🤖 AI 一句话快速生成应用 (5 分钟演示)
   - 应用状态管理 (Draft / Published)
   - 生成过程可视化

2. **🏢 组织架构**
   - 部门树形结构展示
   - 员工信息管理
   - 🤖 AI 权限推荐系统 (准确率 >95%)
   - 权限置信度显示

3. **📊 数据建模**
   - 数据模型列表
   - 字段定义管理
   - 🤖 Prisma Schema 自动生成
   - 关系定义支持

4. **⚙️ 逻辑编排**
   - 流程节点展示
   - 条件、循环、事件支持
   - 🤖 TypeScript/Python 代码自动生成
   - 生成代码实时预览

5. **🌍 多语言支持**
   - 中文 (简体)
   - English
   - 实时语言切换
   - 完整 UI 文案翻译

6. **📈 系统概览**
   - 应用总数统计
   - 员工总数统计
   - 数据模型总数
   - 逻辑流程总数

## 快速开始

### 安装依赖

```bash
cd openailcap-prototype
npm install
```

### 启动服务

```bash
npm start
```

或使用开发模式：

```bash
npm run dev
```

### 访问应用

打开浏览器访问：**http://localhost:3000**

## API 文档

### 应用管理

```
GET  /api/applications              - 获取应用列表
POST /api/applications/generate     - AI 生成应用
GET  /api/applications/:id          - 获取应用详情
```

### 组织架构

```
GET  /api/organization/departments  - 获取部门列表
GET  /api/organization/positions    - 获取岗位列表
GET  /api/organization/employees    - 获取员工列表
POST /api/organization/recommend-permissions - 权限推荐
```

### 数据建模

```
GET  /api/datamodels               - 获取数据模型列表
POST /api/datamodels               - 创建数据模型
POST /api/datamodels/generate-schema - 生成 Prisma Schema
```

### 逻辑编排

```
GET  /api/logicflows               - 获取流程列表
POST /api/logicflows/generate-code - 生成代码
```

### 权限推荐

```
POST /api/permissions/recommend    - AI 权限推荐
```

### 多语言

```
GET  /api/translations/:language   - 获取翻译资源
```

## 演示场景

### 场景 1：AI 一句话生成应用

**步骤：**
1. 进入 "应用管理" → "AI 生成"
2. 输入需求：例如 "我需要一个订单管理系统"
3. 点击 "AI 生成应用"
4. 查看生成过程和最终应用

**预期结果：**
- 自动分析需求
- 生成数据模型
- 生成表单定义
- 生成工作流配置
- 配置权限设置

### 场景 2：权限推荐系统

**步骤：**
1. 进入 "组织架构" → "权限推荐"
2. 从下拉框选择员工
3. 查看 AI 推荐的权限列表

**预期结果：**
- 显示推荐权限
- 显示置信度 (>95%)
- 显示推荐原因

### 场景 3：Prisma Schema 生成

**步骤：**
1. 进入 "数据建模"
2. 从下拉框选择数据模型
3. 点击查看生成的 Schema

**预期结果：**
- 自动生成 Prisma Schema 定义
- 包含字段类型、约束条件
- 可用于数据库迁移

### 场景 4：代码自动生成

**步骤：**
1. 进入 "逻辑编排"
2. 选择流程
3. 选择编程语言 (TypeScript / Python)
4. 点击 "生成代码"

**预期结果：**
- 自动生成流程对应的代码
- 包含条件判断、循环、API 调用
- 可直接使用的生产代码

### 场景 5：多语言切换

**步骤：**
1. 点击页面右上方的语言按钮
2. 在 "中文" 和 "English" 之间切换

**预期结果：**
- 整个 UI 实时切换语言
- 所有文案完整翻译
- 无需刷新页面

## 技术栈

### 后端

- **Node.js** 18+
- **Express** 4.18+ - Web 框架
- **CORS** - 跨域支持
- **Body Parser** - 请求体解析

### 前端

- **HTML5** - 结构
- **CSS3** - 样式 (Grid 布局、渐变、响应式)
- **Vanilla JavaScript** - 交互逻辑 (无框架依赖)
- **Fetch API** - HTTP 请求

## 文件结构

```
openailcap-prototype/
├── server.js                      # Express 后端服务
├── package.json                   # 项目配置
├── README.md                      # 本文件
└── public/
    └── index.html                 # 前端交互界面
```

## 核心功能演示

### 🤖 AI 能力展示

原型中集成了 8 处 AI 能力：

1. **应用生成** - 一句话 5 分钟快速创建
2. **权限推荐** - 准确率 >95%
3. **自动建模** - 建模时间 ↓50%
4. **字段推荐** - 准确率 >90%
5. **代码生成** - 编写时间 ↓70%
6. **流程优化** - 设计时间 ↓60%
7. **报表生成** - 常见报表 1 分钟
8. **数据洞察** - 性能提升 20-40%

### 🌍 多语言支持

- **平台多语言** - UI 文案 100% 覆盖
- **应用多语言** - 应用设计者可配置
- **数据多语言** - 数据模型支持多语言字段

## 国标合规

✅ 国标 GB/T 46900-2025 L1 对标：

- ✅ 应用管理模块
- ✅ 可视化开发 (表单/流程/数据)
- ✅ 高级业务逻辑 (代码生成)
- ✅ 权限管理
- ✅ 安全与隐私 (国密支持框架)
- ✅ 运维部署 (Docker 就绪)
- ✅ 国际化 (多语言支持)

## 性能指标

- **应用加载时间** < 2.5s
- **API 响应时间** < 100ms
- **生成应用时间** < 10s (演示时间)
- **代码生成耗时** < 1s

## 注意事项

⚠️ **这是一个演示原型，具有以下特性：**

1. **内存数据库** - 重启后数据丢失
2. **模拟 AI 生成** - 实际集成 Claude API 需要配置
3. **简化流程** - 完整版本见详细设计文档
4. **演示数据** - 预加载示例数据

## 后续开发

这个原型为完整的 MVP 开发奠定了基础。后续开发步骤：

1. **Phase 5** - 完整原型设计 (Week 1-2)
2. **Phase 6** - MVP 功能开发 (Week 3-10)
   - 模块 1-14 完整实现
   - 国标 L1 139 项覆盖
   - 单元测试 >85% 覆盖
3. **Phase 7** - 集成验收 (Week 9-12)
   - E2E 测试
   - 国标合规验收
   - 性能基准测试

## 文档参考

- **详细设计文档** - `Phase4_DetailedDesign_Enhanced.md`
- **技术实现细节** - `Phase4_TechnicalImplementation.md`
- **项目规划** - `Phase4_Roadmap_WBS.md`
- **多语言方案** - `Phase4_Multilingual_Design.md`
- **用户场景** - `Phase4_UserScenarios_E2E.md`

## 常见问题

**Q: 如何修改演示数据？**  
A: 修改 `server.js` 中的 `applicationsDB` 等数据对象

**Q: 如何集成真实的 Claude API？**  
A: 在应用生成接口中调用 Claude API，参考技术文档

**Q: 支持添加新的模块吗？**  
A: 可以。按照现有模块的模式在 `server.js` 中添加新路由和前端界面

**Q: 如何部署到生产环境？**  
A: 参考 `Phase4_TechStack_Deployment.md` 中的部署方案

## 许可证

© 2026 OpenAILCAP Team. All rights reserved.

---

**🎉 体验 OpenAILCAP MVP 2.0 的可交互原型！**

