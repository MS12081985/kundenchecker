"""Typed, evidence-based company data extracted from an imprint page."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ImprintData:
    owner_names: list[str] = field(default_factory=list)
    managing_director_names: list[str] = field(default_factory=list)
    representative_names: list[str] = field(default_factory=list)
    legal_form: str = ""
    imprint_company_name: str = ""
    imprint_street: str = ""
    imprint_house_number: str = ""
    imprint_postal_code: str = ""
    imprint_city: str = ""
    imprint_country: str = ""
    imprint_phone: str = ""
    imprint_email: str = ""
    vat_id: str = ""
    commercial_register_type: str = ""
    commercial_register_number: str = ""
    register_court: str = ""
    imprint_extraction_confidence: float = 0.0
    imprint_sources: list[str] = field(default_factory=list)
    imprint_raw_label_values: dict[str, str] = field(default_factory=dict)
    imprint_analyzed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any] | None) -> "ImprintData":
        payload = dict(value or {})
        for name in ("owner_names", "managing_director_names", "representative_names", "imprint_sources"):
            payload[name] = list(payload.get(name) or [])
        payload["imprint_raw_label_values"] = dict(payload.get("imprint_raw_label_values") or {})
        known = cls.__dataclass_fields__
        return cls(**{key: value for key, value in payload.items() if key in known})

    def has_company_data(self) -> bool:
        ignored = {"imprint_extraction_confidence", "imprint_sources", "imprint_raw_label_values", "imprint_analyzed_at"}
        return any(value for key, value in asdict(self).items() if key not in ignored)

    def formatted_address(self) -> str:
        street = " ".join(value for value in (self.imprint_street, self.imprint_house_number) if value)
        city = " ".join(value for value in (self.imprint_postal_code, self.imprint_city) if value)
        return ", ".join(value for value in (street, city, self.imprint_country) if value)
