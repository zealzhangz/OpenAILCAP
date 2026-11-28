> **2026-11-28 技术实现补充：生产级正确性门槛**
>
> 数据模型生成器以 AppSpec 为输入，生成 Prisma Schema 和 SQL DDL 时必须保证类型、主键、外键、唯一约束、普通索引、复合索引、枚举、默认值、精度、可空性、删除/更新策略完全一致。先生成全部基础表，再建立跨表外键，或按拓扑顺序生成；循环依赖必须采用后置约束策略。单字段主键不得重复输出复合主键；多个独立 unique 不得错误合并成复合 unique；索引必须引用字段名而非内部 ID。
>
> 每次生成后强制执行：格式化、Schema 校验、临时 PostgreSQL 迁移、迁移回滚、迁移后结构 diff、关系完整性测试。未通过时不得生成可发布 Artifact。
>
> 安全实现不得使用固定 IV、固定 nonce、明文硬编码密钥、进程内随机临时密钥或普通哈希替代认证完整性保护。加密材料必须携带算法版本/keyId/IV/认证标签等元数据，支持密钥轮换、旧密钥解密、备份恢复和篡改检测，方案经密码评审后方可实现。
>
> 自定义代码、Agent 工具和第三方插件必须通过工具权限声明、沙箱执行、资源配额、网络策略、审计和可撤销变更；禁止对用户代码或策略表达式使用任意 eval。
>
># OpenAILCAP 技术细节补充文档
# 模块 2/3/5/13 核心实现方案

**版本：** v1.0  
**日期：** 2026-11-28  
**目标受众：** 架构师 + 资深工程师

---

## 一、模块 2：组织架构管理 - 实现细节

### 1.1 数据库 Schema 设计

```sql
-- 部门表
CREATE TABLE departments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code VARCHAR(50) UNIQUE NOT NULL,           -- 部门代码，如 DEPT001
  name VARCHAR(100) NOT NULL,
  parent_id UUID REFERENCES departments(id),  -- 自引用，支持树形结构
  level INT DEFAULT 0,                        -- 层级深度（0=顶级）
  manager_id UUID REFERENCES employees(id),   -- 部门负责人
  cost_center VARCHAR(50),                    -- 成本中心代码
  active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  
  CONSTRAINT dept_hierarchy CHECK (level >= 0)
);

CREATE INDEX idx_dept_parent ON departments(parent_id);
CREATE INDEX idx_dept_code ON departments(code);

-- 岗位表
CREATE TABLE positions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code VARCHAR(50) UNIQUE NOT NULL,
  name VARCHAR(100) NOT NULL,                 -- "销售主管"
  level VARCHAR(20),                          -- 职级: M1/M2/M3...
  permission_template_id UUID REFERENCES permission_templates(id),
  
  -- 工作流权限模板
  workflow_permissions JSONB,                 -- 存储工作流权限配置
  
  active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- 员工表
CREATE TABLE employees (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code VARCHAR(50) UNIQUE NOT NULL,           -- 工号
  name VARCHAR(100) NOT NULL,
  email VARCHAR(100) UNIQUE,
  phone VARCHAR(20),
  
  -- 组织关系
  department_id UUID NOT NULL REFERENCES departments(id),
  position_id UUID NOT NULL REFERENCES positions(id),
  manager_id UUID REFERENCES employees(id),   -- 直接主管
  
  -- 权限配置
  inherited_permissions JSONB,                -- 继承的权限
  extra_permissions JSONB,                    -- 额外权限
  
  active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_emp_dept ON employees(department_id);
CREATE INDEX idx_emp_position ON employees(position_id);
CREATE INDEX idx_emp_manager ON employees(manager_id);

-- 组织变更历史
CREATE TABLE org_change_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  employee_id UUID NOT NULL REFERENCES employees(id),
  change_type VARCHAR(50),                    -- 'transfer', 'promotion', 'demotion'
  from_department_id UUID,
  to_department_id UUID,
  from_position_id UUID,
  to_position_id UUID,
  change_date TIMESTAMP DEFAULT NOW(),
  reason TEXT,
  approved_by UUID REFERENCES employees(id),
  created_at TIMESTAMP DEFAULT NOW()
);

-- 权限模板表（岗位级权限预设）
CREATE TABLE permission_templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(100),                          -- "销售主管权限模板"
  permissions JSONB,                          -- 权限数组
  description TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

### 1.2 Prisma Schema 定义

```prisma
// prisma/schema.prisma

model Department {
  id              String       @id @default(cuid())
  code            String       @unique
  name            String
  
  // 层级关系
  parentId        String?      @map("parent_id")
  parent          Department?  @relation("DepartmentHierarchy", fields: [parentId], references: [id])
  children        Department[] @relation("DepartmentHierarchy")
  
  level           Int          @default(0)
  
  // 负责人
  managerId       String?      @map("manager_id")
  manager         Employee?    @relation("DepartmentManager", fields: [managerId], references: [id])
  
  costCenter      String?
  employees       Employee[]   @relation("EmployeeDepartment")
  
  active          Boolean      @default(true)
  createdAt       DateTime     @default(now())
  updatedAt       DateTime     @updatedAt
  
  @@index([parentId])
  @@index([code])
}

model Position {
  id                    String     @id @default(cuid())
  code                  String     @unique
  name                  String
  level                 String?    // M1, M2, M3...
  
  permissionTemplateId  String?    @map("permission_template_id")
  permissionTemplate    PermissionTemplate? @relation(fields: [permissionTemplateId], references: [id])
  
  // 工作流权限配置
  workflowPermissions   Json?      @db.Json
  
  employees             Employee[]
  
  active                Boolean    @default(true)
  createdAt             DateTime   @default(now())
  updatedAt             DateTime   @updatedAt
}

model Employee {
  id                   String     @id @default(cuid())
  code                 String     @unique
  name                 String
  email                String     @unique
  phone                String?
  
  // 组织关系
  departmentId         String     @map("department_id")
  department           Department @relation("EmployeeDepartment", fields: [departmentId], references: [id])
  
  positionId           String     @map("position_id")
  position             Position   @relation(fields: [positionId], references: [id])
  
  managerId            String?    @map("manager_id")
  manager              Employee?  @relation("EmployeeManager", fields: [managerId], references: [id])
  subordinates         Employee[] @relation("EmployeeManager")
  
  // 权限
  inheritedPermissions Json?      @db.Json
  extraPermissions     Json?      @db.Json
  
  // 关系
  managedDepartments   Department[] @relation("DepartmentManager")
  changeLogs           OrgChangeLog[]
  
  active               Boolean    @default(true)
  createdAt            DateTime   @default(now())
  updatedAt            DateTime   @updatedAt
  
  @@index([departmentId])
  @@index([positionId])
  @@index([managerId])
}

