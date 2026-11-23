"""High-volume parametrized stress tests for Gymkhana polls and voting.

Covers:
- BR-GYM-012: at least 2 non-empty distinct choices
- BR-GYM-013: poll targeting by batch / branch
- BR-GYM-014: vote only allowed before expiry
- BR-GYM-015: one-vote-per-student guarantee (re-vote defense)
- UC-GYM-006: create poll workflow
- UC-GYM-007: cast vote workflow
- BW-GYM-02: poll lifecycle (active → expired)
"""
import datetime

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.directory.models import UserRef
from modules.gymkhana.models.club import Club
from modules.gymkhana.models.poll import Poll, PollChoice, PollTargetGroup

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _temp_media(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path / "media")


def _as(stub_iam, uid, perms, kind="student", roles=("student",)):
    stub_iam(
        make_session(
            user_id=uid,
            kind=kind,
            roles=roles,
            modules=("gymkhana",),
            permissions=perms,
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test-token-123")
    return client


HEAD_PERMS = ("gymkhana.poll.view", "gymkhana.poll.create", "gymkhana.poll.vote")
VOTER_PERMS = ("gymkhana.poll.view", "gymkhana.poll.vote")


@pytest.fixture
def club_and_head():
    """Confirmed club with head=uid 101, co=102, fac=201."""
    UserRef.objects.create(
        user_id=101, username="stu101", display_name="S101", kind="student", is_active=True
    )
    UserRef.objects.create(
        user_id=102, username="stu102", display_name="S102", kind="student", is_active=True
    )
    UserRef.objects.create(
        user_id=201, username="fac201", display_name="F201", kind="faculty", is_active=True
    )
    return Club.objects.create(
        name="Poll Club",
        category="cultural",
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=201,
        status="confirmed",
    )


def _future(seconds=86400):
    return (datetime.datetime.now(datetime.UTC) + datetime.timedelta(seconds=seconds)).isoformat()


def _past(seconds=10):
    return (datetime.datetime.now(datetime.UTC) - datetime.timedelta(seconds=seconds)).isoformat()


def _create_poll_via_api(client, club_id, choices, target_groups=None, expires_in=86400):
    target_groups = target_groups or [{"batch": "all", "branch": "all"}]
    return client.post(
        "/api/v1/gymkhana/polls/",
        {
            "club_id": club_id,
            "title": "Stress Poll",
            "description": "d",
            "expires_at": _future(expires_in),
            "choices": choices,
            "target_groups": target_groups,
        },
        format="json",
    )


# ---------------------------------------------------------------------------
# A. Poll choice permutations (BR-GYM-012)
# ---------------------------------------------------------------------------

CHOICE_CASES = [
    # (choices, expect_valid, description)
    # --- Invalid ---
    ([], False, "empty list"),
    (["A"], False, "only 1 choice"),
    ([""], False, "one empty string"),
    (["", ""], False, "two empty strings"),
    (["  "], False, "one whitespace"),
    (["  ", "   "], False, "two whitespace strings"),
    (["A", "A"], False, "two identical choices"),
    (["Alpha", "Alpha"], False, "two identical Alpha"),
    (["alpha", "alpha"], False, "two identical alpha"),
    (["A", "A", "B"], False, "duplicate in triplet"),
    (["X"] * 10, False, "ten identical choices"),
    (["A", " A "], False, "strip-normalized duplicate"),
    ([" B ", "B"], False, "strip-normalized duplicate reversed"),
    (["Same", "Same", "Same"], False, "triple identical"),
    # --- Valid ---
    (["A", "B"], True, "minimum 2 distinct"),
    (["Alice", "Bob"], True, "2 names"),
    (["Option 1", "Option 2", "Option 3"], True, "3 options"),
    (["Alpha", "alpha"], True, "case-sensitive distinct"),
    (["Alpha", "ALPHA"], True, "upper/lower distinct"),
    ([f"Choice {i}" for i in range(10)], True, "10 distinct choices"),
    (["  A  ", "  B  "], True, "whitespace-padded but distinct after strip"),
    (["yes", "no", "maybe", "abstain"], True, "4 valid options"),
    (["1", "2"], True, "numeric strings"),
    (["a" * 100, "b" * 100], True, "long strings distinct"),
]


@pytest.mark.parametrize(
    "choices,expect_valid,desc",
    CHOICE_CASES,
    ids=[d for _, _, d in CHOICE_CASES],
)
def test_poll_choice_validation(stub_iam, club_and_head, choices, expect_valid, desc):
    """Validate poll creation succeeds/fails based on choice list content."""
    club = club_and_head
    client = _as(stub_iam, 101, HEAD_PERMS)

    res = _create_poll_via_api(client, club.id, choices)

    if expect_valid:
        assert res.status_code == 201, f"[{desc}] expected 201, got {res.status_code}: {res.data}"
    else:
        assert res.status_code == 400, f"[{desc}] expected 400, got {res.status_code}: {res.data}"


# ---------------------------------------------------------------------------
# B. Poll targeting: batch x branch eligibility matrix (BR-GYM-013)
# ---------------------------------------------------------------------------

# Poll target configs to test: (poll_batch, poll_branch)
POLL_TARGET_CONFIGS = [
    ("all", "all"),
    ("2024", "all"),
    ("2025", "all"),
    ("2026", "all"),
    ("all", "CSE"),
    ("all", "ECE"),
    ("all", "ME"),
    ("2024", "CSE"),
    ("2024", "ECE"),
    ("2025", "CSE"),
    ("2026", "ME"),
]

# Voter profiles: (student_batch, student_branch)
# Note: since Principal has no batch/discipline, we test via is_student_targeted logic.
# Targeted votes use "all"/"all" for the poll, targeting-failure tests use specific batch/branch
# with no matching principal attributes (getattr returns None → no match for specific targets).

# Eligibility: eligible if poll targets "all"/"all", or if principal had matching batch/branch.
# Since Principal never carries batch/discipline, only "all"/"all" polls pass targeting.


@pytest.mark.parametrize(
    "poll_batch,poll_branch",
    POLL_TARGET_CONFIGS,
    ids=[f"poll-{b}-{br}" for b, br in POLL_TARGET_CONFIGS],
)
def test_poll_targeting_all_all_always_eligible(stub_iam, club_and_head, poll_batch, poll_branch):
    """Polls with target=all/all let any student vote; specific-only polls block students."""
    club = club_and_head
    head_client = _as(stub_iam, 101, HEAD_PERMS)

    # Create poll with given target
    res = head_client.post(
        "/api/v1/gymkhana/polls/",
        {
            "club_id": club.id,
            "title": f"Target Poll {poll_batch}/{poll_branch}",
            "description": "d",
            "expires_at": _future(),
            "choices": ["Yes", "No"],
            "target_groups": [{"batch": poll_batch, "branch": poll_branch}],
        },
        format="json",
    )
    assert res.status_code == 201
    poll_id = res.data["id"]
    choice_id = res.data["choices"][0]["id"]

    voter_uid = 500
    if not UserRef.objects.filter(user_id=voter_uid).exists():
        UserRef.objects.create(
            user_id=voter_uid, username="voter500", display_name="Voter", kind="student", is_active=True
        )
    voter_client = _as(stub_iam, voter_uid, VOTER_PERMS)
    vote_res = voter_client.post(
        f"/api/v1/gymkhana/polls/{poll_id}/vote/",
        {"choice_id": choice_id},
        format="json",
    )

    if poll_batch == "all" and poll_branch == "all":
        # Principal has no batch/branch but "all"/"all" matches anyone
        assert vote_res.status_code == 200, (
            f"all/all poll: expected 200, got {vote_res.status_code}: {vote_res.data}"
        )
    else:
        # Specific batch/branch: principal has no batch/discipline → no match → 403
        assert vote_res.status_code == 403, (
            f"specific {poll_batch}/{poll_branch} poll: expected 403, got {vote_res.status_code}: {vote_res.data}"
        )


# ---------------------------------------------------------------------------
# C. Expiry boundary temporal testing (BR-GYM-014)
# ---------------------------------------------------------------------------

# Note: creating a poll with expires_at in the past fails at creation time
# (the create_poll service checks expires_at <= now → BadRequest).
# We test: voting on a poll whose status was set to 'expired' manually → 400.

EXPIRY_VOTING_CASES = [
    # (is_active, is_expired, expect_vote_code)
    (True, False, 200),    # active poll → 200
    (False, True, 400),    # expired poll → 400
]


@pytest.mark.parametrize("is_active,is_expired,expected", EXPIRY_VOTING_CASES)
def test_vote_on_expired_vs_active_poll(stub_iam, club_and_head, is_active, is_expired, expected):
    """Voting on an expired poll must return 400; active → 200."""
    club = club_and_head
    # Create poll manually to control status
    if is_expired:
        past_time = datetime.datetime.now(datetime.UTC) - datetime.timedelta(seconds=10)
        poll = Poll.objects.create(
            club=club,
            created_by_id=101,
            title="Expired Poll",
            expires_at=past_time,
            status="expired",
        )
    else:
        future_time = datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=24)
        poll = Poll.objects.create(
            club=club,
            created_by_id=101,
            title="Active Poll",
            expires_at=future_time,
            status="active",
        )
    PollTargetGroup.objects.create(poll=poll, batch="all", branch="all")
    choice = PollChoice.objects.create(poll=poll, choice_text="Yes")

    voter_uid = 601
    if not UserRef.objects.filter(user_id=voter_uid).exists():
        UserRef.objects.create(
            user_id=voter_uid, username="voter601", display_name="Voter601",
            kind="student", is_active=True
        )
    voter_client = _as(stub_iam, voter_uid, VOTER_PERMS)
    res = voter_client.post(
        f"/api/v1/gymkhana/polls/{poll.id}/vote/",
        {"choice_id": choice.id},
        format="json",
    )
    assert res.status_code == expected, (
        f"is_active={is_active}: expected {expected}, got {res.status_code}: {res.data}"
    )


# ---------------------------------------------------------------------------
# D. Expiry boundary at poll creation level
# ---------------------------------------------------------------------------

EXPIRY_CREATION_CASES = [
    # (seconds_from_now, expect_valid, label)
    (86400, True, "24h in future"),
    (3600, True, "1h in future"),
    (60, True, "1 min in future"),
    (1, True, "1 second in future"),
    (0, False, "exactly now (expires_at == now) → invalid"),
    (-1, False, "1 second in past"),
    (-3600, False, "1 hour in past"),
    (-86400, False, "1 day in past"),
]


@pytest.mark.parametrize("delta_seconds,expect_valid,label", EXPIRY_CREATION_CASES, ids=[lbl for _, _, lbl in EXPIRY_CREATION_CASES])
def test_poll_expiry_creation_boundary(stub_iam, club_and_head, delta_seconds, expect_valid, label):
    """Poll creation must reject expiry at or before now."""
    club = club_and_head
    client = _as(stub_iam, 101, HEAD_PERMS)

    if delta_seconds == 0:
        # exactly now — by the time we send the request it'll be in the past
        expires_at = datetime.datetime.now(datetime.UTC).isoformat()
    else:
        expires_at = (
            datetime.datetime.now(datetime.UTC) + datetime.timedelta(seconds=delta_seconds)
        ).isoformat()

    res = client.post(
        "/api/v1/gymkhana/polls/",
        {
            "club_id": club.id,
            "title": f"Expiry Test {label}",
            "description": "d",
            "expires_at": expires_at,
            "choices": ["A", "B"],
            "target_groups": [{"batch": "all", "branch": "all"}],
        },
        format="json",
    )

    if expect_valid:
        assert res.status_code == 201, f"[{label}] expected 201, got {res.status_code}: {res.data}"
    else:
        assert res.status_code == 400, f"[{label}] expected 400, got {res.status_code}: {res.data}"


# ---------------------------------------------------------------------------
# E. Re-vote defense: 20 sequential attempts, only 1 succeeds (BR-GYM-015)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("attempt_num", list(range(1, 21)))
def test_revote_defense_sequential(stub_iam, club_and_head, attempt_num):
    """Each attempt after the first must fail with 409 (already voted)."""
    club = club_and_head

    # Create a shared poll (created once per test due to django_db isolation per parametrize)
    future_time = datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=24)
    poll = Poll.objects.create(
        club=club,
        created_by_id=101,
        title="Revote Defense Poll",
        expires_at=future_time,
        status="active",
    )
    PollTargetGroup.objects.create(poll=poll, batch="all", branch="all")
    choice = PollChoice.objects.create(poll=poll, choice_text="Option A")
    PollChoice.objects.create(poll=poll, choice_text="Option B")

    voter_uid = 700
    if not UserRef.objects.filter(user_id=voter_uid).exists():
        UserRef.objects.create(
            user_id=voter_uid, username="voter700", display_name="V700", kind="student", is_active=True
        )

    voter_client = _as(stub_iam, voter_uid, VOTER_PERMS)

    # Submit `attempt_num` votes, capturing the last one
    final_code = None
    for _i in range(attempt_num):
        res = voter_client.post(
            f"/api/v1/gymkhana/polls/{poll.id}/vote/",
            {"choice_id": choice.id},
            format="json",
        )
        final_code = res.status_code

    if attempt_num == 1:
        assert final_code == 200, f"First vote should succeed, got {final_code}"
    else:
        assert final_code == 409, f"Attempt {attempt_num} should return 409, got {final_code}"


