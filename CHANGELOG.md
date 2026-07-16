# Changelog

## 1.3.2

- Seitenabhängige Aktionsleiste für Dashboard, Kundenansicht und Berichte.
- Kompakte Recherche- und Datenqualitätsmenüs mit gemeinsam genutzten Aktionen.
- Responsives Dashboard mit umbrechenden Statuskarten und Schnellaktionen.
- Dashboard-Statuskarten öffnen die passende gefilterte Kundenansicht.
- Nach abgeschlossener Firmenprüfung kann direkt die Websiteanalyse gestartet werden.
- Erweiterte Impressumsanalyse für Inhaber, Geschäftsführung, Rechtsform, Adresse, Umsatzsteuer-ID und Handelsregister.

## 1.3.1

- Optionaler Straßenabgleich vor „Alle Firmen prüfen“, standardmäßig aktiviert.
- Auswahl kann in den bestehenden Einstellungen gespeichert werden.
- Einzel- und Wiederholungsrecherchen verwenden weiterhin verbindlich den Straßenabgleich.
- Websiteanalyse im Kundendetail vor den CRM-Feldern angeordnet und kompakter dargestellt.
- Auswahlgestützte Massenanalyse für sichtbare, geladene, markierte, fehlende, alte, schwache oder fehlerhafte Websites ergänzt.
- Live-Aktualisierung von Tabelle, Kundendetail, Fortschritt und gedrosseltem Dashboard während der Massenanalyse.
- Kombinierter Kundenstatusfilter für Vollständig und Aktiv.

## 1.3.0

- Kostenlose, begrenzte Websiteanalyse ausschließlich für bereits zugeordnete offizielle Firmenwebsites.
- Transparenter Website-Score mit zentraler Gewichtung und vollständiger Kriterienaufschlüsselung.
- Erkennung von HTTPS/TLS, Impressum, Datenschutz, Kontaktseite und Kontaktformular.
- Lokale Erkennung von Social-Media-Profilen und strukturierten beziehungsweise sichtbaren Öffnungszeiten.
- Regelbasierte Branchenklassifikation mit Konfidenz und nachvollziehbaren Hinweisen.
- Lokale Kurzbeschreibung aus belegbaren Websiteinhalten ohne Cloud-KI.
- Cache, Force Refresh, Massenanalyse, Abbruch und automatische Veraltung bei Websiteänderung.
- Websiteanalyse im Kundendetail, Dashboard und optional im Kundenexport.

## 1.2.3

- Importprüfung mit Kennzahlen zu Pflichtwerten, Kontaktdaten, Websites und leeren Zeilen.
- Sichere Excel-Dublettenbereinigung vor der Übernahme in die Kundenansicht.
- Bereinigte XLSX-Datei mit separatem Importbericht und Schutz der Originaldatei.
- Transparenter Datenqualitäts-Score und Qualitätskennzahlen im Dashboard.

## 1.2.2

- Automatische Updateprüfung nach dem sichtbaren Programmstart ergänzt.
- Manuelle Updateprüfung über das Hilfe-Menü hinzugefügt.
- Sicherer Download von Plattform-Assets über GitHub Releases mit optionaler SHA-256-Prüfung.
- Startdialog um die letzten fünf erfolgreich geöffneten Excel-Dateien erweitert.
- Hilfe-Menü um Diagnoseordner, kopierbare Systeminformationen und Über-Dialog ergänzt.
- Tägliche, auf zehn Stände begrenzte automatische SQLite-Backups hinzugefügt.
- Mehrfachstart verhindert; vorhandene Instanz wird aktiviert.
- Lizenzgenerator um unbegrenzte, feste und tageweise Gültigkeit mit Vorschau erweitert.
- Ablaufstatus, deutsches Ablaufdatum und verbleibende Tage werden zentral ausgewertet.
- Zeitlich unbegrenzte ältere Lizenzdateien ohne `expires_at` bleiben kompatibel.
- Sofort sichtbarer Splash Screen mit echten Startstatusmeldungen.
- Startprofilierung mit Zeitmarken für UI, Einstellungen, Lizenz und Datenbank.
- Recherche-, Export- und seltene Dialogmodule werden erst bei Bedarf geladen.
- Schwere Drittanbieterimporte aus dem unmittelbaren Startpfad entfernt.
- Datenbankinstanz zwischen CRM und Recherche geteilt und doppelte Dashboard-Aktualisierung entfernt.
- PyInstaller-Bundle um Test- und nicht verwendete Entwicklungsmodule bereinigt.

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
