"""The current configuration as domain values, and every write of a new revision."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.db import transaction

from core.api.exceptions import ConflictError, DomainError
from modules.leave import registry
from modules.leave.domain import categories as cat
from modules.leave.domain import policy as pol
from modules.leave.domain import routing
from modules.leave.domain import sla as sla_domain
from modules.leave.domain.authority import STEP_PERMISSIONS
from modules.leave.domain.validation import CalendarView
from modules.leave.models import (
    CategoryRule,
    HierarchyRevision,
    Holiday,
    HolidayCalendar,
    OrgUnit,
    PolicyRevision,
    SanctionRoute,
    SlaRevision,
    SlaRule,
    VacationPeriod,
)
from modules.leave.services import authz


class ConfigurationInvalid(DomainError):
    code = "configuration_invalid"
    message = "The configuration was not saved."


def _missing(what: str) -> ConflictError:
    return ConflictError(f"No {what} is configured yet. Ask the Leave Administrator to set it "
                         f"up before using Leave.", code="not_configured")


# -- policy -------------------------------------------------------------------
def current_policy(*, required: bool = True) -> pol.Policy | None:
    rev = PolicyRevision.objects.prefetch_related("rules").first()
    if rev is None:
        if required:
            raise _missing("leave policy")
        return None
    return pol.Policy(
        rules={r.category: pol.CategoryRule(r.category, r.annual_entitlement, r.substitute,
                                            r.evidence_min_days)
               for r in rev.rules.all()},
        weekend_days=frozenset(rev.weekend_days),
        max_backdate_days=rev.max_backdate_days, revision_id=rev.pk)


@transaction.atomic
def save_policy(*, actor, rules: Iterable[dict], weekend_days: Iterable[int],
                max_backdate_days: int, note: str = "") -> PolicyRevision:
    authz.require(actor, "leave.policy.update")
    policy = pol.Policy(
        rules={r["category"]: pol.CategoryRule(
            r["category"], Decimal(str(r["annual_entitlement"])),
            r.get("substitute", pol.OPTIONAL),
            Decimal(str(r["evidence_min_days"])) if r.get("evidence_min_days") not in (None, "")
            else None) for r in rules},
        weekend_days=frozenset(int(d) for d in weekend_days),
        max_backdate_days=int(max_backdate_days))
    try:
        pol.validate(policy)
    except pol.PolicyInvalid as exc:
        raise ConfigurationInvalid(
            "The policy was not saved.",
            details=[{"message": p} for p in exc.problems]) from exc
    return _write_policy(policy, actor_id=actor.user_id, note=note)


def _write_policy(policy: pol.Policy, *, actor_id: int | None, note: str) -> PolicyRevision:
    rev = PolicyRevision.objects.create(weekend_days=sorted(policy.weekend_days),
                                        max_backdate_days=policy.max_backdate_days,
                                        note=note[:300], created_by_user_id=actor_id)
    CategoryRule.objects.bulk_create([
        CategoryRule(revision=rev, category=r.category, annual_entitlement=r.annual_entitlement,
                     substitute=r.substitute, evidence_min_days=r.evidence_min_days)
        for r in policy.rules.values()])
    return rev


def seed_policy(*, note: str = "Baseline from PS v1.4") -> PolicyRevision | None:
    """Idempotent: writes the baseline only when no policy exists."""
    if PolicyRevision.objects.exists():
        return None
    return _write_policy(pol.baseline(), actor_id=None, note=note)


# -- hierarchy ----------------------------------------------------------------
def designations_with(code: str) -> frozenset[str]:
    return frozenset(d for d, codes in registry.ROLE_GRANTS.items()
                     if code in codes and d not in cat.EMPLOYEE_KINDS)


def current_hierarchy(*, required: bool = True) -> routing.Hierarchy | None:
    rev = HierarchyRevision.objects.prefetch_related("units", "routes").first()
    if rev is None:
        if required:
            raise _missing("leave hierarchy")
        return None
    return routing.Hierarchy(
        units={u.department: routing.OrgUnit(u.department, u.unit_head_designation,
                                             u.head_leave_designation)
               for u in rev.units.all()},
        routes=tuple(routing.SanctionRoute(
            sanction_designation=r.sanction_designation,
            establishment_designation=r.establishment_designation,
            employee_kind=r.employee_kind, category=r.category, department=r.department,
            applicant_designation=r.applicant_designation) for r in rev.routes.all()),
        revision_id=rev.pk)


@transaction.atomic
def save_hierarchy(*, actor, units: Iterable[dict], routes: Iterable[dict],
                   note: str = "") -> HierarchyRevision:
    authz.require(actor, "leave.hierarchy.update")
    h = routing.Hierarchy(
        units={u["department"].strip(): routing.OrgUnit(
            u["department"].strip(), u["unit_head_designation"].strip(),
            (u.get("head_leave_designation") or "").strip()) for u in units},
        routes=tuple(routing.SanctionRoute(
            sanction_designation=r["sanction_designation"].strip(),
            establishment_designation=(r.get("establishment_designation") or "").strip(),
            employee_kind=(r.get("employee_kind") or "").strip(),
            category=(r.get("category") or "").strip(),
            department=(r.get("department") or "").strip(),
            applicant_designation=(r.get("applicant_designation") or "").strip())
            for r in routes))
    return _write_hierarchy(h, actor_id=actor.user_id, note=note)


def _write_hierarchy(h: routing.Hierarchy, *, actor_id: int | None,
                     note: str) -> HierarchyRevision:
    problems = routing.validate(
        h, reviewers=designations_with(STEP_PERMISSIONS["unit_head"]),
        establishments=designations_with(STEP_PERMISSIONS["establishment"]),
        authorities=designations_with(STEP_PERMISSIONS["authority"]))
    if problems:
        raise ConfigurationInvalid("The hierarchy was not saved.",
                                   details=[{"message": p} for p in problems])
    rev = HierarchyRevision.objects.create(note=note[:300], created_by_user_id=actor_id)
    OrgUnit.objects.bulk_create([
        OrgUnit(revision=rev, department=u.department,
                unit_head_designation=u.unit_head_designation,
                head_leave_designation=u.head_leave_designation) for u in h.units.values()])
    SanctionRoute.objects.bulk_create([
        SanctionRoute(revision=rev, employee_kind=r.employee_kind, category=r.category,
                      department=r.department, applicant_designation=r.applicant_designation,
                      establishment_designation=r.establishment_designation,
                      sanction_designation=r.sanction_designation) for r in h.routes])
    return rev


#: A starting point for the institute to correct (blueprint §8 Q13), not its policy.
SEED_UNITS = (
    ("CSE", "HOD (CSE)", "Director"), ("ECE", "HOD (ECE)", "Director"),
    ("ME", "HOD (ME)", "Director"), ("Natural Science", "HOD (NS)", "Director"),
    ("Design", "HOD (Design)", "Director"), ("Registrar Office", "Registrar", "Director"),
)
SEED_ROUTES = (
    routing.SanctionRoute("Director", "Deputy Registrar", employee_kind=cat.FACULTY),
    routing.SanctionRoute("Registrar", "Deputy Registrar", employee_kind=cat.STAFF),
    routing.SanctionRoute("Director", "", applicant_designation="Registrar"),
    routing.SanctionRoute("Registrar", "", applicant_designation="Deputy Registrar"),
)


def seed_hierarchy() -> HierarchyRevision | None:
    if HierarchyRevision.objects.exists():
        return None
    h = routing.Hierarchy(units={d: routing.OrgUnit(d, head, alt) for d, head, alt in SEED_UNITS},
                          routes=SEED_ROUTES)
    return _write_hierarchy(h, actor_id=None, note="Seeded starting point; review it.")


# -- SLA ----------------------------------------------------------------------
def current_sla() -> dict[str, sla_domain.Rule]:
    rev = SlaRevision.objects.prefetch_related("rules").first()
    if rev is None:
        return {}
    return {r.step: sla_domain.Rule(r.step, r.reminder_hours, r.escalation_hours, r.action,
                                    r.escalate_to) for r in rev.rules.all()}


@transaction.atomic
def save_sla(*, actor, rules: Iterable[dict], note: str = "") -> SlaRevision:
    authz.require(actor, "leave.sla.update")
    parsed = [sla_domain.Rule(r["step"], int(r["reminder_hours"]), int(r["escalation_hours"]),
                              r.get("action", sla_domain.NOTIFY),
                              (r.get("escalate_to") or "").strip()) for r in rules]
    problems = sla_domain.validate(
        parsed, may_act={step: designations_with(code)
                         for step, code in STEP_PERMISSIONS.items()})
    if problems:
        raise ConfigurationInvalid("The SLA thresholds were not saved.",
                                   details=[{"message": p} for p in problems])
    rev = SlaRevision.objects.create(note=note[:300], created_by_user_id=actor.user_id)
    SlaRule.objects.bulk_create([
        SlaRule(revision=rev, step=r.step, reminder_hours=r.reminder_hours,
                escalation_hours=r.escalation_hours, action=r.action, escalate_to=r.escalate_to)
        for r in parsed])
    return rev


# -- calendars ----------------------------------------------------------------
@dataclass(frozen=True)
class EffectiveCalendar:
    view: CalendarView
    vacations: tuple[tuple[date, date], ...]


def calendar_for(start: date, end: date) -> EffectiveCalendar:
    """BR-EL-031: the published calendar of every year the period touches, merged."""
    years = list(range(start.year, end.year + 1))
    published = {c.year: c for c in HolidayCalendar.objects.filter(
        year__in=years, status=HolidayCalendar.PUBLISHED)}
    rows = Holiday.objects.filter(calendar__in=published.values()).values_list("date", "kind")
    closed = frozenset(d for d, k in rows if k == Holiday.CLOSED)
    restricted = frozenset(d for d, k in rows if k == Holiday.RESTRICTED)
    vacations = tuple(VacationPeriod.objects.filter(end_date__gte=start, start_date__lte=end)
                      .values_list("start_date", "end_date"))
    return EffectiveCalendar(
        CalendarView(published=all(y in published for y in years), closed=closed,
                     restricted=restricted), vacations)
