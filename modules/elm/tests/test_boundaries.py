from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from core.api.exceptions import ConflictError, DomainError
from modules.elm.models import (
    Account,
    Application,
    AuditEntry,
    EmployeeConfiguration,
    HolidayCalendar,
    LedgerEntry,
    Policy,
    WorkflowTask,
)
from modules.elm.services import administration as admin
from modules.elm.services import workflow as w

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("kind,active", [("student", True), ("staff", False)])
def test_nonemployee_or_inactive_identity_cannot_submit(elm, kind, active):
    elm["people"][1] = replace(elm["people"][1], kind=kind, is_active=active)
    with pytest.raises(DomainError) as error:
        elm["submit"]()
    assert error.value.code == "not_employee"
    assert not Application.objects.exists()


def test_col_evidence_and_employee_category_eligibility_are_enforced(elm):
    Policy.objects.update(require_col_evidence=True)
    with pytest.raises(DomainError) as error:
        elm["submit"](category="COL")
    assert error.value.code == "medical_evidence_required"
    elm["submit"](category="COL", medical_reference="MED/1")
    EmployeeConfiguration.objects.filter(user_id=1).update(eligible_categories=["CL"])
    with pytest.raises(DomainError) as error:
        elm["submit"](category="EL", start=date(2026, 11, 3))
    assert error.value.code == "category_ineligible"


def test_staff_vl_is_rejected_and_faculty_calendar_provider_is_required(elm):
    with pytest.raises(DomainError) as error:
        elm["submit"](category="VL")
    assert error.value.code == "category_ineligible"
    with pytest.raises(DomainError) as error:
        w.submit(actor=elm["actor"](6, "faculty"), data=elm["payload"](category="VL"))
    assert error.value.code == "vacation_calendar_unavailable"


def test_vl_uses_external_provider_and_rejects_outside_dates(elm, settings, monkeypatch):
    settings.ELM_VACATION_PERIODS_PROVIDER = "test.provider"
    monkeypatch.setattr(
        w,
        "import_string",
        lambda path: lambda ids, start, end: {6: [(date(2026, 11, 2), date(2026, 11, 3))]},
    )
    app = w.submit(actor=elm["actor"](6, "faculty"), data=elm["payload"](category="VL"))
    assert app.category == "VL"
    with pytest.raises(DomainError) as error:
        w.submit(
            actor=elm["actor"](6, "faculty"),
            data=elm["payload"](category="VL", start=date(2026, 11, 4)),
        )
    assert error.value.code == "outside_vacation"


def test_published_calendar_remains_effective_until_replacement_publication(elm):
    actor = elm["actor"](7, "Leave Administrator", permissions=("elm.configuration.manage",))
    original = HolidayCalendar.objects.get(year=2026, published=True)
    draft = admin.save_calendar(
        actor,
        {"year": 2026, "holidays": [], "restricted_holidays": ["2026-11-05"], "published": False},
    )
    assert HolidayCalendar.objects.get(year=2026, published=True).pk == original.pk
    app = elm["submit"](category="RH")
    w.withdraw(actor=elm["actor"](), application_id=app.pk, revision=app.revision)
    replacement = admin.save_calendar(
        actor,
        {"year": 2026, "holidays": [], "restricted_holidays": ["2026-11-05"], "published": True},
    )
    assert HolidayCalendar.objects.get(year=2026, published=True).pk == replacement.pk
    draft.refresh_from_db()
    assert not draft.published
    with pytest.raises(DomainError) as error:
        elm["submit"](category="RH")
    assert error.value.code == "invalid_rh"


def test_rh_annual_balance_cannot_be_exceeded(elm):
    for day in (2, 3):
        elm["approved"](category="RH", start=date(2026, 11, day))
    with pytest.raises(DomainError) as error:
        elm["submit"](category="RH", start=date(2026, 11, 4))
    assert error.value.code == "insufficient_balance"


def test_second_approval_revalidates_balance_and_rolls_back_on_failure(elm):
    first = elm["submit"](start=date(2026, 11, 2), end=date(2026, 11, 6))
    second = elm["submit"](start=date(2026, 11, 9), end=date(2026, 11, 13))
    elm["decide"](first)
    with pytest.raises(DomainError) as error:
        elm["decide"](second)
    assert error.value.code == "insufficient_balance"
    second.refresh_from_db()
    assert second.status == "unit_head"
    assert WorkflowTask.objects.filter(application=second, pending=True).count() == 1
    assert not LedgerEntry.objects.filter(application=second).exists()
    assert Account.objects.get(user_id=1, year=2026).cl == Decimal("3")


def test_substitute_cannot_be_self_or_on_overlapping_leave(elm):
    EmployeeConfiguration.objects.filter(user_id=1).update(coverage_required=True)
    with pytest.raises(DomainError) as error:
        elm["submit"](substitute_id=1)
    assert error.value.code == "invalid_substitute"
    w.submit(actor=elm["actor"](4), data=elm["payload"]())
    with pytest.raises(ConflictError):
        elm["submit"](substitute_id=4)


def test_year_end_reports_pending_account_and_does_not_partially_close(elm):
    app = elm["submit"](start=date(2025, 11, 3))
    result = admin.process_year_end(2025)
    assert result["processed"] == 0
    assert result["exceptions"][0]["account_user_id"] == app.user_id
    account = Account.objects.get(user_id=1, year=2025)
    assert not account.year_end_processed
    assert account.cl == Decimal("8")


def test_offline_reference_correction_preserves_sanction_balance_and_history(elm):
    actor = elm["actor"](7, "Leave Administrator", permissions=("elm.record.manage",))
    data = {
        **elm["payload"](),
        "user_id": 1,
        "offline_reference": "OLD/1",
        "unavailability_reason": "Outage",
        "authority_id": 2,
        "authority_role": "Unit Head",
    }
    app = admin.offline_entry(actor, data)
    admin.correct_reference(actor, app.pk, "Clerical reference correction", "NEW/1")
    app.refresh_from_db()
    assert app.offline_reference == "NEW/1"
    assert app.status == "approved"
    assert Account.objects.get(user_id=1, year=2026).cl == Decimal("7")
    assert LedgerEntry.objects.filter(application=app).count() == 1
    assert AuditEntry.objects.filter(application=app, action="correct_reference").count() == 1
    with pytest.raises(DomainError):
        admin.correct_reference(actor, app.pk, "Remove evidence", " ")


def test_director_configuration_cannot_use_normal_approval_route(elm):
    config = EmployeeConfiguration.objects.get(user_id=1)
    with pytest.raises(DomainError):
        admin.validate_routes(
            {
                "user_id": 1,
                "designation": "Director",
                "eligible_categories": config.eligible_categories,
                "routes": config.routes,
            }
        )