# ---------------------------------------------------------------------------
# F. Poll creation authorization (only club head can create)
# ---------------------------------------------------------------------------

NON_HEAD_CREATOR_UIDS = [103, 104, 500, 999]


@pytest.mark.parametrize("uid", NON_HEAD_CREATOR_UIDS)
def test_non_head_cannot_create_poll(stub_iam, club_and_head, uid):
    """Non-head students should receive 403 when trying to create a poll."""
    if not UserRef.objects.filter(user_id=uid).exists():
        UserRef.objects.create(
            user_id=uid, username=f"stu{uid}", display_name=f"S{uid}",
            kind="student", is_active=True
        )
    client = _as(stub_iam, uid, HEAD_PERMS)

    res = _create_poll_via_api(client, club_and_head.id, ["A", "B"])
    assert res.status_code == 403, f"uid={uid}: expected 403, got {res.status_code}: {res.data}"


# ---------------------------------------------------------------------------
# G. Poll on unconfirmed club → 409
# ---------------------------------------------------------------------------

def test_poll_on_unconfirmed_club_rejected(stub_iam):
    """Poll creation on a non-confirmed club must return 409."""
    UserRef.objects.get_or_create(
        user_id=401, defaults={"username": "s401", "display_name": "S401", "kind": "student", "is_active": True}
    )
    UserRef.objects.get_or_create(
        user_id=402, defaults={"username": "s402", "display_name": "S402", "kind": "student", "is_active": True}
    )
    UserRef.objects.get_or_create(
        user_id=201, defaults={"username": "f201", "display_name": "F201", "kind": "faculty", "is_active": True}
    )
    club = Club.objects.create(
        name="Open Club",
        category="sports",
        coordinator_id=401,
        co_coordinator_id=402,
        faculty_councillor_id=201,
        status="open",
    )
    client = _as(stub_iam, 401, HEAD_PERMS)
    res = _create_poll_via_api(client, club.id, ["Yes", "No"])
    assert res.status_code == 409, f"expected 409, got {res.status_code}: {res.data}"


