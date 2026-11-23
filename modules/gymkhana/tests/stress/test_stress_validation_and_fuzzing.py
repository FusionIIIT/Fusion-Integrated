"""High-volume validation and fuzzing stress tests for Gymkhana module.

Covers:
- BR-GYM-001: Club name uniqueness (implied)
- BR-GYM-002: Faculty councillor must be faculty kind
- BR-GYM-003: Club category must be technical/sports/cultural
- BR-GYM-004: Coordinator and co-coordinator must be distinct
- BR-GYM-007: Membership only for confirmed clubs
- BR-GYM-008: Student can only have one active membership per club
- BR-GYM-009: Leadership must be active students
- BR-GYM-017: Budget amount non-negative
- BR-GYM-018: Budget supporting file required
- BR-GYM-019: Event report file required
- BW-GYM-01: Club state machine (open → confirmed)
- BW-GYM-02: Poll lifecycle transitions
- BW-GYM-03: Membership state machine (open → confirmed)
"""
import datetime

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
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


@pytest.fixture
def base_users():
    UserRef.objects.create(user_id=101, username="s101", display_name="S101", kind="student", is_active=True)
    UserRef.objects.create(user_id=102, username="s102", display_name="S102", kind="student", is_active=True)
    UserRef.objects.create(user_id=103, username="s103", display_name="S103", kind="student", is_active=True)
    UserRef.objects.create(user_id=104, username="s104", display_name="S104", kind="student", is_active=True)
    UserRef.objects.create(user_id=201, username="f201", display_name="F201", kind="faculty", is_active=True)
    UserRef.objects.create(user_id=202, username="f202", display_name="F202", kind="faculty", is_active=True)


@pytest.fixture
def confirmed_club(base_users):
    return Club.objects.create(
        name="Fuzz Club",
        category="technical",
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=201,
        status="confirmed",
    )


CREATE_PERMS = ("gymkhana.club.view", "gymkhana.club.create")
APPROVE_PERMS = ("gymkhana.club.view", "gymkhana.club.create", "gymkhana.club.approve")


