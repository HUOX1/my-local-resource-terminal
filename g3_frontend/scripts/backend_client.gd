extends Node
class_name TerminalBackendClient

signal connected
signal disconnected(code: int, reason: String)
signal response_received(request_id: String, ok: bool, data: Variant, error: Variant)
signal event_received(event_type: String, payload: Dictionary)

const BACKEND_URL: String = "ws://127.0.0.1:8765"
const PROTOCOL_VERSION: int = 1

var _socket: WebSocketPeer = WebSocketPeer.new()
var _request_counter: int = 0
var _handshake_sent: bool = false
var _was_open: bool = false
var _pending_types: Dictionary = {}
var _retry_elapsed: float = 0.0
var _connect_started: bool = false

func _ready() -> void:
    set_process(true)

func connect_backend() -> int:
    _socket = WebSocketPeer.new()
    _handshake_sent = false
    _was_open = false
    _retry_elapsed = 0.0
    var result: int = _socket.connect_to_url(BACKEND_URL)
    _connect_started = result == OK
    return result

func is_connected_to_backend() -> bool:
    return _socket.get_ready_state() == WebSocketPeer.STATE_OPEN and _handshake_sent

func request(command_type: String, payload: Dictionary = {}) -> String:
    if _socket.get_ready_state() != WebSocketPeer.STATE_OPEN:
        return ""
    _request_counter += 1
    var request_id: String = "g%06d" % _request_counter
    var packet: Dictionary = {
        "id": request_id,
        "type": command_type,
        "payload": payload,
    }
    _pending_types[request_id] = command_type
    var json_text: String = JSON.stringify(packet)
    var send_error: int = _socket.send_text(json_text)
    if send_error != OK:
        _pending_types.erase(request_id)
        return ""
    return request_id

func _process(delta: float) -> void:
    _socket.poll()
    var state: int = _socket.get_ready_state()
    if state == WebSocketPeer.STATE_OPEN:
        if not _was_open:
            _was_open = true
            _send_hello()
        while _socket.get_available_packet_count() > 0:
            var packet: PackedByteArray = _socket.get_packet()
            if _socket.was_string_packet():
                _handle_text(packet.get_string_from_utf8())
    elif state == WebSocketPeer.STATE_CLOSED:
        if _was_open:
            _was_open = false
            _handshake_sent = false
            disconnected.emit(_socket.get_close_code(), _socket.get_close_reason())
        _connect_started = false
        _retry_elapsed += delta
        if _retry_elapsed >= 1.5:
            connect_backend()

func _send_hello() -> void:
    if _handshake_sent:
        return
    _handshake_sent = true
    _request_counter += 1
    var request_id: String = "hello-%06d" % _request_counter
    _pending_types[request_id] = "hello"
    var packet: Dictionary = {
        "id": request_id,
        "type": "hello",
        "payload": {"protocol": PROTOCOL_VERSION},
    }
    _socket.send_text(JSON.stringify(packet))

func _handle_text(text: String) -> void:
    var parsed: Variant = JSON.parse_string(text)
    if not (parsed is Dictionary):
        return
    var message: Dictionary = parsed as Dictionary
    if str(message.get("type", "")) == "response":
        var request_id: String = str(message.get("id", ""))
        var pending_type: String = str(_pending_types.get(request_id, ""))
        _pending_types.erase(request_id)
        var ok: bool = bool(message.get("ok", false))
        if pending_type == "hello" and ok:
            connected.emit()
        if not ok:
            push_error(
                "Backend request %s failed: %s" % [
                    pending_type,
                    JSON.stringify(message.get("error", {})),
                ]
            )
        response_received.emit(
            request_id,
            ok,
            message.get("data", null),
            message.get("error", null)
        )
        return
    var event_type: String = str(message.get("type", ""))
    var payload_value: Variant = message.get("payload", {})
    if not event_type.is_empty() and payload_value is Dictionary:
        event_received.emit(event_type, payload_value as Dictionary)
