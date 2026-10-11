from dataclasses import dataclass

@dataclass(frozen=True)
class LeaveRequestEntity:
    user_id: int
    leave_type: str
    start_date: str
    end_date: str
    half_day: bool
    status: str
