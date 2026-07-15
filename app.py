import sys

from PySide6.QtWidgets import QApplication

from controllers.application_controller import ApplicationController


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("KundenChecker")
    app.setOrganizationName("MS Software")

    controller = ApplicationController()
    controller.quit_requested.connect(app.quit)
    controller.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
