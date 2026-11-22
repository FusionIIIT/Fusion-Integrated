from django.db import transaction
from django.utils import timezone

from modules.psm.domain.validators import ValidationError
from modules.psm.models.vendor import Vendor, VendorStatus


def generate_vendor_code() -> str:
    timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
    return f"VND-{timestamp}"


@transaction.atomic
def register_vendor(
    name: str,
    gstin: str,
    email: str,
    phone: str,
    address: str = "",
    bank_account_number: str = "",
    bank_ifsc: str = "",
) -> Vendor:
    """Registers a new vendor in PENDING_VERIFICATION status."""
    if not name or not name.strip():
        raise ValidationError("Vendor name cannot be empty.")
    if not gstin or len(gstin.strip()) != 15:
        raise ValidationError("Valid 15-character GSTIN is required.")

    if Vendor.objects.filter(gstin=gstin.strip()).exists():
        raise ValidationError(f"Vendor with GSTIN {gstin} is already registered.")

    return Vendor.objects.create(
        vendor_code=generate_vendor_code(),
        name=name.strip(),
        gstin=gstin.strip().upper(),
        email=email.strip(),
        phone=phone.strip(),
        address=address.strip(),
        bank_account_number=bank_account_number.strip(),
        bank_ifsc=bank_ifsc.strip().upper(),
        status=VendorStatus.PENDING_VERIFICATION,
    )


@transaction.atomic
def verify_vendor(vendor_id: int, user_id: int) -> Vendor:
    """Enforces BR-PSM-012: Vets and verifies vendor master record."""
    vendor = Vendor.objects.select_for_update().get(pk=vendor_id)
    vendor.status = VendorStatus.VERIFIED
    vendor.verified_by_user_id = user_id
    vendor.verified_at = timezone.now()
    vendor.save(update_fields=["status", "verified_by_user_id", "verified_at", "updated_at"])
    return vendor


@transaction.atomic
def blacklist_vendor(vendor_id: int, user_id: int, reason: str = "") -> Vendor:
    vendor = Vendor.objects.select_for_update().get(pk=vendor_id)
    vendor.status = VendorStatus.BLACKLISTED
    vendor.save(update_fields=["status", "updated_at"])
    return vendor
