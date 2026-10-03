# 红帽企业 Linux (RHEL / Rocky / AlmaLinux / Fedora) 部署指南

[English](RHEL_GUIDE.md) | [简体中文](RHEL_GUIDE_zh-CN.md)

本指南为在红帽企业 Linux 发行版（包括 **RHEL**、**Rocky Linux**、**AlmaLinux** 和 **Fedora**）上部署 **Glowhaven Helix Agent** 提供详细操作步骤。

---

## 概述

Helix Agent 是一款轻量级 Python 服务，通过出站 HTTP/HTTPS 与 Helix 控制台 (Control Plane) 通信。在 Enterprise Linux 系统上，Agent 与系统 `systemctl` 协作，执行受控的服务生命周期操作（`start`、`stop`、`restart`）。

受管服务器上**无需开放任何入站防火墙端口**。

---

## 第一步：系统前置条件

确保已安装 Python 3.12+ 及基础系统管理工具：

```bash
# RHEL / Rocky / AlmaLinux 9+
sudo dnf install -y python3 python3-pip

# 检查 Python 版本 (推荐 3.12+)
python3 --version
```

---

## 第二步：创建专用服务账户

为 Helix Agent 创建独立的系统用户和目录：

```bash
# 创建系统组和用户
sudo groupadd --system helix
sudo useradd --system -g helix -s /sbin/nologin -d /opt/helix-agent helix

# 创建安装目录
sudo mkdir -p /opt/helix-agent
sudo chown helix:helix /opt/helix-agent
sudo chmod 0750 /opt/helix-agent
```

---

## 第三步：环境准备与代码部署

将 Agent 源码复制或克隆至 `/opt/helix-agent` 并建立虚拟环境：

```bash
cd /opt/helix-agent

# 创建 Python 虚拟环境
sudo -u helix python3 -m venv venv
sudo -u helix /opt/helix-agent/venv/bin/pip install --upgrade pip
sudo -u helix /opt/helix-agent/venv/bin/pip install psutil httpx
```

将 `agent/` 代码放置于 `/opt/helix-agent/agent/` 目录下。

---

## 第四步：Agent 节点注册 (Enrollment)

从 Helix 控制台 UI 或 API 申请一个注册令牌（Enrollment Token）。

以 `helix` 用户身份运行首次注册：

```bash
sudo -u helix /opt/helix-agent/venv/bin/python3 -m agent \
  --controller https://helix.yourdomain.com \
  --enrollment-token <你的注册令牌> \
  --name $(hostname -s)
```

注册成功后，Agent 将在 `/opt/helix-agent/agent.json` 生成本地配置文件（包含持久化 Agent ID 及 API 密钥）。配置安全权限：

```bash
sudo chmod 0600 /opt/helix-agent/agent.json
sudo chown helix:helix /opt/helix-agent/agent.json
```

---

## 第五步：配置 Systemd 服务文件

创建 systemd 服务配置文件 `/etc/systemd/system/helix-agent.service`：

```ini
[Unit]
Description=Glowhaven Helix Server Control Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=helix
Group=helix
WorkingDirectory=/opt/helix-agent
ExecStart=/opt/helix-agent/venv/bin/python3 -m agent --controller https://helix.yourdomain.com
Restart=on-failure
RestartSec=10s

# 安全加固配置
ProtectSystem=full
ProtectHome=true
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

重载 systemd，启用并启动 Agent 服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now helix-agent
```

检查服务状态与日志：

```bash
sudo systemctl status helix-agent
sudo journalctl -u helix-agent -f
```

---

## 第六步：SELinux 与 Firewalld 防火墙配置

### Firewalld 防火墙

因为 Helix Agent 只向 Helix 控制台发起**出站** HTTPS 连接，所以无需在 `firewalld` 打开任何入站端口。

如果服务器限制了出站规则，请允许 HTTPS 流量出站：

```bash
sudo firewall-cmd --zone=trusted --add-service=https --permanent
sudo firewall-cmd --reload
```

### SELinux 配置

若 SELinux 处于 `Enforcing` 强制模式，请仅为不可变代码路径设置 `bin_t`，并将可写状态放到独立目录：

```bash
# 仅标记代码/虚拟环境为可执行类型
sudo semanage fcontext -a -t bin_t "/opt/helix-agent/bin(/.*)?"
sudo semanage fcontext -a -t bin_t "/opt/helix-agent/venv(/.*)?"

# 可写状态目录使用数据类型（例如 agent.json、运行时文件）
sudo mkdir -p /var/lib/helix-agent
sudo semanage fcontext -a -t var_lib_t "/var/lib/helix-agent(/.*)?"

# 应用标签
sudo restorecon -R /opt/helix-agent /var/lib/helix-agent
```

---

## 第七步：通过 Sudo / Polkit 提权服务管理 (可选)

若 `helix` 用户需要执行 `systemctl` 管理系统服务，可以在 `/etc/sudoers.d/helix-agent` 中添加**仅限明确服务名**的受限 sudo 规则（请按实际服务替换）：

```text
helix ALL=(ALL) NOPASSWD: /usr/bin/systemctl start nginx.service, /usr/bin/systemctl stop nginx.service, /usr/bin/systemctl restart nginx.service, /usr/bin/systemctl start myapp.service, /usr/bin/systemctl stop myapp.service, /usr/bin/systemctl restart myapp.service
```

确保权限设为 `0440`：

```bash
sudo chmod 0440 /etc/sudoers.d/helix-agent
```

---

## 社区支持与问题反馈

若在 Enterprise Linux 部署过程中遇到问题，欢迎在 GitHub 仓库提交 Issue 或提交 PR 共同改进！