# ---------------------------------------------------------------------------
# H. Vote on wrong choice (choice belongs to different poll) → 404
# ---------------------------------------------------------------------------

def test_vote_wrong_poll_choice_rejected(stub_iam, club_and_head):
    """Voting with a choice_id from a different poll must return 404."""
    club = club_and_head
    head_client = _as(stub_iam, 101, HEAD_PERMS)

    # Create poll A
    res_a = _create_poll_via_api(head_client, club.id, ["A1", "A2"])
    assert res_a.status_code == 201
    poll_a_id = res_a.data["id"]

    # Create poll B
    res_b = _create_poll_via_api(head_client, club.id, ["B1", "B2"])
    assert res_b.status_code == 201
    # Get choice from poll B
    choice_b_id = res_b.data["choices"][0]["id"]

    voter_uid = 800
    if not UserRef.objects.filter(user_id=voter_uid).exists():
        UserRef.objects.create(
            user_id=voter_uid, username="v800", display_name="V800", kind="student", is_active=True
        )
    voter = _as(stub_iam, voter_uid, VOTER_PERMS)

    # Try voting in poll A with poll B's choice
    res = voter.post(
        f"/api/v1/gymkhana/polls/{poll_a_id}/vote/",
        {"choice_id": choice_b_id},
        format="json",
    )
    assert res.status_code == 404, f"expected 404, got {res.status_code}: {res.data}"


