"""What the ERP can say someone is, and what it cannot."""
from types import SimpleNamespace

from django.test import SimpleTestCase

from iam.erp_source import _kind


def extra(user_type):
    return SimpleNamespace(user_type=user_type)


class KindInferenceTests(SimpleTestCase):
    def test_the_erps_own_classification_wins(self):
        assert _kind(extra("student"), holds_designation=False) == "student"
        assert _kind(extra("faculty"), holds_designation=False) == "faculty"

    def test_it_is_normalised(self):
        assert _kind(extra("Faculty"), holds_designation=True) == "faculty"

    def test_a_classified_row_with_a_blank_type_falls_back_to_staff(self):
        # There is an ExtraInfo, so somebody set this person up deliberately.
        assert _kind(extra(""), holds_designation=False) == "staff"

    def test_an_unclassified_account_holding_a_designation_is_staff(self):
        # The designation is the evidence; the missing ExtraInfo is a gap in the record.
        assert _kind(None, holds_designation=True) == "staff"

    def test_an_unclassified_account_with_nothing_at_all_is_unknown(self):
        # Regression: this used to return "staff" and put orphaned rows on the payroll.
        assert _kind(None, holds_designation=False) == "unknown"

    def test_unknown_is_a_declared_kind_and_the_model_default(self):
        from iam.models import IamUser

        assert "unknown" in dict(IamUser.KINDS)
        # Fail closed: a row written without an explicit kind is not an employee.
        assert IamUser._meta.get_field("kind").default == "unknown"
