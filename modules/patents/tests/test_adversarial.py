from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from core.api.exceptions import ConflictError
from modules.patents.domain import (
    deadlines,
    policy,
)
from modules.patents.domain import (
    state_machine as sm,
)
from modules.patents.domain.validation import ConflictOfInterestError
from modules.patents.models import (
    AttorneyPanelMember,
    CoInventor,
    PatentApplication,
    PatentBudgetLedger,
    PatentPolicy,
)
from modules.patents.selectors.scoping import applications_for
from modules.patents.services.applications import transition_application


def pcc_admin_actor(user_id: int = 999):
    class Actor:
        def __init__(self):
            self.user_id = user_id
            self.roles = {"pcc_admin"}

        def has_permission(self, perm: str) -> bool:
            return True

    return Actor()


def director_actor(user_id: int = 201):
    class Actor:
        def __init__(self):
            self.user_id = user_id
            self.roles = {"director"}

        def has_permission(self, perm: str) -> bool:
            return perm in {
                "patents.application.review",
                "patents.budget.approve",
                "patents.application.decide_appeal",
                "patents.maintenance.decide",
            }

    return Actor()


def applicant_actor(user_id: int = 101):
    class Actor:
        def __init__(self):
            self.user_id = user_id
            self.roles = {"faculty"}

        def has_permission(self, perm: str) -> bool:
            return perm in {"patents.application.update", "patents.application.withdraw"}

    return Actor()


def attorney_actor(user_id: int = 301):
    class Actor:
        def __init__(self):
            self.user_id = user_id
            self.roles = {"attorney"}

        def has_permission(self, perm: str) -> bool:
            return perm in {
                "patents.attorney.respond_assignment",
                "patents.assessment.perform",
                "patents.filing.record",
                "patents.office_action.record",
                "patents.office_action.respond",
                "patents.maintenance.track",
            }

    return Actor()


@pytest.mark.django_db
def test_conflict_of_interest_guard():
    # BR-PMS-021: COI prevents an author or co-inventor from reviewing their own application.
    app = PatentApplication.objects.create(
        user_id=101,
        application_number="PMS-2026-COI-01",
        title="COI Solar Cell",
        abstract="Abs",
        description="Desc",
        claims="Claims",
        status=sm.SUBMITTED,
    )
    CoInventor.objects.create(
        application=app,
        user_id=102,
        name="Co Inventor",
        email="co@example.com",
        share_percentage=Decimal("30.00"),
    )
    adm_actor = pcc_admin_actor(999)

    # Attempting to assign the primary inventor as director raises ConflictOfInterestError
    with pytest.raises(ConflictOfInterestError, match="authored"):
        transition_application(app.id, "assign_director", adm_actor, payload={"director_id": 101})

    # Attempting to assign a co-inventor as director raises ConflictOfInterestError
    with pytest.raises(ConflictOfInterestError, match="authored"):
        transition_application(app.id, "assign_director", adm_actor, payload={"director_id": 102})

    # Assigning an independent director succeeds
    updated = transition_application(
        app.id, "assign_director", adm_actor, payload={"director_id": 201}
    )
    assert updated.status == sm.UNDER_REVIEW
    assert updated.assigned_director_id == 201


@pytest.mark.django_db
def test_scoping_director():
    # BR-PMS-005/006: Director visibility is strictly scoped to assigned applications.
    dir_actor = director_actor(user_id=201)

    app_assigned = PatentApplication.objects.create(
        user_id=101,
        application_number="PMS-2026-DIR-01",
        title="Assigned to Director 201",
        abstract="Abs",
        description="Desc",
        claims="Claims",
        status=sm.UNDER_REVIEW,
        assigned_director_id=201,
    )
    app_other = PatentApplication.objects.create(
        user_id=101,
        application_number="PMS-2026-DIR-02",
        title="Assigned to Director 202",
        abstract="Abs",
        description="Desc",
        claims="Claims",
        status=sm.UNDER_REVIEW,
        assigned_director_id=202,
    )

    scoped_apps = list(applications_for(dir_actor))
    assert app_assigned in scoped_apps
    assert app_other not in scoped_apps


@pytest.mark.django_db
def test_budget_model():
    # BR-PMS-050..054: Budget ledger records currency, categories, and policy escalation thresholds.
    app = PatentApplication.objects.create(
        user_id=101,
        application_number="PMS-2026-BUD-01",
        title="Budget Test App",
        abstract="Abs",
        description="Desc",
        claims="Claims",
        status=sm.APPROVED,
    )
    entry = PatentBudgetLedger.objects.create(
        application=app,
        entry_type="APPROVAL",
        amount=Decimal("45000.00"),
        category="filing_fee",
        authorized_by_user_id=201,
        notes="Filing fee approval",
    )
    assert entry.currency == "INR"
    assert entry.status == "PENDING"
    assert entry.amount == Decimal("45000.00")

    # Policy threshold evaluation: ₹50,000 threshold
    pol = policy.PolicySpec(cost_escalation_threshold=Decimal("50000.00"))
    assert pol.is_cost_escalation_triggered(Decimal("45000.00")) is False
    assert pol.is_cost_escalation_triggered(Decimal("55000.00")) is True


