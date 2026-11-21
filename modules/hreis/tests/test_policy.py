"""Institutional HR policy is explicit, effective-dated and auditable."""

from datetime import timedelta

import pytest
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, PermissionDeniedError
from fusion_auth.principal import Principal
from modules.hreis.models import AuditEvent, HRPolicyVersion
from modules.hreis.services import policies

pytestmark = pytest.mark.django_db


def actor(role="hradmin", permission=True):
    return Principal(
        user_id=99,
        username="administrator",
        display_name="HR",
        kind="staff",
        active_role=role,
        roles=(role,),
        permissions=frozenset({"hreis.policy.manage"} if permission else ()),
        modules=("hreis",),
    )


def dates():
    now = timezone.now()
    return now - timedelta(days=1), now + timedelta(days=1)


def payload():
    return {
        "routes": [
            {
                "employee_kind": "faculty",
                "department": "CSE",
                "authorities": ["HOD (CSE)", "Registrar"],
            },
        ],
        "eligibility": {"faculty": {"Casual": True, "Medical": False}},
    }


def create(
    *,
    family="leave",
    version=1,
    start=None,
    end=None,
    parameters=None,
    key="policy-v1",
    acting=None,
):
    past, future = dates()
    return policies.create_policy(
        acting or actor(),
        family=family,
        version=version,
        effective_from=start or past,
        effective_until=future if end is None else end,
        parameters=parameters or payload(),
        idempotency_key=key,
    )


def test_version_is_immutable_audited_and_current():
    # HR-UC-017, HR-AFR-012, BR-HR-025: immutable approved policy versions.
    row = create()
    assert row.approved_by_user_id == 99
    assert policies.current_policy("leave").pk == row.pk
    event = AuditEvent.objects.get(event_key="policy:policy-v1")
    assert event.actor_user_id == 99
    assert event.data == {"family": "leave", "version": 1}


def test_uncertain_or_conflicting_policy_is_refused():
    with pytest.raises(ConflictError) as exc:
        policies.current_policy("leave")
    assert exc.value.code == "policy_unavailable"
    create()
    with pytest.raises(ConflictError) as exc:
        create(version=2, key="policy-v2")
    assert exc.value.code == "policy_overlap"
    assert HRPolicyVersion.objects.count() == 1


def test_bad_roles_cannot_publish_policy():
    with pytest.raises(PermissionDeniedError):
        create(acting=actor("staff"))
    with pytest.raises(PermissionDeniedError):
        create(acting=actor(permission=False))
    assert not HRPolicyVersion.objects.exists()


@pytest.mark.parametrize(
    "invalid",
    [
        {
            "routes": [
                {"employee_kind": "faculty", "department": "CSE", "authorities": ["Unknown Role"]}
            ]
        },
        {
            "routes": [
                {
                    "employee_kind": "faculty",
                    "department": "CSE",
                    "authorities": ["Registrar", "Registrar"],
                }
            ]
        },
        {
            "routes": [
                {"employee_kind": "faculty", "department": "CSE", "authorities": ["Registrar"]},
                {"employee_kind": "faculty", "department": "CSE", "authorities": ["Director"]},
            ]
        },
        {"eligibility": {"faculty": {"Casual": "yes"}}},
        {"entitlements": {"Casual": 365}},
        {"submission_window": {"start": "2026-01-01", "end": "2026-02-01"}},
    ],
)
def test_invalid_policy_cannot_be_published(invalid):
    with pytest.raises(BadRequestError):
        create(parameters=invalid)
    assert not HRPolicyVersion.objects.exists()


def test_operation_replay_cannot_create_second_policy():
    create()
    later = timezone.now() + timedelta(days=2)
    with pytest.raises(ConflictError) as exc:
        create(version=2, start=later, end=later + timedelta(days=1))
    assert exc.value.code == "operation_replayed"
    assert HRPolicyVersion.objects.count() == 1


def test_back_to_back_policy_windows_do_not_overlap():
    _past, future = dates()
    create(end=future)
    next_row = create(version=2, start=future, end=future + timedelta(days=2), key="next-window")
    assert next_row.version == 2
    assert policies.current_policy("leave").version == 1


def test_open_ended_immutable_policy_can_be_superseded_by_higher_version():
    # BR-HR-025: a new immutable version succeeds without modifying its predecessor.
    now = timezone.now()
    original = policies.create_policy(
        actor(), family="leave", version=1,
        effective_from=now - timedelta(days=2),
        effective_until=None, parameters=payload(),
        idempotency_key="open-policy-first",
    )
    original_end = original.effective_until
    successor = policies.create_policy(
        actor(), family="leave", version=2,
        effective_from=now + timedelta(hours=1),
        effective_until=None,
        parameters=payload(),
        idempotency_key="open-policy-next",
    )
    original.refresh_from_db()
    assert original.effective_until is original_end is None
    assert policies.current_policy("leave", at=now).pk == original.pk
    assert policies.current_policy("leave", at=now + timedelta(hours=2)).pk == successor.pk
    with pytest.raises(ConflictError):
        policies.create_policy(
            actor(), family="leave", version=1,
            effective_from=now + timedelta(hours=3),
            effective_until=None, parameters=payload(),
            idempotency_key="bad-policy-regression",
        )
    assert HRPolicyVersion.objects.count() == 2


def test_bounded_successor_supersedes_immutable_open_version_without_revival():
    # BR-HR-025: bounded successor publication never edits or revives the old policy.
    now = timezone.now()
    first = policies.create_policy(
        actor(), family="leave", version=1,
        effective_from=now - timedelta(days=2), effective_until=None,
        parameters=payload(), idempotency_key="bounded-predecessor",
    )
    second = policies.create_policy(
        actor(), family="leave", version=2,
        effective_from=now + timedelta(hours=1),
        effective_until=now + timedelta(hours=3),
        parameters=payload(), idempotency_key="bounded-successor",
    )
    first.refresh_from_db()
    assert first.effective_until is None
    assert policies.current_policy("leave", at=now).pk == first.pk
    assert policies.current_policy(
        "leave", at=now + timedelta(hours=2)
    ).pk == second.pk
    with pytest.raises(ConflictError) as expired:
        policies.current_policy("leave", at=now + timedelta(hours=4))
    assert expired.value.code == "policy_unavailable"
    assert HRPolicyVersion.objects.count() == 2


@pytest.mark.django_db(transaction=True)
def test_concurrent_overlapping_policy_publications_serialize(monkeypatch):
    # BR-HR-025: simultaneous versions cannot both pass the overlap check.
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import close_old_connections

    gate = Barrier(2)
    original_check = policies._check_parameters

    def both_enter_before_db_lock(family, parameters):
        result = original_check(family, parameters)
        gate.wait(timeout=15)
        return result

    monkeypatch.setattr(policies, "_check_parameters", both_enter_before_db_lock)
    now = timezone.now()

    def publish(version):
        close_old_connections()
        try:
            return policies.create_policy(
                actor(), family="leave", version=version,
                effective_from=now - timedelta(hours=1),
                effective_until=now + timedelta(hours=2),
                parameters=payload(),
                idempotency_key=f"concurrent-publish-{version}",
            )
        except ConflictError as error:
            return error
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(publish, (30, 31)))
    assert sum(isinstance(x, HRPolicyVersion) for x in results) == 1
    denied = [x for x in results if isinstance(x, ConflictError)]
    assert len(denied) == 1 and denied[0].code == "policy_overlap"
    assert HRPolicyVersion.objects.filter(family="leave").count() == 1
