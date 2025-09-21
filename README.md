# confluence-markdown

A Python-based tool to synchronise documents between **Markdown** (in Git) and
**Confluence** pages, supporting two-way conversion and CI/CD automation.

---

## 🚀 Features

- Note: These features are planned but not yet implemented.
- Convert Markdown → Confluence (publish to pages via REST API).
- Convert Confluence → Markdown (store as version-controlled files in Git).
- Support for headings, lists, tables, code blocks.
- CLI tool `conmd` for push/pull/sync operations.
- CI/CD ready: publish approved Markdown from GitHub Actions into Confluence.

---

## 📦 Getting Started

### 1. Install dependencies

```bash
poetry install
```

### 2. Run CLI

```bash
poetry run conmd
```

### 3. Run tests

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
