from django.test import TestCase

from modules.elm.models import HierarchyRule
from modules.elm.services import routing as r

S = HierarchyRule.Stage


class RoutingTests(TestCase):
    def rule(self, stage, approver, status="published", **kw):
        return HierarchyRule.objects.create(stage=stage, approver_id=approver,
                                            status=status, **kw)

    def test_default_unit_head(self):
        self.rule(S.UNIT_HEAD, 10)
        self.assertEqual(r.approver_for(S.UNIT_HEAD, applicant_id=1, unit="CSE"), 10)

    def test_specific_unit_beats_default(self):
        self.rule(S.UNIT_HEAD, 10)
        self.rule(S.UNIT_HEAD, 11, unit="CSE")
        self.assertEqual(r.approver_for(S.UNIT_HEAD, applicant_id=1, unit="CSE"), 11)
        self.assertEqual(r.approver_for(S.UNIT_HEAD, applicant_id=1, unit="ECE"), 10)

    def test_leave_type_rule_beats_generic(self):
        self.rule(S.FINAL, 40)
        self.rule(S.FINAL, 50, leave_type="VL", applicant_kind="faculty")
        got = r.approver_for(S.FINAL, applicant_id=1, unit="CSE", kind="faculty", leave_type="VL")
        self.assertEqual(got, 50)
        got = r.approver_for(S.FINAL, applicant_id=1, unit="CSE", kind="staff", leave_type="EL")
        self.assertEqual(got, 40)

    def test_draft_rules_ignored(self):
        self.rule(S.UNIT_HEAD, 10, status="draft")
        with self.assertRaises(r.RoutingError):
            r.approver_for(S.UNIT_HEAD, applicant_id=1)

    def test_no_rule_raises(self):
        with self.assertRaises(r.RoutingError):
            r.approver_for(S.FINAL, applicant_id=1)

    def test_nobody_approves_own_leave(self):
        self.rule(S.UNIT_HEAD, 10, unit="CSE")     # applicant 10 is the CSE head
        self.rule(S.UNIT_HEAD, 99)                 # fallback
        self.assertEqual(r.approver_for(S.UNIT_HEAD, applicant_id=10, unit="CSE"), 99)

    def test_establishment_configured(self):
        self.assertFalse(r.establishment_configured(applicant_id=1))
        self.rule(S.ESTABLISHMENT, 20, leave_type="EL")
        self.assertTrue(r.establishment_configured(applicant_id=1, leave_type="EL"))
        self.assertFalse(r.establishment_configured(applicant_id=1, leave_type="CL"))

    def test_is_director(self):
        self.rule(S.DIRECTOR, 7)
        self.assertTrue(r.is_director(7))
        self.assertFalse(r.is_director(8))
