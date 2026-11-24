# Vendor onboarding, maintenance, versioning, and verification (PSM-UC-019).
from __future__ import annotations

from django.db import IntegrityError, transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.psm.domain.vendor_rules import VendorMasterInput, validate_vendor_master
from modules.psm.models import Vendor, VendorVersion
from modules.psm.services.common import audit_record, next_number, translate_errors


def _snapshot(v: Vendor) -> dict:
    return {
        "code": v.code,
        "name": v.name,
        "gstin": v.gstin,
        "bank_account_number": v.bank_account_number,
        "bank_ifsc": v.bank_ifsc,
        "bank_name": v.bank_name,
        "compliance_documents": list(v.compliance_documents or []),
        "contact_email": v.contact_email,
        "is_verified": v.is_verified,
        "is_active": v.is_active,
    }


@transaction.atomic
def onboard_vendor(
    *,
    actor,
    name: str,
    gstin: str = "",
    bank_account_number: str = "",
    bank_ifsc: str = "",
    bank_name: str = "",
    compliance_documents: list[str] | None = None,
    contact_email: str = "",
    code: str | None = None,
) -> Vendor:
    """Create a new unverified vendor master record with version 1 history (PSM-UC-019)."""
    try:
        vendor = Vendor.objects.create(
            code=(code or next_number("VND")).strip().upper(),
            name=name.strip(),
            gstin=gstin.strip().upper(),
            bank_account_number=bank_account_number.strip(),
            bank_ifsc=bank_ifsc.strip().upper(),
            bank_name=bank_name.strip(),
            compliance_documents=list(compliance_documents or []),
            contact_email=contact_email.strip(),
            is_verified=False,
            version=1,
        )
    except IntegrityError as exc:
        raise ConflictError(
            "A vendor with that code already exists; choose a unique vendor code.",
            code="vendor_code_exists",
        ) from exc
    VendorVersion.objects.create(
        vendor=vendor,
        version=1,
        snapshot=_snapshot(vendor),
        changed_by_user_id=actor.user_id,
        change_reason="Initial onboarding",
    )
    audit_record(
        actor=actor,
        action="vendor.onboarded",
        target_type="vendor",
        target_id=vendor.pk,
        to_state="unverified",
    )
    return vendor


_MUTABLE_VENDOR_FIELDS = (
    "name",
    "gstin",
    "bank_account_number",
    "bank_ifsc",
    "bank_name",
    "compliance_documents",
    "contact_email",
    "is_active",
)
_SENSITIVE_VENDOR_FIELDS = frozenset(
    {"gstin", "bank_account_number", "bank_ifsc", "bank_name", "compliance_documents"}
)


def _apply_vendor_fields(vendor: Vendor, fields: dict) -> bool:
    """Apply normalized vendor edits and return True if sensitive compliance fields changed."""
    sensitive_changed = False
    for key in _MUTABLE_VENDOR_FIELDS:
        if key not in fields:
            continue
        val = fields[key]
        if key in ("gstin", "bank_ifsc") and isinstance(val, str):
            val = val.strip().upper()
        elif isinstance(val, str):
            val = val.strip()
        if getattr(vendor, key) != val:
            if key in _SENSITIVE_VENDOR_FIELDS:
                sensitive_changed = True
            setattr(vendor, key, val)
    return sensitive_changed


@transaction.atomic
def update_vendor(*, actor, vendor_id: int, change_reason: str = "", **fields) -> Vendor:
    """Update vendor master data and append a VendorVersion snapshot (BR-PSM-025)."""
    vendor = Vendor.objects.select_for_update().filter(pk=vendor_id).first()
    if vendor is None:
        raise NotFoundError("Vendor not found.")
    if _apply_vendor_fields(vendor, fields):
        vendor.is_verified = False
        vendor.verified_at = None
        vendor.verified_by_user_id = None
    vendor.version += 1
    vendor.save()
    VendorVersion.objects.create(
        vendor=vendor,
        version=vendor.version,
        snapshot=_snapshot(vendor),
        changed_by_user_id=actor.user_id,
        change_reason=change_reason.strip() or "Master data updated",
    )
    audit_record(
        actor=actor,
        action="vendor.updated",
        target_type="vendor",
        target_id=vendor.pk,
        to_state="verified" if vendor.is_verified else "unverified",
        details={"version": vendor.version},
    )
    return vendor


@transaction.atomic
def verify_vendor(*, actor, vendor_id: int) -> Vendor:
    """Validate GST, bank, and compliance documents and mark vendor verified (BR-PSM-012)."""
    vendor = Vendor.objects.select_for_update().filter(pk=vendor_id).first()
    if vendor is None:
        raise NotFoundError("Vendor not found.")
    with translate_errors():
        validate_vendor_master(
            VendorMasterInput(
                name=vendor.name,
                gstin=vendor.gstin,
                bank_account_number=vendor.bank_account_number,
                bank_ifsc=vendor.bank_ifsc,
                bank_name=vendor.bank_name,
                compliance_documents=tuple(vendor.compliance_documents or ()),
            )
        )
    vendor.is_verified = True
    vendor.verified_by_user_id = actor.user_id
    vendor.verified_at = timezone.now()
    vendor.version += 1
    vendor.save(
        update_fields=["is_verified", "verified_by_user_id", "verified_at", "version", "updated_at"]
    )
    VendorVersion.objects.create(
        vendor=vendor,
        version=vendor.version,
        snapshot=_snapshot(vendor),
        changed_by_user_id=actor.user_id,
        change_reason="Vendor master verified",
    )
    audit_record(
        actor=actor,
        action="vendor.verified",
        target_type="vendor",
        target_id=vendor.pk,
        from_state="unverified",
        to_state="verified",
    )
    return vendor