# ---------------------------------------------------------------------------
# I. Multiple target groups — cartesian product eligibility
# ---------------------------------------------------------------------------

MULTI_TARGET_CASES = [
    # (target_groups, voter_should_match_description)
    (
        [{"batch": "all", "branch": "all"}, {"batch": "2024", "branch": "CSE"}],
        True,
        "has all/all group → matches",
    ),
    (
        [{"batch": "2024", "branch": "CSE"}, {"batch": "2025", "branch": "ECE"}],
        False,
        "both specific groups → no match (principal has no batch/branch)",
    ),
    (
        [{"batch": "all", "branch": "CSE"}],
        False,
        "all batch but specific branch → branch won't match (no branch on principal)",
    ),
]


@pytest.mark.parametrize(
    "target_groups,expect_vote_ok,desc",
    MULTI_TARGET_CASES,
    ids=[d for _, _, d in MULTI_TARGET_CASES],
)
def test_multi_target_group_eligibility(stub_iam, club_and_head, target_groups, expect_vote_ok, desc):
    """Verify multiple target groups use OR logic."""
    club = club_and_head
    head_client = _as(stub_iam, 101, HEAD_PERMS)

    res = head_client.post(
        "/api/v1/gymkhana/polls/",
        {
            "club_id": club.id,
            "title": f"Multi Target {desc}",
            "description": "d",
            "expires_at": _future(),
            "choices": ["X", "Y"],
            "target_groups": target_groups,
        },
        format="json",
    )
    assert res.status_code == 201
    poll_id = res.data["id"]
    choice_id = res.data["choices"][0]["id"]

    voter_uid = 900
    if not UserRef.objects.filter(user_id=voter_uid).exists():
        UserRef.objects.create(
            user_id=voter_uid, username="v900", display_name="V900", kind="student", is_active=True
        )
    voter = _as(stub_iam, voter_uid, VOTER_PERMS)
    vote_res = voter.post(
        f"/api/v1/gymkhana/polls/{poll_id}/vote/",
        {"choice_id": choice_id},
        format="json",
    )

    if expect_vote_ok:
        assert vote_res.status_code == 200, f"[{desc}] expected 200, got {vote_res.status_code}: {vote_res.data}"
    else:
        assert vote_res.status_code == 403, f"[{desc}] expected 403, got {vote_res.status_code}: {vote_res.data}"


