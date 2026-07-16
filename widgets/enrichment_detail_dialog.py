"""Read-only presentation of a typed enrichment result."""

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLabel, QPlainTextEdit, QScrollArea, QVBoxLayout, QWidget


class EnrichmentDetailDialog(QDialog):
    def __init__(self, result, parent=None):
        super().__init__(parent); self.setWindowTitle("Details der Websiteanalyse"); self.resize(720, 680)
        content = QWidget(); layout = QVBoxLayout(content); form = QFormLayout()
        form.addRow("Firma:", QLabel(result.company)); form.addRow("Website:", self._label(result.website))
        form.addRow("Score:", QLabel(f"{result.website_score}/100 – {result.website_score_category}"))
        form.addRow("Branche:", QLabel(f"{result.industry.industry} ({result.industry.confidence:.0%})"))
        form.addRow("Analysezeitpunkt:", QLabel(result.analyzed_at or "–")); layout.addLayout(form)
        score = QPlainTextEdit(); score.setReadOnly(True)
        score.setPlainText("\n".join(f"{'✓' if item.achieved else '✗'} {item.label}: {item.points}/{item.maximum}" for item in result.website_score_details.criteria))
        layout.addWidget(QLabel("Score-Aufschlüsselung")); layout.addWidget(score)
        details = QPlainTextEdit(); details.setReadOnly(True)
        social = "\n".join(f"{name}: {getattr(result.social_media, name)}" for name in result.social_media.active_platforms()) or "Keine erkannt"
        hints = "\n".join(result.industry.hints) or "Keine belastbaren Hinweise"
        details.setPlainText(f"Öffnungszeiten:\n{result.opening_hours.display_text() or 'Keine zuverlässig erkannt'}\n\nSocial Media:\n{social}\n\nBranchenhinweise:\n{hints}\n\nKurzbeschreibung:\n{result.short_description}\n\nFehler/Unsicherheit:\n{result.enrichment_error or 'Keine'}")
        layout.addWidget(details)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(content)
        outer = QVBoxLayout(self); outer.addWidget(scroll)
        buttons = QDialogButtonBox(QDialogButtonBox.Close); buttons.rejected.connect(self.reject); outer.addWidget(buttons)

    @staticmethod
    def _label(text):
        label = QLabel(text or "–"); label.setWordWrap(True); label.setToolTip(text or ""); return label
