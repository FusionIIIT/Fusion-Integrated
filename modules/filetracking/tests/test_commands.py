"""Tests for File Tracking System management commands."""

from io import StringIO

import pytest
from django.core.management import call_command

from modules.filetracking.models import TrackedFile

pytestmark = pytest.mark.django_db


def test_seed_filetracking_command():
    out = StringIO()
    call_command("seed_filetracking", stdout=out)
    assert "Successfully seeded FileTracking demo data" in out.getvalue()
    assert TrackedFile.objects.count() >= 2

    # Second run is idempotent
    out2 = StringIO()
    call_command("seed_filetracking", stdout=out2)
    assert "already exists" in out2.getvalue()
