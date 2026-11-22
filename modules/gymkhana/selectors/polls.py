from django.db.models import QuerySet
from django.utils import timezone

from modules.gymkhana.models.poll import PollVote, VotingPoll
from modules.gymkhana.selectors.scoping import scope_polls


def get_poll(poll_id: int) -> VotingPoll | None:
    return VotingPoll.objects.filter(id=poll_id).prefetch_related("choices").first()


def list_active_polls(user) -> QuerySet[VotingPoll]:
    now = timezone.now()
    return scope_polls(user).filter(expires_at__gt=now).order_by("expires_at")


def has_user_voted(poll: VotingPoll, student_id: int) -> bool:
    return PollVote.objects.filter(poll=poll, student_id=student_id).exists()
