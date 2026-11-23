"""PMS settings as one immutable value; a published version is superseded, never edited."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation

from modules.pms.domain.errors import InvalidInput
from modules.pms.domain.state_machine import WITHDRAWAL_CANDIDATES

DOMAIN_CODE = re.compile(r"^[a-z][a-z0-9_]{1,39}$")
JURISDICTION = re.compile(r"^[A-Z]{2,5}$")
IPC_CLASS = re.compile(r"^[A-H][0-9]{2}[A-Z]$")
MAX_THRESHOLD = Decimal("9999999999.99")


@dataclass(frozen=True)
class Domain:
    code: str
    label: str
    ipc_classes: tuple[str, ...] = ()


@dataclass(frozen=True)
class LicensingRoute:
    kind: str                      # "director" or "committee"
    director_user_id: int | None = None
    committee_name: str = ""


@dataclass(frozen=True)
class PolicySpec:
    version: int = 0
    cost_threshold: Decimal | None = None
    appeal_period_days: int = 30                          # ruling B7
    alert_offsets_days: tuple[int, ...] = (30, 15, 5)     # BR-PMS-101..103
    withdrawal_statuses: frozenset[str] = frozenset()     # ruling C15: none to start
    withdrawal_consent_required: bool = False             # ruling C15
    holidays: frozenset[date] = frozenset()               # ruling C10
    domains: tuple[Domain, ...] = ()                      # ruling C13
    maintenance_rules: dict[str, tuple[int, ...]] = field(default_factory=dict)
    escalation_chain: tuple[int, ...] = ()                # ruling C21
    pcc_contact_user_id: int | None = None                # blueprint Q-7
    auto_routing_enabled: bool = False                    # BR-PMS-022
    licensing_route: LicensingRoute | None = None         # BR-PMS-088

    def domain(self, code: str) -> Domain | None:
        return next((d for d in self.domains if d.code == code), None)

    @property
    def domain_codes(self) -> frozenset[str]:
        return frozenset(d.code for d in self.domains)

    @property
    def escalation_recipients(self) -> tuple[int, ...]:
        """BR-PMS-104: the configured chain, else the PCC_ADMIN contact, else nobody."""
        if self.escalation_chain:
            return self.escalation_chain
        return (self.pcc_contact_user_id,) if self.pcc_contact_user_id else ()


DEFAULTS = PolicySpec()


def _int(value, name: str, lo: int, hi: int) -> int:
    try:
        out = int(value)
    except (TypeError, ValueError) as exc:
        raise InvalidInput(f"{name} must be a whole number.", code="invalid_policy") from exc
    if isinstance(value, bool) or not lo <= out <= hi:
        raise InvalidInput(f"{name} must be between {lo} and {hi}.", code="invalid_policy")
    return out


def _user_id(value, name: str) -> int:
    return _int(value, name, 1, 2_147_483_647)


def _domains(raw) -> tuple[Domain, ...]:
    if not isinstance(raw, list):
        raise InvalidInput("Technical areas must be a list.", code="invalid_policy")
    seen, out = set(), []
    for item in raw:
        if not isinstance(item, dict):
            raise InvalidInput("Each technical area needs a code and a label.",
                               code="invalid_policy")
        code = str(item.get("code", "")).strip()
        label = str(item.get("label", "")).strip()
        if not DOMAIN_CODE.match(code):
            raise InvalidInput(
                f"Area code '{code}' must be 2-40 lowercase letters, digits or underscores, "
                f"starting with a letter.", code="invalid_policy")
        if not label or len(label) > 120:
            raise InvalidInput(f"Area '{code}' needs a label of at most 120 characters.",
                               code="invalid_policy")
        if code in seen:
            raise InvalidInput(f"Area code '{code}' appears twice.", code="invalid_policy")
        ipc = item.get("ipc_classes", []) or []
        if not isinstance(ipc, list) or not all(isinstance(c, str) and IPC_CLASS.match(c)
                                                for c in ipc):
            raise InvalidInput(
                f"Area '{code}': IPC classes look like G06F (section, two digits, a letter).",
                code="invalid_policy")
        seen.add(code)
        out.append(Domain(code, label, tuple(ipc)))
    return tuple(out)


def _maintenance(raw) -> dict[str, tuple[int, ...]]:
    if not isinstance(raw, dict):
        raise InvalidInput("Maintenance rules must map a jurisdiction to months.",
                           code="invalid_policy")
    out = {}
    for juris, months in raw.items():
        if not JURISDICTION.match(str(juris)):
            raise InvalidInput(f"Jurisdiction '{juris}' must be 2-5 capital letters, like IN.",
                               code="invalid_policy")
        if not isinstance(months, list) or not months:
            raise InvalidInput(f"{juris}: list the months after grant when fees fall due.",
                               code="invalid_policy")
        values = tuple(_int(m, f"{juris} month", 1, 600) for m in months)
        if list(values) != sorted(set(values)):
            raise InvalidInput(f"{juris}: months must increase with no repeats.",
                               code="invalid_policy")
        out[str(juris)] = values
    return out


def _route(raw) -> LicensingRoute | None:
    if raw in (None, {}):
        return None
    if not isinstance(raw, dict) or raw.get("kind") not in ("director", "committee"):
        raise InvalidInput("Licensing routing goes to a 'director' or a 'committee'.",
                           code="invalid_policy")
    if raw["kind"] == "director":
        return LicensingRoute("director", director_user_id=_user_id(
            raw.get("director_user_id"), "The licensing Director"))
    name = str(raw.get("committee_name", "")).strip()
    if not name or len(name) > 200:
        raise InvalidInput("Name the licensing committee (at most 200 characters).",
                           code="invalid_policy")
    return LicensingRoute("committee", committee_name=name)


def parse(raw: dict, *, version: int) -> PolicySpec:
    """Validate a settings payload and build the spec, refusing with a sentence per problem."""
    threshold = raw.get("cost_threshold")
    if threshold in (None, ""):
        cost = None
    else:
        try:
            cost = Decimal(str(threshold))
        except InvalidOperation as exc:
            raise InvalidInput("The budget threshold must be an amount in rupees.",
                               code="invalid_policy") from exc
        if not cost.is_finite() or cost <= 0 or cost > MAX_THRESHOLD \
                or cost != cost.quantize(Decimal("0.01")):
            raise InvalidInput("The budget threshold must be a positive amount in rupees "
                               "with at most two decimal places.", code="invalid_policy")
    offsets = raw.get("alert_offsets_days", list(DEFAULTS.alert_offsets_days))
    if not isinstance(offsets, list) or not offsets:
        raise InvalidInput("List at least one alert interval in days.", code="invalid_policy")
    alert = tuple(sorted({_int(o, "An alert interval", 1, 365) for o in offsets},
                         reverse=True))
    statuses = raw.get("withdrawal_statuses", [])
    if not isinstance(statuses, list) or not set(statuses) <= set(WITHDRAWAL_CANDIDATES):
        raise InvalidInput("Withdrawal can only be allowed from: "
                           + ", ".join(WITHDRAWAL_CANDIDATES) + ".", code="invalid_policy")
    holidays_raw = raw.get("holidays", [])
    if not isinstance(holidays_raw, list):
        raise InvalidInput("Holidays must be a list of dates.", code="invalid_policy")
    try:
        holidays = frozenset(date.fromisoformat(str(d)) for d in holidays_raw)
    except ValueError as exc:
        raise InvalidInput("Write each holiday as YYYY-MM-DD.", code="invalid_policy") from exc
    chain_raw = raw.get("escalation_chain", [])
    if not isinstance(chain_raw, list):
        raise InvalidInput("The escalation chain must be a list of people.",
                           code="invalid_policy")
    chain = tuple(dict.fromkeys(_user_id(u, "An escalation recipient") for u in chain_raw))
    contact = raw.get("pcc_contact_user_id")
    return PolicySpec(
        version=version,
        cost_threshold=cost,
        appeal_period_days=_int(raw.get("appeal_period_days", DEFAULTS.appeal_period_days),
                                "The appeal period", 1, 365),
        alert_offsets_days=alert,
        withdrawal_statuses=frozenset(statuses),
        withdrawal_consent_required=bool(raw.get("withdrawal_consent_required", False)),
        holidays=holidays,
        domains=_domains(raw.get("domains", [])),
        maintenance_rules=_maintenance(raw.get("maintenance_rules", {})),
        escalation_chain=chain,
        pcc_contact_user_id=None if contact in (None, "") else _user_id(
            contact, "The PCC_ADMIN contact"),
        auto_routing_enabled=bool(raw.get("auto_routing_enabled", False)),
        licensing_route=_route(raw.get("licensing_route")),
    )


def to_payload(spec: PolicySpec) -> dict:
    """The JSON shape `parse` accepts, so a version round-trips exactly."""
    route = spec.licensing_route
    return {
        "cost_threshold": None if spec.cost_threshold is None else str(spec.cost_threshold),
        "appeal_period_days": spec.appeal_period_days,
        "alert_offsets_days": list(spec.alert_offsets_days),
        "withdrawal_statuses": sorted(spec.withdrawal_statuses),
        "withdrawal_consent_required": spec.withdrawal_consent_required,
        "holidays": sorted(d.isoformat() for d in spec.holidays),
        "domains": [{"code": d.code, "label": d.label, "ipc_classes": list(d.ipc_classes)}
                    for d in spec.domains],
        "maintenance_rules": {k: list(v) for k, v in sorted(spec.maintenance_rules.items())},
        "escalation_chain": list(spec.escalation_chain),
        "pcc_contact_user_id": spec.pcc_contact_user_id,
        "auto_routing_enabled": spec.auto_routing_enabled,
        "licensing_route": None if route is None else {
            "kind": route.kind, "director_user_id": route.director_user_id,
            "committee_name": route.committee_name},
    }


def missing_configuration(spec: PolicySpec, *, directors: int, panel: int) -> list[str]:
    """Settings PCC_ADMIN has not supplied yet, each as an instruction (Step 2.8)."""
    gaps = []
    if not spec.domains:
        gaps.append("No technical areas are configured, so no application can be submitted. "
                    "Add areas under Settings.")
    if directors == 0:
        gaps.append("No Directors are on the roster, so no application can be assigned for "
                    "review. Add them under Directors.")
    if panel == 0:
        gaps.append("The attorney panel is empty, so attorneys can only be assigned by "
                    "recorded exception. Add attorneys under Attorney Panel.")
    if spec.cost_threshold is None:
        gaps.append("No budget threshold is configured, so no budget can be decided. "
                    "Set one under Settings.")
    if not spec.withdrawal_statuses:
        gaps.append("No status allows withdrawal yet, so applicants cannot withdraw. "
                    "Choose the statuses under Settings.")
    if spec.pcc_contact_user_id is None:
        gaps.append("No PCC_ADMIN contact is set, so escalations and declines are shown "
                    "in PMS but not emailed. Set the contact under Settings.")
    if not spec.maintenance_rules:
        gaps.append("No maintenance schedule rules are configured; attorneys must enter "
                    "each maintenance due date by hand.")
    if spec.licensing_route is None:
        gaps.append("No licensing route is configured, so licensing requests wait in "
                    "Submitted until PCC_ADMIN routes them.")
    return gaps
