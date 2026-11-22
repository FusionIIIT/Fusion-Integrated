from django.db.models import Q, QuerySet
from django.http import Http404

from modules.pms.models.application import PatentApplication


def visible_applications(user_id: int, roles: list[str]) -> QuerySet[PatentApplication]:
    """Return the narrowed queryset of PatentApplications visible to the acting user.
    
    Enforces §2.5: Scoping yields 404, never 403, so no existence information leaks.
    """
    qs = PatentApplication.objects.filter(is_active=True)

    # Coordinators, Directors, and Admins have institutional oversight (BR-PMS-005, BR-PMS-006)
    admin_roles = {"pms_coordinator", "Dean R&D", "Director", "pcc_admin", "admin", "superadmin"}
    if any(r in admin_roles for r in roles):
        return qs

    # Attorneys see applications where they are the assigned counsel
    if "pms_attorney" in roles or "attorney" in roles:
        return qs.filter(assigned_attorney_id=user_id)

    # Reviewers see applications assigned to them for evaluation
    if "pms_reviewer" in roles:
        return qs.filter(Q(assigned_director_id=user_id) | Q(reviews__reviewer_user_id=user_id)).distinct()

    # Plain applicants (student, faculty, staff) see only applications where they are primary inventor or co-inventor
    return qs.filter(
        Q(applicant_user_id=user_id) | Q(inventors__user_id=user_id)
    ).distinct()


def get_application_scoped(app_id: int, user_id: int, roles: list[str]) -> PatentApplication:
    """Fetch an application enforcing visibility scoping. Raises Http404 if out-of-scope."""
    qs = visible_applications(user_id, roles)
    try:
        return qs.get(pk=app_id)
    except PatentApplication.DoesNotExist as err:
        raise Http404(f"Patent Application #{app_id} does not exist or is not accessible.") from err
