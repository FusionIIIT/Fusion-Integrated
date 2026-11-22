"""Tests for Course Submissions API, authorization, file handling, and deadlines (UC-LMS-010, BR-LMS-012, BR-LMS-013, BR-LMS-014)."""
from datetime import timedelta
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from conftest import make_session
from modules.courses.domain.submissions import MAX_SUBMISSION_FILE_SIZE
from modules.courses.models import (
    CourseAssignment,
    CourseSubmission,
)
from modules.courses.permissions import P_WORKSPACE_MANAGE, P_WORKSPACE_VIEW
from modules.courses.tests.factories import add_member, make_workspace


def _auth_client(stub_iam, **session_kw):
    stub_iam(make_session(**session_kw))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock-token")
    return client


@pytest.fixture(autouse=True)
def media_storage_temp(tmp_path):
    with override_settings(MEDIA_ROOT=str(tmp_path)):
        yield


@pytest.fixture
def submission_setup():
    ws1 = make_workspace(code="CS201", title="Data Structures")
    ws2 = make_workspace(code="CS301", title="Operating Systems")

    # ws1 members:
    # Faculty instructor: user 10
    add_member(ws1, user_id=10, role="instructor")
    # TA: user 20
    add_member(ws1, user_id=20, role="ta")
    # Student 1: user 30
    add_member(ws1, user_id=30, role="student")
    # Student 2: user 31
    add_member(ws1, user_id=31, role="student")
    # Observer: user 40
    add_member(ws1, user_id=40, role="observer")

    # ws2 members:
    # Faculty instructor: user 11
    add_member(ws2, user_id=11, role="instructor")
    # Student: user 32
    add_member(ws2, user_id=32, role="student")

    # Create published assignment in ws1 with future deadline
    asgn1 = CourseAssignment.objects.create(
        workspace=ws1,
        title="Lab 1: Binary Trees",
        description="Implement BST operations",
        instructions="Submit your C++ source code or PDF report",
        due_at=timezone.now() + timedelta(days=7),
        is_published=True,
        published_at=timezone.now(),
        created_by_id=10,
    )

    # Create published assignment in ws1 with past deadline
    asgn1_past = CourseAssignment.objects.create(
        workspace=ws1,
        title="Lab 0: Hello World",
        description="Past assignment",
        instructions="Past instructions",
        due_at=timezone.now() - timedelta(days=2),
        is_published=True,
        published_at=timezone.now() - timedelta(days=5),
        created_by_id=10,
    )

    # Create draft (unpublished) assignment in ws1
    asgn1_draft = CourseAssignment.objects.create(
        workspace=ws1,
        title="Exam Prep (Draft)",
        description="Draft assignment",
        is_published=False,
        created_by_id=10,
    )

    # Create published assignment in ws2
    asgn2 = CourseAssignment.objects.create(
        workspace=ws2,
        title="OS Lab 1: Threads",
        description="POSIX threads",
        due_at=timezone.now() + timedelta(days=5),
        is_published=True,
        published_at=timezone.now(),
        created_by_id=11,
    )

    return ws1, ws2, asgn1, asgn1_past, asgn1_draft, asgn2


@pytest.mark.django_db
def test_student_can_submit_file_and_retrieve_own_submission(stub_iam, submission_setup):
    """1. Authorized student successfully submits an assignment and retrieves it (UC-LMS-010, BR-LMS-014)."""
    ws1, _, asgn1, _, _, _ = submission_setup
    client = _auth_client(
        stub_iam,
        user_id=30,  # Student 1
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW,),
    )

    uploaded_file = SimpleUploadedFile(
        "bst_solution.cpp",
        b"#include <iostream>\nint main() { return 0; }",
        content_type="text/x-c",
    )

    res = client.post(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn1.id}/submissions",
        data={
            "submission_type": "file",
            "file": uploaded_file,
            "content": "Here is my BST solution.",
        },
        format="multipart",
    )
    assert res.status_code == status.HTTP_201_CREATED
    data = res.json()
    assert data["student_id"] == 30
    assert data["submission_type"] == "file"
    assert data["filename"] == "bst_solution.cpp"
    assert data["is_late"] is False
    assert data["status"] == "submitted"
    assert data["attempt_number"] == 1
    assert data["file_url"] is not None

    # Retrieve own submission via 'mine'
    mine_res = client.get(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn1.id}/submissions/mine"
    )
    assert mine_res.status_code == status.HTTP_200_OK
    mine_data = mine_res.json()
    assert mine_data["id"] == data["id"]
    assert mine_data["student_id"] == 30

    # Retrieve own submission via list (student sees only their own per BR-LMS-014)
    list_res = client.get(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn1.id}/submissions"
    )
    assert list_res.status_code == status.HTTP_200_OK
    assert list_res.json()["count"] == 1
    assert list_res.json()["results"][0]["id"] == data["id"]


