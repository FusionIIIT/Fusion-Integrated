"""Role-scoped read queries for MMS."""

from modules.mms.models import (
    Announcement,
    Enrollment,
    Feedback,
    MenuWeek,
    MonthlyBill,
    RebateRequest,
    RegistrationWindow,
    SpecialFoodRequest,
    StudentRequest,
    VacationSurvey,
)


def pending_requests():
    return StudentRequest.objects.filter(status="pending").order_by("created_at")


def oversight_requests():
    registrations = StudentRequest.objects.prefetch_related("history").order_by(
        "-created_at")
    rebates = RebateRequest.objects.all()
    special = SpecialFoodRequest.objects.all()
    return {
        "registration": registrations,
        "rebates": rebates,
        "special_food": special,
    }


def student_requests(user_id: int):
    return StudentRequest.objects.filter(user_id=user_id).prefetch_related(
        "history").order_by("-created_at")


def student_bills(user_id: int):
    return MonthlyBill.objects.filter(user_id=user_id, status="published")


def operational_dashboard():
    requests = oversight_requests()
    return {
        "requests": requests["registration"],
        "registered_students": Enrollment.objects.filter(deregistered_at__isnull=True),
        "registration_windows": RegistrationWindow.objects.order_by("-opens_at"),
        "rebates": requests["rebates"],
        "special_food": requests["special_food"],
        "surveys": VacationSurvey.objects.all(),
        "feedback": Feedback.objects.all(),
        "announcements": Announcement.objects.all(),
        "menus": MenuWeek.objects.all(),
    }
