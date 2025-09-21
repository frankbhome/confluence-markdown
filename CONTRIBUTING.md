# Contributing to Confluence-Markdown

Thank you for your interest in contributing! 🎉
This project is licensed under the **Apache License 2.0** and welcomes
contributions from the community.

---

## 📦 Getting Started

1. **Fork & clone the repository**

   ```bash
   git clone https://github.com/<your-fork>/confluence-markdown.git
   cd confluence-markdown
   ```

2. **Set up the Poetry environment**

   ```bash
   poetry install
   poetry run pre-commit install
   ```

3. **Verify your setup**

   ```bash
   poetry run conmd
   poetry run pytest
   ```

---

## 📝 Coding Standards

- **Language**: Python 3.12+
- **Formatting**: Black (line length 100)
- **Linting**: Ruff
- **Typing**: Mypy (strict mode)
- **YAML**: yamllint

Run all checks locally:

```bash
poetry run pre-commit run --all-files
```

---

## 📂 Project Structure

```text
src/confluence_markdown/   # Source code
tests/                     # Unit and integration tests
.github/workflows/         # CI/CD workflows
docs/                      # Style guide & examples
```

Helpful docs:

- Style Guide: `docs/style-guide.md`
- Examples: `docs/examples/` (basic page, requirements page, design page)

---

## 🔀 Git Workflow

1. Create a feature branch:

   ```bash
   git checkout -b feature/short-description
   ```

2. Follow **Conventional Commits**:
   - `feat:` new feature
   - `fix:` bug fix
   - `chore:` maintenance / tooling
   - `test:` tests
   - `docs:` documentation

   Example:

   ```text
   feat: add table conversion support
   ```

3. Push and open a Pull Request to `main`.

---

## ✅ Testing

- Add/modify tests for all code changes.
- Run:

  ```bash
  poetry run pytest --cov=confluence_markdown --cov-report=term-missing
  ```

- Target coverage: **≥80%** (green). PRs with lower coverage may be
  challenged unless justified.

---

## 🚀 Release Process

Releases follow **Semantic Versioning** and are managed with **Commitizen**.

Maintainers cut releases:

```bash
poetry run cz bump --increment [patch|minor|major]
git push --follow-tags
```

GitHub Actions builds and attaches artifacts (wheel + sdist) to the GitHub
Release.

---

## 🛡️ Code of Conduct

All contributors are expected to follow our **Code of Conduct**
(Contributor Covenant 2.1).
Reports can be made via
[**GitHub's Report Abuse form**](https://github.com/contact/report-abuse).

---

## 🔒 Security

- **Never** commit secrets or API tokens.
- Use environment variables locally (e.g., `CONFLUENCE_API_TOKEN`,
  `JIRA_API_TOKEN`).
- In CI, store secrets in **GitHub Actions Secrets** and consume at runtime.
- Prefer least-privilege tokens and rotate regularly (e.g., every 90 days).

---

## ⚠️ Safety

- Test sync operations in a **sandbox Confluence space** before production.
- CI pipelines should only publish **approved** Markdown from `main` or
  release branches.
- Round-trip conversions should be covered by regression tests where feasible.

---

## 🙏 Getting Help

- Open a **GitHub Issue** for bugs and feature requests.
- Check Confluence for requirements and design documentation.
- For general questions, start a **GitHub Discussion** or open a **draft PR**.

---

Thanks again for contributing! 💙