def _base_club_payload(coordinator_id=101, co_coordinator_id=102, fc_id=201, **overrides):
    payload = {
        "name": "New Fuzz Club",
        "category": "technical",
        "description": "d",
        "coordinator_id": coordinator_id,
        "co_coordinator_id": co_coordinator_id,
        "faculty_councillor_id": fc_id,
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# A. Club category fuzzing (BR-GYM-003)
# ---------------------------------------------------------------------------

VALID_CATEGORIES = [
    ("technical", True, "technical lowercase"),
    ("sports", True, "sports lowercase"),
    ("cultural", True, "cultural lowercase"),
    ("Technical", True, "Technical capitalized"),
    ("Sports", True, "Sports capitalized"),
    ("Cultural", True, "Cultural capitalized"),
    ("TECHNICAL", True, "TECHNICAL uppercase"),
    ("SPORTS", True, "SPORTS uppercase"),
    ("CULTURAL", True, "CULTURAL uppercase"),
    ("  technical  ", True, "technical with spaces"),
    ("  sports  ", True, "sports with spaces"),
    ("  cultural  ", True, "cultural with spaces"),
    ("TeChNiCaL", True, "mixed case technical"),
    ("SpOrTs", True, "mixed case sports"),
    ("CuLtUrAl", True, "mixed case cultural"),
]

INVALID_CATEGORIES = [
    ("", False, "empty string"),
    (" ", False, "whitespace only"),
    ("academic", False, "academic - not in list"),
    ("robotics", False, "robotics - not in list"),
    ("arts", False, "arts - not in list"),
    ("science", False, "science - not in list"),
    ("humanities", False, "humanities - not in list"),
    ("technica", False, "partial match technical"),
    ("sport", False, "partial match sports"),
    ("cultur", False, "partial match cultural"),
    ("sports2", False, "sports with suffix"),
    ("cultural!", False, "cultural with special char"),
    ("'; DROP TABLE--", False, "SQL injection"),
    ("null", False, "null string"),
    ("undefined", False, "undefined string"),
    ("None", False, "None string"),
    ("True", False, "True string"),
    ("1", False, "numeric string"),
    ("A" * 500, False, "500-char string"),
    ("<script>", False, "XSS attempt"),
    ("technical sports", False, "compound category"),
    ("social", False, "social - not in list"),
    ("literary", False, "literary - not in list"),
]

ALL_CATEGORY_CASES = VALID_CATEGORIES + INVALID_CATEGORIES


@pytest.mark.parametrize(
    "category,expect_valid,desc",
    ALL_CATEGORY_CASES,
    ids=[d for _, _, d in ALL_CATEGORY_CASES],
)
def test_club_category_validation(stub_iam, base_users, category, expect_valid, desc):
    """Club creation accepts only technical/sports/cultural (case-insensitive, strips whitespace)."""
    client = _as(stub_iam, 999, CREATE_PERMS)
    if not UserRef.objects.filter(user_id=999).exists():
        UserRef.objects.create(user_id=999, username="admin999", display_name="A999", kind="student", is_active=True)

    res = client.post(
        "/api/v1/gymkhana/clubs/",
        _base_club_payload(category=category, name=f"Cat Test {desc[:20]}"),
        format="json",
    )

    if expect_valid:
        assert res.status_code == 201, f"[{desc}] expected 201, got {res.status_code}: {res.data}"
    else:
        assert res.status_code == 400, f"[{desc}] expected 400, got {res.status_code}: {res.data}"


# ---------------------------------------------------------------------------
# B. Distinct leaders validation (BR-GYM-004)
# ---------------------------------------------------------------------------

LEADER_CASES = [
    # (coordinator_id, co_coordinator_id, expect_valid, desc)
    (101, 102, True, "distinct students"),
    (101, 101, False, "same student as both"),
    (102, 102, False, "same uid repeated"),
    (103, 103, False, "same uid repeated alt"),
]


@pytest.mark.parametrize(
    "coord_id,co_coord_id,expect_valid,desc",
    LEADER_CASES,
    ids=[d for _, _, _, d in LEADER_CASES],
)
def test_distinct_leaders_validation(stub_iam, base_users, coord_id, co_coord_id, expect_valid, desc):
    """Coordinator and Co-coordinator must be different users (BR-GYM-004)."""
    client = _as(stub_iam, 999, CREATE_PERMS)
    if not UserRef.objects.filter(user_id=999).exists():
        UserRef.objects.create(user_id=999, username="admin999", display_name="A999", kind="student", is_active=True)

    res = client.post(
        "/api/v1/gymkhana/clubs/",
        _base_club_payload(coordinator_id=coord_id, co_coordinator_id=co_coord_id, name="Leader Test"),
        format="json",
    )
    if expect_valid:
        assert res.status_code == 201, f"[{desc}] expected 201, got {res.status_code}: {res.data}"
    else:
        assert res.status_code == 400, f"[{desc}] expected 400, got {res.status_code}: {res.data}"


# ---------------------------------------------------------------------------
# C. Faculty councillor must be faculty kind (BR-GYM-002)
# ---------------------------------------------------------------------------

FC_KIND_CASES = [
    (201, True, "valid faculty"),
    (202, True, "valid faculty 2"),
    (101, False, "student uid as fc"),
    (102, False, "student uid as fc 2"),
    (9999, False, "non-existent user as fc"),
    (0, False, "zero uid"),
]


@pytest.mark.parametrize(
    "fc_id,expect_valid,desc",
    FC_KIND_CASES,
    ids=[d for _, _, d in FC_KIND_CASES],
)
def test_faculty_councillor_kind_validation(stub_iam, base_users, fc_id, expect_valid, desc):
    """Faculty councillor must be of kind=faculty (BR-GYM-002)."""
    client = _as(stub_iam, 999, CREATE_PERMS)
    if not UserRef.objects.filter(user_id=999).exists():
        UserRef.objects.create(user_id=999, username="admin999", display_name="A999", kind="student", is_active=True)

    res = client.post(
        "/api/v1/gymkhana/clubs/",
        _base_club_payload(fc_id=fc_id, name=f"FC Kind Test {desc[:15]}"),
        format="json",
    )
    if expect_valid:
        assert res.status_code == 201, f"[{desc}] expected 201, got {res.status_code}: {res.data}"
    else:
        assert res.status_code in (400, 404), f"[{desc}] expected 400/404, got {res.status_code}: {res.data}"


# ---------------------------------------------------------------------------
# D. Budget amount fuzzing (BR-GYM-017)
# ---------------------------------------------------------------------------

BUDGET_AMOUNT_CASES = [
    # (amount, expect_valid, desc)
    ("0.00", True, "zero allowed"),
    ("0.01", True, "one cent"),
    ("100.00", True, "round number"),
    ("99999999.99", True, "large positive"),
    ("1234567.89", True, "large decimal"),
    ("-0.01", False, "negative tiny"),
    ("-1", False, "negative one"),
    ("-500", False, "large negative"),
    ("-99999999.99", False, "large negative decimal"),
]


@pytest.mark.parametrize(
    "amount,expect_valid,desc",
    BUDGET_AMOUNT_CASES,
    ids=[d for _, _, d in BUDGET_AMOUNT_CASES],
)
def test_budget_amount_validation(stub_iam, confirmed_club, amount, expect_valid, desc):
    """Budget amounts must be non-negative (BR-GYM-017)."""
    client = _as(stub_iam, 101, ("gymkhana.budget.view", "gymkhana.budget.create"))
    dummy_file = SimpleUploadedFile("bill.pdf", b"data", content_type="application/pdf")

    res = client.post(
        "/api/v1/gymkhana/budgets/",
        {
            "club_id": confirmed_club.id,
            "amount": amount,
            "purpose": f"Amount test {desc[:20]}",
            "description": "d",
            "supporting_file": dummy_file,
        },
        format="multipart",
    )
    if expect_valid:
        assert res.status_code == 201, f"[{desc}] expected 201, got {res.status_code}: {res.data}"
    else:
        assert res.status_code == 400, f"[{desc}] expected 400, got {res.status_code}: {res.data}"


# ---------------------------------------------------------------------------
# E. Budget file required (BR-GYM-018)
# ---------------------------------------------------------------------------

def test_budget_missing_file_rejected(stub_iam, confirmed_club):
    """Budget submission without supporting_file must be rejected with 400."""
    client = _as(stub_iam, 101, ("gymkhana.budget.view", "gymkhana.budget.create"))

    res = client.post(
        "/api/v1/gymkhana/budgets/",
        {
            "club_id": confirmed_club.id,
            "amount": "500.00",
            "purpose": "No file test",
            "description": "d",
            # No supporting_file!
        },
        format="multipart",
    )
    assert res.status_code == 400, f"expected 400, got {res.status_code}: {res.data}"


BUDGET_FILE_TYPE_CASES = [
    ("bill.pdf", b"PDF content", "application/pdf", True, "valid PDF"),
    ("bill.xlsx", b"XLSX content", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", True, "XLSX"),
    ("image.jpg", b"JPEG content", "image/jpeg", True, "JPEG image"),
    ("bill.txt", b"plain text", "text/plain", True, "plain text"),
]


@pytest.mark.parametrize(
    "filename,content,content_type,expect_ok,desc",
    BUDGET_FILE_TYPE_CASES,
    ids=[d for _, _, _, _, d in BUDGET_FILE_TYPE_CASES],
)
def test_budget_file_types(stub_iam, confirmed_club, filename, content, content_type, expect_ok, desc):
    """Budget accepts any file type as long as a file is attached."""
    client = _as(stub_iam, 101, ("gymkhana.budget.view", "gymkhana.budget.create"))
    file = SimpleUploadedFile(filename, content, content_type=content_type)

    res = client.post(
        "/api/v1/gymkhana/budgets/",
        {
            "club_id": confirmed_club.id,
            "amount": "250.00",
            "purpose": f"File type {desc}",
            "description": "d",
            "supporting_file": file,
        },
        format="multipart",
    )
    if expect_ok:
        assert res.status_code == 201, f"[{desc}] expected 201, got {res.status_code}: {res.data}"
    else:
        assert res.status_code == 400, f"[{desc}] expected 400, got {res.status_code}: {res.data}"


# ---------------------------------------------------------------------------
# F. Event report file required (BR-GYM-019)
# ---------------------------------------------------------------------------

def test_event_report_missing_file_rejected(stub_iam, confirmed_club):
    """Event report without report_file must return 400."""
    client = _as(stub_iam, 101, ("gymkhana.report.view", "gymkhana.report.create"))

    res = client.post(
        "/api/v1/gymkhana/reports/",
        {
            "club_id": confirmed_club.id,
            "student_incharge_id": 102,
            "event_name": "No File Event",
            "event_date": "2027-05-01T10:00:00Z",
            "description": "d",
            # No report_file!
        },
        format="multipart",
    )
    assert res.status_code == 400, f"expected 400, got {res.status_code}: {res.data}"


# ---------------------------------------------------------------------------
# G. State machine: Club (BW-GYM-01) illegal transitions
# ---------------------------------------------------------------------------

def test_club_double_confirm_rejected(stub_iam, confirmed_club):
    """Confirming an already-confirmed club should be idempotent or rejected (409 or 200)."""
    client = _as(stub_iam, 999, APPROVE_PERMS, roles=("student_admin",))
    if not UserRef.objects.filter(user_id=999).exists():
        UserRef.objects.create(user_id=999, username="admin999", display_name="A999", kind="student", is_active=True)

    # confirmed_club is already confirmed; try confirming again
    res = client.post(f"/api/v1/gymkhana/clubs/{confirmed_club.id}/confirm/")
    # Should be rejected (409) since it's already confirmed
    assert res.status_code in (409, 400), (
        f"Double confirm: expected 409/400, got {res.status_code}: {res.data}"
    )


CLUB_STATE_MACHINE_CASES = [
    # (initial_status, action_perm, action_url_suffix, expected_code, desc)
    ("open", APPROVE_PERMS, "confirm", 200, "open → confirm: allowed"),
    ("confirmed", APPROVE_PERMS, "confirm", 409, "confirmed → confirm: rejected"),
]


@pytest.mark.parametrize(
    "initial_status,action_perms,action,expected,desc",
    CLUB_STATE_MACHINE_CASES,
    ids=[d for _, _, _, _, d in CLUB_STATE_MACHINE_CASES],
)
def test_club_state_machine_transitions(stub_iam, base_users, initial_status, action_perms, action, expected, desc):
    """Club state machine must enforce valid transitions."""
    if not UserRef.objects.filter(user_id=999).exists():
        UserRef.objects.create(user_id=999, username="admin999", display_name="A999", kind="student", is_active=True)

    club = Club.objects.create(
        name=f"SM Club {desc[:20]}",
        category="sports",
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=201,
        status=initial_status,
    )
    client = _as(stub_iam, 999, action_perms, roles=("student_admin",))
    res = client.post(f"/api/v1/gymkhana/clubs/{club.id}/{action}/")
    assert res.status_code == expected, f"[{desc}] expected {expected}, got {res.status_code}: {res.data}"


# ---------------------------------------------------------------------------
# H. State machine: Membership (BW-GYM-03) illegal transitions
# ---------------------------------------------------------------------------

def test_membership_double_approve_rejected(stub_iam, confirmed_club):
    """Approving an already-confirmed membership should be rejected."""
    # First application
    UserRef.objects.get_or_create(
        user_id=103, defaults={"username": "s103", "display_name": "S103", "kind": "student", "is_active": True}
    )
    student_client = _as(stub_iam, 103, ("gymkhana.membership.view", "gymkhana.membership.create"))
    app_res = student_client.post(
        "/api/v1/gymkhana/memberships/apply/",
        {"club_id": confirmed_club.id, "description": "Join request"},
        format="json",
    )
    assert app_res.status_code == 201
    mem_id = app_res.data["id"]

    # First approval
    head_client = _as(stub_iam, 101, ("gymkhana.membership.view", "gymkhana.membership.approve"))
    approve_res = head_client.post(
        f"/api/v1/gymkhana/memberships/{mem_id}/approve/",
        {"remarks": "Approved"},
        format="json",
    )
    assert approve_res.status_code == 200

    # Second approval attempt on already-confirmed membership → should fail
    res2 = head_client.post(
        f"/api/v1/gymkhana/memberships/{mem_id}/approve/",
        {"remarks": "Double approve"},
        format="json",
    )
    assert res2.status_code in (400, 409), (
        f"Double approve: expected 400/409, got {res2.status_code}: {res2.data}"
    )


# ---------------------------------------------------------------------------
# I. State machine: Poll (BW-GYM-02) — voting on expired poll
# ---------------------------------------------------------------------------

POLL_ILLEGAL_TRANSITIONS = [
    # (poll_status, action, expected_code, desc)
    ("expired", "vote", 400, "vote on expired poll → 400"),
    ("active", "vote", 200, "vote on active poll → 200"),
]


@pytest.mark.parametrize(
    "poll_status,action,expected,desc",
    POLL_ILLEGAL_TRANSITIONS,
    ids=[d for _, _, _, d in POLL_ILLEGAL_TRANSITIONS],
)
def test_poll_state_machine_transitions(stub_iam, confirmed_club, poll_status, action, expected, desc):
    """Poll state transitions: expired poll must reject votes."""
    if poll_status == "expired":
        expires_at = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=1)
    else:
        expires_at = datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=24)

    poll = Poll.objects.create(
        club=confirmed_club,
        created_by_id=101,
        title=f"Poll SM {desc[:20]}",
        expires_at=expires_at,
        status=poll_status,
    )
    PollTargetGroup.objects.create(poll=poll, batch="all", branch="all")
    choice = PollChoice.objects.create(poll=poll, choice_text="Option")

    UserRef.objects.get_or_create(
        user_id=600, defaults={"username": "v600", "display_name": "V600", "kind": "student", "is_active": True}
    )
    voter = _as(stub_iam, 600, ("gymkhana.poll.view", "gymkhana.poll.vote"))
    res = voter.post(
        f"/api/v1/gymkhana/polls/{poll.id}/vote/",
        {"choice_id": choice.id},
        format="json",
    )
    assert res.status_code == expected, f"[{desc}] expected {expected}, got {res.status_code}: {res.data}"


