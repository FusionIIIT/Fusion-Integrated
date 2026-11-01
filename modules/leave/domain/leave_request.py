"""Pure Python domain data representations for leave requests.

Conforms to the strict domain isolation rule (no Django, DRF or Celery imports).
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional

from modules.leave.domain.constants import HalfDayOption, LeaveCategory, LeaveStatus


@dataclass(frozen=True)
class LeaveApplicationData:
    user_id: int
    category: LeaveCategory
    start_date: date
    end_date: date
    computed_days: Decimal
    reason: str
    half_day: HalfDayOption = HalfDayOption.NONE
    substitute_user_id: Optional[int] = None
    station_leave: bool = False
    station_address: str = ""
    station_contact: str = ""
    station_start_date: Optional[date] = None
    station_end_date: Optional[date] = None
    medical_certificate_url: str = ""


@dataclass(frozen=True)
class LeaveRecordData:
    id: int
    user_id: int
    category: LeaveCategory
    start_date: date
    end_date: date
    computed_days: Decimal
    status: LeaveStatus
    reason: str
