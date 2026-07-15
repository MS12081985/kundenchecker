from dataclasses import dataclass, field


@dataclass
class DashboardData:
    total: int = 0
    complete: int = 0
    active: int = 0
    inactive: int = 0
    not_found: int = 0
    missing_website: int = 0
    missing_phone: int = 0
    missing_email: int = 0
    visible_rows: int = 0
    last_research_at: str = ""
    last_research_processed: int | None = None
    last_research_errors: int | None = None
    last_research_cancelled: bool | None = None
    last_research_duration: float | None = None
    recent_changes: list = field(default_factory=list)
