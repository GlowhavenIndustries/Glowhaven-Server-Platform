# Glowhaven Server Platform

[English](README.md) | [简体中文](README_zh-CN.md)

<div align="center">

# **Glowhaven Helix**

### The server control plane for your infrastructure.

**A unified open-source operational control layer for server identity, telemetry, bounded remote operations, job orchestration, and tamper-evident audit logging.**

[![CI](https://github.com/GlowhavenIndustries/Glowhaven-Server-Platform/actions/workflows/ci.yml/badge.svg)](https://github.com/GlowhavenIndustries/Glowhaven-Server-Platform/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/Python-3.12%2B-111827?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-control%20plane-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-111827.svg)](LICENSE)
[![Security Policy](https://img.shields.io/badge/Security-Policy-blue.svg)](SECURITY.md)

</div>

---

## What Helix is

**Glowhaven Helix** is a self-hosted server control plane that coordinates managed server identity, fleet inventory, real-time host telemetry, controlled operations, job state, and audit events through a centralized API and lightweight agents.

Designed for infrastructure, DevOps, platform, SRE, and systems administration teams, Helix provides a single control surface to monitor managed nodes and execute safe, allowlisted administrative tasks without exposing unrestricted remote shell gateways.

---

## Why Helix exists

Modern server fleets are frequently managed across disconnected tools: static inventory CMDBs, standalone monitoring agents, ad-hoc SSH scripts, configuration management jobs, and uncentralized activity logs. When an incident occurs or routine maintenance is required, operators must cross-reference multiple systems to answer fundamental questions:

1. **What machines exist and what is their live health state?**
2. **What operational actions are permitted on target servers?**
3. **Who authorized a change, when was it executed, and what was the outcome?**

Helix addresses this fragmentation by unifying server state, agent polling, bounded job execution, and cryptographically linked audit logging into a single self-hosted control plane.

---

## What Helix is not

To maintain clarity around architectural scope, Helix is intentionally bounded:

- **Not a general-purpose remote shell gateway:** Helix does not expose interactive SSH, WebSockets shell streams, or arbitrary command execution endpoints.
- **Not a complete Kubernetes control plane:** Helix manages server nodes and host-level services rather than container pod scheduling.
- **Not a configuration management tool:** Helix does not replace declarative state engines like Ansible, Puppet, or Chef, but can execute discrete lifecycle jobs on managed nodes.
- **Not a general SIEM or long-term observability warehouse:** Helix tracks operational host telemetry and control plane audit trails; historical metric storage should be handled by dedicated time-series databases.
- **Not a hardware BMC controller:** Out-of-band IPMI/Redfish power management is planned for future releases but is not part of host-agent operations.

---

## Core capabilities

- **Fleet Identity & Inventory:** Track hostnames, CPU architecture, OS distributions, system memory, disk allocations, and user-assigned labels.
- **Telemetry & Health Monitoring:** Real-time host heartbeat collecting CPU, memory, and disk utilization, uptime, load averages, and active process metrics.
- **Bounded Remote Operations:** Allowlist-driven execution model preventing arbitrary command execution while enabling essential host tasks.
- **Multi-Platform Agent Operations:** Native system service control using `systemctl` on Linux and `sc.exe` on Windows hosts.
- **Step-Up Multi-Factor Authentication:** Require TOTP multi-factor verification for high-impact operations such as host reboot or shutdown.
- **Tamper-Evident Audit Logging:** Cryptographically chained audit log (`SHA-256` prev-hash links) ensuring all administrative actions and agent state transitions are verifiable and immutable.
- **Secure Token-Based Enrollment:** Expiring, single-use enrollment tokens paired with hashed per-agent persistent API keys (`SHA-256`).

---

## Feature matrix

| Capability | Status | Implementation Details |
| :--- | :--- | :--- |
| **Server Enrollment** | Available | Expiring, single-use enrollment tokens via API/UI |
| **Fleet Inventory** | Available | Dynamic system resource discovery and custom labels |
| **Host Telemetry** | Available | Real-time CPU, RAM, disk, uptime, and load tracking |
| **Health State Derived Metrics** | Available | Instant status calculation (`online`, `warning`, `offline`) |
| **Bounded Server Operations** | Available | Parameter-validated action catalog (`reboot`, `shutdown`, `service_*`) |
| **Linux Service Management** | Available | Process orchestration via `systemctl` (`start`, `stop`, `restart`) |
| **Windows Service Management** | Available | Process orchestration via `sc.exe` (`start`, `stop`, `restart`) |
| **Enterprise Linux (RHEL/Rocky/Alma)** | Available | Systemd service integration & firewalld guidelines ([RHEL Deployment Guide](docs/RHEL_GUIDE.md)) |
| **Audit Logging & Verification** | Available | SHA-256 prev-hash linked ledger with `/api/audit/verify` integrity endpoint |
| **Authentication & RBAC** | Available | scrypt password hashing, session tokens, role tiers (`admin`, `operator`, `viewer`) |
| **TOTP Step-Up MFA** | Available | RFC 6238 TOTP enforcement for login and destructive operations |
| **CSRF & Security Headers** | Available | Double-submit CSRF cookie token pattern, strict CSP, HSTS, frame options |
| **Container Hardening** | Available | Non-root runtime execution, read-only root FS, dropped Linux capabilities |
| **OIDC / SAML SSO Integration** | Roadmap | Enterprise identity provider synchronization |
| **PostgreSQL & High Availability** | Roadmap | Migration path from SQLite to external HA database clusters |
| **Redfish / IPMI Out-of-Band Control** | Roadmap | Hardware BMC integration for physical server lifecycle management |
| **Patch & Maintenance Orchestration**| Roadmap | Automated kernel and package update scheduling with approval windows |

---

## Architecture

Helix follows a centralized controller and distributed agent architecture. Agents establish outbound HTTPS connections to the control plane to send health telemetry and poll for queued jobs, requiring no inbound network ports on managed host servers.

```text
               +-------------------------------------------+
               |  Operator / Web UI / Automation Client    |
               +---------------------+---------------------+
                                     |
                                HTTPS / REST API
                                     |
               +---------------------v---------------------+
               |           HELIX CONTROL PLANE             |
               |-------------------------------------------|
               |  - RBAC & Session Auth                    |
               |  - TOTP Multi-Factor Verification         |
               |  - Fleet Inventory Engine                 |
               |  - Bounded Action Catalog Validation      |
               |  - Job Dispatcher & Queue                 |
               |  - Cryptographic Audit Ledger             |
               |  - SQLite Storage (PostgreSQL Roadmap)    |
               +---------+---------------+---------------+
                         |               |               |
                         | Heartbeat     | Job Polling   | Job Reporting
                         | (Outbound)    | (Outbound)    | (Outbound)
                         |               |               |
             +-----------v----+  +-------v--------+  +---v------------+
             | Managed Server |  | Managed Server |  | Managed Server |
             |   (Linux A)    |  |   (Linux B)    |  |  (Windows C)   |
             |----------------|  |----------------|  |----------------|
             | Helix Agent    |  | Helix Agent    |  | Helix Agent    |
             | - systemctl    |  | - systemctl    |  | - sc.exe       |
             +----------------+  +----------------+  +----------------+
```

---

## Security architecture

Helix prioritizes defense-in-depth across authentication, session handling, execution limits, and transport boundaries.

### Implemented security controls

- **Password Hashing:** Passwords are hashed using `scrypt` with random salt per account.
- **Session Security:** Cryptographically strong session identifiers (`token()` token generation) stored in `HttpOnly`, `SameSite=Strict` cookies.
- **CSRF Protection:** Anti-CSRF double-submit token verification (`X-CSRF-Token` header comparison against `helix_csrf` cookie) for all state-modifying requests (`POST`, `PUT`, `PATCH`, `DELETE`).
- **Role-Based Access Control (RBAC):** Three privilege tiers enforced at API level:
  - `admin`: Full control, user lifecycle, enrollment token issuance, audit verification.
  - `operator`: Fleet viewing, diagnostic execution, approved job dispatch.
  - `viewer`: Read-only access to inventory, telemetry, and job status.
- **Step-Up Authentication:** Destructive or high-impact actions (`reboot`, `shutdown`) require an active TOTP code when MFA is enabled on the operator session.
- **Agent Credential Protection:** Agent enrollment generates a unique persistent agent key. Only the `SHA-256` hash of the key is stored in the control plane database (`agent_key_hash`). Agents send `X-Helix-Agent-Key` headers on outbound polling requests.
- **Action Allowlisting & Parameter Validation:** The API enforces a strict allowlist of executable actions (`reboot`, `shutdown`, `service_start`, `service_stop`, `service_restart`, `refresh_inventory`, `collect_diagnostics`). Service names are restricted by regular expression (`^[A-Za-z0-9_.@-]{1,128}$`).
- **Cryptographic Audit Ledger:** Audit trail records include `actor`, `action`, `target`, `detail_json`, `created_at`, and `prev_hash`. Record hashes are generated using `HMAC-SHA256` or `SHA-256` hash chains, allowing automated detection of log tampering.
- **Container Isolation:** The official `Dockerfile` executes as non-root user `helix` (`UID 10001`), drops Linux capabilities (`cap_drop: ALL`), sets `read_only: true` for the filesystem root, and configures `/tmp` as `tmpfs`.

### Security policy & private vulnerability disclosure

Security vulnerabilities should be disclosed privately according to our security policy. **Do not submit public GitHub issues for security vulnerabilities.**

Refer to [SECURITY.md](SECURITY.md) for full submission guidelines and coordination procedures.

---

## Security philosophy

> **Helix prefers explicit permissions and bounded operations over unrestricted administrative power.**

Many infrastructure management tools grant direct, unconstrained shell access to remote hosts. While flexible, this approach introduces significant security risks, including unaudited command execution, accidental destructive commands, and expanded blast radiuses in the event of credential compromise.

Helix intentionally limits remote operations to a strictly validated catalog of administrative actions. Commands cannot be arbitrarily injected or formatted by clients. Every action parameter is validated on the control plane before reaching the managed agent.

---

## Quick start

### Prerequisites

- **Python:** 3.12 or higher
- **Operating System:** Linux, macOS, or Windows
- **Dependencies:** `fastapi`, `uvicorn`, `psutil`, `httpx` (for test suite)

### Local setup

```bash
# Clone the repository
git clone https://github.com/GlowhavenIndustries/Glowhaven-Server-Platform.git
cd Glowhaven-Server-Platform

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt

# Define initial admin bootstrap password (optional, otherwise random password printed)
export HELIX_BOOTSTRAP_PASSWORD="ChangeThisToASecurePassword123!"

# Start the Helix Control Plane server
python3 -m uvicorn helix.main:app --host 127.0.0.1 --port 8700
```

Access the control plane UI in your browser:

```text
http://127.0.0.1:8700
```

Default administrator username: `admin`

---

## Docker deployment

To deploy Helix using Docker and Docker Compose:

1. **Configure Environment:**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` to configure `HELIX_BOOTSTRAP_PASSWORD`, `HELIX_SECURE_COOKIES`, and `HELIX_DB_PATH`.

2. **Launch Container Service:**

   ```bash
   docker compose up --build -d
   ```

3. **Verify Container Status:**

   ```bash
   docker compose ps
   curl -f http://localhost:8700/healthz
   ```

---

## Production deployment considerations

When deploying Helix in enterprise production environments, implement the following infrastructure controls:

- **TLS Termination:** Deploy a reverse proxy (e.g., NGINX, HAProxy, or Caddy) in front of the control plane to enforce TLS 1.3 encryption.
- **Secure Cookie Flag:** Enable `HELIX_SECURE_COOKIES=true` in production environment settings so session and CSRF cookies carry `Secure` flags over HTTPS.
- **Persistence & Backups:** Mount a persistent volume for the SQLite database file (`/app/data/helix.db`) and schedule periodic database backups or volume snapshots.
- **Network Segmentation:** Place the control plane API behind internal firewalls or VPNs. Restrict agent communication paths to authorized internal subnet IP ranges.
- **Secrets Management:** Pass sensitive environment variables (`HELIX_BOOTSTRAP_PASSWORD`) via cloud secrets managers (e.g., HashiCorp Vault, AWS Secrets Manager) rather than plaintext files.

---

## Server enrollment

Enrolling a new managed node into Helix is a simple 8-step workflow:

```text
1. Administrator signs into Helix Control Plane.
2. Admin requests new Enrollment Token via UI or POST /api/enrollment-tokens.
3. Controller generates 15-minute, single-use token.
4. Administrator runs Helix Agent on target machine with enrollment token.
5. Agent executes POST /api/agent/register to exchange token for unique Agent Key.
6. Controller stores SHA-256 hash of Agent Key and returns enrollment confirmation.
7. Agent stores credential locally in agent.json (chmod 0600 where supported).
8. Agent initiates periodic outbound heartbeat and enters fleet inventory.
```

### Command example

On the target server, execute the lightweight agent:

```bash
python3 -m agent \
  --controller http://127.0.0.1:8700 \
  --enrollment-token <ENROLLMENT_TOKEN> \
  --name prod-app-01
```

Once registered, the agent automatically polls the controller every 15 seconds for queued operations.

---

## Real-world use cases

- **Internal IT Fleet Operations:** Manage on-premises and cloud Linux and Windows servers from a unified control plane without maintaining individual SSH keys or administrative credentials.
- **Platform Engineering Operational Control Layer:** Provide platform teams with a standardized API to query fleet status, monitor host metrics, and execute service lifecycle operations safely.
- **Self-Hosted Infrastructure Environments:** Operate server control software in air-gapped, sovereign, or private data centers where cloud-hosted vendor agents are prohibited.
- **Laboratory & Staging Fleet Operations:** Standardize operational workflows and job auditing across development, staging, and lab infrastructure environments.

---

## Differentiation

| Aspect | Traditional Remote Shell / Scripts | Legacy Monitoring Dashboards | Glowhaven Helix Control Plane |
| :--- | :--- | :--- | :--- |
| **Execution Surface** | Unrestricted arbitrary commands (`bash`, `powershell`) | Read-only metrics; no action capability | Bounded, validated action catalog |
| **Audit Visibility** | Local command history files (mutable/losable) | Metrics logs only | Cryptographically linked SHA-256 audit ledger |
| **Network Boundary** | Inbound SSH/RDP ports open to network | Outbound telemetry stream | Agent-initiated outbound HTTP/S polling |
| **Access Control** | Host-level user accounts or SSH key distribution | Dashboard login permissions | Granular API RBAC + Step-Up MFA |

---

## Ecosystem positioning

Helix is designed to integrate into existing infrastructure ecosystems rather than replace specialized tooling:

- **Configuration Management (Ansible / Puppet):** Use configuration management to provision operating systems and deploy the Helix Agent; use Helix for day-to-day operational status and rapid service restarts.
- **Infrastructure Source of Truth (NetBox):** Synchronize server metadata and IP allocations with CMDB sources of truth via Helix REST APIs.
- **Observability Systems (Prometheus / Grafana):** Use Prometheus for deep time-series metrics storage and alert routing; use Helix for operational intervention and job execution.
- **Incident Management (PagerDuty / Opsgenie):** Trigger diagnostic gathering or service restarts through Helix APIs in response to incident webhooks.

---

## Technology stack

- **Control Plane Framework:** [FastAPI](https://fastapi.tiangolo.com/) (Python 3.12+)
- **Application Server:** [Uvicorn](https://www.uvicorn.org/) (ASGI interface)
- **Database / Persistence:** SQLite 3 (embedded zero-config relational store with JSON field support)
- **System Telemetry:** [psutil](https://github.com/giampaolo/psutil) (cross-platform host process and resource utilization)
- **Frontend Layer:** Vanilla JavaScript (ES6+), HTML5, and CSS3 static assets (no heavy NPM build dependencies)
- **Containerization:** Docker & OCI-compliant multi-stage images

---

## API overview

Helix provides a complete RESTful API for control plane management and agent communication.

### Core API endpoints

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/healthz` | Unauthenticated system health check | None |
| `POST` | `/api/auth/login` | User login (returns session & CSRF cookies) | None |
| `POST` | `/api/auth/logout` | Revoke active user session | Session + CSRF |
| `GET` | `/api/me` | Fetch active user session information | Session |
| `GET` | `/api/summary` | Fetch fleet summary statistics | Session |
| `GET` | `/api/servers` | List all registered servers | Session |
| `GET` | `/api/servers/{id}` | Fetch server details and job history | Session |
| `POST` | `/api/servers/{id}/jobs` | Enqueue job on server (`admin`, `operator`) | Session + CSRF (+ Step-Up MFA for reboot/shutdown) |
| `GET` | `/api/jobs` | Fetch recent job queue execution history | Session |
| `POST` | `/api/enrollment-tokens` | Generate single-use agent enrollment token | `admin` + CSRF |
| `GET` | `/api/audit` | Retrieve structured audit log records | `admin` |
| `GET` | `/api/audit/verify` | Verify cryptographic hash chain of audit log | `admin` |

### Agent endpoints

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/agent/register` | Register new agent with enrollment token | Enrollment Token |
| `POST` | `/api/agent/heartbeat` | Submit host metrics telemetry heartbeat | `X-Helix-Agent-Key` Header |
| `POST` | `/api/agent/jobs/poll` | Poll controller for queued jobs | `X-Helix-Agent-Key` Header |
| `POST` | `/api/agent/jobs/{id}/report` | Report job execution completion status | `X-Helix-Agent-Key` Header |

Interactive OpenAPI documentation is available when running the server at `/api/docs`.

---

## Project structure

```text
Glowhaven-Server-Platform/
├── .github/
│   └── workflows/
│       └── ci.yml             # GitHub Actions CI workflow (tests, compile, audit)
├── agent/
│   └── __main__.py            # Lightweight Helix server agent implementation
├── helix/
│   ├── __init__.py            # Package entry initialization
│   ├── config.py              # Pydantic BaseSettings configuration management
│   ├── db.py                  # Database connection & schema migration engine
│   ├── main.py                # FastAPI routes, middleware, and API endpoints
│   ├── security.py            # Hashing, TOTP, and audit hash calculation utilities
│   └── static/                # Control plane web UI static assets
│       ├── app.css            # Dark-theme application stylesheet
│       ├── app.js             # Single-page application UI logic
│       └── index.html         # Web UI layout
├── tests/
│   └── test_security.py       # Unit and security integration test suite
├── .dockerignore              # Docker build file exclusion rules
├── .env.example               # Example environment configuration template
├── .gitignore                 # Git repository exclusion definitions
├── Dockerfile                 # Multi-stage hardened OCI container image build
├── docker-compose.yml         # Container orchestration specification
├── LICENSE                    # MIT open-source license text
├── pyproject.toml             # Python project configuration
├── README.md                  # Project documentation
├── requirements-dev.txt       # Development dependencies (pytest, httpx)
├── requirements.txt           # Application runtime dependencies
└── SECURITY.md                # Vulnerability disclosure and security policy
```

---

## Development & testing

### Development setup

1. Clone repository and set up environment as shown in [Quick start](#quick-start).
2. Install development tools:

   ```bash
   pip install -r requirements-dev.txt
   ```

### Running the test suite

Run the automated test suite using `pytest`:

```bash
pytest -q
```

### Syntax validation

Verify syntax compilation across control plane and agent code:

```bash
python3 -m py_compile helix/*.py agent/*.py
```

### CI pipeline checks

The repository's GitHub Actions workflow (`.github/workflows/ci.yml`) executes:

- Unit and security integration tests via `pytest`.
- Python code compilation verification.
- Dependency security auditing via `pip-audit`.

---

## Operating-system & platform compatibility

### Platform classification matrix

| Operating System / Distribution | Classification Status | Operational Details |
| :--- | :--- | :--- |
| **Ubuntu / Debian Linux** | **Tested & Validated** | Fully supported; `systemctl` service management verified |
| **Enterprise Linux (RHEL / Rocky / Alma / Fedora)** | **Tested & Validated** | Fully supported; standard systemd integration tested |
| **macOS (Darwin)** | **Expected to work** | Agent telemetry supported; service management varies by Launchd |
| **Windows Server (2016+) / Windows 10/11** | **Tested & Validated** | Service management via native `sc.exe` and PowerShell/cmd |

---

## Red Hat & Enterprise Linux ecosystem considerations

Helix is engineered to operate seamlessly within Enterprise Linux environments (RHEL, Rocky Linux, AlmaLinux, Fedora):

- **Systemd Service Control:** Service start, stop, and restart operations interact directly with `systemctl` units via standard system interfaces.
- **SELinux Compatibility:** The Helix agent does not require modifying SELinux policy modules or disabling enforcement. Custom service units created for the agent should be assigned standard `bin_t` or service execution contexts.
- **Least-Privilege Execution:** The agent can run under unprivileged dedicated system user accounts (`helix-agent`), utilizing standard `sudoers` rules or polkit policies strictly scoped to `/usr/bin/systemctl <action> <service>`.

---

## Enterprise evaluation & operating model

Organizations evaluating Helix for enterprise server operations can model deployment around the operational workflow:

```text
  [ Discover ]  ---> Identify target servers across cloud and on-premises subnets.
       |
  [  Enroll  ]  ---> Issue single-use tokens; register agents without opening inbound firewall ports.
       |
  [ Observe  ]  ---> Ingest real-time CPU, memory, disk, load, and process state.
       |
  [  Assess  ]  ---> Evaluate host health and derive warning/offline statuses.
       |
  [ Approve  ]  ---> Request administrative job; enforce TOTP step-up authentication for high-impact actions.
       |
  [ Operate  ]  ---> Dispatch bounded job to target agent; execute systemctl/sc.exe operation.
       |
  [  Audit   ]  ---> Verify immutable SHA-256 audit ledger entry for compliance and reporting.
```

---

## Project maturity & roadmap

### Current release maturity

**Current Status:** Early open-source control-plane release (v0.1.0).

- **Functional Today:** Complete single-node control plane, authentication, TOTP MFA, role management, agent enrollment, telemetry heartbeat, bounded job execution (`systemctl` / `sc.exe`), and tamper-evident audit logging.
- **In Development:** Multi-node controller scalability, external database persistence, and advanced alert notification hooks.

### Technical roadmap

#### Phase 1: Persistence & High Availability
- [ ] External PostgreSQL persistence driver support.
- [ ] Multi-instance controller deployment with shared session store.
- [ ] High-throughput Redis/RabbitMQ job queue adapter.

#### Phase 2: Enterprise Identity & Governance
- [ ] OIDC / OAuth2 / SAML 2.0 Single Sign-On (SSO) integration.
- [ ] Fine-grained attribute-based access control (ABAC).
- [ ] Scheduled maintenance windows and multi-approver workflow policies.

#### Phase 3: Infrastructure & Ecosystem Expansion
- [ ] Out-of-band IPMI / Redfish physical server power management.
- [ ] Ansible playbook execution dispatcher integration.
- [ ] Prometheus metrics exporter endpoint (`/metrics`).
- [ ] NetBox CMDB bidirectional inventory synchronization.

---

## Contributing

We welcome contributions from infrastructure engineers, security researchers, and developers.

### Contribution guidelines

1. **Issues:** Before proposing major architectural changes, open a GitHub Issue to discuss design goals with maintainers.
2. **Pull Requests:** Ensure all new code includes unit tests, passes `pytest`, and compiles cleanly (`python -m py_compile`).
3. **Code Style:** Follow standard Python clean coding practices (PEP 8) and maintain explicit type annotations.
4. **Security Vulnerabilities:** Follow the private security reporting process outlined in [SECURITY.md](SECURITY.md).

---

## License

Glowhaven Helix is open-source software released under the [MIT License](LICENSE).

<div align="center">

**Glowhaven Server Platform · Glowhaven Helix**

*Controlled infrastructure operations. Unified telemetry. Proven audit trails.*

</div>
