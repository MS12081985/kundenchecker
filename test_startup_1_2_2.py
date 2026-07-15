import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from config.startup_profiler import StartupProfiler
from controllers.application_controller import ApplicationController


APP = QApplication.instance() or QApplication([])


def test_heavy_modules_are_lazy_after_controller_creation():
    controller = ApplicationController()
    assert controller._customer_service is None
    assert controller._research_service is None
    assert controller._customer_export_service is None


def test_main_window_is_requested_once_before_start_dialog():
    profiler = StartupProfiler()
    controller = ApplicationController(startup_profiler=profiler)
    controller.start_dialog_requested.disconnect(controller.window.show_start_dialog)
    controller.license_dialog_requested.disconnect(controller.window.show_license_dialog)
    controller.settings["general"]["check_updates_on_start"] = False
    requested = []
    dialogs = []
    controller.window_requested.connect(lambda: requested.append("window"))
    controller.start_dialog_requested.connect(lambda _files: dialogs.append("dialog"))
    controller.start()
    APP.processEvents()
    assert requested == ["window"]
    assert dialogs == ["dialog"]
    labels = [label for label, _elapsed in profiler.milestones]
    assert labels.index("Hauptfenster sichtbar") < labels.index("Startdialog sichtbar")


def test_research_service_reuses_crm_database():
    controller = ApplicationController()
    assert controller.research_service.database is controller.crm_service.database
