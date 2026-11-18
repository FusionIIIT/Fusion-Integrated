from decimal import Decimal, InvalidOperation

ROLES = (
    "employee",
    "department_admin",
    "department_head",
    "ps_admin",
    "accounts",
    "final_authority",
    "committee",
    "vendor",
    "auditor",
)
TERMINAL = ("cancelled", "withdrawn", "rejected", "completed", "paid")


def decimal_value(value):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("Enter a valid decimal number.") from exc
    if not result.is_finite():
        raise ValueError("Enter a finite number.")
    return result


def approval_route(configuration, amount, priority):
    bands = configuration.get("approval_bands", [])
    for band in bands:
        ceiling = band.get("up_to")
        if ceiling is None or amount <= decimal_value(ceiling):
            route = band.get("roles", [])
            if not route or any(r not in ROLES for r in route):
                raise ValueError("Approval route has not been configured.")
            return configuration.get("priority_routes", {}).get(str(priority), route)
    raise ValueError("No configured approval band covers this indent.")


def procurement_method(configuration, amount):
    threshold = configuration.get("tender_threshold")
    if threshold is None:
        raise ValueError("Configure the tender threshold before procurement.")
    return "tender" if amount >= decimal_value(threshold) else "direct"
