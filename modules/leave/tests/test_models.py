from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from modules.leave.models import (
    LeaveApplication,
    LeaveApplicationTransition,
    LeaveBalance,
    LeaveCategory,
)


@pytest.fixture
def cl():
    """Fixture for Casual Leave category."""
    return LeaveCategory.objects.create(code="CL", name="Casual Leave")

@pytest.fixture
def el():
    """Fixture for Earned Leave category."""
    return LeaveCategory.objects.create(code="EL", name="Earned Leave")

@pytest.fixture
def make_app():
    """Helper to create a LeaveApplication with default values."""
    def _make_app(category, **overrides):
        defaults = {
            "user_id": 1,
            "start_date": date(2026, 11, 2),
            "end_date": date(2026, 11, 2),
            "reason": "test",
            "category": category,
        }
        defaults.update(overrides)
        return LeaveApplication.objects.create(**defaults)
    return _make_app

@pytest.mark.django_db
def test_same_user_can_apply_twice_for_same_category(cl, make_app):
    """Test that a user can apply multiple times for the same category."""
    make_app(cl)
    make_app(cl)
    assert LeaveApplication.objects.filter(user_id=1, category=cl).count() == 2

@pytest.mark.django_db
def test_default_status_is_awaiting_unit_head(cl, make_app):
    """Test that the default status of a new application is 'awaiting_unit_head'."""
    app = make_app(cl)
    assert app.status == "awaiting_unit_head"

@pytest.mark.django_db
def test_end_before_start_rejected(cl, make_app):
    """Test that an application with end_date before start_date raises IntegrityError."""
    with transaction.atomic(), pytest.raises(IntegrityError):
        make_app(cl, start_date=date(2026, 11, 2), end_date=date(2026, 11, 1))

@pytest.mark.django_db
def test_half_day_on_single_day_allowed(cl, make_app):
    """Test that half day is allowed on a single day."""
    app = make_app(cl, half_day="first")
    assert app.pk is not None

@pytest.mark.django_db
def test_half_day_on_multi_day_rejected(cl, make_app):
    """Test that half day is rejected on a multi-day range."""
    with transaction.atomic(), pytest.raises(IntegrityError):
        make_app(cl, half_day="first", end_date=date(2026, 11, 3))

@pytest.mark.django_db
def test_no_half_day_multi_day_allowed(cl, make_app):
    """Test that multi-day range is allowed without half day specified."""
    app = make_app(cl, end_date=date(2026, 11, 4), half_day="")
    assert app.pk is not None

@pytest.mark.django_db
def test_extension_links_to_parent(el, make_app):
    """Test that an extension correctly links to its parent application."""
    parent = make_app(el)
    ext = make_app(el, parent=parent)
    assert ext.parent == parent
    assert parent.extensions.count() == 1

@pytest.mark.django_db
def test_balance_unique_per_category_user_year(cl, make_app):
    """Test that balance is unique per category, user, and year."""
    # First balance (should pass)
    balance1 = LeaveBalance.objects.create(
        category=cl, user_id=1, year=2026, balance_days=Decimal("10.00")
    )
    assert balance1.pk is not None

    # Second balance for same user/category/year (should fail)
    with transaction.atomic(), pytest.raises(IntegrityError):
        LeaveBalance.objects.create(
            category=cl, user_id=1, year=2026, balance_days=Decimal("5.00")
        )

    # Balance for different year (should pass)
    balance2 = LeaveBalance.objects.create(
        category=cl, user_id=1, year=2027, balance_days=Decimal("10.00")
    )
    assert balance2.pk is not None

@pytest.mark.django_db
def test_balance_cannot_be_negative(cl):
    """Test that balance_days cannot be negative."""
    with transaction.atomic(), pytest.raises(IntegrityError):
        LeaveBalance.objects.create(
            category=cl, user_id=1, year=2026, balance_days=Decimal("-0.5")
        )

@pytest.mark.django_db
def test_balance_keeps_fractions(cl):
    """Test that Decimal values are correctly stored and retrieved."""
    initial_balance = Decimal("2.50")
    balance = LeaveBalance.objects.create(
        category=cl, user_id=1, year=2026, balance_days=initial_balance
    )

    # Refresh from DB to ensure persistence
    balance.refresh_from_db()
    assert balance.balance_days == initial_balance

@pytest.mark.django_db
def test_transition_records_audit_row(make_app, cl):
    """Test that LeaveApplicationTransition records an audit row correctly."""
    app = make_app(cl)

    transition = LeaveApplicationTransition.objects.create(
        application=app,
        from_status="awaiting_unit_head",
        to_status="approved",
        actor_user_id=9,
        actor_label="unit_head",
        reason="Approved by Unit Head"
    )

    assert app.transitions.count() == 1
    assert transition.at is not None

@pytest.mark.django_db
def test_category_code_is_unique(cl):
    """LeaveCategory.code is unique."""
    with pytest.raises(IntegrityError), transaction.atomic():
        LeaveCategory.objects.create(code="CL", name="Duplicate")

@pytest.mark.django_db
def test_str_of_application_contains_status(cl, make_app):
    """Test that the string representation of LeaveApplication includes its status."""
    app = make_app(cl)
    app.status = "awaiting_unit_head"
    app.save()

    assert "awaiting_unit_head" in str(app)
