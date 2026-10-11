"""Service-level authorization.

Two questions, answered separately — exactly like the
platform's own gates:

* **permission** — does the caller hold the ``elm.*``
  permission for this kind of work at all?
* **scope** — is this caller the *right* Unit Head, the
  *right* Sanctioning Authority, the named substitute?

A person who holds the permission but is not the right
office-holder gets a 403, not a silent success: ELM routing
is office-based, not merely role-based.
"""
from __future__ import annotations

from fusion_auth.principal import Principal
from modules.elm.models import EmployeeProfile, OrgUnit


def require_permission(principal: Principal, code: str) -> None:
    """The platform's second gate, re-stated at service
    depth so a task or command path cannot skip it."""
    if not principal.has_permission(code):
        from core.api.exceptions import PermissionDeniedError

        raise PermissionDeniedError(
            f"This action requires the {code} permission.",
            code="permission_denied",
            details=[{"permission": code}],
        )


def employee_profile(user_id: int) -> EmployeeProfile | None:
    return EmployeeProfile.objects.filter(
        user_id=user_id, is_active=True).first()


def applicant_unit(user_id: int) -> OrgUnit | None:
    profile = employee_profile(user_id)
    if profile is None or profile.unit_code_id is None:
        return None
    return OrgUnit.objects.filter(
        code=profile.unit_code_id).first()


def is_unit_head_of(principal: Principal,
                      applicant_user_id: int) -> bool:
    """True when the caller is the configured Unit Head of
    the applicant's organizational unit (PS §1)."""
    unit = applicant_unit(applicant_user_id)
    return bool(unit and unit.head_user_id == principal.user_id)


def is_establishment_role(principal: Principal) -> bool:
    """True when the caller holds an Establishment
    processing designation (EL-UC-004)."""
    from modules.elm.services import policy as policy_service

    profile = employee_profile(principal.user_id)
    if profile is None:
        return False
    return policy_service.establishment_designations(
    ) and profile.designation_name in (
        policy_service.establishment_designations())


def is_final_authority(principal: Principal,
                         authority_designation: str) -> bool:
    """True when the caller holds the designation the
    request's resolved route names as final authority."""
    profile = employee_profile(principal.user_id)
    return bool(
        profile and profile.designation_name == authority_designation)


def unit_head_user_ids() -> list[int]:
    """Every configured Unit Head — used to notify the
    concerned roles on withdrawal and to seed queues."""
    return sorted(
        OrgUnit.objects.exclude(
            head_user_id__isnull=True).values_list(
                "head_user_id", flat=True))


def user_label(principal: Principal) -> str:
    return principal.display_name or principal.username
