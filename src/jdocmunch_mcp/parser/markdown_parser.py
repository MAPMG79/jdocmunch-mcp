"""Markdown parser: ATX + setext heading splitter with byte offsets."""

import os
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# MDX pre-processor
# ---------------------------------------------------------------------------

_MDX_FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n?", re.DOTALL)
_MDX_DISCARD_FENCE_RE = re.compile(r":::js\n.*?(?=\n:::|\Z)", re.DOTALL)
_MDX_FENCE_DELIM_RE = re.compile(r"^:::(?:python|js)\s*$|^:::\s*$", re.MULTILINE)
_MDX_API_LINK_BACKTICK_RE = re.compile(r"@\[`([^`]+)`\]")
_MDX_API_LINK_RE = re.compile(r"@\[([^\]]+)\]")
_MDX_MERMAID_RE = re.compile(r"```mermaid\n.*?```", re.DOTALL)
_MDX_BLANK_LINES_RE = re.compile(r"\n{3,}")

_BLOCK_TAGS = (
    r"Note|Tip|Warning|Info|Accordion|Steps?|Cards?|CardGroup|Tabs?|Tab|CodeGroup"
)
_MDX_OPEN_TAG_RE = re.compile(r"<(?:" + _BLOCK_TAGS + r")(?:\s[^>]*)?>", re.MULTILINE)
_MDX_CLOSE_TAG_RE = re.compile(r"</(?:" + _BLOCK_TAGS + r")>", re.MULTILINE)
_MDX_SELF_CLOSE_KNOWN_RE = re.compile(r"<(?:" + _BLOCK_TAGS + r")\s*/>")
_MDX_SELF_CLOSE_UNKNOWN_RE = re.compile(r"<[A-Z][A-Za-z]*(?:\s[^>]*)?\s*/>")
_MDX_IMPORT_EXPORT_RE = re.compile(r"^(?:import|export)\s+.*$", re.MULTILINE)


def strip_mdx(content: str) -> str:
    """Strip MDX-specific syntax from content, leaving clean Markdown.

    Keeps Python code fences (:::python) and discards JavaScript (:::js).
    JSX component tags are removed; their inner text is preserved.

    Args:
        content: Raw MDX file content.

    Returns:
        Clean Markdown string suitable for the standard parser.
    """
    content = _MDX_FRONTMATTER_RE.sub("", content)
    content = _MDX_DISCARD_FENCE_RE.sub("", content)
    content = _MDX_FENCE_DELIM_RE.sub("", content)
    content = _MDX_API_LINK_BACKTICK_RE.sub(r"\1", content)
    content = _MDX_API_LINK_RE.sub(r"\1", content)
    content = _MDX_MERMAID_RE.sub("", content)
    content = _MDX_OPEN_TAG_RE.sub("", content)
    content = _MDX_CLOSE_TAG_RE.sub("", content)
    content = _MDX_SELF_CLOSE_KNOWN_RE.sub("", content)
    content = _MDX_SELF_CLOSE_UNKNOWN_RE.sub("", content)
    content = _MDX_IMPORT_EXPORT_RE.sub("", content)
    content = _MDX_BLANK_LINES_RE.sub("\n\n", content)
    return content.strip()

from .sections import (
    Section,
    slugify,
    resolve_slug_collision,
    make_section_id,
    make_hierarchical_slug,
    compute_content_hash,
    extract_references,
    extract_tags,
)

_ATX_RE = re.compile(r"^(#{1,6})\s+(.+?)(?:\s+#+\s*)?$")
_SETEXT_H1_RE = re.compile(r"^=+\s*$")
_SETEXT_H2_RE = re.compile(r"^-+\s*$")


def parse_markdown(content: str, doc_path: str, repo: str) -> list:
    """Parse a markdown file into a list of Section objects.

    Handles both ATX headings (# Heading) and setext headings (underline style).
    Tracks byte offsets per line. Content before the first heading becomes a
    level-0 root section.

    Args:
        content: Raw markdown text.
        doc_path: Relative path of the document (used in section IDs).
        repo: Repository identifier (used in section IDs).

    Returns:
        List of Section objects, in document order, without hierarchy wiring.
    """
    lines = content.splitlines(keepends=True)
    used_slugs: dict = {}
    slug_stack: list = []
    sections = []

    # State for the current open section
    current_title: str = Path(doc_path).stem  # fallback for level-0
    current_level: int = 0
    current_slug: str = ""
    current_byte_start: int = 0
    current_lines: list = []

    byte_cursor = 0

    def _finalize_section(byte_end: int) -> None:
        """Close the current open section and append it to sections."""
        nonlocal current_slug
        body = "".join(current_lines)
        slug = current_slug or slugify(current_title)
        section_id = make_section_id(repo, doc_path, slug, current_level)
        sec = Section(
            id=section_id,
            repo=repo,
            doc_path=doc_path,
            title=current_title,
            content=body,
            level=current_level,
            parent_id="",      # wired later by hierarchy.py
            children=[],       # wired later by hierarchy.py
            byte_start=current_byte_start,
            byte_end=byte_end,
            summary="",
        )
        sec.content_hash = compute_content_hash(body)
        sec.references = extract_references(body)
        sec.tags = extract_tags(body)
        sections.append(sec)

    prev_line: str = ""
    prev_byte_start: int = 0

    for i, line in enumerate(lines):
        line_bytes = len(line.encode("utf-8"))
        line_stripped = line.rstrip("\n").rstrip("\r")

        # Check for setext heading (underline of previous line)
        if i > 0 and _SETEXT_H1_RE.match(line_stripped) and prev_line.strip():
            heading_text = prev_line.strip()
            heading_level = 1
        elif i > 0 and _SETEXT_H2_RE.match(line_stripped) and prev_line.strip() and len(line_stripped) >= 2:
            heading_text = prev_line.strip()
            heading_level = 2
        else:
            heading_text = None
            heading_level = None

        # Check for ATX heading
        atx_match = _ATX_RE.match(line_stripped)
        if atx_match and not heading_text:
            heading_text = atx_match.group(2).strip()
            heading_level = len(atx_match.group(1))

        if heading_text and heading_level:
            # Setext: the previous line was the heading text — remove it from current_lines
            if _SETEXT_H1_RE.match(line_stripped) or (_SETEXT_H2_RE.match(line_stripped) and len(line_stripped) >= 2):
                # prev_line is heading text; finalize up to prev_byte_start
                if current_lines:
                    # Remove the last line (prev_line) from current_lines
                    current_lines = current_lines[:-1]
                _finalize_section(byte_end=prev_byte_start)

                current_title = heading_text
                current_level = heading_level
                current_slug = make_hierarchical_slug(heading_text, heading_level, slug_stack, used_slugs)
                current_byte_start = prev_byte_start
                current_lines = []
            else:
                # ATX: current line is the heading
                _finalize_section(byte_end=byte_cursor)

                current_title = heading_text
                current_level = heading_level
                current_slug = make_hierarchical_slug(heading_text, heading_level, slug_stack, used_slugs)
                current_byte_start = byte_cursor
                current_lines = [line]
        else:
            current_lines.append(line)

        prev_line = line_stripped
        prev_byte_start = byte_cursor
        byte_cursor += line_bytes

    # Finalize last open section
    _finalize_section(byte_end=byte_cursor)

    return sections
