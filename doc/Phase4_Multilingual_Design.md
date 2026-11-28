# OpenAILCAP 多语言设计方案 (i18n)
# 国际化与本地化完整设计

**版本：** v1.0  
**日期：** 2026-11-28  
**状态：** ✅ 推荐纳入 MVP

---

## 一、多语言设计总体策略

### 1.1 支持语言清单

#### MVP 版本 (上线必须)

```
✅ 中文简体 (zh-CN)      - 默认语言，100% 覆盖
✅ 英文 (en-US)          - 国际化支持，100% 覆盖
⏳ 中文繁体 (zh-TW)      - 后续版本 (Q2)
⏳ 日语 (ja-JP)          - 后续版本 (Q2)
⏳ 韩语 (ko-KR)          - 后续版本 (Q3)
```

#### 多语言覆盖范围

```
1. 平台多语言（系统 UI）
   ├─ 菜单、按钮、标签
   ├─ 错误提示、成功消息
   ├─ 表单标签、placeholder
   ├─ 帮助文本、文档链接
   └─ 100% 覆盖

2. 应用交互多语言（用户应用的 UI）
   ├─ 表单字段显示名称
   ├─ 表格列头
   ├─ 枚举值选项
   ├─ 业务逻辑的提示文本
   └─ 由应用设计者配置

3. 应用数据多语言（业务数据）
   ├─ 客户名称、地址等多语言字段
   ├─ 产品描述、分类多语言存储
   ├─ 报告、文档多语言版本
   └─ 由数据模型支持多语言字段类型
```

---

## 二、技术架构

### 2.1 前端 i18n 实现

#### 技术栈选择

```
推荐方案: i18next (业界标准)

特点:
✓ 生态成熟，社区活跃
✓ 支持 React/Vue/Angular 等所有框架
✓ 支持命名空间 (namespace) 组织翻译
✓ 支持插值 (interpolation) 和复数
✓ 支持动态加载语言包
✓ 支持 RTL (从右到左) 的阿拉伯语等
```

#### 前端文件结构

```
src/
├─ locales/
│  ├─ zh-CN/
│  │  ├─ common.json         // 通用翻译
│  │  ├─ applications.json   // 应用管理模块
│  │  ├─ org.json            // 组织架构模块
│  │  ├─ dataModel.json      // 数据建模模块
│  │  ├─ logicFlow.json      // 逻辑编排模块
│  │  ├─ form.json           // 表单设计模块
│  │  ├─ bpm.json            // BPM 流程模块
│  │  ├─ reports.json        // 报表模块
│  │  ├─ permissions.json    // 权限管理模块
│  │  ├─ security.json       // 安全与合规模块
│  │  ├─ errors.json         // 错误提示
│  │  └─ validations.json    // 验证提示
│  │
│  └─ en-US/
│     ├─ common.json
│     ├─ applications.json
│     ├─ ... (相同结构)
│     └─ validations.json
│
├─ config/
│  └─ i18n.config.ts         // i18next 配置
│
└─ components/
   └─ LanguageSwitcher.tsx   // 语言切换器组件
```

#### i18n 配置文件示例

