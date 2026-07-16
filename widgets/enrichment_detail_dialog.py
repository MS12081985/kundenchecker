"""Read-only presentation of a typed enrichment result."""

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLabel, QPlainTextEdit, QPushButton, QScrollArea, QVBoxLayout, QWidget


class EnrichmentDetailDialog(QDialog):
    def __init__(self, result, parent=None):
        super().__init__(parent); self.setWindowTitle("Details der Websiteanalyse"); self.resize(720, 680)
        content = QWidget(); layout = QVBoxLayout(content); form = QFormLayout()
        form.addRow("Firma:", QLabel(result.company)); form.addRow("Website:", self._label(result.website))
        form.addRow("Score:", QLabel(f"{result.website_score}/100 – {result.website_score_category}"))
        form.addRow("Branche:", QLabel(f"{result.industry.industry} ({result.industry.confidence:.0%})"))
        form.addRow("Analysezeitpunkt:", QLabel(result.analyzed_at or "–")); layout.addLayout(form)
        imprint = result.imprint_data
        imprint_form = QFormLayout()
        values = (
            ("Inhaber:", ", ".join(imprint.owner_names)),
            ("Geschäftsführung:", ", ".join(imprint.managing_director_names)),
            ("Vertretung:", ", ".join(imprint.representative_names)),
            ("Rechtsform:", imprint.legal_form), ("Firma laut Impressum:", imprint.imprint_company_name),
            ("Impressumsadresse:", imprint.formatted_address()),
            ("Telefon:", imprint.imprint_phone), ("E-Mail:", imprint.imprint_email),
            ("USt-IdNr.:", imprint.vat_id), ("Registerart:", imprint.commercial_register_type),
            ("Registernummer:", imprint.commercial_register_number), ("Registergericht:", imprint.register_court),
            ("Konfidenz:", f"{imprint.imprint_extraction_confidence:.0%}" if imprint.imprint_extraction_confidence else ""),
            ("Quelle:", "\n".join(imprint.imprint_sources)),
        )
        for title, value in values:
            imprint_form.addRow(title, self._label(value))
        layout.addWidget(QLabel("Impressumsdaten")); layout.addLayout(imprint_form)
        open_imprint = QPushButton("Impressumsseite öffnen")
        open_imprint.setEnabled(bool(result.imprint_url))
        open_imprint.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(result.imprint_url)))
        layout.addWidget(open_imprint)
        score = QPlainTextEdit(); score.setReadOnly(True)
        score.setPlainText("\n".join(f"{'✓' if item.achieved else '✗'} {item.label}: {item.points}/{item.maximum}" for item in result.website_score_details.criteria))
        layout.addWidget(QLabel("Score-Aufschlüsselung")); layout.addWidget(score)
        details = QPlainTextEdit(); details.setReadOnly(True)
        social = "\n".join(f"{name}: {getattr(result.social_media, name)}" for name in result.social_media.active_platforms()) or "Keine erkannt"
        hints = "\n".join(result.industry.hints) or "Keine belastbaren Hinweise"
        details.setPlainText(f"Öffnungszeiten:\n{result.opening_hours.display_text() or 'Keine zuverlässig erkannt'}\n\nSocial Media:\n{social}\n\nBranchenhinweise:\n{hints}\n\nKurzbeschreibung:\n{result.short_description}\n\nFehler/Unsicherheit:\n{result.enrichment_error or 'Keine'}")
        layout.addWidget(details)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff); scroll.setWidget(content)
        outer = QVBoxLayout(self); outer.addWidget(scroll)
        buttons = QDialogButtonBox(QDialogButtonBox.Close); buttons.rejected.connect(self.reject); outer.addWidget(buttons)

    @staticmethod
    def _label(text):
        label = QLabel(text or "–"); label.setWordWrap(True); label.setToolTip(text or ""); return label