model OrgChangeLog {
  id                 String     @id @default(cuid())
  
  employeeId         String
  employee           Employee   @relation(fields: [employeeId], references: [id])
  
  changeType         String     // transfer, promotion, demotion
  
  fromDepartmentId   String?
  toDepartmentId     String?
  
  fromPositionId     String?
  toPositionId       String?
  
  changeDate         DateTime   @default(now())
  reason             String?
  
  approvedBy         String?
  createdAt          DateTime   @default(now())
  
  @@index([employeeId])
}

model PermissionTemplate {
  id          String     @id @default(cuid())
  name        String
  permissions Json       @db.Json  // 权限数组
  description String?
  
  positions   Position[]
  createdAt   DateTime   @default(now())
  updatedAt   DateTime   @updatedAt
}
```

### 1.3 API 端点设计

```typescript
// API 端点列表

// ===== 部门管理 =====
GET    /api/departments                      // 获取部门树形结构
GET    /api/departments/:id                  // 获取部门详情
POST   /api/departments                      // 创建部门
PUT    /api/departments/:id                  // 更新部门
DELETE /api/departments/:id                  // 删除部门
GET    /api/departments/:id/employees        // 获取部门下的员工

// ===== 岗位管理 =====
GET    /api/positions                        // 获取所有岗位
GET    /api/positions/:id                    // 获取岗位详情
POST   /api/positions                        // 创建岗位
PUT    /api/positions/:id                    // 更新岗位
DELETE /api/positions/:id                    // 删除岗位

// ===== 员工管理 =====
GET    /api/employees                        // 获取员工列表（支持筛选、分页）
GET    /api/employees/:id                    // 获取员工详情
POST   /api/employees                        // 创建员工
PUT    /api/employees/:id                    // 更新员工信息
DELETE /api/employees/:id                    // 删除员工

// 组织关系查询
GET    /api/employees/:id/subordinates       // 获取员工的直属下属
GET    /api/employees/:id/hierarchy          // 获取员工的汇报线（上级链）
GET    /api/employees/:id/peers              // 获取同级员工

// ===== 权限操作 =====
GET    /api/employees/:id/permissions        // 获取员工权限（继承 + 额外）
POST   /api/employees/:id/permissions        // 分配额外权限
DELETE /api/employees/:id/permissions/:perm  // 移除额外权限

// AI 权限推荐
POST   /api/employees/:id/recommend-permissions   // AI 推荐该员工应有的权限

// ===== 变更管理 =====
POST   /api/employees/:id/transfer           // 员工转部门
POST   /api/employees/:id/promote            // 员工晋升
GET    /api/change-logs                      // 获取变更历史
GET    /api/change-logs/analytics            // 获取组织变更分析（趋势）

// ===== 批量操作 =====
POST   /api/employees/bulk-import            // 批量导入员工（CSV/Excel）
POST   /api/employees/bulk-export            // 批量导出员工
POST   /api/org/sync-external                // 从 AD/LDAP 同步组织结构

// ===== 权限模板 =====
GET    /api/permission-templates             // 获取权限模板列表
POST   /api/permission-templates             // 创建权限模板
PUT    /api/permission-templates/:id         // 更新权限模板
```

### 1.4 权限推荐算法（伪代码）

```typescript
// AI 权限推荐引擎
class PermissionRecommendationEngine {
  
  async recommendPermissions(employeeId: string): Promise<Permission[]> {
    const employee = await db.employee.findUnique({
      where: { id: employeeId },
      include: { position: true, department: true, manager: true }
    });
    
    const recommendations: Array<{ permission: string; confidence: number; reason: string }> = [];
    
    // 1. 岗位模板权限（基础）
    const positionPerms = employee.position.permissionTemplate?.permissions || [];
    recommendations.push(...positionPerms.map(p => ({
      permission: p,
      confidence: 0.95,
      reason: `岗位 ${employee.position.name} 的标准权限`
    })));
    
    // 2. 分析同岗位其他人的额外权限
    const peers = await db.employee.findMany({
      where: {
        positionId: employee.positionId,
        id: { not: employeeId }
      },
      include: { extraPermissions: true }
    });
    
    const peerPermFreq = new Map<string, number>();
    peers.forEach(peer => {
      peer.extraPermissions?.forEach(perm => {
        peerPermFreq.set(perm, (peerPermFreq.get(perm) || 0) + 1);
      });
    });
    
    // 同岗位 70% 以上的人都有的权限，推荐给这个人
    peerPermFreq.forEach((freq, perm) => {
      const ratio = freq / peers.length;
      if (ratio >= 0.7) {
        recommendations.push({
          permission: perm,
          confidence: ratio * 0.9,  // 最多 90%
          reason: `${Math.round(ratio * 100)}% 的 ${employee.position.name} 都有这个权限`
        });
      }
    });
    
    // 3. 分析操作历史
    const recentActions = await db.auditLog.findMany({
      where: { actorId: employeeId },
      orderBy: { createdAt: 'desc' },
      take: 100
    });
    
    const deniedActions = recentActions.filter(a => a.status === 'denied');
    deniedActions.slice(0, 5).forEach(action => {
      recommendations.push({
        permission: action.requiredPermission,
        confidence: 0.6,
        reason: `你最近尝试过此操作，但缺少权限`
      });
    });
    
    // 4. 分析上级的权限
    if (employee.manager) {
      const managerPerms = await this.getEffectivePermissions(employee.manager.id);
      
      // 如果主管有某个权限，这个人也可能需要（但不一定）
      const inheritablePerms = managerPerms.filter(p => p.inheritable);
      inheritablePerms.forEach(perm => {
        recommendations.push({
          permission: perm.name,
          confidence: 0.5,
          reason: `你的主管 ${employee.manager.name} 有这个权限`
        });
      });
    }
    
    // 5. 去重 & 排序
    const uniqueRecs = new Map<string, typeof recommendations[0]>();
    recommendations.forEach(rec => {
      const existing = uniqueRecs.get(rec.permission);
      if (!existing || rec.confidence > existing.confidence) {
        uniqueRecs.set(rec.permission, rec);
      }
    });
    
    // 按置信度排序
    return Array.from(uniqueRecs.values())
      .sort((a, b) => b.confidence - a.confidence)
      .slice(0, 10);  // 返回前 10 个推荐
  }
  
