from __future__ import annotations

import re


def parse_batch_terms(text: str) -> list[str]:
    """Split tag input on common Western/Chinese separators and de-duplicate."""
    seen: set[str] = set()
    result: list[str] = []
    for value in re.split(r"[,，、;；\n]+", text):
        item = value.strip()
        key = item.casefold()
        if item and key not in seen:
            result.append(item)
            seen.add(key)
    return result
