"""Parser dispatcher for doc files."""

from .markdown_parser import parse_markdown, strip_mdx
from .text_parser import parse_text
from .hierarchy import wire_hierarchy


# Supported extensions -> parser key
ALL_EXTENSIONS = {
    ".md": "markdown",
    ".markdown": "markdown",
    ".mdx": "markdown",  # MDX = Markdown + JSX; stripped before parsing
    ".txt": "text",
    ".rst": "text",  # treat RST as plain text for now
}


def parse_file(content: str, doc_path: str, repo: str) -> list:
    """Parse a document file into Section objects with hierarchy wired.

    Args:
        content: Raw file content.
        doc_path: Relative file path (used in IDs and section metadata).
        repo: Repository identifier.

    Returns:
        List of Section objects with parent_id/children populated.
    """
    import os
    _, ext = os.path.splitext(doc_path)
    ext = ext.lower()
    doc_type = ALL_EXTENSIONS.get(ext, "text")

    if doc_type == "markdown":
        if ext == ".mdx":
            content = strip_mdx(content)
        sections = parse_markdown(content, doc_path, repo)
    else:
        sections = parse_text(content, doc_path, repo)

    return wire_hierarchy(sections)
