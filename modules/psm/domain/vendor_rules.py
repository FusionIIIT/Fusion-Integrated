# Pure-Python vendor master validation and verification gate (BR-PSM-012, BR-PSM-025).
from __future__ import annotations

import re
from dataclasses import dataclass

from modules.psm.domain.errors import ConflictRuleError, ValidationRuleError

_GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
_IFSC_RE = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")


@dataclass(frozen=True)
class VendorMasterInput:
    name: str
    gstin: str
    bank_account_number: str
    bank_ifsc: str
    bank_name: str
    compliance_documents: tuple[str, ...]


def validate_vendor_master(data: VendorMasterInput) -> None:
    """Validate GST, bank, and compliance docs for verification (BR-PSM-012)."""
    errors: list[dict[str, str]] = []
    if not (data.name or "").strip():
        errors.append({"field": "name", "message": "Enter the vendor legal name."})
    gstin = (data.gstin or "").strip().upper()
    if not _GSTIN_RE.match(gstin):
        errors.append({"field": "gstin", "message": "Enter a valid 15-character GSTIN."})
    acct = (data.bank_account_number or "").strip()
    if len(acct) < 6 or not acct.isalnum():
        errors.append(
            {"field": "bank_account_number", "message": "Enter a valid bank account number."}
        )
    ifsc = (data.bank_ifsc or "").strip().upper()
    if not _IFSC_RE.match(ifsc):
        errors.append(
            {"field": "bank_ifsc", "message": "Enter a valid 11-character bank IFSC code."}
        )
    if not (data.bank_name or "").strip():
        errors.append({"field": "bank_name", "message": "Enter the vendor bank name."})
    if not [d for d in data.compliance_documents if (d or "").strip()]:
        errors.append(
            {
                "field": "compliance_documents",
                "message": "Attach at least one compliance document reference.",
            }
        )
    if errors:
        fields = ", ".join(e["field"] for e in errors)
        raise ValidationRuleError(
            f"Vendor verification failed; fix these fields first: {fields}.",
            code="vendor_master_invalid",
            details=errors,
        )


def ensure_vendor_verified(
    *, vendor_name: str, is_verified: bool, is_active: bool, action: str
) -> None:
    """Block PO issuance and payment for unverified or inactive vendors (BR-PSM-012)."""
    if not is_active:
        raise ConflictRuleError(
            f"Vendor '{vendor_name}' is inactive and cannot be used to {action}.",
            code="vendor_inactive",
        )
    if not is_verified:
        raise ConflictRuleError(
            f"Vendor '{vendor_name}' is unverified; verify vendor before trying to {action}.",
            code="vendor_unverified",
        )
