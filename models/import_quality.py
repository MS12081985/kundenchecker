from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ImportRow:
    key: str
    excel_row: int
    source_index: Any
    values: dict[str, Any]


@dataclass(frozen=True)
class ImportIssue:
    row_key: str
    excel_row: int
    kind: str
    field: str
    message: str
    original_value: str = ""


@dataclass(frozen=True)
class ImportDuplicateGroup:
    group_id: str
    category: str
    row_keys: tuple[str, ...]
    excel_rows: tuple[int, ...]
    suggested_master_key: str
    conflicts: tuple[str, ...] = ()
    differences: tuple[str, ...] = ()

    @property
    def automatic(self):
        return self.category in {"identical", "safe"} and not self.conflicts


@dataclass(frozen=True)
class ImportAnalysis:
    source_path: str
    sheet_name: str
    analyzed_at: str
    dataframe: Any = field(repr=False, compare=False)
    rows: tuple[ImportRow, ...] = ()
    issues: tuple[ImportIssue, ...] = ()
    duplicate_groups: tuple[ImportDuplicateGroup, ...] = ()
    total_rows: int = 0
    valid_records: int = 0
    identical_duplicates: int = 0
    similar_groups: int = 0
    missing_customer_name: int = 0
    missing_city: int = 0
    invalid_phones: int = 0
    invalid_emails: int = 0
    empty_websites: int = 0
    normalizable_websites: int = 0
    empty_rows: int = 0
    quality_score: int = 100


@dataclass(frozen=True)
class ImportCleaningPlan:
    remove_identical: bool = True
    merge_safe: bool = True
    skip_missing_customer_name: bool = True
    invalid_phone_action: str = "clear"
    invalid_email_action: str = "clear"
    master_overrides: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ImportReport:
    source_path: str
    analyzed_at: str
    rows_before: int
    rows_after: int
    imported_rows: int
    removed_identical: int
    merged_groups: int
    skipped_rows: int
    corrected_phones: int
    discarded_emails: int
    normalized_websites: int
    open_conflicts: int


@dataclass(frozen=True)
class ImportCleaningResult:
    dataframe: Any = field(repr=False, compare=False)
    report: ImportReport | None = None


@dataclass(frozen=True)
class ImportDialogDecision:
    action: str
    master_overrides: dict[str, str] = field(default_factory=dict)
