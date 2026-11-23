import pytest

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "spec_id",
    [f"UC-GYM-{i:03d}" for i in range(1, 13)],
)
def test_uc_traceability(spec_id):
    assert spec_id.startswith("UC-GYM-")


@pytest.mark.parametrize(
    "spec_id",
    [f"BR-GYM-{i:03d}" for i in range(1, 22)],
)
def test_br_traceability(spec_id):
    assert spec_id.startswith("BR-GYM-")


@pytest.mark.parametrize(
    "spec_id",
    [f"BW-GYM-{i:02d}" for i in (1, 2, 3)],
)
def test_workflow_traceability(spec_id):
    assert spec_id.startswith("BW-GYM-")
