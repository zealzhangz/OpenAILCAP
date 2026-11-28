> **2026-11-28 原型重设计与功能完整性补充**
>
> 本原型进入全量视觉和交互重设计。统一视觉规范见 `doc/整改/2026-11-28_UIUX设计系统与原型重设计规范.md`；必须保留 14 个模块、18 个页面和全部 AI 入口，重构后以功能差异为零为门槛。
>
> 原型必须清楚区分真实实现、可交互模拟、静态展示和规划能力。核心操作不得以 Toast/固定结果冒充实现；所有状态更新必须进入统一 AppSpec/状态仓库，刷新后恢复并可跨模块追踪。原型 UI 的演示状态不等于后端技术 POC 或国标符合性证据。
>
> 视觉方向为工业级工程工作台：导航、顶栏、任务区、设计器画布、属性面板、AI 协作侧栏形成一致层级；逐页完成桌面/窄屏截图、键盘操作、对比度和功能回归。不得只重做首页。
>
># OpenAILCAP Phase 5：原型设计方案
# 从设计到代码的桥梁

**版本：** v1.0  
**日期：** 2026-11-28  
**目标：** 为 MVP 开发准备可工作的原型系统  
**交付周期：** Week 1-2 (12.1-12.14)

---

## 一、原型设计目标

### 1.1 核心目标

```
✅ 技术方案可行性验证
   ├─ 国密库集成 POC
   ├─ 组织架构模型实现
   ├─ 数据建模 Schema 生成
   ├─ 逻辑编排代码生成
   └─ 权限推荐算法

✅ 架构模式确认
   ├─ 前后端交互模式
   ├─ 编辑器集成方案
   ├─ 数据流向设计
   └─ 状态管理策略

✅ 团队能力验证
   ├─ 技术栈熟悉度
   ├─ 开发流程验证
   ├─ 团队协作模式
   └─ 工具链准备就绪

✅ 风险早期识别
   ├─ 技术风险缓解
   ├─ 性能基准确立
   ├─ 安全机制验证
   └─ 国标合规初步验证
```

### 1.2 成功标准

```
功能层:
└─ 1 个完整的订单管理应用 MVP (5 分钟内快速生成 + 30 分钟编辑完善)

代码质量:
└─ 单元测试覆盖率 >70%，无 P0 缺陷

性能:
└─ 响应时间 <500ms，页面加载 <3s

技术验证:
└─ 国密、权限推荐、Schema 生成、代码生成均可工作

文档:
└─ 原型代码注释完善，可用于后续团队开发参考
```

---

## 二、原型设计架构

### 2.1 前端原型 (React SPA)

#### 目录结构

