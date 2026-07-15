# Lizenzgenerator intern

1. Abhängigkeiten installieren: `pip install -r requirements-dev.txt`.
2. Einen privaten Ed25519-Schlüssel außerhalb des Repositorys erzeugen.
3. `license_generator_app.py` mit dem externen Schlüssel starten.
4. Lizenznehmer, Edition, Ablauf und Limit eingeben und als `.kcl` speichern.

Private Schlüssel niemals committen, versenden oder in einen App-Build
aufnehmen. Bei Schlüsselverlust müssen ein neues Schlüsselpaar und eine neue
App-Version veröffentlicht werden.
