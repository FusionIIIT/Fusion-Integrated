"""Comprehensive unit tests for VMS query selectors and filtering logic."""

from datetime import timedelta

import pytest
from django.utils import timezone

from modules.vms.models import (
    BlacklistRegistry,
    CampusGate,
    Host,
    PassStatus,
    RequestStatus,
    VisitLog,
    Visitor,
    VisitorPass,
    VisitRequest,
    VisitStatus,
)
from modules.vms.selectors.queries import (
    check_is_blacklisted,
    get_active_on_site_visits,
    get_active_passes,
    get_all_campus_gates,
    get_all_requests,
    get_pending_requests_for_host,
    get_request_by_id,
)


@pytest.mark.django_db
class TestVmsSelectorsComprehensive:
    """Exhaustive tests for query selectors and database lookups."""

    @pytest.fixture
    def setup_data(self):
        host1 = Host.objects.create(
            user_id=201,
            employee_id="E-201",
            full_name="Host One",
            department="CSE",
            designation="Prof",
            email="h1@test.org",
        )
        host2 = Host.objects.create(
            user_id=202,
            employee_id="E-202",
            full_name="Host Two",
            department="ME",
            designation="Assoc Prof",
            email="h2@test.org",
        )
        visitor = Visitor.objects.create(
            full_name="Alice Smith",
            email="alice@test.org",
            phone="9876500001",
            id_document_type="AADHAAR",
            id_document_number="AADHAAR-01",
        )
        now = timezone.now()
        req1 = VisitRequest.objects.create(
            visitor=visitor,
            host=host1,
            purpose="Collab 1",
            scheduled_start_time=now,
            scheduled_end_time=now + timedelta(hours=2),
            status=RequestStatus.PENDING_HOST_APPROVAL,
        )
        req2 = VisitRequest.objects.create(
            visitor=visitor,
            host=host1,
            purpose="Collab 2",
            scheduled_start_time=now,
            scheduled_end_time=now + timedelta(hours=2),
            status=RequestStatus.APPROVED,
        )
        req3 = VisitRequest.objects.create(
            visitor=visitor,
            host=host2,
            purpose="Collab 3",
            scheduled_start_time=now,
            scheduled_end_time=now + timedelta(hours=2),
            status=RequestStatus.PENDING_HOST_APPROVAL,
        )
        return host1, host2, visitor, req1, req2, req3

    def test_get_pending_requests_for_host(self, setup_data):
        host1, host2, _, req1, _, req3 = setup_data
        h1_pending = list(get_pending_requests_for_host(host1.user_id))
        assert len(h1_pending) == 1
        assert h1_pending[0].request_id == req1.request_id

        h2_pending = list(get_pending_requests_for_host(host2.user_id))
        assert len(h2_pending) == 1
        assert h2_pending[0].request_id == req3.request_id

    def test_get_pending_requests_empty_for_unknown_host(self):
        pending = list(get_pending_requests_for_host(99999))
        assert len(pending) == 0

    def test_get_pending_requests_ignores_approved(self, setup_data):
        host1, _, _, _, req2, _ = setup_data
        h1_pending = list(get_pending_requests_for_host(host1.user_id))
        assert req2.request_id not in [r.request_id for r in h1_pending]

    def test_get_pending_requests_ordering(self, setup_data):
        host1, _, visitor, _, _, _ = setup_data
        now = timezone.now()
        req_earlier = VisitRequest.objects.create(
            visitor=visitor,
            host=host1,
            purpose="Earlier",
            scheduled_start_time=now - timedelta(hours=1),
            scheduled_end_time=now + timedelta(hours=1),
            status=RequestStatus.PENDING_HOST_APPROVAL,
        )
        pending = list(get_pending_requests_for_host(host1.user_id))
        assert len(pending) == 2
        assert pending[0].request_id == req_earlier.request_id

    def test_get_all_requests(self, setup_data):
        all_reqs = list(get_all_requests())
        assert len(all_reqs) == 3

    def test_get_all_requests_empty_when_no_records(self):
        VisitRequest.objects.all().delete()
        assert list(get_all_requests()) == []

    def test_get_all_requests_ordering(self, setup_data):
        reqs = list(get_all_requests())
        assert reqs[0].submission_timestamp >= reqs[1].submission_timestamp

    def test_get_request_by_id_found(self, setup_data):
        _, _, _, req1, _, _ = setup_data
        fetched = get_request_by_id(req1.request_id)
        assert fetched is not None
        assert fetched.request_id == req1.request_id

    def test_get_request_by_id_not_found(self):
        assert get_request_by_id("non-existent-uuid") is None

    def test_get_request_by_id_empty_string(self):
        assert get_request_by_id("") is None

    def test_get_request_by_id_select_related_visitor(self, setup_data):
        _, _, _, req1, _, _ = setup_data
        fetched = get_request_by_id(req1.request_id)
        assert fetched.visitor.full_name == "Alice Smith"

    def test_get_request_by_id_select_related_host(self, setup_data):
        _, _, _, req1, _, _ = setup_data
        fetched = get_request_by_id(req1.request_id)
        assert fetched.host.department == "CSE"

    def test_get_active_passes(self, setup_data):
        _, _, _, _, req2, _ = setup_data
        now = timezone.now()
        p1 = VisitorPass.objects.create(
            request=req2,
            credential_data="cred-active-1",
            valid_from=now,
            valid_until=now + timedelta(hours=3),
            status=PassStatus.ACTIVE,
        )
        p2 = VisitorPass.objects.create(
            request=req2,
            credential_data="cred-expired-1",
            valid_from=now,
            valid_until=now + timedelta(hours=3),
            status=PassStatus.EXPIRED,
        )
        active_list = list(get_active_passes())
        assert p1 in active_list
        assert p2 not in active_list

    def test_get_active_passes_empty(self):
        VisitorPass.objects.all().delete()
        assert list(get_active_passes()) == []

    def test_get_active_passes_deactivated_excluded(self, setup_data):
        _, _, _, _, req2, _ = setup_data
        now = timezone.now()
        p = VisitorPass.objects.create(
            request=req2,
            credential_data="cred-deact-1",
            valid_from=now,
            valid_until=now + timedelta(hours=3),
            status=PassStatus.DEACTIVATED,
        )
        assert p not in list(get_active_passes())

    def test_get_active_passes_completed_excluded(self, setup_data):
        _, _, _, _, req2, _ = setup_data
        now = timezone.now()
        p = VisitorPass.objects.create(
            request=req2,
            credential_data="cred-comp-1",
            valid_from=now,
            valid_until=now + timedelta(hours=3),
            status=PassStatus.COMPLETED,
        )
        assert p not in list(get_active_passes())

    def test_get_active_on_site_visits(self, setup_data):
        _, _, _, _, req2, _ = setup_data
        now = timezone.now()
        gate = CampusGate.objects.create(gate_id="G-SEL-01", gate_name="Gate 1")
        p = VisitorPass.objects.create(
            request=req2,
            credential_data="cred-site-1",
            valid_from=now,
            valid_until=now + timedelta(hours=3),
            status=PassStatus.ACTIVE,
        )
        vlog = VisitLog.objects.create(
            visitor_pass=p, entry_gate=gate, check_in_time=now, status=VisitStatus.ON_SITE
        )
        assert vlog in list(get_active_on_site_visits())

    def test_get_active_on_site_visits_excludes_completed(self, setup_data):
        _, _, _, _, req2, _ = setup_data
        now = timezone.now()
        gate = CampusGate.objects.create(gate_id="G-SEL-02", gate_name="Gate 2")
        p = VisitorPass.objects.create(
            request=req2,
            credential_data="cred-site-2",
            valid_from=now,
            valid_until=now + timedelta(hours=3),
            status=PassStatus.ACTIVE,
        )
        vlog = VisitLog.objects.create(
            visitor_pass=p, entry_gate=gate, check_in_time=now, status=VisitStatus.COMPLETED
        )
        assert vlog not in list(get_active_on_site_visits())

    def test_get_active_on_site_visits_empty(self):
        VisitLog.objects.all().delete()
        assert list(get_active_on_site_visits()) == []

    def test_get_active_on_site_visits_ordering(self, setup_data):
        _, _, _, _, req2, _ = setup_data
        now = timezone.now()
        gate = CampusGate.objects.create(gate_id="G-SEL-03", gate_name="Gate 3")
        p = VisitorPass.objects.create(
            request=req2,
            credential_data="cred-site-3",
            valid_from=now,
            valid_until=now + timedelta(hours=3),
            status=PassStatus.ACTIVE,
        )
        VisitLog.objects.create(
            visitor_pass=p, entry_gate=gate, check_in_time=now - timedelta(minutes=10)
        )
        l2 = VisitLog.objects.create(visitor_pass=p, entry_gate=gate, check_in_time=now)
        active = list(get_active_on_site_visits())
        assert active[0].log_id == l2.log_id

    def test_get_all_campus_gates_active_only(self):
        g1 = CampusGate.objects.create(gate_id="G1", gate_name="Alpha Gate", is_operational=True)
        g2 = CampusGate.objects.create(gate_id="G2", gate_name="Beta Gate", is_operational=False)
        gates = list(get_all_campus_gates())
        assert g1 in gates
        assert g2 not in gates

    def test_get_all_campus_gates_alphabetical(self):
        CampusGate.objects.all().delete()
        g_c = CampusGate.objects.create(gate_id="GC", gate_name="Charlie Gate", is_operational=True)
        g_a = CampusGate.objects.create(gate_id="GA", gate_name="Alpha Gate", is_operational=True)
        gates = list(get_all_campus_gates())
        assert gates[0].gate_id == g_a.gate_id
        assert gates[1].gate_id == g_c.gate_id

    def test_get_all_campus_gates_empty(self):
        CampusGate.objects.all().delete()
        assert list(get_all_campus_gates()) == []

    def test_get_all_campus_gates_count(self):
        CampusGate.objects.all().delete()
        for i in range(5):
            CampusGate.objects.create(
                gate_id=f"GATE-{i}", gate_name=f"Gate {i}", is_operational=True
            )
        assert get_all_campus_gates().count() == 5

    @pytest.mark.parametrize(
        ("check_phone", "check_id_doc", "expected_blocked"),
        [
            ("9111111111", "CLEAR-01", True),
            ("9000000000", "BLOCKED-DOC-01", True),
            ("9111111111", "BLOCKED-DOC-01", True),
            ("9999999999", "CLEAN-DOC-99", False),
            ("", "", False),
            ("9111111111", "", True),
            ("", "BLOCKED-DOC-01", True),
            ("9222222222", "CLEAR-02", True),
            ("9333333333", "CLEAR-03", False),
            ("9444444444", "BLOCKED-DOC-02", True),
            ("9555555555", "CLEAR-04", False),
            ("9666666666", "BLOCKED-DOC-03", True),
        ],
    )
    def test_check_is_blacklisted_variations(self, check_phone, check_id_doc, expected_blocked):
        BlacklistRegistry.objects.get_or_create(
            phone="9111111111",
            id_document_number="",
            defaults={"reason": "Flagged phone", "is_active": True, "flagged_by": 1},
        )
        BlacklistRegistry.objects.get_or_create(
            phone="9222222222",
            id_document_number="",
            defaults={"reason": "Flagged phone 2", "is_active": True, "flagged_by": 1},
        )
        BlacklistRegistry.objects.get_or_create(
            phone="9333333333",
            id_document_number="",
            defaults={"reason": "Deactivated entry", "is_active": False, "flagged_by": 1},
        )
        BlacklistRegistry.objects.get_or_create(
            phone="",
            id_document_number="BLOCKED-DOC-01",
            defaults={"reason": "Flagged document", "is_active": True, "flagged_by": 1},
        )
        BlacklistRegistry.objects.get_or_create(
            phone="",
            id_document_number="BLOCKED-DOC-02",
            defaults={"reason": "Flagged document 2", "is_active": True, "flagged_by": 1},
        )
        BlacklistRegistry.objects.get_or_create(
            phone="",
            id_document_number="BLOCKED-DOC-03",
            defaults={"reason": "Flagged document 3", "is_active": True, "flagged_by": 1},
        )

        is_blocked, reason = check_is_blacklisted(check_phone, check_id_doc)
        assert is_blocked == expected_blocked
        if expected_blocked:
            assert len(reason) > 0
