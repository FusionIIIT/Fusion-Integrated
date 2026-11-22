"""
Vendor Read Selectors.
"""

from typing import Any, Optional
from django.db.models import QuerySet
from modules.psm.models import Vendor


def list_vendors(principal: Any = None, is_verified: Optional[bool] = None) -> QuerySet[Vendor]:
    """List vendors, optionally filtered by verification status."""
    qs = Vendor.objects.all().order_by("name")
    if is_verified is not None:
        qs = qs.filter(is_verified=bool(is_verified))
    return qs


def get_vendor_by_id(vendor_id: Any) -> Optional[Vendor]:
    """Retrieve vendor by primary key."""
    try:
        return Vendor.objects.filter(id=int(vendor_id)).first()
    except Exception:
        return None
