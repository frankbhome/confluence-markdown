<!--
Copyright (c) 2025 Francis Bain
SPDX-License-Identifier: Apache-2.0
-->

# Development Guide

This guide covers development setup, processes, and standards for the
confluence-markdown project.

## Quick Start

```bash
# Clone and setup
git clone https://github.com/frankbhome/confluence-markdown.git
cd confluence-markdown

# Install dependencies with Poetry
poetry install

# Install pre-commit hooks
poetry run pre-commit install --hook-type pre-commit --hook-type commit-msg

# Run tests
poetry run pytest

# Run the package
poetry run python -m confluence_markdown
```

## Development Environment

### Requirements

- **Python**: 3.9+ (3.12+ recommended)
- **Poetry**: Latest version for dependency management
- **Git**: For version control with conventional commits

### Setup

1. **Install Poetry**: [Poetry Installation Guide](https://python-poetry.org/docs/#installation)

2. **Clone and Install**:

   ```bash
   git clone https://github.com/frankbhome/confluence-markdown.git
   cd confluence-markdown
   poetry install
   ```

3. **Configure Pre-commit**:

   ```bash
   poetry run pre-commit install --hook-type pre-commit --hook-type commit-msg
   ```

4. **Verify Setup**:

   ```bash
   poetry run pytest
   poetry run python -m confluence_markdown
   ```

## Development Workflow

### Branch Strategy

- **main**: Production-ready code
- **feature/CMD-XX**: Feature branches for JIRA tickets
- **hotfix/**: Emergency fixes for production issues

### Commit Standards

We use [Conventional Commits](https://www.conventionalcommits.org/) enforced by Commitizen:

```bash
# Good commit messages
feat(auth): add Confluence OAuth support
fix(api): handle timeout errors gracefully
docs(readme): update installation instructions
test(units): add round-trip conversion tests

# Commitizen will guide you
poetry run cz commit
```

### Code Quality Standards

#### Formatting & Linting

- **Black**: Code formatting (line length 100)
- **Ruff**: Linting with PEP8 + selected rulesets
- **Mypy**: Type checking in strict mode

```bash
# Manual runs (pre-commit runs these automatically)
poetry run ruff check .
poetry run ruff format .
poetry run mypy src/
```

#### Pre-commit Hooks

All commits must pass:

- ✅ **Ruff**: Linting
- ✅ **Ruff Format**: Code formatting
- ✅ **Gitleaks**: Secret detection
- ✅ **End-of-file**: Proper file endings
- ✅ **Trailing whitespace**: Clean whitespace
- ✅ **YAML**: Valid YAML syntax
- ✅ **Commitizen**: Conventional commit messages

### Testing

#### Running Tests

```bash
# All tests with coverage
poetry run pytest --cov=src --cov-report=html --cov-report=term

# Specific test files
poetry run pytest tests/test_smoke.py -v

# Watch mode for development
poetry run pytest --cov=src --cov-report=term --tb=short -x
```

#### Test Structure

- **Unit tests**: `tests/test_*.py`
- **Smoke tests**: `tests/test_smoke.py` (CLI and import verification)
- **Integration tests**: `tests/test_confluence_publisher.py`

#### Coverage Requirements

- **Target**: ≥80% line coverage (currently at 95%)
- **Branch coverage**: Enabled and tracked
- **Reports**: Generated in `htmlcov/` and CI artifacts

### Type Checking

```bash
# Run mypy type checking
poetry run mypy src/

# Check specific files
poetry run mypy src/confluence_markdown/__main__.py
```

### Documentation

#### Docstring Standards

```python
def example_function(param: str) -> bool:
    """Brief description of what the function does.

    Args:
        param: Description of the parameter.

    Returns:
        Description of the return value.

    Raises:
        ValueError: When param is invalid.
    """
```

#### README Updates

Keep `README.md` current with:

- Installation instructions
- Basic usage examples
- Feature overview
- Contribution guidelines

## Release Process

### Versioning

We use [Semantic Versioning](https://semver.org/) with Commitizen:

```bash
# Automated version bumps based on commits
poetry run cz bump --check-consistency

# Manual version specification
poetry run cz bump --increment PATCH  # 1.0.0 -> 1.0.1
poetry run cz bump --increment MINOR  # 1.0.0 -> 1.1.0
poetry run cz bump --increment MAJOR  # 1.0.0 -> 2.0.0
```

### Release Workflow

1. **Prepare Release**:

   ```bash
   git checkout main
   git pull origin main
   poetry run cz bump
   ```

2. **Create GitHub Release**:
   - CI/CD automatically triggers on tag push
   - PyPI publication via trusted publishing
   - GitHub Release with artifacts

3. **Verify Publication**:
   - Check [PyPI package page](https://pypi.org/project/confluence-markdown/)
   - Verify GitHub Release artifacts
   - Test installation: `pip install confluence-markdown`

## Configuration

### Environment Variables

For Confluence integration:

```bash
# Required for Confluence operations
export CONFLUENCE_URL="https://your-org.atlassian.net/wiki"
export CONFLUENCE_USER="your-email@example.com"
export CONFLUENCE_TOKEN="your-api-token"
export CONFLUENCE_SPACE="SPACE_KEY"

# Optional
export CONFLUENCE_PARENT_PAGE="Parent Page Name"
```

### Poetry Configuration

The project uses Poetry with these key configurations:

```toml
# pyproject.toml highlights
[tool.poetry]
python = ">=3.9,<4.0"  # Python version range

[tool.ruff]
line-length = 100      # Code formatting
target-version = "py39" # Minimum Python version

[tool.commitizen]
name = "cz_conventional_commits"  # Conventional commits
```

## CI/CD Pipeline

### GitHub Actions

- **CI** (on PRs/pushes): Linting, type checking, tests, coverage
- **CD** (on releases): Build, publish to PyPI, create GitHub release
- **Dependencies**: Weekly Dependabot updates

### Local CI Simulation

```bash
# Run the same checks as CI
poetry run pre-commit run --all-files
poetry run pytest --cov=src --cov-report=term
poetry run mypy src/
```

## Troubleshooting

### Common Issues

#### **Poetry Issues**

```bash
# Clear cache and reinstall
poetry cache clear pypi --all
poetry install --sync
```

#### **Pre-commit Issues**

```bash
# Reinstall hooks
poetry run pre-commit clean
poetry run pre-commit install --hook-type pre-commit --hook-type commit-msg
```

#### **Test Failures**

```bash
# Verbose output for debugging
poetry run pytest -vvv --tb=long
```

#### **Import Errors**

```bash
# Check PYTHONPATH and package installation
poetry run python -c "import confluence_markdown; print('OK')"
```

### Getting Help

1. **Check existing issues**: [GitHub Issues](https://github.com/frankbhome/confluence-markdown/issues)
2. **Review documentation**: README.md, CONTRIBUTING.md
3. **Run diagnostics**: `poetry run pytest tests/test_smoke.py -v`

## Contributing

### Code Contributions

1. **Fork** the repository
2. **Create feature branch**: `git checkout -b feature/your-feature`
3. **Follow standards**: Use conventional commits, maintain test coverage
4. **Submit PR**: With clear description and tests

### Documentation

- Update relevant documentation for new features
- Ensure examples work and are current
- Follow the existing documentation style

### Bug Reports

Include in bug reports:

- Python version: `python --version`
- Package version: `poetry run python -c "import confluence_markdown; print(confluence_markdown.__version__)"`
- Environment details
- Reproduction steps
- Expected vs actual behavior

## Architecture

### Package Structure

```text
confluence-markdown/
├── src/confluence_markdown/     # Main package
│   ├── __init__.py             # Package initialization
│   └── __main__.py             # CLI entry point
├── tests/                      # Test suite
│   ├── test_smoke.py           # Basic functionality tests
│   └── test_confluence_publisher.py  # Integration tests
├── scripts/                    # Utility scripts
│   └── publish_release.py      # Release automation
├── docs/                       # Documentation
└── .github/workflows/          # CI/CD pipelines
```

### Extension Points

The project is designed for extensibility:

- **Content conversion**: Extend markdown processing
- **API integration**: Add other platforms beyond Confluence
- **CLI commands**: Add new command-line functionality
- **Publishing targets**: Support additional documentation platforms

## License & Compliance

This project follows strict compliance standards:

- **License**: Apache-2.0
- **Copyright**: All source files include proper headers
- **Dependencies**: Tracked in NOTICE file
- **Security**: Secret scanning, dependency updates
- **Standards**: PEP8, type hints, comprehensive testing

For compliance details, see the main project documentation.
