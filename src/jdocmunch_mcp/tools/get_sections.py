"""Batch content retrieval for multiple sections."""

import time
from typing import Optional

from .get_section import get_section as _get_one


def get_sections(
    repo: str,
    section_ids: list,
    verify: bool = False,
    storage_path: Optional[str] = None,
) -> dict:
    """Retrieve full content for multiple sections in one call.

    Args:
        repo: Repository identifier.
        section_ids: List of section IDs to retrieve.
        verify: If True, verify content hashes.
        storage_path: Custom storage path.

    Returns:
        Dict with list of section results.
    """
    t0 = time.time()
    results = []
    total_tokens_saved = 0

    for section_id in section_ids:
        result = _get_one(
            repo=repo,
            section_id=section_id,
            verify=verify,
            storage_path=storage_path,
        )
        meta = result.pop("_meta", {})
        total_tokens_saved += meta.get("tokens_saved", 0)
        results.append(result)

    latency_ms = int((time.time() - t0) * 1000)
    return {
        "sections": results,
        "section_count": len(results),
        "_meta": {
            "latency_ms": latency_ms,
            "sections_returned": len(results),
            "tokens_saved": total_tokens_saved,
        },
    }
