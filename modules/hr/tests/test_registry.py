"""Integration metadata for the HR module registry."""

from modules.hr.registry import MODULE


def test_hr_module_is_active_when_seeded():
    """The access-control layer only exposes modules declared as active."""
    assert MODULE["status"] == "active"
