from __future__ import annotations

from collections.abc import Sequence

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import F, Q
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.directory import contracts as directory
from modules.gymkhana.models import (
    BookingLock,
    Club,
    ClubEvent,
    ClubSession,
    MembershipApplication,
    NotificationOutbox,
    PollChoice,
    PollTargetGroup,
    PollVote,
    VotingPoll,
)


def validate_people(
    user_ids: Sequence[int],
    kind: str,
) -> dict[int, directory.UserDTO]:
    records = directory.get_users(user_ids)
    invalid = [
        int(user_id)
        for user_id in set(user_ids)
        if user_id not in records
        or records[user_id].kind != kind
        or not records[user_id].is_active
    ]
    if invalid:
        raise ConflictError(
            f"Every assigned person must be an active {kind}.",
            code=f"invalid_{kind}_assignment",
        )
    return records


def validate_leaders(coordinator_user_id: int, co_coordinator_user_id: int) -> None:
    validate_people((coordinator_user_id, co_coordinator_user_id), "student")


def require_club_head(club: Club, user_id: int) -> None:
    if user_id not in (club.coordinator_user_id, club.co_coordinator_user_id):
        raise PermissionDeniedError("Only this club's current Club Head may perform this action.")


def confirmed_club(club_id: int) -> Club:
    club = Club.objects.filter(pk=club_id, status=Club.Status.CONFIRMED).first()
    if club is None:
        raise NotFoundError("No confirmed club was found.")
    return club


def _configured_venue(venue: str) -> None:
    if venue not in settings.GYMKHANA_VENUES:
        raise ConflictError("Select a configured Gymkhana venue.", code="invalid_venue")


def _check_booking(*, venue: str, date, start_time, end_time) -> None:
    _configured_venue(venue)
    if start_time >= end_time:
        raise ConflictError("The booking start time must precede its end time.",
                            code="invalid_time_range")
    BookingLock.objects.get_or_create(venue=venue, date=date)
    BookingLock.objects.select_for_update().get(venue=venue, date=date)
    overlaps = Q(start_time__lt=end_time, end_time__gt=start_time)
    if ClubSession.objects.filter(venue=venue, date=date).filter(overlaps).exists():
        raise ConflictError("The venue is already booked for an overlapping session or event.",
                            code="venue_conflict")
    if ClubEvent.objects.filter(venue=venue, date=date).filter(overlaps).exists():
        raise ConflictError("The venue is already booked for an overlapping session or event.",
                            code="venue_conflict")


def _enqueue_recipients(*, topic: str, dedupe_prefix: str, subject: str,
                        body: str, user_ids: Sequence[int]) -> None:
    rows = {
        (int(uid), f"{dedupe_prefix}:{uid}")
        for uid in user_ids
        if uid is not None
    }
    if rows:
        NotificationOutbox.objects.bulk_create(
            [
                NotificationOutbox(
                    topic=topic,
                    dedupe_key=dedupe_key,
                    recipient_user_id=uid,
                    subject=subject,
                    body=body,
                )
                for uid, dedupe_key in rows
            ],
            ignore_conflicts=True,
        )


def _club_student_ids(club: Club) -> list[int]:
    return list(
        MembershipApplication.objects.filter(
            club=club, status=MembershipApplication.Status.CONFIRMED,
        ).values_list("student_user_id", flat=True)
    )


@transaction.atomic
def create_club(*, data: dict) -> Club:
    validate_leaders(data["coordinator_user_id"], data["co_coordinator_user_id"])
    validate_people((data["faculty_councillor_user_id"],), "faculty")
    try:
        with transaction.atomic():
            return Club.objects.create(**data, status=Club.Status.OPEN)
    except IntegrityError as exc:
        raise ConflictError(
            "A club with this name already exists.",
            code="club_name_exists",
        ) from exc


@transaction.atomic
def approve_club(*, club_id: int) -> Club:
    club = Club.objects.select_for_update().filter(pk=club_id).first()
    if club is None:
        raise NotFoundError("No such club.")
    if club.status != Club.Status.OPEN:
        raise ConflictError("Only an open club can be confirmed.", code="club_not_open")
    club.status = Club.Status.CONFIRMED
    club.save(update_fields=["status", "updated_at"])
    return club


@transaction.atomic
def change_leadership(*, club: Club, coordinator_user_id: int,
                      co_coordinator_user_id: int) -> Club:
    validate_leaders(coordinator_user_id, co_coordinator_user_id)
    club = Club.objects.select_for_update().get(pk=club.pk)
    club.coordinator_user_id = coordinator_user_id
    club.co_coordinator_user_id = co_coordinator_user_id
    club.save(update_fields=[
        "coordinator_user_id", "co_coordinator_user_id", "updated_at",
    ])
    return club


@transaction.atomic
def book_session(*, club: Club, user_id: int, data: dict) -> ClubSession:
    _check_booking(**{key: data[key] for key in ("venue", "date", "start_time", "end_time")})
    row = ClubSession.objects.create(club=club, created_by_user_id=user_id, **data)
    _enqueue_recipients(
        topic="session.booked",
        dedupe_prefix=f"session:{row.pk}",
        subject=f"New {club.name} session",
        body=f"{club.name} has booked a session on {row.date} at {row.venue}.",
        user_ids=_club_student_ids(club),
    )
    return row


