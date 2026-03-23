# jdocmunch-mcp

**Version:** 1.4.3 | **Tests:** `pytest tests/ -q`

## Purpose
Documentation section indexing for the jMunch suite. Companion to jcodemunch-mcp (which owns code symbols). Do NOT add code/docstring parsing here.

## Supported Formats
`.md/.mdx`, `.rst`, `.adoc`, `.ipynb`, `.html`, `.txt`, `.yaml/.yml` (OpenAPI only), `.json/.jsonc`, `.xml/.svg/.xhtml`, `.tscn/.tres` (Godot scenes/resources)

## Key Modules
- `storage/doc_store.py` — DocIndex, DocStore, detect_changes, incremental_save
- `parser/` — one file per format (markdown, rst, asciidoc, notebook, html, text, openapi, json, xml)
- `tools/` — index_local, index_repo, get_toc, get_toc_tree, search_sections, get_section, get_sections, list_repos, delete_index
- `embeddings/` — provider.py (Gemini + OpenAI), cosine_similarity, embed_sections, embed_query

## Architecture
- INDEX_VERSION=1; version mismatch triggers full re-index
- O(1) section lookup via `DocIndex.__post_init__` id dict
- `pyyaml>=6.0` required (hard dep)
- Semantic search: pass `use_embeddings=True` to index_local/index_repo; search_sections auto-selects cosine-similarity if embeddings present
- Embedding providers: GOOGLE_API_KEY (Gemini, text-embedding-004) or OPENAI_API_KEY (text-embedding-3-small); override with JDOCMUNCH_EMBEDDING_PROVIDER env var
