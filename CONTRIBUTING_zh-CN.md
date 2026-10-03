# 贡献指南 (Contributing to Glowhaven Helix)

感谢您关注并打算参与 Glowhaven Helix 项目的建设！我们非常欢迎来自全球的技术人员、系统管理员、DevOps / SRE 工程师及安全研究人员（包括红帽 / Enterprise Linux 开发者社区）加入我们，共同打造安全、可信、防篡改的服务器控制台平台。

[English](CONTRIBUTING.md) | [简体中文](CONTRIBUTING_zh-CN.md)

---

## 行为准则

我们致力于营造开放、友好和包容的社区氛围。请尊重每一位社区成员，不论其背景、身份或经验水平如何。

---

## 如何参与贡献

您可以多种方式参与 Glowhaven Helix 项目：

1. **提交 Bug 报告：** 通过 [GitHub Issues](https://github.com/GlowhavenIndustries/Glowhaven-Server-Platform/issues) 反馈您遇到的问题。
2. **提出功能建议：** 为 Helix 的架构改进、新功能或系统集成提出建议。
3. **贡献代码：** 修复已知的 Bug，实现新特性，或优化已有代码结构。
4. **完善文档：** 改进安装指南、API 文档以及多语言支持（包括针对 RHEL / Rocky / Alma 等 Enterprise Linux 的部署指南）。
5. **社区交流：** 在 Issue 和 Discussion 中解答其他用户的疑问，分享部署实践。

---

## 本地开发与测试流程

### 1. 前置要求

- Python 3.12+
- Git

### 2. 初始化开发环境

```bash
# Fork 并克隆项目仓库
git clone https://github.com/YOUR_USERNAME/Glowhaven-Server-Platform.git
cd Glowhaven-Server-Platform

# 创建 Python 虚拟环境
python3 -m venv .venv
source .venv/bin/activate  # Windows 环境: .venv\Scripts\activate

# 安装开发依赖
pip install -r requirements-dev.txt
```

### 3. 运行测试套件

在提交 Pull Request 之前，请确保所有测试均已通过：

```bash
python3 -m pytest
```

同时请检查语法编译无报错：

```bash
python3 -m py_compile helix/*.py agent/*.py
```

---

## 提交 Pull Request (PR) 规范

1. **分支命名：** 使用清晰简洁的分支名称（如 `feature/rhel-selinux-docs` 或 `fix/jwt-expiration`）。
2. **代码风格：** 遵守 PEP 8 代码规范，保持明确的类型注解。
3. **测试覆盖：** 提交新功能或 Bug 修复时，请包含相应的单元测试或集成测试。
4. **提交信息：** 编写简明扼要的 Commit 描述。
5. **双语文档：** 修改文档时，建议同步更新英文 (`.md`) 与中文 (`_zh-CN.md`) 版本。

---

## 安全漏洞报告

请**不要**直接在 GitHub Issue 中公开发布安全漏洞。
请参阅 [SECURITY.md](SECURITY.md) 获取安全漏洞私密披露流程。

再次感谢您对 Glowhaven Helix 开源项目的支持！
