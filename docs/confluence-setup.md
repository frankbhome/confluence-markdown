# Confluence Integration Setup

This document explains how to set up the Confluence integration for automated
release note publishing.

## Prerequisites

1. **Confluence API Token**: Generate an API token from your Atlassian account
2. **Confluence Space**: Access to a Confluence space where release notes will
   be published
3. **Python Dependencies**: Install required packages with `poetry install`

## Configuration

### 1. Environment Variables

Copy the example environment file and configure your settings:

```bash
cp .env.example .env
```

Edit `.env` with your actual values:

```bash
# Confluence base URL (without trailing slash)
CONFLUENCE_URL=https://your-domain.atlassian.net/wiki

# Confluence API credentials
CONFLUENCE_USER=your-email@company.com
CONFLUENCE_TOKEN=your_api_token_here

# Confluence space and page configuration
CONFLUENCE_SPACE=PROJ
CONFLUENCE_PARENT_PAGE=Release Notes

# GitHub configuration (for automated releases)
GITHUB_TOKEN=your_github_token_here
GITHUB_REPOSITORY=owner/repo-name
```

### 2. Generate Confluence API Token

1. Go to <https://id.atlassian.com/manage-profile/security/api-tokens>
2. Click "Create API token"
3. Give it a label like "Release Notes Automation"
4. Copy the generated token to your `.env` file

### 3. Generate GitHub Personal Access Token

1. Go to <https://github.com/settings/tokens>
2. Click "Generate new token" → "Generate new token (classic)"
3. Give it a name like "Confluence Release Integration"
4. Select scopes: `repo` and `workflow`
5. Set expiration (recommended: 90 days)
6. Click "Generate token" and copy it immediately

### 4. Find Your Confluence Space

1. Navigate to your Confluence space
2. The space key is shown in the URL: `https://domain.atlassian.net/wiki/spaces/PROJ/`
3. In this example, `PROJ` is the space key

## Usage

### Manual Publishing

Run the script manually to publish release notes:

```bash
# Using poetry
poetry run python scripts/publish_release.py

# Or directly with python
python scripts/publish_release.py
```

### Automated GitHub Actions

The script is designed to work with GitHub Actions. Add this to your release workflow:

```yaml
- name: Publish to Confluence
  env:
    CONFLUENCE_URL: ${{ secrets.CONFLUENCE_URL }}
    CONFLUENCE_USER: ${{ secrets.CONFLUENCE_USER }}
    CONFLUENCE_TOKEN: ${{ secrets.CONFLUENCE_TOKEN }}
    CONFLUENCE_SPACE: ${{ secrets.CONFLUENCE_SPACE }}
    CONFLUENCE_PARENT_PAGE: ${{ secrets.CONFLUENCE_PARENT_PAGE }}
  run: poetry run python scripts/publish_release.py
```

## Features

- **Automatic Page Creation**: Creates new pages for each release
- **Markdown Conversion**: Converts GitHub markdown to Confluence storage format
- **Parent Page Support**: Organizes releases under a parent page
- **Duplicate Detection**: Avoids creating duplicate pages for the same release
- **Error Handling**: Comprehensive error reporting and logging

## Troubleshooting

### Permission Issues

Ensure your Confluence user has:

- Space permissions to create and edit pages
- Access to the target space
- Valid API token that hasn't expired

### Authentication Errors

- Verify your username and API token are correct
- Check that the Confluence URL is formatted correctly (no trailing slash)
- Ensure you're using an API token, not your account password

### Page Creation Failures

- Verify the space key exists and you have access
- Check that the parent page exists (if specified)
- Ensure page titles don't conflict with existing pages

## Security Notes

- **Never commit `.env` files to version control** - they contain sensitive credentials
- **Local development**: Use `.env` files (already excluded in .gitignore)
- **Production/CI**: Store sensitive values in GitHub Secrets for CI/CD
- **API tokens**: Regularly rotate API tokens (recommended every 90 days)
- **Permissions**: Use principle of least privilege for Confluence permissions
- **Token scope**: Confluence API tokens inherit user permissions - use dedicated
  service accounts when possible
