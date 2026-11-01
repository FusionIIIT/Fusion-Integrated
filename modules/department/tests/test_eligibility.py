"""Pure-Python tests for Department domain eligibility (OA-BR-61)."""
import datetime
from modules.department.domain.eligibility import (
    is_pg_student,
    check_seminar_eligibility,
    validate_seminar_request,
    validate_scheduling_parameters,
)


def test_is_pg_student_recognizes_pg_programmes():
    assert is_pg_student("M.Tech") is True
    assert is_pg_student("MTech") is True
    assert is_pg_student("Ph.D.") is True
    assert is_pg_student("PhD") is True
    assert is_pg_student("M.Des") is True
    assert is_pg_student("PG") is True
    assert is_pg_student("Postgraduate") is True


def test_is_pg_student_rejects_ug_programmes():
    assert is_pg_student("B.Tech") is False
    assert is_pg_student("BTech") is False
    assert is_pg_student("B.Des") is False
    assert is_pg_student("") is False
    assert is_pg_student(None) is False


def test_check_seminar_eligibility_oa_br_61():
    # Eligible PG student
    res = check_seminar_eligibility("M.Tech CSE")
    assert res.allowed is True
    assert "Eligible" in res.reason

    # Ineligible UG student
    res = check_seminar_eligibility("B.Tech ECE")
    assert res.allowed is False
    assert "OA-BR-61" in res.reason


def test_validate_seminar_request_valid():
    today = datetime.date(2026, 11, 1)
    future = datetime.date(2026, 11, 15)
    valid, msg = validate_seminar_request(
        topic="Deep Learning in Medical Imaging",
        abstract="This seminar presents novel transformer architectures for MRI segmentation.",
        preferred_date=future,
        current_date=today,
    )
    assert valid is True
    assert "Valid" in msg


def test_validate_seminar_request_empty_topic():
    valid, msg = validate_seminar_request(topic="", abstract="Valid abstract")
    assert valid is False
    assert "topic or title is required" in msg


def test_validate_seminar_request_short_topic():
    valid, msg = validate_seminar_request(topic="AI", abstract="Valid abstract")
    assert valid is False
    assert "at least 5 characters" in msg


def test_validate_seminar_request_empty_abstract():
    valid, msg = validate_seminar_request(topic="Valid Topic Name", abstract="")
    assert valid is False
    assert "abstract or description is required" in msg


def test_validate_seminar_request_past_date():
    today = datetime.date(2026, 11, 1)
    past = datetime.date(2026, 10, 15)
    valid, msg = validate_seminar_request(
        topic="Valid Topic Name",
        abstract="Valid abstract description",
        preferred_date=past,
        current_date=today,
    )
    assert valid is False
    assert "cannot be in the past" in msg


def test_validate_scheduling_parameters_valid():
    today = datetime.date(2026, 11, 1)
    sem_date = datetime.date(2026, 11, 10)
    valid, msg = validate_scheduling_parameters(
        scheduled_date=sem_date,
        start_time=datetime.time(14, 0),
        end_time=datetime.time(15, 30),
        venue="Seminar Hall 1",
        current_date=today,
    )
    assert valid is True
    assert "Valid" in msg


def test_validate_scheduling_parameters_past_date():
    today = datetime.date(2026, 11, 1)
    past = datetime.date(2026, 10, 20)
    valid, msg = validate_scheduling_parameters(
        scheduled_date=past,
        start_time=datetime.time(14, 0),
        end_time=datetime.time(15, 0),
        venue="Room 101",
        current_date=today,
    )
    assert valid is False
    assert "cannot be in the past" in msg


def test_validate_scheduling_parameters_invalid_time_order():
    today = datetime.date(2026, 11, 1)
    sem_date = datetime.date(2026, 11, 10)
    valid, msg = validate_scheduling_parameters(
        scheduled_date=sem_date,
        start_time=datetime.time(16, 0),
        end_time=datetime.time(15, 0),
        venue="Room 101",
        current_date=today,
    )
    assert valid is False
    assert "start time must be before end time" in msg


def test_validate_scheduling_parameters_missing_venue():
    today = datetime.date(2026, 11, 1)
    sem_date = datetime.date(2026, 11, 10)
    valid, msg = validate_scheduling_parameters(
        scheduled_date=sem_date,
        start_time=datetime.time(14, 0),
        end_time=datetime.time(15, 0),
        venue="   ",
        current_date=today,
    )
    assert valid is False
    assert "Venue is required" in msg
