"""Tests for CMS public cross-module contracts."""
import pytest
from unittest.mock import MagicMock, patch

from modules.complaints.contracts import (
    ComplaintCountsDTO,
    ComplaintSummaryDTO,
    get_user_complaint_counts,
    get_complaint_summaries,
)


@pytest.mark.django_db
def test_get_user_complaint_counts_empty():
    res = get_user_complaint_counts([])
    assert res == {}


@pytest.mark.django_db
def test_get_complaint_summaries_empty():
    res = get_complaint_summaries([])
    assert res == {}

