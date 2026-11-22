"""Menu (UC-008/009), announcements (UC-022/023), feedback (UC-012/013), reports (UC-024/025),
oversight (UC-007). BR-MMS-005, 011, 014, 020, 032..034, 038, 039."""
import pytest

from core.api.exceptions import BadRequestError, PermissionDeniedError
from modules.mms.models import MessAnnouncement, MessFeedback, MessMenu
from modules.mms.services import operations as svc
from modules.mms.tests.factories import (
    AnnouncementFactory,
    DeregistrationFactory,
    FeedbackFactory,
    MenuFactory,
    RegistrationFactory,
)
from modules.mms.tests.helpers import (
    CARETAKER_ID,
    OTHER_STUDENT_ID,
    STUDENT_ID,
    WARDEN_ID,
    admin,
    caretaker,
    student,
    warden,
)

pytestmark = pytest.mark.django_db
ALL_ROLES = [admin, caretaker, warden, student]


# ---- menu ---------------------------------------------------------------------
def test_br014_caretaker_publishes_a_day_and_meal():
    m = svc.publish_or_update_menu(actor=caretaker(), day_of_week="monday", meal_type="lunch",
                                   items=["Dal", "Rice"])
    assert (m.day_of_week, m.meal_type, m.items, m.updated_by_user_id) == (
        "monday", "lunch", ["Dal", "Rice"], CARETAKER_ID)


def test_updating_a_slot_replaces_it_instead_of_adding_a_second_row():
    svc.publish_or_update_menu(actor=caretaker(), day_of_week="monday", meal_type="lunch",
                               items=["Dal"])
    svc.publish_or_update_menu(actor=caretaker(), day_of_week="monday", meal_type="lunch",
                               items=["Paneer"])
    [only] = MessMenu.objects.all()
    assert only.items == ["Paneer"]


def test_publishing_again_reactivates_a_withdrawn_slot():
    MenuFactory(is_active=False)
    m = svc.publish_or_update_menu(actor=caretaker(), day_of_week="monday", meal_type="lunch",
                                   items=["Dal"])
    assert m.is_active is True


@pytest.mark.parametrize(("day", "meal"), [("MONDAY", "Lunch"), ("Monday", "DINNER")])
def test_day_and_meal_are_case_insensitive(day, meal):
    m = svc.publish_or_update_menu(actor=caretaker(), day_of_week=day, meal_type=meal, items=["x"])
    assert (m.day_of_week, m.meal_type) == (day.lower(), meal.lower())


@pytest.mark.parametrize(("day", "meal"), [("funday", "lunch"), ("monday", "brunch"), ("", "lunch")])
def test_br014_only_real_days_and_the_three_meals(day, meal):
    with pytest.raises(BadRequestError):
        svc.publish_or_update_menu(actor=caretaker(), day_of_week=day, meal_type=meal, items=[])
    assert MessMenu.objects.count() == 0


