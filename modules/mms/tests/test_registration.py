"""Registration (MMS-UC-002..004) and deregistration (MMS-UC-005, 006, 027).

Workflows: BW-MMS-01/02, CW-MMS-01 and BW-MMS-03/04, CW-MMS-02. BR-MMS-008..013.
"""
import pytest

from core.api.exceptions import BadRequestError, ConflictError, PermissionDeniedError
from modules.mms.models import MessDeregistration, MessRegistration, MessRegistrationWindow
from modules.mms.services import operations as svc
from modules.mms.tests.factories import (
    DeregistrationFactory,
    RegistrationFactory,
    RegistrationWindowFactory,
)
from modules.mms.tests.helpers import (
    CARETAKER_ID,
    OTHER_STUDENT_ID,
    STUDENT_ID,
    TODAY,
    admin,
    caretaker,
    days_from_today,
    student,
    warden,
)

pytestmark = pytest.mark.django_db


# =============================================================================
# Registration window — BR-MMS-008
# =============================================================================
def _open(**kw):
    kw.setdefault("start_date", TODAY)
    kw.setdefault("end_date", days_from_today(14))
    return svc.open_registration_window(
        actor=caretaker(), academic_year="2026-27", semester="Autumn", **kw)


def test_br008_caretaker_opens_a_window():
    w = _open()
    assert (w.status, w.opened_by_user_id) == ("open", CARETAKER_ID)


@pytest.mark.parametrize("who", [student, warden, admin])
def test_br008_nobody_but_the_caretaker_opens_a_window(who):
    with pytest.raises(PermissionDeniedError):
        svc.open_registration_window(actor=who(), academic_year="x", semester="y",
                                     start_date=TODAY, end_date=days_from_today(1))
    assert MessRegistrationWindow.objects.count() == 0


def test_window_cannot_end_before_it_starts():
    with pytest.raises(BadRequestError):
        _open(start_date=days_from_today(5), end_date=days_from_today(1))


def test_opening_a_new_window_closes_the_previous_one():
    old = _open()
    new = _open()
    old.refresh_from_db()
    assert (old.status, new.status) == ("closed", "open")
    assert MessRegistrationWindow.objects.filter(status="open").count() == 1


# =============================================================================
# Submit registration — BR-MMS-009, BW-MMS-01 step 2
# =============================================================================
def test_br009_student_submits_while_a_window_is_open(sent):
    w = RegistrationWindowFactory()
    r = svc.submit_registration_request(actor=student(), reason="hostel")
    assert (r.status, r.user_id, r.window_id) == ("submitted", STUDENT_ID, w.pk)
    assert [n.recipient_user_id for n in sent("registration_submitted")] == [STUDENT_ID]


def test_br009_no_window_means_no_registration():
    with pytest.raises(ConflictError):
        svc.submit_registration_request(actor=student())
    assert MessRegistration.objects.count() == 0


def test_br009_a_closed_window_does_not_count():
    RegistrationWindowFactory(closed=True)
    with pytest.raises(ConflictError):
        svc.submit_registration_request(actor=student())


def test_br009_naming_a_closed_window_explicitly_is_refused():
    w = RegistrationWindowFactory(closed=True)
    RegistrationWindowFactory()            # an open one exists, but it is not the one asked for
    with pytest.raises(ConflictError):
        svc.submit_registration_request(actor=student(), window_id=w.pk)


def test_br009_naming_an_unknown_window_is_a_conflict_not_a_crash():
    with pytest.raises(ConflictError):
        svc.submit_registration_request(actor=student(), window_id=999_999)


def test_submitting_against_a_specific_open_window():
    RegistrationWindowFactory()
    target = RegistrationWindowFactory()
    r = svc.submit_registration_request(actor=student(), window_id=target.pk)
    assert r.window_id == target.pk


@pytest.mark.parametrize("who", [caretaker, warden, admin])
def test_only_students_submit_registrations(who):
    RegistrationWindowFactory()
    with pytest.raises(PermissionDeniedError):
        svc.submit_registration_request(actor=who())


@pytest.mark.parametrize("existing", ["submitted", "approved"])
def test_a_second_live_registration_is_refused(existing):
    RegistrationWindowFactory()
    RegistrationFactory(status=existing)
    with pytest.raises(ConflictError):
        svc.submit_registration_request(actor=student())
    assert MessRegistration.objects.count() == 1


