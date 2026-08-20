from __future__ import annotations

from collections.abc import Callable

from PySide6.QtNetwork import QLocalServer, QLocalSocket


class SingleInstanceGate:
    """Coordinate a single GUI instance through Qt local IPC."""

    def __init__(self, server_name: str) -> None:
        self.server_name = server_name
        self._server: QLocalServer | None = None
        self._activation_handler: Callable[[], None] | None = None
        self._pending_activation = False

    def acquire(self) -> bool:
        """Return True for the primary instance; notify and return False otherwise."""
        if self.notify_primary(timeout_ms=150):
            return False

        server = QLocalServer()
        try:
            server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        except (AttributeError, TypeError):
            pass
        server.newConnection.connect(self._on_new_connection)
        if server.listen(self.server_name):
            self._server = server
            return True

        # A near-simultaneous launch may have won the listen race after our
        # first connection attempt. Retry before treating the name as stale.
        if self.notify_primary(timeout_ms=500):
            return False

        # Primarily useful on Unix after an unclean shutdown; on Windows this
        # is harmless and does not replace the no-file-lock design.
        QLocalServer.removeServer(self.server_name)
        if server.listen(self.server_name):
            self._server = server
            return True

        raise RuntimeError(f"无法建立单实例通信通道：{server.errorString()}")

    def release(self) -> None:
        """Release the local IPC endpoint before an intentional restart."""
        if self._server is not None:
            self._server.close()
            self._server = None
        QLocalServer.removeServer(self.server_name)

    def notify_primary(self, *, timeout_ms: int = 250) -> bool:
        socket = QLocalSocket()
        socket.connectToServer(self.server_name)
        if not socket.waitForConnected(timeout_ms):
            socket.abort()
            return False
        socket.write(b"activate\n")
        socket.flush()
        socket.waitForBytesWritten(timeout_ms)
        socket.disconnectFromServer()
        return True

    def set_activation_handler(self, handler: Callable[[], None]) -> None:
        self._activation_handler = handler
        if self._pending_activation:
            self._pending_activation = False
            handler()

    def _request_activation(self) -> None:
        if self._activation_handler is None:
            self._pending_activation = True
            return
        self._activation_handler()

    def _on_new_connection(self) -> None:
        if self._server is None:
            return
        while self._server.hasPendingConnections():
            socket = self._server.nextPendingConnection()
            if socket is None:
                break

            def read_request(sock: QLocalSocket = socket) -> None:
                payload = bytes(sock.readAll()).decode("utf-8", errors="ignore").strip()
                if payload == "activate":
                    self._request_activation()
                sock.disconnectFromServer()
                sock.deleteLater()

            socket.readyRead.connect(read_request)
            if socket.bytesAvailable() > 0:
                read_request()
