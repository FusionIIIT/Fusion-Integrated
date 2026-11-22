"""Tests for LMS background tasks and operator commands."""

import io

import pytest
from django.core.management import call_command

from modules.lms.tasks import publish_scheduled_content

pytestmark = pytest.mark.django_db


def test_publish_scheduled_content_task():
    result = publish_scheduled_content()
    assert isinstance(result, int)


def test_publish_scheduled_content_management_command():
    out = io.StringIO()
    call_command("publish_scheduled_content", stdout=out)
    output = out.getvalue()
    assert "Released" in output
