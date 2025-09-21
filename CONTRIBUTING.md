# Contributing to Confluence-Markdown

Thank you for your interest in contributing! 🎉
This project is licensed under the **Apache License 2.0** and welcomes
contributions from the community.
See the full terms in [LICENSE](./LICENSE).

---

## 📦 Getting Started

1. **Fork & clone the repository**

   ```bash
   git clone https://github.com/<your-fork>/confluence-markdown.git
   cd confluence-markdown
   git remote add upstream https://github.com/frankbhome/confluence-markdown.git
   git fetch upstream
   ```

2. **Set up the Poetry environment**

   ```bash
   poetry install
   poetry run pre-commit install
   # Install commit message validation (Conventional Commits enforcement):
   poetry run pre-commit install --hook-type commit-msg
   ```

3. **Verify your setup**

   ```bash
   poetry run conmd
   poetry run pytest
   ```

---

## 📝 Coding Standards

- **Language**: Python 3.12+
- **Formatting**: Ruff (line length 100) - single formatter
- **Linting**: Ruff
- **Typing**: Mypy (strict mode)
- **YAML**: yamllint

**Note**: Ruff handles both linting and formatting. Configure line-length = 100
in pyproject.toml under [tool.ruff] to maintain consistency.

Run all checks locally:

```bash
poetry run pre-commit run --all-files
```

Common one-offs:

```bash
poetry run ruff check --fix .
poetry run ruff format .
poetry run mypy .
poetry run yamllint .
```

Configs are in pyproject.toml (Ruff/Mypy) and .pre-commit-config.yaml.
Please keep them in sync.

---

## 📂 Project Structure

```text
src/confluence_markdown/   # Source code
tests/                     # Unit and integration tests
.github/workflows/         # CI/CD workflows
docs/                      # Style guide & examples
```

Helpful docs:

- Style Guide: [`docs/style-guide.md`](./docs/style-guide.md)
- Examples: [`docs/examples/`](./docs/examples/) (basic page, requirements page,
  design page)

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
   - `refactor:` code change that neither fixes a bug nor adds a feature
   - `perf:` performance improvements
   - `build:` build system or external deps
   - `ci:` CI configuration and scripts
   - `revert:` reverts a previous commit

   See: [Conventional Commits Specification](https://www.conventionalcommits.org)

   Tips:
   - Use scopes when helpful, e.g., `feat(cli): ...`, `fix(sync): ...`
   - Breaking changes: `feat!: ...` and include `BREAKING CHANGE:` footer
   - Reference issues: `Closes #123` or JIRA keys when applicable (e.g., `CMD-34`)

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
  poetry run pytest --cov=confluence_markdown --cov-report=term-missing --cov-fail-under=80
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

GitHub Actions (see [.github/workflows/release.yml](./.github/workflows/release.yml))
builds and attaches artifacts (wheel + sdist) to the GitHub Release.

**Note**: Currently, packages are distributed via GitHub Releases only.
PyPI publishing is not configured. If PyPI distribution is needed in the future,
it would require adding PyPI tokens to GitHub Secrets and updating the release
workflow with publishing steps.

---

## 🛡️ Code of Conduct

All contributors are expected to follow our **[Code of Conduct](./CODE_OF_CONDUCT.md)**
(Contributor Covenant 2.1).
Reports can be made via [GitHub's Report Abuse form](https://github.com/contact/report-abuse)
or by contacting the project maintainers directly through GitHub Issues.

---

## 🔒 Security

- **Never** commit secrets or API tokens.
- Use environment variables locally (e.g., `CONFLUENCE_API_TOKEN`,
  `JIRA_API_TOKEN`).
- In CI, store secrets in **GitHub Actions Secrets** and consume at runtime.
- Prefer least-privilege tokens and rotate regularly (e.g., every 90 days).
- Enable secret scanning:
  - Locally via pre-commit (e.g., gitleaks or detect-secrets)
  - In CI via a dedicated job that fails on findings

Example (pre-commit):

```yaml
- repo: https://github.com/gitleaks/gitleaks
  rev: v8.18.4
  hooks:
    - id: gitleaks
```

---

## ⚠️ Safety

- Test sync operations in a **sandbox Confluence space** before production.
- CI pipelines should only publish **approved** Markdown from `main` or
  release branches.
- Round-trip conversions should be covered by regression tests where feasible.

---

## 🙏 Getting Help

- Open a **GitHub Issue** for bugs and feature requests.
- Use the provided issue templates for better triage.
- Check Confluence for requirements and design documentation.
- For general questions, start a **GitHub Discussion** (if enabled) or open a
  **draft PR**.

---

Thanks again for contributing! 💙
