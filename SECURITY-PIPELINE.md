# Enhanced Security Pipeline

## Implementation Summary

This implementation adds comprehensive security automation to confluence-markdown
through enhanced GitHub Actions workflows.

## Key Features

✅ **Vulnerability Scanning** - pip-audit with CycloneDX SBOM generation
✅ **License Compliance** - Automated detection of prohibited licenses
✅ **SBOM Generation** - Industry-standard dependency documentation
✅ **Security Gates** - Pipeline failures for critical security issues
✅ **Secret Detection** - Enhanced gitleaks configuration
✅ **Artifact Management** - 1-year retention for compliance documentation

## Files Added

- `.github/workflows/security-pipeline.yml` - Enhanced security pipeline
- `.gitleaks.toml` - Secret scanning configuration

## Pipeline Jobs

1. **vulnerability-scan** - Scans for CVEs, fails on critical issues with fixes
2. **license-scan** - Blocks GPL/AGPL/LGPL/SSPL licenses
3. **sbom-generation** - Creates CycloneDX SBOM and dependency reports
4. **security-gate** - Validates all security scans
5. **collect-artifacts** - Bundles reports with 1-year retention

## Triggers

- Pull requests to main
- Pushes to main/develop
- Weekly scheduled scans (Sundays 2 AM UTC)

## Failure Conditions

The pipeline will FAIL on:

- Critical/High CVEs with available fixes
- Dependencies with copyleft licenses (GPL, AGPL, LGPL, SSPL)
- Secrets detected in commits

## Usage

The security pipeline runs automatically alongside existing CI. Artifacts are
available in GitHub Actions for download and review.

## Benefits

- **Continuous Security Monitoring** - Automated vulnerability detection
- **License Compliance** - Maintains Apache-2.0 compatibility
- **Supply Chain Transparency** - Complete SBOM generation
- **Audit Trail** - Long-term artifact retention for compliance

---

**Implementation Date**: October 4, 2025
**Version**: 1.0.0
**Commit**: edb5bd1
