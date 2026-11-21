# S1 / G1-B01 / C2：真实 Saltcorn 原生字段编辑器受限改造实验

> **研究实验，不是 Saltcorn 官方支持的扩展、生产补丁或 OpenAILCAP 的完整统一写入实现。** 此工程会在一次性 GitHub Actions Runner 上直接修改已安装 npm 包的 `routes/fields.js`。绝不可对生产环境运行 `patch_native.py`。

## 核心问题

真实 Saltcorn 1.7.0-beta.5 的 `/field/:id` 可视设计器，两个标签页保持旧字段上下文时，后保存的旧表单可以静默覆盖先前修改（[原始负例 19](../../docs/01-research/19-real-browser-edit-evidence.md)）。本实验验证：给**原生 Web 字段向导**加入带 HMAC 的旧基线校验，是否可以在一个**顺序过时提交**场景下阻止覆盖？同时检查 Saltcorn 原生 CLI 是否依旧绕过网页校验。

## 代码说明

- [inspect_route.py](inspect_route.py)：只读定位安装的 Saltcorn `routes/fields.js`，报告 `fieldFlow`、`Field.update` 和 GET 初始化调用链的真实字节级位置。
- [patch_native.py](patch_native.py)：在一次性 npm 安装的编译输出中插入研究用代码，给原生 GET `/field/:id` 工作流上下文加入签名的原始标签，在 `fieldFlow.onDone` 调用 `Field.update` 前检查当前标签；若旧基线失效，POST `/field` 返回 HTTP 409。**这不是原子 CAS**：比较和实际写入仍可发生 TOCTOU 竞争。
- [native_browser.py](native_browser.py)：真正 Playwright Chromium、真实 Saltcorn 临时管理员、原生向导多步 POST、旧标签页 409 和新标签页继续修改，使用物理 SQLite 验收。
- [verify_bypass.py](verify_bypass.py)：复用已有 [native-out-of-band.js](../platform-saltcorn/governed/native-out-of-band.js) 在真实 Saltcorn CLI 中直接调用 `Field.update`，证明 Web 路由的保护没有覆盖 CLI。
- [工作流](../../.github/workflows/s1-g1-b01-c2.yml)：Ubuntu 24.04、Node 24、Python 3.13、Saltcorn CLI 1.7.0-beta.5、Playwright 1.56 Chromium、全新 SQLite 和随机密码；**没有任何 DeepSeek 或其他付费推理**。

## 真实运行记录

- 上游研究固定 SHA：`saltcorn/saltcorn@515254bee5a98df70530cc59846b1df02d5db350`；测试包版本 `@saltcorn/cli@1.7.0-beta.5`，**不能推论二者构建字节完全一致**。
- [成功 CI Run #44887680474](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44887680474) — completed / success，Job 136796430685，Artifact [#14699859357](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44887680474/artifacts/14699859357)。
- 原生浏览器 C2-01—C2-08 **8/8 符合预注册预期**：B 保存 `Browser B Protected`；A 持旧表单在第三个 POST 收到 HTTP **409**；物理 SQLite 仍是 B 的值；重新打开看到 B；全新表单正常改为 `Browser C Fresh Edit`。
- C2-09 **1/1 负对照成立**：原生 Saltcorn CLI 仍可绕开被改造的 Web 路由，数据库最终记录 `Native Outside Gateway`。这是系统级风险**仍存在**的证据，不是“插件/CLI 安全”通过。
- 首次完整 CI [#44887534989](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44887534989) 因实验脚本取名 `inspect.py`，覆盖 Python 标准库 `inspect`，使 Playwright 导入失败。已更名为 `inspect_route.py` 后成功；错误与修复均可追溯。
- 早先源码路径定位 Probe [#44887303753](https://github.com/zealzhangz/OpenAILCAP/actions/runs/44887303753) 提供编译文件独立证据。

## 不可外推的安全性质

1. **非原子**：研究改造在 `Field.update` 前检查签名原始标签，无法证明两个并发请求同一旧 revision 只有一胜一拒；Saltcorn SQLite 的 `withTransaction` 在历史研究中不等于真实 SQL BEGIN/COMMIT。
2. **不是强制全渠道**：CLI、Pack、插件、数据库管理路径并未接入共享 CAS。单个 Web 字段/标签的签名不覆盖其他字段、依赖引用和应用发布。
3. **维护不可持续**：运行时改写第三方 npm 的已编译 JS 文件，不是稳定 API，版本升级和热部署时可失效；不得复制为生产集成方案。
4. **不是 AI 实测**：本轮仅真实 Chromium 和确定性脚本；没有真实 Agent 提案或真实 Plugin 生命周期，不增加原冻结 W01—W24 的完整通过计数。
5. **不等于 G1 通过**：明确仍有直连 CLI 越过安全治理的负例，因此 G1-B01 保持 OPEN。下一步优先验证由 OpenAILCAP 管理的最小人工设计器 + C1 受限命令入口，或对第三方平台进行真正统一模型层拦截，而不是进一步给现有网页补临时签名。

## 研究结论

本实验把风险从“猜测 Saltcorn 改造难”推进到“真实原生向导**可以**通过受限补丁在顺序旧表单场景下返回 409，但**不能**靠这层补丁管理所有写入者”。这支持将受治理命令入口设计为 OpenAILCAP 的平台内核职责，而不是让 Agent 独享 CAS sidecar。参见 [完整报告 33](../../docs/01-research/33-g1-b01-c2-native-route-evidence.md)。
