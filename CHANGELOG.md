# Changelog

## 0.8.0

- Neues Dashboard mit Statuskarten, Kennzahlen und Schnellaktionen.
- Dashboard-/Kunden-Navigation per Ansicht und Tastenkürzel.
- Dashboard-Daten werden signalbasiert durch den Controller aktualisiert.

## 0.7.8

- Vierstufige Statuslogik: Vollständig, Aktiv, Nicht aktiv, Nicht gefunden.
- Cacheeinträge werden beim Lesen nach der aktuellen Kontaktvollständigkeit neu bewertet.
- Statusfarben und Rechercheberichte an die neue Auswertung angepasst.

## 0.7.4

- Filterdialog für intelligente Massenrecherchen ergänzt.
- Filterkriterien werden im Controller mit ODER verknüpft.
- Live-Vorschau, Dauerabschätzung und Bestätigung vor dem Start ergänzt.

## 0.7.5

- Telefon- und E-Mail-Validierung verbessert.
- Kontaktseiten und Kontaktkandidaten werden begrenzt und bewertet durchsucht.
- Dokument- und Tracking-URLs werden vor dem Speichern bereinigt.
- Status wird aus Website-, Telefon- und E-Mail-Qualität berechnet.
- Ungültige Cachewerte werden bei Verwendung korrigiert.

## 0.7.6

- Einzelne Firmen können den Cache gezielt umgehen und erneut recherchiert werden.
- Markierte sowie nicht aktive Firmen können gesammelt neu recherchiert werden.
- Die bestehende Recherchepipeline unterstützt `force_refresh`.
## 0.7.7

- Strukturierte Rechercheberichte für Einzel- und Massenrecherche
- Vorher-/Nachher-Vergleich, Qualitätsauswertung und Berichtsexport
- Letzten Recherchebericht anzeigen und als Excel/CSV exportieren
