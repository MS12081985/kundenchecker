# KundenChecker

KundenChecker ist eine Desktop-Anwendung auf Basis von **Python** und **PySide6**.

Die Anwendung dient dazu, Kundendaten aus Excel-Dateien einzulesen, zu durchsuchen, Dubletten zu erkennen und Firmen automatisch im Internet zu recherchieren.

---

# Funktionen

## Bereits umgesetzt

- Excel-Dateien (.xls / .xlsx) importieren
- Live-Suche
- Dublettenerkennung
- SQLite-Datenbank
- Firmenrecherche
- Website-Suche
- Kontaktdaten aus Webseiten auslesen

---

## Geplant

- Alle Firmen automatisch prüfen
- Fortschrittsanzeige
- Intelligente Website-Erkennung
- Verbesserte Dublettenerkennung
- Excel-Export
- Statistiken
- Einstellungen

---

# Projektstruktur

```
kundenchecker/
│
├── app.py
├── requirements.txt
├── README.md
│
├── database/
├── excel/
├── services/
├── ui/
├── widgets/
├── exports/
├── icons/
└── tests/
```

---

# Installation

Virtuelle Umgebung erstellen:

```bash
python -m venv .venv
```

Aktivieren:

### macOS / Linux

```bash
source .venv/bin/activate
```

### Windows

```powershell
.venv\Scripts\activate
```

Pakete installieren:

```bash
pip install -r requirements.txt
```

---

# Starten

```bash
python app.py
```

---

# Version

Aktuelle Version:

**v0.6.0**

---

# Roadmap

## Version 0.7

- Alle Firmen prüfen
- Fortschrittsbalken
- Hintergrund-Thread

## Version 0.8

- Intelligente Website-Suche
- Kontaktseite durchsuchen
- Impressum auswerten

## Version 0.9

- Excel-Export
- Statistik
- Log-Dateien

## Version 1.0

- Fertige Desktop-Anwendung
- Automatische Datenpflege
- Optimierte Recherche
- Stabile Version
# Dashboard

KundenChecker startet mit einem Dashboard. Es zeigt Statusverteilungen, fehlende Kontaktdaten, sichtbare Datensätze und die letzte Recherche. Schnellaktionen führen direkt zum Excel-Import, zur Kundenliste, Recherche, Bericht oder Export.

Die manuelle Website-Prüfung kann separat gestartet werden:

```bash
python manual_website_check.py
```

Rechercheberichte sind über die Hauptnavigation als eigene Seite mit Filtern,
Detailansicht und Export erreichbar.

Über **Datei → Excel-Importvorlage speichern** kann die Importvorlage kopiert werden.
`KUNDENNAME` ist eine Pflichtspalte, `CITY` wird für präzisere Recherchen empfohlen.
Die Beispielzeile sollte vor dem Import gelöscht werden.

## Installation und Start

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```

Automatisierte Tests:

```bash
.venv/bin/python -m pytest -q
```

## macOS-App

Der lokale Build erzeugt mit `scripts/build_macos.sh` eine nicht signierte
`dist/KundenChecker.app` und `release/KundenChecker-1.0.0.dmg`. Beim ersten
Start kann macOS einen Sicherheitshinweis anzeigen; dann per Rechtsklick →
Öffnen starten. Für die lokale App gelten die Hinweise in `BUILDING.md`.