# ---------------------------------------------------------------------------
# J. Membership for unconfirmed club → 400 (BR-GYM-007)
# ---------------------------------------------------------------------------

MEMBERSHIP_CLUB_STATUS_CASES = [
    ("open", False, "open club"),
    ("confirmed", True, "confirmed club"),
]


@pytest.mark.parametrize(
    "club_status,expect_ok,desc",
    MEMBERSHIP_CLUB_STATUS_CASES,
    ids=[d for _, _, d in MEMBERSHIP_CLUB_STATUS_CASES],
)
def test_membership_club_status_validation(stub_iam, base_users, club_status, expect_ok, desc):
    """Membership application only allowed for confirmed clubs (BR-GYM-007)."""
    club = Club.objects.create(
        name=f"Status Club {desc[:15]}",
        category="sports",
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=201,
        status=club_status,
    )
    student_client = _as(stub_iam, 103, ("gymkhana.membership.view", "gymkhana.membership.create"))
    res = student_client.post(
        "/api/v1/gymkhana/memberships/apply/",
        {"club_id": club.id, "description": "Join"},
        format="json",
    )
    if expect_ok:
        assert res.status_code == 201, f"[{desc}] expected 201, got {res.status_code}: {res.data}"
    else:
        assert res.status_code in (400, 409), f"[{desc}] expected 400/409, got {res.status_code}: {res.data}"


