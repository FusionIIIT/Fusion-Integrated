from django.test import SimpleTestCase, TestCase

from modules.elm.api.serializers import (
    LeaveHierarchySerializer,
    LeavePolicySerializer,
    OfflineLeaveRecordSerializer,
    VacationPeriodSerializer,
)


class ELMInputSerializerTests(SimpleTestCase):
    def test_offline_record_rejects_reversed_dates(self):
        serializer = OfflineLeaveRecordSerializer(
            data={
                "applicant_user_id": 12,
                "employee_kind": "staff",
                "category": "EL",
                "start_date": "2026-10-20",
                "end_date": "2026-10-19",
                "purpose": "Historical approved leave",
                "evidence_reference": "OFFLINE-42",
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("end_date", serializer.errors)

    def test_offline_record_rejects_out_of_range_user_id(self):
        serializer = OfflineLeaveRecordSerializer(
            data={
                "applicant_user_id": 999999999999999,
                "employee_kind": "staff",
                "category": "EL",
                "start_date": "2026-10-19",
                "end_date": "2026-10-20",
                "purpose": "Historical approved leave",
                "evidence_reference": "OFFLINE-42",
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("applicant_user_id", serializer.errors)

    def test_vacation_period_rejects_reversed_dates(self):
        serializer = VacationPeriodSerializer(
            data={
                "name": "Winter break",
                "start_date": "2026-12-20",
                "end_date": "2026-12-10",
                "external_reference": "",
                "active": True,
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("end_date", serializer.errors)


class ELMPolicyAndHierarchySerializerTests(TestCase):
    def test_policy_rejects_negative_annual_entitlement(self):
        serializer = LeavePolicySerializer(
            data={
                "annual_entitlement": "-1.00",
                "employee_scope": "all",
                "carry_forward": False,
                "continuous_counting": False,
                "medical_evidence_required": False,
                "enabled": True,
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("annual_entitlement", serializer.errors)

    def test_hierarchy_rejects_nonpositive_authority_ids(self):
        serializer = LeaveHierarchySerializer(
            data={
                "unit_key": "Computer Science",
                "unit_head_user_id": 10,
                "establishment_user_id": None,
                "sanctioning_authority_user_id": -4,
                "director_user_id": None,
                "active": True,
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("sanctioning_authority_user_id", serializer.errors)
