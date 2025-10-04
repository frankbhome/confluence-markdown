# ADR-001: Adopt atlassian-python-api for Confluence Integration

## Status
Accepted (2025-10-04)

## Context
Our Confluence Markdown project previously implemented a custom HTTP client for interacting with Confluence Cloud's REST API. This custom implementation required significant maintenance overhead and duplicated functionality available in well-established libraries.

## Decision
We will replace our custom Confluence API client with the `atlassian-python-api` library (version ^4.0.7).

## Rationale

### Library Evaluation Results
A comprehensive evaluation following the Dukosi Python Library Evaluation Checklist showed:

**Strengths:**
- ✅ **Security**: No known CVEs, clean dependency tree, proper token handling
- ✅ **License**: Apache 2.0 (compatible with our usage)
- ✅ **Maintenance**: Active development (1k+ stars, 200+ contributors, recent releases)
- ✅ **API Coverage**: Complete support for Confluence Cloud operations we require
- ✅ **Cloud Compatibility**: Explicit Confluence Cloud support with storage format handling
- ✅ **Testability**: Clean interfaces suitable for mocking and testing
- ✅ **Performance**: Built on requests.Session with connection pooling

**Areas Requiring Attention:**
- ⚠️ **Retry Logic**: Library delegates retry handling to consumers
- ⚠️ **Logging**: Minimal built-in logging requires our structured logging wrapper

### Implementation Strategy
To address the evaluation caveats, we implemented:

1. **Enhanced Retry/Backoff Logic**: Custom decorator with exponential backoff
2. **Preserved Structured Logging**: Maintained operation context and duration metrics
3. **Improved Testability**: Factory method pattern for better mocking support
4. **Backward Compatibility**: Same public API with camelCase aliases preserved

## Consequences

### Positive
- **Reduced Maintenance**: ~400 lines of custom HTTP logic replaced with thin wrapper
- **Better Reliability**: Leveraging battle-tested upstream implementation
- **Future-Proof**: Automatic updates and new features through library updates
- **Industry Standard**: Alignment with widely-adopted Confluence integration patterns

### Negative
- **Breaking Change**: Fundamental dependency shift (mitigated by API compatibility)
- **New Dependency**: Additional library to manage and monitor for updates

### Neutral
- **Learning Curve**: Team needs familiarity with new library internals (minimal impact)
- **Version Pinning**: Need quarterly review cycle for library updates

## Implementation Details

### Core Changes
- Replaced `src/confluence_markdown/confluence_api.py` implementation
- Added `atlassian-python-api = "^4.0.7"` dependency
- Implemented `@with_retry_and_logging` decorator for operation enhancement
- Created `_create_confluence_client()` factory method for testability

### Compatibility Guarantees
- All public methods preserved (`get_page_by_id`, `create_page`, `update_page`, etc.)
- CamelCase aliases maintained (`getPage`, `createPage`, `updatePage`)
- Same exception hierarchy and error types
- Environment variable contract unchanged
- Session attribute exposed for testing backward compatibility

### Migration Path
Existing code continues to work without changes. The breaking change designation reflects the fundamental dependency shift, not API changes.

## References
- Library Evaluation Document (2025-10-04)
- [atlassian-python-api Documentation](https://github.com/atlassian-api/atlassian-python-api)
- CMD-48: Original implementation request
- Dukosi Python Library Evaluation Checklist

## Review Date
Next review: 2026-01-04 (quarterly cycle for dependency updates)