  private async getEffectivePermissions(employeeId: string): Promise<Permission[]> {
    // 合并继承权限 + 额外权限
  }
}
```

---

## 二、模块 3：数据建模设计器 - 实现细节

### 2.1 数据模型存储 Schema

```typescript
// 数据建模相关的数据模型

interface DataModel {
  id: string;
  appId: string;
  name: string;              // 表名
  displayName: string;       // 显示名
  description: string;
  
  // 字段定义
  fields: DataField[];
  
  // 关系定义
  relations: DataRelation[];
  
  // 索引定义
  indexes: DataIndex[];
  
  // 验证规则
  validations: ValidationRule[];
  
  // 生成的制品
  prismaModel?: string;      // 生成的 Prisma 模型代码
  sqlSchema?: string;        // 生成的 SQL 建表语句
  
  // 版本与发布
  version: string;
  status: 'draft' | 'published' | 'deprecated';
  
  // 元数据
  createdAt: Date;
  updatedAt: Date;
  createdBy: string;
}

interface DataField {
  id: string;
  name: string;
  displayName: string;
  
  // 字段类型
  type: 'string' | 'integer' | 'decimal' | 'boolean' | 'date' | 'datetime' 
        | 'json' | 'enum' | 'reference' | 'file' | 'image' | 'rich_text';
  
  // 类型配置
  config?: {
    length?: number;              // varchar(50)
    precision?: number;           // decimal 精度
    scale?: number;               // decimal 小数位
    defaultValue?: any;
    enumValues?: string[];        // 枚举值
    referencedModel?: string;     // 外键引用的模型
    referenceField?: string;      // 外键引用的字段
  };
  
  // 约束
  constraints: {
    primaryKey?: boolean;
    unique?: boolean;
    notNull?: boolean;
    foreignKey?: boolean;
    autoIncrement?: boolean;
  };
  
  // 文档
  description: string;
  businessMeaning?: string;      // 业务含义说明
}

interface DataRelation {
  id: string;
  name: string;
  
  // 关系方向
  fromModel: string;
  fromField: string;
  
  toModel: string;
  toField: string;
  
  // 关系类型
  type: 'one-to-one' | 'one-to-many' | 'many-to-many';
  
  // 级联操作
  cascadeDelete?: boolean;
  cascadeUpdate?: boolean;
}

interface DataIndex {
  id: string;
  name: string;
  
  // 索引字段
  fields: Array<{ fieldId: string; order: 'ASC' | 'DESC' }>;
  
  // 索引类型
  type: 'normal' | 'unique' | 'fulltext';
  
  description?: string;
}

interface ValidationRule {
  id: string;
  fieldId: string;
  
  // 验证规则
  type: 'required' | 'unique' | 'regex' | 'length' | 'range' | 'custom';
  
  config: {
    pattern?: string;             // 正则表达式
    minLength?: number;
    maxLength?: number;
    min?: number;
    max?: number;
    customFunction?: string;      // 自定义校验函数
  };
  
  errorMessage: string;           // 错误提示
}
```

### 2.2 生成 Prisma Schema 的算法

```typescript
class DataModelToPrismaGenerator {
  
  generate(dataModel: DataModel): string {
    let schema = `// 自动生成的 Prisma Schema\n\n`;
    
    // 生成 datasource 和 generator（仅一次）
    if (dataModel.isFirstModel) {
      schema += `datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

generator client {
  provider = "prisma-client-js"
}

`;
    }
    
    // 生成 model 定义
    schema += `model ${dataModel.name} {\n`;
    
    // 字段定义
    dataModel.fields.forEach(field => {
      schema += this.generateFieldLine(field);
    });
    
    // 关系字段
    dataModel.relations.forEach(rel => {
      if (rel.fromModel === dataModel.name) {
        schema += this.generateRelationField(rel);
      }
    });
    
    // 主键定义
    const pkField = dataModel.fields.find(f => f.constraints.primaryKey);
    if (pkField) {
      schema += `\n  @@id([${pkField.name}])\n`;
    }
    
    // 复合唯一约束
    const uniqueFields = dataModel.fields.filter(f => f.constraints.unique);
    if (uniqueFields.length > 1) {
      const names = uniqueFields.map(f => f.name).join(', ');
      schema += `  @@unique([${names}])\n`;
    }
    
    // 索引定义
    dataModel.indexes.forEach((idx, i) => {
      const fields = idx.fields.map(f => f.fieldId).join(', ');
      schema += `  @@index([${fields}])\n`;
    });
    
    schema += `}\n`;
    
    return schema;
  }
  
  private generateFieldLine(field: DataField): string {
    let line = `  ${field.name}`;
    
    // 类型映射
    const prismaType = this.mapToPrismaType(field.type, field.config);
    line += ` ${prismaType}`;
    
    // 修饰符
    if (field.constraints.primaryKey) line += ` @id`;
    if (field.constraints.autoIncrement) line += ` @default(autoincrement())`;
    if (field.constraints.unique) line += ` @unique`;
    if (!field.constraints.notNull && !field.constraints.primaryKey) line += `?`;
    
    // 默认值
    if (field.config?.defaultValue !== undefined) {
      const defaultVal = this.formatValue(field.config.defaultValue);
      line += ` @default(${defaultVal})`;
    }
    
    // 数据库类型注解
    if (field.config?.length) line += ` @db.VarChar(${field.config.length})`;
    
    line += `\n`;
    return line;
  }
  
  private generateRelationField(rel: DataRelation): string {
    if (rel.type === 'one-to-many') {
      // 一对多：在"一"侧定义关系字段
      return `  ${rel.name}  ${rel.toModel}[] @relation("${rel.name}")\n`;
    } else if (rel.type === 'one-to-one') {
      // 一对一：双向定义
      return `  ${rel.name}  ${rel.toModel}? @relation("${rel.name}")\n`;
    }
    return '';
  }
  
