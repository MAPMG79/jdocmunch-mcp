# Security Controls

jdocmunch-mcp indexes documentation files from local folders and GitHub repositories. This document describes the security controls that protect against common risks when handling arbitrary file trees.

---

## Path Traversal Prevention

All user-supplied paths are validated before any file is read or written.

* **`validate_path(root, target)`** resolves both paths to absolute form and verifies the target is a descendant of `root` using `os.path.commonpath()`.
* Applied during file discovery and again before each file read (defense in depth).
* Paths such as `../../etc/passwd` or absolute paths outside the repository root are rejected.

---

## Symlink Escape Protection

Symlinks can be used to escape the repository root and read arbitrary files.

* **Default:** `follow_symlinks=False` — symlinks are skipped during file discovery.
* When symlinks are followed (`follow_symlinks=True`), each symlink target is resolved and validated against the repository root. Escaping symlinks are skipped with a warning.
* **`is_symlink_escape(root, path)`** checks whether a symlink resolves outside the root.
* On Windows, environments without symlink support automatically skip symlink traversal.

---

## Default Ignore Policy

Files are filtered through multiple layers:

1. **SKIP_PATTERNS** — directories always excluded: `node_modules/`, `vendor/`, `venv/`, `.venv/`, `__pycache__/`, `dist/`, `build/`, `.git/`, `.tox/`, `.mypy_cache/`, `.gradle/`, `target/`.
2. **`.gitignore`** — respected by default for local folders (via the `pathspec` library).
3. **`extra_ignore_patterns`** — user-configurable additional gitignore-style patterns passed to `index_local`.

---

## Secret Exclusion

Files matching known secret patterns are excluded during indexing.

**Excluded patterns include:**

* Environment files: `.env`, `.env.*`, `*.env`
* Certificates / keys: `*.pem`, `*.key`, `*.p12`, `*.pfx`, `*.keystore`, `*.jks`
* SSH keys: `id_rsa*`, `id_ed25519*`, `id_dsa*`, `id_ecdsa*`
* Credentials: `credentials.json`, `service-account*.json`, `*.credentials`
* Auth files: `.htpasswd`, `.netrc`, `.npmrc`, `.pypirc`
* Generic secret indicators: `*secret*`, `*.secrets`, `*.token`

When a secret file is detected, a warning is included in the indexing response. Secret files are never stored in the index or cached content directory.

---

## File Size Limits

* **Default maximum:** 500 KB per file.
* Files exceeding the limit are skipped during discovery.
* A configurable **file count limit** (default: 500 files) prevents runaway indexing of extremely large repositories.

---

## Binary File Detection

Binary files are excluded using a two-stage check:

1. **Extension-based detection** — common binary extensions (`.exe`, `.dll`, `.so`, `.png`, `.jpg`, `.zip`, `.pyc`, `.db`, `.mp3`, `.mp4`, fonts, etc.).
2. **Content-based detection** — files containing null bytes within the first 8 KB are treated as binary and skipped, even if the extension suggests a text format.

Note: doc extensions (`.md`, `.txt`, `.rst`, `.mdx`) are always treated as text and bypass the binary extension filter.

---

## Storage Safety

* Index storage defaults to `~/.doc-index/`.
* The storage path can be overridden using the `DOC_INDEX_PATH` environment variable.
* Repository identifiers are stored under `{owner}/{name}.json`, using validated path components — only alphanumeric characters, hyphens, underscores, and dots are accepted; slashes and path separators are rejected.
* Raw cached files are written only after validating each doc path against the content directory root using `_safe_content_path()`, preventing path injection via malicious doc paths.
* Index files are stored as JSON and schema-validated during load. Indexes from future versions are rejected.
* Atomic writes (temp file + rename) prevent partial/corrupt index files.

---

## Encoding Safety

* All file reads use `errors="replace"` to substitute invalid UTF-8 bytes with the Unicode replacement character (U+FFFD) instead of raising decode errors.
* Section content retrieval also uses `errors="replace"` for safe decoding.
* Cached raw files are stored using UTF-8 encoding.

---

## Summary of Controls

| Control                   | Location                            | Default                     |
| ------------------------- | ----------------------------------- | --------------------------- |
| Path traversal validation | `security.validate_path()`          | Always enabled              |
| Symlink escape protection | `security.is_symlink_escape()`      | Symlinks skipped by default |
| Secret file exclusion     | `security.is_secret_file()`         | Always enabled              |
| Binary file detection     | `security.is_binary_file()`         | Always enabled              |
| File size limit           | File discovery pipeline             | 500 KB                      |
| File count limit          | File discovery pipeline             | 500 files                   |
| `.gitignore` respect      | `index_local` discovery pipeline    | Enabled                     |
| Storage path injection    | `DocStore._safe_content_path()`     | Always validated            |
| UTF-8 safe decode         | All file reads                      | `errors="replace"`          |
| Atomic index writes       | `DocStore.save_index()`             | temp + rename               |
