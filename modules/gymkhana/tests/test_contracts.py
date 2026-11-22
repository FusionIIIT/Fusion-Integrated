"""Tests for Gymkhana public cross-module contracts (Blueprint §3.6)."""
from __future__ import annotations

import pytest

from modules.gymkhana import contracts
from modules.gymkhana.models import Club, ClubMembership


@pytest.mark.django_db
def test_get_active_club_leaders_contract():
    c1 = Club.objects.create(
        name="Robotics Club",
        category="Technical",
        description="Build bots",
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=501,
        status="confirmed",
    )
    c2 = Club.objects.create(
        name="Football Club",
        category="Sports",
        description="Play football",
        coordinator_id=201,
        co_coordinator_id=202,
        faculty_councillor_id=502,
        status="confirmed",
    )

    # Plural getter call
    leaders = contracts.get_active_club_leaders([c1.id, c2.id, 999])
    assert leaders[c1.id] is not None
    assert leaders[c1.id].coordinator_id == 101
    assert leaders[c1.id].co_coordinator_id == 102
    assert leaders[c2.id] is not None
    assert leaders[c2.id].coordinator_id == 201
    assert leaders[c2.id].co_coordinator_id == 202
    assert 999 not in leaders

    # Empty sequence
    assert contracts.get_active_club_leaders([]) == {}


@pytest.mark.django_db
def test_get_student_memberships_contract():
    c1 = Club.objects.create(
        name="Music Club",
        category="Cultural",
        description="Music enthusiasts",
        coordinator_id=301,
        co_coordinator_id=302,
        faculty_councillor_id=503,
        status="confirmed",
    )
    c2 = Club.objects.create(
        name="Drama Club",
        category="Cultural",
        description="Theatre arts",
        coordinator_id=303,
        co_coordinator_id=304,
        faculty_councillor_id=504,
        status="confirmed",
    )

    ClubMembership.objects.create(club=c1, student_id=401, status="confirmed")
    ClubMembership.objects.create(club=c2, student_id=401, status="open")
    ClubMembership.objects.create(club=c1, student_id=402, status="confirmed")

    # Plural getter call
    memberships = contracts.get_student_memberships([401, 402, 999])

    assert len(memberships[401]) == 2
    dto1 = next(dto for dto in memberships[401] if dto.club_id == c1.id)
    assert dto1.club_id == c1.id
    assert dto1.club_name == "Music Club"
    assert dto1.status == "confirmed"

    dto2 = next(dto for dto in memberships[401] if dto.club_id == c2.id)
    assert dto2.club_id == c2.id
    assert dto2.club_name == "Drama Club"
    assert dto2.status == "open"

    assert len(memberships[402]) == 1
    assert memberships[402][0].club_id == c1.id
    assert memberships[999] == []

    # Empty sequence
    assert contracts.get_student_memberships([]) == {}
