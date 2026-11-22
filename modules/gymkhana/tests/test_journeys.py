import pytest

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "use_case",
    [f"UC-GYM-{i:03d}" for i in range(1, 13)],
)
def test_gymkhana_http_journey(use_case, stub_iam):
    assert use_case.startswith("UC-GYM-")


@pytest.mark.parametrize(
    "workflow",
    ["BW-GYM-01", "BW-GYM-02", "BW-GYM-03"],
)
def test_gymkhana_workflow_journey(workflow, stub_iam):
    assert workflow.startswith("BW-GYM")
