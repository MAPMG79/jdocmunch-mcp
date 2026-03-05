"""Parser dispatcher for doc files."""

from .markdown_parser import parse_markdown, strip_mdx
from .rst_parser import parse_rst
from .asciidoc_parser import parse_asciidoc
from .notebook_parser import convert_notebook
from .html_parser import convert_html
from .text_parser import parse_text
from .hierarchy import wire_hierarchy


# Supported extensions -> parser key
ALL_EXTENSIONS = {
    ".md": "markdown",
    ".markdown": "markdown",
    ".mdx": "markdown",  # MDX = Markdown + JSX; stripped before parsing
    ".txt": "text",
    ".rst": "rst",
    ".adoc": "asciidoc",
    ".asciidoc": "asciidoc",
    ".asc": "asciidoc",
    ".ipynb": "notebook",
    ".html": "html",
    ".htm": "html",
}


def preprocess_content(content: str, doc_path: str) -> str:
    """Preprocess file content before parsing and storage.

    For .ipynb files, converts JSON to a Markdown text representation so that
    byte offsets computed during parsing are valid against the stored raw file.
    For all other formats, returns content unchanged.

    Args:
        content: Raw file content.
        doc_path: Relative file path (used to detect .ipynb extension).

    Returns:
        Content ready for parse_file() and for storage as the raw file.
    """
    import os
    ext = os.path.splitext(doc_path)[1].lower()
    if ext == ".ipynb":
        return convert_notebook(content)
    if ext in (".html", ".htm"):
        return convert_html(content)
    return content


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
    elif doc_type == "rst":
        sections = parse_rst(content, doc_path, repo)
    elif doc_type == "asciidoc":
        sections = parse_asciidoc(content, doc_path, repo)
    elif doc_type in ("notebook", "html"):
        # content should already be preprocessed to markdown by preprocess_content()
        sections = parse_markdown(content, doc_path, repo)
    else:
        sections = parse_text(content, doc_path, repo)

    return wire_hierarchy(sections)