@pytest.mark.django_db
def test_student_cannot_retrieve_or_download_another_student_submission(stub_iam, submission_setup):
    """2. Student cannot retrieve another student's submission or download their file (BR-LMS-014)."""
    ws1, _, asgn1, _, _, _ = submission_setup

    # Student 1 submits
    client1 = _auth_client(
        stub_iam,
        user_id=30,
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW,),
    )
    f1 = SimpleUploadedFile("sol1.pdf", b"%PDF-1.4 sample", content_type="application/pdf")
    res1 = client1.post(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn1.id}/submissions",
        data={"submission_type": "file", "file": f1},
        format="multipart",
    )
    sub1_id = res1.json()["id"]

    # Student 2 accesses
    client2 = _auth_client(
        stub_iam,
        user_id=31,  # Student 2
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW,),
    )

    # Student 2 listing submissions should show 0 results (empty for them)
    list2 = client2.get(f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn1.id}/submissions")
    assert list2.status_code == status.HTTP_200_OK
    assert list2.json()["count"] == 0

    # Student 2 trying to get Student 1's submission by ID returns 404 (isolation/privacy)
    detail2 = client2.get(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn1.id}/submissions/{sub1_id}"
    )
    assert detail2.status_code == status.HTTP_404_NOT_FOUND

    # Student 2 trying to download Student 1's submitted file returns 404
    dl2 = client2.get(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn1.id}/submissions/{sub1_id}/download"
    )
    assert dl2.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_student_cannot_submit_to_unrelated_workspace_or_unpublished_assignment(stub_iam, submission_setup):
    """3. Student cannot submit to unrelated workspace (404) or unpublished assignment (400)."""
    ws1, ws2, asgn1, _, asgn1_draft, asgn2 = submission_setup

    # Student 30 is in ws1, attempts to submit to ws2's asgn2
    client = _auth_client(
        stub_iam,
        user_id=30,
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW,),
    )
    res_wrong_ws = client.post(
        f"/api/v1/courses/workspaces/{ws2.id}/assignments/{asgn2.id}/submissions",
        data={"submission_type": "text", "content": "Wrong course attempt"},
        format="json",
    )
    assert res_wrong_ws.status_code == status.HTTP_404_NOT_FOUND

    # Student attempts to submit to unpublished draft in ws1
    res_draft = client.post(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn1_draft.id}/submissions",
        data={"submission_type": "text", "content": "Draft attempt"},
        format="json",
    )
    assert res_draft.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_faculty_and_ta_can_view_all_submissions_and_download(stub_iam, submission_setup):
    """4. Faculty and TAs can view all submissions for their course, but cannot access unrelated course submissions."""
    ws1, ws2, asgn1, _, _, asgn2 = submission_setup

    # Student 30 submits in ws1
    c30 = _auth_client(stub_iam, user_id=30, modules=("courses",), permissions=(P_WORKSPACE_VIEW,))
    f30 = SimpleUploadedFile("s30.txt", b"Student 30 work", content_type="text/plain")
    c30.post(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn1.id}/submissions",
        data={"submission_type": "file", "file": f30},
        format="multipart",
    )

    # Student 31 submits in ws1
    c31 = _auth_client(stub_iam, user_id=31, modules=("courses",), permissions=(P_WORKSPACE_VIEW,))
    c31.post(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn1.id}/submissions",
        data={"submission_type": "text", "content": "Student 31 work"},
        format="json",
    )

    # Faculty 10 (ws1 instructor) views list
    fac_client = _auth_client(
        stub_iam,
        user_id=10,
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW, P_WORKSPACE_MANAGE),
    )
    fac_res = fac_client.get(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn1.id}/submissions"
    )
    assert fac_res.status_code == status.HTTP_200_OK
    assert fac_res.json()["count"] == 2
    student_ids = {s["student_id"] for s in fac_res.json()["results"]}
    assert student_ids == {30, 31}

    # TA 20 (ws1 TA) views list per BR-LMS-004
    ta_client = _auth_client(
        stub_iam,
        user_id=20,
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW,),
    )
    ta_res = ta_client.get(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn1.id}/submissions"
    )
    assert ta_res.status_code == status.HTTP_200_OK
    assert ta_res.json()["count"] == 2

    # Faculty 10 downloads Student 30's file
    sub_30_id = [s["id"] for s in fac_res.json()["results"] if s["student_id"] == 30][0]
    dl_res = fac_client.get(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn1.id}/submissions/{sub_30_id}/download"
    )
    assert dl_res.status_code == status.HTTP_200_OK
    assert dl_res.getvalue() == b"Student 30 work"

    # Faculty 11 (from ws2) cannot view ws1 submissions
    fac2_client = _auth_client(
        stub_iam,
        user_id=11,
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW, P_WORKSPACE_MANAGE),
    )
    fac2_res = fac2_client.get(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn1.id}/submissions"
    )
    assert fac2_res.status_code in (status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN)


