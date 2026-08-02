"""All reads. Ownership filtering lives HERE — once per module, not once per
view — which is why a foreign id naturally yields 404 instead of 403."""
from __future__ import annotations

from modules.placement.models import Application, JobPosting


def visible_applications(principal):
    qs = Application.objects.select_related("posting", "posting__company")
    if principal.has_permission("placement_cell.application.view"):
        return qs
    return qs.filter(user_id=principal.user_id)


def visible_postings(principal):
    qs = JobPosting.objects.select_related("company")
    if principal.has_permission("placement_cell.job_posting.view"):
        return qs
    return qs.filter(status="published")
