from datetime import date, timedelta
from decimal import Decimal

import pytest

from core.api.exceptions import ConflictError, DomainError, NotFoundError, PermissionDeniedError
from modules.elm.models import (
    Account,
    Application,
    AttendanceOutbox,
    AuditEntry,
    EmployeeConfiguration,
    LedgerEntry,
    Notification,
    Policy,
    WorkflowTask,
)
from modules.elm.services import administration as admin
from modules.elm.services import workflow as w

pytestmark = pytest.mark.django_db


def test_approval_posts_once_and_stale_retry_does_not_post(elm):
    app = elm["submit"]()
    assert not LedgerEntry.objects.exists()
    elm["decide"](app)
    assert Account.objects.get(user_id=1, year=2026).cl == Decimal("7")
    assert LedgerEntry.objects.filter(application=app).count() == 1
    with pytest.raises(ConflictError):
        w.act(
            actor=elm["actor"](2, "Unit Head"), application_id=app.pk, action="approve", revision=1
        )
    assert LedgerEntry.objects.filter(application=app).count() == 1


def test_not_recommended_is_forwarded_not_rejected(elm):
    app = elm["submit"](category="EL")
    elm["decide"](app, "not_recommend", reason="Staffing concern")
    app.refresh_from_db()
    assert app.status == "sanction"
    assert not LedgerEntry.objects.exists()
    elm["decide"](app, user_id=3, role="Registrar")
    assert Account.objects.get(user_id=1, year=2026).el == Decimal("29")


def test_substitute_decline_replacement_and_accept_gate(elm):
    EmployeeConfiguration.objects.filter(user_id=1).update(coverage_required=True)
    app = elm["submit"](substitute_id=4)
    assert app.status == "substitute"
    elm["decide"](app, "decline", user_id=4, role="staff", reason="Unavailable")
    app.refresh_from_db()
    assert app.status == "applicant_action"
    app = w.replace_substitute(
        actor=elm["actor"](), application_id=app.pk, revision=app.revision, substitute_id=5
    )
    assert app.status == "substitute"
    elm["decide"](app, "accept", user_id=5, role="staff")
    app.refresh_from_db()
    assert app.status == "unit_head"


def test_withdrawal_closes_task_and_blocks_decision(elm):
    app = elm["submit"]()
    w.withdraw(actor=elm["actor"](), application_id=app.pk, revision=app.revision)
    assert not WorkflowTask.objects.filter(application=app, pending=True).exists()
    with pytest.raises(ConflictError):
        elm["decide"](app)
    assert not LedgerEntry.objects.exists()
    assert Notification.objects.filter(
        user_id=2, application=app, message__contains="withdrawn"
    ).exists()


def test_cancellation_rejection_keeps_approval_and_success_refunds_once(elm):
    parent = elm["approved"]()
    change = w.lifecycle(
        actor=elm["actor"](), application_id=parent.pk, kind="cancellation", reason="Plan changed"
    )
    elm["decide"](change, "reject", reason="Still required")
    parent.refresh_from_db()
    assert parent.status == "approved"
    assert Account.objects.get(user_id=1, year=2026).cl == Decimal("7")
    change = w.lifecycle(
        actor=elm["actor"](), application_id=parent.pk, kind="cancellation", reason="Plan changed"
    )
    elm["decide"](change)
    parent.refresh_from_db()
    assert parent.status == "cancelled"
    assert Account.objects.get(user_id=1, year=2026).cl == Decimal("8")


def test_cancellation_cannot_be_finalized_after_start(elm):
    parent = elm["approved"]()
    change = w.lifecycle(
        actor=elm["actor"](), application_id=parent.pk, kind="cancellation", reason="Cancel"
    )
    elm["today"][0] = parent.start_date
    with pytest.raises(ConflictError):
        elm["decide"](change)
    assert WorkflowTask.objects.get(application=change, pending=True)


