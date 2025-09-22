# confluence-markdown

[![CI (main)](https://github.com/frankbhome/confluence-markdown/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/frankbhome/confluence-markdown/actions/workflows/ci.yml?query=branch%3Amain)
[![codecov (main)](https://codecov.io/gh/frankbhome/confluence-markdown/branch/main/graph/badge.svg)](https://codecov.io/gh/frankbhome/confluence-markdown)

A Python-based tool to synchronize documents between Markdown (in Git) and
Confluence pages. The project aims to support two‑way conversion and CI/CD
automation.

---

## 🚀 Features

Currently: Pre‑alpha; APIs and CLI subject to change.

### ✅ Current

- Project scaffolding and documentation.

### 🗺️ Roadmap

- [ ] Markdown → Confluence (publish via REST API).
- [ ] Confluence → Markdown (versioned files in Git).
- [ ] Formatting coverage: headings, lists, tables, code blocks.
- [ ] CLI `conmd` for push/pull/sync operations.
- [ ] CI/CD: publish approved Markdown from GitHub Actions to Confluence.

---

## 📦 Getting Started

### Prerequisites

- Python 3.11+ recommended
- Poetry installed: [Installation Guide](https://python-poetry.org/docs/#installation)
- A Confluence Cloud/Server base URL and API token (see Atlassian docs)

### 1. Install dependencies

```bash
poetry install
```

### 2. Configure credentials (environment variables)

```bash
export CONFLUENCE_BASE_URL="https://your-domain.atlassian.net/wiki"
export CONFLUENCE_SPACE_KEY="ENG"
export CONFLUENCE_USER_EMAIL="you@example.com"
export CONFLUENCE_TOKEN="xxxx"
```

### 3. Run CLI

```bash
poetry run conmd --help
```

### 4. Run tests

```bash
poetry run pytest
```

---

## 📝 Documentation

- [Style Guide: Markdown ↔ Confluence](docs/style-guide.md)
- [Examples](docs/examples/)
  - [Basic Page](docs/examples/basic-page.md)
  - [Requirements Page](docs/examples/requirements-page.md)
  - [Design Page](docs/examples/design-page.md)

---

## 🤝 Contributing

Please see our [Contributing Guidelines](CONTRIBUTING.md).
All participants are expected to follow our [Code of Conduct](CODE_OF_CONDUCT.md).

---

## 🛡️ Security

- API tokens (Confluence, JIRA) must never be committed to the repository.
- Use environment variables (CONFLUENCE_TOKEN, JIRA_TOKEN) for local development.
- In CI/CD pipelines, store tokens in GitHub Secrets and access them
  securely at runtime.
- Rotate API tokens regularly (recommended every 90 days).
- The project follows the principle of least privilege — tokens should only
  have the minimum scope required.

---

## ⚠️ Safety

- This tool only reads/writes Markdown files and Confluence pages.
- It does not modify or delete files outside the project’s configured scope.
- Always test sync operations in a sandbox Confluence space
  before enabling on production spaces.
- Ensure requirements/design documentation is baselined before syncing, to avoid
  accidental overwrites.
- CI/CD pipelines should be configured to only publish approved Markdown
  changes from main or release branches.

---

## 📜 License

This project is licensed under the [Apache License 2.0](LICENSE).