# ---------------------------------------------------------------------------
# K. Duplicate membership application (BR-GYM-008)
# ---------------------------------------------------------------------------

def test_duplicate_membership_rejected(stub_iam, confirmed_club):
    """A student cannot submit more than one membership application to the same club."""
    UserRef.objects.get_or_create(
        user_id=103, defaults={"username": "s103", "display_name": "S103", "kind": "student", "is_active": True}
    )
    student_client = _as(stub_iam, 103, ("gymkhana.membership.view", "gymkhana.membership.create"))

    # First application
    res1 = student_client.post(
        "/api/v1/gymkhana/memberships/apply/",
        {"club_id": confirmed_club.id, "description": "First"},
        format="json",
    )
    assert res1.status_code == 201

    # Second application to same club
    res2 = student_client.post(
        "/api/v1/gymkhana/memberships/apply/",
        {"club_id": confirmed_club.id, "description": "Second"},
        format="json",
    )
    assert res2.status_code in (400, 409), (
        f"Duplicate membership: expected 400/409, got {res2.status_code}: {res2.data}"
    )


# ---------------------------------------------------------------------------
# L. Club name required / must not be blank
# ---------------------------------------------------------------------------

CLUB_NAME_CASES = [
    ("Valid Club Name", True, "normal name"),
    ("A", True, "single char name"),
    ("A" * 120, True, "max length name"),
    ("Club & Co.", True, "name with special chars"),
    ("", False, "empty name"),
    ("   ", False, "whitespace only name"),
]


