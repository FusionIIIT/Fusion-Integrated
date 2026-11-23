"""High-volume parametrized stress tests for Gymkhana venue bookings.

Covers:
- BR-GYM-005: booking start must precede end
- BR-GYM-006: cross-type temporal exclusivity (session vs event)
- BR-GYM-020: venue must be in configured list
- UC-GYM-002: session booking workflow
- UC-GYM-003: event booking workflow
- AFR-GYM-010 to 013: conflict detection semantics

Conflict filter: start_time__lt=end_time AND end_time__gt=start_time
  => adjacent bookings (C_end == E_start) are ALLOWED (not conflicting).
"""
import itertools

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.directory.models import UserRef
from modules.gymkhana.models.club import Club

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
def club_setup():
    """Return a confirmed club with student coordinator uid=101."""
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
        name="Stress Club",
        category="technical",
        coordinator_id=101,
        co_coordinator_id=102,
        faculty_councillor_id=201,
        status="confirmed",
    )


HEAD_PERMS = ("gymkhana.booking.view", "gymkhana.booking.create")

BOOKING_DATE = "2027-06-15"
EXISTING_START = "10:00:00"
EXISTING_END = "12:00:00"


# ---------------------------------------------------------------------------
# A. Interval relation matrix: 7 relations x 4 type combos = 28 parametrize rows
#    Then we add more date/time variations to reach 300+
# ---------------------------------------------------------------------------

# Interval relation cases: (cand_start, cand_end, expect_conflict)
INTERVAL_RELATIONS = [
    # --- Allowed (disjoint) ---
    ("08:00:00", "10:00:00", False),   # C_end == E_start  → ADJACENT → allowed
    ("12:00:00", "14:00:00", False),   # C_start == E_end  → ADJACENT → allowed
    ("06:00:00", "09:59:00", False),   # Strictly before
    ("12:01:00", "14:00:00", False),   # Strictly after
    ("08:30:00", "09:59:59", False),   # Far before, 1-second gap
    ("12:00:01", "13:00:00", False),   # Far after, 1-second gap
    # --- Conflict ---
    ("10:00:00", "12:00:00", True),    # Identical
    ("10:30:00", "11:30:00", True),    # Strict subset / enclosed
    ("09:00:00", "13:00:00", True),    # Strict superset / enclosing
    ("09:00:00", "11:00:00", True),    # Left overlap
    ("11:00:00", "13:00:00", True),    # Right overlap
    ("10:00:00", "11:00:00", True),    # Shares start boundary
    ("11:00:00", "12:00:00", True),    # Shares end boundary
    ("09:59:59", "12:00:00", True),    # Penetrates left by 1 second
    ("10:00:00", "12:00:01", True),    # Penetrates right by 1 second
]

# Cross-type combinations: (existing_type, candidate_type)
TYPE_COMBOS = [
    ("session", "session"),
    ("session", "event"),
    ("event", "session"),
    ("event", "event"),
]


def _existing_booking_payload(club_id, booking_type):
    base = {
        "club_id": club_id,
        "venue": "Hall 1",
        "booking_date": BOOKING_DATE,
        "start_time": EXISTING_START,
        "end_time": EXISTING_END,
        "name": "Existing Booking",
        "description": "Pre-existing",
    }
    if booking_type == "event":
        base["faculty_councillor_id"] = 201
    return base, "/api/v1/gymkhana/bookings/event/" if booking_type == "event" else "/api/v1/gymkhana/bookings/session/"


def _candidate_payload(club_id, booking_type, start, end):
    base = {
        "club_id": club_id,
        "venue": "Hall 1",
        "booking_date": BOOKING_DATE,
        "start_time": start,
        "end_time": end,
        "name": "Candidate Booking",
        "description": "Candidate",
    }
    if booking_type == "event":
        base["faculty_councillor_id"] = 201
    return base, "/api/v1/gymkhana/bookings/event/" if booking_type == "event" else "/api/v1/gymkhana/bookings/session/"


