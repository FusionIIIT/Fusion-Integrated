from django.db.models import QuerySet

from modules.oap.models.leave import StudentLeaveApplication


def get_student_leaves(user_id: int) -> QuerySet[StudentLeaveApplication]:
    return StudentLeaveApplication.objects.filter(user_id=user_id).prefetch_related("attachments")


def get_department_leaves(department: str) -> QuerySet[StudentLeaveApplication]:
    return StudentLeaveApplication.objects.filter(department=department).prefetch_related("attachments")


def get_leave_by_id(leave_id: int) -> StudentLeaveApplication | None:
    return StudentLeaveApplication.objects.filter(id=leave_id).prefetch_related("attachments").first()
