from modules.gymkhana.models import MembershipApplication


def for_student(student_id: int):
    return MembershipApplication.objects.filter(
        student_id=student_id
    ).select_related("club").order_by("-created_at")


def for_club(club_id: int):
    return MembershipApplication.objects.filter(
        club_id=club_id
    ).select_related("club").order_by("-created_at")