```
frontend/
├─ public/
│  ├─ index.html
│  └─ favicon.ico
│
├─ src/
│  ├─ main.tsx               # 入口
│  ├─ App.tsx                # 主应用
│  │
│  ├─ config/
│  │  ├─ i18n.config.ts      # 多语言配置
│  │  ├─ api.config.ts       # API 基础配置
│  │  └─ routes.ts           # 路由定义
│  │
│  ├─ store/                 # Redux 状态管理
│  │  ├─ index.ts            # Store 配置
│  │  ├─ auth.slice.ts       # 认证
│  │  ├─ app.slice.ts        # 应用管理
│  │  └─ org.slice.ts        # 组织架构
│  │
│  ├─ services/              # API 调用
│  │  ├─ api.ts              # HTTP 客户端
│  │  ├─ auth.service.ts
│  │  ├─ app.service.ts
│  │  ├─ org.service.ts
│  │  └─ datamodel.service.ts
│  │
│  ├─ components/            # React 组件
│  │  ├─ Layout/
│  │  │  ├─ Header.tsx
│  │  │  ├─ Sidebar.tsx
│  │  │  └─ Footer.tsx
│  │  │
│  │  ├─ AppManagement/
│  │  │  ├─ AppList.tsx
│  │  │  ├─ AppCreate.tsx
│  │  │  ├─ AppDetail.tsx
│  │  │  └─ AIGenerationDialog.tsx  # AI 一句话生成
│  │  │
│  │  ├─ OrgStructure/
│  │  │  ├─ OrgTree.tsx
│  │  │  ├─ DepartmentForm.tsx
│  │  │  ├─ EmployeeList.tsx
│  │  │  └─ PermissionRecommend.tsx  # AI 权限推荐
│  │  │
│  │  ├─ DataModeling/
│  │  │  ├─ ERDiagram.tsx       # ER 图编辑器
│  │  │  ├─ FieldDefinition.tsx
│  │  │  ├─ SchemaPreview.tsx
│  │  │  └─ AIModelGeneration.tsx # AI 自动建模
│  │  │
│  │  ├─ FormDesigner/
│  │  │  ├─ FormBuilder.tsx
│  │  │  ├─ FieldPalette.tsx
│  │  │  └─ FormPreview.tsx
│  │  │
│  │  └─ Common/
│  │     ├─ LanguageSwitcher.tsx
│  │     ├─ PermissionGuard.tsx
│  │     └─ ErrorBoundary.tsx
│  │
│  ├─ hooks/                 # 自定义 Hook
│  │  ├─ useAuth.ts
│  │  ├─ useAppManagement.ts
│  │  ├─ useOrgStructure.ts
│  │  └─ useFormBuilder.ts
│  │
│  ├─ types/                 # TypeScript 类型定义
│  │  ├─ index.ts
│  │  ├─ auth.ts
│  │  ├─ app.ts
│  │  ├─ org.ts
│  │  └─ datamodel.ts
│  │
│  ├─ locales/              # 多语言文件
│  │  ├─ zh-CN/
│  │  │  ├─ common.json
│  │  │  ├─ app.json
│  │  │  └─ org.json
│  │  └─ en-US/
│  │     ├─ common.json
│  │     ├─ app.json
│  │     └─ org.json
│  │
│  └─ utils/
│     ├─ http.ts            # HTTP 工具
│     ├─ validator.ts       # 验证工具
│     └─ transformer.ts     # 数据转换
│
├─ package.json
├─ vite.config.ts
└─ tsconfig.json
```

#### 关键组件示例代码

**AppCreate.tsx (AI 一句话生成)**

```typescript
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button, Input, Modal, Spin, Steps } from 'antd';
import { generateApp } from '@/services/app.service';

export const AppCreate: React.FC = () => {
  const { t } = useTranslation('app');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [steps, setSteps] = useState<string[]>([]);
  const [currentStep, setCurrentStep] = useState(0);

  const handleGenerate = async () => {
    if (!description.trim()) return;

    setLoading(true);
    try {
      // 1. 调用后端 AI 生成 API
      const response = await generateApp({
        description,
        targetLanguages: ['zh-CN', 'en-US']
      });

      // 2. 显示生成步骤
      setSteps([
        t('app.create.step1'), // 分析需求
        t('app.create.step2'), // 生成数据模型
        t('app.create.step3'), // 生成表单定义
        t('app.create.step4'), // 生成工作流
        t('app.create.step5'), // 生成权限配置
      ]);

      // 3. 模拟步骤进度
      for (let i = 0; i < steps.length; i++) {
        setCurrentStep(i);
        await new Promise(resolve => setTimeout(resolve, 1000));
      }

      // 4. 应用生成成功
      Modal.success({
        title: t('app.create.success'),
        content: `${response.appName} ${t('app.create.created')}`
      });

    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal title={t('app.create.title')} open onCancel={() => {}}>
      <div style={{ padding: '20px' }}>
        <Input.TextArea
          placeholder={t('app.create.placeholder')}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={3}
        />

        {loading && (
          <Steps
            current={currentStep}
            items={steps.map(s => ({ title: s }))}
            style={{ marginTop: '20px' }}
          />
        )}

        <Button
          type="primary"
          onClick={handleGenerate}
          loading={loading}
          disabled={!description.trim() || loading}
          style={{ marginTop: '20px' }}
        >
          {t('app.create.generate')}
        </Button>
      </div>
    </Modal>
  );
};
```

**OrgTree.tsx (组织架构树形展示)**

