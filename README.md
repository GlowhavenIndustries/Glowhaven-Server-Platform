# Glowhaven Server Platform

<div align="center">

# **HELIX**

### The server control plane for your entire infrastructure.

**Inventory. Observe. Operate. Audit.**

A self-hosted control plane for managing corporate server fleets through one secure, operator-first system.

[![CI](https://github.com/GlowhavenIndustries/Glowhaven-Server-Platform/actions/workflows/ci.yml/badge.svg)](https://github.com/GlowhavenIndustries/Glowhaven-Server-Platform/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.12%2B-111827?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-control%20plane-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-111827.svg)](LICENSE)

</div>

---

## The idea

Modern infrastructure is usually split across too many control surfaces.

One tool knows the machine. Another knows the operating system. Another handles monitoring. Another handles automation. Another stores inventory. Another records changes.

**Helix brings the operational layer together.**

It gives infrastructure teams one place to answer three questions quickly:

**What is running? What needs attention? What can I safely change?**

Helix is designed as a server control plane rather than a dashboard-only monitoring product. The system combines fleet identity, live telemetry, controlled operations, agent communication, job state, and audit events around the same infrastructure model.

## Built for serious infrastructure

Helix takes proven ideas from the broader infrastructure ecosystem and connects them into a focused server operations layer.

| Layer | Helix approach |
| --- | --- |
| Fleet identity | Server inventory, OS identity, architecture, labels, and last-seen state |
| Health | CPU, memory, disk, uptime, connectivity, and derived fleet status |
| Operations | Explicitly allowlisted actions with validated parameters |
| Execution | Lightweight server agent for Linux and Windows |
| Work management | Queued operations with running, succeeded, and failed states |
| Security | Sessions, CSRF protection, password hashing, enrollment controls, and security headers |
| Accountability | Operator and agent audit events |
| Deployment | Self-hosted, container-ready architecture |

Helix deliberately does **not** start with unrestricted remote shell execution. High-impact infrastructure software should make safe operations easy without creating an uncontrolled command gateway.

---

## What you can do today

### Fleet control

See the state of registered servers from one control surface.

- Server identity and hostname
- Operating system and architecture
- CPU, memory, and disk utilization
- Uptime and last-seen telemetry
- Online, warning, and offline state
- Searchable fleet view

### Controlled operations

Queue bounded actions against managed servers.

- Refresh inventory
- Collect diagnostics
- Start a service
- Stop a service
- Restart a service
- Reboot a server
- Shut down a server

Operations are validated by the control plane before they reach an agent.

### Secure enrollment

Add servers through expiring, single-use enrollment tokens.

The workflow is intentionally simple:

```text
Admin
  |
  | Generate enrollment token
  v
Helix Control Plane
  |
  | Secure registration
  v
Helix Agent
  |
  | Telemetry + controlled jobs
  v
Managed Server
```

### Auditability

Security-relevant activity is recorded as structured audit events, giving operators a clear trail for authentication, server enrollment, operation requests, and agent job results.

---

## Architecture

```text
                         CORPORATE INFRASTRUCTURE
                                  |
                    +-------------+-------------+
                    |                           |
              Web / API Clients            Internal Operators
                    |                           |
                    +-------------+-------------+
                                  |
                         +--------v--------+
                         |   HELIX CONTROL |
                         |                 |
                         | Auth            |
                         | Fleet inventory|
                         | Telemetry      |
                         | Operations     |
                         | Job queue      |
                         | Audit          |
                         +--------+--------+
                                  |
                    +-------------+-------------+
                    |             |             |
             +------v------+ +----v-----+ +-----v------+
             | Production  | | Database | | Application|
             | Server      | | Server   | | Server     |
             | Helix Agent | | Helix    | | Helix      |
             +-------------+ +----------+ +------------+
                    |
             telemetry + approved operations
```

The current release uses SQLite for a straightforward self-hosted deployment. The architecture is intentionally shaped so the persistence layer can evolve to PostgreSQL and high-availability deployment as the platform matures.

---

## Security architecture

Helix is built around a narrow control boundary.

**Authentication**
- Local admin authentication
- scrypt password hashing
- HttpOnly, SameSite session cookies
- Expiring sessions

**Browser security**
- CSRF protection on state-changing requests
- Restrictive Content Security Policy
- Clickjacking protection
- MIME sniffing protection
- Referrer and permissions policies
- Optional HSTS when secure cookies are enabled

**Server enrollment**
- Expiring enrollment tokens
- Single-use enrollment
- Per-server agent credentials
- Agent credentials stored as SHA-256 hashes in the control plane

**Remote operations**
- Explicit server-side action allowlist
- Strict service-name validation
- No arbitrary command endpoint
- Job execution and result reporting through authenticated agents

**Container hardening**
- Non-root runtime user
- Dropped Linux capabilities
- no-new-privileges
- Read-only filesystem
- Temporary filesystem for runtime scratch space

See [SECURITY.md](SECURITY.md) for vulnerability reporting and security expectations.

> **Important:** This repository is an engineering project, not a certification or guarantee of security. Production environments should add TLS, enterprise identity, protected backups, centralized logging, network segmentation, secrets management, and infrastructure controls appropriate to their threat model.

---

## Quick start

### Local development

```bash
git clone https://github.com/GlowhavenIndustries/Glowhaven-Server-Platform.git
cd Glowhaven-Server-Platform

python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

pip install -r requirements-dev.txt

# Set a strong bootstrap password
# PowerShell:
$env:HELIX_BOOTSTRAP_PASSWORD="replace-with-a-long-random-password"

# Bash:
export HELIX_BOOTSTRAP_PASSWORD="replace-with-a-long-random-password"

uvicorn helix.main:app --host 127.0.0.1 --port 8700
```

Open:

```
http://127.0.0.1:8700
```

Default bootstrap username:

```
admin
```

The password should always be supplied through environment configuration in real deployments.

### Docker

```bash
cp .env.example .env
docker compose up --build
```

For production, terminate TLS at a trusted reverse proxy, enable secure cookies, provide durable storage, and protect the control plane from untrusted network exposure.

---

## Enroll your first server

Sign in as an administrator and select **Add server**.

Generate a single-use enrollment token, then run the agent on the target server:

```bash
python -m agent \
  --controller https://helix.example.internal \
  --enrollment-token <TOKEN> \
  --name prod-web-01
```

After registration, the agent stores its returned credential locally with restrictive file permissions where the operating system supports them.

The agent then sends heartbeats and polls for approved work.

---

## Agent behavior

The Helix agent is intentionally small.

It collects:

- Hostname
- Platform
- Architecture
- OS version
- CPU utilization
- Memory utilization
- Disk utilization
- Uptime
- Basic machine inventory
- Labels

It can execute only the operations exposed by the control plane's action catalog.

On Linux, service operations use `systemctl`.

On Windows, service operations use `sc.exe`.

This design keeps the security boundary visible in both the controller and the agent.

---

## Repository structure

```text
Glowhaven-Server-Platform/
├── helix/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── db.py
│   ├── security.py
│   └── static/
│       ├── index.html
│       ├── app.css
│       └── app.js
├── agent/
│   └── __main__.py
├── tests/
│   └── test_security.py
├── .github/
│   └── workflows/
│       └── ci.yml
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── LICENSE
├── README.md
├── SECURITY.md
├── pyproject.toml
├── requirements.txt
└── requirements-dev.txt
```

---

## Development

Run the test suite:

```bash
pytest -q
```

Run syntax validation:

```bash
python -m py_compile helix/*.py agent/*.py
```

The CI workflow runs the test suite, Python compilation checks, and dependency vulnerability auditing.

---

## Product direction

Helix is intended to grow into a complete infrastructure control platform.

The next layers are planned around real operator workflows:

**Identity and access**
- OIDC and enterprise SSO
- Fine-grained RBAC
- Scoped permissions
- Approval policies
- Break-glass access controls

**Infrastructure**
- PostgreSQL
- High availability
- Multi-site control planes
- Edge relays
- Network-aware inventory
- Rack and data-center modeling

**Operations**
- Maintenance windows
- Scheduled changes
- Change approvals
- Dry runs
- Rollback-aware jobs
- Staged fleet rollouts

**Lifecycle**
- Patch management
- Configuration drift detection
- Policy enforcement
- Compliance reporting
- Signed agent releases
- Automatic agent updates

**Hardware and platforms**
- Redfish
- IPMI
- BMC workflows
- Virtualization platforms
- Cluster management

**Observability**
- Alert routing
- Incident workflows
- Historical telemetry
- Capacity planning
- Service dependency views

The long-term goal is straightforward:

> **One control plane where infrastructure teams can understand the fleet, make safe changes, and prove what happened.**

---

## Why this project exists

Enterprise infrastructure should not require operators to think about six products before they can answer one question.

Helix is an open, self-hosted foundation for bringing those workflows closer together without hiding the underlying systems.

It is intentionally transparent:

- The control plane is inspectable.
- Operations are explicit.
- Agents are small.
- Security boundaries are visible.
- Infrastructure state is modeled directly.
- Deployment is designed for environments that need to keep control of their data.

---

## Contributing

Contributions are welcome.

For meaningful changes, open an issue first so the architecture and operational impact can be discussed before implementation.

Security vulnerabilities should **not** be posted publicly. See [SECURITY.md](SECURITY.md).

---

## License

Helix is released under the MIT License. See [LICENSE](LICENSE).

<div align="center">

**Glowhaven Server Platform · Helix**

*Infrastructure control, without the infrastructure maze.*

</div>
