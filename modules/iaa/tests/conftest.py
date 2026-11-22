"""Fixtures: the cast of actors, and a published policy with a financial year and a budget."""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.cache import cache
from django.utils import timezone

from modules.iaa.services import configuration
from modules.iaa.tests.helpers import POLICY, USERS, cast


@pytest.fixture(autouse=True)
def fresh_throttle_counts():
    """Throttle counts live in the cache; one test's writes must not count against the next."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def people(stub_iam):
    stub_iam(users=USERS)
    return cast()


@pytest.fixture
def configured(people):
    """What Finance and the approvers need before any request can move."""
    today = timezone.localdate()
    year = configuration.add_financial_year(
        people.admin, code="2026-27", starts_on=today - timedelta(days=30),
        ends_on=today + timedelta(days=300))
    configuration.add_budget_entry(people.admin, financial_year_id=year.pk, department="CSE",
                                   kind="allocation", amount=Decimal("500000"))
    configuration.publish_policy(people.admin, POLICY)
    return year