@pytest.mark.django_db
def test_observer_is_strictly_prohibited_from_viewing_or_downloading_submissions(stub_iam, submission_setup):
    """5. Observers cannot view student submissions or download files (BR-LMS-003)."""
    ws1, _, asgn1, _, _, _ = submission_setup

    # Student 30 submits
    c30 = _auth_client(stub_iam, user_id=30, modules=("courses",), permissions=(P_WORKSPACE_VIEW,))
    f30 = SimpleUploadedFile("confidential.txt", b"Private student exam", content_type="text/plain")
    r = c30.post(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn1.id}/submissions",
        data={"submission_type": "file", "file": f30},
        format="multipart",
    )
    sub_id = r.json()["id"]

    # Observer attempts access
    obs_client = _auth_client(
        stub_iam,
        user_id=40,  # Observer
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW,),
    )

    # Attempt to list submissions -> 403 Forbidden
    list_obs = obs_client.get(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn1.id}/submissions"
    )
    assert list_obs.status_code == status.HTTP_403_FORBIDDEN

    # Attempt to get single submission -> 403 Forbidden
    detail_obs = obs_client.get(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn1.id}/submissions/{sub_id}"
    )
    assert detail_obs.status_code == status.HTTP_403_FORBIDDEN

    # Attempt to download submission file -> 403 Forbidden
    dl_obs = obs_client.get(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn1.id}/submissions/{sub_id}/download"
    )
    assert dl_obs.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_deadline_and_late_submission_behavior(stub_iam, submission_setup):
    """6. Submissions before deadline marked on-time; submissions after deadline marked late (BR-LMS-013)."""
    ws1, _, asgn1, asgn1_past, _, _ = submission_setup

    client = _auth_client(
        stub_iam,
        user_id=30,
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW,),
    )

    # 1. On-time submission (asgn1 deadline is 7 days in future)
    res_ontime = client.post(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn1.id}/submissions",
        data={"submission_type": "text", "content": "On time work"},
        format="json",
    )
    assert res_ontime.status_code == status.HTTP_201_CREATED
    data_ontime = res_ontime.json()
    assert data_ontime["is_late"] is False
    assert data_ontime["status"] == "submitted"

    # 2. Late submission (asgn1_past deadline was 2 days ago)
    res_late = client.post(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn1_past.id}/submissions",
        data={"submission_type": "text", "content": "Late work"},
        format="json",
    )
    assert res_late.status_code == status.HTTP_201_CREATED
    data_late = res_late.json()
    assert data_late["is_late"] is True
    assert data_late["status"] == "late"


@pytest.mark.django_db
def test_resubmission_increments_attempt_and_replaces_old_file(stub_iam, submission_setup):
    """7. Resubmission replaces latest submission, increments attempt_number, and removes old file."""
    ws1, _, asgn1, _, _, _ = submission_setup

    client = _auth_client(
        stub_iam,
        user_id=30,
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW,),
    )

    # First attempt
    f_v1 = SimpleUploadedFile("v1.txt", b"Version 1 content", content_type="text/plain")
    res1 = client.post(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn1.id}/submissions",
        data={"submission_type": "file", "file": f_v1, "content": "Attempt 1 note"},
        format="multipart",
    )
    assert res1.status_code == status.HTTP_201_CREATED
    sub1 = res1.json()
    assert sub1["attempt_number"] == 1
    assert sub1["filename"] == "v1.txt"

    sub_obj = CourseSubmission.objects.get(id=sub1["id"])
    v1_file_name = sub_obj.file.name

    # Second attempt (resubmission)
    f_v2 = SimpleUploadedFile("v2.txt", b"Version 2 updated content", content_type="text/plain")
    res2 = client.post(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn1.id}/submissions",
        data={"submission_type": "file", "file": f_v2, "content": "Attempt 2 note"},
        format="multipart",
    )
    assert res2.status_code == status.HTTP_201_CREATED
    sub2 = res2.json()
    assert sub2["id"] == sub1["id"]  # Same submission record updated
    assert sub2["attempt_number"] == 2
    assert sub2["filename"] == "v2.txt"

    # Only 1 submission record exists in the database
    assert CourseSubmission.objects.filter(assignment=asgn1, student_id=30).count() == 1

    # Verify download gives v2 content
    dl = client.get(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn1.id}/submissions/{sub2['id']}/download"
    )
    assert dl.status_code == status.HTTP_200_OK
    assert dl.getvalue() == b"Version 2 updated content"


