# S1 正向研究：基于真实 Saltcorn SQLite 的共享版本化 HTTP 编辑契约

本目录是 **实验适配器，不是生产服务、Saltcorn 官方插件或 OpenAILCAP MVP**。之前已在真实 Saltcorn 浏览器编辑器中复现旧表单覆盖问题。本实验要验证：如果人工和模拟 Agent **都使用同一个治理 HTTP 写入接口**，是否可以保留非冲突修改、拒绝过时版本、回滚失败事务，以及记录审计。

## 文件

- [gateway.py](gateway.py)：Python 标准库 ThreadingHTTPServer，绑定 127.0.0.1:3200，直接连接测试用 Saltcorn SQLite 的 _sc_fields 字段标签。真正 BEGIN IMMEDIATE 事务同时更新字段、研究修订表、幂等回执与审计事件。人工使用网关自带 HTML 登录/表单 + Cookie/CSRF；自动化使用独立随机 Bearer Token。
- [acceptance.py](acceptance.py)：Playwright Chromium 网页保存、独立 Agent HTTP 请求、冲突与并发、错误注入、源数据库物理读回。
- [native-out-of-band.js](native-out-of-band.js)：故意调用 Saltcorn 原生 Field.update 绕过研究网关；网关必须发现内容指纹漂移并拒绝继续写入。
- [GitHub Actions Workflow](../../../.github/workflows/s1-governed-gateway.yml)：Ubuntu 24.04、Saltcorn CLI 1.7.0-beta.5、Playwright 1.56.0，独立全新数据库和运行时随机凭据。

## 冻结的 26 项验收

主流程 G01—G22：健康检查、未认证拒绝、只读授权、跨应用拒绝、非法标签、匿名浏览器登录跳转、真实 Chromium 登录、两个旧标签页 B 先保存后 A 获得 HTTP 409、CSRF、Agent 读到最新人工版本、旧 Agent 409、不同资源增量修改保留、幂等重试、同键不同内容拒绝、独立 HTTP 并发同资源一胜一拒、物理数据库版本只增一次、故障注入真正 SQL 回滚、审计 human/agent/拒绝信息。

负对照 D01—D04：Saltcorn 原生 Field.update 故意绕过网关后，物理标签变动但版本账本没有变；网关 GET 与 Agent POST 必须返回 409 OUT_OF_BAND_DRIFT，资源版本、幂等成功回执不能被错误推进。最后重新启动真实 Saltcorn 运行时，检查合同 REST 与 HTML 页面仍然可用。

## 严格限制

**实验浏览器是我们自己创建的网关页面，不是 Saltcorn 原生 /field/:id 设计器。** 网关控制下的人工/模拟 Agent 可以共享版本账本，但 Saltcorn 自带的网页编辑、CLI 和插件依然可能绕过它。本轮尝试“检测绕过后失败关闭”，并未改造所有写入口；不得将其称为生产级统一写入闭环完成。

此适配器直接 UPDATE 内部 _sc_fields，绕过 Saltcorn Field.update 的缓存刷新、插件事件和其他副作用；只在一次性实验数据库使用。真实 Saltcorn 重启后读回的 REST/HTML 也不能证明热更新和全量业务逻辑一致。

身份机制仅用于 localhost 的测试账号与随机 Token，没有 HTTPS、组织权限、持久会话安全和 Agent 授权委托。Agent 是确定性 HTTP 客户端，不是真正大模型。金额审批与其他完整合同验收项仍未实现；冻结合同 TC01—TC18 继续 NOT_RUN，G1 仍需复审。

参考：[真实浏览器覆盖负例](../../../docs/01-research/19-real-browser-edit-evidence.md)、[真实 SQL 事务与并发研究](../../../docs/01-research/18-saltcorn-sqlite-atomic-evidence.md)。