def _extended(elm):
    parent = elm["approved"](category="EL", start=date(2026, 10, 26), end=date(2026, 10, 30))
    extension = w.lifecycle(
        actor=elm["actor"](),
        application_id=parent.pk,
        kind="extension",
        reason="More time",
        end_date=date(2026, 11, 3),
    )
    elm["decide"](extension, "recommend")
    elm["decide"](extension, user_id=3, role="Registrar")
    parent.refresh_from_db()
    assert parent.effective_end_date == date(2026, 11, 3)
    assert Account.objects.get(user_id=1, year=2026).el == Decimal("21")
    return parent


def test_early_resumption_releases_dates_previously_in_approved_extension(elm):
    parent = _extended(elm)
    elm["today"][0] = date(2026, 10, 31)
    change = w.lifecycle(
        actor=elm["actor"](),
        application_id=parent.pk,
        kind="resumption",
        reason="Returned early",
        end_date=date(2026, 10, 30),
    )
    elm["decide"](change, "review", user_id=3, role="Registrar")
    assert Account.objects.get(user_id=1, year=2026).el == Decimal("25")
    assert AttendanceOutbox.objects.filter(application=change).count() == 1
    fresh = elm["submit"](start=date(2026, 11, 2))
    assert fresh.status == "unit_head"


@pytest.mark.parametrize(
    "return_date,expected", [(date(2026, 10, 30), "25"), (date(2026, 11, 2), "22")]
)
def test_normal_and_late_resumption_adjust_balance_once(elm, return_date, expected):
    parent = elm["approved"](category="EL", start=date(2026, 10, 26), end=date(2026, 10, 30))
    elm["today"][0] = date(2026, 11, 3)
    change = w.lifecycle(
        actor=elm["actor"](),
        application_id=parent.pk,
        kind="resumption",
        reason="Returned",
        end_date=return_date,
    )
    elm["decide"](change, "review", user_id=3, role="Registrar")
    assert Account.objects.get(user_id=1, year=2026).el == Decimal(expected)
    parent.refresh_from_db()
    assert parent.resumption_reviewed
    assert parent.effective_end_date == return_date
    with pytest.raises(ConflictError):
        w.lifecycle(
            actor=elm["actor"](),
            application_id=parent.pk,
            kind="resumption",
            reason="Duplicate",
            end_date=return_date,
        )


def test_resumption_uses_current_configured_final_authority(elm):
    parent = elm["approved"](category="EL", start=date(2026, 10, 26), end=date(2026, 10, 30))
    config = EmployeeConfiguration.objects.get(user_id=1)
    config.routes["EL"][-1] = {"stage": "sanction", "user_id": 7, "role": "Dean"}
    config.save()
    change = w.lifecycle(
        actor=elm["actor"](),
        application_id=parent.pk,
        kind="resumption",
        reason="Returned",
        end_date=date(2026, 10, 27),
    )
    task = WorkflowTask.objects.get(application=change, pending=True)
    assert (task.user_id, task.role) == (7, "Dean")


def test_foreign_user_wrong_role_and_missing_module_cannot_act(elm):
    app = elm["submit"]()
    with pytest.raises(NotFoundError):
        w.act(
            actor=elm["actor"](4, "Unit Head"), application_id=app.pk, action="approve", revision=1
        )
    with pytest.raises(NotFoundError):
        w.act(actor=elm["actor"](2, "staff"), application_id=app.pk, action="approve", revision=1)
    with pytest.raises(PermissionDeniedError):
        w.submit(actor=elm["actor"](modules=()), data=elm["payload"]())


def test_director_self_sanction_is_the_explicit_exception(elm):
    config = EmployeeConfiguration.objects.get(user_id=1)
    config.designation = "Director"
    config.routes = {
        c: [{"stage": "sanction", "user_id": 1, "role": "Director"}]
        for c in config.eligible_categories
    }
    config.save()
    app = w.submit(actor=elm["actor"](role="Director"), data=elm["payload"]())
    elm["decide"](app, user_id=1, role="Director")
    assert Account.objects.get(user_id=1, year=2026).cl == Decimal("7")


