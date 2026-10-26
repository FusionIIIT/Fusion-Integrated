"""Pure domain state machine and mathematical logic for ELM (Fusion architecture compliant).
No Django/DRF/Celery imports allowed here.
Encodes CFR-EL-001 through CFR-EL-032 and BR-EL-001 through BR-EL-038.
"""
from datetime import date, timedelta

# Leave Categories (BR-EL-001)
CAT_CL = "CL"
CAT_RH = "RH"
CAT_SCL = "SCL"
CAT_EL = "EL"
CAT_COL = "COL"
CAT_VL = "VL"
ALL_CATEGORIES: set[str] = {CAT_CL, CAT_RH, CAT_SCL, CAT_EL, CAT_COL, CAT_VL}

# Workflow States (CW-EL-01 through CW-EL-04)
ST_DRAFT = "DRAFT"
ST_AWAITING_SUBSTITUTE = "AWAITING_SUBSTITUTE"
ST_APPLICANT_ACTION_REQUIRED = "APPLICANT_ACTION_REQUIRED"
ST_AWAITING_UNIT_HEAD = "AWAITING_UNIT_HEAD"
ST_AWAITING_ESTABLISHMENT = "AWAITING_ESTABLISHMENT"
ST_AWAITING_SANCTION = "AWAITING_SANCTION"
ST_AWAITING_DIRECTOR_SELF_SANCTION = "AWAITING_DIRECTOR_SELF_SANCTION"
ST_APPROVED = "APPROVED"
ST_REJECTED = "REJECTED"
ST_WITHDRAWN = "WITHDRAWN"
ST_CANCELLED = "CANCELLED"

# Cancellation States (CW-EL-02)
ST_CANCELLATION_PENDING_UH = "CANCELLATION_PENDING_UH"
ST_CANCELLATION_PENDING_EST = "CANCELLATION_PENDING_EST"
ST_CANCELLATION_PENDING_SANCTION = "CANCELLATION_PENDING_SANCTION"

# Resumption States (CW-EL-04)
ST_RESUMPTION_PENDING = "RESUMPTION_PENDING"
ST_RESUMPTION_REVIEWED_NORMAL = "RESUMPTION_REVIEWED_NORMAL"
ST_RESUMPTION_REVIEWED_ADJUSTED = "RESUMPTION_REVIEWED_ADJUSTED"


def calculate_days(
    category: str,
    start_date: date,
    end_date: date,
    is_half_day: bool = False,
    published_holidays: set[date] | None = None,
    is_continuous_count: bool | None = None,
) -> float:
    """Computes chargeable leave days according to BR-EL-010 and BR-EL-011.
    - EL, COL, VL: continuous calendar count (intervening weekends & closed holidays included).
    - CL and SCL exclude intervening weekends and closed holidays.
    - RH is one chargeable day; the service validates its published RH date.
    - CL Half-day: exactly 0.5 day.
    """
    if category == CAT_CL and is_half_day:
        return 0.5

    # An RH date is itself an applicable holiday and still consumes one RH day.
    # The service separately enforces that RH requests contain exactly one date.
    if category == CAT_RH:
        return 1.0 if start_date == end_date else 0.0

    holidays = published_holidays or set()
    current = start_date
    count = 0.0
    continuous = (
        category in (CAT_EL, CAT_COL, CAT_VL)
        if is_continuous_count is None else is_continuous_count
    )

    while current <= end_date:
        if continuous:
            count += 1.0
        else:
            is_weekend = current.weekday() in (5, 6)
            is_holiday = current in holidays
            if not is_weekend and not is_holiday:
                count += 1.0
        current += timedelta(days=1)

    return count


def check_applicant_overlap(
    cand_start: date,
    cand_end: date,
    cand_half: bool,
    cand_half_type: str | None,
    active_start: date,
    active_end: date,
    active_half: bool,
    active_half_type: str | None,
) -> bool:
    """Evaluates applicant non-overlap with the half-day CL exception (BR-EL-012)."""
    if cand_end < active_start or cand_start > active_end:
        return False

    # Different halves on the same date do not collide.
    return not (
        cand_start == cand_end == active_start == active_end
        and cand_half
        and active_half
        and cand_half_type
        and active_half_type
        and cand_half_type != active_half_type
    )


def execute_year_end_processing(
    employee_type: str,
    balances: dict[str, float],
) -> tuple[dict[str, float], list[str]]:
    """Implements event-triggered year-end leave execution (EL-UC-020, CFR-EL-028, BR-EL-002-009).
    - CL, RH, SCL lapse to 0.
    - Faculty VL: converted 2 VL : 1 EL (preserves fractional output), VL balance set to 0.
    - EL and COL: carry forward.
    """
    updated = dict(balances)
    audit_notes = []

    # CL, RH, SCL lapse
    updated[CAT_CL] = 0.0
    updated[CAT_RH] = 0.0
    updated[CAT_SCL] = 0.0
    audit_notes.append("Lapsed unused CL, RH, SCL.")

    if employee_type == "faculty":
        unused_vl = updated.get(CAT_VL, 0.0)
        converted_el = unused_vl / 2.0
        updated[CAT_VL] = 0.0
        updated[CAT_EL] = updated.get(CAT_EL, 0.0) + converted_el
        audit_notes.append(f"Converted {unused_vl} VL into {converted_el} EL (2:1 ratio).")

    audit_notes.append(
        f"Carried forward EL ({updated.get(CAT_EL, 0.0)}) "
        f"and COL ({updated.get(CAT_COL, 0.0)})."
    )
    return updated, audit_notes
