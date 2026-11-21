# S1 B7：Linux 宿主权限隔离——可信 Domain Kernel 与原生插件/CLI 分离

> **研究约束**：B5-28、B6-32 已证明有 SQLite 文件权限的宿主进程可物理绕过 B5 Tool Broker。B7 进一步研究**实际不同 Linux OS UID**的限制：权威 B2/B4 数据库由非 root 内核独占，原生 Plugin/CLI 不能直接打开它，只能经 B5 类型化工具管理。**这是对非特权 OS 用户隔离的检验，绝不等于阻止 root 或共享内核 UID 的进程。**

## 假设、可证伪条件

- **H7.1**：B2/B4 SQLite 实际存储于专用 Linux 内核用户持有的 mode-0700 私有目录，DB 与凭据文件 mode-0600；不同的普通 Plugin 和 Agent OS 用户无法经 `os.open(O_RDONLY/O_RDWR)`、`sqlite3.connect(mode=ro/rw)`、原生 `UPDATE`、`/proc/<kernelPid>/environ` 或读取私有配置来获取不受授权的数据/持久化写入。若任一探针真正成功，本假设失败。
- **H7.2**：Linux UID 隔离后，B2/B4 可信内核仍然能够通过 localhost B5 v3 Tool Broker 接收并验证指定 Agent/Plugin 请求；Plugin 仅可写 View，不能改 Model/调用未注册 SQL 工具、无法跨 app、不能使用原始 B2 v2 Bearer 接口。命令成功会留下 Receipt/角色 Audit；旧版写冲突 409，真人 Chromium 浏览器编辑和发布仍可运行。
- **H7.3**：权限边界不损坏低代码功能，发布 Manifest 可实际执行合同 Form/View/两级 Workflow。**不调用 DeepSeek**、不需要假造任何 AI 自动生成结果。
- **H7.4（重要反例）**：真正 `root` 或其他可以通过 `runuser` 切换为内核 UID 的宿主管理员，仍然可以直接 SQLite UPDATE；共享内核 UID 的任何被攻陷进程也一样。对此必须**保留物理成功的负对照**，而不是用 HTTP 409 假装阻止了这类物理写入。

## 实际 OS 架构

~~~text
Linux UID: ailcapb7kern（独立非 root 用户）
   /tmp/.../private/ (owner kernel, mode 0700)
      authority.sqlite (owner kernel, mode 0600)
      service-config.json (owner kernel, mode 0600)
   Python kernel_service.py（专用独立进程）
      B2 SchemaStore + B4 ExtensionRegistry 内核
      B5 Typed ToolBroker（内核进程内）
      Loopback: HTTP 127.0.0.1:<ephemeral port>
             ▲                          ▲
             │                          │
  Linux UID: ailcapb7agen     Linux UID: ailcapb7plug
  仅限定 Agent bearer        仅限定 Plugin bearer
  严禁直接访问 private      严禁直接访问 private
  native_client.py          native_client.py
      ▲                          ▲
      └── 两者均只能调用 v3 受治理的工具 API ──┘
             
  人工真实 Chromium 浏览器：B2 同源 Session/CSRF
  实体 SQLite 独立 Oracle：以受信 kernel UID **只读进程**运行
~~~

**安全边界重点**：配置中的 Agent/Plugin/Runtime 随机授权凭据以 mode-0600 仅存储在内核私有目录，由受信实验编排器通过 **stdin** 单次输入给获准的 native_client 进程，**不放进命令行参数、调试日志、公开 ready.json 或环境变量**。普通插件实际使用其有限 Token，但拿不到内核管理员密码与其他工具权限。服务在启动后只监听 `127.0.0.1`；该 API 并非防御任意本机攻击的网络安全边界，生产需进一步接入 Unix Socket ACL/mTLS、服务授权与端到端审计。

工作流在 GitHub Ubuntu 24.04 上通过 `sudo useradd` 创建三名不同非 root 研究用户，由专门 OS 用户执行服务/真实 SQLite 直接访问探针；标准 Python 测试编排器模拟受信高权限管理员，是**隔离环境中仍然具备 sudo 的控制平面**，不是普通业务插件。

