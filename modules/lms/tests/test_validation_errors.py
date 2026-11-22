import pytest

from modules.lms.domain.rules import RuleViolation, payload
from modules.lms.models import Material, MaterialSection, Submission
from modules.lms.tests.conftest import available

pytestmark = pytest.mark.django_db
MAX_ORDER = 2_147_483_647


@pytest.mark.parametrize("material", [False, True])
def test_malformed_link_is_a_domain_validation_error(material):
    with pytest.raises(RuleViolation, match="valid HTTP or HTTPS link"):
        payload("LINK", url="http://[", material=material)


@pytest.mark.parametrize("resource", ["sections", "materials"])
@pytest.mark.parametrize("method", ["create", "edit"])
def test_out_of_range_display_order_returns_400_and_preserves_data(world, resource, method):
    client = world.actor()
    collection = f"/api/v1/lms/courses/{world.workspace.pk}/{resource}/"
    data = (
        {"kind": "MODULE", "label": "Unit"}
        if resource == "sections"
        else {
            "kind": "NOTE",
            "text": "Course notes",
        }
    )
    model = MaterialSection if resource == "sections" else Material
    if method == "edit":
        created = client.post(collection, {**data, "order": 3}, format="json")
        assert created.status_code == 201
        pk = created.json()["id"]
        response = client.patch(
            f"/api/v1/lms/{resource}/{pk}/", {"order": MAX_ORDER + 1}, format="json"
        )
        assert model.objects.get(pk=pk).order == 3
        assert model.objects.count() == 1
    else:
        response = client.post(collection, {**data, "order": MAX_ORDER + 1}, format="json")
        assert model.objects.count() == 0
    assert response.status_code == 400
    assert any(detail["field"] == "order" for detail in response.json()["error"]["details"])


@pytest.mark.parametrize("resource", ["sections", "materials"])
@pytest.mark.parametrize("order", [0, MAX_ORDER])
def test_supported_display_order_boundaries_are_accepted(world, resource, order):
    client = world.actor()
    data = (
        {"kind": "MODULE", "label": "Unit"}
        if resource == "sections"
        else {
            "kind": "NOTE",
            "text": "Course notes",
        }
    )
    response = client.post(
        f"/api/v1/lms/courses/{world.workspace.pk}/{resource}/",
        {**data, "order": order},
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["order"] == order


def test_malformed_material_link_returns_422_without_saving(world):
    response = world.actor().post(
        f"/api/v1/lms/courses/{world.workspace.pk}/materials/",
        {"kind": "LINK", "url": "http://["},
        format="json",
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "LMS_RULE_VIOLATION"
    assert Material.objects.count() == 0


def test_malformed_submission_link_consumes_no_attempt(world):
    assignment = available(world, submission_type="LINK")
    client = world.actor("student")
    url = f"/api/v1/lms/assignments/{assignment['id']}/submissions/"
    bad = client.post(url, {"kind": "LINK", "url": "http://["}, format="json")
    assert bad.status_code == 422 and Submission.objects.count() == 0
    valid = client.post(
        url, {"kind": "LINK", "url": "https://example.org/course-work"}, format="json"
    )
    assert valid.status_code == 201 and Submission.objects.count() == 1