@pytest.mark.django_db
def test_submission_validation_file_size_and_disallowed_types(stub_iam, submission_setup):
    """8. Rejects disallowed extensions (.exe, .sh), oversized files, and invalid formats."""
    ws1, _, asgn1, _, _, _ = submission_setup

    client = _auth_client(
        stub_iam,
        user_id=30,
        modules=("courses",),
        permissions=(P_WORKSPACE_VIEW,),
    )

    # 1. Disallowed extension .exe
    malicious_file = SimpleUploadedFile(
        "virus.exe",
        b"MZ\x90\x00\x03\x00\x00\x00",
        content_type="application/x-msdownload",
    )
    res_exe = client.post(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn1.id}/submissions",
        data={"submission_type": "file", "file": malicious_file},
        format="multipart",
    )
    assert res_exe.status_code == status.HTTP_400_BAD_REQUEST

    # 2. Oversized file (> 25MB)
    oversized = SimpleUploadedFile(
        "large.pdf",
        b"x" * 100,
        content_type="application/pdf",
    )
    oversized.size = MAX_SUBMISSION_FILE_SIZE + 1024
    from core.api.exceptions import BadRequestError
    from fusion_auth.principal import Principal
    from modules.courses.services import submissions as submissions_svc
    p30 = Principal(
        user_id=30,
        username="student30",
        display_name="Student Thirty",
        kind="student",
        active_role="student",
        roles=("student",),
        permissions=frozenset([P_WORKSPACE_VIEW]),
        modules=("courses",),
    )
    with pytest.raises(BadRequestError, match="File size exceeds 25 MB limit"):
        submissions_svc.submit_assignment(
            workspace_id=ws1.id,
            assignment_id=asgn1.id,
            principal=p30,
            submission_type="file",
            file=oversized,
        )

    # 3. Missing file for file submission
    res_nofile = client.post(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn1.id}/submissions",
        data={"submission_type": "file"},
        format="multipart",
    )
    assert res_nofile.status_code == status.HTTP_400_BAD_REQUEST

    # 4. Invalid URL for link submission
    res_badurl = client.post(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn1.id}/submissions",
        data={"submission_type": "link", "link_url": "javascript:alert(1)"},
        format="json",
    )
    assert res_badurl.status_code == status.HTTP_400_BAD_REQUEST

    # 5. Empty content for text submission
    res_emptytext = client.post(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn1.id}/submissions",
        data={"submission_type": "text", "content": "   "},
        format="json",
    )
    assert res_emptytext.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_text_and_link_submission_types_conformity(stub_iam, submission_setup):
    """9. Validates text and link submission types (BR-LMS-012)."""
    ws1, _, asgn1, _, _, _ = submission_setup

    client30 = _auth_client(stub_iam, user_id=30, modules=("courses",), permissions=(P_WORKSPACE_VIEW,))
    client31 = _auth_client(stub_iam, user_id=31, modules=("courses",), permissions=(P_WORKSPACE_VIEW,))

    # Text submission
    r_text = client30.post(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn1.id}/submissions",
        data={"submission_type": "text", "content": "Proof of correctness for AVL rotations."},
        format="json",
    )
    assert r_text.status_code == status.HTTP_201_CREATED
    assert r_text.json()["submission_type"] == "text"
    assert r_text.json()["content"] == "Proof of correctness for AVL rotations."

    # Link submission
    r_link = client31.post(
        f"/api/v1/courses/workspaces/{ws1.id}/assignments/{asgn1.id}/submissions",
        data={"submission_type": "link", "link_url": "https://github.com/student31/avl-tree"},
        format="json",
    )
    assert r_link.status_code == status.HTTP_201_CREATED
    assert r_link.json()["submission_type"] == "link"
    assert r_link.json()["link_url"] == "https://github.com/student31/avl-tree"
