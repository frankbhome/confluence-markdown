# Copyright (c) 2025 Francis Bain
# SPDX-License-Identifier: Apache-2.0

"""Main entry point for the confluence-markdown tool."""

import sys

from .cli import main as cli_main


def main() -> None:
    """Main entry point for the confluence-markdown tool."""
    sys.exit(cli_main())


if __name__ == "__main__":
    main()
