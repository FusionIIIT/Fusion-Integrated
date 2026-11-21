"""Unit tests for FTS Public Contracts and REST APIs."""

import pytest
from rest_framework import status
from rest_framework.test import APIRequestFactory

from modules.fts.api.views import FTSFileViewSet
from modules.fts.contracts import (
    get_active_inbox_files_for_employees,
    get_files_by_uins,
)
from modules.fts.models import FTSAttachment, FTSComment, FTSFile, FTSMovement
from modules.fts.registry import (
    get_module_info,
    get_permissions,
    get_role_grants,
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

    def test_get_files_by_empty_uins(self):
        assert get_files_by_uins([]) == []


class TestFTSRegistry:
    """Tests for registry.py metadata and access functions."""

    def test_registry_metadata(self):
        info = get_module_info()
        assert info["code"] == "fts"
        assert info["icon"] == "Folder"

        perms = get_permissions()
        assert len(perms) == 4
        codes = [c for c, _ in perms]
        assert "fts.file.view" in codes

        grants = get_role_grants()
        assert "faculty" in grants
        assert "staff" in grants


@pytest.mark.django_db
class TestFTSModelStr:
    """Tests for model string representations."""

    def test_model_string_representations(self):
        draft = create_file_draft(
            creator_id="emp_str_1",
            creator_role="Staff",
            subject="Str Test File",
            initial_comment="Testing string representations",
        )
        file_obj = FTSFile.objects.get(id=draft["file_id"])
        assert str(file_obj) == f"{file_obj.uin} - Str Test File"

        mov = FTSMovement.objects.filter(file=file_obj).first()
        assert mov is not None
        assert "emp_str_1" in str(mov)

        com = FTSComment.objects.filter(file=file_obj).first()
        assert com is not None
        assert "emp_str_1" in str(com)

        att = FTSAttachment.objects.create(
            file=file_obj,
            movement=mov,
            file_name="spec.pdf",
            file_url="https://example.com/spec.pdf",
            uploaded_by_id="emp_str_1",
        )
        assert str(att) == "spec.pdf"



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

    def test_outbox_and_drafts_endpoints(self):
        draft = create_file_draft(
            creator_id="user_api_1",
            creator_role="Staff",
            subject="Draft and Outbox File",
            initial_comment="Testing outbox and drafts",
        )

        drafts_view = FTSFileViewSet.as_view(
            {"get": "drafts"},
            authentication_classes=[],
            permission_classes=[],
        )
        req = self.factory.get("/api/fts/files/drafts/", HTTP_X_EMPLOYEE_ID="user_api_1")
        resp = drafts_view(req)
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) >= 1

        forward_file(
            file_id=draft["file_id"],
            sender_id="user_api_1",
            sender_role="Staff",
            receiver_id="user_api_2",
            receiver_role="Faculty",
            comment="Sending to user 2",
        )

        outbox_view = FTSFileViewSet.as_view(
            {"get": "outbox"},
            authentication_classes=[],
            permission_classes=[],
        )
        req2 = self.factory.get("/api/fts/files/outbox/", HTTP_X_EMPLOYEE_ID="user_api_1")
        resp2 = outbox_view(req2)
        assert resp2.status_code == status.HTTP_200_OK
        assert len(resp2.data) >= 1

    def test_forward_endpoint_success_and_error(self):
        draft = create_file_draft(
            creator_id="user_fwd_1",
            creator_role="Staff",
            subject="Forward API File",
            initial_comment="Initial",
        )

        fwd_view = FTSFileViewSet.as_view(
            {"post": "forward"},
            authentication_classes=[],
            permission_classes=[],
        )
        # Success
        payload = {
            "sender_role": "Staff",
            "receiver_id": "user_fwd_2",
            "receiver_role": "Faculty",
            "comment": "Forwarding via API",
        }
        req = self.factory.post(
            f"/api/fts/files/{draft['file_id']}/forward/",
            payload,
            format="json",
            HTTP_X_EMPLOYEE_ID="user_fwd_1",
        )
        resp = fwd_view(req, pk=str(draft["file_id"]))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["current_holder_id"] == "user_fwd_2"

        # Failure: non-custodian forward attempt
        req_fail = self.factory.post(
            f"/api/fts/files/{draft['file_id']}/forward/",
            payload,
            format="json",
            HTTP_X_EMPLOYEE_ID="intruder_user",
        )
        resp_fail = fwd_view(req_fail, pk=str(draft["file_id"]))
        assert resp_fail.status_code == status.HTTP_400_BAD_REQUEST

    def test_return_endpoint_success_and_error(self):
        draft = create_file_draft(
            creator_id="user_ret_1",
            creator_role="Staff",
            subject="Return API File",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="user_ret_1",
            sender_role="Staff",
            receiver_id="user_ret_2",
            receiver_role="Faculty",
            comment="Sent to 2",
        )

        ret_view = FTSFileViewSet.as_view(
            {"post": "return_file_action"},
            authentication_classes=[],
            permission_classes=[],
        )
        # Success
        payload = {
            "sender_role": "Faculty",
            "comment": "Returning to creator",
        }
        req = self.factory.post(
            f"/api/fts/files/{draft['file_id']}/return_file_action/",
            payload,
            format="json",
            HTTP_X_EMPLOYEE_ID="user_ret_2",
        )
        resp = ret_view(req, pk=str(draft["file_id"]))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["returned_to_id"] == "user_ret_1"

        # Failure: non-custodian return attempt
        req_fail = self.factory.post(
            f"/api/fts/files/{draft['file_id']}/return_file_action/",
            payload,
            format="json",
            HTTP_X_EMPLOYEE_ID="random_user",
        )
        resp_fail = ret_view(req_fail, pk=str(draft["file_id"]))
        assert resp_fail.status_code == status.HTTP_400_BAD_REQUEST

    def test_archive_endpoint_success_and_error(self):
        draft = create_file_draft(
            creator_id="user_arc_1",
            creator_role="Staff",
            subject="Archive API File",
            initial_comment="Initial",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="user_arc_1",
            sender_role="Staff",
            receiver_id="user_arc_2",
            receiver_role="Faculty",
            comment="Sent to 2",
        )

        arc_view = FTSFileViewSet.as_view(
            {"post": "archive"},
            authentication_classes=[],
            permission_classes=[],
        )
        # Success
        payload = {
            "user_role": "Staff",
            "remarks": "Process complete. Archiving.",
        }
        req = self.factory.post(
            f"/api/fts/files/{draft['file_id']}/archive/",
            payload,
            format="json",
            HTTP_X_EMPLOYEE_ID="user_arc_1",
        )
        resp = arc_view(req, pk=str(draft["file_id"]))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["status"] == "archived"

        # Failure: attempt to archive again
        req_fail = self.factory.post(
            f"/api/fts/files/{draft['file_id']}/archive/",
            payload,
            format="json",
            HTTP_X_EMPLOYEE_ID="user_arc_1",
        )
        resp_fail = arc_view(req_fail, pk=str(draft["file_id"]))
        assert resp_fail.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_draft_endpoint_validation_error(self):
        view = FTSFileViewSet.as_view(
            {"post": "create_draft"},
            authentication_classes=[],
            permission_classes=[],
        )
        # Missing subject
        req = self.factory.post(
            "/api/fts/files/create-draft/",
            {"initial_comment": "Missing subject"},
            format="json",
            HTTP_X_EMPLOYEE_ID="user_val",
        )
        resp = view(req)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_authenticated_user_context(self):
        class MockUser:
            username = "auth_ctx_user"

        view = FTSFileViewSet()
        req = self.factory.get("/api/fts/files/inbox/")
        req.user = MockUser()
        user_id = view._get_current_user_id(req)
        assert user_id == "auth_ctx_user"

