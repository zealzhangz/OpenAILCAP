# S1 深度源码追踪：ToolJet MCP 的人机编辑同步

观察日期：2026-11-21。固定源码：[ToolJet/tooljet-mcp @ 8a178ad3](https://github.com/ToolJet/tooljet-mcp/tree/8a178ad34f6e3326b6957503ca4ed4f555d23096)。

**证据等级 S1：真实源码静态阅读。尚未运行 ToolJet 平台和测试套件。**

## 1. 实际追踪范围

这条调用链位于 ToolJet MCP 的 Code mode 源码文件编辑接口。不能据此宣称 ToolJet 的所有页面元数据、数据库和工作流也采用同样机制。

主文件：[src/tools/codeApp.ts](https://github.com/ToolJet/tooljet-mcp/blob/8a178ad34f6e3326b6957503ca4ed4f555d23096/src/tools/codeApp.ts)；证据测试：[tests/codeAppSync.test.ts](https://github.com/ToolJet/tooljet-mcp/blob/8a178ad34f6e3326b6957503ca4ed4f555d23096/tests/codeAppSync.test.ts)。

## 2. 调用链（固定 commit 和源码行）

| 环节 | 代码入口 | 通过阅读源码确认的行为 |
|---|---|---|
| 编辑器同步 | [syncEditorEdits，约 713 行](https://github.com/ToolJet/tooljet-mcp/blob/8a178ad34f6e3326b6957503ca4ed4f555d23096/src/tools/codeApp.ts#L713-L763) | 执行 CLI 的 app source-pull，处理变更、不可覆盖文件和权限拒绝 |
| Agent 读取 | [codeAppReadFilesTool，约 1006—1030 行](https://github.com/ToolJet/tooljet-mcp/blob/8a178ad34f6e3326b6957503ca4ed4f555d23096/src/tools/codeApp.ts#L1006-L1030) | 先刷新已有编辑，再读取文件，按文件计算哈希写入 readHashes |
| Agent 提交 | [codeAppWriteFilesTool，约 1041—1114 行](https://github.com/ToolJet/tooljet-mcp/blob/8a178ad34f6e3326b6957503ca4ed4f555d23096/src/tools/codeApp.ts#L1041-L1114) | 写入前同步后再次比对文件哈希；未读或被改的文件拒绝；文本 find 要恰好匹配一次 |
| 实际文件写入 | [约 1115—1134 行](https://github.com/ToolJet/tooljet-mcp/blob/8a178ad34f6e3326b6957503ca4ed4f555d23096/src/tools/codeApp.ts#L1115-L1134) | 校验没有拒绝项后才写文件，更新哈希并进行类型检查 |
| 代码安装接口 | [codeAppInstallTool，约 1401 行](https://github.com/ToolJet/tooljet-mcp/blob/8a178ad34f6e3326b6957503ca4ed4f555d23096/src/tools/codeApp.ts#L1401-L1427) | 描述 build/check 后经 ToolJet CLI 安装代码；服务端实现尚未验证 |
| 反例/回归 | [codeAppSync.test.ts](https://github.com/ToolJet/tooljet-mcp/blob/8a178ad34f6e3326b6957503ca4ed4f555d23096/tests/codeAppSync.test.ts) | 构造人工改样式、Agent 用旧文件继续修改，以及版本号相同但内容不同等情况 |

## 3. 数据流

~~~mermaid
flowchart TD
    A[人工在 Code Panel 修改] --> B[平台存储代码]
    C[Agent read_files] --> D[同步 source-pull]
    B --> D
    D --> E[读取内容并记住文件哈希]
    E --> F[Agent 构造局部修改]
    F --> G[Agent write_files]
    G --> H[再同步并校验哈希]
    H --> I{修改后文件与读时一致?}
    I -- 否 --> J[拒绝旧写入，要求重新读取]
    I -- 是 --> K[校验增量修改定位准确]
    K --> L[写入并记录新哈希]
    L --> M[后续构建/安装检查]
~~~

## 4. 有根据的结论

**事实**：Code mode 入口实施先读/刷新、增量修改、写前检查和拒绝旧写入的防护；其测试显式覆盖人工/Agent 多轮修改。

**不能推断**：所有代码文件集合具备数据库事务原子性；所有低代码资源遵循同一模型；生产实例已通过真实测试；文件不覆盖就等于跨资源业务行为正确；实际版本权限和回滚完全可靠。

## 5. 转化为 OpenAILCAP 的实验要求

1. AI、人工使用同一受治理写入契约；不应让 AI 直写平台核心表。
2. 提交 Patch 时带资源稳定 ID、可信基线、权限、预期影响、幂等键。
3. 同 revision 不同内容必须明确检测并采纳/拒绝；不能只叫 Agent 再读一次。
4. 对事件、流程和代码的跨对象引用做业务级校验。
5. 将“静态检查通过”“编辑器读回正确”“真实运行成功”“部署回滚成功”作为不同验收证据。

**下一步证据缺口**：需要继续追踪 ToolJet CLI 的 source-pull 和平台服务端持久化、真实用户授权和版本机制，并在真实平台上重演人工样式/Agent 变更。这是 G1 未通过的原因之一。
