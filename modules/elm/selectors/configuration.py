from modules.elm.models import CalendarVersion, LeavePolicy


def policies():
    return LeavePolicy.objects.all().order_by("-effective_from", "-version")


def policy_by_id(policy_id):
    return LeavePolicy.objects.filter(pk=policy_id).first()


def calendars():
    return CalendarVersion.objects.all().order_by("-effective_from", "-version")


def calendar_by_id(calendar_id):
    return CalendarVersion.objects.filter(pk=calendar_id).first()