def test_deadlines():
    # BR-PMS-038 / BR-PMS-060 / BR-PMS-065: Deadline evaluation and alert intervals.
    base = datetime(2026, 1, 1, 10, 0, 0)
    assert not deadlines.is_revision_expired(base, base + timedelta(days=59), limit_days=60)
    assert deadlines.is_revision_expired(base, base + timedelta(days=60), limit_days=60)

    assert not deadlines.is_review_overdue(base, base + timedelta(days=14), limit_days=15)
    assert deadlines.is_review_overdue(base, base + timedelta(days=15), limit_days=15)

    today = date(2026, 6, 1)
    assert deadlines.match_alert_interval(date(2026, 7, 1), today) == 30
    assert deadlines.match_alert_interval(date(2026, 6, 16), today) == 15
    assert deadlines.match_alert_interval(date(2026, 6, 6), today) == 5
    assert deadlines.match_alert_interval(date(2026, 6, 20), today) is None


@pytest.mark.django_db
def test_attorney_assignment_and_workload():
    # BR-PMS-043: Configurable cap (refused at configured limit, allowed below it, and unset).
    adm_actor = pcc_admin_actor(999)

    # 1. Configured limit: max_attorney_workload = 5
    PatentPolicy.objects.create(max_attorney_workload=5, is_active=True)

    app = PatentApplication.objects.create(
        user_id=101,
        application_number="PMS-2026-ATT-01",
        title="Attorney Assignment App",
        abstract="Abs",
        description="Desc",
        claims="Claims",
        status=sm.APPROVED,
    )

    # Attorney at capacity limit (workload = 5) is refused
    busy_attorney = AttorneyPanelMember.objects.create(
        user_id=305,
        firm_name="Overloaded IP Firm",
        active_workload=5,
        is_approved_panel=True,
    )
    with pytest.raises(ConflictError, match="maximum active workload capacity"):
        transition_application(
            app.id, "assign_attorney", adm_actor, payload={"attorney_id": busy_attorney.user_id}
        )

    # Attorney below capacity limit (workload = 4) is allowed
    avail_attorney = AttorneyPanelMember.objects.create(
        user_id=306,
        firm_name="Available IP Firm",
        active_workload=4,
        is_approved_panel=True,
    )
    app = transition_application(
        app.id, "assign_attorney", adm_actor, payload={"attorney_id": avail_attorney.user_id}
    )
    assert app.status == sm.ASSIGNMENT_OFFERED

    # Acceptance increments workload to 5
    att_actor = attorney_actor(avail_attorney.user_id)
    app = transition_application(app.id, "accept_assignment", att_actor)
    assert app.status == sm.ATTORNEY_ASSIGNED
    avail_attorney.refresh_from_db()
    assert avail_attorney.active_workload == 5

    # 2. Unset behaviour: when policy cap is unconfigured (None), no cap is enforced
    PatentPolicy.objects.filter(is_active=True).update(max_attorney_workload=None)
    app2 = PatentApplication.objects.create(
        user_id=101,
        application_number="PMS-2026-ATT-02",
        title="Unset Cap App",
        abstract="Abs",
        description="Desc",
        claims="Claims",
        status=sm.APPROVED,
    )
    high_load_attorney = AttorneyPanelMember.objects.create(
        user_id=307,
        firm_name="Uncapped IP Firm",
        active_workload=10,
        is_approved_panel=True,
    )
    app2 = transition_application(
        app2.id, "assign_attorney", adm_actor, payload={"attorney_id": high_load_attorney.user_id}
    )
    assert app2.status == sm.ASSIGNMENT_OFFERED