```typescript
// src/config/i18n.config.ts

import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import HttpBackend from 'i18next-http-backend';

// 翻译资源
import zhCNCommon from '../locales/zh-CN/common.json';
import zhCNApplications from '../locales/zh-CN/applications.json';
import enUSCommon from '../locales/en-US/common.json';
import enUSApplications from '../locales/en-US/applications.json';

const resources = {
  'zh-CN': {
    common: zhCNCommon,
    applications: zhCNApplications,
    org: require('../locales/zh-CN/org.json'),
    dataModel: require('../locales/zh-CN/dataModel.json'),
    logicFlow: require('../locales/zh-CN/logicFlow.json'),
    form: require('../locales/zh-CN/form.json'),
    bpm: require('../locales/zh-CN/bpm.json'),
    reports: require('../locales/zh-CN/reports.json'),
    permissions: require('../locales/zh-CN/permissions.json'),
    security: require('../locales/zh-CN/security.json'),
    errors: require('../locales/zh-CN/errors.json'),
    validations: require('../locales/zh-CN/validations.json'),
  },
  'en-US': {
    common: enUSCommon,
    applications: enUSApplications,
    org: require('../locales/en-US/org.json'),
    dataModel: require('../locales/en-US/dataModel.json'),
    logicFlow: require('../locales/en-US/logicFlow.json'),
    form: require('../locales/en-US/form.json'),
    bpm: require('../locales/en-US/bpm.json'),
    reports: require('../locales/en-US/reports.json'),
    permissions: require('../locales/en-US/permissions.json'),
    security: require('../locales/en-US/security.json'),
    errors: require('../locales/en-US/errors.json'),
    validations: require('../locales/en-US/validations.json'),
  }
};

i18n
  // 检测用户语言
  .use(LanguageDetector)
  // 加载翻译资源
  .use(initReactI18next)
  .init({
    resources,
    
    // 默认语言
    fallbackLng: 'zh-CN',
    
    // 命名空间
    ns: ['common'],
    defaultNS: 'common',
    
    // 插值选项
    interpolation: {
      escapeValue: false, // React 已防止 XSS
    },
    
    // 语言检测顺序
    detection: {
      order: ['localStorage', 'navigator', 'htmlTag'],
      caches: ['localStorage'],
    },
    
    // 后端加载器（生产环境）
    backend: {
      loadPath: '/locales/{{lng}}/{{ns}}.json',
    },
  });

export default i18n;
```

#### 翻译文件结构示例

```json
// locales/zh-CN/common.json
{
  "app.name": "OpenAILCAP",
  "app.version": "版本 2.0",
  "app.tagline": "AI 原生低代码平台",
  
  "common.search": "搜索",
  "common.create": "新建",
  "common.edit": "编辑",
  "common.delete": "删除",
  "common.save": "保存",
  "common.cancel": "取消",
  "common.confirm": "确认",
  "common.close": "关闭",
  "common.loading": "加载中...",
  "common.success": "成功",
  "common.error": "错误",
  "common.warning": "警告",
  "common.info": "信息",
  
  "nav.applications": "应用管理",
  "nav.organization": "组织架构",
  "nav.dataModel": "数据建模",
  "nav.form": "表单设计",
  "nav.workflow": "工作流",
  "nav.logicFlow": "逻辑编排",
  "nav.reports": "报表",
  "nav.settings": "设置",
  "nav.help": "帮助",
  
  "user.login": "登录",
  "user.logout": "登出",
  "user.profile": "个人资料",
  "user.settings": "账户设置",
  "user.language": "语言",
  
  "error.404": "页面未找到",
  "error.403": "访问被拒绝",
  "error.500": "服务器错误",
  "error.network": "网络连接失败"
}
```

```json
// locales/en-US/common.json
{
  "app.name": "OpenAILCAP",
  "app.version": "Version 2.0",
  "app.tagline": "AI-Native Low-Code Platform",
  
  "common.search": "Search",
  "common.create": "Create",
  "common.edit": "Edit",
  "common.delete": "Delete",
  "common.save": "Save",
  "common.cancel": "Cancel",
  "common.confirm": "Confirm",
  "common.close": "Close",
  "common.loading": "Loading...",
  "common.success": "Success",
  "common.error": "Error",
  "common.warning": "Warning",
  "common.info": "Information",
  
  "nav.applications": "Applications",
  "nav.organization": "Organization",
  "nav.dataModel": "Data Model",
  "nav.form": "Form Designer",
  "nav.workflow": "Workflow",
  "nav.logicFlow": "Logic Flow",
  "nav.reports": "Reports",
  "nav.settings": "Settings",
  "nav.help": "Help",
  
  "user.login": "Sign In",
  "user.logout": "Sign Out",
  "user.profile": "My Profile",
  "user.settings": "Account Settings",
  "user.language": "Language",
  
  "error.404": "Page Not Found",
  "error.403": "Access Denied",
  "error.500": "Server Error",
  "error.network": "Network Connection Failed"
}
```

