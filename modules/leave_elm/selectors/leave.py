from modules.leave_elm.models import LeaveApplication, LeaveBalance


def get_employee_balance(employee_id: str, category: str) -> dict | None:
    """Fetches leave balance for an employee and specific category."""
    try:
        balance, _created = LeaveBalance.objects.get_or_create(
            user_id=employee_id,
            category=category,
            defaults={"available_balance": 0.0, "annual_entitlement": 0.0},
        )
    except LeaveBalance.DoesNotExist:
        return None
    else:
        return {
            "available_balance": balance.available_balance,
            "annual_entitlement": balance.annual_entitlement,
        }


def get_all_balances(employee_ids: list[str]) -> dict[str, dict]:
    """Fetches balances for a list of employee IDs."""
    balances_map: dict[str, dict] = {}
    query = LeaveBalance.objects.filter(user_id__in=employee_ids)
    for balance in query:
        if balance.user_id not in balances_map:
            balances_map[balance.user_id] = {}
        balances_map[balance.user_id][balance.category] = {
            "available_balance": balance.available_balance,
            "annual_entitlement": balance.annual_entitlement,
        }
    return balances_map


def get_applications_for_employee(employee_id: str) -> list[dict]:
    """Retrieves all leave applications submitted by a specific employee, ordered by date."""
    applications = LeaveApplication.objects.filter(employee_id=employee_id).order_by("-start_date")
    return [
        {
            "id": app.pk,
            "category": app.category,
            "start_date": app.start_date.isoformat(),
            "end_date": app.end_date.isoformat(),
            "reason": app.reason,
            "status": app.status,
            "substitute_id": app.substitute_id,
            "is_station_leave": app.is_station_leave,
            "is_half_day_start": app.is_half_day_start,
            "is_half_day_end": app.is_half_day_end,
        }
        for app in applications
    ]


def get_all_applications(
    user_id: str | None = None, user_role: str = "Employee", is_admin: bool = False
) -> list[dict]:
    """Retrieves leave applications based on user role with Row-Level Security."""
    applications_queryset = LeaveApplication.objects.all()
    if is_admin:
        pass
    elif user_role == "Employee" and user_id:
        applications_queryset = applications_queryset.filter(employee_id=user_id)
    elif user_role == "HOD":
        applications_queryset = applications_queryset.filter(status__in=["pending", "recommended"])
    elif user_role in ["Registrar", "Leave Approver"]:
        applications_queryset = applications_queryset.filter(status="pending")
    else:
        return []
    return [
        {
            "id": app.pk,
            "employee_id": app.employee_id,
            "category": app.category,
            "start_date": app.start_date.isoformat(),
            "end_date": app.end_date.isoformat(),
            "reason": app.reason,
            "status": app.status,
            "substitute_id": app.substitute_id,
            "is_station_leave": app.is_station_leave,
            "is_half_day_start": app.is_half_day_start,
            "is_half_day_end": app.is_half_day_end,
        }
        for app in applications_queryset.order_by("-start_date")
    ]
