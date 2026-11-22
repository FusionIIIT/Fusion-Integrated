from typing import Any
from django.db.models import QuerySet

from modules.pms.models.application import PatentApplication
from modules.pms.selectors.scoping import visible_applications


def list_applications(
    user_id: int,
    roles: list[str],
    status: str | None = None,
    filing_type: str | None = None,
    search: str | None = None,
) -> QuerySet[PatentApplication]:
    """List applications visible to the user with optional filters."""
    qs = visible_applications(user_id, roles)

    if status:
        qs = qs.filter(status=status)
    if filing_type:
        qs = qs.filter(filing_type=filing_type)
    if search:
        qs = qs.filter(title__icontains=search) | qs.filter(application_no__icontains=search)

    return qs.prefetch_related("inventors", "reviews", "documents").order_by("-created_at")


def get_application_details(app_id: int, user_id: int, roles: list[str]) -> PatentApplication:
    """Retrieve full application aggregate including relations."""
    from modules.pms.selectors.scoping import get_application_scoped

    app = get_application_scoped(app_id, user_id, roles)
    return app
