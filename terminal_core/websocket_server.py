from __future__ import annotations

import json
from collections.abc import Awaitable, Callable

from websockets.asyncio.server import ServerConnection, serve

from .protocol import (
    PROTOCOL_VERSION,
    ProtocolError,
    event_message,
    parse_request,
    response_message,
)


HOST = "127.0.0.1"
PORT = 8765


class TerminalWebSocketServer:
    def __init__(
        self,
        command_handler: Callable[[str, dict], Awaitable[object]],
        *,
        host: str = HOST,
        port: int = PORT,
    ) -> None:
        if host != HOST:
            raise ValueError("v0.6 backend must bind to 127.0.0.1")
        self._command_handler = command_handler
        self.host = host
        self.port = int(port)
        self._server = None
        self._clients: set[ServerConnection] = set()

    @property
    def bound_port(self) -> int:
        if self._server is None or not self._server.sockets:
            return self.port
        return int(self._server.sockets[0].getsockname()[1])

    async def start(self) -> None:
        self._server = await serve(self._handle_connection, self.host, self.port)

    async def close(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        self._clients.clear()

    async def broadcast(self, event_type: str, payload: dict[str, object]) -> None:
        if not self._clients:
            return
        message = json.dumps(event_message(event_type, payload))
        stale: list[ServerConnection] = []
        for client in tuple(self._clients):
            try:
                await client.send(message)
            except Exception:
                stale.append(client)
        for client in stale:
            self._clients.discard(client)

    async def _handle_connection(self, websocket: ServerConnection) -> None:
        handshaken = False
        try:
            async for raw in websocket:
                request_id = ""
                try:
                    value = json.loads(raw)
                    request = parse_request(value)
                    request_id = request.id

                    if not handshaken:
                        if request.type != "hello":
                            await websocket.send(json.dumps(response_message(
                                request.id,
                                error={"code": "handshake_required", "message": "hello required"},
                            )))
                            continue
                        protocol = request.payload.get("protocol")
                        if protocol != PROTOCOL_VERSION:
                            await websocket.send(json.dumps(response_message(
                                request.id,
                                error={
                                    "code": "protocol_mismatch",
                                    "message": f"expected protocol {PROTOCOL_VERSION}",
                                },
                            )))
                            continue
                        handshaken = True
                        self._clients.add(websocket)
                        result = {"protocol": PROTOCOL_VERSION}
                    else:
                        result = await self._command_handler(request.type, request.payload)

                    await websocket.send(json.dumps(response_message(request.id, data=result)))
                except (json.JSONDecodeError, ProtocolError, ValueError) as exc:
                    await websocket.send(json.dumps(response_message(
                        request_id or "invalid",
                        error={"code": "bad_request", "message": str(exc)},
                    )))
                except (KeyError, FileNotFoundError) as exc:
                    await websocket.send(json.dumps(response_message(
                        request_id or "invalid",
                        error={"code": "not_found", "message": str(exc)},
                    )))
                except Exception as exc:
                    await websocket.send(json.dumps(response_message(
                        request_id or "invalid",
                        error={"code": "internal_error", "message": str(exc)},
                    )))
        finally:
            self._clients.discard(websocket)
