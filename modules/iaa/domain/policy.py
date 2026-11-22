"""The administered policy (UC-703, UC-704): its shape, its validation and its lookups."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from modules.iaa.domain.roles import APPROVERS, RESOLVERS
from modules.iaa.domain.state_machine import KINDS

ANOMALY_CATEGORIES = ("budget", "policy", "financial")


class PolicyInvalid(Exception):
    def __init__(self, errors: list[dict]):
        super().__init__("The policy is not valid.")
        self.errors = errors


@dataclass(frozen=True)
class Route:
    kind: str
    request_type: str
    department: str
    min_amount: Decimal
    max_amount: Decimal | None
    levels: tuple[str, ...]
    escalation_designation: str

    def covers(self, kind: str, request_type: str, department: str, amount: Decimal) -> bool:
        return (self.kind == kind
                and self.request_type in ("", request_type)
                and self.department in ("", department)
                and amount >= self.min_amount
                and (self.max_amount is None or amount < self.max_amount))

    def specificity(self) -> int:
        return (2 if self.department else 0) + (1 if self.request_type else 0)


@dataclass(frozen=True)
class Policy:
    approval_timeout_hours: int
    ta_high_value_threshold: Decimal
    budget_check_required: bool
    request_types: tuple[str, ...]
    required_documents: dict[str, int]
    routes: tuple[Route, ...]
    anomaly_resolvers: dict[str, tuple[str, ...]]


def _decimal(value, field: str, errors: list[dict]) -> Decimal | None:
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError):
        errors.append({"field": field, "message": "Enter a number."})
        return None
    if d < 0:
        errors.append({"field": field, "message": "Enter zero or more."})
        return None
    return d


def _route(i: int, raw: dict, errors: list[dict]) -> Route | None:
    f = f"routes[{i}]"
    if not isinstance(raw, dict):
        errors.append({"field": f, "message": "Each route must be an object."})
        return None
    kind = raw.get("kind")
    if kind not in KINDS:
        errors.append({"field": f + ".kind", "message": "Use 'expense' or 'ta'."})
    levels = raw.get("levels") or []
    if not isinstance(levels, list) or not levels:
        errors.append({"field": f + ".levels", "message": "List at least one approving role."})
        levels = []
    bad = [lv for lv in levels if lv not in APPROVERS]
    if bad:
        errors.append({"field": f + ".levels",
                       "message": f"Only HoD, Dean or Director roles may approve: {bad}."})
    if len(set(levels)) != len(levels):
        errors.append({"field": f + ".levels", "message": "A role may appear only once."})
    esc = raw.get("escalation_designation") or ""
    if esc and esc not in APPROVERS:
        errors.append({"field": f + ".escalation_designation",
                       "message": "Escalation must go to an HoD, Dean or Director role."})
    lo = _decimal(raw.get("min_amount", "0"), f + ".min_amount", errors)
    hi_raw = raw.get("max_amount")
    hi = None if hi_raw in (None, "") else _decimal(hi_raw, f + ".max_amount", errors)
    if lo is not None and hi is not None and hi <= lo:
        errors.append({"field": f + ".max_amount", "message": "Must be above min_amount."})
    if kind not in KINDS or lo is None:
        return None
    return Route(kind, str(raw.get("request_type") or ""), str(raw.get("department") or ""),
                 lo, hi, tuple(levels), esc)


def _overlaps(a: Route, b: Route) -> bool:
    if (a.kind, a.request_type, a.department) != (b.kind, b.request_type, b.department):
        return False
    a_hi = a.max_amount if a.max_amount is not None else Decimal("Infinity")
    b_hi = b.max_amount if b.max_amount is not None else Decimal("Infinity")
    return a.min_amount < b_hi and b.min_amount < a_hi


def parse(raw: dict) -> Policy:
    errors: list[dict] = []
    try:
        timeout = int(raw.get("approval_timeout_hours", 0))
    except (TypeError, ValueError):
        timeout = 0
    if timeout <= 0:
        errors.append({"field": "approval_timeout_hours", "message": "Enter whole hours above 0."})
    threshold = _decimal(raw.get("ta_high_value_threshold", ""), "ta_high_value_threshold",
                         errors)
    types = raw.get("request_types") or []
    if not isinstance(types, list) or not all(isinstance(t, str) and t.strip() for t in types):
        errors.append({"field": "request_types", "message": "List the expense request types."})
        types = []
    if not types:
        errors.append({"field": "request_types", "message": "Add at least one request type."})
    docs = raw.get("required_documents") or {}
    if not isinstance(docs, dict):
        errors.append({"field": "required_documents", "message": "Give a number for each kind."})
        docs = {}
    required: dict[str, int] = {}
    for kind in KINDS:
        try:
            required[kind] = int(docs.get(kind, 0))
        except (TypeError, ValueError):
            required[kind] = -1
        if required[kind] < 0:
            errors.append({"field": f"required_documents.{kind}", "message": "Enter 0 or more."})
    routes = [r for i, raw_r in enumerate(raw.get("routes") or [])
              if (r := _route(i, raw_r, errors)) is not None]
    errors.extend({"field": "routes", "message": f"Add at least one {kind} route."}
                  for kind in KINDS if not any(r.kind == kind for r in routes))
    errors.extend({"field": "routes",
                   "message": f"Two {a.kind} routes overlap for type "
                              f"'{a.request_type or 'any'}', department '{a.department or 'any'}'."}
                  for i, a in enumerate(routes) for b in routes[i + 1:] if _overlaps(a, b))
    resolvers_raw = raw.get("anomaly_resolvers") or {}
    resolvers: dict[str, tuple[str, ...]] = {}
    for cat in ANOMALY_CATEGORIES:
        chain = resolvers_raw.get(cat) if isinstance(resolvers_raw, dict) else None
        if not isinstance(chain, list) or not chain or any(c not in RESOLVERS for c in chain):
            errors.append({"field": f"anomaly_resolvers.{cat}",
                           "message": "List the resolving roles, first resolver first."})
            continue
        resolvers[cat] = tuple(chain)
    if errors:
        raise PolicyInvalid(errors)
    return Policy(timeout, threshold, bool(raw.get("budget_check_required", True)),
                  tuple(t.strip() for t in types), required, tuple(routes), resolvers)


class NoRoute(Exception):
    pass


def select_route(policy: Policy, kind: str, request_type: str, department: str,
                 amount: Decimal) -> Route:
    matches = [r for r in policy.routes if r.covers(kind, request_type, department, amount)]
    if not matches:
        raise NoRoute(kind)
    return max(matches, key=Route.specificity)


def is_high_value(policy: Policy, amount: Decimal) -> bool:
    return amount >= policy.ta_high_value_threshold
