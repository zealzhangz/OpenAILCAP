# ADR-0001：AppSpec 作为唯一应用中间表示

- 状态：Accepted（AppSpec 1.0.0 结构契约）；运行时/编译器实现仍为 In Progress
- 日期：2026-11-28
- 关联评审问题：A-01（缺少统一、版本化 AppSpec/IR）
- 关联交付基线：`doc/整改/2026-11-28_L3全量交付实施基线.md`

## 背景

应用管理、数据建模、表单、逻辑编排、BPM、权限、Agent、编译器和运行时必须共享一致的应用语义。若各设计器分别保存独立对象，跨模块引用、生成物一致性、版本迁移、差异比较和回滚无法形成可验证闭环。

## 决策

1. AppSpec 是应用定义的唯一规范化事实源（Single Source of Truth）。
2. AppSpec 使用显式 `schemaVersion`，当前已定义版本为 `1.0.0` 与 `1.1.0`（1.1.0 增加版本化字典引用）；JSON Schema 文件是结构契约的机器可读定义。
3. AppSpec 顶层至少包含 `meta`、`dataModels`、`relations`、`ui`、`forms`、`logic`、`workflows`、`security`、`i18n`、`deployment`，并为 `reports`、`integrations`、`extensions` 等扩展域保留显式位置。
4. 所有实体、表单、页面、关系、流程和节点使用稳定 ID；跨对象引用必须在保存、导入、编译和发布前校验。
5. 设计器与 Agent 只能通过有版本的 AppSpec 命令/补丁修改规格；AI 生成先形成候选差异，必须校验并由用户确认后写入。
6. SQL、Prisma、页面代码、流程定义、权限策略和部署制品均是 AppSpec 的派生物，必须记录源 AppSpec 版本、编译器版本、插件/依赖锁和构建摘要。
7. 变更必须具备 diff、迁移、冲突检测、审计和回滚语义；不得直接在派生物上做不可追踪的配置漂移。

## 不在本 ADR 中宣称已完成的能力

- 现有浏览器原型的 localStorage 仍是演示存储，不是多用户生产存储。
- 当前 `app-spec.js` 是轻量运行时结构/引用校验器，不等同于完整 JSON Schema 2020-12 验证器。
- 尚未完成服务端 AppSpec API、数据库版本化存储、迁移执行器、编译器、制品签名和生产运行时。
- 当前生成逻辑仅为本地规则模板，不是 LLM/Agent 生成服务。

## 结构契约

- Schema：`doc/architecture/schemas/app-spec-1.0.0.schema.json`
- 浏览器原型校验器：`openailcap-prototype/public/js/app-spec.js`
- 显式迁移预览：`openailcap-prototype/public/js/app-spec-migrations.js`
- 原型测试：`openailcap-prototype/test/prototype-static.test.js`

## 验收标准

1. JSON Schema 结构校验通过；非法版本、缺失必需域、类型错误被拒绝。
2. 所有 ID 唯一；关系的源/目标实体和字段均存在。
3. 页面引用的表单存在；表单字段引用的数据模型字段存在。
4. Logic/BPM 所有边的起点和终点节点均存在。
5. 同一 AppSpec 在相同编译器与依赖锁下可重复生成一致的规范化输出。
6. v1.0.0 → 后续版本迁移具备向前/回滚策略、迁移测试和审计证据。
7. AI 修改通过 JSON Patch/领域命令表达，支持预览、人工批准、执行和撤销。

## 后续工作

- G1：补齐 AppSpec API、命令模型、版本/迁移策略和领域约束。
- G2：实现 TypeScript/Prisma/DDL/BPMN/权限策略生成器，并用真实 PostgreSQL、Prisma CLI 和 BPMN 引擎验证。
- G3：以服务端 AppSpec 作为唯一持久化源，替换生产场景下的 localStorage。


## AppSpec 1.1.0 向后兼容补充（2026-11-28）

- 1.0.0 Schema 保持不可变，字典规范通过 1.1.0 新 Schema 增量引入。
- 1.1.0 将字典作为规范 IR 的一等对象；表单字段以 dictionaryId + version 精确引用，避免只依赖可变 code。
- 浏览器校验器兼容 1.0.0 与 1.1.0；生产服务端必须按 schemaVersion 选择对应完整 JSON Schema，并执行引用、租户、权限与并发校验。
- 本地原型字典 version=1 仅是演示映射，不构成不可变版本仓库或发布能力。
- `openailcap-prototype/public/js/app-spec-migrations.js` 提供 1.0.0→1.1.0 的非破坏性迁移预览：只返回副本和差异，不写入 Store；字典必须由调用方显式提供并按 code 唯一匹配。未知/重复引用、外部字典源和模型字段引用错误均失败关闭。预览通过不等于用户批准或已持久化；生产迁移仍需服务端事务、审计、完整 Schema 校验和版本策略。
