"""Leave entitlements (BR-EL-002..009). Small dict, local llm style."""
ENTITLEMENT = {
    "CL": 8,
    "RH": 2,
    "SCL": 15,
    "EL": 30,
    "COL": 20,
    "VL": 60,
}

# leave that carry forward
CARRY = {"EL", "COL"}

# counted continuously incl weekends
CONTINUOUS = {"EL", "COL", "VL"}


def yearly_credit(category: str) -> int:
    return ENTITLEMENT.get(category, 0)


def carries_forward(category: str) -> bool:
    return category in CARRY


def vl_to_el(vl_left: float) -> float:
    return vl_left / 2.0


def count_days(category: str, start, end, half=False) -> float:
    if half and category == "CL":
        return 0.5
    days = (end - start).days + 1
    return float(max(days, 0))
