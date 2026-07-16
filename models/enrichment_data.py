"""Typed data transferred between website enrichment service, worker and UI."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from models.imprint_data import ImprintData


@dataclass(frozen=True)
class ScoreCriterion:
    key: str
    label: str
    achieved: bool
    points: int
    maximum: int


@dataclass(frozen=True)
class WebsiteScoreBreakdown:
    total: int = 0
    category: str = "Schwach"
    criteria: tuple[ScoreCriterion, ...] = ()

    @property
    def missing_labels(self) -> tuple[str, ...]:
        return tuple(item.label for item in self.criteria if not item.achieved)


@dataclass(frozen=True)
class SocialMediaLinks:
    facebook: str = ""
    instagram: str = ""
    linkedin: str = ""
    youtube: str = ""
    tiktok: str = ""
    x: str = ""
    pinterest: str = ""

    def active_platforms(self) -> tuple[str, ...]:
        return tuple(name for name, value in asdict(self).items() if value)


@dataclass(frozen=True)
class OpeningHoursEntry:
    day: str
    periods: tuple[str, ...] = ()
    closed: bool = False
    by_appointment: bool = False


@dataclass(frozen=True)
class OpeningHoursData:
    entries: tuple[OpeningHoursEntry, ...] = ()
    original_text: str = ""
    source: str = ""
    reliable: bool = False

    def display_text(self) -> str:
        lines = []
        for entry in self.entries:
            value = "geschlossen" if entry.closed else ("nach Vereinbarung" if entry.by_appointment else ", ".join(entry.periods))
            if value:
                lines.append(f"{entry.day}: {value}")
        return "\n".join(lines) or self.original_text


@dataclass(frozen=True)
class IndustryResult:
    industry: str = "Unklar"
    confidence: float = 0.0
    hints: tuple[str, ...] = ()
    alternative: str = ""


@dataclass(frozen=True)
class EnrichmentResult:
    company: str
    city: str
    website: str
    customer_id: int | None = None
    company_key: str = ""
    website_score: int = 0
    website_score_category: str = "Schwach"
    website_score_details: WebsiteScoreBreakdown = field(default_factory=WebsiteScoreBreakdown)
    has_https: bool = False
    ssl_valid: bool = False
    has_imprint: bool = False
    imprint_url: str = ""
    imprint_data: ImprintData = field(default_factory=ImprintData)
    has_privacy_policy: bool = False
    privacy_url: str = ""
    has_contact_page: bool = False
    contact_page_url: str = ""
    has_opening_hours: bool = False
    opening_hours: OpeningHoursData = field(default_factory=OpeningHoursData)
    social_media: SocialMediaLinks = field(default_factory=SocialMediaLinks)
    industry: IndustryResult = field(default_factory=IndustryResult)
    short_description: str = "Keine verlässliche Kurzbeschreibung verfügbar."
    description_sources: tuple[str, ...] = ()
    contact_form_url: str = ""
    website_title: str = ""
    meta_description: str = ""
    has_structured_data: bool = False
    response_time_seconds: float | None = None
    analyzed_at: str = ""
    analysis_version: str = ""
    enrichment_status: str = "Nicht analysiert"
    enrichment_error: str = ""
    from_cache: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "EnrichmentResult":
        payload = dict(value)
        score = payload.get("website_score_details") or {}
        score["criteria"] = tuple(ScoreCriterion(**item) for item in score.get("criteria", ()))
        payload["website_score_details"] = WebsiteScoreBreakdown(**score)
        hours = payload.get("opening_hours") or {}
        hours["entries"] = tuple(OpeningHoursEntry(**item) for item in hours.get("entries", ()))
        payload["opening_hours"] = OpeningHoursData(**hours)
        payload["social_media"] = SocialMediaLinks(**(payload.get("social_media") or {}))
        payload["industry"] = IndustryResult(**(payload.get("industry") or {}))
        payload["imprint_data"] = ImprintData.from_dict(payload.get("imprint_data"))
        payload["description_sources"] = tuple(payload.get("description_sources") or ())
        return cls(**payload)
