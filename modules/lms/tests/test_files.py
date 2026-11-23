import io
import json
import tarfile
import zipfile

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from core.api.exceptions import DomainError, NotFoundError
from core.files import writers
from modules.lms.models import Material, StoredFile, Submission
from modules.lms.tests.conftest import available

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def private_storage(settings, tmp_path):
    settings.PRIVATE_UPLOAD_ROOT = str(tmp_path / "private")


def archive(docx=False):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as stream:
        stream.writestr("word/document.xml" if docx else "exercise.txt", "content")
        if docx:
            stream.writestr("[Content_Types].xml", "metadata")
    return output.getvalue()


def tar():
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as stream:
        item = tarfile.TarInfo("exercise.txt")
        item.size = 4
        stream.addfile(item, io.BytesIO(b"work"))
    return output.getvalue()


@pytest.mark.parametrize(
    "name,content,mime",
    [
        ("notes.txt", b"Course material", "text/plain"),
        ("sheet.pdf", b"%PDF-1.7\n%%EOF", "application/pdf"),
        ("work.zip", archive(), "application/zip"),
        ("work.tar.gz", tar(), "application/gzip"),
        ("work.docx", archive(True), writers.TYPES[".docx"]),
        ("work.ipynb", json.dumps({"nbformat": 4, "cells": []}).encode(), writers.TYPES[".ipynb"]),
    ],
)
def test_allowed_file_bytes_are_private_and_streamed(name, content, mime):
    stored = writers.write_upload(
        SimpleUploadedFile(name, content), profile="material", namespace="lms"
    )
    assert stored["mime_type"] == mime and stored["name"] == name and stored["size"] == len(content)
    assert name not in stored["storage_key"]
    response = writers.stream_upload(stored["storage_key"], name=name, mime_type=mime)
    assert (
        response["Cache-Control"] == "private, no-store"
        and "attachment" in response["Content-Disposition"]
    )
    assert b"".join(response.streaming_content) == content
    writers.discard_upload(stored["storage_key"])
    with pytest.raises(NotFoundError):
        writers.stream_upload(stored["storage_key"], name=name, mime_type=mime)


@pytest.mark.parametrize(
    "name,content",
    [
        ("run.py", b"print('no')"),
        ("run.exe", b"MZ"),
        ("run.sh", b"#!/bin/sh"),
        ("run.bat", b"@echo off"),
        ("index.html", b"<html>"),
        ("vector.svg", b"<svg>"),
        ("disguised.pdf", b"not a PDF"),
        ("bad.zip", b"not zip"),
        ("bad.docx", archive()),
        ("bad.ipynb", b'{"cells": "bad", "nbformat": 4}'),
        ("bad.ipynb", b"{invalid"),
        ("bad.txt", b"\x00binary"),
        ("bad.txt", b"\xff"),
        ("bad.txt", b" <html>"),
        ("bad.tar.gz", b"not gzip"),
        ("bad.zip", b"PK\x03\x04broken"),
    ],
)
def test_extension_and_magic_disagreement_never_persist_bytes(name, content):
    with pytest.raises(DomainError) as failure:
        writers.write_upload(SimpleUploadedFile(name, content), profile="material", namespace="lms")
    assert failure.value.code == "UPLOAD_TYPE_REJECTED"
    assert not writers.private_root().exists()


@pytest.mark.parametrize("profile", ["material", "submission"])
def test_exact_approved_byte_cap_and_one_byte_over(profile):
    size = writers.LIMITS[profile]
    stored = writers.write_upload(
        SimpleUploadedFile("work.txt", b"a" * size), profile=profile, namespace="lms"
    )
    assert stored["size"] == size
    writers.discard_upload(stored["storage_key"])
    with pytest.raises(DomainError) as failure:
        writers.write_upload(
            SimpleUploadedFile("work.txt", b"a" * (size + 1)), profile=profile, namespace="lms"
        )
    assert failure.value.code == "UPLOAD_TOO_LARGE"


