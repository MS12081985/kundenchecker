import sys

from config.startup_profiler import StartupProfiler

STARTUP_PROFILER = StartupProfiler()

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMessageBox, QSplashScreen, QWidget

from services.single_instance_service import InstanceResult, SingleInstanceService


class ImmediateSplashScreen(QSplashScreen):
    """QSplashScreen without its blocking wait-for-exposure event loop."""

    def event(self, event):
        return QWidget.event(self, event)


def _create_splash():
    from config.app_config import AppConfig

    pixmap = QPixmap(560, 260)
    pixmap.fill(QColor("#20252b"))
    painter = QPainter(pixmap)
    painter.setPen(QColor("#f4f6f8"))
    painter.setFont(QFont("Sans Serif", 28, QFont.Bold))
    painter.drawText(36, 82, "KundenChecker")
    painter.setPen(QColor("#b9c2cc"))
    painter.setFont(QFont("Sans Serif", 13))
    painter.drawText(38, 116, f"Version {AppConfig.VERSION}")
    painter.setPen(QColor("#3a84d8"))
    painter.drawRect(0, 250, 560, 10)
    painter.end()
    return ImmediateSplashScreen(pixmap)


def _splash_status(app, splash, message):
    splash.showMessage(message, Qt.AlignLeft | Qt.AlignBottom, QColor("#f4f6f8"))
    app.processEvents()


def activate_running_window(app, main_window):
    """Bring the current modal window, or otherwise the main window, forward."""
    target = app.activeModalWidget() or app.activeWindow() or main_window
    if target.isMinimized():
        target.showNormal()
    else:
        target.show()
    target.raise_()
    target.activateWindow()
    # A queued repeat improves activation reliability after macOS space changes.
    from PySide6.QtCore import QTimer

    QTimer.singleShot(0, target.raise_)
    QTimer.singleShot(0, target.activateWindow)


def main():
    profiler = STARTUP_PROFILER
    app = QApplication(sys.argv)
    profiler.mark("QApplication erzeugt")
    app.setApplicationName("KundenChecker")
    app.setOrganizationName("MS Software")

    single_instance = SingleInstanceService()
    instance_result = single_instance.start_or_notify()
    if instance_result == InstanceResult.SECONDARY:
        return 0
    if instance_result == InstanceResult.ERROR:
        QMessageBox.critical(None, "KundenChecker", single_instance.error_message)
        return 1
    app.aboutToQuit.connect(single_instance.close)

    splash = _create_splash()
    splash.show()
    _splash_status(app, splash, "Anwendung wird gestartet …")
    profiler.mark("Splash sichtbar")

    try:
        from loguru import logger
        from config.app_config import AppConfig
        AppConfig.LOG_DIR.mkdir(parents=True, exist_ok=True)
        logger.add(AppConfig.LOG_FILE, rotation="1 MB", retention=3, encoding="utf-8")

        _splash_status(app, splash, "Oberfläche wird geladen …")
        from controllers.application_controller import ApplicationController

        controller = ApplicationController(
            startup_profiler=profiler,
            startup_status=lambda message: _splash_status(app, splash, message),
        )
        profiler.mark("ApplicationController erzeugt")
        controller.quit_requested.connect(app.quit)
        app.aboutToQuit.connect(controller.shutdown_background_tasks)
        pending_activation = [False]

        def activate_primary():
            if controller.window.isVisible():
                activate_running_window(app, controller.window)
            else:
                pending_activation[0] = True

        single_instance.activation_requested.connect(activate_primary)

        def finish_splash():
            _splash_status(app, splash, "Fertig")
            splash.finish(controller.window)
            profiler.mark("Splash geschlossen")
            profiler.log_summary()
            if pending_activation[0]:
                pending_activation[0] = False
                activate_running_window(app, controller.window)

        controller.main_window_visible.connect(finish_splash)
        controller.start()
    except Exception as error:
        try:
            from loguru import logger
            logger.exception("Anwendungsstart fehlgeschlagen")
        finally:
            splash.close()
            QMessageBox.critical(None, "KundenChecker", f"Die Anwendung konnte nicht gestartet werden.\n\n{error}\n\nDetails stehen in logs/startup.log.")
        return 1

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
