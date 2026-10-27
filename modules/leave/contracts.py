from core.api.contracts import Contract


class LeaveApplicationContract(Contract):
    id: int
    user_id: int
    category: str
    start_date: str
    end_date: str
    half_day_slot: str
    calculated_days: float
    reason: str
    status: str
    station_leave_applied: bool
    station_leave_address: str
    station_leave_contact: str
    substitute_id: int | None
    substitute_status: str
    unit_head_id: int | None
    unit_head_recommendation: str
    sanctioning_authority_id: int | None
    created_at: str


class LeaveBalanceContract(Contract):
    id: int
    user_id: int
    year: int
    category: str
    credited: float
    availed: float
    available_balance: float


class LeaveApplicationAuditContract(Contract):
    id: int
    application_id: int
    actor_id: int
    action: str
    from_status: str
    to_status: str
    remarks: str
    created_at: str


class HolidayCalendarContract(Contract):
    id: int
    name: str
    date: str
    is_rh: bool
    year: int
