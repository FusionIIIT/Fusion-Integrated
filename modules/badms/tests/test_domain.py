from types import SimpleNamespace

import pytest

from modules.badms.domain.departments import department_code
from modules.badms.domain.scheduling import effective_schedules
from modules.badms.domain.state_machine import InvalidTransition, transition


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("CSE", "cse"),
        ("Computer Science Engineering", "cse"),
        ("Liberal   Arts", "liberal arts"),
    ],
)
def test_department_code_normalizes_directory_and_role_labels(label, expected):
    assert department_code(label) == expected


def test_archive_approval_is_restricted_to_department_head():
    assert transition("archive", "submitted", "approve", "hod") == "approved"
    with pytest.raises(InvalidTransition):
        transition("archive", "submitted", "approve", "sysadmin")


def test_enabled_local_schedule_overrides_global_for_same_dataset():
    global_schedule = SimpleNamespace(
        enabled=True, dataset_key="db", scope="global", pk=1,
    )
    local_schedule = SimpleNamespace(
        enabled=True, dataset_key="db", scope="local", pk=2,
    )
    unrelated_global = SimpleNamespace(
        enabled=True, dataset_key="files", scope="global", pk=3,
    )
    assert effective_schedules(
        [global_schedule, local_schedule, unrelated_global],
    ) == [local_schedule, unrelated_global]
