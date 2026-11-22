from django.db.models import Q, QuerySet

from modules.hr.models import Appraisal


def visible_appraisals(principal) -> QuerySet[Appraisal]:
    appraisals = Appraisal.objects.all()
    if principal.has_permission("hr.appraisal.assign"):
        return appraisals

    scope = Q()
    if principal.has_permission("hr.appraisal.view_self"):
        scope |= Q(employee_user_id=principal.user_id)
    if principal.has_permission("hr.appraisal.review"):
        scope |= Q(current_reviewer_user_id=principal.user_id)
    return appraisals.filter(scope) if scope else appraisals.none()
