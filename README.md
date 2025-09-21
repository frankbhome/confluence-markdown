# confluence-markdown

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
export CONFLUENCE_API_TOKEN="xxxx"
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

## 📜 License

This project is licensed under the [Apache License 2.0](LICENSE).
