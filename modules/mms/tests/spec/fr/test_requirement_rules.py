from datetime import date, timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from modules.mms.domain import rules
from modules.mms.domain.exceptions import GuardFailed
from modules.mms.models import Feedback, MenuItem, NotificationOutbox
from modules.mms.services import menu, notifications
from modules.mms.services.menu import list_items


def test_fr_afr_024_menu_items_are_day_and_meal_scoped():
    """test_id=FR-AFR-024; source_id=AFR-MMS-024; FR_source_ids=AFR-MMS-024"""
    assert MenuItem._meta.get_field("day").get_internal_type() == "DateField"
    meal_field = MenuItem._meta.get_field("meal")
    assert meal_field.get_internal_type() == "CharField"
    assert {value for value, _label in meal_field.choices} == {"breakfast", "lunch", "dinner"}


def test_fr_afr_025_student_can_view_weekly_menu(student_actor):
    """test_id=FR-AFR-025,FR-AFR-008; source_id=AFR-MMS-025; FR_source_ids=AFR-MMS-008,AFR-MMS-025"""
    queryset = list_items(student_actor)
    assert queryset.model is MenuItem
    assert not queryset.query.where.children
    assert queryset.query.order_by == ("day", "meal")


def test_fr_afr_064_accepts_yes_and_no_only():
    """test_id=FR-AFR-064; source_id=AFR-MMS-064; FR_source_ids=AFR-MMS-064"""
    rules.valid_vacation_response("yes")
    rules.valid_vacation_response("no")
    with pytest.raises(GuardFailed):
        rules.valid_vacation_response("maybe")


def test_fr_afr_100_scope_rejects_payment_processing():
    """test_id=FR-AFR-100,FR-AFR-042,FR-AFR-093,FR-CFR-021; source_id=AFR-MMS-100; FR_source_ids=AFR-MMS-042,AFR-MMS-093,AFR-MMS-100,CFR-MMS-021"""
    from modules.mms.api.urls import urlpatterns

    out_of_scope_paths = ("payment", "accounting", "payroll", "procurement", "inventory")
    exposed_paths = [str(pattern.pattern) for pattern in urlpatterns]
    assert not any(term in path.lower() for path in exposed_paths for term in out_of_scope_paths)


def test_fr_afr_052_rebate_minimum_duration_boundary():
    """test_id=FR-AFR-052,FR-CFR-011; source_id=AFR-MMS-052; FR_source_ids=AFR-MMS-052,CFR-MMS-011"""
    submitted = date(2026, 11, 22)
    rules.rebate_valid("medical", "", date(2026, 11, 25), date(2026, 11, 28), submitted, [])
    with pytest.raises(GuardFailed):
        rules.rebate_valid("medical", "", date(2026, 11, 25), date(2026, 11, 27), submitted, [])


def test_fr_afr_053_rebate_one_day_lead_boundary():
    """test_id=FR-AFR-053,FR-CFR-011; source_id=AFR-MMS-053; FR_source_ids=AFR-MMS-053,CFR-MMS-011"""
    start, end = date(2026, 11, 23), date(2026, 11, 27)
    rules.rebate_valid("medical", "", start, end, date(2026, 11, 22), [])
    with pytest.raises(GuardFailed):
        rules.rebate_valid("medical", "", start, end, date(2026, 11, 23), [])


def test_fr_afr_054_overlapping_rebate_is_rejected():
    """test_id=FR-AFR-054,FR-CFR-011; source_id=AFR-MMS-054; FR_source_ids=AFR-MMS-054,CFR-MMS-011"""
    with pytest.raises(GuardFailed):
        rules.rebate_valid(
            "medical", "", date(2026, 11, 28), date(2026, 12, 2), date(2026, 11, 22),
            [(date(2026, 11, 25), date(2026, 11, 30))],
        )


def test_fr_afr_051_other_reason_requires_explanation():
    """test_id=FR-AFR-051,FR-CFR-011; source_id=AFR-MMS-051; FR_source_ids=AFR-MMS-051,CFR-MMS-011"""
    args = (date(2026, 11, 25), date(2026, 11, 29), date(2026, 11, 22), [])
    rules.rebate_valid("other", "conference", *args)
    with pytest.raises(GuardFailed):
        rules.rebate_valid("other", " ", *args)


def test_fr_afr_071_special_food_one_day_lead_boundary():
    """test_id=FR-AFR-071,FR-CFR-015; source_id=AFR-MMS-071; FR_source_ids=AFR-MMS-071,CFR-MMS-015"""
    today = date(2026, 11, 22)
    rules.special_food_lead_time_ok(today, date(2026, 11, 23))
    with pytest.raises(GuardFailed):
        rules.special_food_lead_time_ok(today, today)


@pytest.mark.django_db
def test_fr_afr_029_030_031_032_caretaker_maintains_menu_and_notifies(caretaker_actor):
    """test_id=FR-AFR-029,FR-AFR-030,FR-AFR-031,FR-AFR-032; source_id=AFR-MMS-029/030/031/032; FR_source_ids=AFR-MMS-029,AFR-MMS-030,AFR-MMS-031,AFR-MMS-032"""
    day = timezone.localdate() + timedelta(days=1)
    item = menu.upsert_item(caretaker_actor, day, "dinner", "Rice")
    changed = menu.upsert_item(caretaker_actor, day, "dinner", "Rice and lentils", pk=item.pk)

    assert changed.item == "Rice and lentils"
    assert NotificationOutbox.objects.filter(topic="menu.updated").exists()

    menu.delete_item(caretaker_actor, item.pk)
    assert not MenuItem.objects.filter(pk=item.pk).exists()


