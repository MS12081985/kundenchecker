"""Typed hand-off from completed research to optional website enrichment."""

from dataclasses import dataclass, field


@dataclass
class ResearchRunSummary:
    research_mode: str
    processed_customer_keys: list[tuple] = field(default_factory=list)
    successful_customer_keys: list[tuple] = field(default_factory=list)
    website_customer_keys: list[tuple] = field(default_factory=list)
    results: list[object] = field(default_factory=list, repr=False)
    error_count: int = 0
    aborted: bool = False
    force_refresh: bool = False


@dataclass
class ResearchRunState:
    mode: str
    force_refresh: bool = False
    processed_customer_keys: list[tuple] = field(default_factory=list)
    successful_customer_keys: list[tuple] = field(default_factory=list)
    website_customer_keys: list[tuple] = field(default_factory=list)
    failed_customer_keys: list[tuple] = field(default_factory=list)
    results: list[object] = field(default_factory=list, repr=False)
    aborted: bool = False
    result_count: int = 0
    pending_result_count: int = 0
    finished_received: bool = False
    finalized: bool = False
    error_count: int = 0
    completion_message: str = ""



@dataclass
class PostResearchEnrichmentOffer:
    customers: list[dict]
    processed_count: int
    website_count: int
    pending_count: int
    error_count: int = 0
    single: bool = False
