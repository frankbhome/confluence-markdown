# Security Policy

## API Token Handling

### Storage Requirements

- **Never hardcode tokens** in source code, scripts, or committed
  configuration
- **Never commit tokens to Git** (even in `.env` files) - `.gitignore` covers
  `.env`, `.venv/`, `*.secrets`, etc.
- **Use environment variables** for all sensitive credentials

### Local Development

Store tokens in environment variables:

- `CONFLUENCE_URL` - Your Confluence instance URL
- `CONFLUENCE_USER` - Your Confluence username/email
- `CONFLUENCE_TOKEN` - Your Confluence API token
- `CONFLUENCE_SPACE` - Confluence space key
- `CONFLUENCE_PARENT_PAGE` - Parent page title (optional)
- `GITHUB_REPOSITORY` - GitHub repository (optional)

Developers may use a local `.env` file managed via
[python-decouple](https://github.com/HBNetwork/python-decouple) but excluded
from Git.

### CI/CD

- Tokens must be stored in **GitHub Actions Secrets**
- Workflow jobs consume secrets at runtime via `secrets.CONFLUENCE_TOKEN`
- No secrets are logged (masking enabled by GitHub Actions)
- Secret scanning runs on every commit via gitleaks

## Authentication Model

- **Confluence**: Use Atlassian Cloud API tokens tied to user accounts with
  minimal scope
- **GitHub**: Use `GITHUB_TOKEN` for repo actions (no PATs unless necessary)
- **Principle of least privilege**: Tokens should only access what's needed
  for page read/write

## Risk Mitigation

### Accidental Secret Exposure

- **Pre-commit hooks**: gitleaks scanning with `--redact`, `--staged`,
  `--verbose` flags
- **CI scanning**: gitleaks-action runs on every push/PR
- **`.gitignore`**: Excludes `.env`, `*.secrets`, `*.key`, `*.token`,
  `.secrets/`

### CI Log Exposure

- **GitHub Actions**: Automatic secret masking in logs
- **Gitleaks**: Redacted output prevents secret logging

### Token Security

- **Rotation**: Rotate API tokens every 90 days
- **Cleanup**: Remove/revoke unused tokens immediately
- **Access Review**: Review who has access to secrets in GitHub repo settings
- **Encryption**: Use HTTPS/TLS only for all API communications

## Compliance

- **Requirement**: "The system shall protect API credentials"
- **Implementation**: API tokens stored in secrets, never in repo; credentials
  injected at runtime
- **Verification**: Pre-commit hooks and CI scanning prevent accidental
  exposure

## Reporting Security Issues

Please report security vulnerabilities by creating a private security advisory
in this repository.
