# Glowhaven Helix 服务器控制台平台

[English](README.md) | [简体中文](README_zh-CN.md)

<div align="center">

# **Glowhaven Helix**

### 面向基础设施的统一服务器控制台 (Control Plane)

**适用于服务器身份认证、实时遥测、有界远程运维、任务编排与防篡改审计日志的统一开源运维控制层。**

[![CI](https://github.com/GlowhavenIndustries/Glowhaven-Server-Platform/actions/workflows/ci.yml/badge.svg)](https://github.com/GlowhavenIndustries/Glowhaven-Server-Platform/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/Python-3.12%2B-111827?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-control%20plane-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-111827.svg)](LICENSE)
[![Security Policy](https://img.shields.io/badge/Security-Policy-blue.svg)](SECURITY.md)

</div>

---

## 什么是 Helix

**Glowhaven Helix** 是一款私有化部署的服务器控制台平台。它通过集中式 API 和轻量级 Agent，协调纳管服务器身份、集群资产清单、主机实时遥测、有界运维操作、任务状态及审计事件。

Helix 为基础设施、DevOps、平台工程、SRE 和系统管理员团队设计，提供统一的控制界面，用于监控受管节点并执行安全、许可列表驱动的系统管理任务，无需开放无限制的远程 Shell Gateway。

---

## 为什么选择 Helix

现代服务器集群往往通过分散的工具进行管理：静态资产 CMDB、独立监控 Agent、临时 SSH 脚本、配置管理作业以及分散的日志记录。当发生故障或需要日常维护时，运维人员必须跨多个系统核对信息：

1. **存在哪些机器，它们的实时健康状态如何？**
2. **目标服务器上允许执行哪些运维操作？**
3. **谁授权了变更，何时执行的，结果如何？**

Helix 通过将服务器状态、Agent 轮询、有界任务执行和密码学关联审计日志统一整合至单个私有部署控制台，解决了这种碎片化问题。

---

## Helix 不是什么

为了保持明确的架构边界，Helix 明确限定了功能范围：

- **不是通用远程 Shell 网关：** Helix 不提供交互式 SSH、WebSockets Shell 流或任意命令执行端点。
- **不是完整的 Kubernetes 控制平面：** Helix 管理服务器节点及主机级服务，而非容器 Pod 调度。
- **不是配置管理工具：** Helix 不替代 Ansible、Puppet 或 Chef 等声明式状态引擎，但可以在受管节点上执行离散的生命周期任务。
- **不是通用 SIEM 或长期可观测性仓库：** Helix 追踪运维主机遥测与控制台审计轨迹；历史指标存储应由专用时序数据库处理。
- **不是硬件 BMC 控制器：** 带外 IPMI/Redfish 电源管理计划在未来版本中推出，目前不属于主机 Agent 操作范围。

---

## 核心能力

- **集群身份与资产清单：** 追踪主机名、CPU 架构、操作系统发行版、系统内存、磁盘分配及用户自定义标签。
- **遥测与健康监控：** 实时主机心跳收集 CPU、内存和磁盘利用率、运行时间（Uptime）、平均负载及活动进程指标。
- **有界远程运维：** 白名单驱动的执行模型，禁止执行任意命令，同时支持关键的主机运维任务。
- **多平台 Agent 操作：** Linux 主机使用 `systemctl`，Windows 主机使用 `sc.exe` 原生系统服务控制。
- **Step-Up 多因子身份验证 (MFA)：** 高风险操作（如服务器重启或关机）需进行 TOTP 二步验证。
- **防篡改审计日志：** 密码学关联审计日志（`SHA-256` 前向哈希链），确保所有管理员操作和 Agent 状态变更均可验证且不可篡改。
- **安全令牌注册：** 过期的单次使用注册令牌，与哈希化的持久 Agent API 密钥（`SHA-256`）配对。

---

## 功能矩阵

| 能力 | 状态 | 实现细节 |
| :--- | :--- | :--- |
| **服务器注册** | 已上线 | 通过 API/UI 发行过期、单次使用的注册令牌 |
| **集群资产清单** | 已上线 | 动态系统资源发现与自定义标签 |
| **主机遥测** | 已上线 | 实时 CPU、内存、磁盘、运行时间与负载追踪 |
| **健康状态衍生指标** | 已上线 | 即时状态计算（`online` 在线、`warning` 警告、`offline` 离线） |
| **有界服务器运维** | 已上线 | 参数校验的操作目录（`reboot` 重启、`shutdown` 关机、`service_*` 服务控制） |
| **Linux 服务管理** | 已上线 | 通过 `systemctl` 进行进程编排（`start`, `stop`, `restart`） |
| **Windows 服务管理** | 已上线 | 通过 `sc.exe` 进行进程编排（`start`, `stop`, `restart`） |
| **审计日志与验证** | 已上线 | SHA-256 前向哈希关联账本与 `/api/audit/verify` 完整性校验端点 |
| **身份认证与 RBAC** | 已上线 | scrypt 密码哈希、会话 Token、角色分级（`admin`, `operator`, `viewer`） |
| **TOTP Step-Up MFA** | 已上线 | 针对登录和高风险操作强制执行 RFC 6238 TOTP |
| **CSRF 与安全标头** | 已上线 | 双重提交 CSRF Cookie 模式、严格 CSP、HSTS、Frame 限制 |
| **容器安全加固** | 已上线 | 非 root 用户运行、只读根文件系统、删除 Linux Capability |
| **Enterprise Linux (RHEL/Rocky/Alma) 支持** | 已上线 | 详见 [Enterprise Linux 部署指南](docs/RHEL_GUIDE.md) |
| **OIDC / SAML SSO 集成** | 路线图中 | 企业身份提供商同步 |
| **PostgreSQL & 高可用** | 路线图中 | 从 SQLite 迁移至外部 HA 数据库集群 |
| **Redfish / IPMI 带外控制** | 路线图中 | 物理服务器生命周期管理的硬件 BMC 集成 |
| **补丁与维护编排** | 路线图中 | 带有审批窗口的自动化内核与软件包更新调度 |

---

## 架构说明

Helix 采用集中式控制器与分布式 Agent 架构。Agent 建立向外的 HTTPS 连接连接至控制台，发送健康遥测并轮询排队任务，受管服务器无需开放任何入站网络端口。

```text
               +-------------------------------------------+
               |  管理员 / Web UI / 自动化客户端             |
               +---------------------+---------------------+
                                     |
                                HTTPS / REST API
                                     |
               +---------------------v---------------------+
               |           HELIX 控制台 (Control Plane)    |
               |-------------------------------------------|
               |  - RBAC & 会话认证                        |
               |  - TOTP 多因子验证                        |
               |  - 集群资产清单引擎                       |
               |  - 有界操作目录校验                       |
               |  - 任务调度器与队列                       |
               |  - 密码学审计账本                         |
               |  - SQLite 存储 (PostgreSQL 在路线图中)    |
               +---------+---------------+---------------+
                         |               |               |
                         | 心跳 (出站)    | 任务轮询 (出站)| 任务汇报 (出站)
                         |               |               |
             +-----------v----+  +-------v--------+  +---v------------+
             |   受管服务器   |  |   受管服务器   |  |   受管服务器   |
             |   (Linux A)    |  |   (Linux B)    |  |  (Windows C)   |
             |----------------|  |----------------|  |----------------|
             | Helix Agent    |  | Helix Agent    |  | Helix Agent    |
             | - systemctl    |  | - systemctl    |  | - sc.exe       |
             +----------------+  +----------------+  +----------------+
```

---

## 安全架构

Helix 在认证、会话处理、执行限制和传输边界方面贯彻深度防御。

### 已实现的安全控制

- **密码哈希：** 使用 `scrypt` 算法，每个账户使用随机 Salt。
- **会话安全：** 强密码学会话标识符，存储在 `HttpOnly`、`SameSite=Strict` Cookie 中。
- **CSRF 防护：** 针对所有修改状态的请求（`POST`, `PUT`, `PATCH`, `DELETE`），验证双重提交 Token（比对 `X-CSRF-Token` 请求头与 `helix_csrf` Cookie）。
- **基于角色的访问控制 (RBAC)：** API 层强制执行三级权限：
  - `admin`：完全控制，用户生命周期，注册 Token 发行，审计验证。
  - `operator`：集群查看，诊断执行，已批准任务下发。
  - `viewer`：资产清单、遥测与任务状态的只读权限。
- **Step-Up 身份验证：** 当操作员会话启用 MFA 时，破坏性或高影响操作（`reboot`, `shutdown`）必须提供有效的 TOTP 动态码。
- **Agent 凭据保护：** Agent 注册生成唯一的持久 Agent Key。控制台数据库中仅存储 API Key 的 `SHA-256` 哈希（`agent_key_hash`）。Agent 在出站轮询请求中带上 `X-Helix-Agent-Key` 标头。
- **操作白名单与参数校验：** API 强制执行严格的可执行操作白名单（`reboot`, `shutdown`, `service_start`, `service_stop`, `service_restart`, `refresh_inventory`, `collect_diagnostics`）。服务名称受正则表达式限制（`^[A-Za-z0-9_.@-]{1,128}$`）。
- **密码学审计账本：** 审计记录包括 `actor`（操作者）、`action`（操作）、`target`（目标）、`detail_json`（细节）、`created_at`（创建时间）及 `prev_hash`（前向哈希）。哈希采用 `SHA-256` 链条生成，可自动校验日志是否遭到篡改。

---

## 快速开始

### 前置条件

- **Python：** 3.12 或更高版本
- **操作系统：** Linux (RHEL/Rocky/Alma/Ubuntu/Debian), macOS, 或 Windows
- **依赖：** `fastapi`, `uvicorn`, `psutil`, `httpx`

### 本地部署

```bash
# 克隆仓库
git clone https://github.com/GlowhavenIndustries/Glowhaven-Server-Platform.git
cd Glowhaven-Server-Platform

# 创建并激活虚拟环境
python3 -m venv .venv
source .venv/bin/activate  # Windows 环境: .venv\Scripts\activate

# 安装开发依赖
pip install -r requirements-dev.txt

# 设置初始管理员密码（可选，未设置将随机生成并在控制台输出）
export HELIX_BOOTSTRAP_PASSWORD="ChangeThisToASecurePassword123!"

# 启动 Helix 控制台服务
python3 -m uvicorn helix.main:app --host 127.0.0.1 --port 8700
```

在浏览器中访问控制台 UI：

```text
http://127.0.0.1:8700
```

默认管理员用户名：`admin`

### Enterprise Linux (RHEL / Rocky / AlmaLinux) 快速部署指南

如需在红帽企业 Linux (RHEL) 及兼容发行版上将 Agent 部署为 systemd 后台服务，请参阅：
📖 **[Enterprise Linux (RHEL/Rocky/Alma) 部署与 Systemd 配置指南](docs/RHEL_GUIDE.md)**

---

## 社区与贡献

我们非常欢迎来自开源社区、Enterprise Linux 用户与安全研究人员的贡献！

- **参与贡献：** 请参阅 [贡献指南 (CONTRIBUTING.md)](CONTRIBUTING.md) 或 [中文贡献指南](CONTRIBUTING_zh-CN.md)。
- **问题反馈：** 欢迎通过 GitHub Issue 提交功能建议或 Bug 汇报。
- **安全漏洞：** 敏感安全问题请遵循 [SECURITY.md](SECURITY.md) 私密披露。

---

## 许可证

Glowhaven Helix 采用 [MIT 开源许可证](LICENSE)。

<div align="center">

**Glowhaven Server Platform · Glowhaven Helix**

*受控的基础设施运维 · 统一遥测 · 验证可信审计链*

</div>