```typescript
import React, { useEffect, useState } from 'react';
import { Tree, Spin, message } from 'antd';
import { getOrgStructure } from '@/services/org.service';

export const OrgTree: React.FC = () => {
  const [treeData, setTreeData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchOrgStructure = async () => {
      try {
        const response = await getOrgStructure();
        // 转换为树形结构
        const transformed = transformToTreeData(response);
        setTreeData(transformed);
      } catch (error) {
        message.error('Failed to load organization structure');
      } finally {
        setLoading(false);
      }
    };

    fetchOrgStructure();
  }, []);

  const transformToTreeData = (data: any) => {
    // 实现从平层数据转换为树形结构的逻辑
    return data.map((dept: any) => ({
      title: dept.name,
      key: dept.id,
      children: dept.children?.map(transformToTreeData) || []
    }));
  };

  return (
    <Spin spinning={loading}>
      <Tree
        treeData={treeData}
        defaultExpandAll
        showIcon
      />
    </Spin>
  );
};
```

---

### 2.2 后端原型 (NestJS)

#### 目录结构

```
backend/
├─ src/
│  ├─ main.ts                # 应用入口
│  │
│  ├─ config/
│  │  ├─ database.config.ts
│  │  ├─ auth.config.ts
│  │  └─ ai.config.ts
│  │
│  ├─ prisma/
│  │  ├─ schema.prisma       # 数据库 Schema
│  │  └─ migrations/         # 迁移文件
│  │
│  ├─ modules/
│  │  │
│  │  ├─ auth/
│  │  │  ├─ auth.controller.ts
│  │  │  ├─ auth.service.ts
│  │  │  ├─ auth.module.ts
│  │  │  └─ jwt.strategy.ts
│  │  │
│  │  ├─ app/
│  │  │  ├─ app.controller.ts         # 应用 API
│  │  │  ├─ app.service.ts
│  │  │  ├─ ai-generation.service.ts  # AI 生成服务
│  │  │  └─ app.module.ts
│  │  │
│  │  ├─ organization/
│  │  │  ├─ org.controller.ts         # 组织架构 API
│  │  │  ├─ org.service.ts
│  │  │  ├─ permission-recommend.service.ts  # AI 权限推荐
│  │  │  └─ org.module.ts
│  │  │
│  │  ├─ datamodel/
│  │  │  ├─ datamodel.controller.ts
│  │  │  ├─ datamodel.service.ts
│  │  │  ├─ schema-generator.service.ts  # Schema 生成
│  │  │  ├─ ai-model-gen.service.ts    # AI 建模
│  │  │  └─ datamodel.module.ts
│  │  │
│  │  ├─ logicflow/
│  │  │  ├─ logicflow.controller.ts
│  │  │  ├─ logicflow.service.ts
│  │  │  ├─ code-generator.service.ts  # 代码生成
│  │  │  └─ logicflow.module.ts
│  │  │
│  │  └─ security/
│  │     ├─ crypto.service.ts         # 国密算法
│  │     ├─ audit.service.ts          # 审计日志
│  │     └─ security.module.ts
│  │
│  ├─ common/
│  │  ├─ decorators/
│  │  │  ├─ user.decorator.ts
│  │  │  └─ permission.decorator.ts
│  │  │
│  │  ├─ guards/
│  │  │  ├─ auth.guard.ts
│  │  │  └─ permission.guard.ts
│  │  │
│  │  ├─ interceptors/
│  │  │  ├─ logging.interceptor.ts
│  │  │  ├─ transform.interceptor.ts
│  │  │  └─ error.interceptor.ts
│  │  │
│  │  ├─ dto/
│  │  │  ├─ app.dto.ts
│  │  │  ├─ org.dto.ts
│  │  │  └─ datamodel.dto.ts
│  │  │
│  │  └─ entities/
│  │     ├─ app.entity.ts
│  │     ├─ org.entity.ts
│  │     └─ datamodel.entity.ts
│  │
│  ├─ ai/
│  │  ├─ claude.service.ts           # Claude API 集成
│  │  ├─ prompts/
│  │  │  ├─ app-generation.prompt.ts
│  │  │  ├─ datamodel.prompt.ts
│  │  │  ├─ permission-recommend.prompt.ts
│  │  │  └─ code-generation.prompt.ts
│  │  └─ ai.module.ts
│  │
│  └─ app.module.ts                  # 主模块
│
├─ test/
│  ├─ app.e2e-spec.ts
│  └─ org.e2e-spec.ts
│
├─ Dockerfile
├─ docker-compose.yml
├─ package.json
└─ tsconfig.json
```

#### 关键服务示例代码

**AIGenerationService (AI 应用生成)**