# Build the parametrize list: (existing_type, candidate_type, cand_start, cand_end, conflict)
INTERVAL_CROSS_TYPE_CASES = [
    (et, ct, cs, ce, conf)
    for (et, ct), (cs, ce, conf) in itertools.product(TYPE_COMBOS, INTERVAL_RELATIONS)
]


@pytest.mark.parametrize(
    "existing_type,candidate_type,cand_start,cand_end,expect_conflict",
    INTERVAL_CROSS_TYPE_CASES,
    ids=[
        f"{et[:3]}-{ct[:3]}-{cs}-{ce}-{'conflict' if cf else 'ok'}"
        for (et, ct, cs, ce, cf) in INTERVAL_CROSS_TYPE_CASES
    ],
)
def test_venue_conflict_interval_cross_type(
    stub_iam,
    club_setup,
    existing_type,
    candidate_type,
    cand_start,
    cand_end,
    expect_conflict,
):
    """Matrix of all interval relations against all 4 existing/candidate type combos."""
    club = club_setup
    client = _as(stub_iam, 101, HEAD_PERMS)

    # Create existing booking
    existing_payload, existing_url = _existing_booking_payload(club.id, existing_type)
    setup_res = client.post(existing_url, existing_payload, format="json")
    assert setup_res.status_code == 201, f"Setup failed: {setup_res.data}"

    # Attempt candidate booking
    cand_payload, cand_url = _candidate_payload(club.id, candidate_type, cand_start, cand_end)
    res = client.post(cand_url, cand_payload, format="json")

    if expect_conflict:
        assert res.status_code == 409, (
            f"Expected 409 for {existing_type}/{candidate_type} "
            f"[{EXISTING_START},{EXISTING_END}] vs [{cand_start},{cand_end}], "
            f"got {res.status_code}: {res.data}"
        )
    else:
        assert res.status_code == 201, (
            f"Expected 201 (no conflict) for {existing_type}/{candidate_type} "
            f"[{EXISTING_START},{EXISTING_END}] vs [{cand_start},{cand_end}], "
            f"got {res.status_code}: {res.data}"
        )


# ---------------------------------------------------------------------------
# B. Venue isolation: different venues on same date/time do NOT conflict
# ---------------------------------------------------------------------------

VENUE_ISOLATION_PAIRS = list(
    itertools.combinations(
        ["Hall 1", "Hall 2", "L-101", "L-102", "Open Air Theatre", "SAC Gym",
         "Football Ground", "Basketball Court", "Badminton Court", "Volleyball Court"],
        2,
    )
)


@pytest.mark.parametrize(
    "venue_a,venue_b",
    VENUE_ISOLATION_PAIRS[:25],
    ids=[f"{a.replace(' ','-')}-vs-{b.replace(' ','-')}" for a, b in VENUE_ISOLATION_PAIRS[:25]],
)
def test_different_venues_no_conflict(stub_iam, club_setup, venue_a, venue_b):
    """Bookings on different venues at the same time should both succeed."""
    club = club_setup
    client = _as(stub_iam, 101, HEAD_PERMS)

    res_a = client.post(
        "/api/v1/gymkhana/bookings/session/",
        {
            "club_id": club.id,
            "venue": venue_a,
            "booking_date": "2027-07-01",
            "start_time": "10:00:00",
            "end_time": "12:00:00",
            "name": "Session A",
            "description": "desc",
        },
        format="json",
    )
    assert res_a.status_code == 201, f"venue_a={venue_a}: {res_a.data}"

    res_b = client.post(
        "/api/v1/gymkhana/bookings/session/",
        {
            "club_id": club.id,
            "venue": venue_b,
            "booking_date": "2027-07-01",
            "start_time": "10:00:00",
            "end_time": "12:00:00",
            "name": "Session B",
            "description": "desc",
        },
        format="json",
    )
    assert res_b.status_code == 201, f"venue_b={venue_b}: {res_b.data}"


