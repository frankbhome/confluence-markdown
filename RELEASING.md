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