#### React 组件使用示例

```typescript
// src/components/AppHeader.tsx

import React from 'react';
import { useTranslation } from 'react-i18next';

export const AppHeader: React.FC = () => {
  const { t, i18n } = useTranslation();
  
  const handleLanguageChange = (lang: string) => {
    i18n.changeLanguage(lang);
    localStorage.setItem('preferredLanguage', lang);
  };
  
  return (
    <header>
      <div className="app-name">{t('app.name')}</div>
      
      <nav>
        <a href="/applications">{t('nav.applications')}</a>
        <a href="/organization">{t('nav.organization')}</a>
        <a href="/datamodel">{t('nav.dataModel')}</a>
        <a href="/form">{t('nav.form')}</a>
      </nav>
      
      <div className="user-menu">
        <button>{t('user.profile')}</button>
        <div className="language-selector">
          <button 
            onClick={() => handleLanguageChange('zh-CN')}
            className={i18n.language === 'zh-CN' ? 'active' : ''}
          >
            中文
          </button>
          <button 
            onClick={() => handleLanguageChange('en-US')}
            className={i18n.language === 'en-US' ? 'active' : ''}
          >
            English
          </button>
        </div>
        <button onClick={() => i18n.changeLanguage('zh-CN')}>
          {t('user.logout')}
        </button>
      </div>
    </header>
  );
};
```

---

### 2.2 后端 i18n 实现

#### 后端文件结构

```
backend/src/
├─ locales/
│  ├─ zh-CN.json          // 中文文案
│  └─ en-US.json          // 英文文案
│
├─ config/
│  └─ i18n.ts             // i18n 配置
│
├─ middleware/
│  └─ i18n.middleware.ts   // 语言检测中间件
│
└─ services/
   └─ i18n.service.ts     // i18n 服务
```

#### 后端 i18n 服务

```typescript
// backend/src/services/i18n.service.ts

import { Injectable } from '@nestjs/common';
import zhCN from '../locales/zh-CN.json';
import enUS from '../locales/en-US.json';

@Injectable()
export class I18nService {
  private translations = {
    'zh-CN': zhCN,
    'en-US': enUS,
  };
  
  private defaultLanguage = 'zh-CN';
  
  /**
   * 获取翻译文案
   */
  t(key: string, language: string = this.defaultLanguage, params?: Record<string, any>): string {
    const lang = this.translations[language] || this.translations[this.defaultLanguage];
    
    let message = this.getNestedValue(lang, key) || key;
    
    // 参数替换
    if (params) {
      Object.entries(params).forEach(([paramKey, paramValue]) => {
        message = message.replace(`{{${paramKey}}}`, String(paramValue));
      });
    }
    
    return message;
  }
  
  /**
   * 获取错误提示文案
   */
  getErrorMessage(errorCode: string, language: string = this.defaultLanguage): string {
    const errorKey = `errors.${errorCode}`;
    return this.t(errorKey, language);
  }
  
  /**
   * 获取验证错误提示
   */
  getValidationMessage(fieldName: string, rule: string, language: string = this.defaultLanguage): string {
    const validationKey = `validations.${rule}`;
    return this.t(validationKey, language, { field: fieldName });
  }
  
  /**
   * 获取支持的语言列表
   */
  getSupportedLanguages(): Array<{ code: string; name: string; nativeName: string }> {
    return [
      { code: 'zh-CN', name: 'Chinese (Simplified)', nativeName: '简体中文' },
      { code: 'en-US', name: 'English', nativeName: 'English' },
    ];
  }
  
  private getNestedValue(obj: any, path: string): any {
    return path.split('.').reduce((current, prop) => current?.[prop], obj);
  }
}

// 使用示例
export class ApplicationService {
  constructor(private i18nService: I18nService) {}
  
  async createApplication(data: any, language: string) {
    try {
      // 创建应用逻辑
      return { success: true };
    } catch (error) {
      const errorMessage = this.i18nService.getErrorMessage('APP_CREATE_FAILED', language);
      throw new BadRequestException(errorMessage);
    }
  }
}
```

