from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QRadioButton,
    QVBoxLayout,
)


class StreetMatchingDialog(QDialog):
    """Erfragt die Matching-Genauigkeit vor einer Massenrecherche."""

    def __init__(self, use_street_matching=True, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Firmenprüfung starten")
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Soll der Straßenname beim Firmenabgleich berücksichtigt werden?", self))

        self.yes_option = QRadioButton("Ja (empfohlen)", self)
        self.yes_option.setChecked(bool(use_street_matching))
        layout.addWidget(self.yes_option)
        yes_description = QLabel(
            "Firmenname + Ort + Straße müssen übereinstimmen.\n"
            "Höhere Genauigkeit, aber weniger Treffer.",
            self,
        )
        yes_description.setIndent(24)
        layout.addWidget(yes_description)

        self.no_option = QRadioButton("Nein", self)
        self.no_option.setChecked(not bool(use_street_matching))
        layout.addWidget(self.no_option)
        no_description = QLabel(
            "Firmenname + Ort reichen aus.\n"
            "Mehr Treffer, aber höhere Verwechslungsgefahr.",
            self,
        )
        no_description.setIndent(24)
        layout.addWidget(no_description)

        self.remember_choice = QCheckBox("Auswahl merken", self)
        self.remember_choice.setChecked(True)
        layout.addWidget(self.remember_choice)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            parent=self,
        )
        buttons.button(QDialogButtonBox.Ok).setText("Starten")
        buttons.button(QDialogButtonBox.Cancel).setText("Abbrechen")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @property
    def use_street_matching(self):
        return self.yes_option.isChecked()

    @property
    def remember(self):
        return self.remember_choice.isChecked()
