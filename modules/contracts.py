from typing import List

from core.api.contracts import Contract

class LeaveApplicationContract(Contract):
    user_id: int
    posting_id: int
    category: str
    start_date: str
    end_date: str
    reason: str
    half_day_cl: bool
    station_leave_details: dict
    substitute_id: int | None
    status: str

class LeaveBalanceContract(Contract):
    user_id: int
    year: int
    balance: float

class LeaveApplicationAuditContract(Contract):
    application_id: int
    status: str
    reason: str
    at: str
