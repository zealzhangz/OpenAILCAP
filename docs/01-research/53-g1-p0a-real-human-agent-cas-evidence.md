# G1 P0-A 第二轮：真实人工 Web 与 Agent / Plugin 的同实例冲突验证（预注册）

状态：**提交时未验证**；以本 PR CI 和原始物理 Oracle 作为唯一运行结果，不因完成代码自动升级冻结验收。

## 问题与实验位置

沿用上一轮已经合并的 B9/P0-A **同一个非 root B2 Domain Kernel、authority.sqlite、B5 Tool Broker、第三 UID Plugin、Saltcorn Native 真实派生库**。既有 B9 36 项 + P0A-01—06 6 项完全保留。本轮不增加新 Kernel 或另一份演示应用，而在 B9 真实 Chrome Session 及已发布 v1/回滚之后继续运行九个附加检查。

新增 `experiments/g1-b01-b9/p0a_browser_suite.py`，由 `experiment.py` 在第 42 项之后调用。扩展后预期共 51 项真实检查；仍有 25 + 18 + 40 个既有单测/回归。不读取 `DEEPSEEK_KEY`。

| ID | 同实例真实操作 | 独立成功判据 | 对应冻结用例（仅局部） |
|---|---|---|---|
| P0A-07 | 两个登录后的实际 Chromium 设计器标签页基于相同 View revision；B 保存，A 旧草稿再保存 | 实际 POST 200/409；SQL 仅一笔版本+回执+审计；保留 B title | W02 |
| P0A-08 | 人工 Web 修改 title 后，Agent 以旧 snapshot 提交同字段 | Agent 409，物理 SQL 留存 Web title | W03 |
| P0A-09 | Agent 先改同字段，人工 Web 持旧页 POST | Web 409，物理 SQL 留存 Agent title | W04 |
| P0A-10 | 人工修改 View title，Agent 持旧版本修改 View columns；明确重读后人工审阅合并 | 旧 Agent 409，重读+不同字段合并成功，物理保留 title 和 columns | W05 |
| P0A-11 | 不调用任何大模型，只用 Chrome 人工编辑页面 | 成功 200，独立 SQL revision、receipt 真实改变 | W22 |
| P0A-12 | 另一写入者完成更高 revision 后 Agent 同 changeId 原请求重放；换 Actor 或摘要冒用 | 原回执重放 200/replayed，跨 Actor 和摘要篡改各 409，物理无任何新增事务 | W08, W09 |
| P0A-13 | 有真实登录 Cookie 的 Chromium fetch 缺 CSRF 或错误 CSRF | JSON 403，非 HTML 假成功，物理无副作用 | W15 |
| P0A-14 | 插件工具输入伪造 actorId/role/appId | ToolBroker 422，物理无副作用 | W13 |
| P0A-15 | 独立 SQL 全量账本审计 + **无重启** Native Chrome 只读已发布 v1 | 上述步骤恰好 6 个成功写入，6 个审计与成功回执；Kernel 最新 draft 与未变已发布 v1 的 Native View 隔离，app-b 无变化 | W11, W17（仅读写隔离局部） |

## 不得偷换的结论

1. 这里的“人工设计器”是 B2 **自研最小 JSON 编辑器**，不是 Saltcorn 原生拖拽设计器；真实 Saltcorn Native `/field`、CLI、Pack 的副本污染/重建已由同一 B9 既有步骤覆盖，但**尚未实现 Native 原生编辑至权威 Kernel 的自动协调**。不能把 409 说成原生 Saltcorn 409。
2. P0A-15 检查 Native 浏览器不泄露**未经发布**的草稿，但不是“发布后 Native 无重启热更新”；后者仍需权威签名、原子切换及 B15/B17 读前 Guard。未实现时不能算 W17 FULL PASS。
3. 当前 Agent HTTP 执行由受信 CI Controller 发起，Plugin 为独立 Linux UID，均非生产 SSO；三写入者认证/Token 撤销/Root 和同 UID 越权仍有未覆盖路径。W15 只新增 CSRF 部分，Token 过期/撤销未验证。
4. 两个原生浏览器版本共享研究 Session；无生产组织角色、分布式锁、跨机网络隔离或 Plugin 安装器。不会在这轮伪称插件 W16 / TC14 FULL PASS。
5. 原冻结 **W01—W24、TC01—TC18 均维持 NOT_RUN (0/42 FULL PASS)**；G1 **NOT_PASSED**。实际新增证据成立后才可追加 `g1-convergence-ledger.json` 的 `partial_evidence` 链接。

## 验证及退出条件

GitHub Actions `.github/workflows/s1-b9-authority-projection.yml`，Ubuntu 24.04 / Python 3.13 / Node 24 / `@saltcorn/cli@1.7.0-beta.5` / Chromium Playwright 1.56，保存 JSON 与真实日志。

出现任意丢失人工写入、未经授权修改、数据库审计不一致、两旧版本写入均成功、生产数据越界、以及 Native 派生草稿混入正式发布页面，应保留失败日志并保持 No-Go。验证后只在**可重现同实例执行**和独立审计范围内确认局部证据。

下一步仍应优先真正“授权命令改变后，重新验证来源并原子投影到运行时/浏览器无重启展示”、真实插件沙箱、Pack 全量 diff 审批，再进入 P0-B 全链签名发布，不得另起相互独立的演示工程。
