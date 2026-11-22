from django.db.models import QuerySet

from modules.oap.models.bonafide import BonafideRequest, BonafideStatus
from modules.oap.models.branch_change import BranchChangeRequest
from modules.oap.models.leave import RequestStatus, StudentLeaveRequest
from modules.oap.models.nodues import NoDuesRequest


def get_student_leaves(student_id: str) -> QuerySet[StudentLeaveRequest]:
    return StudentLeaveRequest.objects.filter(student_id=student_id).order_by("-created_at")


def get_pending_leaves_for_approver() -> QuerySet[StudentLeaveRequest]:
    return StudentLeaveRequest.objects.filter(
        status__in=[RequestStatus.PENDING, RequestStatus.RECOMMENDED]
    ).order_by("created_at")


def get_student_bonafides(student_id: str) -> QuerySet[BonafideRequest]:
    return BonafideRequest.objects.filter(student_id=student_id).order_by("-created_at")


def get_pending_bonafides() -> QuerySet[BonafideRequest]:
    return BonafideRequest.objects.filter(status=BonafideStatus.PENDING).order_by("created_at")


def get_student_no_dues(student_id: str) -> QuerySet[NoDuesRequest]:
    return NoDuesRequest.objects.filter(student_id=student_id).prefetch_related("signoffs")


def get_all_branch_change_applications() -> QuerySet[BranchChangeRequest]:
    return BranchChangeRequest.objects.all().order_by("-current_cpi")
