"""Registry readiness must never pretend absent institutional policies are configured."""

from datetime import timedelta
from io import StringIO

import pytest
from django.apps import apps
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from modules.hreis.models import HRPolicyVersion
from modules.hreis.registry import readiness

pytestmark = pytest.mark.django_db


def _policy(family, parameters, *, start=None, end=None, version=1):
    now = timezone.now()
    return HRPolicyVersion.objects.create(
        family=family,
        version=version,
        effective_from=start or now - timedelta(days=1),
        effective_until=end,
        parameters=parameters,
        approved_by_user_id=99,
        approved_designation="hradmin",
    )


def _routes():
    return [
        {"employee_kind": "faculty", "department": "CSE", "authorities": ["HOD (CSE)"]}
    ]


def test_seed_modules_marks_unconfigured_hr_eis_planned():
    # HR-CFR-003, HR-CFR-007/008/009/010: no invented policy defaults.
    reasons = readiness()
    assert len(reasons) == 4
    assert all(word in " ".join(reasons) for word in ("LEAVE", "APPRAISAL", "LTC", "CPDA"))
    log = StringIO()
    call_command("seed_modules", stdout=log)
    assert "hreis: registered but NOT active" in log.getvalue()
    assert "registered hreis (planned)" in log.getvalue()
    module_model = apps.get_model("accesscontrol", "Module")
    assert module_model.objects.get(code="hreis").status == "planned"

    with pytest.raises(CommandError, match="4 prerequisite"):
        call_command("hreis_readiness", stdout=StringIO(), stderr=StringIO())


def test_ready_requires_effective_versions_and_complete_required_fields():
    # HR-UC-018, BR-HR-025/029: configuration must be explicit and effective.
    _policy("leave", {"routes": _routes()})
    reasons = readiness()
    assert len(reasons) == 4
    assert "eligibility" in " ".join(reasons)

    _policy(
        "appraisal",
        {
            "routes": _routes(),
            "submission_window": {
                "start": (timezone.now() - timedelta(days=1)).isoformat(),
                "end": (timezone.now() + timedelta(days=1)).isoformat(),
            },
        },
    )
    _policy("ltc", {"routes": _routes()})
    _policy("cpda", {"routes": _routes()})
    assert len(readiness()) == 1


def test_complete_policy_families_become_ready_without_policy_mutation():
    # BR-HR-025: policy versions are append-only, so publish complete new versions.
    now = timezone.now()
    _policy(
        "leave",
        {"routes": _routes(), "eligibility": {"faculty": {"Casual": True}}},
    )
    _policy(
        "appraisal",
        {
            "routes": _routes(),
            "submission_window": {
                "start": (now - timedelta(days=1)).isoformat(),
                "end": (now + timedelta(days=1)).isoformat(),
            },
        },
    )
    _policy("ltc", {"routes": _routes()})
    _policy("cpda", {"routes": _routes()})
    assert readiness() == []
    call_command("hreis_readiness", stdout=StringIO())
    call_command("seed_modules", stdout=StringIO())
    module_model = apps.get_model("accesscontrol", "Module")
    assert module_model.objects.get(code="hreis").status == "active"


def test_expired_and_immutable_superseding_policies_use_latest_effective_version():
    # BR-HR-025: a later higher open-ended revision supersedes a prior immutable one.
    now = timezone.now()
    _policy(
        "leave",
        {"routes": _routes(), "eligibility": {"faculty": {"Casual": True}}},
        start=now - timedelta(days=5),
        end=now - timedelta(days=2),
    )
    assert any("LEAVE" in reason and "Publish" in reason for reason in readiness())

    _policy(
        "leave",
        {"routes": _routes(), "eligibility": {"faculty": {"Casual": True}}},
        start=now - timedelta(days=1),
        version=2,
    )
    _policy(
        "leave",
        {"routes": _routes(), "eligibility": {"faculty": {"Casual": True}}},
        start=now - timedelta(hours=1),
        version=3,
    )
    assert not any("LEAVE" in reason for reason in readiness())
    assert len(readiness()) == 3


def test_finite_overlapping_policy_records_still_fail_readiness():
    now = timezone.now()
    _policy(
        "leave",
        {"routes": _routes(), "eligibility": {"faculty": {"Casual": True}}},
        start=now - timedelta(days=2),
        end=now + timedelta(days=2),
    )
    _policy(
        "leave",
        {"routes": _routes(), "eligibility": {"faculty": {"Casual": True}}},
        start=now - timedelta(days=1),
        end=now + timedelta(days=1),
        version=2,
    )
    assert any("overlapping effective LEAVE" in reason for reason in readiness())
