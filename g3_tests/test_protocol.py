import pytest
from g3_core.protocol import ProtocolError,parse_request,response_message

def test_parse_request_rejects_missing_id():
    with pytest.raises(ProtocolError): parse_request({"type":"hello","payload":{"protocol":1}})
def test_parse_request_rejects_missing_type():
    with pytest.raises(ProtocolError): parse_request({"id":"1","payload":{}})
def test_parse_request_requires_object_payload():
    with pytest.raises(ProtocolError): parse_request({"id":"1","type":"hello","payload":[]})
def test_response_message_preserves_request_id():
    assert response_message("abc",data={"ok":True})=={"id":"abc","type":"response","ok":True,"data":{"ok":True},"error":None}

@pytest.mark.asyncio
async def test_server_requires_hello_before_other_commands():
    import json
    from websockets.asyncio.client import connect
    from g3_core.websocket_server import TerminalWebSocketServer,HOST,PORT
    async def handler(command_type,payload): return []
    server=TerminalWebSocketServer(handler); await server.start()
    try:
        async with connect(f"ws://{HOST}:{PORT}") as ws:
            await ws.send(json.dumps({"id":"1","type":"library.games.list","payload":{}})); msg=json.loads(await ws.recv()); assert msg["ok"] is False; assert msg["error"]["code"]=="handshake_required"
    finally: await server.close()

@pytest.mark.asyncio
async def test_server_accepts_protocol_1_hello_then_command():
    import json
    from websockets.asyncio.client import connect
    from g3_core.websocket_server import TerminalWebSocketServer,HOST,PORT
    async def handler(command_type,payload): assert command_type=="library.games.list"; return []
    server=TerminalWebSocketServer(handler); await server.start()
    try:
        async with connect(f"ws://{HOST}:{PORT}") as ws:
            await ws.send(json.dumps({"id":"h","type":"hello","payload":{"protocol":1}})); assert json.loads(await ws.recv())["ok"] is True
            await ws.send(json.dumps({"id":"2","type":"library.games.list","payload":{}})); msg=json.loads(await ws.recv()); assert msg["ok"] is True and msg["data"]==[]
    finally: await server.close()

@pytest.mark.asyncio
async def test_server_broadcasts_event_after_handshake():
    import json
    from websockets.asyncio.client import connect
    from g3_core.websocket_server import TerminalWebSocketServer,HOST
    async def handler(command_type,payload): return {}
    server=TerminalWebSocketServer(handler,port=0); await server.start()
    try:
        async with connect(f"ws://{HOST}:{server.bound_port}") as ws:
            await ws.send(json.dumps({"id":"h","type":"hello","payload":{"protocol":1}})); assert json.loads(await ws.recv())["ok"] is True
            await server.broadcast("library.changed",{"media_type":"game"}); event=json.loads(await ws.recv()); assert event=={"type":"library.changed","payload":{"media_type":"game"}}
    finally: await server.close()
