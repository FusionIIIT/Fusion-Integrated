from django.db.models import QuerySet

from modules.gymkhana.models.club import Club
from modules.gymkhana.models.report import ClubEventReport
from modules.gymkhana.selectors.scoping import scope_reports


def list_event_reports(user, club: Club) -> QuerySet[ClubEventReport]:
    return scope_reports(user, club).order_by("-created_at")
