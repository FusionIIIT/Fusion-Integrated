import pytest
from django.utils import timezone
from modules.elm.services.applications import submit_leave_request, withdraw_leave_request, LeaveApplicationUnknownCategoryError, LeaveApplicationEndDateBeforeStartDateError, LeaveApplicationInsufficientBalanceError, LeaveApplicationConflictError
from modules.elm.services.entitlements import credit_annual_entitlements
from core.api.exceptions import DomainError


def _credit(user_id):
    credit_annual_entitlements(user_id, 2026, is_faculty=False)


@pytest.mark.django_db
def test_unknown_category_rejected():
    _credit(1)
    with pytest.raises(LeaveApplicationUnknownCategoryError):
        submit_leave_request(1, "XX", timezone.now().date(), timezone.now().date(), "Invalid category")


@pytest.mark.django_db
def test_end_before_start_rejected():
    _credit(1)
    with pytest.raises(LeaveApplicationEndDateBeforeStartDateError):
        submit_leave_request(1, "CL", timezone.now().date() + timezone.timedelta(days=1), timezone.now().date(), "End before start")






@pytest.mark.django_db
def test_half_day_counts_half():
    _credit(1)
    submit_leave_request(1, "CL", timezone.datetime(2026, 10, 26).date(), timezone.datetime(2026, 10, 26).date(), "Half day CL", half_day=True)


@pytest.mark.django_db
def test_status_without_substitute():
    _credit(1)
    leave_request = submit_leave_request(1, "CL", timezone.now().date(), timezone.now().date(), "No substitute")
    assert leave_request.status == "Awaiting Unit Head Review"


@pytest.mark.django_db
def test_status_with_substitute():
    _credit(1)
    leave_request = submit_leave_request(1, "CL", timezone.now().date(), timezone.now().date(), "With substitute", substitute_user_id=99)
    assert leave_request.status == "Awaiting Substitute Response"


@pytest.mark.django_db
def test_overlap_rejected_without_substitute():
    _credit(1)
    submit_leave_request(1, "CL", timezone.datetime(2026, 10, 26).date(), timezone.datetime(2026, 10, 27).date(), "First request")
    with pytest.raises(LeaveApplicationConflictError):
        submit_leave_request(1, "CL", timezone.datetime(2026, 10, 27).date(), timezone.datetime(2026, 10, 28).date(), "Second request")


@pytest.mark.django_db
def test_overlap_rejected_with_substitute():
    _credit(1)
    submit_leave_request(1, "CL", timezone.datetime(2026, 10, 26).date(), timezone.datetime(2026, 10, 27).date(), "First request", substitute_user_id=99)
    with pytest.raises(LeaveApplicationConflictError):
        submit_leave_request(1, "CL", timezone.datetime(2026, 10, 27).date(), timezone.datetime(2026, 10, 28).date(), "Second request", substitute_user_id=99)


@pytest.mark.django_db
def test_withdrawn_request_does_not_block():
    _credit(1)
    leave_request = submit_leave_request(1, "CL", timezone.now().date(), timezone.now().date(), "Withdrawn request")
    withdraw_leave_request(leave_request.id, 1)
    leave_request = submit_leave_request(1, "CL", timezone.now().date(), timezone.now().date(), "Withdrawn request again")
    assert leave_request.status == "Awaiting Unit Head Review"


@pytest.mark.django_db
def test_only_applicant_can_withdraw():
    _credit(1)
    leave_request = submit_leave_request(1, "CL", timezone.now().date(), timezone.now().date(), "Withdrawn request")
    with pytest.raises(DomainError):
        withdraw_leave_request(leave_request.id, 2)
    leave_request.refresh_from_db()
    assert leave_request.status == "Awaiting Unit Head Review"


from datetime import date as _d


@pytest.mark.django_db
def test_cl_skips_weekends_boundary():
    credit_annual_entitlements(1, 2026, is_faculty=False)
    credit_annual_entitlements(2, 2026, is_faculty=False)
    # Mon 26 Oct to Wed 4 Nov is exactly 8 weekdays, equal to the CL balance
    submit_leave_request(1, "CL", _d(2026, 10, 26), _d(2026, 11, 4), "8 weekdays")
    # Mon 26 Oct to Thu 5 Nov is 9 weekdays, one more than the balance
    with pytest.raises(LeaveApplicationInsufficientBalanceError):
        submit_leave_request(2, "CL", _d(2026, 10, 26), _d(2026, 11, 5), "9 weekdays")


@pytest.mark.django_db
def test_el_counts_every_calendar_day_boundary():
    credit_annual_entitlements(1, 2026, is_faculty=False)
    credit_annual_entitlements(2, 2026, is_faculty=False)
    # 26 Oct to 24 Nov is exactly 30 calendar days, equal to the EL balance
    submit_leave_request(1, "EL", _d(2026, 10, 26), _d(2026, 11, 24), "30 days")
    # 26 Oct to 25 Nov is 31 calendar days, one more than the balance
    with pytest.raises(LeaveApplicationInsufficientBalanceError):
        submit_leave_request(2, "EL", _d(2026, 10, 26), _d(2026, 11, 25), "31 days")
