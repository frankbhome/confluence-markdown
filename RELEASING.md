# Releasing

## Prerequisites

Ensure you have the required tools installed:

```bash
# Install Poetry (if not already installed)
pipx install poetry

# Install project dependencies including commitizen
poetry install

# Verify commitizen is available
poetry run cz version
```

## Versioning

- Semantic Versioning: MAJOR.MINOR.PATCH
- Pre-releases: `-alpha.N`, `-rc.N`
- Tags must be `vX.Y.Z`

## Flow

1) Ensure `main` is green and up to date.

   ```bash
   git checkout main
   git pull origin main
   ```

2) Choose bump:

   ```bash
   make release-patch   # or release-minor / release-major
   # or pre-releases:
   make release-alpha
   make release-rc
   ```

3) Verify the release was created successfully:

   ```bash
   make verify-release
   git log --oneline -5
   ```

4) The automated release workflow will:
   - Build and test the package
   - Create a GitHub release with changelog
   - Automatically publish release notes to Confluence (if configured)

5) Monitor the release:
   - Check GitHub Actions for successful workflow completion
   - Verify the release appears on GitHub releases page
   - Confirm Confluence page creation (if enabled)
   - Test package installation: `pip install confluence-markdown==X.Y.Z`

6) Post-release verification:

   ```bash
   # Verify package is available on PyPI
   pip index versions confluence-markdown

   # Test fresh installation
   pip install --upgrade confluence-markdown
   python -m confluence_markdown  # Should print "confluence-markdown OK"
   ```

## Confluence Integration

The release workflow includes automatic Confluence publishing. To enable this
feature, configure the following GitHub Secrets in your repository:

### Required GitHub Secrets

- `CONFLUENCE_URL`: Your Confluence instance URL
  (e.g., `https://yourcompany.atlassian.net/wiki`)
- `CONFLUENCE_USER`: Your Confluence user email
- `CONFLUENCE_TOKEN`: Your Confluence API token
- `CONFLUENCE_SPACE`: The Confluence space key where release notes should be
  published
- `CONFLUENCE_PARENT_PAGE`: (Optional) The parent page title under which
  release pages should be created

### Setting up Confluence API Token

1. Go to [Atlassian Account Settings](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Create a new API token
3. Add the token to your GitHub repository secrets as `CONFLUENCE_TOKEN`

### Manual Release Note Publishing

You can also manually publish release notes using the publish script:

```bash
python scripts/publish_release.py v1.0.0 "Release notes content here"
```

The script will automatically:

- Convert markdown to Confluence storage format
- Create or update the release page
- Include installation instructions and GitHub links

## Troubleshooting

### Common Issues

**Release workflow fails:**

- Ensure all required secrets are configured in GitHub repository settings
- Check that the tag follows the correct format (`vX.Y.Z`)
- Verify Poetry lockfile is committed and up to date

**Confluence publishing fails:**

- Verify all required Confluence secrets are set
- Test the connection manually using the publish script
- Check Confluence space permissions for the API user

**Version bump fails:**

- Ensure working directory is clean: `git status`
- Verify you're on the main branch: `git branch`
- Check commitizen configuration: `poetry run cz info`

### Manual Recovery

If automated release fails, you can manually complete the process:

```bash
# Create GitHub release manually
gh release create v1.2.3 --title "v1.2.3" --generate-notes

# Publish to Confluence manually
poetry run python scripts/publish_release.py v1.2.3 "Release notes here"
```
