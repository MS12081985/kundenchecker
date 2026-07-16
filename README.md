# KundenChecker

KundenChecker ist eine Desktop-Anwendung auf Basis von **Python** und **PySide6**.

Pro angemeldetem Benutzer läuft nur eine App-Instanz; ein erneuter Start holt
die bereits geöffnete Anwendung in den Vordergrund.

Die optionale Updateprüfung benötigt Internetzugang und verwendet die
öffentliche GitHub-Releases-API. KundenChecker funktioniert weiterhin
vollständig offline. Heruntergeladene Updates werden nicht automatisch
installiert; die Installation erfolgt weiterhin manuell.

Die Anwendung dient dazu, Kundendaten aus Excel-Dateien einzulesen, zu durchsuchen, Dubletten zu erkennen und Firmen automatisch im Internet zu recherchieren.

Vor der Übernahme prüft KundenChecker Excel-Dateien auf fehlende Pflichtwerte,
ungültige Kontaktdaten und Dubletten. Identische und sichere ergänzende
Datensätze können nach Bestätigung bereinigt werden. Die Originaldatei bleibt
unverändert; optional wird eine neue `_bereinigt.xlsx`-Datei mit Importbericht
gespeichert. Das Dashboard zeigt einen transparent berechneten
Datenqualitäts-Score.

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

**v1.3.2**

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

## Offline-Lizenzierung

Die Recherche ist in v1.0.1 nur mit einer lokal signierten Ed25519-Lizenz
verfügbar. Lizenz- und Nutzungsdateien liegen im Application-Support-Ordner;
es gibt keine Online-Aktivierung. Das Entwicklerwerkzeug `tools/create_license.py`
benötigt einen privaten Schlüssel außerhalb des Repositorys.

Ab Version 1.1.0 werden Lizenzen als `.kcl` importiert. Die Lizenzen sind
übertragbar und nicht an Geräte gebunden. Der öffentliche Schlüssel ist in
der App enthalten; der private Schlüssel bleibt ausschließlich beim
Entwickler.

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
`dist/KundenChecker.app` und `release/KundenChecker-1.3.2.dmg`. Beim ersten
Start kann macOS einen Sicherheitshinweis anzeigen; dann per Rechtsklick →
Öffnen starten. Für die lokale App gelten die Hinweise in `BUILDING.md`.
## CRM und Google Maps (1.2.0)

Kunden können lokal mit Ansprechpartner, Position, Direktkontakt, Kundenstatus,
Priorität, Tags, Notizen und Wiedervorlagen ergänzt werden. Aktivitäten werden
im Kontaktverlauf in SQLite gespeichert. Über „In Google Maps öffnen“ wird eine
kodierte Suchadresse im externen Browser geöffnet; es wird keine Google-Maps-API
oder ein API-Schlüssel verwendet.

## Datenbereinigung (1.2.1)

Unter **Extras → Dubletten finden** können Datenbank-Dubletten geprüft und
kontrolliert zusammengeführt werden. Ein Hauptdatensatz wird anhand vorhandener
CRM-Aktivitäten und der Datenqualität vorgeschlagen; abweichende Werte werden
vor dem Merge ausgewählt. Tags und Notizen werden vereinigt, Aktivitäten werden
übertragen und Wiedervorlagen bleiben erhalten. Vor jeder Änderung entsteht ein
zeitgestempeltes SQLite-Backup im zentralen Benutzerdatenordner.

Unter **Extras → Telefonnummern neu validieren** zeigt eine Vorschau gültige,
ungültige und normalisierte Nummern sowie Statusänderungen. Erst nach Bestätigung
und erfolgreichem Backup werden Änderungen transaktional gespeichert. Die Prüfung
nutzt `phonenumbers`, akzeptiert vollständige deutsche und internationale Nummern
und verwirft lokale Nummern ohne Vorwahl wie `9 50189`, Datums-/ID-Werte,
Wiederholungsmuster und Faxnummern als Haupttelefon. Gültige Nummern werden im
internationalen Format gespeichert.

## Gefilterter Kundenexport (1.2.1)

Der Exportdialog bietet die sichtbaren Kunden, einzelne Kontaktstatusgruppen,
markierte Kunden oder ausdrücklich alle geladenen Datensätze als Datenumfang an.
Statusfilter werden innerhalb der aktuellen Suche und der vorhandenen
Kundenfilter angewendet. CRM-Felder können ein- oder ausgeschlossen werden;
interne Schlüssel werden standardmäßig nicht exportiert. Unterstützt werden
formatierte Excel-Arbeitsmappen und CSV-Dateien mit UTF-8-BOM.

## Schneller Anwendungsstart (1.2.2)

Beim Start zeigt KundenChecker unmittelbar einen Splash Screen mit dem aktuellen
Initialisierungsstatus. Das Hauptfenster erscheint anschließend automatisch;
Recherche-, Export- und selten verwendete Dialogmodule werden erst bei Bedarf
geladen.

## Bekannte Einschränkung

Vollständig identische Excel-Dubletten ohne getrennte Datenbank-IDs können
erkannt werden, aber nicht immer automatisch zusammengeführt werden.

## Kostenlose Websiteanalyse (1.3.0)

KundenChecker analysiert auf Wunsch die bereits sicher zugeordnete offizielle
Firmenwebsite. Die begrenzte Analyse erkennt technische und inhaltliche Signale
wie HTTPS/TLS, Impressum, Datenschutz, Kontaktseite, Kontaktformular,
Öffnungszeiten, Social-Media-Profile und strukturierte Daten. Daraus entstehen
ein transparenter Website-Score, eine regelbasierte Branchenzuordnung und eine
kurze, lokal erzeugte Beschreibung. Die Anreicherungsfelder können im
Kundenexport ein- oder ausgeschlossen werden.

Aus einer vorhandenen Impressumsseite werden außerdem nur klar belegte
Unternehmensangaben wie Inhaber und Geschäftsführung, Rechtsform,
Impressumsadresse, validierte Kontaktdaten, Umsatzsteuer-ID sowie
Handelsregister und Registergericht extrahiert. Diese Angaben bleiben getrennte
Analysefelder und überschreiben Recherche- oder CRM-Daten nicht automatisch.

Über **Recherche → Alle Websites analysieren** lässt sich eine Massenanalyse für
sichtbare, geladene oder markierte Kunden starten. Zusätzlich können noch nicht
analysierte, veraltete, schwache oder zuvor fehlerhafte Websites ausgewählt
werden. Eine Vorschau zeigt Arbeitsliste und übersprungene aktuelle Analysen;
fertige Ergebnisse erscheinen bereits während der laufenden Analyse in der
Kundenansicht.

Die Funktion verwendet keine kostenpflichtige API und keine Cloud-KI. Es werden
keine Kundendaten an einen KI-Anbieter übertragen, keine Google-Bewertungen
abgerufen und weder Google Maps noch Social-Media-Plattformen gescrapt. Grundlage
sind ausschließlich öffentlich sichtbare Angaben der jeweiligen Firmenwebsite.
Die Kernfunktionen der Anwendung bleiben ohne KI-Anbieter und offline nutzbar;
für eine neue Websiteanalyse ist naturgemäß ein Internetzugang erforderlich.

Automatische Erkennungen können unvollständig sein. Website-Score, Impressums-
und Datenschutzerkennung sind weder eine rechtliche Bewertung noch eine Garantie
für Konformität, Qualität oder geschäftlichen Erfolg.