def test_storage_configuration_and_path_traversal_fail_closed(settings, tmp_path):
    for key in ("../secrets", "/etc/passwd"):
        with pytest.raises(NotFoundError):
            writers.stream_upload(key, name="file", mime_type="text/plain")
    settings.PRIVATE_UPLOAD_ROOT = str(settings.BASE_DIR / "public")
    assert writers.check_private_upload_root()
    with pytest.raises(DomainError):
        writers.write_upload(
            SimpleUploadedFile("work.txt", b"x"), profile="material", namespace="lms"
        )
    settings.PRIVATE_UPLOAD_ROOT = "/"
    assert writers.check_private_upload_root()
    settings.PRIVATE_UPLOAD_ROOT = str(tmp_path / "web" / "uploads")
    settings.STATIC_ROOT = str(tmp_path / "web")
    assert writers.check_private_upload_root()
    settings.STATIC_ROOT = str(tmp_path / "elsewhere")
    with pytest.raises(ValueError):
        writers.write_upload(
            SimpleUploadedFile("work.txt", b"x"), profile="unknown", namespace="lms"
        )


def test_material_and_submission_file_journey_with_scoped_download(world):
    # UC-LMS-003/004/010/011: FILE variants; BR-LMS-005/012/014.
    url = f"/api/v1/lms/courses/{world.workspace.pk}/materials/"
    response = world.actor().post(
        url,
        {"kind": "FILE", "file": SimpleUploadedFile("notes.txt", b"Faculty notes")},
        format="multipart",
    )
    assert response.status_code == 201
    pk = response.json()["id"]
    assert "storage_key" not in response.content.decode()
    download = f"/api/v1/lms/materials/{pk}/download/"
    assert world.actor("lms_observer").get(download).status_code == 404
    world.actor().post(f"/api/v1/lms/materials/{pk}/publish/", {}, format="json")
    response = world.actor("lms_observer").get(download)
    assert response.status_code == 200 and b"".join(response.streaming_content) == b"Faculty notes"
    assignment = available(world, submission_type="FILE")
    submitted = world.actor("student").post(
        f"/api/v1/lms/assignments/{assignment['id']}/submissions/",
        {"kind": "FILE", "file": SimpleUploadedFile("answer.txt", b"Student work")},
        format="multipart",
    )
    assert submitted.status_code == 201
    response = world.actor("lms_ta").get(
        f"/api/v1/lms/submissions/{submitted.json()['id']}/download/"
    )
    assert response.status_code == 200 and b"".join(response.streaming_content) == b"Student work"


def test_failed_file_validation_consumes_no_submission(world):
    row = available(world, submission_type="FILE")
    url = f"/api/v1/lms/assignments/{row['id']}/submissions/"
    response = world.actor("student").post(
        url, {"kind": "FILE", "file": SimpleUploadedFile("bad.pdf", b"not pdf")}, format="multipart"
    )
    assert response.status_code == 422 and Submission.objects.count() == 0
    assert StoredFile.objects.count() == 0


@pytest.mark.parametrize("kind", ["material", "submission"])
def test_database_failure_cleans_new_bytes(world, monkeypatch, kind):
    def fail(*args, **kwargs):
        raise RuntimeError("Simulated database failure")

    if kind == "material":
        monkeypatch.setattr(Material, "save", fail)
        url = f"/api/v1/lms/courses/{world.workspace.pk}/materials/"
        client = world.actor()
    else:
        row = available(world, submission_type="FILE")
        monkeypatch.setattr(Submission.objects, "create", fail)
        url = f"/api/v1/lms/assignments/{row['id']}/submissions/"
        client = world.actor("student")
    with pytest.raises(RuntimeError):
        client.post(
            url,
            {"kind": "FILE", "file": SimpleUploadedFile("work.txt", b"work")},
            format="multipart",
        )
    assert StoredFile.objects.count() == 0
    assert not [path for path in writers.private_root().rglob("*") if path.is_file()]
