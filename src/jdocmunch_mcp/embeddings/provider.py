"""Embedding providers for semantic section search.

Supports Gemini (text-embedding-004) and OpenAI (text-embedding-3-small).
Auto-detects from GOOGLE_API_KEY / OPENAI_API_KEY env vars.
Set JDOCMUNCH_EMBEDDING_PROVIDER=none to disable.
"""

import math
import os
from typing import Optional


# ---------------------------------------------------------------------------
# Text preparation
# ---------------------------------------------------------------------------

def _section_embed_text(section) -> str:
    """Build the text to embed for a section.

    Prepends title so short-titled sections (e.g. "Emotional Consequences"
    followed by a bullet list) still get a semantically rich embedding.
    """
    parts = [section.title]
    if section.summary and section.summary != section.title:
        parts.append(section.summary)
    if section.content:
        parts.append(section.content[:1000])
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Cosine similarity (pure Python — no numpy dependency)
# ---------------------------------------------------------------------------

def cosine_similarity(a: list, b: list) -> float:
    """Cosine similarity between two float vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


# ---------------------------------------------------------------------------
# Provider detection
# ---------------------------------------------------------------------------

def get_provider_name() -> Optional[str]:
    """Return 'gemini', 'openai', or None based on env vars."""
    explicit = os.environ.get("JDOCMUNCH_EMBEDDING_PROVIDER", "").lower().strip()
    if explicit == "gemini":
        return "gemini"
    if explicit == "openai":
        return "openai"
    if explicit == "none":
        return None
    # Auto-detect: Gemini wins if both keys present (already a dep)
    if os.environ.get("GOOGLE_API_KEY"):
        return "gemini"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    return None


# ---------------------------------------------------------------------------
# Gemini provider
# ---------------------------------------------------------------------------

class _GeminiProvider:
    """Embed via Google Gemini text-embedding-004 (768 dims)."""

    MODEL = "models/text-embedding-004"
    BATCH_SIZE = 50  # conservative to avoid rate limits

    def __init__(self):
        import google.generativeai as genai
        genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
        self._genai = genai

    def embed_texts(self, texts: list, task_type: str = "retrieval_document") -> list:
        embeddings = []
        for text in texts:
            try:
                result = self._genai.embed_content(
                    model=self.MODEL,
                    content=text,
                    task_type=task_type,
                )
                embeddings.append(result["embedding"])
            except Exception:
                embeddings.append([])
        return embeddings


# ---------------------------------------------------------------------------
# OpenAI provider
# ---------------------------------------------------------------------------

class _OpenAIProvider:
    """Embed via OpenAI text-embedding-3-small (1536 dims)."""

    MODEL = "text-embedding-3-small"
    BATCH_SIZE = 100

    def __init__(self):
        from openai import OpenAI
        self._client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    def embed_texts(self, texts: list, task_type: str = "retrieval_document") -> list:
        # task_type is ignored for OpenAI — included for interface compatibility
        embeddings = []
        for i in range(0, len(texts), self.BATCH_SIZE):
            batch = texts[i:i + self.BATCH_SIZE]
            try:
                response = self._client.embeddings.create(model=self.MODEL, input=batch)
                embeddings.extend([e.embedding for e in response.data])
            except Exception:
                embeddings.extend([[] for _ in batch])
        return embeddings


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _get_provider():
    name = get_provider_name()
    if name == "gemini":
        try:
            return _GeminiProvider()
        except Exception:
            return None
    if name == "openai":
        try:
            return _OpenAIProvider()
        except Exception:
            return None
    return None


def embed_sections(sections: list) -> list:
    """Generate and attach embeddings to sections in-place.

    Mirrors the summarize_sections() interface — modifies and returns the list.
    Silently degrades (leaves embedding=None) if no provider is configured.
    """
    provider = _get_provider()
    if not provider:
        return sections

    texts = [_section_embed_text(s) for s in sections]
    try:
        embeddings = provider.embed_texts(texts, task_type="retrieval_document")
        for sec, emb in zip(sections, embeddings):
            if emb:
                sec.embedding = emb
    except Exception:
        pass  # lexical search still works

    return sections


def embed_query(query: str) -> Optional[list]:
    """Embed a search query. Returns None if no provider is configured."""
    provider = _get_provider()
    if not provider:
        return None
    try:
        results = provider.embed_texts([query], task_type="retrieval_query")
        return results[0] if results and results[0] else None
    except Exception:
        return None
