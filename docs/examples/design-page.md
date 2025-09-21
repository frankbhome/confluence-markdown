---
title: "Design – Conversion Pipeline"
confluence-page-id: 123458
jira-epic: CMD-50
---

# Design – Conversion Pipeline

This page describes the design approach for the Markdown ↔ Confluence
conversion pipeline.

## Architecture Overview

- Modules:
  - `parser`: handle Markdown parsing
  - `converter`: map Markdown → Confluence elements
  - `api`: handle REST calls
- CLI (`conmd`) invokes `push` and `pull` commands.

## Sequence Diagram

<!-- confluence-macro:drawio -->
(diagram goes here)
<!-- /confluence-macro -->

## Data Flow

1. Read Markdown from Git repo.
2. Convert to Confluence format.
3. Push via REST API.
4. Store Confluence page ID in metadata.

## Error Handling

- Authentication errors → abort with exit code 1.
- Conversion errors → log and skip unsupported macros.
