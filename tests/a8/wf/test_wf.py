"""Automated backend test suite for Gymkhana Workflow Requirements (WF).

Generated from a8_design/WF_DESIGN.json.
Rules applied:
- Implement exactly the supplied test cases (TC-WF-01 to TC-WF-15).
- Do not add, remove, merge or reinterpret test cases.
- Preserve each specified expected result.
- Do not modify production code.
- Use the Django isolated test database (@pytest.mark.django_db).
- Reuse existing Fusion test infrastructure where appropriate (APIClient, User model).
- Do not mock the behavior being tested.
- Do not use xfail to hide failures.
- Every test contains its test_id and source_id in its name and docstring.
- Tests that genuinely cannot be automated using available interfaces are skipped with
NOT_AUTOMATED: <reason>.
"""

import datetime
import itertools

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from applications.gymkhana.models import (
    Club,
    ClubMembership,
    GymkhanaWorkflowHistory,
    PollChoice,
    PollVote,
    VotingPoll,
)

User = get_user_model()

# ---------------------------------------------------------------------------
# Test Data Helpers
# ---------------------------------------------------------------------------

_counter = itertools.count(1)


def _unique_name(prefix: str) -> str:
    return f"{prefix}_{next(_counter)}"


def _make_user(username: str, is_staff: bool = False, is_superuser: bool = False):
    uname = _unique_name(username)
    return User.objects.create_user(
        username=uname,
        password="testpass123",  # noqa: S106
        is_staff=is_staff,
        is_superuser=is_superuser,
    )


def _make_club(
    coordinator, co_coordinator, faculty, status="confirmed", name=None, category="technical"
):
    club_name = name or _unique_name("TestClub")
    return Club.objects.create(
        name=club_name,
        description="A test club",
        category=category,
        coordinator=coordinator,
        co_coordinator=co_coordinator,
        faculty_councillor=faculty,
        status=status,
    )


