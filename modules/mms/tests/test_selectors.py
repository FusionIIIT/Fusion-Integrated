"""Selectors decide what a role may SEE. Scope is enforced here, so a foreign row is absent
rather than forbidden. BR-MMS-005 (admin sees no operational data), 011, 020, 040, 042."""
import pytest

from conftest import make_principal
from modules.mms.selectors import scoping
from modules.mms.tests import factories as f
from modules.mms.tests.helpers import (
    OTHER_STUDENT_ID,
    STUDENT_ID,
    admin,
    caretaker,
    student,
    warden,
)

pytestmark = pytest.mark.django_db
MINE, THEIRS = STUDENT_ID, OTHER_STUDENT_ID

# (selector, factory) for every selector that returns per-student operational rows.
PER_STUDENT = [
    (scoping.visible_registrations, f.RegistrationFactory),
    (scoping.visible_deregistrations, lambda **kw: f.DeregistrationFactory(
        registration=f.RegistrationFactory(approved=True, user_id=kw["user_id"]), **kw)),
    (scoping.visible_rebates, f.RebateFactory),
    (scoping.visible_special_food_requests, f.SpecialFoodFactory),
    (scoping.visible_bills, f.BillFactory),
    (scoping.visible_feedback, f.FeedbackFactory),
]
IDS = [s.__name__ for s, _ in PER_STUDENT]


@pytest.mark.parametrize(("selector", "make"), PER_STUDENT, ids=IDS)
def test_br042_a_student_sees_only_their_own_rows(selector, make):
    mine, _theirs = make(user_id=MINE), make(user_id=THEIRS)
    assert list(selector(student())) == [mine]


@pytest.mark.parametrize(("selector", "make"), PER_STUDENT, ids=IDS)
def test_a_student_with_no_rows_sees_nothing_not_everything(selector, make):
    make(user_id=THEIRS)
    assert list(selector(student())) == []


@pytest.mark.parametrize(("selector", "make"), PER_STUDENT, ids=IDS)
def test_br005_the_mess_admin_sees_no_operational_data_at_all(selector, make):
    make(user_id=MINE)
    make(user_id=THEIRS)
    assert selector(admin()).count() == 0


@pytest.mark.parametrize(("selector", "make"), PER_STUDENT, ids=IDS)
def test_an_actor_with_no_mms_permissions_sees_nothing(selector, make):
    make(user_id=MINE)
    nobody = make_principal(permissions=())
    assert selector(nobody).count() == 0


@pytest.mark.parametrize(("selector", "make"), PER_STUDENT, ids=IDS)
def test_the_caretaker_sees_every_students_rows(selector, make):
    make(user_id=MINE)
    make(user_id=THEIRS)
    assert selector(caretaker()).count() == 2


def test_br011_the_warden_oversees_registrations_and_deregistrations():
    f.RegistrationFactory(user_id=MINE)
    f.RegistrationFactory(user_id=THEIRS)
    assert scoping.visible_registrations(warden()).count() == 2
    f.DeregistrationFactory(user_id=MINE)
    assert scoping.visible_deregistrations(warden()).count() == 1


def test_the_warden_sees_rebate_summaries_for_supervision():
    f.RebateFactory(user_id=MINE)
    f.RebateFactory(user_id=THEIRS)
    assert scoping.visible_rebates(warden()).count() == 2


def test_the_warden_does_not_see_billing_or_special_food_requests():
    """The PS gives the warden registration/deregistration oversight, rebate summaries,
    feedback and announcements — not individual bills or special-food requests."""
    f.BillFactory()
    f.SpecialFoodFactory()
    assert scoping.visible_bills(warden()).count() == 0
    assert scoping.visible_special_food_requests(warden()).count() == 0


@pytest.mark.parametrize("who", [caretaker, warden])
def test_br020_caretaker_and_warden_read_all_feedback(who):
    f.FeedbackFactory(user_id=MINE)
    f.FeedbackFactory(user_id=THEIRS)
    assert scoping.visible_feedback(who()).count() == 2


def test_menus_show_only_active_slots_to_anyone_with_menu_view():
    f.MenuFactory(day_of_week="monday", meal_type="lunch")
    f.MenuFactory(day_of_week="monday", meal_type="dinner", is_active=False)
    for who in (student, caretaker, warden):
        assert scoping.visible_menus(who()).count() == 1


def test_announcements_show_only_active_ones():
    f.AnnouncementFactory()
    f.AnnouncementFactory(is_active=False)
    assert scoping.visible_announcements(student()).count() == 1


# ---- vacation responses ---------------------------------------------------------
def _responses():
    survey, other_survey = f.VacationSurveyFactory(), f.VacationSurveyFactory(title="other")
    from modules.mms.models import VacationFoodResponse as R
    R.objects.create(survey=survey, user_id=MINE, requires_food=True)
    R.objects.create(survey=survey, user_id=THEIRS, requires_food=False)
    R.objects.create(survey=other_survey, user_id=MINE, requires_food=True)
    return survey


def test_a_student_sees_only_their_own_response_to_that_survey():
    survey = _responses()
    assert [r.user_id for r in scoping.visible_vacation_responses(student(), survey.pk)] == [MINE]


@pytest.mark.parametrize("who", [caretaker, warden])
def test_caretaker_and_warden_see_the_response_summary_for_that_survey_only(who):
    survey = _responses()
    assert scoping.visible_vacation_responses(who(), survey.pk).count() == 2


def test_the_admin_sees_no_vacation_responses():
    survey = _responses()
    assert scoping.visible_vacation_responses(admin(), survey.pk).count() == 0
