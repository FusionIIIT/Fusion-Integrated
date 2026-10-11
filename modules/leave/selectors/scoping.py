"""Queryset scoping for Employee Leave Management.

Enforces visibility and multi-tenant department isolation.
Ownership is enforced by queryset narrowing in selectors — a foreign id yields 404, never 403.
"""
from django.db.models import Q, QuerySet

from fusion_auth.principal import Principal
from modules.directory.contracts import get_users
from modules.leave.domain.constants import RequestStatus
from modules.leave.models.requests import LeaveRequest


def get_user_department(user_id: int) -> str:
    """Retrieves user department from directory projection contract."""
    users = get_users([user_id])
    user_dto = users.get(user_id)
    return user_dto.department if user_dto else ""


def visible_requests_for_principal(principal: Principal) -> QuerySet[LeaveRequest]:
    """Returns the queryset of leave requests this principal is permitted to see."""
    # 1. Own requests (all employees)
    q = Q(user_id=principal.user_id)

    # 2. Substitute requests assigned to me
    if principal.has_permission("leave.substitute.respond"):
        q |= Q(substitute_user_id=principal.user_id)

    # 3. Unit Head queue (scoped by department)
    if principal.has_permission("leave.request.review"):
        dept = get_user_department(principal.user_id)
        if dept:
            q |= Q(department=dept, status__in=[
                RequestStatus.AWAITING_UNIT_HEAD_REVIEW,
                RequestStatus.CANCELLATION_PENDING_UNIT_HEAD,
                RequestStatus.EXT_AWAITING_UNIT_HEAD,
            ])

    # 4. Establishment queue
    if principal.has_permission("leave.request.route"):
        q |= Q(status__in=[
            RequestStatus.AWAITING_ESTABLISHMENT_ROUTING,
            RequestStatus.CANCELLATION_PENDING_ESTABLISHMENT,
            RequestStatus.EXT_PENDING_ESTABLISHMENT,
        ])

    # 5. Sanctioning Authority queue
    if principal.has_permission("leave.request.sanction"):
        q |= Q(status__in=[
            RequestStatus.AWAITING_FINAL_SANCTION_DECISION,
            RequestStatus.CANCELLATION_PENDING_FINAL_DECISION,
            RequestStatus.EXT_PENDING_FINAL_DECISION,
        ])
        # Director self-sanction
        if principal.active_role == "Director":
            q |= Q(status=RequestStatus.AWAITING_DIRECTOR_SELF_SANCTION)

    # 6. Resumption reviewer queue
    if principal.has_permission("leave.resumption.review"):
        q |= Q(status=RequestStatus.RESUMPTION_REVIEW_PENDING)

    # 7. Leave Administrator sees all
    if principal.has_permission("leave.policy.manage"):
        return LeaveRequest.objects.all()

    return LeaveRequest.objects.filter(q).distinct()
