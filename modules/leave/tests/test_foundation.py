from django.apps import apps

from modules.leave.contracts import LeaveSummaryDTO, get_leave_summaries
from modules.leave.registry import MODULE, NAV_ITEMS, PERMISSIONS, ROLE_GRANTS


def test_leave_app_config_registered():
    config = apps.get_app_config("leave")
    assert config.name == "modules.leave"
    assert config.label == "leave"


def test_leave_contract_plural_signature():
    summaries = get_leave_summaries([101, 102])
    assert len(summaries) == 2
    assert isinstance(summaries[101], LeaveSummaryDTO)
    assert summaries[101].user_id == 101


def test_leave_registry_declarations():
    assert MODULE["code"] == "leave"
    assert MODULE["base_path"] == "/leave"
    assert len(NAV_ITEMS) > 0
    assert len(PERMISSIONS) > 0
    assert "faculty" in ROLE_GRANTS
    assert "staff" in ROLE_GRANTS
