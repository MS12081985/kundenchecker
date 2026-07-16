from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMenu,
    QSizePolicy,
    QStackedWidget,
    QToolButton,
    QWidget,
)


class Toolbar(QWidget):
    """Compact page-dependent action bar backed by shared QActions."""

    DASHBOARD = 0
    CUSTOMERS = 1
    REPORTS = 2

    def __init__(self, actions, parent=None):
        super().__init__(parent)
        self.actions = actions
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        self.stack = QStackedWidget(self)
        self.stack.addWidget(QWidget(self))
        self.stack.addWidget(self._customer_bar())
        self.stack.addWidget(self._report_bar())
        layout.addWidget(self.stack)

    @staticmethod
    def _action_button(action):
        button = QToolButton()
        button.setDefaultAction(action)
        button.setToolButtonStyle(Qt.ToolButtonTextOnly)
        button.setMinimumHeight(32)
        return button

    @staticmethod
    def _menu_button(text, actions):
        button = QToolButton()
        button.setText(text)
        button.setPopupMode(QToolButton.InstantPopup)
        button.setToolButtonStyle(Qt.ToolButtonTextOnly)
        button.setMinimumHeight(32)
        menu = QMenu(button)
        menu.addActions(actions)
        button.setMenu(menu)
        return button

    def _customer_bar(self):
        bar = QWidget(self)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.btn_open = self._action_button(self.actions["open"])
        self.research_button = self._menu_button("🔍 Recherche ▾", [
            self.actions["research"],
            self.actions["research_refresh"],
            self.actions["bulk"],
            self.actions["marked_refresh"],
            self.actions["inactive_refresh"],
            self.actions["enrichment_all"],
            self.actions["enrichment_marked"],
            self.actions["enrichment_missing"],
        ])
        self.quality_button = self._menu_button("🧹 Datenqualität ▾", [
            self.actions["duplicates"],
            self.actions["import_check"],
            self.actions["phone_cleanup"],
            self.actions["enrichment_refresh"],
            self.actions["import_report"],
        ])
        self.btn_export = self._action_button(self.actions["export"])
        for widget in (self.btn_open, self.research_button, self.quality_button, self.btn_export):
            layout.addWidget(widget)
        layout.addStretch()
        return bar

    def _report_bar(self):
        bar = QWidget(self)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        for key in ("report_reload", "report_export", "report_detail", "report_company"):
            layout.addWidget(self._action_button(self.actions[key]))
        layout.addStretch()
        return bar

    def set_context(self, page_index):
        self.stack.setCurrentIndex(page_index)
        self.setVisible(page_index != self.DASHBOARD)

    def set_enabled(self, enabled):
        for action in self.actions.values():
            action.setEnabled(bool(enabled))
