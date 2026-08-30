from __future__ import annotations

import asyncio
import json

from websockets.asyncio.client import connect

from terminal_core.websocket_server import HOST, PORT, TerminalWebSocketServer


async def _main() -> int:
    async def handler(command_type: str, payload: dict) -> object:
        if command_type == "library.games.list":
            return []
        raise ValueError(f"unsupported command: {command_type}")

    server = TerminalWebSocketServer(handler)
    await server.start()
    try:
        async with connect(f"ws://{HOST}:{PORT}") as ws:
            await ws.send(json.dumps({"id":"hello","type":"hello","payload":{"protocol":1}}))
            hello = json.loads(await ws.recv())
            if not hello.get("ok"):
                return 1
            await ws.send(json.dumps({"id":"list","type":"library.games.list","payload":{}}))
            result = json.loads(await ws.recv())
            return 0 if result.get("ok") and result.get("data") == [] else 1
    finally:
        await server.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
