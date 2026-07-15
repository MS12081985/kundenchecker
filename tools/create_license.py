"""Erzeugt eine signierte Offline-Lizenz (privater Schlüssel bleibt extern)."""
import argparse, base64, json, uuid
from datetime import date
from pathlib import Path
from cryptography.hazmat.primitives import serialization


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--key", required=True); parser.add_argument("--output", required=True)
    parser.add_argument("--customer", required=True); parser.add_argument("--edition", choices=("trial", "full", "professional"), default="full")
    parser.add_argument("--expires-at"); parser.add_argument("--max-researches", type=int)
    args = parser.parse_args()
    key = serialization.load_pem_private_key(Path(args.key).read_bytes(), password=None)
    data = {"schema_version": 1, "license_id": str(uuid.uuid4()), "customer_name": args.customer, "edition": args.edition, "issued_at": date.today().isoformat(), "application": "KundenChecker", "application_major_version": "1"}
    if args.expires_at: data["expires_at"] = args.expires_at
    if args.max_researches is not None: data["max_researches"] = args.max_researches
    data["signature"] = base64.b64encode(key.sign(json.dumps(data, sort_keys=True, separators=(",", ":")).encode())).decode()
    Path(args.output).write_text(json.dumps(data, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
