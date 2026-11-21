"""BR-EL-016..020 and BR-EL-030: resolve who acts, from current configuration."""
from __future__ import annotations

from dataclasses import dataclass

from django.db.models import Q

from core.api.exceptions import ConflictError
from modules.leave.domain.categories import UNIT_HEAD_FINAL, Category, EmployeeKind
from modules.leave.domain.workflow import Route
from modules.leave.models import AuthorityRule, InstituteOffice, OrgUnit


@dataclass(frozen=True)
class ResolvedRoute:
    route: Route
    unit_head_user_id: int | None
    establishment_user_id: int | None
    sanctioning_user_id: int


def director_id() -> int | None:
    office = InstituteOffice.objects.filter(code=InstituteOffice.DIRECTOR).first()
    return office.user_id if office else None


def _unit_head(unit: OrgUnit, applicant_id: int) -> int | None:
    """A head never reviews their own leave; it goes to the parent unit's head."""
    seen: set[int] = set()
    while unit is not None and unit.pk not in seen:
        seen.add(unit.pk)
        if unit.head_user_id and unit.head_user_id != applicant_id:
            return unit.head_user_id
        unit = unit.parent
    return None


def _rule(category: Category, unit: OrgUnit, kind: EmployeeKind) -> AuthorityRule | None:
    candidates = AuthorityRule.objects.filter(
        Q(unit=unit) | Q(unit__isnull=True), category=category,
        applicant_kind__in=[kind.value, ""])
    return min(candidates, default=None,
               key=lambda r: (r.unit_id is None, r.applicant_kind == ""))


def resolve(applicant_id: int, kind: EmployeeKind, department: str,
            category: Category) -> ResolvedRoute:
    if director_id() == applicant_id:
        return ResolvedRoute(Route(unit_head_final=False, establishment=False,
                                   director_self=True), None, None, applicant_id)
    unit = OrgUnit.objects.filter(name=department).first() if department else None
    if unit is None:
        raise ConflictError(
            f"Your unit ({department or 'not recorded'}) has no leave hierarchy yet. "
            "Ask the Leave Administrator to configure it.", code="unit_not_configured")
    head = _unit_head(unit, applicant_id)
    if head is None:
        raise ConflictError(f"No Unit Head is configured for {unit.name}. Ask the Leave "
                            "Administrator to assign one.", code="unit_head_missing")
    if category in UNIT_HEAD_FINAL:
        return ResolvedRoute(Route(unit_head_final=True, establishment=False,
                                   director_self=False), head, None, head)
    rule = _rule(category, unit, kind)
    if rule is None:
        raise ConflictError(f"No sanctioning authority is configured for {category} in "
                            f"{unit.name}. Ask the Leave Administrator to add one.",
                            code="authority_not_configured")
    if applicant_id in (rule.sanctioning_user_id, rule.establishment_user_id):
        raise ConflictError("The configured route would have you act on your own leave. "
                            "Ask the Leave Administrator to correct the hierarchy.",
                            code="self_routing")
    return ResolvedRoute(
        Route(unit_head_final=False, establishment=rule.establishment_user_id is not None,
              director_self=False),
        head, rule.establishment_user_id, rule.sanctioning_user_id)
