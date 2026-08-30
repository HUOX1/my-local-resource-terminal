from __future__ import annotations

from dataclasses import dataclass
from typing import Any


PROTOCOL_VERSION = 1


class ProtocolError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Request:
    id: str
    type: str
    payload: dict[str, Any]


def parse_request(value: object) -> Request:
    if not isinstance(value, dict):
        raise ProtocolError("request must be an object")
    request_id = value.get("id")
    request_type = value.get("type")
    payload = value.get("payload")
    if not isinstance(request_id, str) or not request_id:
        raise ProtocolError("request id must be a non-empty string")
    if not isinstance(request_type, str) or not request_type:
        raise ProtocolError("request type must be a non-empty string")
    if not isinstance(payload, dict):
        raise ProtocolError("request payload must be an object")
    return Request(id=request_id, type=request_type, payload=payload)


def response_message(request_id: str, *, data: object | None = None, error: object | None = None) -> dict[str, object]:
    ok = error is None
    return {"id": request_id, "type": "response", "ok": ok, "data": data if ok else None, "error": None if ok else error}


def event_message(event_type: str, payload: dict[str, object]) -> dict[str, object]:
    return {"type": event_type, "payload": payload}
