"""BR-EL-001. The policy decides which categories reach which employee."""
from datetime import date

import pytest

from core.api.exceptions import BadRequestError
from modules.leave.domain.categories import Category
from modules.leave.models import CategoryRule
from modules.leave.services import requests as service
from modules.leave.tests import factories
from modules.leave.tests.factories import YEAR

pytestmark = pytest.mark.django_db
STAFF, FACULTY = 501, 502


def apply_for(category, *, faculty, user_id, **kw):
    return service.submit(
        user_id=user_id, category=category, starts_on=date(YEAR, 5, 20),
        ends_on=date(YEAR, 5, 21), reason="x", unit="CSE", faculty=faculty,
        designations=frozenset({"Assistant Professor"}), **kw)


class TestWhoMayTakeWhat:
    def test_faculty_may_take_vacation_leave(self):
        factories.setup_all(FACULTY)
        factories.credit(FACULTY, Category.VL, 60)

        created = apply_for(Category.VL, faculty=True, user_id=FACULTY)

        assert created.category == "VL"

    def test_staff_may_not_even_holding_a_balance(self):
        factories.setup_all(STAFF)
        # A correction or an opening figure is enough to pass the balance check.
        factories.credit(STAFF, Category.VL, 60)

        with pytest.raises(BadRequestError, match="not available to you"):
            apply_for(Category.VL, faculty=False, user_id=STAFF)

    def test_a_category_open_to_everyone_stays_open(self):
        factories.setup_all(STAFF)

        created = service.submit(
            user_id=STAFF, category=Category.CL, starts_on=date(YEAR, 5, 20),
            ends_on=date(YEAR, 5, 21), reason="x", unit="CSE", faculty=False,
            designations=frozenset({"Junior Assistant"}))

        assert created.category == "CL"


class TestEvidence:
    def _demand_evidence(self, policy, category=Category.SCL):
        CategoryRule.objects.filter(
            policy=policy, category=category.value).update(requires_evidence=True)

    def test_a_category_needing_evidence_refuses_without_it(self):
        policy, _ = factories.setup_all(STAFF)
        factories.credit(STAFF, Category.SCL, 15)
        self._demand_evidence(policy)

        with pytest.raises(BadRequestError, match="certificate or letter"):
            apply_for(Category.SCL, faculty=False, user_id=STAFF)

    def test_whitespace_is_not_evidence(self):
        policy, _ = factories.setup_all(STAFF)
        factories.credit(STAFF, Category.SCL, 15)
        self._demand_evidence(policy)

        with pytest.raises(BadRequestError, match="certificate or letter"):
            apply_for(Category.SCL, faculty=False, user_id=STAFF,
                      evidence_reference="   ")

    def test_a_reference_satisfies_it_and_is_kept(self):
        policy, _ = factories.setup_all(STAFF)
        factories.credit(STAFF, Category.SCL, 15)
        self._demand_evidence(policy)

        created = apply_for(Category.SCL, faculty=False, user_id=STAFF,
                            evidence_reference="MC/2026/114")

        assert created.evidence_reference == "MC/2026/114"

    def test_a_category_not_demanding_evidence_needs_none(self):
        factories.setup_all(STAFF)

        created = apply_for(Category.CL, faculty=False, user_id=STAFF)

        assert created.evidence_reference == ""