@transaction.atomic
def book_event(*, club: Club, user_id: int, data: dict) -> ClubEvent:
    validate_people((data["faculty_user_id"],), "faculty")
    _check_booking(**{key: data[key] for key in ("venue", "date", "start_time", "end_time")})
    row = ClubEvent.objects.create(club=club, created_by_user_id=user_id, **data)
    _enqueue_recipients(
        topic="event.booked",
        dedupe_prefix=f"event:{row.pk}",
        subject=f"New {club.name} event: {row.name}",
        body=f"{row.name} is scheduled for {row.date} at {row.venue}.",
        user_ids=_club_student_ids(club),
    )
    return row


@transaction.atomic
def apply_for_membership(*, club: Club, student_user_id: int, description: str):
    if club.status != Club.Status.CONFIRMED:
        raise ConflictError("Membership applications require a confirmed club.",
                            code="club_not_confirmed")
    try:
        with transaction.atomic():
            return MembershipApplication.objects.create(
                club=club, student_user_id=student_user_id, description=description,
            )
    except IntegrityError as exc:
        raise ConflictError("You already applied to this club.",
                            code="duplicate_membership") from exc


@transaction.atomic
def approve_membership(*, application_id: int, club: Club, actor_user_id: int,
                       remarks: str = "") -> MembershipApplication:
    application = (
        MembershipApplication.objects.select_for_update()
        .filter(pk=application_id, club=club).first()
    )
    if application is None:
        raise NotFoundError("No such membership application.")
    if application.status != MembershipApplication.Status.OPEN:
        raise ConflictError("Only open applications can be approved.",
                            code="membership_not_open")
    application.status = MembershipApplication.Status.CONFIRMED
    application.remarks = remarks
    application.approved_by_user_id = actor_user_id
    application.save(update_fields=[
        "status", "remarks", "approved_by_user_id", "updated_at",
    ])
    return application


@transaction.atomic
def create_poll(*, club: Club, user_id: int, data: dict) -> VotingPoll:
    targets = data.pop("target_groups")
    choices = data.pop("choices")
    audiences = directory.student_ids_in_groups(targets)
    if not audiences:
        raise ConflictError("The selected groups contain no active students.",
                            code="empty_poll_audience")
    poll = VotingPoll.objects.create(club=club, created_by_user_id=user_id, **data)
    PollChoice.objects.bulk_create([PollChoice(poll=poll, text=text) for text in choices])
    PollTargetGroup.objects.bulk_create([
        PollTargetGroup(poll=poll, **target) for target in targets
    ])
    _enqueue_recipients(
        topic="poll.created",
        dedupe_prefix=f"poll:{poll.pk}",
        subject=f"New poll: {poll.title}",
        body=f"{club.name} has opened a poll: {poll.title}.",
        user_ids=audiences,
    )
    return poll


def poll_is_eligible(poll: VotingPoll, student_user_id: int) -> bool:
    person = directory.get_users((student_user_id,)).get(student_user_id)
    if person is None or person.kind != "student" or not person.is_active:
        return False
    return poll.target_groups.filter(
        batch_year=person.batch_year,
    ).filter(Q(discipline=person.discipline) | Q(discipline="*")).exists()


@transaction.atomic
def cast_vote(*, poll_id: int, choice_id: int, student_user_id: int) -> PollVote:
    poll = VotingPoll.objects.select_for_update().filter(pk=poll_id).first()
    if poll is None:
        raise NotFoundError("No such poll.")
    if not poll.is_active or poll.expires_at <= timezone.now():
        raise ConflictError("This poll is no longer active.", code="poll_closed")
    if not poll_is_eligible(poll, student_user_id):
        raise ConflictError("You are not in this poll's target audience.",
                            code="poll_not_targeted")
    choice = PollChoice.objects.filter(pk=choice_id, poll=poll).first()
    if choice is None:
        raise NotFoundError("No such choice in this poll.")
    try:
        with transaction.atomic():
            return PollVote.objects.create(
                poll=poll, choice=choice, student_user_id=student_user_id,
            )
    except IntegrityError as exc:
        raise ConflictError("You have already voted in this poll.",
                            code="already_voted") from exc


def eligible_polls(student_user_id: int):
    now = timezone.now()
    person = directory.get_users((student_user_id,)).get(student_user_id)
    if person is None or person.kind != "student" or not person.is_active:
        return []
    polls = VotingPoll.objects.filter(is_active=True, expires_at__gt=now).prefetch_related(
        "target_groups", "choices",
    ).order_by("expires_at")
    return [
        poll for poll in polls
        if poll.target_groups.filter(batch_year=person.batch_year)
        .filter(Q(discipline=person.discipline) | Q(discipline="*")).exists()
    ]


def faculty_report_club_ids(faculty_user_id: int):
    return Club.objects.filter(
        faculty_councillor_user_id=faculty_user_id,
    ).values_list("id", flat=True)


def student_audience_ids(targets: Sequence[dict]) -> list[int]:
    return directory.student_ids_in_groups(targets)
