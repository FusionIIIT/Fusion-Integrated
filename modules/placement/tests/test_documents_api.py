"""Placement-profile documents: Drive links a student keeps here (PC-UC-001, PC-AFR-003)."""
import pytest

from modules.placement.models import Application, ProfileDocument
from modules.placement.tests.test_spec_journeys import API, OTHER, STUDENT, World

pytestmark = pytest.mark.django_db

DRIVE = "https://drive.google.com/file/d/1AbCdEfGhIjKlMnOpQrStUvWxYz012345/view"


@pytest.fixture
def world(stub_iam):
    return World(stub_iam)


def _attach(client, kind="certificate"):
    r = client.post(f"{API}/documents", {"kind": kind, "url": DRIVE, "title": "AWS cert"},
                    format="json")
    assert r.status_code == 201, r.content
    return r.json()["id"]


def test_student_attaches_lists_opens_and_removes_a_document(world):
    # PC-UC-001, PC-AFR-003
    c = world.student()
    doc = _attach(c)
    assert [d["id"] for d in c.get(f"{API}/documents").json()["results"]] == [doc]
    opened = c.get(f"{API}/documents/{doc}/download")
    assert opened.status_code == 302
    assert opened["Location"].startswith("https://drive.google.com/")
    assert c.delete(f"{API}/documents/{doc}").status_code == 204
    assert c.get(f"{API}/documents/{doc}/download").status_code == 404


def test_attaching_the_same_link_twice_is_one_document(world):
    c = world.student()
    assert _attach(c) == _attach(c)
    assert ProfileDocument.objects.count() == 1


@pytest.mark.parametrize(("kind", "url", "status"), [
    ("resume", DRIVE, 400),
    ("certificate", "https://evil.example/file", 409),
    ("certificate", "http://drive.google.com/file/d/abc/view", 409),
])
def test_a_bad_document_is_refused_and_nothing_is_saved(world, kind, url, status):
    # PC-UC-001 E1
    r = world.student().post(f"{API}/documents", {"kind": kind, "url": url}, format="json")
    assert r.status_code == status
    assert not ProfileDocument.objects.exists()


def test_another_student_cannot_open_or_remove_my_document(world):
    # PC-UC-001 E2, PC-BR-023
    doc = _attach(world.student())
    other = world.student(OTHER)
    assert other.get(f"{API}/documents/{doc}/download").status_code == 404
    assert other.delete(f"{API}/documents/{doc}").status_code == 404


def test_a_company_opens_a_certificate_only_from_its_own_applicant(world):
    # PC-BR-009
    cert = _attach(world.student())
    letter = _attach(world.student(), kind="offer_letter")
    assert world.recruiter.get(f"{API}/documents/{cert}/download").status_code == 404
    pid = world.company_publishes()
    Application.objects.create(posting_id=pid, user_id=STUDENT, status="submitted")
    assert world.recruiter.get(f"{API}/documents/{cert}/download").status_code == 302
    assert world.recruiter.get(f"{API}/documents/{letter}/download").status_code == 404


def test_the_tpo_opens_any_students_document(world):
    doc = _attach(world.student())
    assert world.tpo().get(f"{API}/documents/{doc}/download").status_code == 302