@pytest.mark.django_db
def test_attorney_workload_exits():
    # Verify workload decrements across exits per approved blueprint: decline, reassignment, withdrawal, completion.
    adm_actor = pcc_admin_actor(999)
    app_actor = applicant_actor(101)
    PatentPolicy.objects.create(
        max_attorney_workload=5,
        withdrawal_eligible_states=[sm.ATTORNEY_ASSIGNED, sm.ASSESSMENT_IN_PROGRESS],
        is_active=True,
    )

    # 1. Decline (ASSIGNMENT_OFFERED -> PENDING_REVIEW, BW-PMS-07 row 2)
    # Case A: Decline offered assignment where attorney had active workload
    att1 = AttorneyPanelMember.objects.create(
        user_id=311, firm_name="Firm 311", active_workload=1, is_approved_panel=True
    )
    app1 = PatentApplication.objects.create(
        user_id=101,
        application_number="PMS-2026-EXIT-01",
        title="Exit Decline Test",
        abstract="Abs",
        description="Desc",
        claims="Claims",
        status=sm.ASSIGNMENT_OFFERED,
        assigned_attorney_id=att1.user_id,
    )
    assert att1.active_workload == 1  # Workload before decline
    app1 = transition_application(app1.id, "decline_assignment", attorney_actor(311))
    assert app1.status == sm.PENDING_REVIEW
    att1.refresh_from_db()
    assert att1.active_workload == 0  # Workload after decline
    assert app1.assigned_attorney_id is None

    # Case B: Decline unaccepted offer where attorney workload was 0
    att1_b = AttorneyPanelMember.objects.create(
        user_id=312, firm_name="Firm 312", active_workload=0, is_approved_panel=True
    )
    app1_b = PatentApplication.objects.create(
        user_id=101,
        application_number="PMS-2026-EXIT-01B",
        title="Exit Decline Unaccepted Test",
        abstract="Abs",
        description="Desc",
        claims="Claims",
        status=sm.ASSIGNMENT_OFFERED,
        assigned_attorney_id=att1_b.user_id,
    )
    assert att1_b.active_workload == 0  # Workload before decline
    app1_b = transition_application(app1_b.id, "decline_assignment", attorney_actor(312))
    assert app1_b.status == sm.PENDING_REVIEW
    att1_b.refresh_from_db()
    assert att1_b.active_workload == 0  # Workload after decline

    # 2. Reassignment (PENDING_REVIEW -> ASSIGNMENT_OFFERED, BW-PMS-07 row 3)
    att2 = AttorneyPanelMember.objects.create(
        user_id=313, firm_name="Firm 313", active_workload=0, is_approved_panel=True
    )
    assert att2.active_workload == 0  # Workload before reassignment offer
    app1 = transition_application(
        app1.id, "assign_attorney", adm_actor, payload={"attorney_id": att2.user_id}
    )
    assert app1.status == sm.ASSIGNMENT_OFFERED
    att2.refresh_from_db()
    assert att2.active_workload == 0  # Workload before acceptance
    app1 = transition_application(app1.id, "accept_assignment", attorney_actor(313))
    assert app1.status == sm.ATTORNEY_ASSIGNED
    att2.refresh_from_db()
    assert att2.active_workload == 1  # Workload after acceptance

    # 3. Withdrawal (ATTORNEY_ASSIGNED -> WITHDRAWN, BW-PMS-16)
    att3 = AttorneyPanelMember.objects.create(
        user_id=314, firm_name="Firm 314", active_workload=0, is_approved_panel=True
    )
    app3 = PatentApplication.objects.create(
        user_id=101,
        application_number="PMS-2026-EXIT-03",
        title="Exit Withdrawal Test",
        abstract="Abs",
        description="Desc",
        claims="Claims",
        status=sm.APPROVED,
    )
    app3 = transition_application(
        app3.id, "assign_attorney", adm_actor, payload={"attorney_id": att3.user_id}
    )
    app3 = transition_application(app3.id, "accept_assignment", attorney_actor(314))
    att3.refresh_from_db()
    assert att3.active_workload == 1  # Workload before withdrawal
    app3 = transition_application(
        app3.id, "withdraw", app_actor, payload={"reason": "Business strategy changed"}
    )
    assert app3.status == sm.WITHDRAWN
    att3.refresh_from_db()
    assert att3.active_workload == 0  # Workload after withdrawal

    # 4. Completion (FILED -> GRANTED, BR-PMS-059)
    att4 = AttorneyPanelMember.objects.create(
        user_id=315, firm_name="Firm 315", active_workload=0, is_approved_panel=True
    )
    app4 = PatentApplication.objects.create(
        user_id=101,
        application_number="PMS-2026-EXIT-04",
        title="Exit Completion Test",
        abstract="Abs",
        description="Desc",
        claims="Claims",
        status=sm.APPROVED,
    )
    app4 = transition_application(
        app4.id, "assign_attorney", adm_actor, payload={"attorney_id": att4.user_id}
    )
    app4 = transition_application(app4.id, "accept_assignment", attorney_actor(315))
    app4 = transition_application(app4.id, "start_assessment", attorney_actor(315))
    app4.status = sm.FILED
    app4.save()
    att4.refresh_from_db()
    assert att4.active_workload == 1  # Workload before grant completion
    app4 = transition_application(app4.id, "grant", adm_actor)
    assert app4.status == sm.GRANTED
    att4.refresh_from_db()
    assert att4.active_workload == 0  # Workload after grant completion