# ---------------------------------------------------------------------------
# J. Poll listing - anonymous / no-perm
# ---------------------------------------------------------------------------

def test_poll_list_anonymous():
    """Anonymous request must get 401."""
    client = APIClient()
    res = client.get("/api/v1/gymkhana/polls/")
    assert res.status_code == 401


def test_poll_list_no_perm(stub_iam):
    """No gymkhana.poll.view permission → 403."""
    client = _as(stub_iam, 500, ())
    res = client.get("/api/v1/gymkhana/polls/")
    assert res.status_code == 403


# ---------------------------------------------------------------------------
# K. Poll title / description edge cases (empty, whitespace, long)
# ---------------------------------------------------------------------------

TITLE_CASES = [
    ("Valid Title", True),
    ("A" * 200, True),    # max_length boundary
    ("  Whitespace Padded  ", True),  # title with whitespace
]


@pytest.mark.parametrize("title,expect_ok", TITLE_CASES)
def test_poll_title_variations(stub_iam, club_and_head, title, expect_ok):
    """Test poll creation with various title values."""
    club = club_and_head
    client = _as(stub_iam, 101, HEAD_PERMS)
    res = client.post(
        "/api/v1/gymkhana/polls/",
        {
            "club_id": club.id,
            "title": title,
            "description": "d",
            "expires_at": _future(),
            "choices": ["A", "B"],
            "target_groups": [{"batch": "all", "branch": "all"}],
        },
        format="json",
    )
    if expect_ok:
        assert res.status_code == 201, f"title={title!r}: expected 201, got {res.status_code}: {res.data}"
    else:
        assert res.status_code == 400, f"title={title!r}: expected 400, got {res.status_code}: {res.data}"


