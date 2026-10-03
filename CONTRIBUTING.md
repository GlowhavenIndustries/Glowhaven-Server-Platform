# Contributing to Glowhaven Helix

Thank you for your interest in contributing to Glowhaven Helix! We welcome developers, system administrators, DevOps engineers, and security researchers from around the world to join us in building a unified, safe, and tamper-evident server control plane.

[English](CONTRIBUTING.md) | [简体中文](CONTRIBUTING_zh-CN.md)

---

## Code of Conduct

We are committed to providing an open, welcoming, and safe environment for everyone. Please treat all contributors with respect and courtesy regardless of background, identity, or experience level.

---

## How You Can Contribute

There are many ways to contribute to Glowhaven Helix:

1. **Reporting Bugs:** File detailed bug reports via [GitHub Issues](https://github.com/GlowhavenIndustries/Glowhaven-Server-Platform/issues).
2. **Suggesting Features:** Propose new capabilities, architecture improvements, or integrations.
3. **Submitting Code:** Fix issues, implement features, or optimize existing components.
4. **Improving Documentation:** Enhance installation guides, API docs, translations (including Enterprise Linux / RHEL guides).
5. **Community Engagement:** Answer questions, share deployment experiences, and participate in discussions.

---

## Development & Testing Workflow

### 1. Prerequisites

- Python 3.12+
- Git

### 2. Setting Up Your Development Environment

```bash
# Fork & clone the repository
git clone https://github.com/YOUR_USERNAME/Glowhaven-Server-Platform.git
cd Glowhaven-Server-Platform

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt
```

### 3. Running Tests

Before submitting a pull request, make sure all tests pass:

```bash
python3 -m pytest
```

Verify Python syntax across files:

```bash
python3 -m py_compile helix/*.py agent/*.py
```

---

## Submitting Pull Requests (PRs)

1. **Branch Naming:** Use clear, descriptive branch names (e.g., `feature/rhel-selinux-docs` or `fix/jwt-expiration`).
2. **Code Style:** Follow PEP 8 guidelines and maintain explicit type annotations in Python code.
3. **Test Coverage:** Include tests for any new features or bug fixes.
4. **Commit Messages:** Write concise, meaningful commit messages.
5. **Bilingual Documentation:** If updating documentation, consider updating both English and Simplified Chinese (`_zh-CN.md`) versions.

---

## Security Vulnerabilities

Please **do not** submit public GitHub issues for security vulnerabilities.
Refer to [SECURITY.md](SECURITY.md) for full submission guidelines and private disclosure procedures.

Thank you for helping build a safer server control platform!
