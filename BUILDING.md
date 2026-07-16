# KundenChecker macOS Build

Die lokale, nicht signierte App wird mit PyInstaller gebaut:

```bash
.venv/bin/pip install -r requirements-dev.txt
chmod +x scripts/build_macos.sh
scripts/build_macos.sh
```

Ergebnis: `dist/KundenChecker.app` und `release/KundenChecker-1.3.0.dmg`.
Die DMG enthält die App und eine Verknüpfung zu `/Applications`.

Die App ist zunächst nicht signiert. macOS kann beim ersten Start warnen; dann
über Rechtsklick → Öffnen starten. Codesignierung, Hardened Runtime und
Notarisierung sind für einen späteren Release vorgesehen und werden nicht
automatisch ausgeführt.