@pytest.mark.parametrize(
    "name,expect_ok,desc",
    CLUB_NAME_CASES,
    ids=[d for _, _, d in CLUB_NAME_CASES],
)
def test_club_name_validation(stub_iam, base_users, name, expect_ok, desc):
    """Club name must be non-empty (serializer validation)."""
    if not UserRef.objects.filter(user_id=999).exists():
        UserRef.objects.create(user_id=999, username="admin999", display_name="A999", kind="student", is_active=True)
    client = _as(stub_iam, 999, CREATE_PERMS)

    res = client.post(
        "/api/v1/gymkhana/clubs/",
        _base_club_payload(name=name),
        format="json",
    )
    if expect_ok:
        assert res.status_code == 201, f"[{desc}] expected 201, got {res.status_code}: {res.data}"
    else:
        assert res.status_code == 400, f"[{desc}] expected 400, got {res.status_code}: {res.data}"


# ---------------------------------------------------------------------------
# M. Domain validation unit tests (pure Python, no HTTP)
# ---------------------------------------------------------------------------

def test_validate_budget_amount_non_negative():
    """Unit test: validate_budget_amount accepts non-negative values."""
    from decimal import Decimal

    from modules.gymkhana.domain.exceptions import DomainValidationError
    from modules.gymkhana.domain.validation import validate_budget_amount

    assert validate_budget_amount("0.00") == Decimal("0.00")
    assert validate_budget_amount("100.50") == Decimal("100.50")
    assert validate_budget_amount(0) == Decimal("0")

    with pytest.raises(DomainValidationError):
        validate_budget_amount("-0.01")

    with pytest.raises(DomainValidationError):
        validate_budget_amount(-1)