  private mapToPrismaType(type: string, config?: any): string {
    const mapping: Record<string, string> = {
      'string': 'String',
      'integer': 'Int',
      'decimal': `Decimal`,
      'boolean': 'Boolean',
      'date': 'DateTime',
      'datetime': 'DateTime',
      'json': 'Json',
      'enum': `${config?.enumName || 'Enum'}`,
      'file': 'String',           // 文件 URL
      'image': 'String',          // 图片 URL
      'rich_text': 'String'       // 大文本
    };
    return mapping[type] || 'String';
  }
  
  private formatValue(value: any): string {
    if (value === 'now') return 'now()';
    if (typeof value === 'string') return `"${value}"`;
    if (typeof value === 'boolean') return value ? 'true' : 'false';
    return String(value);
  }
}
```

### 2.3 AI 自动建模流程

```typescript
class AIDataModelGenerator {
  
  async generateFromDescription(description: string): Promise<DataModel> {
    // 调用 Claude API 进行分析
    const response = await this.analyzeWithAI(description);
    
    // 解析 AI 输出，转换为 DataModel
    const dataModel = this.parseAIResponse(response);
    
    return dataModel;
  }
  
  private async analyzeWithAI(description: string): Promise<string> {
    const prompt = `
用户需求: "${description}"

请分析并返回一个 JSON 格式的数据模型定义，包括：
1. 核心实体（表）及其字段
2. 实体间的关系（1:1 / 1:N / M:N）
3. 建议的索引

返回格式：
{
  "entities": [
    {
      "name": "Order",
      "displayName": "订单",
      "fields": [
        { "name": "id", "type": "integer", "constraints": { "primaryKey": true } },
        { "name": "orderNo", "type": "string", "constraints": { "unique": true } },
        ...
      ]
    }
  ],
  "relations": [
    { "from": "Order", "to": "Customer", "type": "many-to-one" }
  ],
  "indexes": [
    { "model": "Order", "fields": ["orderNo", "createdAt"] }
  ]
}
    `;
    
    const result = await claude.messages.create({
      model: "claude-3-5-sonnet-20241022",
      max_tokens: 2000,
      messages: [{
        role: "user",
        content: prompt
      }]
    });
    
    return result.content[0].text;
  }
  
  private parseAIResponse(response: string): DataModel {
    // 从 AI 响应中提取 JSON
    const jsonMatch = response.match(/\{[\s\S]*\}/);
    if (!jsonMatch) throw new Error('AI 响应格式错误');
    
    const parsed = JSON.parse(jsonMatch[0]);
    
    // 转换为 DataModel 格式
    return {
      id: generateId(),
      name: parsed.entities[0].name,
      displayName: parsed.entities[0].displayName,
      fields: parsed.entities[0].fields.map(this.mapField),
      relations: parsed.relations.map(this.mapRelation),
      indexes: parsed.indexes.map(this.mapIndex),
      version: '1.0',
      status: 'draft'
    };
  }
  
  private mapField(field: any): DataField {
    return {
      id: generateId(),
      name: field.name,
      displayName: field.displayName || field.name,
      type: field.type,
      constraints: field.constraints || {},
      description: field.description || ''
    };
  }
  
  private mapRelation(rel: any): DataRelation {
    return {
      id: generateId(),
      name: `${rel.from}_${rel.to}`,
      fromModel: rel.from,
      toModel: rel.to,
      type: rel.type
    };
  }
  
  private mapIndex(idx: any): DataIndex {
    return {
      id: generateId(),
      name: `idx_${idx.fields.join('_')}`,
      fields: idx.fields.map(f => ({ fieldId: f, order: 'ASC' })),
      type: 'normal'
    };
  }
}
```

---

## 三、模块 5：逻辑编排设计器 - 实现细节

### 3.1 逻辑节点类型系统

```typescript
// 逻辑编排节点定义

type NodeType = 'event' | 'condition' | 'data' | 'api' | 'loop' | 
                'function' | 'error' | 'parallel' | 'variable' | 'return';

// 基础节点接口
interface LogicNode {
  id: string;
  type: NodeType;
  name: string;
  position: { x: number; y: number };
  
  // 节点配置（取决于具体类型）
  config: NodeConfig;
  
  // 连接
  inputs: string[];   // 前置节点 ID
  outputs: string[];  // 后置节点 ID
}

type NodeConfig = 
  | EventNodeConfig
  | ConditionNodeConfig
  | DataNodeConfig
  | APINodeConfig
  | LoopNodeConfig
  | FunctionNodeConfig
  | ErrorHandlerConfig
  | ParallelNodeConfig
  | VariableConfig
  | ReturnConfig;

// ===== 事件节点 =====
interface EventNodeConfig {
  eventType: 'form_submit' | 'button_click' | 'timer' | 'webhook' | 'page_load';
  
  // 表单提交事件
  formId?: string;
  formFields?: Array<{ fieldId: string; fieldName: string }>;
  
  // 按钮点击事件
  buttonId?: string;
  
  // 定时器事件
  timerInterval?: number;         // 毫秒
  timerCron?: string;             // Cron 表达式
  
  // Webhook 事件
  webhookUrl?: string;
  webhookMethod?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  webhookAuthType?: 'none' | 'api_key' | 'bearer' | 'basic';
}

// ===== 条件节点 =====
interface ConditionNodeConfig {
  expression: string;             // e.g., "${order.amount} > 10000"
  operator?: 'and' | 'or';
  
  // 分支配置
  trueBranch?: string;            // true 分支的节点 ID
  falseBranch?: string;           // false 分支的节点 ID（可选）
  
  // 多分支（Switch）
  cases?: Array<{
    value: string;
    nodeId: string;
  }>;
  defaultNodeId?: string;
}

// ===== 数据操作节点 =====
interface DataNodeConfig {
  operation: 'select' | 'insert' | 'update' | 'delete' | 'batch' | 'count' | 'aggregate';
  
  table: string;                  // 操作的表名
  
  // SELECT 操作
  columns?: string[];             // 选择的列
  where?: FilterExpression;       // WHERE 条件
  orderBy?: Array<{ field: string; order: 'ASC' | 'DESC' }>;
  limit?: number;
  offset?: number;
  
