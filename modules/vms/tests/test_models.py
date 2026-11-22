"""Comprehensive unit tests for VMS Django ORM models and schema constraints."""

from datetime import timedelta

import pytest
from django.utils import timezone

from modules.vms.models import (
    BlacklistRegistry,
    CampusGate,
    Host,
    HostDecision,
    PassStatus,
    PassType,
    RequestStatus,
    VisitLog,
    Visitor,
    VisitorPass,
    VisitRequest,
    VisitStatus,
)


@pytest.mark.django_db
class TestVmsModelsComprehensive:
    """Exhaustive tests for VMS database models, choices, and relations."""

    @pytest.mark.parametrize(
        ("doc_type", "doc_num"),
        [
            ("AADHAAR", "1111-2222-3333"),
            ("PAN", "ABCDE1234F"),
            ("PASSPORT", "Z1234567"),
            ("VOTER_ID", "VTR987654"),
            ("DRIVING_LICENSE", "DL-01-2026-0001"),
            ("COLLEGE_ID", "STU-2026-999"),
            ("GOVT_EMPLOYEE_ID", "GOV-8888"),
            ("NATIONAL_ID", "NAT-55555"),
            ("OTHER", "OTH-99999"),
            ("AADHAAR", "9999-8888-7777"),
        ],
    )
    def test_visitor_model_creation_various_id_types(self, doc_type, doc_num):
        v = Visitor.objects.create(
            full_name=f"Visitor {doc_type}",
            email=f"{doc_type.lower()}@test.org",
            phone=f"987654{len(doc_type):04d}",
            id_document_type=doc_type,
            id_document_number=doc_num,
            organization="Test Corp",
        )
        assert v.visitor_id is not None
        assert str(v) == f"{v.full_name} ({v.phone})"

    @pytest.mark.parametrize(
        ("dept", "desig", "emp_id"),
        [
            ("Computer Science & Engineering", "Professor", "EMP-CSE-01"),
            ("Mechanical Engineering", "Associate Professor", "EMP-ME-02"),
            ("Electronics & Communication", "Assistant Professor", "EMP-ECE-03"),
            ("Design", "Dean Academics", "EMP-DES-04"),
            ("Administration", "Registrar", "EMP-ADM-05"),
            ("Security & Vigilance", "Security Officer", "EMP-SEC-06"),
            ("Hostel Management", "Chief Warden", "EMP-HOS-07"),
            ("Sports Department", "Director Physical Education", "EMP-SPO-08"),
            ("Library Services", "Head Librarian", "EMP-LIB-09"),
            ("Medical Unit", "Resident Medical Officer", "EMP-MED-10"),
        ],
    )
    def test_host_model_creation(self, dept, desig, emp_id):
        host = Host.objects.create(
            user_id=1000 + len(dept) * 10 + len(emp_id),
            employee_id=emp_id,
            full_name=f"Dr. {desig}",
            department=dept,
            designation=desig,
            email=f"{emp_id.lower()}@iiitdmj.ac.in",
            office_location=f"Block {dept[:3]}-201",
        )
        assert host.host_id is not None
        assert str(host) == f"{host.full_name} ({host.department})"

    @pytest.mark.parametrize(
        ("gate_id", "gate_name", "location_zone"),
        [
            ("GATE-MAIN-01", "Main Campus Gate 1", "MAIN_CAMPUS"),
            ("GATE-MAIN-02", "Main Campus Gate 2", "MAIN_CAMPUS"),
            ("GATE-HOSTEL-01", "Hall of Residence 1 Gate", "HOSTEL_ZONE"),
            ("GATE-HOSTEL-04", "Hall of Residence 4 Gate", "HOSTEL_ZONE"),
            ("GATE-ACAD-01", "Core Academic Block Gate", "ACADEMIC_ZONE"),
            ("GATE-LIB-01", "Central Library Checkpoint", "LIBRARY_ZONE"),
            ("GATE-CC-01", "Computer Center Entry", "LAB_ZONE"),
            ("GATE-GH-01", "Visitor Guest House Gate", "GUEST_HOUSE_ZONE"),
            ("GATE-SPORT-01", "Student Activity Center Entry", "SPORTS_ZONE"),
            ("GATE-HEALTH-01", "Primary Health Center Gate", "MEDICAL_ZONE"),
        ],
    )
    def test_campus_gate_model_creation(self, gate_id, gate_name, location_zone):
        gate = CampusGate.objects.create(
            gate_id=gate_id,
            gate_name=gate_name,
            gate_type="MAIN_GATE",
            location_zone=location_zone,
            is_operational=True,
        )
        assert gate.gate_id == gate_id
        assert str(gate) == f"{gate.gate_name} ({gate.gate_id})"

    @pytest.mark.parametrize(
        "status",
        [
            RequestStatus.NOT_SUBMITTED,
            RequestStatus.PENDING_HOST_APPROVAL,
            RequestStatus.APPROVED,
            RequestStatus.REJECTED,
            RequestStatus.CANCELLED,
            RequestStatus.EXPIRED,
            RequestStatus.COMPLETED,
        ],
    )
    def test_visit_request_statuses(self, status):
        v = Visitor.objects.create(
            full_name="Status Visitor",
            email="status@test.org",
            phone=f"912345678{len(status)}",
            id_document_type="AADHAAR",
            id_document_number=f"1234-9999-{len(status)}",
        )
        host = Host.objects.create(
            user_id=8880 + len(status),
            employee_id=f"EMP-888-{status}",
            full_name="Host 888",
            department="CSE",
            designation="Faculty",
            email=f"h888_{status}@test.org",
        )
        now = timezone.now()
        req = VisitRequest.objects.create(
            visitor=v,
            host=host,
            purpose="Status Check",
            scheduled_start_time=now,
            scheduled_end_time=now + timedelta(hours=3),
            status=status,
        )
        assert req.status == status
        assert f"Req-{req.request_id}" in str(req)

    @pytest.mark.parametrize(
        ("pass_type", "pass_status"),
        [
            (PassType.PRE_REGISTERED, PassStatus.ACTIVE),
            (PassType.PRE_REGISTERED, PassStatus.EXPIRED),
            (PassType.PRE_REGISTERED, PassStatus.DEACTIVATED),
            (PassType.PRE_REGISTERED, PassStatus.COMPLETED),
            (PassType.WALK_IN, PassStatus.ACTIVE),
            (PassType.WALK_IN, PassStatus.COMPLETED),
            (PassType.VIP, PassStatus.ACTIVE),
            (PassType.VIP, PassStatus.COMPLETED),
        ],
    )
    def test_visitor_pass_types_and_statuses(self, pass_type, pass_status):
        v = Visitor.objects.create(
            full_name="Pass Visitor",
            email=f"pass_{pass_type}_{pass_status}@test.org",
            phone=f"90000{len(pass_type):02d}{len(pass_status):03d}",
            id_document_type="PAN",
            id_document_number=f"PASS{pass_type[:3]}{pass_status[:3]}",
        )
        host = Host.objects.create(
            user_id=7770 + len(pass_type) + len(pass_status),
            employee_id=f"EMP-777-{pass_type[:2]}",
            full_name="Host 777",
            department="ECE",
            designation="Faculty",
            email=f"h777_{pass_type}_{pass_status}@test.org",
        )
        now = timezone.now()
        req = VisitRequest.objects.create(
            visitor=v,
            host=host,
            purpose="Pass Check",
            scheduled_start_time=now,
            scheduled_end_time=now + timedelta(hours=2),
            status=RequestStatus.APPROVED,
        )
        pass_obj = VisitorPass.objects.create(
            request=req,
            pass_type=pass_type,
            credential_data=f"token-{pass_type}-{pass_status}-{req.request_id}",
            valid_from=now,
            valid_until=now + timedelta(hours=2),
            status=pass_status,
        )
        assert pass_obj.pass_type == pass_type
        assert pass_obj.status == pass_status
        assert str(pass_obj) == f"Pass-{pass_obj.pass_id} [{pass_status}] ({pass_type})"

    @pytest.mark.parametrize(
        ("phone", "id_doc", "reason"),
        [
            ("9888877771", "BL-001", "Security breach attempt"),
            ("9888877772", "BL-002", "Past vandalism on premises"),
            ("9888877773", "BL-003", "Administrative barring order"),
            ("9888877774", "BL-004", "Repeated trespassing without pass"),
            ("9888877775", "BL-005", "Fraudulent identity documentation"),
            ("9888877776", "BL-006", "Misconduct with campus guards"),
            ("9888877777", "BL-007", "Expired visa or illegal entry"),
            ("9888877778", "BL-008", "Theft suspect in laboratory block"),
        ],
    )
    def test_blacklist_registry_records(self, phone, id_doc, reason):
        bl = BlacklistRegistry.objects.create(
            phone=phone,
            id_document_number=id_doc,
            reason=reason,
            flagged_by=1,
            is_active=True,
        )
        assert bl.is_active is True
        assert str(bl) == f"Blacklist: {phone} ({reason})"

    @pytest.mark.parametrize(
        "visit_status",
        [
            VisitStatus.ON_SITE,
            VisitStatus.COMPLETED,
            VisitStatus.FLAGGED,
            VisitStatus.ON_SITE,
            VisitStatus.COMPLETED,
        ],
    )
    def test_visit_log_creation(self, visit_status):
        v = Visitor.objects.create(
            full_name="Log Visitor",
            email="log_v@test.org",
            phone="9123499999",
            id_document_type="PAN",
            id_document_number="LOG9999X",
        )
        host = Host.objects.create(
            user_id=6661 + len(visit_status),
            employee_id="EMP-666",
            full_name="Host 666",
            department="ME",
            designation="Faculty",
            email="h666@test.org",
        )
        gate = CampusGate.objects.create(
            gate_id=f"GATE-LOG-{visit_status}",
            gate_name="Gate Log",
            location_zone="MAIN_CAMPUS",
        )
        now = timezone.now()
        req = VisitRequest.objects.create(
            visitor=v,
            host=host,
            purpose="Log Test",
            scheduled_start_time=now,
            scheduled_end_time=now + timedelta(hours=2),
            status=RequestStatus.APPROVED,
        )
        pass_obj = VisitorPass.objects.create(
            request=req,
            credential_data=f"token-log-{visit_status}-{req.request_id}",
            valid_from=now,
            valid_until=now + timedelta(hours=2),
            status=PassStatus.ACTIVE,
        )
        log = VisitLog.objects.create(
            visitor_pass=pass_obj,
            entry_gate=gate,
            check_in_time=now,
            status=visit_status,
        )
        assert log.status == visit_status
        assert str(log) == f"Log-{log.log_id}: Pass {pass_obj.pass_id} [{visit_status}]"

    @pytest.mark.parametrize(
        "outcome",
        ["APPROVE", "REJECT", "APPROVE", "REJECT", "APPROVE"],
    )
    def test_host_decision_creation(self, outcome):
        v = Visitor.objects.create(
            full_name="Decision Visitor",
            email="dec_v@test.org",
            phone="9123488888",
            id_document_type="AADHAAR",
            id_document_number="DEC8888X",
        )
        host = Host.objects.create(
            user_id=5551 + len(outcome),
            employee_id="EMP-555",
            full_name="Host 555",
            department="Design",
            designation="Faculty",
            email="h555@test.org",
        )
        now = timezone.now()
        req = VisitRequest.objects.create(
            visitor=v,
            host=host,
            purpose="Decision Test",
            scheduled_start_time=now,
            scheduled_end_time=now + timedelta(hours=2),
            status=RequestStatus.PENDING_HOST_APPROVAL,
        )
        dec = HostDecision.objects.create(
            request=req,
            host=host,
            outcome=outcome,
            permitted_zones=["MAIN_CAMPUS"],
        )
        assert dec.outcome == outcome
        assert dec.decision_id is not None
