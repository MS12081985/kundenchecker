from __future__ import annotations
import base64, hashlib, hmac, json
from datetime import date
from pathlib import Path
from loguru import logger
from config.app_config import AppConfig
from models.license_data import LicenseEvaluation, LicenseStatus

PUBLIC_KEY_B64 = "fIoCqr1xMiFCQtdRsL78dcaAocN337fuCevSWzoM4zE="

class LicenseService:
    def __init__(self, directory=None):
        self.directory = Path(directory) if directory else AppConfig.RUNTIME_DIR / "license"
        self.license_path = self.directory / "license.kcl"; self.usage_path = self.directory / "usage.json"
        self.license = None; self.usage = {"researches": 0}; self._usage_corrupt = False; self.load()
    def load(self):
        try:
            path = self.license_path if self.license_path.exists() else self.directory / "license.json"
            if path.exists(): self.license = json.loads(path.read_text(encoding="utf-8"))
            if self.usage_path.exists():
                self.usage = json.loads(self.usage_path.read_text(encoding="utf-8"))
                expected = hmac.new(self._usage_secret(), str(int(self.usage.get("researches", 0))).encode(), hashlib.sha256).hexdigest()
                self._usage_corrupt = not hmac.compare_digest(expected, self.usage.get("integrity", ""))
        except (OSError, json.JSONDecodeError) as error:
            logger.warning("Lizenzdaten konnten nicht geladen werden: {}", error); self.license = None; self.usage = {"researches": 0, "integrity": ""}
    def validate(self):
        data = self.license
        if self._usage_corrupt: return False, "Die lokale Nutzungsdatei ist beschädigt."
        if not isinstance(data, dict) or not data.get("signature"): return False, "Keine gültige Lizenz geladen."
        if data.get("application", "KundenChecker") != "KundenChecker": return False, "Die Lizenz gehört zu einer anderen Anwendung."
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
            payload = {k: v for k, v in data.items() if k != "signature"}
            key = Ed25519PublicKey.from_public_bytes(base64.b64decode(PUBLIC_KEY_B64))
            key.verify(base64.b64decode(data["signature"]), json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())
        except Exception: return False, "Die Lizenzsignatur ist ungültig oder die Kryptobibliothek fehlt."
        if data.get("expires_at") and date.today().isoformat() > str(data["expires_at"]): return False, "Die Lizenz ist abgelaufen."
        if data.get("max_researches") is not None and int(self.usage.get("researches", 0)) >= int(data["max_researches"]): return False, "Das Recherchelimit der Lizenz ist erreicht."
        return True, "Lizenz gültig."
    def can_research(self, amount=1):
        valid, message = self.validate()
        if not valid: return False, message
        limit = self.license.get("max_researches")
        if limit is not None and int(self.usage.get("researches", 0)) + amount > int(limit): return False, "Nicht genügend Recherchen im Lizenzkontingent verfügbar."
        return True, message
    def record_researches(self, amount):
        if amount <= 0: return
        self.usage["researches"] = int(self.usage.get("researches", 0)) + int(amount)
        self.directory.mkdir(parents=True, exist_ok=True)
        payload = {"researches": self.usage["researches"]}
        payload["integrity"] = hmac.new(self._usage_secret(), str(payload["researches"]).encode(), hashlib.sha256).hexdigest()
        self.usage_path.write_text(json.dumps(payload, indent=2), encoding="utf-8"); self.usage = payload
    def status(self):
        evaluation = self.evaluate(); return {"valid": evaluation.valid, "message": evaluation.message, "license": evaluation.license_data, "used": evaluation.used, "remaining": evaluation.remaining}

    def _usage_secret(self):
        return hashlib.sha256(f"{AppConfig.APP_NAME}:usage-v1".encode()).digest()

    def evaluate(self):
        valid, message = self.validate(); data = self.license or {}; limit = data.get("max_researches")
        remaining = None if limit is None else max(0, int(limit) - int(self.usage.get("researches", 0)))
        status = LicenseStatus.VALID_FULL if valid and data.get("edition") == "full" else LicenseStatus.VALID_TRIAL if valid and data.get("edition") == "trial" else LicenseStatus.VALID_PROFESSIONAL if valid else LicenseStatus.MISSING
        return LicenseEvaluation(status, message, data, int(self.usage.get("researches", 0)), remaining)
