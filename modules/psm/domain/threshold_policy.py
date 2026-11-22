"""Financial threshold policies for PSM procurement routing.

Implements BR-PSM-008 and BR-PSM-010.
"""
from decimal import Decimal


class ProcurementMethod:
    DIRECT = "DIRECT"
    QUOTATION = "QUOTATION"
    TENDER = "TENDER"
    GEM = "GEM"


DIRECT_PROCUREMENT_LIMIT = Decimal("25000.00")
DIRECTOR_SANCTION_THRESHOLD = Decimal("250000.00")


def determine_procurement_method(total_amount: Decimal) -> str:
    """Returns the required procurement method under BR-PSM-008."""
    if total_amount <= DIRECT_PROCUREMENT_LIMIT:
        return ProcurementMethod.DIRECT
    if total_amount <= DIRECTOR_SANCTION_THRESHOLD:
        return ProcurementMethod.QUOTATION
    return ProcurementMethod.TENDER


def requires_director_approval(estimated_total: Decimal) -> bool:
    """High-value procurement gate requiring Director / Registrar approval under BR-PSM-010."""
    return estimated_total >= DIRECTOR_SANCTION_THRESHOLD