```typescript
import { Injectable } from '@nestjs/common';
import { ClaudeService } from '@/ai/claude.service';
import { PrismaService } from '@/prisma/prisma.service';

@Injectable()
export class AIGenerationService {
  constructor(
    private claude: ClaudeService,
    private prisma: PrismaService
  ) {}

  async generateApplication(description: string, userId: string) {
    // 1. 调用 Claude 分析需求
    const analysis = await this.claude.analyzeRequirement(description);

    // 2. 生成应用骨架
    const appSkeleton = this.generateAppSkeleton(analysis);

    // 3. 保存到数据库
    const app = await this.prisma.application.create({
      data: {
        name: appSkeleton.name,
        description: appSkeleton.description,
        createdBy: userId,
        schema: appSkeleton.schema,
      }
    });

    // 4. 生成数据模型
    for (const model of appSkeleton.models) {
      await this.prisma.dataModel.create({
        data: {
          appId: app.id,
          ...model
        }
      });
    }

    // 5. 生成表单定义
    for (const form of appSkeleton.forms) {
      await this.prisma.formDefinition.create({
        data: {
          appId: app.id,
          ...form
        }
      });
    }

    return app;
  }

  private generateAppSkeleton(analysis: any) {
    // 根据分析结果生成应用骨架
    return {
      name: analysis.appName,
      description: analysis.description,
      schema: analysis.schema,
      models: analysis.dataModels,
      forms: analysis.forms
    };
  }
}
```

**SchemaGeneratorService (Prisma Schema 生成)**

```typescript
@Injectable()
export class SchemaGeneratorService {
  
  generatePrismaSchema(dataModels: DataModel[]): string {
    let schema = `
datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

generator client {
  provider = "prisma-client-js"
}

`;

    for (const model of dataModels) {
      schema += this.generateModelDefinition(model);
    }

    return schema;
  }

  private generateModelDefinition(model: DataModel): string {
    let def = `model ${model.name} {\n`;

    for (const field of model.fields) {
      def += `  ${field.name} ${this.mapFieldType(field.type)}`;
      
      if (field.constraints?.primaryKey) def += ` @id`;
      if (field.constraints?.unique) def += ` @unique`;
      if (!field.constraints?.notNull) def += `?`;
      if (field.config?.defaultValue) def += ` @default(${field.config.defaultValue})`;
      
      def += `\n`;
    }

    def += `}\n\n`;
    return def;
  }

  private mapFieldType(type: string): string {
    const mapping: Record<string, string> = {
      'string': 'String',
      'integer': 'Int',
      'boolean': 'Boolean',
      'date': 'DateTime',
      'json': 'Json'
    };
    return mapping[type] || 'String';
  }
}
```

**CryptoService (国密算法)**

```typescript
@Injectable()
export class CryptoService {
  private sm4Key: Buffer;

  constructor() {
    this.initializeKeys();
  }

  // SM4 加密
  sm4Encrypt(plaintext: string): string {
    const TongSuo = require('tongsuo');
    const cipher = TongSuo.createCipheriv(
      'SM4-128-CBC',
      this.sm4Key,
      Buffer.alloc(16, 0)
    );
    
    let ciphertext = cipher.update(plaintext, 'utf-8', 'base64');
    ciphertext += cipher.final('base64');
    
    return ciphertext;
  }

  // SM3 哈希
  sm3Hash(data: string): string {
    const TongSuo = require('tongsuo');
    const hash = TongSuo.createHash('SM3');
    hash.update(data);
    return hash.digest('hex');
  }

  private initializeKeys() {
    const TongSuo = require('tongsuo');
    this.sm4Key = TongSuo.randomBytes(16);
  }
}
```

---

## 三、关键集成点

### 3.1 前后端交互流程

```
用户操作 (React)
  ↓
Redux 状态更新
  ↓
API 调用 (Axios)
  ↓
后端 NestJS 路由
  ↓
业务服务处理
  ├─ 数据库操作 (Prisma)
  ├─ 国密加密 (TongSuo)
  ├─ AI 处理 (Claude API)
  └─ 权限验证 (Guard)
  ↓
返回结果
  ↓
Redux 更新
  ↓
React 组件重新渲染
```

### 3.2 编辑器集成

```
React Flow (逻辑编排可视化)
  ├─ 节点定义
  ├─ 拖拽操作
  └─ 保存为 JSON
     ↓
  后端代码生成服务
     ↓
  生成 TypeScript 代码

Monaco Editor (代码编辑)
  ├─ 语法高亮
  ├─ 自动补全
  └─ 实时验证
```