#### 后端中间件（语言检测）

```typescript
// backend/src/middleware/i18n.middleware.ts

import { Injectable, NestMiddleware } from '@nestjs/common';
import { Request, Response, NextFunction } from 'express';

@Injectable()
export class I18nMiddleware implements NestMiddleware {
  use(req: Request, res: Response, next: NextFunction) {
    // 语言检测顺序
    // 1. Query 参数 (?lang=en-US)
    // 2. Header (Accept-Language)
    // 3. Cookie
    // 4. 默认值 (zh-CN)
    
    let language = 'zh-CN';
    
    // 1. 检查 query 参数
    if (req.query.lang && typeof req.query.lang === 'string') {
      language = req.query.lang;
    }
    
    // 2. 检查 header
    if (req.headers['accept-language']) {
      const acceptLanguage = req.headers['accept-language'] as string;
      const preferredLang = acceptLanguage.split(',')[0].trim();
      
      // 匹配支持的语言
      if (preferredLang.startsWith('zh')) {
        language = 'zh-CN';
      } else if (preferredLang.startsWith('en')) {
        language = 'en-US';
      }
    }
    
    // 3. 检查 cookie
    if (req.cookies?.language) {
      language = req.cookies.language;
    }
    
    // 4. 检查用户配置（如果已登录）
    if (req.user?.language) {
      language = req.user.language;
    }
    
    // 附加到 request 对象
    (req as any).language = language;
    
    res.set('Content-Language', language);
    
    next();
  }
}
```

#### API 响应示例

```typescript
// 成功响应
{
  "code": 200,
  "message": "操作成功", // i18n 翻译后
  "data": { ... }
}

// 错误响应
{
  "code": 400,
  "message": "应用名称已存在", // i18n 翻译后
  "errorCode": "APP_NAME_DUPLICATE",
  "details": { ... }
}
```

---

## 三、应用层多语言设计

### 3.1 应用设计者可配置多语言

#### 表单多语言支持

```typescript
// 表单字段定义
interface FormField {
  id: string;
  name: string;
  
  // 多语言显示名称
  labels: {
    'zh-CN': string;
    'en-US': string;
  };
  
  // 多语言占位符
  placeholders?: {
    'zh-CN': string;
    'en-US': string;
  };
  
  // 多语言帮助文本
  helpTexts?: {
    'zh-CN': string;
    'en-US': string;
  };
  
  // 多语言验证错误提示
  validationMessages?: {
    'zh-CN': Record<string, string>;
    'en-US': Record<string, string>;
  };
  
  // 枚举值多语言
  options?: Array<{
    value: string;
    labels: { 'zh-CN': string; 'en-US': string };
  }>;
}
```

#### 表单设计器 UI 示例

