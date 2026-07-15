from dataclasses import dataclass
from enum import Enum


class LicenseStatus(str, Enum):
    VALID_FULL = "valid_full"
    VALID_TRIAL = "valid_trial"
    VALID_PROFESSIONAL = "valid_professional"
    MISSING = "missing"
    EXPIRED = "expired"
    INVALID_SIGNATURE = "invalid_signature"
    WRONG_APPLICATION = "wrong_application"
    LIMIT_REACHED = "limit_reached"
    MALFORMED = "malformed"


@dataclass
class LicenseEvaluation:
    status: LicenseStatus
    message: str
    license_data: dict
    used: int = 0
    remaining: int | None = None
    expires_display: str = "Unbegrenzt"
    remaining_days: int | None = None

    @property
    def valid(self):
        return self.status in {LicenseStatus.VALID_FULL, LicenseStatus.VALID_TRIAL, LicenseStatus.VALID_PROFESSIONAL}