  // INSERT 操作
  values?: Record<string, any>;   // 要插入的值
  
  // UPDATE 操作
  updateSet?: Record<string, any>;
  
  // 输出变量
  resultVariable?: string;        // 结果存储的变量名
}

// ===== API 调用节点 =====
interface APINodeConfig {
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  url: string;
  
  // 请求配置
  headers?: Record<string, string>;
  queryParams?: Record<string, string>;
  body?: Record<string, any>;
  
  // 认证
  authType?: 'none' | 'api_key' | 'bearer' | 'basic' | 'oauth2';
  authConfig?: any;
  
  // 超时与重试
  timeout?: number;               // 毫秒
  retries?: number;
  retryDelay?: number;
  
  // 响应处理
  successStatusCodes?: number[];  // 默认 [200, 201]
  responseVariable?: string;      // 结果变量
  
  // 错误处理
  errorNodeId?: string;           // 失败时跳转的节点
}

// ===== 循环节点 =====
interface LoopNodeConfig {
  loopType: 'for' | 'while' | 'foreach';
  
  // FOR 循环
  startValue?: number;
  endValue?: number;
  stepValue?: number;
  loopVariable?: string;
  
  // FOREACH 循环
  arrayVariable?: string;         // 要遍历的数组变量
  itemVariable?: string;          // 单项变量名
  
  // WHILE 循环
  whileCondition?: string;        // 循环条件表达式
  
  // 循环体
  bodyNodeId?: string;            // 循环体的起始节点
  breakNodeId?: string;           // 中断条件节点（可选）
}

// ===== 函数定义节点 =====
interface FunctionNodeConfig {
  functionName: string;
  
  // 参数定义
  parameters?: Array<{
    name: string;
    type: string;
    default?: any;
  }>;
  
  // 函数体（逻辑编排的子流程）
  bodyNodeId?: string;
  
  // 返回值
  returnType?: string;
  returnExpression?: string;
}

// ===== 错误处理节点 =====
interface ErrorHandlerConfig {
  errorType: 'all' | 'specific';
  
  // 捕获特定错误类型
  errorPatterns?: string[];
  
  // 处理逻辑
  handlerNodeId?: string;
  
  // 是否重新抛出异常
  rethrow?: boolean;
}

// ===== 并行执行节点 =====
interface ParallelNodeConfig {
  branches: Array<{
    name: string;
    startNodeId: string;
  }>;
  
  // 合并策略
  mergeStrategy: 'wait_all' | 'wait_first' | 'wait_any';
}

// ===== 变量赋值节点 =====
interface VariableConfig {
  variableName: string;
  
  // 赋值表达式
  expression: string;
  
  // 变量作用域
  scope: 'local' | 'global' | 'persistent';
}

// ===== 返回节点 =====
interface ReturnConfig {
  returnExpression?: string;
  
  // 返回值映射
  output?: Record<string, string>;
}

// ===== 通用过滤表达式 =====
interface FilterExpression {
  operator: 'and' | 'or';
  conditions: Array<{
    field: string;
    operator: '=' | '!=' | '>' | '<' | '>=' | '<=' | 'in' | 'like';
    value: any;
  }>;
}
```

### 3.2 生成 TypeScript 代码的引擎

```typescript
class LogicFlowToCodeGenerator {
  
  generate(flow: LogicFlow, language: 'typescript' | 'python' = 'typescript'): string {
    if (language === 'typescript') {
      return this.generateTypeScript(flow);
    } else if (language === 'python') {
      return this.generatePython(flow);
    }
  }
  
  private generateTypeScript(flow: LogicFlow): string {
    let code = `// 自动生成的逻辑编排代码\n\n`;
    
    // 生成函数签名
    const eventNode = this.findEventNode(flow);
    const funcName = this.camelCase(eventNode.name);
    
    code += `export async function ${funcName}(input: any): Promise<any> {\n`;
    
    // 声明变量
    code += `  // 声明变量\n`;
    code += `  let result: any = null;\n`;
    code += `  const variables: Record<string, any> = {};\n\n`;
    
    // 生成节点代码
    const nodeIds = this.topologicalSort(flow);
    const generatedIds = new Set<string>();
    
    for (const nodeId of nodeIds) {
      if (generatedIds.has(nodeId)) continue;
      
      const node = flow.nodes.find(n => n.id === nodeId);
      if (!node) continue;
      
      code += this.generateNodeCode(node, flow);
      generatedIds.add(nodeId);
    }
    
    code += `\n  return result;\n`;
    code += `}\n`;
    
    return code;
  }
  
  private generateNodeCode(node: LogicNode, flow: LogicFlow): string {
    switch (node.type) {
      case 'condition':
        return this.generateConditionCode(node as LogicNode);
      case 'data':
        return this.generateDataCode(node as LogicNode);
      case 'api':
        return this.generateAPICode(node as LogicNode);
      case 'loop':
        return this.generateLoopCode(node as LogicNode);
      case 'variable':
        return this.generateVariableCode(node as LogicNode);
      default:
        return '';
    }
  }
  
  private generateConditionCode(node: LogicNode): string {
    const cfg = node.config as ConditionNodeConfig;
    
    let code = `  // 条件判断: ${node.name}\n`;
    code += `  if (${this.formatExpression(cfg.expression)}) {\n`;
    
    // 真分支代码...
    code += `    // 真分支逻辑\n`;
    
    code += `  } else {\n`;
    code += `    // 假分支逻辑\n`;
    code += `  }\n\n`;
    
    return code;
  }
  
  private generateDataCode(node: LogicNode): string {
    const cfg = node.config as DataNodeConfig;
    
    let code = `  // 数据操作: ${node.name}\n`;
    
    switch (cfg.operation) {
      case 'select':
        code += `  result = await db.${this.camelCase(cfg.table)}.findMany({\n`;
        code += `    // WHERE 条件\n`;
        code += `  });\n`;
        break;
      case 'insert':
        code += `  result = await db.${this.camelCase(cfg.table)}.create({\n`;
        code += `    data: ${JSON.stringify(cfg.values, null, 2)}\n`;
        code += `  });\n`;
        break;
      case 'update':
        code += `  result = await db.${this.camelCase(cfg.table)}.updateMany({\n`;
        code += `    // WHERE 条件\n`;
        code += `    data: ${JSON.stringify(cfg.updateSet, null, 2)}\n`;
        code += `  });\n`;
        break;
    }
    
    if (cfg.resultVariable) {
      code += `  variables['${cfg.resultVariable}'] = result;\n`;
    }
    
    code += `\n`;
    return code;
  }
  