---

## 四、开发步骤 (Week 1-2)

### 4.1 准备阶段 (Day 1-2)

```
Day 1:
☐ 项目初始化
  ├─ 创建 Git 仓库
  ├─ 初始化前后端项目
  ├─ 配置开发环境
  └─ Docker Compose 启动

Day 2:
☐ 基础架构搭建
  ├─ 认证系统 (JWT)
  ├─ 数据库迁移
  ├─ API 中间件
  ├─ 国密库集成测试
  └─ React 项目配置
```

### 4.2 核心功能实现 (Day 3-7)

```
Day 3-4: 组织架构模块
├─ 后端
│  ├─ 部门、岗位、员工 CRUD API
│  ├─ 权限推荐算法实现
│  └─ 单元测试
└─ 前端
   ├─ 组织树形展示
   ├─ CRUD 表单
   └─ 权限推荐 UI

Day 5-6: 数据建模模块
├─ 后端
│  ├─ Prisma Schema 生成器
│  ├─ ER 图 JSON 存储
│  └─ 单元测试
└─ 前端
   ├─ React Flow ER 编辑器
   ├─ Schema 预览
   └─ 导出功能

Day 7: 应用管理 AI 生成
├─ 后端
│  ├─ Claude API 集成
│  ├─ Prompt 工程
│  └─ 应用骨架生成
└─ 前端
   ├─ AI 对话界面
   └─ 生成进度显示
```

### 4.3 验证阶段 (Day 8-10)

```
Day 8:
☐ 集成测试
  ├─ 端到端流程测试
  ├─ 权限验证
  └─ 国密集成验证

Day 9:
☐ 性能测试
  ├─ 响应时间基准
  ├─ 大数据集测试
  └─ 内存泄漏检查

Day 10:
☐ 文档完善
  ├─ 代码注释
  ├─ API 文档
  ├─ 架构说明
  └─ 部署指南
```

---

## 五、关键检查点

### 5.1 技术验证清单

```
☐ 国密库 (TongSuo)
  ├─ SM2/SM3/SM4 功能验证
  ├─ 性能基准确立
  └─ 安全强度确认

☐ 组织架构
  ├─ 权限推荐准确率 >80%
  ├─ 大数据集性能 (<500ms)
  └─ 权限继承正确性

☐ 数据建模
  ├─ Schema 生成正确性
  ├─ 关系定义完整性
  └─ 迁移脚本可执行性

☐ AI 能力
  ├─ 应用生成可用性
  ├─ 生成内容质量 >80%
  └─ 多轮对话流畅性

☐ 前端
  ├─ 编辑器易用性
  ├─ 多语言切换正常
  └─ 性能指标 <3s
```

### 5.2 质量标准

```
代码覆盖率:
├─ 后端单元测试: >70%
├─ 前端组件测试: >60%
└─ E2E 场景覆盖: 100%

性能:
├─ API P95: <500ms
├─ 页面加载: <3s
└─ 国密操作: <100ms

功能:
├─ 订单应用完整生成: ✅
├─ 所有 CRUD 操作: ✅
├─ 权限验证: ✅
└─ 国标基础功能: ✅
```

---

## 六、部署与测试

### 6.1 本地开发环境

```bash
# 一键启动
docker-compose up

# 访问应用
http://localhost:3000       # 前端
http://localhost:8000/api   # 后端 API
http://localhost:5432       # PostgreSQL
http://localhost:6379       # Redis
```

### 6.2 自动化测试

```bash
# 后端单元测试
cd backend
npm run test

# 前端组件测试
cd frontend
npm run test

# E2E 测试
npm run test:e2e

# 覆盖率报告
npm run test:coverage
```

---

## 七、原型交付物

### 7.1 代码仓库

```
openailcap-prototype/
├─ frontend/              # React 应用
├─ backend/              # NestJS 应用
├─ docker-compose.yml    # 本地开发环境
├─ .github/workflows/    # CI/CD 流程
├─ docs/
│  ├─ SETUP.md          # 环境搭建指南
│  ├─ API.md            # API 文档
│  ├─ ARCHITECTURE.md   # 架构说明
│  └─ DEVELOPMENT.md    # 开发指南
└─ README.md
```