```
┌─────────────────────────────────────┐
│ 表单设计器 - 字段属性               │
├─────────────────────────────────────┤
│ 字段名: [orderNo]                   │
│                                     │
│ 显示名称:                           │
│ ├─ 中文:  [订单编号]               │
│ └─ 英文:  [Order Number]           │
│                                     │
│ 占位符:                             │
│ ├─ 中文:  [请输入订单编号]         │
│ └─ 英文:  [Enter order number]     │
│                                     │
│ 帮助文本:                           │
│ ├─ 中文:  [系统自动生成的编号]     │
│ └─ 英文:  [Auto-generated by system]
│                                     │
│ 验证错误提示:                       │
│ ├─ 必填错误:                       │
│ │  ├─ 中文:  [订单编号为必填项]   │
│ │  └─ 英文:  [Order Number is required]
│ └─ 格式错误:                       │
│    ├─ 中文:  [格式不正确]         │
│    └─ 英文:  [Invalid format]     │
│                                     │
│ 枚举值选项 (状态):                  │
│ ├─ 值: draft                       │
│ │  ├─ 中文:  [草稿]               │
│ │  └─ 英文:  [Draft]              │
│ ├─ 值: confirmed                   │
│ │  ├─ 中文:  [已确认]             │
│ │  └─ 英文:  [Confirmed]          │
│ └─ 值: shipped                     │
│    ├─ 中文:  [已发货]             │
│    └─ 英文:  [Shipped]            │
│                                     │
│ [保存] [取消]                       │
└─────────────────────────────────────┘
```

### 3.2 数据模型多语言字段

```typescript
// 数据模型支持多语言字段类型
interface DataField {
  id: string;
  name: string;
  type: 'string' | 'integer' | 'multilingualString' | ...;
  
  // 多语言字段配置
  multilingualConfig?: {
    supportedLanguages: string[]; // ['zh-CN', 'en-US']
    fallbackLanguage: 'zh-CN';
  };
}

// 存储结构示例
// {
//   productId: 123,
//   productName: {
//     'zh-CN': '订单管理系统',
//     'en-US': 'Order Management System'
//   },
//   description: {
//     'zh-CN': '用于管理客户订单的完整系统',
//     'en-US': 'A complete system for managing customer orders'
//   }
// }
```

---

## 四、数据库设计 (多语言存储)

### 4.1 Prisma Schema

```prisma
// 多语言字段类型
model Localization {
  id          String    @id @default(cuid())
  
  // 资源识别
  resourceType String  // 'form', 'email', 'message'
  resourceId  String
  
  // 翻译内容
  key         String   // 'email.subject', 'form.submitBtn'
  
  language    String   // 'zh-CN', 'en-US'
  value       String   @db.Text
  
  // 元数据
  createdAt   DateTime @default(now())
  updatedAt   DateTime @updatedAt
  
  @@unique([resourceType, resourceId, key, language])
  @@index([resourceType, language])
}

// 用户语言偏好
model UserLanguagePreference {
  id          String  @id @default(cuid())
  userId      String  @unique
  user        User    @relation(fields: [userId], references: [id])
  
  // 偏好语言
  preferredLanguage String @default("zh-CN")  // zh-CN, en-US
  
  // 其他偏好
  timezone    String?
  dateFormat  String?
  
  createdAt   DateTime @default(now())
  updatedAt   DateTime @updatedAt
}

// 应用多语言配置
model ApplicationLanguageConfig {
  id              String  @id @default(cuid())
  appId           String
  app             Application @relation(fields: [appId], references: [id])
  
  // 支持的语言
  supportedLanguages Json  // ["zh-CN", "en-US"]
  defaultLanguage    String @default("zh-CN")
  
  // 翻译资源
  translations    Json  // 存储整个应用的翻译
  
  createdAt       DateTime @default(now())
  updatedAt       DateTime @updatedAt
  
  @@unique([appId])
}
```

---

## 五、AI 能力支持多语言

### 5.1 AI 生成内容多语言化

```typescript
class AIMultilingualService {
  
  /**
   * AI 生成应用时，自动生成多语言内容
   */
  async generateApplicationMultilingually(
    appDescription: string,
    targetLanguages: string[] = ['zh-CN', 'en-US']
  ): Promise<Map<string, ApplicationDefinition>> {
    
    const result = new Map<string, ApplicationDefinition>();
    
    for (const language of targetLanguages) {
      // 调用 Claude API，指定生成语言
      const prompt = `
Based on this application description: "${appDescription}"

