# Changelog

## 1.2.1

- Kontrollierte, transaktionale Dubletten-Zusammenführung über stabile SQLite-IDs.
- CRM-Aktivitäten, Tags, Notizen und Wiedervorlagen bleiben beim Merge erhalten.
- Automatische zeitgestempelte SQLite-Backups vor Datenbereinigungen.
- Strenge Telefonnummernprüfung und internationale Normalisierung mit `phonenumbers`.
- Vorschauwerkzeug zur Bereinigung gespeicherter Telefonnummern und Kontaktstatus.
- Kundenexport mit sichtbarer Datenmenge, exakten Statusgruppen, Markierung und optionalen CRM-Feldern.
- Formatierter Excel-Export sowie CSV-Ausgabe mit UTF-8-BOM.

## 1.1.0

- Offline-Lizenzformat `.kcl` mit Ed25519-Signatur eingeführt.
- Lizenzdialog um Status, Restkontingent und Geräte-ID-Kopieren erweitert.
- Separaten Entwickler-Lizenzgenerator vorbereitet.

## 1.0.1

- Offline-Ed25519-Lizenzprüfung ohne Serverkommunikation.
- Recherchefunktionen werden ohne gültige lokale Lizenz gesperrt.
- Nutzungslimits und Lizenzdateien werden lokal verwaltet.

## 1.0.0

- Erste installierbare macOS-App als PyInstaller-Bundle vorbereitet.
- Importvorlage und unveränderliche Ressourcen werden ins Bundle aufgenommen.
- Schreibbare Daten werden in der macOS-App im Application-Support-Verzeichnis abgelegt.

## 0.9.0

- Moderner Startdialog bei jedem Programmstart mit Excel-, Vorlage- und Dashboard-Aktion.

- Excel-Importvorlage im Programm speicherbar.
- Import prüft die Pflichtspalte `KUNDENNAME`.

- Stabilisierung der UI- und Tabellenansicht.
- NaN-Werte werden leer dargestellt und als Tooltips verfügbar gemacht.
- Tabellenbreiten werden nicht mehr bei jedem Inhalt automatisch neu berechnet.
- Recherche-Timeout wird aus den Einstellungen zur Laufzeit angewendet.

## 0.8.2

- Rechercheberichte als eigene Hauptseite ergänzt.
- Berichtfilter, Detailansicht und Firmenwechsel hinzugefügt.
- Berichtsnavigation über Toolbar, Menü und Ctrl/Cmd+3.

## 0.8.1

- Permanente Dashboard-/Kunden-Navigation in der Toolbar ergänzt.
- Zentraler Seitenwechsel über den ApplicationController.
- Fensteranzeige beim Start bleibt unabhängig von der Navigation.

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
## 1.2.0

- Lokales CRM mit Ansprechpartnern, Status, Priorität, Notizen und Wiedervorlagen
- Chronologischer Kontaktverlauf mit SQLite-Persistenz
- Google-Maps-Suche über externe Maps-URLs ohne API-Schlüssel
- CRM-Kennzahlen im Dashboard und CRM-Felder im Kundenexport
