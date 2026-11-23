"""PMS test helpers: actors from the real ROLE_GRANTS, a fake clamd and a configured world."""
import socket
import struct
import threading
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from fusion_auth.client import UserRef
from fusion_auth.principal import Principal
from modules.pms import registry
from modules.pms.domain import state_machine as sm
from modules.pms.models import (
    Application,
    ApplicationVersion,
    AttorneyAssignment,
    Budget,
    DirectorProfile,
    Document,
    DocumentVersion,
    Inventor,
    PanelAttorney,
    PmsPolicy,
    ReviewCycle,
)
from modules.pms.services.scanning import EICAR

APPLICANT, CO_INVENTOR, OTHER_APPLICANT = 1001, 1002, 1003
DIRECTOR, DIRECTOR_2, ATTORNEY, ATTORNEY_2, PCC = 2001, 2002, 3001, 3002, 4001
PDF = b"%PDF-1.7\n1 0 obj << >> endobj\n%%EOF\n"
POLICY = {
    "cost_threshold": "100000.00", "appeal_period_days": 30,
    "alert_offsets_days": [30, 15, 5], "withdrawal_statuses": list(sm.WITHDRAWAL_CANDIDATES),
    "withdrawal_consent_required": False, "holidays": [],
    "domains": [{"code": "materials", "label": "Materials", "ipc_classes": ["H01M"]},
                {"code": "software", "label": "Software", "ipc_classes": ["G06F"]}],
    "maintenance_rules": {"IN": [12, 24]}, "escalation_chain": [],
    "pcc_contact_user_id": PCC, "auto_routing_enabled": False,
    "licensing_route": {"kind": "committee", "committee_name": "Technology Transfer Committee"},
}
KIND = {"student": "student", "faculty": "faculty", "staff": "staff",
        "pms_director": "faculty", "pms_attorney": "staff", "pms_pcc_admin": "staff"}


def users_map():
    def ref(uid, name, kind):
        return UserRef(user_id=uid, username=f"u{uid}", display_name=name, kind=kind,
                       email=f"u{uid}@example.test")
    return {uid: ref(uid, f"Person {uid}", kind) for uid, kind in (
        (APPLICANT, "student"), (CO_INVENTOR, "student"), (OTHER_APPLICANT, "faculty"),
        (DIRECTOR, "faculty"), (DIRECTOR_2, "faculty"), (ATTORNEY, "staff"),
        (ATTORNEY_2, "staff"), (PCC, "staff"))}


class Actor:
    """One person acting as one designation; each request reinstalls their session."""

    def __init__(self, stub_iam, uid, designation, *, permissions=None, modules=("pms",),
                 also_holds=()):
        self.stub, self.uid, self.designation = stub_iam, uid, designation
        kind = KIND[designation]
        perms = registry.ROLE_GRANTS[designation] if permissions is None else permissions
        roles = tuple(dict.fromkeys((kind, designation, *also_holds)))
        self.session = make_session(user_id=uid, permissions=perms, modules=modules,
                                    kind=kind, roles=roles, active_role=designation)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION="Token test-token")

    @property
    def principal(self):
        return Principal.from_session(self.session)

    def _go(self):
        self.stub(self.session, users=users_map())

    def get(self, path, data=None):
        self._go()
        return self.client.get(f"/api/v1/pms/{path}", data)

    def post(self, path, data=None, fmt="json"):
        self._go()
        return self.client.post(f"/api/v1/pms/{path}", data, format=fmt)

    def put(self, path, data=None):
        self._go()
        return self.client.put(f"/api/v1/pms/{path}", data, format="json")

    def patch(self, path, data=None):
        self._go()
        return self.client.patch(f"/api/v1/pms/{path}", data, format="json")


@pytest.fixture
def actors(stub_iam):
    """The plain applicant first: a student holding nothing but `student` (Step 5.2)."""
    return {
        "applicant": Actor(stub_iam, APPLICANT, "student"),
        "co_inventor": Actor(stub_iam, CO_INVENTOR, "student"),
        "other": Actor(stub_iam, OTHER_APPLICANT, "faculty"),
        "director": Actor(stub_iam, DIRECTOR, "pms_director"),
        "director2": Actor(stub_iam, DIRECTOR_2, "pms_director"),
        "attorney": Actor(stub_iam, ATTORNEY, "pms_attorney"),
        "attorney2": Actor(stub_iam, ATTORNEY_2, "pms_attorney"),
        "pcc": Actor(stub_iam, PCC, "pms_pcc_admin"),
    }


