## Cut documentation-reading token costs by up to **98%**

Most AI agents explore documentation the expensive way:
open entire files → skim hundreds of irrelevant paragraphs → repeat.

**jDocMunch indexes a documentation set once and lets agents retrieve only the exact sections they need** — with byte-level precision.

| Task                          | Traditional approach | With jDocMunch  |
| ----------------------------- | -------------------- | --------------- |
| Find a configuration section  | ~12,000 tokens       | ~400 tokens     |
| Browse documentation structure| ~40,000 tokens       | ~800 tokens     |
| Explore a full doc set        | ~100,000 tokens      | ~2k tokens      |

Index once. Query cheaply forever.
Precision context beats brute-force context.

---

# jDocMunch MCP

### Structured documentation retrieval for serious AI agents

![License](https://img.shields.io/badge/license-dual--use-blue)
![MCP](https://img.shields.io/badge/MCP-compatible-purple)
![Local-first](https://img.shields.io/badge/local--first-yes-brightgreen)
[![PyPI version](https://img.shields.io/pypi/v/jdocmunch-mcp)](https://pypi.org/project/jdocmunch-mcp/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/jdocmunch-mcp)](https://pypi.org/project/jdocmunch-mcp/)

**Stop dumping documentation files into context windows. Start retrieving exactly what the agent needs.**

jDocMunch indexes documentation files once by their heading hierarchy, then allows MCP-compatible agents (Claude Desktop, VS Code, Google Antigravity, and others) to **discover and retrieve content by section** instead of brute-reading files.

Every section stores:
- Title and heading level
- One-line summary
- Tags and references extracted from content
- SHA-256 content hash (drift detection)
- Byte offsets into the original file

Full content is retrieved on demand using O(1) byte-offset seeking.

---

## How it works

1. **Discovery** — GitHub API or local directory walk
2. **Security filtering** — traversal protection, secret exclusion, binary detection
3. **Parsing** — heading-based section splitting (ATX, setext, MDX-aware)
4. **Hierarchy wiring** — parent/child relationships established
5. **Summarization** — heading text → AI batch → title fallback
6. **Storage** — JSON index + raw files stored locally (`~/.doc-index/`)
7. **Retrieval** — O(1) byte-offset seeking via stable section IDs

### Stable Section IDs

```
{repo}::{doc_path}::{slug}#{level}
```

Examples:

- `owner/repo::docs/install.md::installation#1`
- `owner/repo::README.md::quick-start#2`
- `local/myproject::guide.md::configuration#2`

IDs remain stable across re-indexing when the file path, heading text, and heading level are unchanged.

---

## Installation

### Prerequisites

- Python 3.10+
- pip

### Install

```bash
pip install jdocmunch-mcp
```

Verify:

```bash
jdocmunch-mcp --help
```

---

## Configure MCP Client

> **PATH note:** MCP clients often run with a limited environment where `jdocmunch-mcp` may not be found even if it works in your terminal. Using [`uvx`](https://github.com/astral-sh/uv) is the recommended approach — it resolves the package on demand without requiring anything to be on your system PATH. If you prefer `pip install`, use the absolute path to the executable instead:
> - **Linux:** `/home/<username>/.local/bin/jdocmunch-mcp`
> - **macOS:** `/Users/<username>/.local/bin/jdocmunch-mcp`
> - **Windows:** `C:\\Users\\<username>\\AppData\\Roaming\\Python\\Python3xx\\Scripts\\jdocmunch-mcp.exe`

### Claude Desktop / Claude Code

Config file location:

| OS      | Path |
| ------- | ---- |
| macOS   | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Linux   | `~/.config/claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |

**Minimal config (no API keys needed):**

```json
{
  "mcpServers": {
    "jdocmunch": {
      "command": "uvx",
      "args": ["jdocmunch-mcp"]
    }
  }
}
```

**With optional AI summaries and GitHub auth:**

```json
{
  "mcpServers": {
    "jdocmunch": {
      "command": "uvx",
      "args": ["jdocmunch-mcp"],
      "env": {
        "GITHUB_TOKEN": "ghp_...",
        "ANTHROPIC_API_KEY": "sk-ant-..."
      }
    }
  }
}
```

After saving the config, **restart Claude Desktop / Claude Code** for the server to appear.

### Google Antigravity

1. Open the Agent pane → click the `⋯` menu → **MCP Servers** → **Manage MCP Servers**
2. Click **View raw config** to open `mcp_config.json`
3. Add the entry below, save, then restart the MCP server from the Manage MCPs pane

```json
{
  "mcpServers": {
    "jdocmunch": {
      "command": "uvx",
      "args": ["jdocmunch-mcp"]
    }
  }
}
```

---

## Usage Examples

```
index_local:          { "path": "/path/to/docs" }
index_repo:           { "url": "owner/repo" }

get_toc:              { "repo": "owner/repo" }
get_toc_tree:         { "repo": "owner/repo" }
get_document_outline: { "repo": "owner/repo", "doc_path": "docs/config.md" }
search_sections:      { "repo": "owner/repo", "query": "authentication" }
get_section:          { "repo": "owner/repo", "section_id": "owner/repo::docs/config.md::authentication#1" }
```

---

## Tools (10)

| Tool                   | Purpose                                   |
| ---------------------- | ----------------------------------------- |
| `index_local`          | Index a local documentation folder        |
| `index_repo`           | Index a GitHub repository's docs          |
| `list_repos`           | List indexed documentation sets           |
| `get_toc`              | Flat section list in document order       |
| `get_toc_tree`         | Nested section tree per document          |
| `get_document_outline` | Section hierarchy for one document        |
| `search_sections`      | Weighted search returning summaries only  |
| `get_section`          | Full content of one section               |
| `get_sections`         | Batch content retrieval                   |
| `delete_index`         | Remove a doc index                        |

Search and retrieval tools include a `_meta` envelope with timing, token savings, and cost avoided:

```json
"_meta": {
  "latency_ms": 12,
  "sections_returned": 5,
  "tokens_saved": 1840,
  "total_tokens_saved": 94320,
  "cost_avoided": { "claude_opus": 0.0276, "gpt5_latest": 0.0184 },
  "total_cost_avoided": { "claude_opus": 1.4148, "gpt5_latest": 0.9432 }
}
```

`total_tokens_saved` and `total_cost_avoided` accumulate across all tool calls and persist to `~/.doc-index/_savings.json`.

---

## Supported Formats

| Format     | Extensions                    | Notes                                                            |
| ---------- | ----------------------------- | ---------------------------------------------------------------- |
| Markdown   | `.md`, `.markdown`            | ATX (`# Heading`) and setext (underline) headings               |
| MDX        | `.mdx`                        | JSX tags, frontmatter, import/export stripped before parsing    |
| Plain text | `.txt`                        | Paragraph-block section splitting                                |
| RST        | `.rst`                        | Treated as plain text (heading detection planned)               |

See ARCHITECTURE.md for parser details.

---

## Security

Built-in protections:

- Path traversal prevention
- Symlink escape protection
- Secret file exclusion (`.env`, `*.pem`, etc.)
- Binary file detection
- Configurable file size limits (500 KB default)
- Storage path injection prevention via `_safe_content_path()`
- Atomic index writes (temp file + rename)

See SECURITY.md for details.

---

## Best Use Cases

- Agent-driven documentation exploration
- Finding configuration and API reference sections
- Onboarding to unfamiliar frameworks
- Token-efficient multi-agent documentation workflows
- Large documentation sets with dozens of files

---

## Not Intended For

- Source code symbol indexing (use [jCodeMunch](https://github.com/jgravelle/jcodemunch-mcp) for that)
- Real-time file watching
- Cross-repository global search
- Semantic/vector similarity search

---

## Environment Variables

| Variable                     | Purpose                   | Required |
| ---------------------------- | ------------------------- | -------- |
| `GITHUB_TOKEN`               | GitHub API auth           | No       |
| `ANTHROPIC_API_KEY`          | Section summaries via Claude Haiku (takes priority) | No |
| `GOOGLE_API_KEY`             | Section summaries via Gemini Flash | No |
| `DOC_INDEX_PATH`             | Custom cache path         | No       |
| `JDOCMUNCH_SHARE_SAVINGS`    | Set to `0` to disable anonymous community token savings reporting | No |

### Community Savings Meter

Each tool call contributes an anonymous delta to a live global counter at [j.gravelle.us](https://j.gravelle.us). Only two values are ever sent: the tokens saved (a number) and a random anonymous install ID — never content, paths, repo names, or anything identifying. The anon ID is generated once and stored in `~/.doc-index/_savings.json`.

To disable, set `JDOCMUNCH_SHARE_SAVINGS=0` in your MCP server env.

---

## Documentation

- [USER_GUIDE.md](USER_GUIDE.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [SPEC.md](SPEC.md)
- [SECURITY.md](SECURITY.md)
- [TOKEN_SAVINGS.md](TOKEN_SAVINGS.md)

---

## License (Dual Use)

This repository is **free for non-commercial use** under the terms below.
**Commercial use requires a paid commercial license.**

---

## Copyright and License Text

Copyright (c) 2026 J. Gravelle

### 1. Non-Commercial License Grant (Free)

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to use, copy, modify, merge, publish, and distribute the Software for **personal, educational, research, hobby, or other non-commercial purposes**, subject to the following conditions:

1. The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

2. Any modifications made to the Software must clearly indicate that they are derived from the original work, and the name of the original author (J. Gravelle) must remain intact. He's kinda full of himself.

3. Redistributions of the Software in source code form must include a prominent notice describing any modifications from the original version.

### 2. Commercial Use

Commercial use of the Software requires a separate paid commercial license from the author.

"Commercial use" includes, but is not limited to:

- Use of the Software in a business environment
- Internal use within a for-profit organization
- Incorporation into a product or service offered for sale
- Use in connection with revenue generation, consulting, SaaS, hosting, or fee-based services

For commercial licensing inquiries, contact:
j@gravelle.us | https://j.gravelle.us

Until a commercial license is obtained, commercial use is not permitted.

### 3. Disclaimer of Warranty

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NONINFRINGEMENT.

IN NO EVENT SHALL THE AUTHOR OR COPYRIGHT HOLDER BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT, OR OTHERWISE, ARISING FROM, OUT OF, OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
