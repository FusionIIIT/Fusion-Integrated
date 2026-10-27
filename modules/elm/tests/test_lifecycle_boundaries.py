from datetime import date
from decimal import Decimal

import pytest

from core.api.exceptions import ConflictError
from modules.elm.models import (
    Account,
    EmployeeConfiguration,
    LedgerEntry,
    Notification,
    WorkflowTask,
)
from modules.elm.services import administration as admin
from modules.elm.services import workflow as w

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "stage", ["substitute", "applicant_action", "unit_head", "establishment", "sanction"]
)
def test_withdrawal_is_immediate_at_each_pending_stage(elm, stage):
    config = EmployeeConfiguration.objects.get(user_id=1)
    if stage in ("substitute", "applicant_action"):
        config.coverage_required = True
    config.routes["EL"].insert(
        1, {"stage": "establishment", "user_id": 7, "role": "Deputy Registrar (Estt.)"}
    )
    config.save()
    app = elm["submit"](category="EL", substitute_id=4 if config.coverage_required else None)
    if stage == "applicant_action":
        elm["decide"](app, "decline", user_id=4, role="staff", reason="Unavailable")
    elif stage in ("establishment", "sanction"):
        elm["decide"](app, "recommend")
        if stage == "sanction":
            elm["decide"](app, "forward", user_id=7, role="Deputy Registrar (Estt.)")
    app.refresh_from_db()
    assert app.status == stage
    assigned = app.tasks.order_by("id").last()
    w.withdraw(actor=elm["actor"](), application_id=app.pk, revision=app.revision)
    app.refresh_from_db()
    assert app.status == "withdrawn"
    assert not WorkflowTask.objects.filter(application=app, pending=True).exists()
    assert not LedgerEntry.objects.filter(application=app).exists()
    with pytest.raises(ConflictError):
        elm["decide"](app, user_id=assigned.user_id, role=assigned.role)


@pytest.mark.parametrize("outcome", ["withdraw", "reject"])
def test_unsuccessful_extension_preserves_original_leave_and_balance(elm, outcome):
    parent = elm["approved"](category="EL", start=date(2026, 10, 26), end=date(2026, 10, 30))
    change = w.lifecycle(
        actor=elm["actor"](),
        application_id=parent.pk,
        kind="extension",
        reason="More time",
        end_date=date(2026, 11, 3),
    )
    if outcome == "withdraw":
        w.withdraw(actor=elm["actor"](), application_id=change.pk, revision=change.revision)
    else:
        elm["decide"](change, "recommend")
        elm["decide"](change, "reject", user_id=3, role="Registrar", reason="Not granted")
    parent.refresh_from_db()
    assert parent.effective_end_date == date(2026, 10, 30)
    assert parent.status == "approved"
    assert Account.objects.get(user_id=1, year=2026).el == Decimal("25")
    assert not LedgerEntry.objects.filter(application=change).exists()


def test_staff_rollover_carries_el_col_and_lapses_annual_categories(elm):
    with w.transaction.atomic():
        account = w.account_for(1, 2025)
    Account.objects.filter(pk=account.pk).update(el=7, col=4)
    assert admin.process_account_year(1, 2025)
    following = Account.objects.get(user_id=1, year=2026)
    assert following.el == Decimal("37")
    assert following.col == Decimal("24")
    assert following.cl == Decimal("8")
    assert following.rh == Decimal("2")
    assert following.scl == Decimal("15")
    account.refresh_from_db()
    assert all(getattr(account, category.lower()) == 0 for category in w.rules.CATEGORIES)


def test_opposite_cl_halves_post_one_day_in_total(elm):
    elm["approved"](half="first")
    elm["approved"](half="second")
    assert Account.objects.get(user_id=1, year=2026).cl == Decimal("7")
    with pytest.raises(ConflictError):
        elm["submit"](half="first")


def test_final_decision_and_task_assignment_notify_the_correct_users(elm):
    app = elm["submit"]()
    assert Notification.objects.filter(application=app, user_id=2).count() == 1
    elm["decide"](app)
    assert (
        Notification.objects.filter(
            application=app, user_id=1, message__contains="approved"
        ).count()
        == 1
    )
