from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

COLLECTION_DOMAINS = {"movies", "games"}


@dataclass(frozen=True, slots=True)
class CollectionFolder:
    id: str
    domain: str
    name: str
    created_at: datetime

    @classmethod
    def new(cls, domain: str, name: str) -> "CollectionFolder":
        domain = _normalize_domain(domain)
        name = _normalize_name(name)
        return cls(str(uuid4()), domain, name, datetime.now(timezone.utc))


def _normalize_domain(domain: str) -> str:
    value = str(domain).strip().casefold()
    if value not in COLLECTION_DOMAINS:
        raise ValueError(f"unsupported collection folder domain: {domain}")
    return value


def _normalize_name(name: str) -> str:
    value = str(name).strip()
    if not value:
        raise ValueError("folder name is required")
    if any(char in value for char in "\\/\r\n\t"):
        raise ValueError("folder name contains unsupported characters")
    return value