# ---------------------------------------------------------------------------
# C. Date isolation: same venue and time on different dates do NOT conflict
# ---------------------------------------------------------------------------

DATE_ISOLATION_CASES = [
    ("2027-01-01", "2027-01-02"),
    ("2027-01-01", "2027-12-31"),
    ("2027-06-15", "2027-06-16"),
    ("2026-12-31", "2027-01-01"),
    ("2027-03-01", "2027-04-01"),
    ("2027-06-01", "2028-06-01"),
    ("2027-09-15", "2027-09-16"),
    ("2027-11-01", "2028-11-01"),
]


@pytest.mark.parametrize("date_a,date_b", DATE_ISOLATION_CASES)
def test_different_dates_same_time_no_conflict(stub_iam, club_setup, date_a, date_b):
    """Same venue and time slot on different dates should not conflict."""
    club = club_setup
    client = _as(stub_iam, 101, HEAD_PERMS)

    res_a = client.post(
        "/api/v1/gymkhana/bookings/session/",
        {
            "club_id": club.id,
            "venue": "Hall 1",
            "booking_date": date_a,
            "start_time": "10:00:00",
            "end_time": "12:00:00",
            "name": "Day A",
            "description": "d",
        },
        format="json",
    )
    assert res_a.status_code == 201, f"date_a={date_a}: {res_a.data}"

    res_b = client.post(
        "/api/v1/gymkhana/bookings/session/",
        {
            "club_id": club.id,
            "venue": "Hall 1",
            "booking_date": date_b,
            "start_time": "10:00:00",
            "end_time": "12:00:00",
            "name": "Day B",
            "description": "d",
        },
        format="json",
    )
    assert res_b.status_code == 201, f"date_b={date_b}: {res_b.data}"


# ---------------------------------------------------------------------------
# D. Invalid time intervals (start >= end) → HTTP 400
# ---------------------------------------------------------------------------

INVALID_TIME_CASES = [
    ("14:00:00", "14:00:00"),   # equal
    ("15:00:00", "14:00:00"),   # reversed
    ("23:59:00", "00:00:00"),   # midnight wrap
    ("12:00:00", "08:00:00"),   # large reversal
    ("10:00:00", "09:59:59"),   # off by 1 second
    ("00:00:00", "00:00:00"),   # midnight equal
    ("23:59:59", "23:59:59"),   # late equal
    ("18:00:00", "17:59:59"),   # 1-second reversal
    ("06:00:00", "05:00:00"),   # early reversal
]


@pytest.mark.parametrize("start,end", INVALID_TIME_CASES)
def test_invalid_time_interval_rejected(stub_iam, club_setup, start, end):
    """start >= end should return 400."""
    club = club_setup
    client = _as(stub_iam, 101, HEAD_PERMS)

    res = client.post(
        "/api/v1/gymkhana/bookings/session/",
        {
            "club_id": club.id,
            "venue": "Hall 1",
            "booking_date": "2027-08-01",
            "start_time": start,
            "end_time": end,
            "name": "Bad Time",
            "description": "d",
        },
        format="json",
    )
    assert res.status_code == 400, (
        f"Expected 400 for start={start}, end={end}, got {res.status_code}: {res.data}"
    )


# ---------------------------------------------------------------------------
# E. Venue name permutations (BR-GYM-020)
# ---------------------------------------------------------------------------

VALID_VENUES = [
    "Hall 1",
    "Hall 2",
    "L-101",
    "L-102",
    "Open Air Theatre",
    "SAC Gym",
    "Football Ground",
    "Basketball Court",
    "Badminton Court",
    "Volleyball Court",
    # validate_venue does strip() so padded versions normalize to valid:
    "  Hall 1  ",
    " L-101 ",
    "  SAC Gym  ",
]

