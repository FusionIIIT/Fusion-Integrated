"""Vacation food continuity — MMS-UC-016, 017, 028. BR-MMS-026, 027, 041.
Workflows BW-MMS-08/09/10, CW-MMS-04."""
import pytest

from core.api.exceptions import ConflictError, PermissionDeniedError
from modules.mms.domain.state_machine import RuleViolation
from modules.mms.models import VacationFoodResponse
from modules.mms.services import operations as svc
from modules.mms.tests.factories import RegistrationFactory, VacationSurveyFactory
from modules.mms.tests.helpers import (
    CARETAKER_ID,
    OTHER_STUDENT_ID,
    STUDENT_ID,
    admin,
    caretaker,
    student,
    warden,
)

pytestmark = pytest.mark.django_db
THIRD_ID = 3003


def _respond(survey, yes, user=STUDENT_ID):
    return svc.respond_to_vacation_survey(actor=student(user), survey_id=survey.pk,
                                          requires_food=yes)


def test_caretaker_creates_an_open_survey():
    from datetime import date

    from django.utils import timezone
    s = svc.create_vacation_survey(
        actor=caretaker(), title="Winter", vacation_start_date=date(2026, 12, 20),
        vacation_end_date=date(2027, 1, 5), response_deadline=timezone.now())
    assert (s.status, s.created_by_user_id) == ("open", CARETAKER_ID)


@pytest.mark.parametrize("who", [student, warden, admin])
def test_only_the_caretaker_creates_surveys(who):
    from datetime import date

    from django.utils import timezone
    with pytest.raises(PermissionDeniedError):
        svc.create_vacation_survey(actor=who(), title="x", vacation_start_date=date(2026, 12, 20),
                                   vacation_end_date=date(2027, 1, 5),
                                   response_deadline=timezone.now())


# ---- responding ---------------------------------------------------------------
@pytest.mark.parametrize("yes", [True, False])
def test_bw08_bw09_a_registered_student_answers_yes_or_no(yes):
    RegistrationFactory(approved=True)
    survey = VacationSurveyFactory()
    r = _respond(survey, yes)
    assert (r.requires_food, r.is_default, r.responded_at is not None) == (yes, False, True)


def test_br026_an_unregistered_student_cannot_respond():
    survey = VacationSurveyFactory()
    with pytest.raises(RuleViolation) as e:
        _respond(survey, True)
    assert e.value.rule_id == "BR-MMS-026"
    assert VacationFoodResponse.objects.count() == 0


@pytest.mark.parametrize("status", ["submitted", "rejected"])
def test_br026_a_pending_or_rejected_registration_is_not_registered(status):
    RegistrationFactory(status=status)
    with pytest.raises(RuleViolation):
        _respond(VacationSurveyFactory(), True)


def test_a_closed_survey_refuses_responses():
    RegistrationFactory(approved=True)
    with pytest.raises(ConflictError):
        _respond(VacationSurveyFactory(closed=True), True)


def test_changing_an_answer_updates_in_place():
    RegistrationFactory(approved=True)
    survey = VacationSurveyFactory()
    _respond(survey, True)
    _respond(survey, False)
    [only] = VacationFoodResponse.objects.filter(survey=survey)
    assert only.requires_food is False


@pytest.mark.parametrize("who", [caretaker, warden, admin])
def test_only_students_respond(who):
    RegistrationFactory(approved=True)
    with pytest.raises(PermissionDeniedError):
        svc.respond_to_vacation_survey(actor=who(), survey_id=VacationSurveyFactory().pk,
                                       requires_food=True)


# ---- UC-028: default No -------------------------------------------------------
def test_bw10_non_responders_get_default_no():
    for uid in (STUDENT_ID, OTHER_STUDENT_ID):
        RegistrationFactory(user_id=uid, approved=True)
    survey = VacationSurveyFactory()
    assert svc.apply_default_vacation_responses(survey_id=survey.pk) == 2
    for r in VacationFoodResponse.objects.filter(survey=survey):
        assert (r.requires_food, r.is_default, r.responded_at is not None) == (False, True, True)


def test_br027_explicit_answers_are_never_overwritten_by_the_default():
    for uid in (STUDENT_ID, OTHER_STUDENT_ID):
        RegistrationFactory(user_id=uid, approved=True)
    survey = VacationSurveyFactory()
    _respond(survey, True, STUDENT_ID)
    assert svc.apply_default_vacation_responses(survey_id=survey.pk) == 1
    mine = VacationFoodResponse.objects.get(survey=survey, user_id=STUDENT_ID)
    other = VacationFoodResponse.objects.get(survey=survey, user_id=OTHER_STUDENT_ID)
    assert (mine.requires_food, mine.is_default) == (True, False)
    assert (other.requires_food, other.is_default) == (False, True)


def test_br026_br027_only_registered_students_receive_a_default():
    RegistrationFactory(user_id=STUDENT_ID, approved=True)
    RegistrationFactory(user_id=OTHER_STUDENT_ID, status="submitted")
    RegistrationFactory(user_id=THIRD_ID, rejected=True)
    survey = VacationSurveyFactory()
    assert svc.apply_default_vacation_responses(survey_id=survey.pk) == 1
    assert list(VacationFoodResponse.objects.values_list("user_id", flat=True)) == [STUDENT_ID]


def test_applying_defaults_twice_creates_nothing_the_second_time():
    RegistrationFactory(approved=True)
    survey = VacationSurveyFactory()
    svc.apply_default_vacation_responses(survey_id=survey.pk)
    assert svc.apply_default_vacation_responses(survey_id=survey.pk) == 0
    assert VacationFoodResponse.objects.filter(survey=survey).count() == 1


def test_defaults_are_per_survey():
    RegistrationFactory(approved=True)
    a, b = VacationSurveyFactory(title="A"), VacationSurveyFactory(title="B")
    svc.apply_default_vacation_responses(survey_id=a.pk)
    assert svc.apply_default_vacation_responses(survey_id=b.pk) == 1


def test_a_student_with_two_approved_registrations_gets_one_default():
    RegistrationFactory(approved=True)
    RegistrationFactory(approved=True)
    survey = VacationSurveyFactory()
    assert svc.apply_default_vacation_responses(survey_id=survey.pk) == 1


def test_defaults_with_no_registered_students_is_a_noop():
    assert svc.apply_default_vacation_responses(survey_id=VacationSurveyFactory().pk) == 0