@pytest.mark.django_db
def test_fr_afr_048_feedback_has_no_resolution_workflow(student_actor):
    """test_id=FR-AFR-048; source_id=AFR-MMS-048; FR_source_ids=AFR-MMS-048"""
    saved = Feedback.objects.create(user_id=student_actor.user_id, text="Keep the dining area clean.")
    field_names = {field.name for field in Feedback._meta.get_fields()}

    assert saved.text == "Keep the dining area clean."
    assert not any("resolution" in name or "resolved" in name for name in field_names)


def test_fr_afr_094_notification_topics_match_the_problem_statement():
    """test_id=FR-AFR-094,FR-CFR-022; source_id=AFR-MMS-094; FR_source_ids=AFR-MMS-094,CFR-MMS-022"""
    assert {
        "registration.submitted",
        "registration.decided",
        "deregistration.submitted",
        "deregistration.decided",
        "rebate.submitted",
        "rebate.decided",
        "special_food.submitted",
        "special_food.decided",
        "special_food.fulfilled",
        "special_food.default_rejected",
        "survey.created",
        "survey.reminder",
        "survey.default_no",
        "menu.updated",
        "bill.published",
        "announcement.published",
    } == notifications.TOPICS


@pytest.mark.django_db
def test_fr_afr_095_enqueue_uses_outbox_without_sending_mail():
    """test_id=FR-AFR-095,FR-CFR-022; source_id=AFR-MMS-095; FR_source_ids=AFR-MMS-095,CFR-MMS-022"""
    with patch("modules.mms.services.notifications.send_mail") as send_mail:
        queued = notifications.enqueue(
            topic="survey.created",
            dedupe_key="survey.created:fr-requirement-test",
            subject="Survey created",
            body="A survey is available.",
            recipient_email="student@example.invalid",
        )

    assert queued is not None
    assert NotificationOutbox.objects.filter(pk=queued.pk, status="pending").exists()
    send_mail.assert_not_called()


@pytest.mark.skip(
    reason="NOT_AUTOMATED: the supplied draft conflicts on Mess Admin menu visibility, so the expected access result is unresolved."
)
def test_fr_afr_028_mess_admin_weekly_menu_visibility_is_not_automated():
    """test_id=FR-AFR-028; source_id=AFR-MMS-028; FR_source_ids=AFR-MMS-028"""


@pytest.mark.skip(
    reason="NOT_AUTOMATED: billing has no served-day source or authoritative daily-rate input to compute the required charge."
)
def test_fr_afr_034_served_day_daily_rate_charge_is_not_automated():
    """test_id=FR-AFR-034; source_id=AFR-MMS-034; FR_source_ids=AFR-MMS-034"""


@pytest.mark.skip(
    reason="NOT_AUTOMATED: no Warden API or authoritative search input/output contract exists for these report views."
)
def test_fr_afr_086_warden_registered_student_search_is_not_automated():
    """test_id=FR-AFR-086; source_id=AFR-MMS-086; FR_source_ids=AFR-MMS-086"""


@pytest.mark.skip(
    reason="NOT_AUTOMATED: no Warden API or authoritative search input/output contract exists for these report views."
)
def test_fr_afr_087_warden_rebate_summary_search_is_not_automated():
    """test_id=FR-AFR-087; source_id=AFR-MMS-087; FR_source_ids=AFR-MMS-087"""


@pytest.mark.skip(
    reason="NOT_AUTOMATED: no Warden API or authoritative search input/output contract exists for these report views."
)
def test_fr_afr_088_warden_survey_summary_search_is_not_automated():
    """test_id=FR-AFR-088; source_id=AFR-MMS-088; FR_source_ids=AFR-MMS-088"""


@pytest.mark.skip(
    reason="NOT_AUTOMATED: the available operational report lacks defined registration trend data and output shape."
)
def test_fr_afr_089_registration_trend_report_is_not_automated():
    """test_id=FR-AFR-089; source_id=AFR-MMS-089; FR_source_ids=AFR-MMS-089"""


@pytest.mark.skip(
    reason="NOT_AUTOMATED: the available operational report lacks a defined special-meal log and output shape."
)
def test_fr_afr_090_special_meal_log_is_not_automated():
    """test_id=FR-AFR-090; source_id=AFR-MMS-090; FR_source_ids=AFR-MMS-090"""


@pytest.mark.skip(
    reason="NOT_AUTOMATED: the available operational report lacks a defined billing summary and output shape."
)
def test_fr_afr_091_billing_summary_report_is_not_automated():
    """test_id=FR-AFR-091; source_id=AFR-MMS-091; FR_source_ids=AFR-MMS-091"""


@pytest.mark.skip(
    reason="NOT_AUTOMATED: no authoritative external institution-policy provider is present to supply or verify policy inputs."
)
def test_fr_afr_101_external_institution_policy_is_not_automated():
    """test_id=FR-AFR-101; source_id=AFR-MMS-101; FR_source_ids=AFR-MMS-101"""