def test_a_full_week_is_twenty_one_slots():
    for d in (["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]):
        for meal in ("breakfast", "lunch", "dinner"):
            svc.publish_or_update_menu(actor=caretaker(), day_of_week=d, meal_type=meal,
                                       items=["x"])
    assert MessMenu.objects.count() == 21


@pytest.mark.parametrize("who", [warden, student, admin])
def test_br039_only_the_caretaker_maintains_the_menu(who):
    with pytest.raises(PermissionDeniedError):
        svc.publish_or_update_menu(actor=who(), day_of_week="monday", meal_type="lunch", items=[])
    assert MessMenu.objects.count() == 0


@pytest.mark.parametrize("who", [caretaker, warden, student])
def test_br038_students_caretaker_and_warden_can_view_the_menu(who):
    MenuFactory()
    assert len(svc.view_weekly_menu(actor=who())) == 1


def test_withdrawn_menu_items_are_not_shown():
    MenuFactory(day_of_week="monday", meal_type="lunch")
    MenuFactory(day_of_week="monday", meal_type="dinner", is_active=False)
    assert [m.meal_type for m in svc.view_weekly_menu(actor=student())] == ["lunch"]


# ---- announcements -------------------------------------------------------------
@pytest.mark.parametrize(("who", "role"), [(caretaker, "mess_caretaker"), (warden, "mess_warden")])
def test_br032_caretaker_and_warden_publish_announcements(who, role):
    a = svc.publish_announcement(actor=who(), title="T", content="C")
    assert (a.published_by_role, a.is_active) == (role, True)


@pytest.mark.parametrize("who", [student, admin])
def test_br032_nobody_else_publishes_announcements(who):
    with pytest.raises(PermissionDeniedError):
        svc.publish_announcement(actor=who(), title="T", content="C")
    assert MessAnnouncement.objects.count() == 0


@pytest.mark.parametrize("who", ALL_ROLES)
def test_br033_every_mms_actor_can_read_announcement_history(who):
    AnnouncementFactory()
    AnnouncementFactory(is_active=False)
    assert len(svc.view_announcements(actor=who())) == 1


# ---- feedback ------------------------------------------------------------------
def test_br020_student_submits_feedback_in_their_own_name():
    f = svc.submit_feedback(actor=student(), description="Cold rice")
    assert (f.user_id, f.category) == (STUDENT_ID, "general")


@pytest.mark.parametrize("who", [caretaker, warden, admin])
def test_only_students_submit_feedback(who):
    with pytest.raises(PermissionDeniedError):
        svc.submit_feedback(actor=who(), description="x")
    assert MessFeedback.objects.count() == 0


@pytest.mark.parametrize("who", [caretaker, warden])
def test_br020_caretaker_and_warden_read_all_feedback(who):
    FeedbackFactory(user_id=STUDENT_ID)
    FeedbackFactory(user_id=OTHER_STUDENT_ID)
    assert len(svc.view_feedback_entries(actor=who())) == 2


@pytest.mark.parametrize("who", [student, admin])
def test_br005_br020_students_and_admin_cannot_browse_feedback(who):
    FeedbackFactory()
    with pytest.raises(PermissionDeniedError):
        svc.view_feedback_entries(actor=who())


# ---- reports and oversight ------------------------------------------------------
def test_br034_operational_reports_are_the_caretakers():
    out = svc.generate_operational_reports(actor=caretaker(), report_type="registration_trends")
    assert (out["report_type"], out["generated_by"]) == ("registration_trends", CARETAKER_ID)


@pytest.mark.parametrize("who", [warden, student, admin])
def test_br034_nobody_else_generates_operational_reports(who):
    with pytest.raises(PermissionDeniedError):
        svc.generate_operational_reports(actor=who())


def test_br034_supervisory_reports_are_the_wardens():
    out = svc.generate_supervisory_reports(actor=warden())
    assert out["generated_by"] == WARDEN_ID


@pytest.mark.parametrize("who", [caretaker, student, admin])
def test_br034_nobody_else_views_supervisory_reports(who):
    with pytest.raises(PermissionDeniedError):
        svc.generate_supervisory_reports(actor=who())


def test_br011_the_warden_sees_registrations_and_deregistrations_for_oversight():
    RegistrationFactory(user_id=STUDENT_ID, approved=True)
    DeregistrationFactory(user_id=OTHER_STUDENT_ID,
                          registration=RegistrationFactory(user_id=OTHER_STUDENT_ID, approved=True))
    regs, deregs = svc.view_registration_oversight(actor=warden())
    assert (len(regs), len(deregs)) == (2, 1)


@pytest.mark.parametrize("who", [student, admin])
def test_br005_br011_students_and_admin_get_no_oversight_view(who):
    RegistrationFactory()
    with pytest.raises(PermissionDeniedError):
        svc.view_registration_oversight(actor=who())
