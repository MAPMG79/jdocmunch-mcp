"""Jupyter Notebook parser: converts .ipynb JSON to a Markdown text representation.

Markdown cells are included as-is. Code cells are wrapped in fenced code blocks.
The resulting text is then parsed by the standard Markdown parser, so heading
structure in markdown cells drives section boundaries.

The text representation (not the original JSON) is stored as the raw file so
that byte-offset content retrieval works correctly.
"""

import json


def _get_kernel_language(notebook: dict) -> str:
    """Extract the kernel language from notebook metadata, defaulting to 'python'."""
    meta = notebook.get("metadata", {})
    lang = (
        meta.get("language_info", {}).get("name")
        or meta.get("kernelspec", {}).get("language")
        or "python"
    )
    return lang.lower()


def _cell_source(cell: dict) -> str:
    """Join cell source lines into a single string."""
    source = cell.get("source", [])
    if isinstance(source, list):
        return "".join(source)
    return source


def convert_notebook(json_str: str) -> str:
    """Convert a Jupyter notebook JSON string to a Markdown text representation.

    Args:
        json_str: Raw .ipynb file content.

    Returns:
        Markdown string suitable for parse_markdown(). Returns empty string on
        parse failure (the caller will skip the file).
    """
    try:
        nb = json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        return ""

    cells = nb.get("cells", [])
    lang = _get_kernel_language(nb)
    parts = []

    for cell in cells:
        cell_type = cell.get("cell_type", "")
        source = _cell_source(cell).strip()
        if not source:
            continue

        if cell_type == "markdown":
            parts.append(source)
        elif cell_type == "code":
            parts.append(f"```{lang}\n{source}\n```")
        else:
            # raw or unknown — include as plain text
            parts.append(source)

    return "\n\n".join(parts)
