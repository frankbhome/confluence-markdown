# CI/CD Automation Guide

This document explains how to use the automated CI/CD features implemented in CMD-23.

## Overview

The project now includes comprehensive automation for:

- **Automated PyPI Publishing**: Secure, token-free package publishing
- **Dependency Management**: Weekly automated dependency updates
- **Release Process**: Streamlined version management and publishing

## PyPI Publishing

### How It Works

When you create a GitHub release, the system automatically:

1. **Validates versions** - Ensures Git tag matches Poetry version
2. **Runs full tests** - Verifies code quality before publishing
3. **Builds package** - Creates wheel and source distributions
4. **Publishes to PyPI** - Uses trusted publishing (no API tokens needed)
5. **Verifies publication** - Confirms package is available on PyPI

### Setting Up PyPI Trusted Publishing

**One-time setup required:**

1. Go to [PyPI Trusted Publishers](https://pypi.org/manage/account/publishing/)
2. Add a new trusted publisher:
   - **Owner**: `frankbhome`
   - **Repository**: `confluence-markdown`
   - **Workflow filename**: `.github/workflows/publish-pypi.yml` (full path required)
   - **Environment**: (leave blank)

**Important**: The workflow must have proper permissions for OIDC and publishing:

```yaml
permissions:
  id-token: write    # Required for OIDC token request
  contents: read     # Required to read repository contents
  # packages: write  # Only needed if publishing to GitHub Packages
```

### Publishing a Release

```bash
# 1. Ensure you're on main branch and it's clean
git checkout main
git pull origin main

# 2. Create a new version (choose one)
make release-patch   # x.x.X (bug fixes)
make release-minor   # x.X.x (new features)
make release-major   # X.x.x (breaking changes)

# 3. Push the release
make release-push

# 4. Monitor the workflows
# - Check GitHub Actions for "Release" workflow
# - Check GitHub Actions for "Publish to PyPI" workflow
# - Verify package appears on PyPI
```

### Manual Publishing

If needed, you can trigger PyPI publishing manually:

1. Go to **Actions** → **Publish to PyPI**
2. Click **Run workflow**
3. Enter the version (e.g., `v1.2.3`)
4. Click **Run workflow**

## Dependency Management

### How Dependabot Works

- **Schedule**: Every Monday at 9:00 AM UTC
- **Python Dependencies**: Updates packages in `pyproject.toml`
- **GitHub Actions**: Updates workflow dependencies
- **Pull Requests**: Creates labeled PRs for review

### Managing Dependency Updates

1. **Review PRs**: Check automated tests pass
2. **Review changes**: Look for breaking changes in changelogs
3. **Merge**: Approve and merge when safe

### Manual Dependency Updates

```bash
# Check for outdated packages
poetry show --outdated

# Update all dependencies
poetry update

# Update specific package
poetry update package-name
```

## Repository Security

### Setting Up Branch Protection

To ensure only you can push to main and create releases:

1. **Branch Protection Rules**:
   - Go to Settings → Branches
   - Add rule for `main` branch
   - Require pull request reviews (1 required)
   - Require status checks to pass
   - Restrict pushes to administrators

2. **Tag Protection via Repository Rules** (New Method):
   - Go to Settings → Rules → Rulesets
   - Create new tag ruleset for `v*.*.*`
   - Restrict creations, updates, and deletions
   - Allow only repository administrators

### Security Features

Enable these in Settings → Security & analysis:

- ✅ **Dependency graph**
- ✅ **Dependabot alerts**
- ✅ **Dependabot security updates**
- ✅ **Secret scanning**
- ✅ **Push protection**

## Troubleshooting

### PyPI Publishing Fails

1. **Check PyPI setup**: Verify trusted publisher configuration
2. **Version mismatch**: Ensure Git tag matches Poetry version
3. **Test failures**: Fix failing tests before retrying
4. **Manual retry**: Use workflow dispatch to retry publishing

### Dependabot Issues

1. **Missing PRs**: Check Dependabot logs in repository Insights
2. **Test failures**: Review and fix failing dependency updates
3. **Too many PRs**: Adjust `open-pull-requests-limit` in config

## Best Practices

### Release Management

- Always test releases in a staging environment first
- Use semantic versioning consistently
- Write clear release notes
- Monitor PyPI publication after releases

### Dependency Management

- Review dependency update PRs promptly
- Test applications after major dependency updates
- Keep an eye on security advisories for your dependencies
- Use `poetry.lock` to ensure reproducible builds

### Security

- Regularly audit your trusted publisher settings
- Monitor PyPI download statistics for anomalies
- Keep GitHub Actions workflows updated
- Review Dependabot PRs for unexpected changes

## Monitoring

### GitHub Actions

Monitor these workflows:

- **Release workflow**: Monitors tag creation and GitHub release publication
- **PyPI workflow**: Monitors package publishing and verification
- **CI workflow**: Monitors code quality on all branches

### PyPI

Check [PyPI project page](https://pypi.org/project/confluence-markdown/) for:

- Download statistics
- Version history
- Security advisories

### Dependabot

Monitor dependency updates:

- Review dependency update PRs in the **Pull Requests** tab
- Check Dependabot logs in **Insights** → **Dependency graph** → **Dependabot**
