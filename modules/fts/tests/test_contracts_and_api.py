"""Unit tests for FTS Public Contracts and REST APIs."""

import pytest
from rest_framework import status
from rest_framework.test import APIRequestFactory

from modules.fts.api.views import FTSFileViewSet
from modules.fts.contracts import (
    get_active_inbox_files_for_employees,
    get_files_by_uins,
)
from modules.fts.services.drafts import create_file_draft
from modules.fts.services.movements import forward_file


@pytest.mark.django_db
class TestFTSContracts:
    """Tests for modules/fts/contracts.py."""

    def test_get_files_by_uins_plural(self):
        draft1 = create_file_draft(
            creator_id="emp_01",
            creator_role="Staff",
            subject="UIN Contract Test 1",
            initial_comment="Remark 1",
        )
        draft2 = create_file_draft(
            creator_id="emp_02",
            creator_role="Staff",
            subject="UIN Contract Test 2",
            initial_comment="Remark 2",
        )

        dtos = get_files_by_uins([draft1["uin"], draft2["uin"]])
        assert len(dtos) == 2
        subjects = [d.subject for d in dtos]
        assert "UIN Contract Test 1" in subjects
        assert "UIN Contract Test 2" in subjects

    def test_get_active_inbox_files_for_employees_plural(self):
        draft = create_file_draft(
            creator_id="emp_01",
            creator_role="Staff",
            subject="Contract Inbox Test",
            initial_comment="Moving",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="emp_01",
            sender_role="Staff",
            receiver_id="emp_recipient",
            receiver_role="Dean",
            comment="Forwarded",
        )

        result_map = get_active_inbox_files_for_employees(["emp_recipient", "other_emp"])
        assert len(result_map["emp_recipient"]) == 1
        assert result_map["emp_recipient"][0].subject == "Contract Inbox Test"
        assert len(result_map["other_emp"]) == 0


@pytest.mark.django_db
class TestFTSAPIEndpoints:
    """Tests for modules/fts/api/views.py via APIRequestFactory."""

    def setup_method(self):
        self.factory = APIRequestFactory()

    def test_create_draft_endpoint(self):
        view = FTSFileViewSet.as_view(
            {"post": "create_draft"},
            authentication_classes=[],
            permission_classes=[],
        )
        payload = {
            "subject": "API Draft Title",
            "initial_comment": "Testing API creation",
            "priority": "high",
            "category": "general",
            "creator_role": "Faculty",
        }

        request = self.factory.post(
            "/api/fts/files/create-draft/",
            payload,
            format="json",
            HTTP_X_EMPLOYEE_ID="api_user_01",
        )
        response = view(request)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["status"] == "draft"
        assert response.data["subject"] == "API Draft Title"

    def test_inbox_and_history_endpoints(self):
        # Create and forward a file
        draft = create_file_draft(
            creator_id="user_x",
            creator_role="Staff",
            subject="API Workflow File",
            initial_comment="Initial remark",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="user_x",
            sender_role="Staff",
            receiver_id="user_y",
            receiver_role="HOD",
            comment="Passing to user_y",
        )

        # Check user_y inbox via API
        inbox_view = FTSFileViewSet.as_view(
            {"get": "inbox"},
            authentication_classes=[],
            permission_classes=[],
        )
        request = self.factory.get("/api/fts/files/inbox/", HTTP_X_EMPLOYEE_ID="user_y")
        response = inbox_view(request)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["id"] == draft["file_id"]

        # Check file history endpoint via API
        history_view = FTSFileViewSet.as_view(
            {"get": "history"},
            authentication_classes=[],
            permission_classes=[],
        )
        history_request = self.factory.get(
            f"/api/fts/files/{draft['file_id']}/history/", HTTP_X_EMPLOYEE_ID="user_y"
        )
        history_response = history_view(history_request, pk=str(draft["file_id"]))
        assert history_response.status_code == status.HTTP_200_OK
        assert len(history_response.data) == 2  # created, forwarded
