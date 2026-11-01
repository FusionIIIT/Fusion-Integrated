"""Clubs (UC-GYM-001, 011) and membership (UC-GYM-004, 005)."""
from django.db.models import Q

from core.api.exceptions import DomainError, NotFoundError
from modules.directory import contracts as directory
from modules.gymkhana import domain
from modules.gymkhana.models import Club, Membership


def _rule(check, *args):
    """Run a domain check; a broken rule becomes a 422."""
    try:
        check(*args)
    except domain.RuleViolation as e:
        raise DomainError(str(e)) from e


def _led_by(user_id):
    return Q(coordinator_user_id=user_id) | Q(co_coordinator_user_id=user_id)


def visible_clubs(principal):
    """Student Admin sees every club; others see confirmed ones and any they lead."""
    if principal.has_permission("gymkhana.club.approve"):
        return Club.objects.all()
    return Club.objects.filter(Q(status=domain.CONFIRMED) | _led_by(principal.user_id))


def visible_memberships(principal):
    """Your own applications, plus applications to clubs you lead."""
    led = Club.objects.filter(_led_by(principal.user_id)).values("id")
    return Membership.objects.filter(Q(user_id=principal.user_id) | Q(club_id__in=led))


def create_club(principal, data):
    ids = [data["coordinator_user_id"], data["co_coordinator_user_id"],
           data["faculty_councillor_user_id"]]
    kinds = {uid: u.kind for uid, u in directory.get_users(ids).items()}
    _rule(domain.check_category, data["category"])
    _rule(domain.check_leaders, *ids, kinds)
    return Club.objects.create(created_by_user_id=principal.user_id, **data)


def approve_club(club_id):
    club = Club.objects.filter(pk=club_id).first()
    if club is None:
        raise NotFoundError("Club not found.")
    _rule(domain.check_open, club.status)
    club.status = domain.CONFIRMED
    club.save()
    return club


def apply(principal, club_id, description):
    club = visible_clubs(principal).filter(pk=club_id).first()
    if club is None:
        raise NotFoundError("Club not found.")
    applied = Membership.objects.filter(club=club, user_id=principal.user_id).exists()
    _rule(domain.check_can_apply, club.status, applied)
    return Membership.objects.create(club=club, user_id=principal.user_id,
                                     description=description)


def approve_membership(principal, membership_id, remarks):
    m = Membership.objects.filter(pk=membership_id).first()
    if m is None:
        raise NotFoundError("Application not found.")
    _rule(domain.check_club_head, principal.user_id, m.club.coordinator_user_id,
          m.club.co_coordinator_user_id)
    _rule(domain.check_open, m.status)
    m.status = domain.CONFIRMED
    m.remarks = remarks
    m.save()
    return m
