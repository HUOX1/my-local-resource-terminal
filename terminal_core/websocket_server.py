from __future__ import annotations

import json
from collections.abc import Awaitable, Callable

from websockets.asyncio.server import ServerConnection, serve

from .protocol import PROTOCOL_VERSION, ProtocolError, parse_request, response_message


HOST = "127.0.0.1"
PORT = 8765


class TerminalWebSocketServer:
    def __init__(self, command_handler: Callable[[str, dict], Awaitable[object]]) -> None:
        self._command_handler = command_handler
        self._server = None

    async def start(self) -> None:
        self._server = await serve(self._handle_connection, HOST, PORT)

    async def close(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    async def _handle_connection(self, websocket: ServerConnection) -> None:
        handshaken = False
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
                    if request.payload.get("protocol") != PROTOCOL_VERSION:
                        await websocket.send(json.dumps(response_message(
                            request.id,
                            error={
                                "code": "protocol_mismatch",
                                "message": f"expected protocol {PROTOCOL_VERSION}",
                            },
                        )))
                        continue
                    handshaken = True
                    result = {"protocol": PROTOCOL_VERSION}
                else:
                    result = await self._command_handler(request.type, request.payload)
                await websocket.send(json.dumps(response_message(request.id, data=result)))
            except (json.JSONDecodeError, ProtocolError) as exc:
                await websocket.send(json.dumps(response_message(
                    request_id or "invalid",
                    error={"code": "bad_request", "message": str(exc)},
                )))
            except Exception as exc:
                await websocket.send(json.dumps(response_message(
                    request_id or "invalid",
                    error={"code": "internal_error", "message": str(exc)},
                )))
