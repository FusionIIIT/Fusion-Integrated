"""Unit & integration tests verifying VMS Business Rules (BR-001 to BR-047)."""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from modules.vms.models.access import AccessPolicy, CampusZone, GateAlert
from modules.vms.models.visits import VisitRequest
from modules.vms.services.access_service import (
    validate_zone_access,
)
from modules.vms.services.blacklist_service import (
    add_to_blacklist,
)
from modules.vms.services.exceptions import (
    BlacklistMatchException,
    CheckoutBlockedException,
    DuplicatePassException,
    UnauthorizedZoneException,
)
from modules.vms.services.gate_service import (
    check_out_visitor,
    validate_and_check_in_visitor,
)
from modules.vms.services.muster_service import (
    audit_muster_overstay_evictions,
    start_emergency_muster,
)
from modules.vms.services.pass_service import (
    issue_visit_pass,
)
from modules.vms.services.visitor_service import (
    register_visitor,
)


class VMSBusinessRulesTests(TestCase):
    def setUp(self):
        # Create standard policy and zones
        self.policy = AccessPolicy.objects.create(
            policy_name="Standard Campus Policy",
            default_walk_in_duration_hours=4,
            default_guest_duration_hours=4,
            max_daily_extension_hours=2,
            is_active=True,
        )
        self.main_gate_zone = CampusZone.objects.create(
            code="ZONE-GATE",
            name="Main Gate",
            is_active=True,
        )
        self.admin_zone = CampusZone.objects.create(
            code="ZONE-ADMIN",
            name="Administrative Block",
            is_active=True,
        )
        self.server_zone = CampusZone.objects.create(
            code="ZONE-SERVER",
            name="Data Center / Server Room",
            requires_special_elevation=True,
            is_active=True,
        )

    def test_br_001_and_004_and_024_blacklist_exact_match(self):
        """BR-001, BR-004, BR-024: Exact match triggers exception and creates critical alert."""
        add_to_blacklist(
            full_name="Bad Actor",
            phone="9000000001",
            id_number="BAD123",
            reason="Prior disciplinary ban",
            added_by_user_id=1001,
        )
        # Attempting to register blacklisted phone raises exception
        with self.assertRaises(BlacklistMatchException) as ctx:
            register_visitor(
                full_name="Bad Actor",
                phone="9000000001",
                id_number="BAD123",
            )
        self.assertEqual(ctx.exception.rule_id, "BR-004")
        # Check that critical alert was logged
        alert = GateAlert.objects.filter(alert_type="blacklist_hit").first()
        self.assertIsNotNone(alert)
        self.assertEqual(alert.severity, "critical")

    def test_br_017_and_020_same_day_duplicate_pass_prevention(self):
        """BR-017, BR-020: Same visitor cannot obtain duplicate active passes on same day."""
        visitor = register_visitor(full_name="Amit Patel", phone="9111111111", id_number="ID111")
        now = timezone.now()
        visit1 = VisitRequest.objects.create(
            visitor=visitor,
            host_user_id=2001,
            purpose="Meeting 1",
            intended_start=now,
            intended_end=now + timedelta(hours=3),
            status="approved",
        )
        issue_visit_pass(visit=visit1, pass_type="walk_in")

        # Second pass request on same day must fail
        visit2 = VisitRequest.objects.create(
            visitor=visitor,
            host_user_id=2002,
            purpose="Meeting 2",
            intended_start=now,
            intended_end=now + timedelta(hours=3),
            status="approved",
        )
        with self.assertRaises(DuplicatePassException) as ctx:
            issue_visit_pass(visit=visit2, pass_type="walk_in")
        self.assertEqual(ctx.exception.rule_id, "BR-020")

    def test_br_032_walk_in_4_hour_duration(self):
        """BR-032: Walk-in pass default duration = 4 hours."""
        visitor = register_visitor(full_name="Walk-in Guest", phone="9222222222", id_number="ID222")
        now = timezone.now()
        visit = VisitRequest.objects.create(
            visitor=visitor,
            host_user_id=1001,
            purpose="General Walk-in",
            intended_start=now,
            intended_end=now + timedelta(hours=4),
            status="approved",
        )
        pass_record = issue_visit_pass(visit=visit, pass_type="walk_in")
        duration = pass_record.valid_to - pass_record.valid_from
        self.assertEqual(round(duration.total_seconds() / 3600), 4)

    def test_br_002_and_028_gate_check_in_and_alert_auto_closure(self):
        """BR-002, BR-028: Valid entrance auto-closes pending non-critical alerts."""
        visitor = register_visitor(full_name="Sunil Das", phone="9333333333", id_number="ID333")
        now = timezone.now()
        visit = VisitRequest.objects.create(
            visitor=visitor,
            host_user_id=1001,
            purpose="Interview",
            intended_start=now,
            intended_end=now + timedelta(hours=4),
            status="approved",
        )
        pass_record = issue_visit_pass(visit=visit, pass_type="registered_guest")

        # Create a pending warning alert for visitor
        alert = GateAlert.objects.create(
            alert_type="overstay",
            severity="medium",
            status="open",
            visitor=visitor,
            details="Prior overstay inquiry",
        )

        # Gate check-in
        validate_and_check_in_visitor(
            qr_code_hash=pass_record.qr_code_hash,
            gate_machine_id="GATE-01",
            security_user_id=9999,
        )
        alert.refresh_from_db()
        self.assertEqual(alert.status, "closed")
        self.assertEqual(visit.status, "on_site")

    def test_br_023_no_duplicate_checkout(self):
        """BR-023: Cannot re-log checkout when visit already complete."""
        visitor = register_visitor(full_name="Vikas Roy", phone="9444444444", id_number="ID444")
        now = timezone.now()
        visit = VisitRequest.objects.create(
            visitor=visitor,
            host_user_id=1001,
            purpose="Delivery",
            intended_start=now,
            intended_end=now + timedelta(hours=2),
            status="approved",
        )
        pass_record = issue_visit_pass(visit=visit, pass_type="walk_in")
        validate_and_check_in_visitor(
            qr_code_hash=pass_record.qr_code_hash,
            gate_machine_id="GATE-01",
            security_user_id=9999,
        )

        # First checkout succeeds
        check_out_visitor(pass_number=pass_record.pass_number, security_user_id=9999)

        # Second checkout must raise CheckoutBlockedException
        with self.assertRaises(CheckoutBlockedException) as ctx:
            check_out_visitor(pass_number=pass_record.pass_number, security_user_id=9999)
        self.assertEqual(ctx.exception.rule_id, "BR-023")

    def test_br_005_and_041_zone_access_enforcement(self):
        """BR-005, BR-041: Authorized zone passes; unauthorized zone triggers denial and alert."""
        visitor = register_visitor(full_name="Pooja Sen", phone="9555555555", id_number="ID555")
        now = timezone.now()
        visit = VisitRequest.objects.create(
            visitor=visitor,
            host_user_id=1001,
            purpose="Library Visit",
            intended_start=now,
            intended_end=now + timedelta(hours=4),
            status="approved",
        )
        pass_record = issue_visit_pass(
            visit=visit,
            allowed_zones=["Administrative Block"],
        )

        # Authorized zone entry passes
        self.assertTrue(validate_zone_access(pass_record, "ZONE-ADMIN"))

        # Unauthorized zone entry raises UnauthorizedZoneException and logs alert
        with self.assertRaises(UnauthorizedZoneException) as ctx:
            validate_zone_access(pass_record, "ZONE-SERVER")
        self.assertEqual(ctx.exception.rule_id, "BR-041")

        alert = GateAlert.objects.filter(alert_type="unauthorized_zone").first()
        self.assertIsNotNone(alert)

    def test_br_045_emergency_muster_overstay_evictions(self):
        """BR-045: Muster duration > 15 minutes triggers eviction alert for unaccounted visitors."""
        visitor = register_visitor(full_name="Muster Guest", phone="9666666666", id_number="ID666")
        now = timezone.now()
        visit = VisitRequest.objects.create(
            visitor=visitor,
            host_user_id=1001,
            purpose="Lab Visit",
            intended_start=now,
            intended_end=now + timedelta(hours=4),
            actual_arrival=now,
            status="on_site",
        )
        issue_visit_pass(visit=visit, pass_type="registered_guest")

        muster = start_emergency_muster(initiated_by_user_id=9999, reason="Test Fire Evacuation")
        self.assertEqual(muster.total_on_site_at_start, 1)

        # Simulate 20 minutes elapsed since muster started
        muster.started_at = timezone.now() - timedelta(minutes=20)
        muster.save()

        # Audit overstay evictions
        alerts_count = audit_muster_overstay_evictions(muster)
        self.assertGreaterEqual(alerts_count, 1)
        eviction_alert = GateAlert.objects.filter(alert_type="muster_eviction").first()
        self.assertIsNotNone(eviction_alert)
        self.assertEqual(eviction_alert.severity, "critical")
