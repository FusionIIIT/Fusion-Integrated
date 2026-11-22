"""Schema and constants must agree: the domain's status sets, the models' choices, the
migrations, and the module boundary."""
import subprocess
import sys
from pathlib import Path

import pytest
from django.core.management import call_command
from django.db import IntegrityError, transaction

from modules.mms.domain import state_machine as sm
from modules.mms.models import (
    MessBill,
    MessDeregistration,
    MessMenu,
    MessRebate,
    MessRegistration,
    MessRegistrationWindow,
    SpecialFoodRequest,
    VacationFoodResponse,
    VacationFoodSurvey,
)
from modules.mms.tests import factories as f

ROOT = Path(__file__).resolve().parents[3]


def _choices(model, field="status"):
    return {c[0] for c in model._meta.get_field(field).choices}


# ---- the domain's vocabulary equals the database's ------------------------------
@pytest.mark.parametrize(("model", "constants"), [
    (MessRegistration, sm.REG_STATUSES),
    (MessDeregistration, sm.DEREG_STATUSES),
    (MessRebate, sm.REBATE_STATUSES),
    (SpecialFoodRequest, sm.SPECIAL_FOOD_STATUSES),
    (MessBill, sm.BILL_STATUSES),
    (MessRegistrationWindow, {sm.WINDOW_OPEN, sm.WINDOW_CLOSED}),
    (VacationFoodSurvey, {sm.SURVEY_OPEN, sm.SURVEY_CLOSED}),
], ids=lambda x: getattr(x, "__name__", None) or "")
def test_status_constants_match_model_choices(model, constants):
    assert _choices(model) == constants


def test_menu_choices_match_the_domains_days_and_meals():
    assert _choices(MessMenu, "day_of_week") == sm.DAYS_OF_WEEK
    assert _choices(MessMenu, "meal_type") == sm.MEAL_TYPES


# ---- constraints the services lean on ------------------------------------------
@pytest.mark.django_db
def test_one_menu_row_per_day_and_meal():
    f.MenuFactory()
    with pytest.raises(IntegrityError), transaction.atomic():
        MessMenu.objects.create(day_of_week="monday", meal_type="lunch", items=[])


@pytest.mark.django_db
def test_one_bill_per_student_per_month():
    f.BillFactory()
    with pytest.raises(IntegrityError), transaction.atomic():
        f.BillFactory()


@pytest.mark.django_db
def test_one_vacation_response_per_student_per_survey():
    s = f.VacationSurveyFactory()
    VacationFoodResponse.objects.create(survey=s, user_id=1)
    with pytest.raises(IntegrityError), transaction.atomic():
        VacationFoodResponse.objects.create(survey=s, user_id=1)


@pytest.mark.django_db
def test_money_columns_hold_two_decimal_places_exactly():
    from decimal import Decimal
    b = f.BillFactory(total_amount=Decimal("1234.56"))
    b.refresh_from_db()
    assert b.total_amount == Decimal("1234.56")


# ---- the module boundary and CI gates, run where a developer will see them -------
@pytest.mark.django_db
def test_migrations_are_in_sync_with_the_models():
    """A model change without a migration passes every other test and breaks deploy."""
    call_command("makemigrations", "mms", check=True, dry_run=True, verbosity=0)


@pytest.mark.parametrize("script", ["no_cross_module_fk", "contracts_are_plural"])
def test_ci_boundary_checks_pass_for_mms(script):
    out = subprocess.run([sys.executable, "-m", f"ops.checks.{script}"], cwd=ROOT,
                         capture_output=True, text=True, check=False)
    assert out.returncode == 0, out.stdout + out.stderr


def test_import_linter_contracts_hold():
    pytest.importorskip("importlinter")
    out = subprocess.run([sys.executable, "-m", "importlinter.cli", "--config", ".importlinter"],
                         cwd=ROOT, capture_output=True, text=True, check=False)
    if out.returncode != 0 and "No such file" in out.stderr:
        pytest.skip("lint-imports entry point unavailable")
    assert out.returncode == 0, out.stdout + out.stderr