def test_processed_account_cannot_accept_late_postings(elm):
    with w.transaction.atomic():
        account = w.account_for(1, 2025)
    Account.objects.filter(pk=account.pk).update(year_end_processed=True)
    account.refresh_from_db()
    with pytest.raises(ConflictError):
        w.post(account, None, "CL", Decimal("1"), "late", "late:closed")
    assert not LedgerEntry.objects.filter(event_key="late:closed").exists()


def test_faculty_fractional_vl_conversion_and_rollover_are_replay_safe(elm):
    with w.transaction.atomic():
        account = w.account_for(6, 2025)
    Account.objects.filter(pk=account.pk).update(vl=Decimal("3"), el=Decimal("2"), col=Decimal("4"))
    assert admin.process_account_year(6, 2025)
    assert not admin.process_account_year(6, 2025)
    next_account = Account.objects.get(user_id=6, year=2026)
    assert next_account.el == Decimal("3.5")
    assert next_account.col == Decimal("24")
    assert next_account.vl == Decimal("60")
    account.refresh_from_db()
    assert account.vl == 0
    assert account.cl == 0


def test_sla_escalation_and_reminder_only_fire_once_for_pending_tasks(elm):
    app = elm["submit"]()
    task = WorkflowTask.objects.get(application=app, pending=True)
    WorkflowTask.objects.filter(pk=task.pk).update(
        created_at=w.timezone.now() - timedelta(hours=49),
        escalation_user_id=7,
        escalation_role="Unit Head",
        reassign_on_escalation=True,
    )
    assert admin.process_sla() == 2
    assert admin.process_sla() == 0
    task.refresh_from_db()
    assert task.user_id == 7
    assert AuditEntry.objects.filter(application=app, action="sla_escalation").count() == 1
    w.withdraw(
        actor=elm["actor"](),
        application_id=app.pk,
        revision=Application.objects.get(pk=app.pk).revision,
    )
    assert admin.process_sla(now=w.timezone.now() + timedelta(days=5)) == 0


def test_offline_higher_sanction_cannot_be_recorded_as_unit_head_approval(elm):
    actor = elm["actor"](7, "Leave Administrator", permissions=("elm.record.manage",))
    data = {
        **elm["payload"](category="EL"),
        "user_id": 1,
        "offline_reference": "ORDER/123",
        "unavailability_reason": "System unavailable",
        "authority_id": 2,
        "authority_role": "Unit Head",
    }
    with pytest.raises(DomainError):
        admin.offline_entry(actor, data)
    assert not Application.objects.exists()
    assert not LedgerEntry.objects.exists()


def test_offline_record_sync_does_not_create_an_approval_task(elm):
    actor = elm["actor"](7, "Leave Administrator", permissions=("elm.record.manage",))
    data = {
        **elm["payload"](category="EL"),
        "user_id": 1,
        "offline_reference": "ORDER/123",
        "unavailability_reason": "System unavailable",
        "authority_id": 3,
        "authority_role": "Registrar",
    }
    app = admin.offline_entry(actor, data)
    assert app.status == "approved"
    assert not WorkflowTask.objects.filter(application=app).exists()
    assert Account.objects.get(user_id=1, year=2026).el == Decimal("29")


def test_invalid_sla_reassignment_configuration_is_rejected(elm):
    config = EmployeeConfiguration.objects.get(user_id=1)
    values = {
        "user_id": 1,
        "designation": config.designation,
        "eligible_categories": ["CL"],
        "routes": {
            "CL": [
                {
                    "stage": "unit_head",
                    "user_id": 2,
                    "role": "Unit Head",
                    "escalation_role": "Unit Head",
                    "reassign_on_escalation": True,
                }
            ]
        },
    }
    with pytest.raises(DomainError):
        admin.validate_routes(values)


def test_policy_update_can_change_one_field_without_a_server_error(elm):
    actor = elm["actor"](7, "Leave Administrator", permissions=("elm.configuration.manage",))
    admin.save_configuration(actor, {"policy": {"reminder_hours": 12}})
    policy = Policy.objects.get(pk=1)
    assert policy.reminder_hours == 12
    assert policy.escalation_hours == 48
