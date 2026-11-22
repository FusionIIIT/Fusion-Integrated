from rest_framework.exceptions import ValidationError

from modules.directory.models import UserRef
from modules.elm.checks import ensure_balance, ensure_nominee, ensure_overlap_free, policy_for
from modules.elm.validation import count_days, resolve_route


def validate_request(data, employee, kind, exclude=None):
    required_keys = ["leave_type", "start_date", "end_date", "purpose"]
    optional_keys = [
        "half_day",
        "substitute",
        "station_leave",
        "station_details",
        "medical_evidence",
    ]
    data = {
        k: data.get(k, v)
        for k, v in zip(
            required_keys + optional_keys,
            [""] * len(required_keys) + [""] * len(optional_keys),
            strict=True,
        )
    }
    data["half_day"] = data["half_day"] or "FULL"
    data["substitute"] = data["substitute"] or None
    data["station_leave"] = data["station_leave"] or False
    data["station_details"] = data["station_details"] or ""
    data["medical_evidence"] = data["medical_evidence"] or ""

    if not all(data[k] for k in required_keys):
        raise ValidationError("Missing required fields: leave_type, start_date, end_date, purpose")

    leave_type = data["leave_type"]
    start = data["start_date"]
    end = data["end_date"]
    purpose = data["purpose"].strip()
    half = data["half_day"]
    substitute = data["substitute"]
    station_leave = data["station_leave"]
    station_details = data["station_details"].strip()
    medical_evidence = data["medical_evidence"]

    if purpose == "":
        raise ValidationError("Purpose cannot be empty")

    if station_leave and station_details == "":
        raise ValidationError("Station details required for station leave")

    policy = policy_for(leave_type, kind, medical_evidence)
    if kind not in ["faculty", "staff"] or (leave_type.type == "VL" and kind != "faculty"):
        raise ValidationError("Ineligible employee category")
    days = count_days(leave_type.type, start, end, half)

    if policy and days > policy.max_days and policy.max_days > 0:
        raise ValidationError(f"Leave days exceed policy maximum: {policy.max_days}")

    ensure_overlap_free(employee, leave_type, start, end, half, exclude)

    required_nominee = leave_type.requires_substitute or (policy and policy.requires_substitute)
    if not ensure_nominee(employee, substitute, required_nominee, start, end):
        raise ValidationError("Invalid substitute")
    ensure_balance(employee, leave_type, start, kind, days, exclude)

    data["employee"] = employee
    data["employee_kind"] = kind
    data["unit"] = UserRef.objects.get(user_id=employee).department
    data["days"] = days
    data["route"] = resolve_route(employee, leave_type.type)
    data["step"] = 0
    data["status"] = "PENDING"
    data["operation"] = "LEAVE"
    data["substitute_status"] = "PENDING" if substitute else "NONE"

    return data
