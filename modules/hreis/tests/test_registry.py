"""Approval queue entry must be independent of any one HR request family."""

from modules.hreis.registry import NAV_ITEMS, ROLE_GRANTS


def test_hr_approval_queue_permission_works_for_each_authority():
    approvals = next(row for row in NAV_ITEMS if row["code"] == "hreis.approvals")
    assert approvals["required_permission"] == "hreis.approval.view"
    for role in ("HOD (CSE)", "HOD (ME)", "Registrar", "Director"):
        grants = ROLE_GRANTS[role]
        assert "hreis.approval.view" in grants
        assert "hreis.request.view" in grants
    assert "hreis.approval.view" not in ROLE_GRANTS["faculty"]
    assert "hreis.approval.view" not in ROLE_GRANTS["hradmin"]
    # Maps the specification's Accountant actor to the existing IAM name,
    # explicitly provisional until the institute confirms exact authority.
    assert "Accountant" not in ROLE_GRANTS
    assert {"hreis.finance.review", "hreis.finance.update"} <= set(ROLE_GRANTS["Accounts Admin"])
    assert not any(
        "hreis.finance.update" in grants
        for name, grants in ROLE_GRANTS.items()
        if name != "Accounts Admin"
    )


def test_builder_actor_permissions_cannot_drift_from_registry():
    import pytest

    from modules.hreis.tests.actors import Principal, make_principal, make_session

    with pytest.raises(AssertionError, match="Undeclared HR-EIS test permissions"):
        make_session(permissions=("hreis.misspelled.view",))
    with pytest.raises(AssertionError, match="Undeclared HR-EIS test permissions"):
        make_principal(permissions=("hreis.misspelled.view",))
    with pytest.raises(AssertionError, match="Undeclared HR-EIS test permissions"):
        Principal(
            user_id=1,
            username="synthetic",
            display_name="Synthetic",
            kind="staff",
            active_role="staff",
            roles=("staff",),
            modules=("hreis",),
            permissions=frozenset({"hreis.misspelled.view"}),
        )
