"""Leave policy validation, sourced from the ELM baseline BR-EL-001..011."""
from decimal import Decimal, InvalidOperation

DEFAULT_PARAMS = {
    "CL": {"annual_entitlement": "8", "carry_forward": False},
    "RH": {"annual_entitlement": "2", "carry_forward": False},
    "SCL": {"annual_entitlement": "15", "carry_forward": False},
    "EL": {"annual_entitlement": "30", "carry_forward": True, "employee_kinds": ["staff"]},
    "COL": {"annual_entitlement": "20", "carry_forward": True},
    "VL": {"annual_entitlement": "60", "carry_forward": False, "employee_kinds": ["faculty"], "vacation_only": True},
}


class PolicyViolation(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def merged_params(params: dict | None) -> dict:
    result = {key: dict(value) for key, value in DEFAULT_PARAMS.items()}
    for key, value in (params or {}).items():
        if key in result and isinstance(value, dict):
            result[key].update(value)
    return result


def annual_credit_for(category: str, kind: str, params: dict | None = None) -> Decimal:
    cfg = merged_params(params).get(category)
    if cfg is None:
        raise PolicyViolation("invalid_category", f"Unknown leave category: {category}.")
    allowed = cfg.get("employee_kinds")
    if allowed and kind not in allowed:
        raise PolicyViolation("category_ineligible", f"{category} is not available to {kind} employees.")
    try:
        amount = Decimal(str(cfg["annual_entitlement"]))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise PolicyViolation("invalid_policy", f"{category} annual entitlement must be numeric.") from exc
    if not amount.is_finite() or amount <= 0:
        raise PolicyViolation("invalid_policy", f"{category} annual entitlement must be a positive finite number.")
    return amount


def check_eligible(category: str, kind: str, params: dict | None = None) -> None:
    annual_credit_for(category, kind, params)


def validate_params(params: dict) -> dict:
    """Validate current parameters without creating a policy-version lifecycle."""
    from decimal import InvalidOperation

    if not isinstance(params, dict):
        raise PolicyViolation("invalid_policy", "Policy parameters must be a JSON object.")
    unknown = set(params) - (set(DEFAULT_PARAMS) | {"sla"})
    if unknown:
        raise PolicyViolation("invalid_policy", f"Unknown policy keys: {', '.join(sorted(unknown))}.")
    for category in DEFAULT_PARAMS:
        if category in params and not isinstance(params[category], dict):
            raise PolicyViolation("invalid_policy", f"{category} parameters must be a JSON object.")
    merged = merged_params(params)
    for category, cfg in merged.items():
        try:
            entitlement = Decimal(str(cfg["annual_entitlement"]))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise PolicyViolation("invalid_policy", f"{category} annual entitlement must be numeric.") from exc
        if not entitlement.is_finite() or entitlement <= 0:
            raise PolicyViolation("invalid_policy", f"{category} annual entitlement must be a positive finite number.")
        if not isinstance(cfg.get("carry_forward"), bool):
            raise PolicyViolation("invalid_policy", f"{category} carry_forward must be boolean.")
        if cfg["carry_forward"] != DEFAULT_PARAMS[category]["carry_forward"]:
            raise PolicyViolation("invalid_policy", f"{category} carry-forward behavior is fixed by the ELM business rules.")
        kinds = cfg.get("employee_kinds")
        if kinds is not None and (not isinstance(kinds, list) or not set(kinds) <= {"faculty", "staff"}):
            raise PolicyViolation("invalid_policy", f"{category} employee_kinds must contain only faculty/staff.")
    sla = params.get("sla", {})
    if not isinstance(sla, dict):
        raise PolicyViolation("invalid_policy", "sla must be a JSON object.")
    unknown_sla = set(sla) - {"reminder_hours", "escalation_hours", "escalation_role"}
    if unknown_sla:
        raise PolicyViolation("invalid_policy", f"Unknown SLA keys: {', '.join(sorted(unknown_sla))}.")
    for key in ("reminder_hours", "escalation_hours"):
        value = sla.get(key)
        if value is not None:
            try:
                number = Decimal(str(value))
            except (InvalidOperation, TypeError, ValueError) as exc:
                raise PolicyViolation("invalid_policy", f"sla.{key} must be numeric.") from exc
            if not number.is_finite() or number < 0:
                raise PolicyViolation("invalid_policy", f"sla.{key} must be a non-negative finite number.")
    reminder, escalation = sla.get("reminder_hours"), sla.get("escalation_hours")
    if escalation is not None and not str(sla.get("escalation_role", "")).strip():
        raise PolicyViolation("invalid_policy", "sla.escalation_role is required when escalation is enabled.")
    if reminder is not None and escalation is not None and Decimal(str(escalation)) < Decimal(str(reminder)):
        raise PolicyViolation("invalid_policy", "SLA escalation must not be earlier than reminder.")
    return params


def validate_hierarchy(hierarchy: dict) -> dict:
    if not isinstance(hierarchy, dict):
        raise PolicyViolation("invalid_hierarchy", "Approval hierarchy must be a JSON object.")
    unit_heads = hierarchy.get("unit_heads", {})
    sanctioning = hierarchy.get("sanctioning", {})
    default_sanctioning = hierarchy.get("default_sanctioning", [])
    if not isinstance(unit_heads, dict) or any(not isinstance(k, str) or not isinstance(v, str) or not v.strip() for k, v in unit_heads.items()):
        raise PolicyViolation("invalid_hierarchy", "unit_heads must map department names to designation names.")
    if not isinstance(sanctioning, dict) or not set(sanctioning) <= {"SCL", "EL", "COL", "VL"} or any(not isinstance(v, list) or any(not isinstance(role, str) or not role.strip() for role in v) for v in sanctioning.values()):
        raise PolicyViolation("invalid_hierarchy", "sanctioning must map higher-sanction categories to lists of designation names.")
    if not isinstance(default_sanctioning, list) or any(not isinstance(role, str) or not role.strip() for role in default_sanctioning):
        raise PolicyViolation("invalid_hierarchy", "default_sanctioning must be a list of designation names.")
    return hierarchy