## 测试构件

| 文件 | 功能 |
|---|---|
| `kernel_service.py` | 真实独立 Linux OS 内核进程，读取 0600 启动凭据、建 B2/B4 权威 SQLite，B5 v3 Broker，服务只监听 loopback；内核无 Docker Build 权限 |
| `direct_probe.py` | 实际另一个 UID 的进程执行数据库文件 O_RDONLY/O_RDWR、SQLite URI `mode=ro/rw` 以及真正 `UPDATE apps SET revision=revision`、读取内核配置、`/proc` 跨 UID 内存信息 |
| `native_client.py` | 真实另外一个 Linux UID 的 v3 插件/Agent 进程，通过 stdin 接受单次凭据并调用受限 HTTP 工具 |
| `physical_sql_oracle.py` | 仅按内核 UID 运行的独立只读 SQLite 查询、Manifest/资源/发布版哈希复核，**不依赖 SchemaStore 审计自评** |
| `test_os_policy.py` | 权限配置、缺漏凭据拒绝、native SQLite 的真阳性与不存在 DB 的真阴性等单测 |
| `experiment.py` | 多 UID 管理、真实启动内核、浏览器交错 CAS、发布/运行、最终 root 物理绕过与漂移检出 |
| `.github/workflows/s1-b7-os-dac-kernel.yml` | 零模型的 GitHub CI 实测 `sudo/useradd/runuser`、Python 3.13、Chromium、独立 SQLite Oracle |

## 运行前提与操作

**仅限一次性研究 VM 或 GitHub CI runner，绝不可对生产宿主使用此脚本。** 需有 sudo useradd 权限、Python 3.13、Playwright 1.56/Chromium。最简单的复现方式是直接运行 GitHub CI 工作流；本地手动运行前须自行创建与隔离环境一一对应的 `ailcapb7kern` / `ailcapb7plug` / `ailcapb7agen` 系统用户。

~~~bash
cd experiments/g1-b01-b7
python3 -m unittest -v test_os_policy
# 隔离 CI 里已建好用户、已安装 Playwright Chromium：
python3 experiment.py --output /tmp/s1-b7-evidence.json
~~~

输出结构化证据包含每条检查的机器可读状态和独立 OS/DB 观察；不存储随机 Token、登录密码或任何敏感密钥。

## 研究限制

1. 本轮保护的是**已分离 Linux UID 且无 sudo / 无 kernel UID 同组目录访问权限**的普通插件、Agent 和“原生 SQLite CLI”模拟程序。它不是实际 Saltcorn Native CLI 或任一真实商业插件安装、加载机制的接入。真实产品中的 `Field.update`、`Pack`、SQL 后门和旧部署权限必须单独审计，不能靠换进程名视作消除。
2. 启动期间使用可信编排器生成凭据并分发短期 Agent/Plugin Token；它作为受信宿主管理员自身依然能够 `sudo` 切换 UID 并访问权威 SQLite。正式内核仍需校验服务签名、最小化 root 权限、轮换密钥、防御泄露的长效 Token，并隔离安装升级器/构建器。
3. 本轮专为 B7 的 OS DAC，故可信 Kernel 不执行 Docker Code Build；已验证的 B4 功能保持原有实验结果，不将其再次冒充在此隔离测试内成功。完整生产架构需要把构建交给与 Kernel 相互隔离的签名 Build Worker，并在 Kernel 验证不可伪造构建回执。
4. root / 同 UID 的宿主进程可物理修改 SQLite；B2 对意外资源哈希漂移会拒绝草稿并隔离，仍不能防止拥有特权的恶意进程**同时修改内容和哈希或者发布指针**。
5. 当前 SQLite 单文件满足实验的原子性，却不覆盖多个数据库、跨服务发布事务、长期运维/灾备、真实外部工作流副作用和成熟开源低代码平台 Native CLI 特权入口。

**B7 通过也只说明有限的 OS UID 边界假设得到实验证据**。正式冻结 G1-B01 W01—W24、TC01—TC18 未自动转成 FULL PASS；S1 IN_PROGRESS，G1 NOT_PASSED，正式 G1-B01 OPEN。
