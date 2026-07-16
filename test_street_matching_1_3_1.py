import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pandas as pd
from PySide6.QtWidgets import QApplication

from config.settings import Settings
from controllers.application_controller import ApplicationController
from widgets.street_matching_dialog import StreetMatchingDialog
from workers.research_worker import ResearchWorker


APP = QApplication.instance() or QApplication([])


class License:
    def can_research(self, _amount=1):
        return True, "Testlizenz gültig"


class Store:
    def __init__(self):
        self.saved = []

    def save(self, settings):
        normalized = Settings.normalize(settings)
        self.saved.append(normalized)
        return normalized


def test_street_matching_setting_defaults_to_enabled():
    assert Settings.defaults()["research"]["use_street_matching"] is True
    assert Settings.normalize({})["research"]["use_street_matching"] is True


def test_street_matching_dialog_reflects_saved_choice():
    enabled = StreetMatchingDialog(True)
    disabled = StreetMatchingDialog(False)
    assert enabled.use_street_matching is True
    assert disabled.use_street_matching is False
    assert enabled.remember is True


def test_confirmed_bulk_research_forwards_and_remembers_disabled_choice():
    controller = ApplicationController()
    controller.license_service = License()
    controller.settings_store = Store()
    controller._pending_research_worklist = pd.DataFrame([
        {"KUNDENNAME": "Firma", "CITY": "Berlin", "STRASSE": "Hauptstraße 10"}
    ])
    started = []
    controller._start_research_worker = lambda frame, force_refresh=False, use_street_matching=True: started.append(
        (len(frame), force_refresh, use_street_matching)
    )

    controller.start_confirmed_research(
        {"use_street_matching": False, "remember_street_matching": True},
        False,
    )

    assert started == [(1, False, False)]
    assert controller.settings_store.saved[-1]["research"]["use_street_matching"] is False


def test_refresh_bulk_always_uses_street_matching():
    controller = ApplicationController()
    controller.license_service = License()
    controller.settings_store = Store()
    controller._pending_research_worklist = pd.DataFrame([
        {"KUNDENNAME": "Firma", "CITY": "Berlin", "STRASSE": "Hauptstraße 10"}
    ])
    started = []
    controller._start_research_worker = lambda frame, force_refresh=False, use_street_matching=True: started.append(
        use_street_matching
    )

    controller.start_confirmed_research({"use_street_matching": False}, True)

    assert started == [True]
    assert controller.settings_store.saved == []


def test_worker_forwards_street_matching_choice():
    class Service:
        cancelled = False

        def research_dataframe(
            self,
            dataframe,
            progress_callback=None,
            force_refresh=False,
            error_callback=None,
            use_street_matching=True,
        ):
            self.received = use_street_matching
            return []

        def cancel(self):
            self.cancelled = True

    worker = ResearchWorker(pd.DataFrame([{"KUNDENNAME": "Firma"}]), use_street_matching=False)
    worker.service = Service()
    worker.run()
    assert worker.service.received is False
