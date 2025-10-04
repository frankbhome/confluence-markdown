# Changelog

All notable changes will be documented here.
This project adheres to [Semantic Versioning](https://semver.org).

## [Unreleased]

### Changed

- **BREAKING**: Refactored Confluence API client to use
  `atlassian-python-api` library (CMD-48)
  - Replaced custom HTTP client implementation with upstream library
  - Maintains same public API for backward compatibility
  - Improved error handling and retry logic through library defaults
  - Better integration with Confluence Cloud REST API
  - Reduced maintenance overhead by using well-maintained upstream library
- **Dependencies**: Added `atlassian-python-api ^4.0.7` as core dependency
- **Performance**: Leverages library's built-in connection pooling and
  session management

### Migration Notes

- **Environment Variables**: No changes required - same `CMT_CONF_BASE_URL`,
  `CMT_CONF_EMAIL`, `CMT_CONF_TOKEN`
- **API Compatibility**: All existing method signatures preserved
- **Error Types**: Same exception hierarchy maintained (`AuthError`,
  `NotFoundError`, etc.)
- **Rollback**: If issues occur, previous custom implementation preserved
  in `confluence_api_old.py`

## v0.2.0 (2025-09-20)

### Added

- **Confluence API Integration**: Complete automation for publishing GitHub
  release notes to Confluence
  - Automatic conversion from GitHub Markdown to Confluence storage format
  - Support for headers, lists, links, code blocks, and rich formatting
  - Configurable parent page organization for release notes
  - Intelligent duplicate detection and page updates
- **Security & Configuration Management**:
  - Environment-based authentication using Confluence API tokens
  - Secure credential handling with python-decouple integration
  - Comprehensive .env.example template with all required variables
- **Development Infrastructure**:
  - Pre-commit hooks with black, ruff, mypy, and yamllint
  - EditorConfig for consistent formatting across environments
  - Enhanced VS Code settings for Python development
  - Git attributes for proper line ending handling
- **Documentation & Setup**:
  - Complete Confluence integration setup guide
  - GitHub Personal Access Token generation instructions
  - Security best practices and troubleshooting guides
  - Automated GitHub Actions workflow examples
- **API Dependencies**: Added requests (^2.32.5) and python-decouple (^3.8)

### Changed

- **Project Structure**: Enhanced for production-ready Confluence integration
- **Error Handling**: Comprehensive validation and user-friendly error messages
- **Code Quality**: Applied consistent formatting and type annotations throughout
- **Configuration**: Standardized environment variable names (CONFLUENCE_USER)

### Fixed

- Environment variable naming consistency across all files and documentation
- Code formatting applied via Black for consistent style
- Enhanced type safety with proper annotations

## v0.1.2 (2025-09-20)

### Changed

- Resolved merge conflicts from origin/main integration
- Fixed YAML formatting issues in workflow files and pre-commit config
- Improved code quality with proper type annotations
- Enhanced documentation formatting with markdownlint compliance

## v0.1.1 (2025-09-18)

### Added

- Pre-commit configuration with Black formatter
- CI/CD pipeline improvements

### Changed

- Switched to Poetry for dependency management
- Updated to Python 3.12
- Fixed package mapping for proper distribution
- Applied code formatting with Black

## v0.1.0 (2025-09-18)

### Added

- Initial project structure
- Basic package scaffolding with `confluence_markdown` module
- Smoke test functionality to verify package installation
- Apache 2.0 license
- Basic README and project documentation