  private generateAPICode(node: LogicNode): string {
    const cfg = node.config as APINodeConfig;
    
    let code = `  // API 调用: ${node.name}\n`;
    code += `  try {\n`;
    code += `    const response = await fetch('${cfg.url}', {\n`;
    code += `      method: '${cfg.method}',\n`;
    
    if (cfg.headers) {
      code += `      headers: ${JSON.stringify(cfg.headers, null, 8)},\n`;
    }
    
    if (cfg.body) {
      code += `      body: JSON.stringify(${JSON.stringify(cfg.body, null, 8)}),\n`;
    }
    
    code += `    });\n\n`;
    code += `    result = await response.json();\n`;
    code += `    \n`;
    
    if (cfg.responseVariable) {
      code += `    variables['${cfg.responseVariable}'] = result;\n`;
    }
    
    code += `  } catch (error) {\n`;
    code += `    console.error('API call failed:', error);\n`;
    code += `    throw error;\n`;
    code += `  }\n\n`;
    
    return code;
  }
  
  private generateLoopCode(node: LogicNode): string {
    const cfg = node.config as LoopNodeConfig;
    
    let code = `  // 循环: ${node.name}\n`;
    
    if (cfg.loopType === 'foreach') {
      code += `  for (const ${cfg.itemVariable} of ${cfg.arrayVariable}) {\n`;
      code += `    // 循环体\n`;
      code += `  }\n`;
    }
    
    code += `\n`;
    return code;
  }
  
  private generateVariableCode(node: LogicNode): string {
    const cfg = node.config as VariableConfig;
    
    let code = `  // 变量赋值: ${node.name}\n`;
    code += `  variables['${cfg.variableName}'] = ${this.formatExpression(cfg.expression)};\n\n`;
    
    return code;
  }
  
  private formatExpression(expr: string): string {
    // 将 ${var} 转换为 variables['var']
    return expr.replace(/\$\{(\w+)\}/g, "variables['$1']");
  }
  
  private topologicalSort(flow: LogicFlow): string[] {
    // 使用 Kahn 算法进行拓扑排序
    const inDegree = new Map<string, number>();
    const adjList = new Map<string, string[]>();
    
    flow.nodes.forEach(node => {
      inDegree.set(node.id, 0);
      adjList.set(node.id, []);
    });
    
    flow.edges?.forEach(edge => {
      inDegree.set(edge.to, (inDegree.get(edge.to) || 0) + 1);
      adjList.get(edge.from)?.push(edge.to);
    });
    
    const queue = Array.from(inDegree.entries())
      .filter(([_, degree]) => degree === 0)
      .map(([id, _]) => id);
    
    const result: string[] = [];
    while (queue.length > 0) {
      const node = queue.shift()!;
      result.push(node);
      
      adjList.get(node)?.forEach(neighbor => {
        inDegree.set(neighbor, (inDegree.get(neighbor) || 0) - 1);
        if (inDegree.get(neighbor) === 0) {
          queue.push(neighbor);
        }
      });
    }
    
    return result;
  }
  
  private camelCase(str: string): string {
    return str.replace(/[-_](.)/g, (_, c) => c.toUpperCase());
  }
  
  private findEventNode(flow: LogicFlow): LogicNode {
    return flow.nodes.find(n => n.type === 'event')!;
  }
}
```

---

## 四、模块 13：安全与合规中心 - 国密集成方案

### 4.1 国密库集成

```typescript
// 国密算法集成方案

import TongSuo from '@tongsuo/nodejs';  // 或 GmSSL

class CryptoService {
  private sm2KeyPair: any;
  private sm4Key: Buffer;
  private sm3: any;
  
  constructor() {
    this.initializeKeys();
  }
  
  // ===== SM2: 公钥密码（椭圆曲线） =====
  
  /**
   * 生成 SM2 密钥对
   */
  generateSM2KeyPair(): { publicKey: string; privateKey: string } {
    const ec = TongSuo.createECDH('SM2');
    const pubKey = ec.generateKeys();
    const privKey = ec.getPrivateKey();
    
    return {
      publicKey: pubKey.toString('base64'),
      privateKey: privKey.toString('base64')
    };
  }
  
  /**
   * 使用 SM2 公钥加密
   */
  sm2Encrypt(publicKey: string, plaintext: string): string {
    const ec = TongSuo.createECDH('SM2');
    ec.setPublicKey(Buffer.from(publicKey, 'base64'));
    
    const ciphertext = ec.computeSecret(Buffer.from(plaintext));
    return ciphertext.toString('base64');
  }
  
  /**
   * 使用 SM2 私钥解密
   */
  sm2Decrypt(privateKey: string, ciphertext: string): string {
    const ec = TongSuo.createECDH('SM2');
    ec.setPrivateKey(Buffer.from(privateKey, 'base64'));
    
    const plaintext = ec.computeSecret(Buffer.from(ciphertext, 'base64'));
    return plaintext.toString('utf-8');
  }
  
  /**
   * SM2 数字签名
   */
  sm2Sign(privateKey: string, data: string): string {
    const signature = TongSuo.createSign('SM2withSM3');
    signature.update(data);
    
    return signature.sign(
      Buffer.from(privateKey, 'base64'),
      'base64'
    );
  }
  
  /**
   * SM2 签名验证
   */
  sm2Verify(publicKey: string, data: string, signature: string): boolean {
    const verifier = TongSuo.createVerify('SM2withSM3');
    verifier.update(data);
    
    return verifier.verify(
      Buffer.from(publicKey, 'base64'),
      Buffer.from(signature, 'base64')
    );
  }
  
  // ===== SM3: 密码哈希算法（256 位） =====
  
  /**
   * 计算 SM3 哈希值
   */
  sm3Hash(data: string): string {
    const hash = TongSuo.createHash('SM3');
    hash.update(data);
    return hash.digest('hex');
  }
  
