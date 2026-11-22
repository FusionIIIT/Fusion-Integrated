from datetime import date
from decimal import Decimal
from django.db import transaction

from modules.pms.domain.business_rules import calculate_annuity_grace_period
from modules.pms.models.maintenance import MaintenanceRenewal, RenewalDecision
from modules.pms.selectors.scoping import get_application_scoped


@transaction.atomic
def record_maintenance_decision(
    app_id: int,
    user_id: int,
    renewal_year: int,
    due_date: date,
    annuity_fee: Decimal,
    decision: str,
    roles: list[str],
    payment_reference: str = "",
) -> MaintenanceRenewal:
    """Record institutional maintenance renewal decision (BW-PMS-14, BW-PMS-15)."""
    app = get_application_scoped(app_id, user_id, roles)

    grace_deadline = calculate_annuity_grace_period(due_date)

    renewal, _ = MaintenanceRenewal.objects.update_or_create(
        application=app,
        renewal_year=renewal_year,
        defaults={
            "due_date": due_date,
            "grace_period_deadline": grace_deadline,
            "annuity_fee": annuity_fee,
            "decision": decision,
            "decided_by_user_id": user_id,
            "payment_reference": payment_reference,
        },
    )

    return renewal