def test_validate_poll_choices_distinct():
    """Unit test: validate_poll_choices enforces distinct non-empty list of >= 2."""
    from modules.gymkhana.domain.exceptions import DomainValidationError
    from modules.gymkhana.domain.validation import validate_poll_choices

    # Valid
    result = validate_poll_choices(["A", "B", "C"])
    assert result == ["A", "B", "C"]

    result = validate_poll_choices(["  A  ", " B "])
    assert result == ["A", "B"]

    # Invalid: too few after stripping
    with pytest.raises(DomainValidationError):
        validate_poll_choices(["", ""])

    with pytest.raises(DomainValidationError):
        validate_poll_choices(["A"])

    # Invalid: duplicates
    with pytest.raises(DomainValidationError):
        validate_poll_choices(["X", "X"])


VALIDATE_VENUE_CASES = [
    ("Hall 1", True),
    ("  Hall 1  ", True),   # strips whitespace
    ("", False),
    ("HALL 1", False),
    ("hall 1", False),
    ("Hall1", False),
    ("Conference Room", False),
]


@pytest.mark.parametrize("venue,expect_valid", VALIDATE_VENUE_CASES)
def test_validate_venue_unit(venue, expect_valid):
    """Unit test: validate_venue strips whitespace and checks configured list."""
    from modules.gymkhana.domain.exceptions import DomainValidationError
    from modules.gymkhana.domain.validation import validate_venue

    configured = [
        "Hall 1", "Hall 2", "L-101", "L-102", "Open Air Theatre",
        "SAC Gym", "Football Ground", "Basketball Court",
        "Badminton Court", "Volleyball Court",
    ]

    if expect_valid:
        result = validate_venue(venue, configured)
        assert result == venue.strip()
    else:
        with pytest.raises(DomainValidationError):
            validate_venue(venue, configured)


