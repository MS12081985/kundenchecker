import os
import time
import uuid

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEventLoop, Qt
from PySide6.QtNetwork import QLocalServer
from PySide6.QtWidgets import QApplication, QDialog, QWidget

from app import activate_running_window
from services.single_instance_service import InstanceResult, SingleInstanceService


APP = QApplication.instance() or QApplication([])


def _name():
    return f"kc-{uuid.uuid4().hex[:12]}"


def _process_until(predicate, timeout_ms=1000):
    deadline = time.monotonic() + timeout_ms / 1000
    while not predicate() and time.monotonic() < deadline:
        APP.processEvents(QEventLoop.AllEvents, 20)
    return predicate()


def test_first_instance_listens_and_clean_restart_works(tmp_path):
    name = _name()
    first = SingleInstanceService(name, lock_directory=tmp_path)
    assert first.start_or_notify() == InstanceResult.PRIMARY
    assert first.server.isListening()
    first.close()
    restarted = SingleInstanceService(name, lock_directory=tmp_path)
    assert restarted.start_or_notify() == InstanceResult.PRIMARY
    restarted.close()


def test_second_instance_notifies_primary_and_does_not_listen(tmp_path):
    name = _name()
    first = SingleInstanceService(name, lock_directory=tmp_path)
    second = SingleInstanceService(name, lock_directory=tmp_path)
    assert first.start_or_notify() == InstanceResult.PRIMARY
    activations = []
    first.activation_requested.connect(lambda: activations.append(True))
    assert second.start_or_notify() == InstanceResult.SECONDARY
    assert not second.server.isListening()
    assert _process_until(lambda: activations == [True])
    first.close()


class TrackingWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.raised = 0
        self.activated = 0

    def raise_(self):
        self.raised += 1
        super().raise_()

    def activateWindow(self):
        self.activated += 1
        super().activateWindow()


def test_minimized_main_window_is_restored_raised_and_activated():
    window = TrackingWidget()
    window.showMinimized()
    APP.processEvents()
    activate_running_window(APP, window)
    APP.processEvents()
    assert not window.isMinimized()
    assert window.raised >= 1
    assert window.activated >= 1
    window.close()


def test_active_modal_dialog_is_activated_instead_of_new_window():
    main = TrackingWidget()
    main.show()
    dialog = QDialog(main)
    dialog.setWindowModality(Qt.ApplicationModal)
    dialog.show()
    APP.processEvents()
    calls = []
    dialog.raise_ = lambda: calls.append("raise")
    dialog.activateWindow = lambda: calls.append("activate")
    activate_running_window(APP, main)
    APP.processEvents()
    assert "raise" in calls and "activate" in calls
    dialog.close()
    main.close()


def test_active_server_is_never_removed_by_second_instance(tmp_path):
    name = _name()
    first = SingleInstanceService(name, lock_directory=tmp_path)
    second = SingleInstanceService(name, lock_directory=tmp_path)
    third = SingleInstanceService(name, lock_directory=tmp_path)
    assert first.start_or_notify() == InstanceResult.PRIMARY
    assert second.start_or_notify() == InstanceResult.SECONDARY
    assert first.server.isListening()
    assert third.start_or_notify() == InstanceResult.SECONDARY
    first.close()


def test_near_simultaneous_attempts_result_in_one_primary(tmp_path):
    name = _name()
    candidates = [
        SingleInstanceService(name, lock_directory=tmp_path),
        SingleInstanceService(name, lock_directory=tmp_path),
    ]
    results = [candidate.start_or_notify() for candidate in candidates]
    assert results.count(InstanceResult.PRIMARY) == 1
    assert results.count(InstanceResult.SECONDARY) == 1
    for candidate in candidates:
        candidate.close()


def test_stale_server_entry_after_crash_is_removed(tmp_path):
    name = _name()
    stale = QLocalServer()
    assert stale.listen(name)
    socket_path = stale.fullServerName()
    stale.close()
    # Recreate the filesystem remnant left by an unclean Unix process exit.
    if socket_path.startswith("/"):
        with open(socket_path, "wb"):
            pass
    service = SingleInstanceService(name, lock_directory=tmp_path)
    assert service.start_or_notify() == InstanceResult.PRIMARY
    assert service.server.isListening()
    service.close()
