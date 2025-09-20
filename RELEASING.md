# Releasing

## Versioning

- Semantic Versioning: MAJOR.MINOR.PATCH
- Pre-releases: `-alpha.N`, `-rc.N`
- Tags must be `vX.Y.Z`

## Flow

1) Ensure `main` is green and up to date.
2) Choose bump:

   ```bash
   make release-patch   # or release-minor / release-major
   # or pre-releases:
   make release-alpha
   make release-rc
   ```

3) The automated release workflow will:
   - Build and test the package
   - Create a GitHub release with changelog
   - Automatically publish release notes to Confluence (if configured)

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
