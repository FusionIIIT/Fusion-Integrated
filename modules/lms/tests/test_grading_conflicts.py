import pytest

from modules.lms.models import Grade, GradeAuditLog, Submission
from modules.lms.tests.conftest import ACTORS, KEY, available

pytestmark = pytest.mark.django_db
BASE = "/api/v1/lms"


def own_submission(world, role):
    row = available(world)
    uid = ACTORS[role][0]
    world.fake.course_associations.extend(
        [
            {
                "user_id": uid,
                "offering_key": KEY,
                "course_role": "STUDENT",
                "source_origin": "fusion_registration",
            },
            {
                "user_id": 6,
                "offering_key": KEY,
                "course_role": "FACULTY",
                "source_origin": "synthetic_fixture",
            },
        ]
    )
    response = world.actor("student", uid=uid, roles=("student", role)).post(
        f"{BASE}/assignments/{row['id']}/submissions/",
        {"kind": "TEXT", "text": "My submitted work"},
        format="json",
    )
    assert response.status_code == 201, response.content
    return response.json()["id"]


def prepare_grade(world, submission_id, state):
    url = f"{BASE}/submissions/{submission_id}/grade/"
    if state != "ABSENT":
        assert (
            world.actor("faculty", uid=6)
            .post(url, {"points": "12", "feedback": "Independent evaluation"}, format="json")
            .status_code
            == 200
        )
    if state == "RELEASED":
        assert (
            world.actor("faculty", uid=6).post(url + "release/", {}, format="json").status_code
            == 200
        )
    return url


def records():
    return [
        list(model.objects.order_by("pk").values()) for model in (Submission, Grade, GradeAuditLog)
    ]


@pytest.mark.parametrize("role", ["faculty", "lms_ta"])
@pytest.mark.parametrize("state", ["ABSENT", "DRAFT", "RELEASED"])
@pytest.mark.parametrize("method", ["post", "patch"])
def test_def_lms_01_own_grading_refused_without_changes(world, role, state, method):
    # DEF-LMS-01: adopted self-grading clarification for BR-LMS-015 / UC-LMS-012.
    submission_id = own_submission(world, role)
    url = prepare_grade(world, submission_id, state)
    before = records()
    client = world.actor(role, roles=("student", role))
    response = getattr(client, method)(
        url, {"points": "20", "feedback": "Own evaluation"}, format="json"
    )
    assert response.status_code == 422, response.content
    assert response.json()["error"]["code"] == "CANNOT_GRADE_OWN_SUBMISSION"
    assert records() == before


@pytest.mark.parametrize("state", ["DRAFT", "RELEASED"])
def test_owner_cannot_release_their_own_grade(world, state):
    submission_id = own_submission(world, "faculty")
    url = prepare_grade(world, submission_id, state)
    before = records()
    response = world.actor().post(url + "release/", {}, format="json")
    assert response.status_code == 422, response.content
    assert response.json()["error"]["code"] == "CANNOT_GRADE_OWN_SUBMISSION"
    assert records() == before


@pytest.mark.parametrize("role", ["faculty", "lms_ta"])
def test_independent_grader_can_grade_after_owner_refusal(world, role):
    submission_id = own_submission(world, role)
    url = prepare_grade(world, submission_id, "ABSENT")
    assert world.actor(role).post(url, {"points": "20"}, format="json").status_code == 422
    response = world.actor("faculty", uid=6).post(
        url, {"points": "15", "feedback": "Independent evaluation"}, format="json"
    )
    assert response.status_code == 200, response.content
    assert response.json()["grader_user_id"] == 6
    assert Grade.objects.count() == 1 and GradeAuditLog.objects.count() == 1
    assert Submission.objects.get(pk=submission_id).user_id == ACTORS[role][0]
