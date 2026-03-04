"""Tests for the parser module."""

import pytest
from pathlib import Path

from jdocmunch_mcp.parser.sections import slugify, resolve_slug_collision, make_section_id, extract_references, extract_tags
from jdocmunch_mcp.parser.markdown_parser import parse_markdown
from jdocmunch_mcp.parser.text_parser import parse_text
from jdocmunch_mcp.parser.hierarchy import wire_hierarchy
from jdocmunch_mcp.parser import parse_file

FIXTURES = Path(__file__).parent / "fixtures"


class TestSlugify:
    def test_basic(self):
        assert slugify("Hello World") == "hello-world"

    def test_special_chars(self):
        assert slugify("API Reference!") == "api-reference"

    def test_numbers(self):
        assert slugify("Step 1: Install") == "step-1-install"

    def test_empty(self):
        assert slugify("") == "section"

    def test_multiple_spaces(self):
        assert slugify("  foo   bar  ") == "foo-bar"


class TestSlugCollision:
    def test_no_collision(self):
        used = {}
        assert resolve_slug_collision("foo", used) == "foo"
        assert used == {"foo": 1}

    def test_collision(self):
        used = {"foo": 1}
        assert resolve_slug_collision("foo", used) == "foo-2"

    def test_multiple_collisions(self):
        used = {}
        s1 = resolve_slug_collision("foo", used)
        s2 = resolve_slug_collision("foo", used)
        s3 = resolve_slug_collision("foo", used)
        assert s1 == "foo"
        assert s2 == "foo-2"
        assert s3 == "foo-3"


class TestSectionId:
    def test_format(self):
        sid = make_section_id("local/docs", "README.md", "installation", 2)
        assert sid == "local/docs::README.md::installation#2"


class TestExtractReferences:
    def test_bare_url(self):
        refs = extract_references("See https://example.com/docs for more.")
        assert "https://example.com/docs" in refs

    def test_markdown_link(self):
        refs = extract_references("[Guide](https://example.com/guide)")
        assert "https://example.com/guide" in refs

    def test_no_duplicates(self):
        refs = extract_references("[Link](https://x.com) and https://x.com")
        assert refs.count("https://x.com") == 1


class TestExtractTags:
    def test_hashtag(self):
        tags = extract_tags("This is #important and #api content.")
        assert "important" in tags
        assert "api" in tags

    def test_no_tags(self):
        assert extract_tags("No tags here.") == []


class TestMarkdownParser:
    def test_basic_headings(self):
        content = "# Title\n\nIntro.\n\n## Section 1\n\nContent.\n\n## Section 2\n\nMore.\n"
        sections = parse_markdown(content, "test.md", "test/repo")
        # Should have root + Section 1 + Section 2
        assert len(sections) >= 2
        titles = [s.title for s in sections]
        assert "Section 1" in titles
        assert "Section 2" in titles

    def test_levels(self):
        content = "# H1\n\n## H2\n\n### H3\n"
        sections = parse_markdown(content, "doc.md", "repo")
        levels = [s.level for s in sections]
        assert 1 in levels
        assert 2 in levels
        assert 3 in levels

    def test_byte_offsets_non_negative(self):
        content = "# Title\n\nContent.\n\n## Sub\n\nMore.\n"
        sections = parse_markdown(content, "doc.md", "repo")
        for sec in sections:
            assert sec.byte_start >= 0
            assert sec.byte_end >= sec.byte_start

    def test_fixture_sample(self):
        content = (FIXTURES / "docs" / "sample.md").read_text(encoding="utf-8")
        sections = parse_markdown(content, "sample.md", "test/docs")
        titles = [s.title for s in sections]
        assert "Installation" in titles
        assert "Usage" in titles
        assert "API Reference" in titles

    def test_setext_headings(self):
        content = (FIXTURES / "docs" / "nested" / "guide.md").read_text(encoding="utf-8")
        sections = parse_markdown(content, "guide.md", "test/docs")
        titles = [s.title for s in sections]
        assert "Setext heading style" in titles or any("setext" in t.lower() for t in titles)

    def test_slug_collision_in_doc(self):
        content = "## Install\n\nFirst.\n\n## Install\n\nSecond.\n"
        sections = parse_markdown(content, "doc.md", "repo")
        ids = [s.id for s in sections]
        assert len(ids) == len(set(ids)), "Section IDs must be unique"

    def test_content_hash_populated(self):
        content = "# Title\n\nHello world.\n"
        sections = parse_markdown(content, "doc.md", "repo")
        for sec in sections:
            assert sec.content_hash != ""


class TestTextParser:
    def test_paragraphs(self):
        content = (FIXTURES / "text" / "sample.txt").read_text(encoding="utf-8")
        sections = parse_text(content, "sample.txt", "test/text")
        assert len(sections) >= 2

    def test_title_from_first_line(self):
        content = "This is paragraph one.\nSecond line.\n\nAnother paragraph.\n"
        sections = parse_text(content, "doc.txt", "repo")
        assert sections[0].title.startswith("This is paragraph one")

    def test_byte_offsets(self):
        content = "Para one.\n\nPara two.\n"
        sections = parse_text(content, "doc.txt", "repo")
        for sec in sections:
            assert sec.byte_start >= 0
            assert sec.byte_end > sec.byte_start


class TestHierarchy:
    def test_parent_child_wiring(self):
        content = "# H1\n\n## H2\n\n### H3\n\n## H2b\n"
        sections = parse_markdown(content, "doc.md", "repo")
        wire_hierarchy(sections)

        h1 = next((s for s in sections if s.level == 1), None)
        h2 = next((s for s in sections if s.level == 2 and "h2b" not in s.id), None)
        h3 = next((s for s in sections if s.level == 3), None)

        assert h1 is not None
        assert h2 is not None
        assert h3 is not None

        assert h3.parent_id == h2.id
        assert h2.parent_id == h1.id
        assert h2.id in h1.children

    def test_top_level_no_parent(self):
        content = "# Title\n\nContent.\n"
        sections = parse_markdown(content, "doc.md", "repo")
        for sec in sections:
            if sec.level <= 1:
                assert sec.parent_id == ""


class TestParseFileDispatcher:
    def test_md_dispatch(self):
        content = "# Title\n\nContent.\n"
        sections = parse_file(content, "README.md", "myrepo")
        assert len(sections) > 0
        assert sections[0].repo == "myrepo"

    def test_txt_dispatch(self):
        content = "Hello world.\n\nSecond paragraph.\n"
        sections = parse_file(content, "notes.txt", "myrepo")
        assert len(sections) > 0
