from django.db.models import QuerySet

from modules.gymkhana.models.budget import ClubBudgetRequest
from modules.gymkhana.models.club import Club
from modules.gymkhana.selectors.scoping import scope_budgets


def list_budget_requests(user, club: Club) -> QuerySet[ClubBudgetRequest]:
    return scope_budgets(user, club).order_by("-created_at")