  /**
   * SM3-HMAC（消息认证码）
   */
  sm3HMAC(key: string, data: string): string {
    const hmac = TongSuo.createHmac('SM3', key);
    hmac.update(data);
    return hmac.digest('hex');
  }
  
  // ===== SM4: 对称密码（分组密码，128 位） =====
  
  /**
   * 生成 SM4 密钥（128 位 = 16 字节）
   */
  generateSM4Key(): string {
    const key = TongSuo.randomBytes(16);
    return key.toString('base64');
  }
  
  /**
   * SM4 加密（CBC 模式）
   */
  sm4Encrypt(key: string, plaintext: string): string {
    const cipher = TongSuo.createCipheriv(
      'SM4-128-CBC',
      Buffer.from(key, 'base64'),
      Buffer.alloc(16, 0)  // IV (初始化向量)
    );
    
    let ciphertext = cipher.update(plaintext, 'utf-8', 'base64');
    ciphertext += cipher.final('base64');
    
    return ciphertext;
  }
  
  /**
   * SM4 解密
   */
  sm4Decrypt(key: string, ciphertext: string): string {
    const decipher = TongSuo.createDecipheriv(
      'SM4-128-CBC',
      Buffer.from(key, 'base64'),
      Buffer.alloc(16, 0)
    );
    
    let plaintext = decipher.update(ciphertext, 'base64', 'utf-8');
    plaintext += decipher.final('utf-8');
    
    return plaintext;
  }
  
  // ===== 密钥管理 =====
  
  /**
   * 密钥轮换
   */
  rotateKeys(): { newKey: string; oldKey: string; nextRotation: Date } {
    const newKey = this.generateSM4Key();
    const oldKey = this.sm4Key.toString('base64');
    
    // 存储新密钥，保留旧密钥用于解密存量数据
    this.sm4Key = Buffer.from(newKey, 'base64');
    
    const nextRotation = new Date();
    nextRotation.setDate(nextRotation.getDate() + 90);  // 90 天后下一次轮换
    
    return { newKey, oldKey, nextRotation };
  }
  
  /**
   * 获取密钥版本信息
   */
  getKeyVersionInfo(): any {
    return {
      sm2: {
        status: 'enabled',
        algorithm: 'EC P-256',
        keySize: 256,
        created: '2026-01-16',
        expires: '2029-01-16'
      },
      sm3: {
        status: 'enabled',
        algorithm: 'Hash',
        outputSize: 256
      },
      sm4: {
        status: 'enabled',
        algorithm: 'Block Cipher',
        keySize: 128,
        currentVersion: 'v2',
        previousVersion: 'v1',
        nextRotation: '2026-04-16'
      }
    };
  }
  
  private initializeKeys(): void {
    // 从配置/环境变量加载密钥
    this.sm4Key = Buffer.from(
      process.env.SM4_KEY_V2 || this.generateSM4Key(),
      'base64'
    );
  }
}

// 导出单例
export const cryptoService = new CryptoService();
```

### 4.2 敏感数据脱敏配置

```typescript
// 敏感字段脱敏规则

interface MaskingRule {
  fieldName: string;
  fieldType: string;           // 'idCard' | 'bankCard' | 'phone' | 'email' etc.
  maskType: 'prefix' | 'suffix' | 'center' | 'custom';
  config: {
    showPrefix?: number;       // 显示前 N 位
    showSuffix?: number;       // 显示后 N 位
    maskChar?: string;         // 掩码字符，默认 '*'
    customPattern?: string;    // 自定义正则替换
  };
}

class DataMaskingService {
  private maskingRules: Map<string, MaskingRule> = new Map();
  
  constructor() {
    this.initializeDefaultRules();
  }
  
  private initializeDefaultRules(): void {
    // 身份证号：显示前3位/后1位
    this.maskingRules.set('idCard', {
      fieldName: 'idCard',
      fieldType: 'idCard',
      maskType: 'custom',
      config: {
        customPattern: '(\\d{3})\\d*(\\d{1})',
        replacement: '$1*********$2'
      }
    });
    
    // 银行卡号：显示后4位
    this.maskingRules.set('bankCard', {
      fieldName: 'bankCard',
      fieldType: 'bankCard',
      maskType: 'suffix',
      config: {
        showSuffix: 4,
        maskChar: '*'
      }
    });
    
    // 手机号：显示前3位/后2位
    this.maskingRules.set('phone', {
      fieldName: 'phone',
      fieldType: 'phone',
      maskType: 'custom',
      config: {
        customPattern: '(\\d{3})\\d*(\\d{2})',
        replacement: '$1****$2'
      }
    });
    
    // 邮箱：显示前3个字符
    this.maskingRules.set('email', {
      fieldName: 'email',
      fieldType: 'email',
      maskType: 'prefix',
      config: {
        showPrefix: 3,
        maskChar: '*'
      }
    });
  }
  
  /**
   * 对数据进行脱敏
   */
  maskData(data: any, rules: MaskingRule[]): any {
    if (typeof data === 'string') {
      return this.maskString(data, rules[0]);
    }
    
    if (typeof data === 'object' && data !== null) {
      const masked: any = {};
      
      for (const [key, value] of Object.entries(data)) {
        const rule = rules.find(r => r.fieldName === key);
        
        if (rule) {
          masked[key] = this.maskString(String(value), rule);
        } else {
          masked[key] = value;
        }
      }
      
      return masked;
    }
    
    return data;
  }
  
  private maskString(value: string, rule: MaskingRule): string {
    if (rule.maskType === 'custom' && rule.config.customPattern) {
      return value.replace(
        new RegExp(rule.config.customPattern),
        rule.config.replacement || ''
      );
    }
    
    if (rule.maskType === 'prefix' && rule.config.showPrefix) {
      const prefix = value.substring(0, rule.config.showPrefix);
      const masked = rule.config.maskChar?.repeat(value.length - rule.config.showPrefix) || '****';
      return prefix + masked;
    }
    
    if (rule.maskType === 'suffix' && rule.config.showSuffix) {
      const suffix = value.substring(value.length - rule.config.showSuffix);
      const masked = rule.config.maskChar?.repeat(value.length - rule.config.showSuffix) || '****';
      return masked + suffix;
    }
    
    return value;
  }
}

export const maskingService = new DataMaskingService();
```

### 4.3 审计日志记录

```typescript
// 审计日志模型和服务

