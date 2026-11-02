"""Unit tests for VMS database models and schema constraints."""
from django.test import TestCase
from django.utils import timezone
from modules.vms.models.visitors import (
    Visitor,
    BlacklistRecord,
    SafeListRecord,
    VisitorIDDocument,
)
from modules.vms.models.visits import (
    VisitRequest,
    VisitPass,
    VisitLog,
)
from modules.vms.models.access import (
    CampusZone,
    AccessPolicy,
    GateAlert,
)
from modules.vms.models.muster import (
    EmergencyMuster,
    MusterRollCall,
)


class VMSModelTests(TestCase):
    def setUp(self):
        self.visitor = Visitor.objects.create(
            full_name="Rajesh Sharma",
            phone="9876543210",
            email="rajesh@example.com",
            identity_type="aadhaar",
            id_number="1234-5678-9012",
            organization="Tech Labs",
        )

    def test_visitor_creation(self):
        self.assertEqual(str(self.visitor), "Rajesh Sharma (9876543210)")
        self.assertTrue(self.visitor.is_active)

    def test_blacklist_record(self):
        bl = BlacklistRecord.objects.create(
            full_name="Ramesh Kumar",
            phone="9999988888",
            id_number="PAN12345",
            reason="Security breach at main gate",
            added_by_user_id=1001,
        )
        self.assertIn("BLACKLISTED", str(bl))
        self.assertTrue(bl.is_active)

    def test_safelist_record(self):
        sl = SafeListRecord.objects.create(
            full_name="Dr. Anita Roy",
            phone="9123456780",
            id_number="DL998877",
            category="vip_guest",
            valid_until=timezone.now() + timezone.timedelta(days=30),
            added_by_user_id=1001,
        )
        self.assertIn("SAFELIST", str(sl))

    def test_visit_and_pass_lifecycle(self):
        now = timezone.now()
        visit = VisitRequest.objects.create(
            visitor=self.visitor,
            host_user_id=2005,
            purpose="Research Collaboration",
            intended_start=now,
            intended_end=now + timezone.timedelta(hours=4),
            status="approved",
        )
        vpass = VisitPass.objects.create(
            visitor=self.visitor,
            visit=visit,
            pass_type="registered_guest",
            valid_from=now,
            valid_to=now + timezone.timedelta(hours=4),
            allowed_zones=["Main Gate", "Computer Center"],
        )
        self.assertTrue(vpass.pass_number.startswith("PASS-"))
        self.assertTrue(vpass.qr_code_hash.startswith("QR-"))
        self.assertEqual(vpass.status, "active")

    def test_emergency_muster_and_roll_call(self):
        muster = EmergencyMuster.objects.create(
            initiated_by_user_id=9001,
            reason="Fire drill evacuation",
        )
        self.assertTrue(muster.muster_code.startswith("MUSTER-"))
        self.assertEqual(muster.status, "in_progress")

        roll = MusterRollCall.objects.create(
            muster=muster,
            visitor=self.visitor,
            status="safe",
            last_known_zone="Assembly Point 1",
        )
        self.assertEqual(roll.status, "safe")
