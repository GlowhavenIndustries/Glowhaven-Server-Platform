# Glowhaven Helix

> **The server control plane built to make infrastructure operations feel like one system.**

Glowhaven Helix is a self-hosted control plane for corporate server fleets. It brings server inventory, live health, controlled operations, agent-based telemetry, enrollment, job tracking, and auditability into one operator experience.

The product is designed around a simple premise: infrastructure teams should not have to jump between a hardware console, an operating-system tool, a patch platform, an automation runner, a monitoring product, and a separate source of truth just to understand or act on one server.

## What Helix is designed to unify

Helix takes useful ideas already proven across infrastructure tooling and connects them through one operational model.

| Capability | Helix direction |
| --- | --- |
| Fleet inventory | One view of every enrolled server and its hardware and OS identity |
| Live health | CPU, memory, disk, uptime, status, and last-seen telemetry |
| Controlled operations | A bounded action catalog for reboot, shutdown, service control, diagnostics, and inventory refresh |
| Secure enrollment | Single-use enrollment tokens with expiring registration windows |
| Server agent | Small cross-platform agent that sends telemetry and executes approved actions |
| Operations queue | Track requested, running, succeeded, and failed work |
| Audit trail | Record authentication, enrollment, and operator actions |
| Self-hosting | Designed for private networks and internal infrastructure |
| API-first control | Browser UI and machine-accessible API share the same control plane |

## Why the architecture looks this way

Canonical MAAS is strong at bare-metal discovery, provisioning, hardware inventory, network configuration, and remote machine operations. https://canonical.com/maas/features

Microsoft Windows Admin Center provides browser-based Windows server and cluster administration with tools covering events, files, firewall, services, storage, virtual machines, updates, and more. https://learn.microsoft.com/en-us/windows-server/manage/windows-admin-center/use/manage-servers

Red Hat Satellite focuses on infrastructure lifecycle, provisioning, configuration, patching, compliance, and distributed management through Satellite and Capsule components. https://www.redhat.com/en/technologies/management/satellite/features

NetBox acts as a network source of truth across IPAM and data-center infrastructure data, while HashiCorp Nomad focuses on workload scheduling and multi-region orchestration. Tailscale adds device posture and least-privilege access controls around infrastructure connectivity. https://netboxlabs.com/docs/netbox/ https://www.hashicorp.com/en/products/nomad/features https://tailscale.com/docs/features/device-posture

Helix is intentionally aimed at the overlap: **one operator control plane for server identity, state, safe actions, and the workflows that sit between infrastructure inventory and day-to-day operations.**

## Current release

This repository contains a working early control-plane release with:

- FastAPI server
- SQLite persistence for the initial deployment
- Local admin authentication using scrypt password hashing
- HttpOnly session cookie and CSRF protection
- Security headers and restrictive browser policy
- Expiring, single-use server enrollment
- Per-server agent credentials stored as hashes
- Agent heartbeats and fleet telemetry
- Server inventory snapshots
- Queue-backed controlled operations
- Explicit action allowlist instead of arbitrary remote shell execution
- Service control on Linux and Windows through platform-native service managers
- Reboot and shutdown actions
- Bounded diagnostics collection
- Audit events
- Containerized deployment
- Automated security regression tests

## Quick start

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements-dev.txt

set HELIX_BOOTSTRAP_PASSWORD=replace-this-with-a-long-random-password
# PowerShell:
$env:HELIX_BOOTSTRAP_PASSWORD = "replace-this-with-a-long-random-password"

uvicorn helix.main:app --host 127.0.0.1 --port 8700
```

Open `http://127.0.0.1:8700` and sign in with the bootstrap admin account configured through `HELIX_BOOTSTRAP_ADMIN` and `HELIX_BOOTSTRAP_PASSWORD`.

For production, terminate TLS in front of Helix, set `HELIX_SECURE_COOKIES=true`, use a strong unique bootstrap password, and place the database on durable protected storage.

## Enroll a server

1. Sign in as an administrator.
2. Select **Add server**.
3. Generate the single-use enrollment token.
4. Install the agent on the target server.
5. Run the agent with the Helix controller URL and enrollment token.

Example:

```bash
python -m agent --controller https://helix.example.internal --enrollment-token <TOKEN> --name prod-web-01
```

After registration, the agent stores its per-server credential in a local state file with restricted permissions where supported by the operating system.

## Supported server actions

Helix deliberately uses a controlled action catalog. The first release supports:

- `refresh_inventory`
- `collect_diagnostics`
- `service_start`
- `service_stop`
- `service_restart`
- `reboot`
- `shutdown`

Arbitrary remote shell execution is intentionally not part of this initial control plane. An operation must exist in the explicit server-side allowlist and pass input validation before it reaches an agent.

## Security model

Helix is designed for private infrastructure and follows a defense-in-depth model:

- Passwords are stored using scrypt-derived hashes rather than plaintext.
- Browser sessions use HttpOnly, SameSite cookies.
- State-changing browser requests require a matching CSRF token.
- Server agents authenticate with per-server credentials stored as SHA-256 hashes in the control plane.
- Enrollment tokens are single-use and expire.
- Service names are constrained to a conservative character set.
- Remote operations are allowlisted rather than accepting arbitrary commands from the web UI.
- Security headers are sent by default.
- The container runs as a non-root user and drops Linux capabilities.
- Audit events are written for security-relevant operator and agent actions.

This is an engineering baseline, not a certification claim. Enterprise deployments should add TLS certificates, identity-provider integration, durable backups, centralized log shipping, and hardened infrastructure controls appropriate to their environment.

## Architecture

```text
                     +-------------------------+
                     |      Helix Web UI       |
                     +------------+------------+
                                  |
                            HTTPS / API
                                  |
                     +------------v------------+
                     |     Helix Control       |
                     |  Auth / RBAC / Jobs     |
                     |  Inventory / Audit      |
                     +------------+------------+
                                  |
                    +-------------+-------------+
                    |             |             |
             +------v------+ +----v-----+ +-----v------+
             | Server A    | | Server B | | Server C  |
             | Helix Agent | |  Agent   | |   Agent   |
             +-------------+ +----------+ +------------+
                    |             |             |
             telemetry + controlled operations
```

## Project structure

```text
Glowhaven-Helix/
├── helix/
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
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

## Tests

```bash
pytest -q
```

The security tests cover authentication, CSRF enforcement, single-use enrollment, heartbeat ingestion, fleet state, and action parameter validation.

## Roadmap

The architecture is intentionally ready for a larger commercial product. The next major layers should be implemented without weakening the current security boundary:

- PostgreSQL-backed HA control plane
- OIDC and enterprise SSO
- Fine-grained RBAC and scoped permissions
- Approval workflows for high-impact actions
- Maintenance windows and change scheduling
- Patch baselines and staged rollouts
- Configuration drift detection
- Policy enforcement and compliance views
- BMC integrations such as IPMI and Redfish
- Network and rack inventory integration
- Virtualization and cluster management
- Signed agent packages and automatic upgrade channels
- Mutual TLS between agents and control planes
- Multi-site relay or edge controllers
- Alert routing and incident workflows
- Job templates with dry-run and rollback semantics
- PostgreSQL-backed immutable audit storage

## Operating principle

Helix should continue to make the common operator workflow simpler without hiding the underlying infrastructure.

The product should feel like a **control system for serious infrastructure**, not a decorative dashboard.

Every feature should be real, observable, permissioned, testable, and documented.
