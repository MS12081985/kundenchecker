# Lizenzgenerator intern

1. Abhängigkeiten installieren: `pip install -r requirements-dev.txt`.
2. Einen privaten Ed25519-Schlüssel außerhalb des Repositorys erzeugen.
3. `license_generator_app.py` mit dem externen Schlüssel starten.
4. Lizenznehmer, Firma, Edition und optional ein Recherchelimit eingeben.
5. Gültigkeit auswählen:
   - `Unbegrenzt` speichert kein Ablaufdatum (`expires_at: null`).
   - `Festes Ablaufdatum` akzeptiert ein Datum ab dem Ausstellungstag.
   - `Dauer in Tagen` berechnet das Ablaufdatum ab dem Ausstellungstag (1–3650 Tage).
6. Die vollständige Vorschau prüfen und die Lizenz als `.kcl` speichern.

Trial-Lizenzen starten standardmäßig mit 30 Tagen Gültigkeit. Full- und
Professional-Lizenzen starten unbegrenzt. Eine manuell gewählte Gültigkeit
bleibt bei einem späteren Editionswechsel erhalten. Das Ablaufdatum selbst ist
einschließlich gültig; ab dem folgenden lokalen Kalendertag gilt die Lizenz als
abgelaufen.

Private Schlüssel niemals committen, versenden oder in einen App-Build
aufnehmen. Bei Schlüsselverlust müssen ein neues Schlüsselpaar und eine neue
App-Version veröffentlicht werden.
