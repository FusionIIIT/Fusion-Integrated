"""Tests for FTS management commands."""
import pytest
from django.core.management import call_command

from modules.fts.models.files import File

pytestmark = pytest.mark.django_db


def test_seed_fts_demo_command():
    call_command("seed_fts_demo")
    assert File.objects.filter(status="DRAFT").exists()
    assert File.objects.filter(status="CIRCULATED").exists()
