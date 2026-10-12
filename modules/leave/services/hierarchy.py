"""The routing hierarchy: Unit Head, establishment, final authority.

Resolved from this module's own configuration rows (BR-EL-016…020), never
from another module's tables: the directory publishes who people are, not
which desk reviews a leave file.
"""
from __future__ import annotations

from core.api.exceptions import ConflictError, NotFoundError
from modules.directory import contracts as directory
from modules.leave.models import AuthorityAssignment, OrganizationalUnit
from modules.leave.services import authz

#: Order in which the final desk is tried (BR-EL-018: configured hierarchy).
_FINAL_ORDER = (AuthorityAssignment.DEAN, AuthorityAssignment.REGISTRAR,
                AuthorityAssignment.DIRECTOR)


def department_of(user_id: int) -> str:
    users = directory.get_users([user_id])
    return users[user_id].department if user_id in users else ""


def unit_for_department(department: str) -> OrganizationalUnit | None:
    if not department:
        return None
    return (OrganizationalUnit.objects
            .filter(code__iexact=department).first()
            or OrganizationalUnit.objects
            .filter(name__iexact=department).first())


def unit_head_user_id(department: str) -> int | None:
    unit = unit_for_department(department)
    return None if unit is None else unit.head_user_id


def is_director(user_id: int) -> bool:
    return AuthorityAssignment.objects.filter(
        role_code=AuthorityAssignment.DIRECTOR, user_id=user_id).exists()


def establishment_assignee(department: str) -> int | None:
    """The establishment desk that verifies this file: the org's own desk
    first, then the institute-wide one."""
    unit = unit_for_department(department)
    rows = AuthorityAssignment.objects.filter(
        role_code=AuthorityAssignment.ESTABLISHMENT)
    if unit is not None:
        hit = rows.filter(org_unit=unit).order_by("id").first()
        if hit is not None:
            return hit.user_id
    hit = rows.filter(org_unit__isnull=True).order_by("id").first()
    return hit.user_id if hit is not None else None


def final_authority_for(category: str, department: str) -> int | None:
    """First desk in the configured hierarchy whose categories cover this
    one; org-specific assignments win over institute-wide ones."""
    unit = unit_for_department(department)
    for role in _FINAL_ORDER:
        rows = AuthorityAssignment.objects.filter(role_code=role)
        scoped = ([rows.filter(org_unit=unit), rows.filter(org_unit__isnull=True)]
                  if unit is not None
                  else [rows.filter(org_unit__isnull=True)])
        for queryset in scoped:
            for row in queryset.order_by("id"):
                cats = list(row.categories or [])
                if not cats or category in cats:
                    return row.user_id
    return None


def require_unit_head(department: str) -> int:
    """The applicant's file cannot enter review without a head to review it
    (CFR-EL-003.2). Configuration, not a bug: fix it in Administration."""
    head = unit_head_user_id(department)
    if head is None:
        raise ConflictError(
            "No Unit Head is configured for your organisational unit; ask an "
            "administrator to set one before applying.",
            code="no_unit_head")
    return head


def require_authority(category: str, department: str) -> int:
    authority = final_authority_for(category, department)
    if authority is None:
        raise ConflictError(
            f"No sanctioning authority is configured for "
            f"{category.upper()} leave; ask an administrator to assign one.",
            code="no_authority")
    return authority


# -- configuration (admin) -------------------------------------------------
def configure_unit(actor, data: dict) -> OrganizationalUnit:
    authz.require(actor, "leave.type.manage")
    pk = data.get("id")
    unit = (OrganizationalUnit.objects.filter(pk=pk).first() if pk
            else OrganizationalUnit.objects.filter(
                code=str(data["code"])).first())
    if unit is None:
        unit = OrganizationalUnit(code=str(data["code"]))
    unit.name = data.get("name", unit.name or unit.code)
    unit.kind = data.get("kind", unit.kind)
    if "head_user_id" in data:
        unit.head_user_id = data["head_user_id"]
    unit.save()
    return unit


def configure_authority(actor, data: dict) -> AuthorityAssignment:
    authz.require(actor, "leave.type.manage")
    role = str(data["role_code"])
    if role not in {r for r, _ in AuthorityAssignment.ROLE}:
        raise NotFoundError("Unknown authority role.", code="unknown_role")
    unit = None
    if data.get("org_unit_id"):
        unit = OrganizationalUnit.objects.filter(
            pk=data["org_unit_id"]).first()
        if unit is None:
            raise NotFoundError("Organisational unit not found.",
                                code="not_found")
    pk = data.get("id")
    row = AuthorityAssignment.objects.filter(pk=pk).first() if pk else None
    if row is None:
        row = AuthorityAssignment.objects.filter(
            role_code=role, org_unit=unit).first()
    if row is None:
        row = AuthorityAssignment(role_code=role, org_unit=unit)
    row.user_id = int(data["user_id"])
    row.categories = list(data.get("categories") or [])
    row.save()
    return row


def remove_authority(actor, pk: int) -> None:
    authz.require(actor, "leave.type.manage")
    deleted, _ = AuthorityAssignment.objects.filter(pk=pk).delete()
    if not deleted:
        raise NotFoundError("Authority assignment not found.",
                            code="not_found")
