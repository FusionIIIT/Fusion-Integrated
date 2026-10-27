from decimal import Decimal

def calculate_year_end_adjustments(current_balances: dict, is_faculty: bool) -> dict:
    balances = {str(k).upper(): Decimal(str(v)) for k, v in current_balances.items()}
    cl = balances.get("CL", Decimal("0"))
    rh = balances.get("RH", Decimal("0"))
    scl = balances.get("SCL", Decimal("0"))
    el = balances.get("EL", Decimal("0"))
    vl = balances.get("VL", Decimal("0"))
    col = balances.get("COL", Decimal("0"))

    converted_el = (vl / Decimal("2")) if is_faculty else Decimal("0")
    carried_el = el + converted_el
    carried_col = col

    # Result mapping
    result = {
        "CL": Decimal("0"),
        "RH": Decimal("0"),
        "SCL": Decimal("0"),
        "EL": carried_el + (Decimal("0") if is_faculty else Decimal("30")),
        "VL": Decimal("0"),
        "COL": carried_col + Decimal("20"),
        "cl": Decimal("0"),
        "rh": Decimal("0"),
        "scl": Decimal("0"),
        "el": carried_el + (Decimal("0") if is_faculty else Decimal("30")),
        "vl": Decimal("0"),
        "col": carried_col + Decimal("20"),
        "converted_el": converted_el,
        "carried_forward_el": carried_el,
        "carried_forward_col": carried_col
    }
    return result