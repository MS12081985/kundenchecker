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
    invalid_phone: int = 0
    invalid_email: int = 0
    detected_duplicates: int = 0
    quality_score: int = 0
    visible_rows: int = 0
    last_research_at: str = ""
    last_research_processed: int | None = None
    last_research_errors: int | None = None
    last_research_cancelled: bool | None = None
    last_research_duration: float | None = None
    recent_changes: list = field(default_factory=list)
    open_follow_ups: int = 0
    overdue_follow_ups: int = 0
    prospects: int = 0
    customers: int = 0
    high_priority: int = 0
    today_activities: int = 0
    average_website_score: float = 0.0
    very_good_websites: int = 0
    weak_websites: int = 0
    websites_without_imprint: int = 0
    websites_without_privacy: int = 0
    websites_with_opening_hours: int = 0
    websites_with_social_media: int = 0
    websites_not_analyzed: int = 0
    industry_distribution: dict = field(default_factory=dict)
