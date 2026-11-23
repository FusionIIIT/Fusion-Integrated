"""BR-GYM-018 and BR-GYM-019: what may be uploaded, where it lands, who gets it back."""
from pathlib import Path

import pytest
from django.conf import settings as live_settings
from django.core.files.base import ContentFile

from modules.gymkhana.domain.constants import MAX_UPLOAD_BYTES
from modules.gymkhana.models import ClubBudgetRequest, VenueBooking
from modules.gymkhana.models.files import PrivateStorage
from modules.gymkhana.tests.support import (
    API,
    HEAD,
    STUDENT,
    make_club,
    people,
    sign_in,
    slot,
    upload,
)

pytestmark = pytest.mark.django_db

REFUSED = [
    ("evil.html", b"<script>alert(1)</script>"), ("evil.svg", b"<svg onload=x>"),
    ("run.exe", b"MZ\x90\x00"), ("noextension", b"hello"), ("empty.pdf", b""),
    ("page.pdf", b"\xef\xbb\xbf  <!DOCTYPE html><html>"), ("tool.txt", b"#!/bin/sh"),
    ("app.pdf", b"MZ\x90\x00"), ("elf.docx", b"\x7fELF"),
    ("big.pdf", b"x" * (MAX_UPLOAD_BYTES + 1)),
]


def submit(client, club, file):
    return client.post(f"{API}/budgets/", {
        "club_id": club.pk, "amount": "0", "purpose": "Kit", "supporting_file": file,
    }, format="multipart")


@pytest.mark.parametrize(("name", "content"), REFUSED, ids=[r[0] for r in REFUSED])
def test_an_unacceptable_file_is_refused(stub_iam, name, content):
    people()
    club = make_club()
    assert submit(sign_in(stub_iam, HEAD), club, upload(name, content)).status_code == 400
    assert not ClubBudgetRequest.objects.exists()


def test_a_poster_must_be_a_picture_or_a_pdf(stub_iam):
    people()
    club = make_club()
    response = sign_in(stub_iam, HEAD).post(
        f"{API}/bookings/session/", {**slot(club), "poster_file": upload("poster.xlsx", b"x")},
        format="multipart")
    assert response.status_code == 400
    assert not VenueBooking.objects.exists()


def test_the_stored_name_is_never_the_uploaders(stub_iam):
    people()
    club = make_club()
    response = submit(sign_in(stub_iam, HEAD), club, upload("../../secret plan.pdf"))
    assert response.status_code == 201
    stored = ClubBudgetRequest.objects.get().supporting_file.name
    assert "secret" not in stored
    assert stored.startswith("budgets/")
    assert stored not in response.content.decode()


def test_a_download_is_an_attachment_with_the_same_bytes(stub_iam):
    people()
    club = make_club()
    client = sign_in(stub_iam, HEAD)
    path = submit(client, club, upload(content=b"%PDF bytes")).json()["supporting_file"]
    response = client.get(f"/api/v1{path}")
    assert b"".join(response.streaming_content) == b"%PDF bytes"
    assert response["Content-Disposition"].startswith("attachment;")
    assert response["X-Content-Type-Options"] == "nosniff"


def test_a_poster_is_served_to_whoever_may_see_the_booking(stub_iam):
    people()
    club = make_club()
    booked = sign_in(stub_iam, HEAD).post(
        f"{API}/bookings/session/", {**slot(club), "poster_file": upload("p.png", b"png")},
        format="multipart").json()
    assert sign_in(stub_iam, STUDENT).get(f"/api/v1{booked['poster_file']}").status_code == 200


def test_a_booking_without_a_poster_has_nothing_to_download(stub_iam):
    people()
    club = make_club()
    client = sign_in(stub_iam, HEAD)
    booked = client.post(f"{API}/bookings/session/", slot(club), format="json").json()
    assert booked["poster_file"] is None
    assert client.get(f"{API}/bookings/{booked['id']}/poster/").status_code == 404


def test_a_file_lost_from_storage_is_a_404(stub_iam):
    people()
    club = make_club()
    row = ClubBudgetRequest.objects.create(
        club=club, submitted_by_id=HEAD, amount=1, purpose="x", supporting_file="budgets/gone.pdf")
    assert sign_in(stub_iam, HEAD).get(f"{API}/budgets/{row.pk}/file/").status_code == 404


def test_files_are_private_and_outside_the_repository():
    storage = PrivateStorage()
    name = storage.save("budgets/x.pdf", ContentFile(b"x"))
    path = Path(storage.path(name))
    assert Path(live_settings.BASE_DIR).resolve() not in path.resolve().parents
    assert path.stat().st_mode & 0o077 == 0
    with pytest.raises(ValueError, match="no public URL"):
        storage.url(name)