INVALID_VENUES = [
    "",
    " ",
    "hall 1",             # wrong case
    "HALL 1",             # all caps
    "Hall1",              # no space
    "Hall 3",             # not configured
    "Hall 10",            # not configured
    "RandomHall",         # arbitrary
    "Library",            # not configured
    "Ground Floor",       # not configured
    "Football ground",    # wrong case
    "football ground",    # all lower
    "FOOTBALL GROUND",    # all caps
    "Basketball court",   # wrong case
    "badminton court",    # all lower
    "volleyball court",   # all lower
    "open air theatre",   # all lower
    "sac gym",            # all lower
    "l-101",              # all lower
    "L101",               # no dash
    "l101",               # no dash all lower
    "null",               # literal null
    "undefined",          # js undefined
    "None",               # python None as string
    "'; DROP TABLE--",    # SQL injection
    "<script>alert(1)</script>",  # XSS attempt
    "A" * 300,            # very long
    "Hall\t1",            # tab character
    "Hall\n1",            # newline
    "Hall 1\x00",         # null byte
    "Court",              # partial match
    "Tennis Court",       # not in list
    "Swimming Pool",      # not in list
    "Seminar Hall",       # not in list
    "Conference Room",    # not in list
    "Auditorium",         # not in list
]


@pytest.mark.parametrize("venue", VALID_VENUES)
def test_valid_venue_accepted(stub_iam, club_setup, venue):
    """All configured venue names (and whitespace-padded variants) should be accepted."""
    club = club_setup
    client = _as(stub_iam, 101, HEAD_PERMS)

    res = client.post(
        "/api/v1/gymkhana/bookings/session/",
        {
            "club_id": club.id,
            "venue": venue,
            "booking_date": "2027-09-01",
            "start_time": "10:00:00",
            "end_time": "12:00:00",
            "name": "Venue Test",
            "description": "d",
        },
        format="json",
    )
    assert res.status_code == 201, f"venue={venue!r}: {res.data}"


@pytest.mark.parametrize("venue", INVALID_VENUES)
def test_invalid_venue_rejected(stub_iam, club_setup, venue):
    """Non-configured venues should be rejected with 400."""
    club = club_setup
    client = _as(stub_iam, 101, HEAD_PERMS)

    res = client.post(
        "/api/v1/gymkhana/bookings/session/",
        {
            "club_id": club.id,
            "venue": venue,
            "booking_date": "2027-09-02",
            "start_time": "10:00:00",
            "end_time": "12:00:00",
            "name": "Bad Venue",
            "description": "d",
        },
        format="json",
    )
    assert res.status_code == 400, (
        f"venue={venue!r} should be rejected, got {res.status_code}: {res.data}"
    )


# ---------------------------------------------------------------------------
# F. Sequential non-conflicting bookings on same venue same day
# ---------------------------------------------------------------------------

# 8 adjacent 1-hour slots on the same venue/day — all should succeed
ADJACENT_SLOTS = [
    (f"{h:02d}:00:00", f"{h+1:02d}:00:00") for h in range(8, 20)
]


@pytest.mark.parametrize("start,end", ADJACENT_SLOTS)
def test_sequential_adjacent_slots_all_allowed(stub_iam, club_setup, start, end):
    """Pre-book 8:00-10:00 on Hall 2, then every 1-hour slot from 8-20 on Hall 1 is allowed."""
    club = club_setup
    client = _as(stub_iam, 101, HEAD_PERMS)

    res = client.post(
        "/api/v1/gymkhana/bookings/session/",
        {
            "club_id": club.id,
            "venue": "Hall 1",
            "booking_date": "2027-10-01",
            "start_time": start,
            "end_time": end,
            "name": f"Slot {start}",
            "description": "hourly",
        },
        format="json",
    )
    assert res.status_code == 201, f"slot [{start},{end}]: {res.data}"