VALIDATE_BOOKING_TIMES_CASES = [
    ("09:00", "10:00", True),
    ("00:00", "23:59", True),
    ("10:00", "10:00", False),  # equal
    ("10:00", "09:00", False),  # reversed
]


@pytest.mark.parametrize("start_str,end_str,expect_valid", VALIDATE_BOOKING_TIMES_CASES)
def test_validate_booking_times_unit(start_str, end_str, expect_valid):
    """Unit test: validate_booking_times rejects start >= end."""
    import datetime as dt

    from modules.gymkhana.domain.exceptions import DomainValidationError
    from modules.gymkhana.domain.validation import validate_booking_times

    h1, m1 = map(int, start_str.split(":"))
    h2, m2 = map(int, end_str.split(":"))
    start = dt.time(h1, m1)
    end = dt.time(h2, m2)

    if expect_valid:
        validate_booking_times(start, end)  # should not raise
    else:
        with pytest.raises(DomainValidationError):
            validate_booking_times(start, end)


VALIDATE_CATEGORY_CASES = [
    ("technical", "technical"),
    ("SPORTS", "sports"),
    ("  Cultural  ", "cultural"),
]


@pytest.mark.parametrize("raw,expected_norm", VALIDATE_CATEGORY_CASES)
def test_validate_club_category_unit(raw, expected_norm):
    """Unit test: validate_club_category normalizes to lowercase."""
    from modules.gymkhana.domain.validation import validate_club_category

    result = validate_club_category(raw)
    assert result == expected_norm


VALIDATE_LEADERS_CASES = [
    (101, 102, True),
    (101, 101, False),
    (200, 200, False),
]


@pytest.mark.parametrize("coord,co,expect_valid", VALIDATE_LEADERS_CASES)
def test_validate_distinct_leaders_unit(coord, co, expect_valid):
    """Unit test: validate_distinct_leaders rejects same uid."""
    from modules.gymkhana.domain.exceptions import DomainValidationError
    from modules.gymkhana.domain.validation import validate_distinct_leaders

    if expect_valid:
        validate_distinct_leaders(coord, co)
    else:
        with pytest.raises(DomainValidationError):
            validate_distinct_leaders(coord, co)


# ---------------------------------------------------------------------------
# N. Budget: non-head tries to submit → 403
# ---------------------------------------------------------------------------

NON_HEAD_BUDGET_UIDS = [103, 104, 500]


@pytest.mark.parametrize("uid", NON_HEAD_BUDGET_UIDS)
def test_non_head_budget_submission_rejected(stub_iam, confirmed_club, uid):
    """Non-club-head student trying to submit budget request must get 403."""
    if not UserRef.objects.filter(user_id=uid).exists():
        UserRef.objects.create(
            user_id=uid, username=f"u{uid}", display_name=f"U{uid}", kind="student", is_active=True
        )
    client = _as(stub_iam, uid, ("gymkhana.budget.view", "gymkhana.budget.create"))
    dummy_file = SimpleUploadedFile("b.pdf", b"data", content_type="application/pdf")

    res = client.post(
        "/api/v1/gymkhana/budgets/",
        {
            "club_id": confirmed_club.id,
            "amount": "1000.00",
            "purpose": "Non-head test",
            "description": "d",
            "supporting_file": dummy_file,
        },
        format="multipart",
    )
    assert res.status_code == 403, f"uid={uid}: expected 403, got {res.status_code}: {res.data}"
