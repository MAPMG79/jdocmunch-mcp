# jDocMunch MCP

Token-efficient MCP server for structured documentation retrieval via section-level indexing.

## Overview

jDocMunch indexes documentation files (.md, .txt, .rst) by their heading hierarchy, assigning each section a stable ID and byte offsets for O(1) content retrieval. It complements jCodeMunch (symbol indexing for source code).

## Tools (10)

| Tool | Description |
|------|-------------|
| `index_local` | Walk local folder, parse .md/.txt, save index |
| `index_repo` | Fetch from GitHub API, parse, save index |
| `list_repos` | List all indexed doc sets |
| `get_toc` | Flat TOC for a repo (all sections, doc order) |
| `get_toc_tree` | Nested TOC tree per document |
| `get_document_outline` | Section hierarchy for one file (no content) |
| `search_sections` | Weighted search returning summaries only |
| `get_section` | Byte-range content retrieval for one section |
| `get_sections` | Batch content retrieval |
| `delete_index` | Remove a repo index |

## Installation

```bash
pip install -e .
```

## Usage

Register in `~/.claude.json`:

```json
"jdocmunch-mcp": {"type": "stdio", "command": "jdocmunch-mcp"}
```

Then in Claude Code: `index_local` a folder, then use `search_sections` + `get_section` to retrieve targeted doc content.

## Environment Variables

- `ANTHROPIC_API_KEY` — enables AI summaries (Claude Haiku)
- `GOOGLE_API_KEY` — enables AI summaries (Gemini Flash, fallback)
- `GITHUB_TOKEN` — higher rate limits for `index_repo`
- `DOC_INDEX_PATH` — override default `~/.doc-index/` storage path
- `JDOCMUNCH_SHARE_SAVINGS=0` — disable anonymous token savings telemetry