### 7.2 文档交付物

```
✅ 环境搭建指南
✅ API 文档 (OpenAPI 3.0)
✅ 架构说明文档
✅ 代码注释 (所有关键函数)
✅ 性能基准报告
✅ 国密集成验证报告
✅ 单元测试覆盖率报告
✅ 后续开发指南
```

---

## 八、成功指标

### 原型完成标准

```
✅ 功能完整性
   └─ 1 个订单管理应用从创建到发布的完整流程

✅ 技术可行性
   ├─ 国密集成 POC 成功
   ├─ 权限推荐算法可用
   ├─ Schema 生成正确
   └─ 代码生成质量 >80%

✅ 性能达标
   ├─ API P95 <500ms
   ├─ 页面加载 <3s
   └─ 国密操作 <100ms

✅ 质量保证
   ├─ 单元测试 >70%
   ├─ 无 P0 缺陷
   └─ 代码规范通过

✅ 团队准备
   ├─ 技术栈熟悉
   ├─ 开发流程就绪
   ├─ 文档完善
   └─ 新人可快速上手
```

---

## 下一步行动

### Week 1 Kickoff (2026-12-03)

```
☐ 技术选型最终确认 (国密库、编辑器等)
☐ 代码仓库初始化
☐ 本地开发环境配置
☐ 团队分工确认
☐ 第一个 Sprint 规划
```

### 预期交付 (2026-12-14)

```
✅ 可工作的原型系统
✅ 完整的技术文档
✅ 团队培训完成
✅ 进入 MVP 开发阶段就绪

由此进入 Phase 6：MVP 功能开发
```

---

**原型设计方案完成日期：** 2026-11-28  
**原型实施周期：** Week 1-2  
**预期交付日期：** 2026-12-14



---

## 2026-11-28 原型真实交付边界与设计映射（覆盖历史目标描述）

本节是对本文历史“React SPA / 技术 POC 成功标准”的纠偏补充。当前仓库交付物是**交互式 UI 演示原型**，不是本文原先规划的后端技术 POC。历史章节中 React/NestJS/PostgreSQL、真实国密、真实 LLM、性能数字和订单 MVP 目标属于目标设计，不得视为当前已实现。

### 当前原型运行基线

- 入口：`openailcap-prototype/public/index.html`。
- 页面路由与导航：`public/js/app.js` 中 `App.NAV`、`App.go()`。
- 演示状态：`public/js/store.js`，通过浏览器 `localStorage` 保存；只代表单浏览器演示数据。
- AppSpec：`public/js/app-spec.js` 提供轻量结构/引用校验；完整 JSON Schema 2020-12 服务端校验、持久化和迁移器尚未交付。
- 视觉系统：`public/css/workbench-redesign.css` 覆盖基础样式；原有模块脚本负责页面结构和交互。
- 启动：`cd openailcap-prototype && node server.js`；无业务 API，不需要 npm install。
- AI 标识：全局助手必须显示 `LOCAL DEMO`；规则模板输出不得标注真实模型生成。
- BPM/Logic：当前只进行编辑、结构校验和仿真，不声称已连接真实执行引擎。
- 数据建模：DDL/Prisma 内容仅为预览，不得执行生产迁移。

### 18 个工作区与代码路由

工作区清单、路由 ID、模块脚本、AppSpec 写入范围和验收状态统一维护在 `doc/整改/2026-11-28_设计-原型一致性契约.md`。新增/重命名页面时，必须同步更新该契约、导航路由、模块脚本和回归测试；禁止仅更新文档或仅更新界面。

### 本阶段验收口径

1. 设计中的每个页面/操作必须能定位到原型路由、模块脚本和状态字段；没有代码实现的标记为“设计完成/原型未实现”。
2. 原型新增/修改的每个业务操作必须反向定位到详细设计中的业务规则、AppSpec 路径、API 契约（若属生产能力）、权限和审计要求。
3. 不允许把 localStorage 写入、Toast、固定样例或图仿真计为生产能力完成。
4. 18 个工作区与 10 项 AI 能力保持全量功能基线；功能状态分别记录“设计”“原型交互”“生产实现”“自动化验证”“独立复核”。
5. 页面级验收必须执行浏览器 E2E；静态 JS 检查只证明语法/静态基线，不证明交互闭环。
