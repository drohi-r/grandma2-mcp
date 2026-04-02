---
title: Markdown Front Matter Rules
description: Required YAML front matter fields and conventions for all .md files in this repo
version: 1.0.0
created: 2026-03-29T21:44:45Z
last_updated: 2026-03-29T21:44:45Z
---

# Markdown Front Matter Rules

All `.md` files in this repository **must** include YAML front matter (`---` fences) at the top.

## Required fields

| Field | Format | Description |
|-------|--------|-------------|
| `title` | string | Document title (matches the `# H1` heading) |
| `description` | string | One-line summary of the document's purpose |
| `version` | semver | `MAJOR.MINOR.PATCH` — bump PATCH for fixes, MINOR for new content, MAJOR for restructures |
| `created` | ISO 8601 | `YYYY-MM-DDTHH:MM:SSZ` — set once when the file is created, never changed |
| `last_updated` | ISO 8601 | `YYYY-MM-DDTHH:MM:SSZ` — update every time the file content changes |

## Rules

1. **New `.md` files** — add front matter before writing any content.
2. **Editing existing `.md` files** — update `last_updated`. Bump `version` for non-trivial changes.
3. **Do not** backfill `created` dates — use the actual date the file was created.

## Template

```yaml
---
title: Document Title
description: Brief purpose of this document
version: 1.0.0
created: YYYY-MM-DDTHH:MM:SSZ
last_updated: YYYY-MM-DDTHH:MM:SSZ
---
```
