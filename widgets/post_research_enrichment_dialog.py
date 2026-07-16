"""Presentation-only prompt for website enrichment after research."""

from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QLabel, QPushButton, QVBoxLayout,
)


class PostResearchEnrichmentDialog(QDialog):
    def __init__(self, offer, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Firmenprüfung abgeschlossen")
        layout = QVBoxLayout(self)
        if offer.single:
            text = "Die Firma wurde geprüft.\nSoll die gefundene Website jetzt analysiert werden?"
        else:
            text = (
                "Die Firmenprüfung ist abgeschlossen.\n\n"
                f"Verarbeitet: {offer.processed_count}\n"
                f"Mit gültiger Website: {offer.website_count}\n"
                f"Davon noch nicht analysiert: {offer.pending_count}"
            )
            if offer.error_count:
                text += f"\nWegen Recherchefehlern übersprungen: {offer.error_count}"
            text += "\n\nSollen diese Websites jetzt analysiert werden?"
        label = QLabel(text, self)
        label.setWordWrap(True)
        layout.addWidget(label)

        self.force_refresh = QCheckBox("Bereits vorhandene aktuelle Analysen erneut durchführen", self)
        layout.addWidget(self.force_refresh)
        self.do_not_ask = QCheckBox("Diese Frage künftig nicht mehr anzeigen", self)
        layout.addWidget(self.do_not_ask)

        buttons = QDialogButtonBox(self)
        analyze = QPushButton("Websites analysieren", self)
        later = QPushButton("Später", self)
        buttons.addButton(analyze, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton(later, QDialogButtonBox.ButtonRole.RejectRole)
        analyze.clicked.connect(self.accept)
        later.clicked.connect(self.reject)
        layout.addWidget(buttons)

