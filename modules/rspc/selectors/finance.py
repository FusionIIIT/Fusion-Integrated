"""Financial selectors for RSPC."""

from __future__ import annotations

from django.db.models import QuerySet

from modules.rspc.models import ProjectBudgetHead, ProjectFundTransaction
from modules.rspc.selectors.scoping import get_project_or_404


def get_project_budget_heads(request, project_id: int) -> QuerySet[ProjectBudgetHead]:
    project = get_project_or_404(request, project_id)
    return ProjectBudgetHead.objects.filter(project=project).order_by("head_type")


def get_project_ledger_transactions(request, project_id: int) -> QuerySet[ProjectFundTransaction]:
    project = get_project_or_404(request, project_id)
    return (
        ProjectFundTransaction.objects.filter(project=project)
        .select_related("budget_head")
        .order_by("-created_at")
    )