Generate a complete application definition in ${language === 'zh-CN' ? 'Simplified Chinese' : 'English'}.

Include:
1. Application name (in ${language})
2. Description (in ${language})
3. Form fields with labels (in ${language})
4. Workflow steps with descriptions (in ${language})
5. Report titles and descriptions (in ${language})
6. All UI text must be in ${language}

Output format: JSON
      `;
      
      const response = await claude.messages.create({
        model: "claude-3-5-sonnet-20241022",
        max_tokens: 2000,
        messages: [{ role: "user", content: prompt }]
      });
      
      const appDef = JSON.parse(response.content[0].text);
      result.set(language, appDef);
    }
    
    return result;
  }
  
  /**
   * AI 自动翻译表单字段
   */
  async translateFormFields(
    fields: FormField[],
    fromLanguage: string,
    toLanguage: string
  ): Promise<FormField[]> {
    
    const fieldsText = fields.map(f => ({
      name: f.name,
      label: f.labels[fromLanguage],
      placeholder: f.placeholders?.[fromLanguage],
      helpText: f.helpTexts?.[fromLanguage]
    }));
    
    const prompt = `
请将以下表单字段从${fromLanguage === 'zh-CN' ? '中文' : '英文'}翻译成${toLanguage === 'zh-CN' ? '中文' : '英文'}。

字段列表:
${JSON.stringify(fieldsText, null, 2)}

要求:
1. 保持字段名 (name) 不变
2. 翻译标签 (label)、占位符 (placeholder)、帮助文本 (helpText)
3. 保持专业术语的一致性
4. 返回 JSON 数组格式

输出格式:
[
  {
    "name": "...",
    "label": "...",
    "placeholder": "...",
    "helpText": "..."
  }
]
    `;
    
    const response = await claude.messages.create({
      model: "claude-3-5-sonnet-20241022",
      messages: [{ role: "user", content: prompt }]
    });
    
    const translations = JSON.parse(response.content[0].text);
    
    // 更新字段的翻译
    return fields.map((field, idx) => ({
      ...field,
      labels: {
        ...field.labels,
        [toLanguage]: translations[idx].label
      },
      placeholders: {
        ...field.placeholders,
        [toLanguage]: translations[idx].placeholder
      },
      helpTexts: {
        ...field.helpTexts,
        [toLanguage]: translations[idx].helpText
      }
    }));
  }
}
```

---

## 六、多语言测试策略

### 6.1 翻译质量检查

```typescript
// 自动化翻译检查
class I18nQualityCheck {
  
  /**
   * 检查翻译的完整性
   */
  validateTranslationCompleteness(lang: string): ValidationResult {
    const zhCNKeys = this.getAllTranslationKeys('zh-CN');
    const targetKeys = this.getAllTranslationKeys(lang);
    
    const missingKeys = zhCNKeys.filter(k => !targetKeys.includes(k));
    
    return {
      isComplete: missingKeys.length === 0,
      missingKeys,
      coverage: ((zhCNKeys.length - missingKeys.length) / zhCNKeys.length) * 100
    };
  }
  
  /**
   * 检查翻译的一致性
   */
  validateTranslationConsistency(lang: string): ConsistencyResult {
    // 检查相同含义的词是否始终使用相同的翻译
    const terms = this.extractTerms(lang);
    const inconsistencies: Array<{ term: string; variations: string[] }> = [];
    
    // 分析重复使用的词汇
    // ... 实现细节
    
    return { isConsistent: inconsistencies.length === 0, inconsistencies };
  }
  
  /**
   * 检查数字和日期格式
   */
  validateFormats(lang: string): FormatValidationResult {
    // 验证数字格式、日期格式、货币格式等
    // 中文: 1,000.00 vs 1000.00
    // 日期: YYYY-MM-DD vs MM/DD/YYYY
    // ...
  }
}
```

---

## 七、多语言部署配置

### 7.1 环境变量

