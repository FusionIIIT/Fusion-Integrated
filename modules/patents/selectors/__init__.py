"""Reads. Ownership filtering lives here, so a foreign id is a 404, not a 403."""

from django.db.models import Q

from modules.patents import models as m


def visible(principal):
    if principal.has_permission("patent_management.application.view_all"):
        return m.Application.objects.all()
    q = Q(pk__in=[])
    if principal.has_permission("patent_management.application.view_own"):
        q |= Q(applicant_user_id=principal.user_id)
    if principal.has_permission("patent_management.application.view_assigned"):
        q |= Q(director_user_id=principal.user_id) | Q(attorney_user_id=principal.user_id)
    return m.Application.objects.filter(q).distinct()