@pytest.fixture
def world(db, actors):
    """Settings published, two Directors and two panel attorneys, all in Materials."""
    now = timezone.now() - timedelta(seconds=1)
    PmsPolicy.objects.create(version=1, effective_from=now, payload=POLICY,
                             published_by_user_id=PCC)
    for uid in (DIRECTOR, DIRECTOR_2):
        DirectorProfile.objects.create(user_id=uid, domain_codes=["materials"], valid_from=now,
                                       added_by_user_id=PCC)
    for uid in (ATTORNEY, ATTORNEY_2):
        PanelAttorney.objects.create(user_id=uid, domain_codes=["materials"], valid_from=now,
                                     added_by_user_id=PCC)
    return actors


class _FakeClamd(threading.Thread):
    """Speaks clamd's INSTREAM and PING over a unix socket: OK, or FOUND for EICAR."""

    def __init__(self, path: Path):
        super().__init__(daemon=True)
        self.path = path
        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server.bind(str(path))
        self.server.listen(8)
        self.scans = 0

    def run(self):
        while True:
            try:
                conn, _ = self.server.accept()
            except OSError:
                return
            with conn:
                command = b""
                while not command.endswith(b"\0"):
                    command += conn.recv(1)
                if command == b"zPING\0":
                    conn.sendall(b"PONG\0")
                    continue
                data = b""
                while True:
                    size = struct.unpack("!L", self._exact(conn, 4))[0]
                    if size == 0:
                        break
                    data += self._exact(conn, size)
                self.scans += 1
                verdict = b"stream: Eicar-Test-Signature FOUND\0" if EICAR in data \
                    else b"stream: OK\0"
                conn.sendall(verdict)

    @staticmethod
    def _exact(conn, n):
        buf = b""
        while len(buf) < n:
            buf += conn.recv(n - len(buf))
        return buf

    def stop(self):
        self.server.close()


@pytest.fixture
def scanner(settings, tmp_path):
    """A real socket round-trip, so the clamd client code is what the tests exercise."""
    sock = Path("/tmp") / f"pms-clamd-{tmp_path.name[-20:]}.sock"
    sock.unlink(missing_ok=True)
    daemon = _FakeClamd(sock)
    daemon.start()
    settings.PMS_MALWARE_SCANNER = "clamd"
    settings.PMS_CLAMD_SOCKET = str(sock)
    settings.PMS_UPLOAD_ROOT = str(tmp_path / "uploads")
    yield daemon
    daemon.stop()
    sock.unlink(missing_ok=True)


def pdf(name="spec.pdf", content=PDF):
    return SimpleUploadedFile(name, content, content_type="application/pdf")


# -- direct builders, for tests about something other than how a record got here --
def make_app(status=sm.SUBMITTED, applicant=APPLICANT, domain="materials", **kw):
    n = Application.objects.count() + 1
    app = Application.objects.create(
        applicant_user_id=applicant, status=status, domain_code=domain,
        reference="" if status == sm.DRAFT else f"PMS-2026-{n:05d}",
        title=kw.pop("title", f"Invention {n}"), abstract="An abstract.",
        description="A description.", claims="1. A claim.",
        version=0 if status == sm.DRAFT else 1, **kw)
    if status != sm.DRAFT:
        ApplicationVersion.objects.create(application=app, version=1, title=app.title,
                                          abstract=app.abstract, description=app.description,
                                          claims=app.claims, domain_code=app.domain_code,
                                          created_by_user_id=applicant)
    Inventor.objects.create(application=app, user_id=applicant, name="Person",
                            share_percent=Decimal("100"),
                            agreement_completed_at=timezone.now(),
                            consent_recorded_at=timezone.now(), agreement_reference="A1")
    doc = Document.objects.create(application=app, kind="specification", title="Spec",
                                  sensitivity="public_internal", created_by_user_id=applicant)
    DocumentVersion.objects.create(document=doc, number=1, storage_key=f"k{app.pk}x1",
                                   original_name="spec.pdf", size_bytes=10, sha256="0" * 64,
                                   scanner="clamd", uploaded_by_user_id=applicant)
    return app


def with_cycle(app, director=DIRECTOR, *, status="open", decision="", due=None):
    today = timezone.localdate()
    n = app.review_cycles.count() + 1
    return ReviewCycle.objects.create(
        application=app, cycle_no=n, director_user_id=director, assigned_on=today,
        due_on=due or today + timedelta(days=21), status=status, decision=decision,
        justification="j" * 60 if decision else "",
        decided_at=timezone.now() if decision else None)


def approved_with_attorney(attorney=ATTORNEY):
    app = make_app(sm.ATTORNEY_ASSIGNED)
    with_cycle(app, status="decided", decision="approve")
    AttorneyAssignment.objects.create(application=app, attorney_user_id=attorney,
                                      assigned_by_user_id=PCC, status=sm.ACCEPTED)
    return app


def with_budget(app, status=sm.BUDGET_APPROVED, total="50000.00"):
    return Budget.objects.create(application=app, proposed_by_user_id=ATTORNEY,
                                 filing_fee=Decimal(total), attorney_fee=0, admin_cost=0,
                                 total=Decimal(total), status=status)