def test_a_rejected_student_may_apply_again():
    RegistrationWindowFactory()
    RegistrationFactory(rejected=True)
    r = svc.submit_registration_request(actor=student())
    assert r.status == "submitted"


def test_one_students_registration_does_not_block_another():
    RegistrationWindowFactory()
    RegistrationFactory(user_id=OTHER_STUDENT_ID, approved=True)
    assert svc.submit_registration_request(actor=student()).user_id == STUDENT_ID


# =============================================================================
# Review registration — BR-MMS-010, BR-MMS-011, BW-MMS-01 / 02
# =============================================================================
@pytest.mark.parametrize(("action", "status"), [("approve", "approved"), ("reject", "rejected")])
def test_br010_caretaker_decides_a_registration(action, status, sent):
    r = RegistrationFactory()
    out = svc.review_registration_request(actor=caretaker(), request_id=r.pk, action=action,
                                          remarks="ok")
    r.refresh_from_db()
    assert out.status == r.status == status
    assert (r.reviewed_by_user_id, r.remarks) == (CARETAKER_ID, "ok")
    assert r.reviewed_at is not None
    [n] = sent(f"registration_{status}")
    assert n.recipient_user_id == STUDENT_ID


@pytest.mark.parametrize("who", [warden, student, admin])
def test_br010_br011_only_the_caretaker_decides_registrations(who):
    r = RegistrationFactory()
    with pytest.raises(PermissionDeniedError):
        svc.review_registration_request(actor=who(), request_id=r.pk, action="approve")
    r.refresh_from_db()
    assert (r.status, r.reviewed_by_user_id) == ("submitted", None)


@pytest.mark.parametrize("decided", ["approved", "rejected"])
@pytest.mark.parametrize("action", ["approve", "reject"])
def test_a_decided_registration_cannot_be_decided_again(decided, action, sent):
    r = RegistrationFactory(status=decided)
    with pytest.raises(ConflictError):
        svc.review_registration_request(actor=caretaker(), request_id=r.pk, action=action)
    r.refresh_from_db()
    assert r.status == decided
    assert sent() == []


@pytest.mark.parametrize("bad", ["", "APPROVE", "approved", "maybe", "delete"])
def test_an_unknown_review_action_changes_nothing(bad, sent):
    r = RegistrationFactory()
    with pytest.raises(BadRequestError):
        svc.review_registration_request(actor=caretaker(), request_id=r.pk, action=bad)
    r.refresh_from_db()
    assert (r.status, r.reviewed_by_user_id) == ("submitted", None)
    assert sent() == []


def test_cw01_full_registration_lifecycle(sent):
    """CW-MMS-01: open window -> submit -> approve; student is then registered."""
    _open()
    r = svc.submit_registration_request(actor=student())
    svc.review_registration_request(actor=caretaker(), request_id=r.pk, action="approve")
    assert MessRegistration.objects.get(user_id=STUDENT_ID).status == "approved"
    assert [n.event_type for n in sent(user_id=STUDENT_ID)] == [
        "registration_submitted", "registration_approved"]


# =============================================================================
# Deregistration — BR-MMS-012, BR-MMS-013, BW-MMS-03 / 04
# =============================================================================
def test_br012_a_registered_student_may_request_deregistration(sent):
    reg = RegistrationFactory(approved=True)
    dr = svc.submit_deregistration_request(actor=student(), reason="leaving")
    assert (dr.status, dr.registration_id) == ("submitted", reg.pk)
    assert len(sent("deregistration_submitted")) == 1


def test_br012_needs_an_approved_registration():
    with pytest.raises(ConflictError):
        svc.submit_deregistration_request(actor=student(), reason="x")


@pytest.mark.parametrize("status", ["submitted", "rejected"])
def test_br012_a_pending_or_rejected_registration_is_not_enough(status):
    RegistrationFactory(status=status)
    with pytest.raises(ConflictError):
        svc.submit_deregistration_request(actor=student(), reason="x")


def test_only_one_pending_deregistration_at_a_time():
    RegistrationFactory(approved=True)
    svc.submit_deregistration_request(actor=student(), reason="x")
    with pytest.raises(ConflictError):
        svc.submit_deregistration_request(actor=student(), reason="again")
    assert MessDeregistration.objects.count() == 1


