"""Prompt injection guard — wraps external text before it enters model context.

All retrieved text (policy excerpts, translations, evidence summaries, document titles)
passes through sanitize_external_context() before entering the LLM message stream.
"""

from __future__ import annotations

MAX_EXCERPT_CHARS = 2000
MAX_SEARCH_RESULTS = 10


def sanitize_external_context(text: str, source_label: str = "external") -> str:
    """Wrap and truncate external text to prevent prompt injection.

    - Wraps in [evidence]...[/evidence] markers
    - Truncates to MAX_EXCERPT_CHARS
    - Appends truncation notice if cut
    """
    if not text:
        return ""

    truncated = text[:MAX_EXCERPT_CHARS]
    if len(text) > MAX_EXCERPT_CHARS:
        truncated += f"\n[...truncated from {len(text)} chars]"

    return f"[evidence:{source_label}]\n{truncated}\n[/evidence:{source_label}]"


def sanitize_evidence_text(text: str) -> str:
    """Shortcut for policy clause / evidence text."""
    return sanitize_external_context(text, "evidence")


def sanitize_tool_result_summary(result: dict, max_items: int = MAX_SEARCH_RESULTS) -> dict:
    """Truncate tool result arrays to prevent context blowout."""
    if not result:
        return {}
    sanitized = dict(result)
    for key in ("items", "results", "candidates"):
        if key in sanitized and isinstance(sanitized[key], list):
            if len(sanitized[key]) > max_items:
                sanitized[f"{key}_truncated"] = True
                sanitized[f"{key}_total"] = len(sanitized[key])
                sanitized[key] = sanitized[key][:max_items]
    return sanitized