# ---------------------------------------------------------------------------
# L. No target_groups → defaults to all/all
# ---------------------------------------------------------------------------

def test_poll_no_target_groups_defaults_all(stub_iam, club_and_head):
    """Creating poll without target_groups should default to all/all and allow any student to vote."""
    club = club_and_head
    client = _as(stub_iam, 101, HEAD_PERMS)

    res = client.post(
        "/api/v1/gymkhana/polls/",
        {
            "club_id": club.id,
            "title": "No Target Groups",
            "description": "d",
            "expires_at": _future(),
            "choices": ["Alpha", "Beta"],
        },
        format="json",
    )
    assert res.status_code == 201
    poll_id = res.data["id"]
    choice_id = res.data["choices"][0]["id"]

    voter_uid = 950
    if not UserRef.objects.filter(user_id=voter_uid).exists():
        UserRef.objects.create(
            user_id=voter_uid, username="v950", display_name="V950", kind="student", is_active=True
        )
    voter = _as(stub_iam, voter_uid, VOTER_PERMS)
    vote_res = voter.post(
        f"/api/v1/gymkhana/polls/{poll_id}/vote/",
        {"choice_id": choice_id},
        format="json",
    )
    assert vote_res.status_code == 200, f"expected 200, got {vote_res.status_code}: {vote_res.data}"


# ---------------------------------------------------------------------------
# M. Expire task integration
# ---------------------------------------------------------------------------

def test_expire_polls_task_marks_overdue(club_and_head):
    """The expire_overdue_polls() function must mark past-due active polls as expired."""
    from modules.gymkhana.services.polls import expire_overdue_polls

    club = club_and_head
    past_time = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=1)
    poll = Poll.objects.create(
        club=club,
        created_by_id=101,
        title="Stale Poll",
        expires_at=past_time,
        status="active",
    )
    count = expire_overdue_polls()
    assert count >= 1
    poll.refresh_from_db()
    assert poll.status == "expired"


EXPIRE_BOUNDARY_CASES = [
    # (seconds_past, should_be_expired)
    (-1, False),   # 1 second in the future → still active
    (0, True),     # expires_at == now → expired (lte check)
    (1, True),     # 1 second past → expired
    (3600, True),  # 1 hour past → expired
]


@pytest.mark.parametrize("seconds_past,should_expire", EXPIRE_BOUNDARY_CASES)
def test_expire_task_boundary(club_and_head, seconds_past, should_expire):
    """Test expire_overdue_polls at time boundaries."""
    from modules.gymkhana.services.polls import expire_overdue_polls

    club = club_and_head
    # expires_at = now - seconds_past  (negative means in future)
    expires_at = datetime.datetime.now(datetime.UTC) - datetime.timedelta(seconds=seconds_past)
    poll = Poll.objects.create(
        club=club,
        created_by_id=101,
        title=f"Boundary {seconds_past}",
        expires_at=expires_at,
        status="active",
    )
    expire_overdue_polls()
    poll.refresh_from_db()

    if should_expire:
        assert poll.status == "expired", f"seconds_past={seconds_past}: expected expired"
    else:
        assert poll.status == "active", f"seconds_past={seconds_past}: expected still active"
