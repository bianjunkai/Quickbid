"""Evidence helpers for tender-derived facts.

The parser already stores page hints in several shapes. These helpers adapt
those shapes into one small contract that downstream UI, outline export, and
review code can consume without forcing a parser prompt rewrite.
"""
from __future__ import annotations

from typing import Any


def make_evidence_ref(
    *,
    page: int | None = None,
    quote: str | None = None,
    field_path: str,
    source_type: str = "tender",
    confidence: str = "high",
) -> dict[str, Any]:
    """Build a normalized evidence reference."""
    return {
        "page": page if isinstance(page, int) and page > 0 else None,
        "quote": (quote or "").strip(),
        "field_path": field_path,
        "source_type": source_type,
        "confidence": confidence,
    }


def evidence_from_k_field(field: Any, field_path: str) -> list[dict[str, Any]]:
    """Extract evidence refs from a K field's current compatible shape."""
    if not isinstance(field, dict):
        quote = "" if field is None else str(field)
        return [make_evidence_ref(quote=quote, field_path=field_path)] if quote else []

    refs: list[dict[str, Any]] = []
    if "items" in field:
        items = field.get("items") or []
        pages = field.get("source_pages") or []
        for i, item in enumerate(items):
            quote = "" if item is None else str(item)
            page = pages[i] if i < len(pages) else None
            if quote or page:
                refs.append(
                    make_evidence_ref(
                        page=page,
                        quote=quote,
                        field_path=f"{field_path}.items[{i}]",
                    )
                )
        return refs

    value = field.get("value")
    quote = "" if value is None else str(value)
    page = field.get("source_page")
    if quote or page:
        refs.append(make_evidence_ref(page=page, quote=quote, field_path=field_path))
    return refs


def evidence_from_marker_item(item: Any, field_path: str) -> list[dict[str, Any]]:
    """Extract evidence refs from marker/risk extraction items."""
    if not isinstance(item, dict):
        quote = "" if item is None else str(item)
        return [make_evidence_ref(quote=quote, field_path=field_path)] if quote else []

    quote = (
        item.get("raw_text")
        or item.get("original_text")
        or item.get("source_text")
        or item.get("condition")
        or item.get("requirement")
        or item.get("content")
        or item.get("text")
        or item.get("description")
        or item.get("semantic")
        or ""
    )
    return [
        make_evidence_ref(
            page=item.get("source_page"),
            quote=str(quote),
            field_path=field_path,
        )
    ]


def first_evidence(refs: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return the first useful evidence ref."""
    return next((r for r in refs if r.get("page") or r.get("quote")), None)