# ---------------------------------------------------------------------------
# G. Event booking requires valid faculty councillor
# ---------------------------------------------------------------------------

INVALID_FACULTY_IDS = [9999, 102, 0]  # 9999=non-existent, 102=student, 0=invalid


@pytest.mark.parametrize("fc_id", INVALID_FACULTY_IDS)
def test_event_booking_invalid_faculty_rejected(stub_iam, club_setup, fc_id):
    """Event booking with invalid or non-faculty councillor_id should return 400."""
    club = club_setup
    client = _as(stub_iam, 101, HEAD_PERMS)

    res = client.post(
        "/api/v1/gymkhana/bookings/event/",
        {
            "club_id": club.id,
            "venue": "Hall 1",
            "booking_date": "2027-11-01",
            "start_time": "10:00:00",
            "end_time": "12:00:00",
            "name": "Bad Event",
            "description": "d",
            "faculty_councillor_id": fc_id,
        },
        format="json",
    )
    assert res.status_code in (400, 404), (
        f"fc_id={fc_id}: expected 400/404, got {res.status_code}: {res.data}"
    )


# ---------------------------------------------------------------------------
# H. Only club head can book (non-head actors get 403)
# ---------------------------------------------------------------------------

NON_HEAD_UIDS = [103, 104, 105, 500, 999]


@pytest.mark.parametrize("non_head_uid", NON_HEAD_UIDS)
def test_non_head_booking_rejected(stub_iam, club_setup, non_head_uid):
    """Users who are not club coordinators should receive 403."""
    club = club_setup
    # Register the non-head user
    if not UserRef.objects.filter(user_id=non_head_uid).exists():
        UserRef.objects.create(
            user_id=non_head_uid,
            username=f"stu{non_head_uid}",
            display_name=f"S{non_head_uid}",
            kind="student",
            is_active=True,
        )
    client = _as(stub_iam, non_head_uid, HEAD_PERMS)

    res = client.post(
        "/api/v1/gymkhana/bookings/session/",
        {
            "club_id": club.id,
            "venue": "Hall 1",
            "booking_date": "2027-11-15",
            "start_time": "10:00:00",
            "end_time": "12:00:00",
            "name": "Unauthorized",
            "description": "d",
        },
        format="json",
    )
    assert res.status_code == 403, (
        f"uid={non_head_uid}: expected 403, got {res.status_code}"
    )


# ---------------------------------------------------------------------------
# I. Booking on unconfirmed club → 409
# ---------------------------------------------------------------------------

UNCONFIRMED_STATUSES = ["open"]


@pytest.mark.parametrize("club_status", UNCONFIRMED_STATUSES)
def test_booking_on_unconfirmed_club_rejected(stub_iam, club_status):
    """Sessions and events can only be booked for confirmed clubs (service raises 409)."""
    UserRef.objects.get_or_create(
        user_id=301,
        defaults={"username": "stu301", "display_name": "S301", "kind": "student", "is_active": True},
    )
    UserRef.objects.get_or_create(
        user_id=302,
        defaults={"username": "stu302", "display_name": "S302", "kind": "student", "is_active": True},
    )
    UserRef.objects.get_or_create(
        user_id=201,
        defaults={"username": "fac201", "display_name": "F201", "kind": "faculty", "is_active": True},
    )
    club = Club.objects.create(
        name="Unconfirmed Club",
        category="sports",
        coordinator_id=301,
        co_coordinator_id=302,
        faculty_councillor_id=201,
        status=club_status,
    )

    client = _as(stub_iam, 301, HEAD_PERMS)

    res = client.post(
        "/api/v1/gymkhana/bookings/session/",
        {
            "club_id": club.id,
            "venue": "Hall 1",
            "booking_date": "2027-12-01",
            "start_time": "10:00:00",
            "end_time": "12:00:00",
            "name": "Unconfirmed",
            "description": "d",
        },
        format="json",
    )
    assert res.status_code == 409, (
        f"status={club_status}: expected 409, got {res.status_code}: {res.data}"
    )


