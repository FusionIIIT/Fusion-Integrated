"""Company registration and authorization (PC-UC-014, PC-AFR-044, PC-BR-007)."""
from __future__ import annotations

from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.text import slugify

from core.api.exceptions import ConflictError, NotFoundError
from modules.placement.models import Company, CompanyContact, RecruiterSession
from modules.placement.services import notifications
from modules.placement.services.authz import require

P_MANAGE = "placement.company.manage"
SLUG_ATTEMPTS = 5


def _unique_slug(name: str) -> str:
    base = slugify(name)[:70] or "company"
    slug, n = base, 1
    while Company.objects.filter(slug=slug).exists():
        n += 1
        slug = f"{base}-{n}"[:80]
    return slug


def _constraint(exc: IntegrityError) -> str | None:
    return getattr(getattr(exc.__cause__, "diag", None), "constraint_name", None)


def _is_slug_clash(exc: IntegrityError) -> bool:
    return _constraint(exc) == f"{Company._meta.db_table}_slug_key"


def _already_registered(name: str) -> ConflictError:
    return ConflictError(f"{name} is already registered with the placement office.",
                         code="company_exists")


def _create_with_unique_slug(**fields) -> Company:
    # Two registrations of one name can both see a slug as free; the unique index picks the winner.
    for _ in range(SLUG_ATTEMPTS):
        try:
            with transaction.atomic():
                return Company.objects.create(slug=_unique_slug(fields["name"]), **fields)
        except IntegrityError as exc:
            if _constraint(exc) == "company_name_unique_ci":
                raise _already_registered(fields["name"]) from exc
            if not _is_slug_clash(exc):
                raise
    raise ConflictError(
        "Several companies with this name are being registered right now. Submit it again.",
        code="company_slug_contention")


@transaction.atomic
def register(*, name: str, sector: str = "", website: str = "",
             hq_city: str = "", contact: dict | None = None,
             registered_by_user_id: int | None = None, actor=None) -> Company:
    """Record a registration request."""
    if actor is not None:
        require(actor, P_MANAGE)
    name = (name or "").strip()
    if not name:
        raise ConflictError("A company name is required.", code="name_required")
    if Company.objects.filter(name__iexact=name).exists():
        raise _already_registered(name)

    company = _create_with_unique_slug(
        name=name, sector=sector, website=website,
        hq_city=hq_city, approval_status="pending", status="prospect",
        registered_by_user_id=registered_by_user_id,
    )
    if contact:
        CompanyContact.objects.create(
            company=company, name=contact.get("name", ""),
            designation=contact.get("designation", ""),
            email=contact.get("email", ""), phone=contact.get("phone", ""),
            is_primary=True)
    return company


@transaction.atomic
def approve(*, company_id: int, actor, note: str = "") -> Company:
    company = Company.objects.select_for_update().filter(pk=company_id).first()
    if company is None:
        raise NotFoundError("No such company.")
    if company.approval_status == "approved":
        return company

    company.approval_status = "approved"
    company.status = "active"
    company.approval_note = note
    company.approved_by_user_id = actor.user_id
    company.approved_at = timezone.now()
    company.save(update_fields=["approval_status", "status", "approval_note",
                                "approved_by_user_id", "approved_at",
                                "updated_at"])

    primary = company.contacts.filter(is_primary=True).first()
    if primary:
        notifications.enqueue(
            topic="company.approved", dedupe_key=f"company.approved:{company.pk}",
            recipient_email=primary.email,
            subject=f"{company.name} is approved for campus recruitment",
            body="Your registration has been approved.",
            payload={"company_id": company.pk})
    return company


@transaction.atomic
def reject(*, company_id: int, actor, note: str) -> Company:
    if not (note or "").strip():
        raise ConflictError("A reason is required to reject a registration.",
                            code="reason_required")
    company = Company.objects.select_for_update().filter(pk=company_id).first()
    if company is None:
        raise NotFoundError("No such company.")

    company.approval_status = "rejected"
    company.approval_note = note
    company.save(update_fields=["approval_status", "approval_note", "updated_at"])
    _cut_off_sessions(company)
    return company


@transaction.atomic
def blacklist(*, company_id: int, actor, note: str) -> Company:
    """Stops a previously-approved company mid-season."""
    company = Company.objects.select_for_update().filter(pk=company_id).first()
    if company is None:
        raise NotFoundError("No such company.")
    company.status = "blacklisted"
    company.approval_note = note
    company.save(update_fields=["status", "approval_note", "updated_at"])
    _cut_off_sessions(company)
    return company


def _cut_off_sessions(company: Company) -> int:
    """Withdrawing authorization must take effect now."""
    return (RecruiterSession.objects
            .filter(account__company=company, revoked_at__isnull=True)
            .update(revoked_at=timezone.now()))