interface AuditLog {
  id: string;
  timestamp: Date;
  
  // 执行者信息
  actorId: string;
  actorName: string;
  actorIp: string;
  
  // 操作信息
  action: string;             // create, read, update, delete, approve, reject
  resourceType: string;       // order, customer, permission, etc.
  resourceId?: string;
  
  // 变更详情
  changesBefore?: Record<string, any>;
  changesAfter?: Record<string, any>;
  
  // 安全相关
  encrypted: boolean;         // 是否采用 SM4 加密存储
  hashValue: string;          // SM3 哈希值（用于完整性验证）
  signature?: string;         // SM2 数字签名
  
  // 结果
  status: 'success' | 'failure';
  errorMessage?: string;
  
  // 敏感数据处理
  masked: boolean;            // 是否已脱敏
  
  createdAt: Date;
}

class AuditLogService {
  
  async recordAudit(auditData: Partial<AuditLog>): Promise<string> {
    const audit: AuditLog = {
      id: generateId(),
      timestamp: new Date(),
      
      actorId: auditData.actorId || 'unknown',
      actorName: auditData.actorName || '',
      actorIp: auditData.actorIp || '',
      
      action: auditData.action || '',
      resourceType: auditData.resourceType || '',
      
      encrypted: true,
      hashValue: '',
      signature: '',
      
      status: 'success',
      masked: false,
      
      createdAt: new Date()
    };
    
    // 计算 SM3 哈希值（用于完整性验证）
    const auditString = JSON.stringify(audit);
    audit.hashValue = cryptoService.sm3Hash(auditString);
    
    // 对敏感字段进行脱敏
    if (audit.changesAfter) {
      audit.masked = true;
      audit.changesAfter = maskingService.maskData(
        audit.changesAfter,
        this.getSensitiveFields(audit.resourceType)
      );
    }
    
    // 加密存储（若启用）
    const encrypted = this.encryptAuditLog(audit);
    
    // 存入数据库
    await db.auditLog.create({
      data: {
        id: audit.id,
        timestamp: audit.timestamp,
        actorId: audit.actorId,
        actorName: audit.actorName,
        action: audit.action,
        resourceType: audit.resourceType,
        encryptedData: encrypted,
        hashValue: audit.hashValue,
        status: audit.status
      }
    });
    
    return audit.id;
  }
  
  /**
   * 验证审计日志的完整性
   */
  async verifyAuditIntegrity(auditId: string): Promise<boolean> {
    const audit = await db.auditLog.findUnique({ where: { id: auditId } });
    
    if (!audit) return false;
    
    // 解密
    const decrypted = this.decryptAuditLog(audit.encryptedData);
    
    // 重新计算哈希值
    const recalculatedHash = cryptoService.sm3Hash(JSON.stringify(decrypted));
    
    // 比较哈希值
    return recalculatedHash === audit.hashValue;
  }
  
  private encryptAuditLog(audit: AuditLog): string {
    const auditString = JSON.stringify(audit);
    return cryptoService.sm4Encrypt(
      process.env.SM4_KEY_V2 || '',
      auditString
    );
  }
  
  private decryptAuditLog(encrypted: string): AuditLog {
    const decrypted = cryptoService.sm4Decrypt(
      process.env.SM4_KEY_V2 || '',
      encrypted
    );
    return JSON.parse(decrypted);
  }
  
  private getSensitiveFields(resourceType: string): any[] {
    const sensitiveFieldMap: Record<string, any[]> = {
      'customer': [
        { fieldName: 'idCard', fieldType: 'idCard' },
        { fieldName: 'phone', fieldType: 'phone' },
        { fieldName: 'email', fieldType: 'email' }
      ],
      'order': [
        { fieldName: 'customerId', fieldType: 'phone' }
      ]
    };
    
    return sensitiveFieldMap[resourceType] || [];
  }
}

export const auditLogService = new AuditLogService();
```

---

## 五、集成与部署清单

### 5.1 技术栈补充

```
后端:
├─ Node.js / NestJS (已有)
├─ Prisma ORM (已有)
├─ PostgreSQL (已有)
├─ ✅ 新增: TongSuo / GmSSL (国密库)
├─ ✅ 新增: Graph QL / Apollo Server (组织层级查询优化)
└─ ✅ 新增: Bull Queue (定时任务调度)

前端:
├─ React / Vue.js (已有)
├─ Monaco Editor (代码编辑，已有)
├─ ✅ 新增: React Flow / Mxgraph (逻辑编排可视化)
├─ ✅ 新增: ECharts (数据可视化)
└─ ✅ 新增: Figma Plugin (UI 设计稿导入)

基础设施:
├─ Docker (已有)
├─ Kubernetes (已有)
├─ ✅ 新增: Vault (密钥管理)
└─ ✅ 新增: OpenTelemetry (审计日志收集)
```

### 5.2 部署检查清单

```
安全合规检查:
☐ 国密算法集成与测试 (SM2/SM3/SM4)
☐ 密钥管理策略配置 (Vault / HSM)
☐ 审计日志完整性验证
☐ 敏感数据脱敏规则应用
☐ 安全漏洞扫描 (OWASP Top 10)
☐ 密钥备份与恢复测试

组织模型部署:
☐ 数据库迁移 (部门、岗位、员工表)
☐ 组织架构 API 实现与测试
☐ 权限推荐引擎部署
☐ 组织变更日志记录启用
☐ 与 BPM 设计器集成 (参与者配置)

数据建模部署:
☐ 数据模型编辑器部署
☐ Prisma Schema 生成逻辑验证
☐ 自动迁移脚本生成与测试
☐ AI 建模功能集成 (Claude API)

逻辑编排部署:
☐ 可视化编排器部署
☐ 代码生成引擎测试 (TypeScript/Python)
☐ 逻辑执行引擎部署
☐ 错误处理与调试工具
☐ AI 代码生成集成 (Claude API)

测试覆盖:
☐ 单元测试 (所有核心模块 >80% 覆盖率)
☐ 集成测试 (跨模块交互)
☐ 性能测试 (大型组织 10000+ 人)
☐ 安全渗透测试
☐ 国标合规性验证
```

---

**下一步：** 基于本技术细节文档，可开始实现原型或工程化细节设计。