```bash
# .env.local

# 默认语言
DEFAULT_LANGUAGE=zh-CN

# 支持的语言（逗号分隔）
SUPPORTED_LANGUAGES=zh-CN,en-US

# i18n 文件路径
I18N_PATH=./public/locales

# 翻译动态加载
I18N_DYNAMIC_LOAD=false

# AI 多语言生成
AI_MULTILINGUAL_GENERATION=true
```

### 7.2 Docker 部署

```dockerfile
# 多语言资源打包
FROM node:18-alpine AS builder

WORKDIR /app
COPY . .

# 安装依赖
RUN npm install

# 构建应用
RUN npm run build

# 验证翻译完整性
RUN npm run i18n:validate

# 最终镜像
FROM node:18-alpine

WORKDIR /app

# 复制多语言资源
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/public/locales ./public/locales

EXPOSE 3000
CMD ["npm", "start"]
```

---

## 八、多语言文档

### 8.1 API 文档多语言版本

```
/api/docs/zh-CN    → 中文 API 文档
/api/docs/en-US    → 英文 API 文档

使用 Accept-Language header 自动重定向
```

### 8.2 用户手册多语言版本

```
/docs/zh-CN/manual.pdf       → 中文用户手册
/docs/en-US/manual.pdf       → 英文用户手册

/docs/zh-CN/tutorial/        → 中文教程
/docs/en-US/tutorial/        → 英文教程
```

---

## 九、多语言推出计划

### 阶段 1: MVP (11 个模块 - 中英双语)

```
Week 1-2:
├─ 确定中英文术语表（系统 UI）
├─ 编写所有 JSON 翻译文件
└─ 实现 i18n 中间件 & React hook

Week 3-6:
├─ 所有前端组件集成 i18n
├─ 后端 API 返回翻译文案
└─ 多语言单元测试

Week 7-9:
├─ 集成测试（切换语言验证所有模块）
├─ 语言切换 UI 完善
└─ 文档翻译
```

### 阶段 2: 后续版本 (Q2+)

```
繁体中文 (zh-TW)
日本語 (ja-JP)
한국어 (ko-KR)
Español (es-ES)
Français (fr-FR)
Deutsch (de-DE)
...
```

---

## 十、核对清单

### MVP 多语言交付清单

```
前端:
☐ i18n 配置完成 (i18next)
☐ 所有 UI 文案提取到翻译文件
☐ zh-CN 和 en-US 翻译 100% 完成
☐ 语言切换器组件实现
☐ localStorage 保存语言偏好
☐ 多语言测试通过 (中英文切换)

后端:
☐ 语言检测中间件实现
☐ 所有错误提示、验证信息翻译
☐ API 返回正确的语言文案
☐ 用户语言偏好保存
☐ 多语言单元测试 >80% 覆盖

应用层:
☐ 表单多语言字段定义实现
☐ 数据模型多语言字段支持
☐ 应用设计者可配置多语言标签
☐ 表单运行时显示正确的语言

文档:
☐ API 文档中英文版本
☐ 用户手册中英文版本
☐ 多语言术语表
☐ i18n 集成指南

测试:
☐ 多语言 E2E 测试
☐ 翻译完整性检查 100%
☐ 翻译一致性检查
☐ 日期/数字格式正确
```

---

## 总结

**多语言设计的核心价值：**

```
✅ 国际市场覆盖 (中文 + 英文)
✅ 用户体验本地化 (母语使用)
✅ 应用内容多国言 (用户可创建多语言应用)
✅ AI 自动翻译能力 (降低手动翻译成本)
✅ 易于扩展 (后续增加新语言成本低)
```

**工作量估算：**
- 前端: 20-25 人天
- 后端: 15-20 人天
- 测试: 10-15 人天
- 文档: 10 人天
- 总计: ~60-70 人天 (1-1.5 周)

**建议：纳入 MVP 交付范围（Week 10-11 完成）**