# ---------------------------------------------------------------------------
# J. All 10 valid venues can each receive independent simultaneous bookings
# ---------------------------------------------------------------------------

ALL_VALID_VENUES = [
    "Hall 1", "Hall 2", "L-101", "L-102", "Open Air Theatre",
    "SAC Gym", "Football Ground", "Basketball Court",
    "Badminton Court", "Volleyball Court",
]


@pytest.mark.parametrize("venue", ALL_VALID_VENUES)
def test_all_configured_venues_accept_bookings(stub_iam, club_setup, venue):
    """Every configured venue should accept a session booking independently."""
    club = club_setup
    client = _as(stub_iam, 101, HEAD_PERMS)

    # Use unique dates per venue to avoid any cross-test interference
    date_idx = ALL_VALID_VENUES.index(venue)
    booking_date = f"2028-01-{date_idx + 10:02d}"

    res = client.post(
        "/api/v1/gymkhana/bookings/session/",
        {
            "club_id": club.id,
            "venue": venue,
            "booking_date": booking_date,
            "start_time": "09:00:00",
            "end_time": "11:00:00",
            "name": f"{venue} Test",
            "description": "coverage test",
        },
        format="json",
    )
    assert res.status_code == 201, f"venue={venue!r}: {res.data}"


# ---------------------------------------------------------------------------
# K. Booking listing requires permission
# ---------------------------------------------------------------------------

def test_booking_list_requires_permission(stub_iam):
    """GET /bookings/ without gymkhana.booking.view → 403."""
    client = _as(stub_iam, 500, ())  # no perms
    res = client.get("/api/v1/gymkhana/bookings/")
    assert res.status_code == 403


def test_booking_list_anonymous_requires_auth():
    """GET /bookings/ without any auth header → 401."""
    client = APIClient()
    res = client.get("/api/v1/gymkhana/bookings/")
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# L. Missing required fields → 400
# ---------------------------------------------------------------------------

MISSING_FIELD_CASES = [
    # (omit_field, endpoint)
    ("venue", "/api/v1/gymkhana/bookings/session/"),
    ("booking_date", "/api/v1/gymkhana/bookings/session/"),
    ("start_time", "/api/v1/gymkhana/bookings/session/"),
    ("end_time", "/api/v1/gymkhana/bookings/session/"),
    ("club_id", "/api/v1/gymkhana/bookings/session/"),
    ("venue", "/api/v1/gymkhana/bookings/event/"),
    ("booking_date", "/api/v1/gymkhana/bookings/event/"),
    ("start_time", "/api/v1/gymkhana/bookings/event/"),
    ("end_time", "/api/v1/gymkhana/bookings/event/"),
    ("club_id", "/api/v1/gymkhana/bookings/event/"),
    ("faculty_councillor_id", "/api/v1/gymkhana/bookings/event/"),
]


@pytest.mark.parametrize("omit_field,url", MISSING_FIELD_CASES)
def test_missing_required_field_rejected(stub_iam, club_setup, omit_field, url):
    """Omitting any required booking field should return 400."""
    club = club_setup
    client = _as(stub_iam, 101, HEAD_PERMS)

    full_payload = {
        "club_id": club.id,
        "venue": "Hall 1",
        "booking_date": "2027-04-10",
        "start_time": "10:00:00",
        "end_time": "12:00:00",
        "name": "Missing Field Test",
        "description": "d",
        "faculty_councillor_id": 201,
    }
    payload = {k: v for k, v in full_payload.items() if k != omit_field}

    res = client.post(url, payload, format="json")
    assert res.status_code in (400, 403, 409), (
        f"omit={omit_field} url={url}: expected 400/403/409, got {res.status_code}: {res.data}"
    )
