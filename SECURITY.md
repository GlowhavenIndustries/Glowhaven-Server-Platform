# Security Policy

## Reporting a vulnerability

Please **do not open a public GitHub issue for a security vulnerability**.

Instead, submit a **private bug submission through GitHub** so the report is not exposed before a fix is available.

Use the repository's GitHub security reporting workflow:

**Repository → Security → Report a vulnerability**

If GitHub's private vulnerability reporting interface is unavailable for this repository, open a private support or security contact available through the repository's GitHub organization rather than posting sensitive details publicly.

## What to include

A useful private report should include:

- A clear description of the vulnerability
- The affected component or file
- Steps to reproduce the issue
- Expected behavior
- Actual behavior
- Security impact and realistic attack scenario
- Relevant logs, screenshots, or proof-of-concept material when safe to provide
- Any suggested mitigation you have identified

Please avoid including real passwords, API keys, session cookies, private certificates, production credentials, or other secrets in a report.

## Coordinated disclosure

Glowhaven Server Platform is an open-source infrastructure project. Security reports are reviewed with the goal of understanding the issue, reproducing it, developing a fix, and communicating the remediation responsibly.

Please allow maintainers reasonable time to investigate and address a privately reported vulnerability before publicly disclosing technical exploitation details.

## Scope

Security reports are especially useful for issues involving:

- Authentication or session handling
- Authorization or privilege boundaries
- CSRF protection
- Server enrollment
- Agent authentication
- Remote operation controls
- Unsafe command execution
- Injection vulnerabilities
- Sensitive data exposure
- Container isolation
- Dependency vulnerabilities with a meaningful exploit path

## Safe testing

Do not intentionally disrupt systems you do not own or have explicit authorization to test.

For research against Helix, use an isolated test environment and test servers under your control.

## Security expectations

Helix is an evolving infrastructure control platform. A clean test suite, security headers, allowlisted operations, and hardened defaults are valuable safeguards, but they are not a substitute for secure deployment practices.

Production operators should use:

- HTTPS with trusted certificates
- Strong unique credentials
- Enterprise identity where appropriate
- Network segmentation
- Protected database and backup storage
- Centralized audit and security monitoring
- Least-privilege infrastructure access
- Regular dependency and operating-system updates

Thank you for helping keep Helix and the infrastructure around it safer.
