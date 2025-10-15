# Development Tooling

The scripts in this directory support local authoring, validation, and publishing
workflows for the Confluence Markdown project. Each script is executable with
`poetry run python <script path>`.

## Common Options

All scripts that accept `-v/--verbose` use a shared logging formatter defined in
`scripts/common.py`. Supply `-v` (or `-vv`) for increasingly detailed output.

## `bulk_publish_docs.py`

Bulk publish mapped Markdown documents to Confluence.

```bash
poetry run python scripts/bulk_publish_docs.py --dry-run docs/overview.md docs/api.md
```

- Reads mappings from `.cmt/map.json`.
- Supports dry runs that only perform conversion.
- Emits a summary of successes, skips, and failures.

## `interactive_publish.py`

Interactively select mapped documents to publish.

```bash
poetry run python scripts/interactive_publish.py --dry-run
```

- Presents a menu of known mappings.
- Allows ad-hoc file arguments to bypass the prompt.
- Reuses the bulk publishing pipeline for consistent behaviour.

## `confluence_publisher.py`

Rich interactive publisher with credential prompts and repository-wide discovery.

```bash
poetry run python scripts/confluence_publisher.py \
  --base-url "https://your-domain.atlassian.net/wiki" \
  --space-key DOC \
  --parent-page-id 123456
```

- Guides the user through credential setup.
- Finds Markdown files under the repository while skipping common build artefacts.
- Provides progress output, error handling, and a final summary.

## `push_core_docs.py`

Publish the curated set of core project documentation.

```bash
poetry run python scripts/push_core_docs.py \
  --base-url "https://your-domain.atlassian.net/wiki" \
  --space-key DOC \
  --parent-page-id 123456
```

- Pushes README, changelog, contribution docs, and key files in `docs/`.
- Relies on `create_page_title` for consistent Confluence titles.

## `test_formatting.py`

Validate Markdown formatting against the golden corpus to catch regression in
the converter.

```bash
poetry run python scripts/test_formatting.py
```

- Compares Markdown fixtures in `tests/golden_corpus/input/` with their HTML counterparts.
- Emits unified diffs for mismatches and returns a non-zero exit code on failure.
- Supports custom fixture locations with `--input-dir` and `--expected-dir`.
