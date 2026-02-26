---
name: gdocs-cli
description: Apply when the user shares a Google Docs URL or asks to read/fetch a Google Doc. Use the `gdocs` CLI to convert Google Docs to markdown.
---

# Google Docs CLI Usage

Use the `gdocs` CLI to fetch Google Docs content as markdown.

## Basic Usage

```bash
# Fetch doc as markdown (clean output, no logs)
gdocs --url="<google-docs-url>" --clean

# Save to file
gdocs --url="<url>" --clean > spec.md

# Preview first 50 lines
gdocs --url="<url>" --clean | head -50
```

## Flags

- `--url` - Google Docs URL (required)
- `--clean` - Suppress logs, output only markdown (recommended)
- `--comments` - Include document comments as a `## Comments` section at the end
- `--init` - Re-authenticate if token expired

## Fetching Comments

Use `--comments` to include all comments and replies in the output:

```bash
gdocs --url="<google-docs-url>" --clean --comments
```

The comments section shows quoted text, author, date, resolved status, and replies.

> **Note:** `--comments` requires the `drive.readonly` OAuth scope. If you get a permission error, re-authenticate:
> ```bash
> rm ~/.config/gdocs-cli/token.json
> gdocs --init
> ```

## Tab Support

For docs with multiple tabs, include the `?tab=t.xxx` parameter in the URL:

```bash
# Fetch a specific tab
gdocs --url="https://docs.google.com/document/d/DOC_ID/edit?tab=t.v63b7x227gkk" --clean
```

Without a tab parameter, the first tab is fetched by default.

## When to Use

- User shares a Google Docs link and wants to discuss its contents
- Reading PRDs, specs, or documentation from Google Docs
- Converting Google Docs to markdown for processing
- Fetching comments/feedback on a doc

## Troubleshooting

If you get authentication errors:
```bash
gdocs --init
```

This will open a browser to re-authenticate with Google OAuth.
