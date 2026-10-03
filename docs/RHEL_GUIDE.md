# Enterprise Linux (RHEL / Rocky / AlmaLinux / Fedora) Deployment Guide

[English](RHEL_GUIDE.md) | [简体中文](RHEL_GUIDE_zh-CN.md)

This guide provides instructions for deploying the **Glowhaven Helix Agent** on Enterprise Linux distributions, including **Red Hat Enterprise Linux (RHEL)**, **Rocky Linux**, **AlmaLinux**, and **Fedora**.

---

## Overview

Helix Agent is a lightweight Python service that communicates with the Helix Control Plane over outbound HTTP/HTTPS. On Enterprise Linux systems, the agent interacts with `systemctl` to execute bounded service lifecycle actions (`start`, `stop`, `restart`).

No inbound firewall ports are required on managed servers.

---

## Step 1: System Prerequisites

Ensure Python 3.12+ and system administration tools are installed:

```bash
# RHEL / Rocky / AlmaLinux 9+
sudo dnf install -y python3 python3-pip

# Verify Python version (3.12+ recommended)
python3 --version
```

---

## Step 2: Service User Setup

Create a dedicated system user and directory for the Helix Agent:

```bash
# Create dedicated system group and user
sudo groupadd --system helix
sudo useradd --system -g helix -s /sbin/nologin -d /opt/helix-agent helix

# Create installation directory
sudo mkdir -p /opt/helix-agent
sudo chown helix:helix /opt/helix-agent
sudo chmod 0750 /opt/helix-agent
```

---

## Step 3: Installation & Environment Setup

Copy or clone the agent source code into `/opt/helix-agent` and set up a virtual environment:

```bash
cd /opt/helix-agent

# Create virtual environment
sudo -u helix python3 -m venv venv
sudo -u helix /opt/helix-agent/venv/bin/pip install --upgrade pip
sudo -u helix /opt/helix-agent/venv/bin/pip install psutil httpx
```

Deploy the agent code:
Copy the `agent/` folder into `/opt/helix-agent/agent/`.

---

## Step 4: Agent Enrollment

Obtain an Enrollment Token from your Helix Control Plane UI or API (`POST /api/enrollment-tokens`).

Run the initial registration as the `helix` user:

```bash
sudo -u helix /opt/helix-agent/venv/bin/python3 -m agent \
  --controller https://helix.yourdomain.com \
  --enrollment-token <YOUR_ENROLLMENT_TOKEN> \
  --name $(hostname -s)
```

Upon success, the agent creates `/opt/helix-agent/agent.json` containing the registered agent ID and persistent hashed key. Secure the permissions:

```bash
sudo chmod 0600 /opt/helix-agent/agent.json
sudo chown helix:helix /opt/helix-agent/agent.json
```

---

## Step 5: Systemd Unit Configuration

Create a systemd unit file at `/etc/systemd/system/helix-agent.service`:

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

# Security hardening directives
ProtectSystem=full
ProtectHome=true
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

Reload systemd, enable, and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now helix-agent
```

Verify service status and logs:

```bash
sudo systemctl status helix-agent
sudo journalctl -u helix-agent -f
```

---

## Step 6: SELinux & Firewalld Considerations

### Firewalld

Since Helix Agent only makes **outbound** HTTP/HTTPS connections to the Helix Controller, no inbound ports need to be opened in `firewalld`.

If outbound connectivity is restricted, allow HTTPS traffic:

```bash
sudo firewall-cmd --zone=trusted --add-service=https --permanent
sudo firewall-cmd --reload
```

### SELinux

If SELinux is in `Enforcing` mode, ensure the file contexts for `/opt/helix-agent` are set properly:

```bash
sudo semanage fcontext -a -t bin_t "/opt/helix-agent(/.*)?"
sudo restorecon -R /opt/helix-agent
```

---

## Step 7: Managing Services via Sudo / Polkit (Optional)

If the `helix` agent user needs permission to restart system services via `systemctl`, add a targeted sudoers rule in `/etc/sudoers.d/helix-agent`:

```text
helix ALL=(ALL) NOPASSWD: /usr/bin/systemctl start *, /usr/bin/systemctl stop *, /usr/bin/systemctl restart *
```

Ensure permissions are set to `0440`:

```bash
sudo chmod 0440 /etc/sudoers.d/helix-agent
```

---

## Support & Feedback

If you encounter issues on Enterprise Linux, please open an issue in the GitHub repository or submit a PR with improvements!
