from __future__ import annotations

from datetime import date
from typing import Any

LEAVE_TYPE_META = {
    "CL": {"label": "Casual Leave", "annual_limit": 8, "half_day_supported": True},
    "RH": {"label": "Restricted Holiday", "annual_limit": 2, "half_day_supported": False},
    "SCL": {"label": "Special Casual Leave", "annual_limit": 15, "half_day_supported": True},
    "EL": {"label": "Earned Leave", "annual_limit": 30, "half_day_supported": True},
    "COL": {
        "label": "Compensatory / Medical Leave",
        "annual_limit": 20,
        "half_day_supported": True,
    },
    "VL": {"label": "Vacation Leave", "annual_limit": 60, "half_day_supported": True},
}


def _default_balances() -> list[dict[str, Any]]:
    return [
        {
            "code": "CL",
            "label": "Casual Leave",
            "used": 1.5,
            "available": 6.5,
            "entitled": 8,
            "carry_forward": 0,
        },
        {
            "code": "RH",
            "label": "Restricted Holiday",
            "used": 0,
            "available": 2,
            "entitled": 2,
            "carry_forward": 0,
        },
        {
            "code": "SCL",
            "label": "Special Casual Leave",
            "used": 1,
            "available": 14,
            "entitled": 15,
            "carry_forward": 0,
        },
        {
            "code": "EL",
            "label": "Earned Leave",
            "used": 2,
            "available": 12,
            "entitled": 14,
            "carry_forward": 0,
        },
        {
            "code": "COL",
            "label": "Compensatory / Medical Leave",
            "used": 3,
            "available": 17,
            "entitled": 20,
            "carry_forward": 0,
        },
        {
            "code": "VL",
            "label": "Vacation Leave",
            "used": 5,
            "available": 55,
            "entitled": 60,
            "carry_forward": 0,
        },
    ]


def _default_requests() -> list[dict[str, Any]]:
    return [
        {
            "id": "EL-2025-001",
            "leave_type": "EL",
            "start_date": "2025-07-12",
            "end_date": "2025-07-15",
            "days_requested": 4,
            "purpose": "Family obligation",
            "status": "approved",
            "substitute": "Arjun Nair",
        },
        {
            "id": "CL-2025-003",
            "leave_type": "CL",
            "start_date": "2025-08-01",
            "end_date": "2025-08-01",
            "days_requested": 0.5,
            "purpose": "Personal appointment",
            "status": "pending",
            "substitute": "Ananya Singh",
        },
        {
            "id": "RH-2025-002",
            "leave_type": "RH",
            "start_date": "2025-06-18",
            "end_date": "2025-06-18",
            "days_requested": 1,
            "purpose": "Religious observance",
            "status": "approved",
            "substitute": "Sidharth Rao",
        },
    ]


def _default_review_items() -> list[dict[str, Any]]:
    return [
        {
            "id": "CL-2025-005",
            "employee": "Ritika Sharma",
            "leave_type": "CL",
            "start_date": "2025-08-06",
            "end_date": "2025-08-08",
            "days_requested": 3,
            "status": "pending",
            "substitute": "Vikas Mehta",
            "purpose": "Travel and family visit",
        },
        {
            "id": "EL-2025-010",
            "employee": "Karan Verma",
            "leave_type": "EL",
            "start_date": "2025-08-20",
            "end_date": "2025-08-25",
            "days_requested": 6,
            "status": "recommended",
            "substitute": "Meera Joshi",
            "purpose": "Outstation leave",
        },
    ]


def calculate_leave_duration(start: date, end: date, leave_type: str) -> float:
    """Approximate the ELM counting rules used by the module UI and APIs.

    This baseline keeps the calculation local and deterministic so the module can
    provide realistic dashboards without depending on a live Postgres state.
    """
    if start > end:
        raise ValueError("start_date cannot be after end_date")

    if leave_type in {"CL", "SCL", "RH"}:
        total_days = (end - start).days + 1
        if leave_type == "RH":
            return float(total_days)
        return float(total_days)

    total_days = (end - start).days + 1
    return float(total_days)


def get_dashboard_summary(user_id: int | None = None) -> dict[str, Any]:
    employee_id = user_id if user_id is not None else 101
    return {
        "module": "leave",
        "employee_id": employee_id,
        "summary": {
            item["code"]: {
                "used": item["used"],
                "available": item["available"],
                "entitled": item["entitled"],
            }
            for item in _default_balances()
        },
        "recent_requests": _default_requests(),
        "enforced_permissions": [
            "leave.request.view_self",
            "leave.request.create",
            "leave.request.delete",
            "leave.request.view",
            "leave.request.approve",
            "leave.balance.update",
            "leave.type.manage",
        ],
    }


def get_leave_requests_for_user(user_id: int | None = None) -> list[dict[str, Any]]:
    return _default_requests()


def get_review_queue() -> list[dict[str, Any]]:
    return _default_review_items()


def get_leave_balances(user_id: int | None = None) -> list[dict[str, Any]]:
    return _default_balances()


def get_leave_types() -> list[dict[str, Any]]:
    return [{"code": code, **meta} for code, meta in LEAVE_TYPE_META.items()]
