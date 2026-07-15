"""Cross-platform coordination for a single application instance per user."""

from __future__ import annotations

import logging
from enum import Enum
from pathlib import Path

from PySide6.QtCore import QLockFile, QObject, QStandardPaths, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket


logger = logging.getLogger(__name__)
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)


class InstanceResult(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    ERROR = "error"


class SingleInstanceService(QObject):
    activation_requested = Signal()

    def __init__(self, name="de.mssoftware.kundenchecker", parent=None, lock_directory=None):
        super().__init__(parent)
        self.name = name
        self.server = QLocalServer(self)
        self.server.newConnection.connect(self._accept_connections)
        self._clients = set()
        runtime = lock_directory or QStandardPaths.writableLocation(QStandardPaths.RuntimeLocation)
        if not runtime:
            runtime = QStandardPaths.writableLocation(QStandardPaths.TempLocation)
        lock_path = Path(runtime) / f"{name}.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = QLockFile(str(lock_path))
        self._lock.setStaleLockTime(10_000)
        self.error_message = ""

    def start_or_notify(self) -> InstanceResult:
        if self._notify_running_instance():
            logger.info("Zweite KundenChecker-Instanz erkannt; Aktivierung gesendet")
            return InstanceResult.SECONDARY

        if not self._lock.tryLock(500):
            if self._notify_running_instance(timeout_ms=500):
                logger.info("Zweite KundenChecker-Instanz nach parallelem Start erkannt")
                return InstanceResult.SECONDARY
            self.error_message = "Eine weitere Instanz startet bereits, konnte aber nicht aktiviert werden."
            logger.error("Single-Instance-Lock belegt, lokaler Server nicht erreichbar")
            return InstanceResult.ERROR

        # Another process may have started its server while this process waited for the lock.
        if self._notify_running_instance():
            self._lock.unlock()
            return InstanceResult.SECONDARY

        if QLocalServer.removeServer(self.name):
            logger.info("Veralteter lokaler Servereintrag entfernt")
        if not self.server.listen(self.name):
            self.error_message = "Der lokale Instanzdienst konnte nicht gestartet werden."
            logger.error("Lokaler Server konnte nicht gestartet werden: %s", self.server.errorString())
            self._lock.unlock()
            return InstanceResult.ERROR
        logger.info("Erste KundenChecker-Instanz gestartet")
        return InstanceResult.PRIMARY

    def _notify_running_instance(self, timeout_ms=200) -> bool:
        socket = QLocalSocket()
        socket.connectToServer(self.name)
        if not socket.waitForConnected(timeout_ms):
            return False
        if socket.write(b"activate\n") < 0 or not socket.waitForBytesWritten(timeout_ms):
            logger.error("Aktivierungsnachricht konnte nicht gesendet werden: %s", socket.errorString())
            socket.disconnectFromServer()
            return False
        socket.disconnectFromServer()
        logger.info("Aktivierungsnachricht gesendet")
        return True

    def _accept_connections(self):
        while self.server.hasPendingConnections():
            socket = self.server.nextPendingConnection()
            self._clients.add(socket)
            socket.readyRead.connect(lambda current=socket: self._read_message(current))
            socket.disconnected.connect(lambda current=socket: self._discard_client(current))
            if socket.bytesAvailable():
                self._read_message(socket)

    def _read_message(self, socket):
        messages = bytes(socket.readAll()).splitlines()
        if b"activate" in messages:
            logger.info("Aktivierungsnachricht empfangen")
            self.activation_requested.emit()

    def _discard_client(self, socket):
        self._clients.discard(socket)
        socket.deleteLater()

    def close(self):
        for socket in tuple(self._clients):
            socket.abort()
        self._clients.clear()
        if self.server.isListening():
            self.server.close()
            QLocalServer.removeServer(self.name)
        if self._lock.isLocked():
            self._lock.unlock()

    def __del__(self):
        self.close()