# ---------------------------------------------------------------------------
# BW-GYM-01: Club Membership Lifecycle (TC-WF-01 to TC-WF-05)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestClubMembershipWorkflow:
    def test_tc_wf_01_membership_apply_success(self):
        """TC-WF-01 (source_id: BW-GYM-01 T1-apply-success):
        Verify Transition 1 success path in BW-GYM-01: No Membership Application -> Membership
        Application Open.
        Preconditions: Student has no application for confirmed club.
        Action: Student invokes UC-GYM-004 (Apply for Club Membership) with valid details.
        Expected result: Application transitions from 'No Membership Application' to 'Membership
        Application Open'.
        """
        coordinator = _make_user("coord_wf01")
        co_coordinator = _make_user("cocoord_wf01")
        faculty = _make_user("faculty_wf01")
        student = _make_user("student_wf01")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        # Precondition verification: No Membership Application
        assert not ClubMembership.objects.filter(club=club, student=student).exists()

        client = APIClient()
        client.force_authenticate(user=student)

        payload = {
            "club": club.pk,
            "achievements": "Interested in robotics competitions and projects",
        }
        resp = client.post("/api/gymkhana/memberships/", payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert resp.data["status"] == "open"
        assert resp.data["achievements"] == "Interested in robotics competitions and projects"

        # Verify application transitioned to 'Membership Application Open'
        membership = ClubMembership.objects.get(club=club, student=student)
        assert membership.status == "open"

    def test_tc_wf_02_membership_apply_rejected(self):
        """TC-WF-02 (source_id: BW-GYM-01 T1-apply-rejected):
        Verify Transition 1 guard failure path in BW-GYM-01: target club is unconfirmed or duplicate
        application exists.
        Preconditions: Target club is in status 'open' (unconfirmed) OR student already
        has application
        for club.
        Action: Student invokes UC-GYM-004.
        Expected result: Guard fails; application is rejected and system remains in 'No Membership
        Application' state for that club.
        """
        coordinator = _make_user("coord_wf02")
        co_coordinator = _make_user("cocoord_wf02")
        faculty = _make_user("faculty_wf02")
        student_1 = _make_user("student_1_wf02")
        student_2 = _make_user("student_2_wf02")

        # Guard failure branch 1: Target club is in status 'open' (unconfirmed)
        unconfirmed_club = _make_club(
            coordinator,
            co_coordinator,
            faculty,
            status="open",
            name=_unique_name("UnconfirmedClub"),
        )
        assert not ClubMembership.objects.filter(club=unconfirmed_club, student=student_1).exists()

        client = APIClient()
        client.force_authenticate(user=student_1)

        payload_unconfirmed = {
            "club": unconfirmed_club.pk,
            "achievements": "Applying to unconfirmed club",
        }
        resp_unconfirmed = client.post(
            "/api/gymkhana/memberships/", payload_unconfirmed, format="json"
        )
        assert resp_unconfirmed.status_code == status.HTTP_400_BAD_REQUEST, resp_unconfirmed.data
        # Guard fails; system remains in 'No Membership Application' state for that club
        assert not ClubMembership.objects.filter(club=unconfirmed_club, student=student_1).exists()

        # Guard failure branch 2: Student already has application for club
        confirmed_club = _make_club(
            coordinator,
            co_coordinator,
            faculty,
            status="confirmed",
            name=_unique_name("ConfirmedClub"),
        )
        ClubMembership.objects.create(club=confirmed_club, student=student_2, status="open")
        assert ClubMembership.objects.filter(club=confirmed_club, student=student_2).count() == 1

        client.force_authenticate(user=student_2)
        payload_duplicate = {
            "club": confirmed_club.pk,
            "achievements": "Duplicate application attempt",
        }
        resp_duplicate = client.post("/api/gymkhana/memberships/", payload_duplicate, format="json")
        assert resp_duplicate.status_code == status.HTTP_400_BAD_REQUEST, resp_duplicate.data
        # Duplicate rejected; remains single application
        assert ClubMembership.objects.filter(club=confirmed_club, student=student_2).count() == 1

    def test_tc_wf_03_membership_approve_success(self):
        """TC-WF-03 (source_id: BW-GYM-01 T2-approve-success):
        Verify Transition 2 success path in BW-GYM-01: Membership Application Open -> Membership
        Confirmed.
        Preconditions: Application in 'Membership Application Open'; Club Head authenticated.
        Action: Club Head invokes UC-GYM-005 (Approve Club Membership) on open application.
        Expected result: Application transitions from 'Membership Application Open' to 'Membership
        Confirmed'.
        """
        coordinator = _make_user("coord_wf03")
        co_coordinator = _make_user("cocoord_wf03")
        faculty = _make_user("faculty_wf03")
        student = _make_user("student_wf03")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        membership = ClubMembership.objects.create(
            club=club, student=student, achievements="Active volunteer", status="open"
        )
        assert membership.status == "open"

        client = APIClient()
        client.force_authenticate(user=coordinator)

        payload = {"action": "approve", "remarks": "Approved by Club Coordinator"}
        resp = client.post(
            f"/api/gymkhana/memberships/{membership.pk}/approve/", payload, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert resp.data["status"] == "confirmed"
        assert resp.data["remarks"] == "Approved by Club Coordinator"

        # Verify application transitioned to 'Membership Confirmed'
        membership.refresh_from_db()
        assert membership.status == "confirmed"
        assert membership.remarks == "Approved by Club Coordinator"

        # Verify audit history logged transition
        history = GymkhanaWorkflowHistory.objects.filter(
            entity_type="membership", entity_id=membership.pk
        ).first()
        assert history is not None
        assert history.from_state == "open"
        assert history.to_state == "confirmed"
        assert history.action_taken == "approve"
        assert history.actor == coordinator

    def test_tc_wf_04_membership_approve_rejected(self):
        """TC-WF-04 (source_id: BW-GYM-01 T2-approve-rejected):
        Verify Transition 2 guard failure path in BW-GYM-01: actor is not applicable Club Head or
        application is not open.
        Preconditions: Requester is not coordinator/co-coordinator for club OR
        application is already
        confirmed.
        Action: Requester invokes UC-GYM-005.
        Expected result: Guard fails; approval rejected and application remains in its prior state
        ('Membership Application Open').
        """
        coordinator = _make_user("coord_wf04")
        co_coordinator = _make_user("cocoord_wf04")
        faculty = _make_user("faculty_wf04")
        student = _make_user("student_wf04")
        unauthorized_actor = _make_user("unauthorized_actor_wf04")

        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")
        membership_open = ClubMembership.objects.create(club=club, student=student, status="open")

        client = APIClient()

        # Guard failure branch 1: Requester is not coordinator/co-coordinator for club
        client.force_authenticate(user=unauthorized_actor)
        payload = {"action": "approve", "remarks": "Unauthorized approval"}
        resp_unauth = client.post(
            f"/api/gymkhana/memberships/{membership_open.pk}/approve/", payload, format="json"
        )
        assert resp_unauth.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND), (
            resp_unauth.data
        )
        membership_open.refresh_from_db()
        # Application remains in its prior state ('Membership Application Open')
        assert membership_open.status == "open"

        # Guard failure branch 2: Application is already confirmed
        membership_confirmed = ClubMembership.objects.create(
            club=club, student=_make_user("student_wf04_b"), status="confirmed"
        )
        client.force_authenticate(user=coordinator)
        resp_already_confirmed = client.post(
            f"/api/gymkhana/memberships/{membership_confirmed.pk}/approve/", payload, format="json"
        )
        assert resp_already_confirmed.status_code == status.HTTP_400_BAD_REQUEST, (
            resp_already_confirmed.data
        )
        membership_confirmed.refresh_from_db()
        # Application remains in its prior state ('confirmed')
        assert membership_confirmed.status == "confirmed"

    def test_tc_wf_05_membership_full_progression_path(self):
        """TC-WF-05 (source_id: BW-GYM-01 full-progression-path):
        Verify complete end-to-end success path for BW-GYM-01 from no application to confirmed
        membership.
        Preconditions: Confirmed club exists; student has no prior application; applicable Club Head
        available.
        Action: Student executes UC-GYM-004 (Apply) -> Club Head executes UC-GYM-005 (Approve).
        Expected result: Lifecycle moves: No Application -> Application Open ->
        Membership Confirmed.
        """
        coordinator = _make_user("coord_wf05")
        co_coordinator = _make_user("cocoord_wf05")
        faculty = _make_user("faculty_wf05")
        student = _make_user("student_wf05")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        # Stage 0: Precondition - No Application
        assert not ClubMembership.objects.filter(club=club, student=student).exists()

        # Stage 1: Student executes UC-GYM-004 (Apply)
        student_client = APIClient()
        student_client.force_authenticate(user=student)

        apply_payload = {
            "club": club.pk,
            "achievements": "Extensive experience in club events",
        }
        apply_resp = student_client.post("/api/gymkhana/memberships/", apply_payload, format="json")
        assert apply_resp.status_code == status.HTTP_201_CREATED, apply_resp.data
        membership_id = apply_resp.data["id"]

        # Lifecycle state: Application Open
        membership = ClubMembership.objects.get(pk=membership_id)
        assert membership.status == "open"
        assert membership.student == student
        assert membership.club == club

        # Stage 2: Club Head executes UC-GYM-005 (Approve)
        head_client = APIClient()
        head_client.force_authenticate(user=coordinator)

        approve_payload = {"action": "approve", "remarks": "Welcome to the club!"}
        approve_resp = head_client.post(
            f"/api/gymkhana/memberships/{membership.pk}/approve/", approve_payload, format="json"
        )
        assert approve_resp.status_code == status.HTTP_200_OK, approve_resp.data

        # Lifecycle state: Membership Confirmed
        membership.refresh_from_db()
        assert membership.status == "confirmed"
        assert membership.remarks == "Welcome to the club!"

        # Audit check: Lifecycle progression recorded in workflow history
        hist = GymkhanaWorkflowHistory.objects.filter(
            entity_type="membership", entity_id=membership.pk
        ).first()
        assert hist is not None
        assert hist.from_state == "open"
        assert hist.to_state == "confirmed"
        assert hist.actor == coordinator


# ---------------------------------------------------------------------------
# BW-GYM-02: Voting Poll Lifecycle (TC-WF-06 to TC-WF-10)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestVotingPollWorkflow:
    def test_tc_wf_06_poll_create_success(self):
        """TC-WF-06 (source_id: BW-GYM-02 T1-create-success):
        Verify Transition 1 success path in BW-GYM-02: Poll Not Available -> Poll Open / Target
        Audience Defined / Student Not Yet Voted.
        Preconditions: Actor is Club Head of confirmed club; poll does not exist.
        Action: Club Head invokes UC-GYM-006 (Create Voting Poll) with >= 2 choices and target
        batch/branch.
        Expected result: Poll created; state becomes 'Poll Open / Target Audience
        Defined / Student Not
        Yet Voted'; notification dispatched.
        """
        coordinator = _make_user("coord_wf06")
        co_coordinator = _make_user("cocoord_wf06")
        faculty = _make_user("faculty_wf06")
        student = _make_user("student_wf06")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        poll_title = _unique_name("AnnualFestThemePoll")

        # Precondition verification: Poll Not Available
        assert not VotingPoll.objects.filter(club=club, title=poll_title).exists()

        client = APIClient()
        client.force_authenticate(user=coordinator)

        expiry_date = (datetime.date.today() + datetime.timedelta(days=7)).isoformat()
        payload = {
            "club": club.pk,
            "title": poll_title,
            "description": "Select the theme for this year's annual fest",
            "expiry_date": expiry_date,
            "choice_texts": ["Cyberpunk Odyssey", "Neon Retro", "Solarpunk Visions"],
            "target_batches": ["2024", "2025"],
            "target_branches": ["CSE", "ECE"],
        }
        resp = client.post("/api/gymkhana/polls/", payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data

        # Verify state: Poll Open
        poll = VotingPoll.objects.get(pk=resp.data["id"])
        assert poll.is_active is True

        # Verify state: Target Audience Defined
        assert poll.target_batches == ["2024", "2025"]
        assert poll.target_branches == ["CSE", "ECE"]

        # Verify state: Student Not Yet Voted
        assert not PollVote.objects.filter(poll=poll, voter=student).exists()

        # Choices created and ready
        assert poll.choices.count() == 3
        for choice in poll.choices.all():
            assert choice.vote_count == 0

    def test_tc_wf_07_poll_create_rejected(self):
        """TC-WF-07 (source_id: BW-GYM-02 T1-create-rejected):
        Verify Transition 1 guard failure path in BW-GYM-02: actor not Club Head or fewer than 2
        choices.
        Preconditions: Requester is unauthorized OR poll data has only 1 choice.
        Action: Requester invokes UC-GYM-006.
        Expected result: Guard fails; poll creation rejected; remains in 'Poll Not Available'.
        """
        coordinator = _make_user("coord_wf07")
        co_coordinator = _make_user("cocoord_wf07")
        faculty = _make_user("faculty_wf07")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        client = APIClient()

        # Guard failure branch 1: Poll data has only 1 choice (< 2 choices)
        client.force_authenticate(user=coordinator)
        single_choice_title = _unique_name("SingleChoicePoll")
        payload_single = {
            "club": club.pk,
            "title": single_choice_title,
            "description": "Invalid poll with only 1 choice",
            "expiry_date": (datetime.date.today() + datetime.timedelta(days=5)).isoformat(),
            "choice_texts": ["Sole Option"],
            "target_batches": ["2024"],
            "target_branches": ["CSE"],
        }
        resp_single = client.post("/api/gymkhana/polls/", payload_single, format="json")
        assert resp_single.status_code == status.HTTP_400_BAD_REQUEST, resp_single.data
        # Guard fails; remains in 'Poll Not Available'
        assert not VotingPoll.objects.filter(title=single_choice_title).exists()

        # Guard failure branch 2: Requester is unauthorized (unauthenticated requester)
        unauth_client = APIClient()
        unauth_title = _unique_name("UnauthorizedPoll")
        payload_unauth = {
            "club": club.pk,
            "title": unauth_title,
            "description": "Unauthorized poll creation",
            "expiry_date": (datetime.date.today() + datetime.timedelta(days=5)).isoformat(),
            "choice_texts": ["Choice A", "Choice B"],
            "target_batches": ["2024"],
            "target_branches": ["CSE"],
        }
        resp_unauth = unauth_client.post("/api/gymkhana/polls/", payload_unauth, format="json")
        assert resp_unauth.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ), resp_unauth.data
        # Guard fails; remains in 'Poll Not Available'
        assert not VotingPoll.objects.filter(title=unauth_title).exists()

    def test_tc_wf_08_poll_vote_success(self):
        """TC-WF-08 (source_id: BW-GYM-02 T2-vote-success):
        Verify Transition 2 success path in BW-GYM-02: Student Not Yet Voted -> Student
        Vote Recorded.
        Preconditions: Poll is open and unexpired; student is in target audience and has
        not yet voted.
        Action: Student invokes UC-GYM-007 (Vote in Poll) and selects valid choice.
        Expected result: Vote accepted; tally updated; state becomes 'Poll Open / Target Audience
        Defined / Student Vote Recorded'.
        """
        coordinator = _make_user("coord_wf08")
        co_coordinator = _make_user("cocoord_wf08")
        faculty = _make_user("faculty_wf08")
        student = _make_user("student_wf08")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        poll = VotingPoll.objects.create(
            club=club,
            title=_unique_name("VoteSuccessPoll"),
            expiry_date=datetime.date.today() + datetime.timedelta(days=10),
            target_batches=["2024"],
            target_branches=["CSE"],
            created_by=coordinator,
        )
        c1 = PollChoice.objects.create(poll=poll, text="Option 1", vote_count=0)
        c2 = PollChoice.objects.create(poll=poll, text="Option 2", vote_count=0)

        # Precondition verification: Poll is open, student not yet voted
        assert poll.is_active is True
        assert not PollVote.objects.filter(poll=poll, voter=student).exists()
        assert c1.vote_count == 0

        client = APIClient()
        client.force_authenticate(user=student)

        vote_payload = {"poll": poll.pk, "choice": c1.pk}
        resp = client.post(f"/api/gymkhana/polls/{poll.pk}/vote/", vote_payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data

        # State verification: Vote accepted and student vote recorded
        assert PollVote.objects.filter(poll=poll, voter=student, choice=c1).exists()

        # State verification: Tally updated
        c1.refresh_from_db()
        c2.refresh_from_db()
        assert c1.vote_count == 1
        assert c2.vote_count == 0

        # State verification: Poll Open / Target Audience Defined / Student Vote Recorded
        assert poll.is_active is True
        assert poll.target_batches == ["2024"]
        assert poll.target_branches == ["CSE"]

    def test_tc_wf_09_poll_vote_rejected(self):
        """TC-WF-09 (source_id: BW-GYM-02 T2-vote-rejected):
        Verify Transition 2 guard failure path in BW-GYM-02: poll expired, student not
        in target group,
        or duplicate vote.
        Preconditions: Poll is expired OR student outside target group OR student already voted.
        Action: Student invokes UC-GYM-007.
        Expected result: Guard fails; vote rejected; tally unchanged; remains in 'Student Not Yet
        Voted' (or rejected for ineligible/duplicate).
        """
        coordinator = _make_user("coord_wf09")
        co_coordinator = _make_user("cocoord_wf09")
        faculty = _make_user("faculty_wf09")
        student = _make_user("student_wf09")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        client = APIClient()
        client.force_authenticate(user=student)

        # Guard failure branch 1: Poll is expired
        expired_poll = VotingPoll.objects.create(
            club=club,
            title=_unique_name("ExpiredPoll"),
            expiry_date=datetime.date.today() - datetime.timedelta(days=2),
            target_batches=["2024"],
            target_branches=["CSE"],
            created_by=coordinator,
        )
        c_exp1 = PollChoice.objects.create(poll=expired_poll, text="Exp 1", vote_count=0)
        PollChoice.objects.create(poll=expired_poll, text="Exp 2", vote_count=0)
        assert expired_poll.is_active is False

        resp_exp = client.post(
            f"/api/gymkhana/polls/{expired_poll.pk}/vote/",
            {"poll": expired_poll.pk, "choice": c_exp1.pk},
            format="json",
        )
        assert resp_exp.status_code == status.HTTP_400_BAD_REQUEST, resp_exp.data
        # Vote rejected; tally unchanged; remains in 'Student Not Yet Voted'
        assert not PollVote.objects.filter(poll=expired_poll, voter=student).exists()
        c_exp1.refresh_from_db()
        assert c_exp1.vote_count == 0

        # Guard failure branch 2: Student already voted (duplicate vote)
        active_poll = VotingPoll.objects.create(
            club=club,
            title=_unique_name("ActivePollDuplicateTest"),
            expiry_date=datetime.date.today() + datetime.timedelta(days=5),
            target_batches=["2024"],
            target_branches=["CSE"],
            created_by=coordinator,
        )
        c_act1 = PollChoice.objects.create(poll=active_poll, text="Act 1", vote_count=0)
        c_act2 = PollChoice.objects.create(poll=active_poll, text="Act 2", vote_count=0)

        # Cast first vote
        first_vote = client.post(
            f"/api/gymkhana/polls/{active_poll.pk}/vote/",
            {"poll": active_poll.pk, "choice": c_act1.pk},
            format="json",
        )
        assert first_vote.status_code == status.HTTP_201_CREATED, first_vote.data
        c_act1.refresh_from_db()
        assert c_act1.vote_count == 1

        # Attempt duplicate vote by same student on choice 2
        resp_dup = client.post(
            f"/api/gymkhana/polls/{active_poll.pk}/vote/",
            {"poll": active_poll.pk, "choice": c_act2.pk},
            format="json",
        )
        assert resp_dup.status_code == status.HTTP_400_BAD_REQUEST, resp_dup.data
        # Duplicate vote rejected; tallies unchanged
        c_act1.refresh_from_db()
        c_act2.refresh_from_db()
        assert c_act1.vote_count == 1
        assert c_act2.vote_count == 0
        assert PollVote.objects.filter(poll=active_poll, voter=student).count() == 1

    def test_tc_wf_10_poll_full_progression_path(self):
        """TC-WF-10 (source_id: BW-GYM-02 full-progression-path):
        Verify complete end-to-end success path for BW-GYM-02 from poll creation to recorded vote.
        Preconditions: Club Head and eligible student in target group ready.
        Action: Club Head creates poll (UC-GYM-006) -> eligible student casts vote (UC-GYM-007).
        Expected result: Workflow progresses: Poll Not Available -> Poll Open (Not Yet
        Voted) -> Poll
        Open (Student Vote Recorded).
        """
        coordinator = _make_user("coord_wf10")
        co_coordinator = _make_user("cocoord_wf10")
        faculty = _make_user("faculty_wf10")
        student = _make_user("student_wf10")
        club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")

        poll_title = _unique_name("EndToEndPollProgression")

        # Stage 0: Precondition - Poll Not Available
        assert not VotingPoll.objects.filter(title=poll_title).exists()

        # Stage 1: Club Head creates poll (UC-GYM-006)
        head_client = APIClient()
        head_client.force_authenticate(user=coordinator)

        expiry_date = (datetime.date.today() + datetime.timedelta(days=7)).isoformat()
        create_payload = {
            "club": club.pk,
            "title": poll_title,
            "description": "Full lifecycle poll test",
            "expiry_date": expiry_date,
            "choice_texts": ["Track Alpha", "Track Beta"],
            "target_batches": ["2024"],
            "target_branches": ["CSE"],
        }
        create_resp = head_client.post("/api/gymkhana/polls/", create_payload, format="json")
        assert create_resp.status_code == status.HTTP_201_CREATED, create_resp.data

        # Stage 1 Verification: Poll Open (Not Yet Voted)
        poll = VotingPoll.objects.get(pk=create_resp.data["id"])
        assert poll.is_active is True
        assert poll.target_batches == ["2024"]
        assert poll.target_branches == ["CSE"]
        assert not PollVote.objects.filter(poll=poll, voter=student).exists()
        choices = list(poll.choices.order_by("pk"))
        assert len(choices) == 2
        assert choices[0].vote_count == 0
        assert choices[1].vote_count == 0

        # Stage 2: Eligible student casts vote (UC-GYM-007)
        student_client = APIClient()
        student_client.force_authenticate(user=student)

        selected_choice = choices[0]
        vote_payload = {"poll": poll.pk, "choice": selected_choice.pk}
        vote_resp = student_client.post(
            f"/api/gymkhana/polls/{poll.pk}/vote/", vote_payload, format="json"
        )
        assert vote_resp.status_code == status.HTTP_201_CREATED, vote_resp.data

        # Stage 2 Verification: Poll Open (Student Vote Recorded)
        assert poll.is_active is True
        assert PollVote.objects.filter(poll=poll, voter=student, choice=selected_choice).exists()
        selected_choice.refresh_from_db()
        choices[1].refresh_from_db()
        assert selected_choice.vote_count == 1
        assert choices[1].vote_count == 0


# ---------------------------------------------------------------------------
# BW-GYM-03: Club Creation and Approval Lifecycle (TC-WF-11 to TC-WF-15)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestClubLifecycleWorkflow:
    def test_tc_wf_11_club_create_open(self):
        """TC-WF-11 (source_id: BW-GYM-03 T1-create-open):
        Verify Transition 1 success path in BW-GYM-03: Club Not Created -> Club Open.
        Preconditions: Student Admin authenticated; valid leaders, faculty councillor, and allowed
        category provided.
        Action: Student Admin invokes UC-GYM-001 (Create New Club).
        Expected result: Club created; state transitions from 'Club Not Created' to 'Club Open'.
        """
        student_admin = _make_user("admin_wf11", is_staff=True)
        coordinator = _make_user("coord_wf11")
        co_coordinator = _make_user("cocoord_wf11")
        faculty = _make_user("faculty_wf11")

        club_name = _unique_name("Robotics Club")

        # Precondition verification: Club Not Created
        assert not Club.objects.filter(name=club_name).exists()

        client = APIClient()
        client.force_authenticate(user=student_admin)

        payload = {
            "name": club_name,
            "category": "technical",
            "coordinator": coordinator.pk,
            "co_coordinator": co_coordinator.pk,
            "faculty_councillor": faculty.pk,
            "description": "Autonomous systems club",
        }
        resp = client.post("/api/gymkhana/clubs/", payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert resp.data["status"] == "open"

        # Verify state: Club Open
        club = Club.objects.get(name=club_name)
        assert club.status == "open"
        assert club.coordinator == coordinator
        assert club.co_coordinator == co_coordinator
        assert club.faculty_councillor == faculty

    def test_tc_wf_12_club_create_rejected(self):
        """TC-WF-12 (source_id: BW-GYM-03 T1-create-rejected):
        Verify Transition 1 guard failure path in BW-GYM-03: invalid student leaders,
        invalid faculty,
        or invalid category.
        Preconditions: Coordinator not valid student OR faculty councillor not valid faculty OR
        category not allowed.
        Action: Student Admin invokes UC-GYM-001 with invalid parameter.
        Expected result: Guard fails; club creation rejected; remains in 'Club Not Created'.
        """
        student_admin = _make_user("admin_wf12", is_staff=True)
        coordinator = _make_user("coord_wf12")
        co_coordinator = _make_user("cocoord_wf12")
        faculty = _make_user("faculty_wf12")

        client = APIClient()
        client.force_authenticate(user=student_admin)

        # Guard failure branch 1: Category not allowed
        invalid_cat_club_name = _unique_name("DisallowedCatClub")
        assert not Club.objects.filter(name=invalid_cat_club_name).exists()

        payload_invalid_category = {
            "name": invalid_cat_club_name,
            "category": "gaming_society",  # Not in {'technical', 'sports', 'cultural'}
            "coordinator": coordinator.pk,
            "co_coordinator": co_coordinator.pk,
            "faculty_councillor": faculty.pk,
            "description": "Club with disallowed category",
        }
        resp_cat = client.post("/api/gymkhana/clubs/", payload_invalid_category, format="json")
        assert resp_cat.status_code == status.HTTP_400_BAD_REQUEST, resp_cat.data
        # Guard fails; remains in 'Club Not Created'
        assert not Club.objects.filter(name=invalid_cat_club_name).exists()

        # Guard failure branch 2: Invalid student leader (coordinator not a valid user)
        invalid_leader_club_name = _unique_name("InvalidLeaderClub")
        assert not Club.objects.filter(name=invalid_leader_club_name).exists()

        payload_invalid_leader = {
            "name": invalid_leader_club_name,
            "category": "technical",
            "coordinator": 999999,  # Non-existent user pk
            "co_coordinator": co_coordinator.pk,
            "faculty_councillor": faculty.pk,
            "description": "Club with invalid coordinator",
        }
        resp_leader = client.post("/api/gymkhana/clubs/", payload_invalid_leader, format="json")
        assert resp_leader.status_code == status.HTTP_400_BAD_REQUEST, resp_leader.data
        # Guard fails; remains in 'Club Not Created'
        assert not Club.objects.filter(name=invalid_leader_club_name).exists()

    def test_tc_wf_13_club_approve_confirmed(self):
        """TC-WF-13 (source_id: BW-GYM-03 T2-approve-confirmed):
        Verify Transition 2 success path in BW-GYM-03: Club Open -> Club Confirmed.
        Preconditions: Club exists with status 'open'; Student Admin authenticated.
        Action: Student Admin invokes UC-GYM-011 (Approve Club).
        Expected result: Club status transitions from 'Club Open' to 'Club Confirmed'.
        """
        student_admin = _make_user("admin_wf13", is_staff=True)
        coordinator = _make_user("coord_wf13")
        co_coordinator = _make_user("cocoord_wf13")
        faculty = _make_user("faculty_wf13")

        club = _make_club(coordinator, co_coordinator, faculty, status="open")
        # Precondition verification: Club exists with status 'open'
        assert club.status == "open"

        client = APIClient()
        client.force_authenticate(user=student_admin)

        resp = client.post(f"/api/gymkhana/clubs/{club.pk}/approve/", {}, format="json")
        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert resp.data["status"] == "confirmed"

        # Verify state transition: Club Open -> Club Confirmed
        club.refresh_from_db()
        assert club.status == "confirmed"

        # Verify audit history record
        hist = GymkhanaWorkflowHistory.objects.filter(entity_type="club", entity_id=club.pk).first()
        assert hist is not None
        assert hist.from_state == "open"
        assert hist.to_state == "confirmed"
        assert hist.action_taken == "approve"
        assert hist.actor == student_admin

    def test_tc_wf_14_club_approve_rejected(self):
        """TC-WF-14 (source_id: BW-GYM-03 T2-approve-rejected):
        Verify Transition 2 guard failure path in BW-GYM-03: actor is not Student Admin or club is
        already confirmed.
        Preconditions: Requester is not Student Admin OR club is already confirmed.
        Action: Requester invokes UC-GYM-011.
        Expected result: Guard fails; approval rejected; club status remains unchanged
        ('Club Open').
        """
        student_admin = _make_user("admin_wf14", is_staff=True)
        coordinator = _make_user("coord_wf14")  # Non-staff, club leader
        co_coordinator = _make_user("cocoord_wf14")
        faculty = _make_user("faculty_wf14")

        open_club = _make_club(coordinator, co_coordinator, faculty, status="open")
        assert open_club.status == "open"

        client = APIClient()

        # Guard failure branch 1: Actor is not Student Admin (coordinator attempts self-approval)
        client.force_authenticate(user=coordinator)
        resp_self = client.post(f"/api/gymkhana/clubs/{open_club.pk}/approve/", {}, format="json")
        assert resp_self.status_code == status.HTTP_403_FORBIDDEN, resp_self.data
        open_club.refresh_from_db()
        # Guard fails; approval rejected; club status remains unchanged ('Club Open')
        assert open_club.status == "open"

        # Guard failure branch 2: Club is already confirmed
        confirmed_club = _make_club(coordinator, co_coordinator, faculty, status="confirmed")
        assert confirmed_club.status == "confirmed"

        client.force_authenticate(user=student_admin)
        resp_already = client.post(
            f"/api/gymkhana/clubs/{confirmed_club.pk}/approve/", {}, format="json"
        )
        assert resp_already.status_code == status.HTTP_400_BAD_REQUEST, resp_already.data
        confirmed_club.refresh_from_db()
        # Club status remains unchanged ('confirmed')
        assert confirmed_club.status == "confirmed"

    def test_tc_wf_15_club_full_progression_path(self):
        """TC-WF-15 (source_id: BW-GYM-03 full-progression-path):
        Verify complete end-to-end success path for BW-GYM-03 from no club to confirmed club.
        Preconditions: Student Admin authenticated; valid leaders and faculty councillor available.
        Action: Student Admin executes UC-GYM-001 (Create) -> Student Admin executes UC-GYM-011
        (Approve).
        Expected result: Workflow progresses: Club Not Created -> Club Open -> Club Confirmed.
        """
        student_admin = _make_user("admin_wf15", is_staff=True)
        coordinator = _make_user("coord_wf15")
        co_coordinator = _make_user("cocoord_wf15")
        faculty = _make_user("faculty_wf15")

        club_name = _unique_name("AeromodellingClub")

        # Stage 0: Precondition - Club Not Created
        assert not Club.objects.filter(name=club_name).exists()

        client = APIClient()
        client.force_authenticate(user=student_admin)

        # Stage 1: Student Admin executes UC-GYM-001 (Create)
        create_payload = {
            "name": club_name,
            "category": "technical",
            "coordinator": coordinator.pk,
            "co_coordinator": co_coordinator.pk,
            "faculty_councillor": faculty.pk,
            "description": "Design and build RC aircraft and drones",
        }
        create_resp = client.post("/api/gymkhana/clubs/", create_payload, format="json")
        assert create_resp.status_code == status.HTTP_201_CREATED, create_resp.data

        # Stage 1 Verification: Club Open
        club = Club.objects.get(name=club_name)
        assert club.status == "open"

        # Stage 2: Student Admin executes UC-GYM-011 (Approve)
        approve_resp = client.post(f"/api/gymkhana/clubs/{club.pk}/approve/", {}, format="json")
        assert approve_resp.status_code == status.HTTP_200_OK, approve_resp.data

        # Stage 2 Verification: Club Confirmed
        club.refresh_from_db()
        assert club.status == "confirmed"

        # Audit history verification
        history = GymkhanaWorkflowHistory.objects.filter(
            entity_type="club", entity_id=club.pk
        ).first()
        assert history is not None
        assert history.from_state == "open"
        assert history.to_state == "confirmed"
        assert history.action_taken == "approve"
        assert history.actor == student_admin