def test_a_rejected_deregistration_does_not_block_a_new_one():
    reg = RegistrationFactory(approved=True)
    DeregistrationFactory(registration=reg, status="rejected")
    assert svc.submit_deregistration_request(actor=student(), reason="x").status == "submitted"


@pytest.mark.parametrize("who", [caretaker, warden, admin])
def test_only_students_submit_deregistrations(who):
    RegistrationFactory(approved=True)
    with pytest.raises(PermissionDeniedError):
        svc.submit_deregistration_request(actor=who(), reason="x")


def test_br013_approval_takes_effect_from_the_next_calendar_day(sent):
    dr = DeregistrationFactory()
    out = svc.review_deregistration_request(actor=caretaker(), request_id=dr.pk, action="approve")
    assert out.status == "approved"
    assert out.effective_date == days_from_today(1)
    assert out.is_active_deregistration is False        # not yet — that is UC-027's job
    assert len(sent("deregistration_approved")) == 1


def test_br013_approval_leaves_the_registration_approved_until_activation():
    dr = DeregistrationFactory()
    svc.review_deregistration_request(actor=caretaker(), request_id=dr.pk, action="approve")
    dr.registration.refresh_from_db()
    assert dr.registration.status == "approved"


def test_a_rejected_deregistration_has_no_effective_date_and_student_stays_registered(sent):
    dr = DeregistrationFactory()
    out = svc.review_deregistration_request(actor=caretaker(), request_id=dr.pk, action="reject",
                                            remarks="exams")
    dr.registration.refresh_from_db()
    assert (out.status, out.effective_date, out.remarks) == ("rejected", None, "exams")
    assert dr.registration.status == "approved"
    assert len(sent("deregistration_rejected")) == 1


@pytest.mark.parametrize("who", [warden, student, admin])
def test_br010_only_the_caretaker_decides_deregistrations(who):
    dr = DeregistrationFactory()
    with pytest.raises(PermissionDeniedError):
        svc.review_deregistration_request(actor=who(), request_id=dr.pk, action="approve")
    dr.refresh_from_db()
    assert dr.status == "submitted"


@pytest.mark.parametrize("decided", ["approved", "rejected"])
def test_a_decided_deregistration_cannot_be_decided_again(decided):
    dr = DeregistrationFactory(status=decided)
    with pytest.raises(ConflictError):
        svc.review_deregistration_request(actor=caretaker(), request_id=dr.pk, action="approve")


def test_an_unknown_deregistration_action_changes_nothing():
    dr = DeregistrationFactory()
    with pytest.raises(BadRequestError):
        svc.review_deregistration_request(actor=caretaker(), request_id=dr.pk, action="x")
    dr.refresh_from_db()
    assert (dr.status, dr.effective_date) == ("submitted", None)


# ---- UC-027: activation ------------------------------------------------------
def test_uc027_activation_deregisters_the_student():
    dr = DeregistrationFactory(approved=True)
    out = svc.activate_approved_deregistration(deregistration_id=dr.pk)
    assert out.is_active_deregistration is True
    dr.registration.refresh_from_db()
    assert dr.registration.status != "approved"           # no longer a live registration


@pytest.mark.parametrize("status", ["submitted", "rejected"])
def test_uc027_only_an_approved_deregistration_can_be_activated(status):
    dr = DeregistrationFactory(status=status)
    with pytest.raises(ConflictError):
        svc.activate_approved_deregistration(deregistration_id=dr.pk)
    dr.refresh_from_db()
    assert dr.is_active_deregistration is False


def test_uc027_activation_is_idempotent():
    dr = DeregistrationFactory(approved=True)
    svc.activate_approved_deregistration(deregistration_id=dr.pk)
    again = svc.activate_approved_deregistration(deregistration_id=dr.pk)
    assert again.is_active_deregistration is True


def test_cw02_deregistered_student_may_register_again_in_a_later_window():
    dr = DeregistrationFactory(approved=True)
    svc.activate_approved_deregistration(deregistration_id=dr.pk)
    RegistrationWindowFactory()
    assert svc.submit_registration_request(actor=student()).status == "submitted"
