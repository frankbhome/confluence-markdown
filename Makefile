.PHONY: release-patch release-minor release-major release-alpha release-rc verify-release

release-patch:
	cz bump --increment patch

release-minor:
	cz bump --increment minor

release-major:
	cz bump --increment major

release-alpha:
	cz bump --prerelease alpha

release-rc:
	cz bump --prerelease rc

verify-release:
	git fetch --tags
	git describe --tags --always
