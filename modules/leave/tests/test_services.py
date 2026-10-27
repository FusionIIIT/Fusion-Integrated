"""Integration tests for leave services."""
import datetime
from decimal import Decimal
import pytest

from core.api.exceptions import ConflictError
from modules.leave.models import LeaveBalance, LeaveApplication, SubstituteRequest
from modules.leave.services import (
    apply_for_leave,
    withdraw_application,
    request_cancellation,
    respond_to_substitute_request,
    review_by_unit_head,
    sanction_application,
    process_cancellation_decision,
    submit_resumption_declaration,
    review_resumption_declaration,
    run_year_end_processing,
)


@pytest.mark.django_db
def test_apply_and_unit_head_approve_cl():
    user_id = 101
    start = datetime.date(2026, 11, 2)  # Monday
    end = datetime.date(2026, 11, 3)    # Tuesday

    # Initialize balance
    bal = LeaveBalance.objects.create(user_id=user_id, year=2026, cl_balance=Decimal("8.0"))

    app = apply_for_leave(
        user_id=user_id,
        category="CL",
        start_date=start,
        end_date=end,
        purpose="Personal work",
    )
    assert app.status == "under_review"
    assert app.days_count == Decimal("2.0")

    # Unit head review (CL: Unit Head is final)
    reviewed = review_by_unit_head(
        reviewer_user_id=201,
        application_id=app.pk,
        recommended=True,
        remarks="Approved",
    )
    assert reviewed.status == "approved"

    bal.refresh_from_db()
    assert bal.cl_balance == Decimal("6.0")  # 8 - 2 = 6


@pytest.mark.django_db
def test_substitute_workflow_and_higher_sanction_el(stub_iam, user_ref):
    applicant_id = 102
    substitute_id = 103
    start = datetime.date(2026, 11, 2)
    end = datetime.date(2026, 11, 6)

    stub_iam(users={substitute_id: user_ref(substitute_id, name="Staff 103", kind="staff")})

    bal = LeaveBalance.objects.create(user_id=applicant_id, year=2026, el_balance=Decimal("30.0"))

    app = apply_for_leave(
        user_id=applicant_id,
        category="EL",
        start_date=start,
        end_date=end,
        purpose="Family event",
        substitute_user_id=substitute_id,
        responsibilities="Handle office inquiries",
    )
    assert app.status == "substitute_pending"

    # Substitute accepts
    sub_req = SubstituteRequest.objects.get(application=app)
    respond_to_substitute_request(
        substitute_user_id=substitute_id,
        request_id=sub_req.pk,
        decision="accepted",
        remarks="Will cover",
    )

    app.refresh_from_db()
    assert app.status == "under_review"

    # Unit Head recommends (EL: Unit head does NOT make final decision)
    review_by_unit_head(
        reviewer_user_id=201,
        application_id=app.pk,
        recommended=True,
        remarks="Recommended to Dean",
    )

    app.refresh_from_db()
    assert app.status == "under_review"
    assert app.unit_head_recommended is True

    # Dean / Sanctioning authority sanctions
    sanction_application(
        sanctioner_user_id=301,
        application_id=app.pk,
        decision="approved",
        remarks="Sanctioned",
    )

    app.refresh_from_db()
    assert app.status == "approved"

    bal.refresh_from_db()
    assert bal.el_balance == Decimal("25.0")  # 30 - 5 = 25


@pytest.mark.django_db
def test_withdrawal_before_approval():
    user_id = 104
    start = datetime.date(2026, 11, 9)
    end = datetime.date(2026, 11, 10)

    LeaveBalance.objects.create(user_id=user_id, year=2026, cl_balance=Decimal("8.0"))
    app = apply_for_leave(
        user_id=user_id,
        category="CL",
        start_date=start,
        end_date=end,
        purpose="Medical checkup",
    )
    assert app.status == "under_review"

    withdrawn = withdraw_application(user_id=user_id, application_id=app.pk, reason="Plans changed")
    assert withdrawn.status == "withdrawn"


@pytest.mark.django_db
def test_resumption_early_return_adjusts_balance():
    user_id = 105
    start = datetime.date(2026, 11, 2)
    end = datetime.date(2026, 11, 6)  # 5 days approved

    bal = LeaveBalance.objects.create(user_id=user_id, year=2026, el_balance=Decimal("30.0"))
    app = apply_for_leave(
        user_id=user_id,
        category="EL",
        start_date=start,
        end_date=end,
        purpose="Conference travel",
    )
    sanction_application(sanctioner_user_id=301, application_id=app.pk, decision="approved")

    bal.refresh_from_db()
    assert bal.el_balance == Decimal("25.0")  # deducted 5 days

    # Early resumption: returns on Nov 5 instead of after Nov 6 (resumed on Nov 5, availed Nov 2-4 = 3 days)
    resumed = submit_resumption_declaration(
        user_id=user_id,
        application_id=app.pk,
        resumption_date=datetime.date(2026, 11, 5),
    )
    assert resumed.status == "resumption_submitted"

    review_resumption_declaration(reviewer_user_id=301, application_id=app.pk)
    resumed.refresh_from_db()
    assert resumed.status == "closed"

    bal.refresh_from_db()
    # 2 unused days restored: 25 + 2 = 27
    assert bal.el_balance == Decimal("27.0")


@pytest.mark.django_db
def test_late_resumption_deducts_additional_days():
    user_id = 106
    start = datetime.date(2026, 11, 2)
    end = datetime.date(2026, 11, 6)  # 5 days approved

    bal = LeaveBalance.objects.create(user_id=user_id, year=2026, el_balance=Decimal("30.0"))
    app = apply_for_leave(
        user_id=user_id,
        category="EL",
        start_date=start,
        end_date=end,
        purpose="Field research",
    )
    sanction_application(sanctioner_user_id=301, application_id=app.pk, decision="approved")
    bal.refresh_from_db()
    assert bal.el_balance == Decimal("25.0")

    # Resumed on Nov 9 instead of Nov 7 (actual leave Nov 2-8 = 7 days)
    resumed = submit_resumption_declaration(
        user_id=user_id,
        application_id=app.pk,
        resumption_date=datetime.date(2026, 11, 9),
    )
    review_resumption_declaration(reviewer_user_id=301, application_id=app.pk)
    resumed.refresh_from_db()
    assert resumed.status == "closed"
    bal.refresh_from_db()
    # 2 extra days deducted: 25 - 2 = 23
    assert bal.el_balance == Decimal("23.0")


@pytest.mark.django_db
def test_substitute_decline_and_renominate_flow(stub_iam, user_ref):
    applicant_id = 110
    sub1_id = 111
    sub2_id = 112
    stub_iam(users={
        sub1_id: user_ref(sub1_id, name="Sub One", kind="faculty"),
        sub2_id: user_ref(sub2_id, name="Sub Two", kind="faculty"),
    })
    LeaveBalance.objects.create(user_id=applicant_id, year=2026, cl_balance=Decimal("8.0"))

    app = apply_for_leave(
        user_id=applicant_id,
        category="CL",
        start_date=datetime.date(2026, 11, 2),
        end_date=datetime.date(2026, 11, 3),
        purpose="Family function",
        substitute_user_id=sub1_id,
        responsibilities="Class coverage",
    )
    assert app.status == "substitute_pending"

    sub1_req = SubstituteRequest.objects.get(application=app, substitute_user_id=sub1_id)
    # Substitute 1 declines (BW-EL-03)
    respond_to_substitute_request(
        substitute_user_id=sub1_id,
        request_id=sub1_req.pk,
        decision="declined",
        remarks="Busy with conference",
    )
    app.refresh_from_db()
    assert app.status == "substitute_pending"

    # Re-nominate Substitute 2 (EL-UC-019)
    from modules.leave.services import re_nominate_substitute
    sub2_req = re_nominate_substitute(
        user_id=applicant_id,
        application_id=app.pk,
        new_substitute_user_id=sub2_id,
        responsibilities="Class coverage updated",
    )
    assert sub2_req.status == "pending"
    assert sub2_req.is_current is True

    # Substitute 2 accepts
    respond_to_substitute_request(
        substitute_user_id=sub2_id,
        request_id=sub2_req.pk,
        decision="accepted",
        remarks="Glad to cover",
    )
    app.refresh_from_db()
    assert app.status == "under_review"


@pytest.mark.django_db
def test_pre_start_cancellation_approved_and_restored():
    user_id = 120
    bal = LeaveBalance.objects.create(user_id=user_id, year=2026, cl_balance=Decimal("8.0"))
    # Apply for next month so leave is strictly future
    start = datetime.date(2026, 12, 1)
    end = datetime.date(2026, 12, 2)
    app = apply_for_leave(
        user_id=user_id,
        category="CL",
        start_date=start,
        end_date=end,
        purpose="Winter travel",
    )
    review_by_unit_head(reviewer_user_id=201, application_id=app.pk, recommended=True)
    bal.refresh_from_db()
    assert bal.cl_balance == Decimal("6.0")  # 8 - 2 = 6

    # Request cancellation before start (BR-EL-023)
    cancel_app = request_cancellation(user_id=user_id, application_id=app.pk, reason="Trip cancelled")
    assert cancel_app.status == "cancel_requested"

    # Approve cancellation
    process_cancellation_decision(reviewer_user_id=201, application_id=cancel_app.pk, decision="approved")
    app.refresh_from_db()
    cancel_app.refresh_from_db()
    assert app.status == "cancelled"
    assert cancel_app.status == "cancelled"
    bal.refresh_from_db()
    # Balance restored!
    assert bal.cl_balance == Decimal("8.0")


@pytest.mark.django_db
def test_pre_start_cancellation_rejected_leaves_original_approved():
    user_id = 121
    bal = LeaveBalance.objects.create(user_id=user_id, year=2026, cl_balance=Decimal("8.0"))
    start = datetime.date(2026, 12, 7)
    end = datetime.date(2026, 12, 8)
    app = apply_for_leave(
        user_id=user_id,
        category="CL",
        start_date=start,
        end_date=end,
        purpose="Event",
    )
    review_by_unit_head(reviewer_user_id=201, application_id=app.pk, recommended=True)
    bal.refresh_from_db()
    assert bal.cl_balance == Decimal("6.0")

    cancel_app = request_cancellation(user_id=user_id, application_id=app.pk, reason="Changed mind")
    # Reject cancellation
    process_cancellation_decision(reviewer_user_id=201, application_id=cancel_app.pk, decision="rejected")
    app.refresh_from_db()
    cancel_app.refresh_from_db()
    assert app.status == "approved"
    assert cancel_app.status == "rejected"
    bal.refresh_from_db()
    assert bal.cl_balance == Decimal("6.0")  # unchanged


@pytest.mark.django_db
def test_vacation_leave_academic_calendar_validation():
    from modules.leave.models import VacationPeriod
    from core.api.exceptions import BadRequestError
    user_id = 130
    LeaveBalance.objects.create(user_id=user_id, year=2026, vl_balance=Decimal("60.0"), is_faculty=True)

    VacationPeriod.objects.create(
        name="Summer Vacation",
        year=2026,
        start_date=datetime.date(2026, 6, 1),
        end_date=datetime.date(2026, 6, 30),
        is_active=True,
    )

    # Outside vacation period -> rejected
    with pytest.raises(BadRequestError) as exc:
        apply_for_leave(
            user_id=user_id,
            category="VL",
            start_date=datetime.date(2026, 5, 10),
            end_date=datetime.date(2026, 5, 15),
            purpose="Summer research",
            is_faculty=True,
        )
    assert "vacation period" in str(exc.value).lower()

    # Inside vacation period -> succeeds
    app = apply_for_leave(
        user_id=user_id,
        category="VL",
        start_date=datetime.date(2026, 6, 10),
        end_date=datetime.date(2026, 6, 15),
        purpose="Summer research",
        is_faculty=True,
    )
    assert app.category == "VL"
    assert app.days_count == Decimal("6.0")


@pytest.mark.django_db
def test_faculty_vl_to_el_fractional_year_end_conversion(stub_iam, user_ref):
    faculty_id = 140
    stub_iam(users={faculty_id: user_ref(faculty_id, name="Prof Raman", kind="faculty")})
    # Faculty with 15 remaining VL (converts 2:1 to 7.5 EL)
    LeaveBalance.objects.create(
        user_id=faculty_id,
        year=2026,
        is_faculty=True,
        cl_balance=Decimal("3.0"),
        rh_balance=Decimal("1.0"),
        scl_balance=Decimal("5.0"),
        vl_balance=Decimal("15.0"),
        el_balance=Decimal("10.0"),
        col_balance=Decimal("20.0"),
    )

    run_year_end_processing(2026)

    next_bal = LeaveBalance.objects.get(user_id=faculty_id, year=2027)
    # CL, RH, SCL lapsed to 0, next year reset to annual grant
    assert next_bal.cl_balance == Decimal("8.0")
    assert next_bal.rh_balance == Decimal("2.0")
    assert next_bal.scl_balance == Decimal("15.0")
    # VL converted: 15 / 2 = 7.5. Carried EL: 10 + 7.5 = 17.5
    assert next_bal.el_balance == Decimal("17.5")
    assert next_bal.col_balance == Decimal("40.0")  # 20 carried + 20 grant


@pytest.mark.django_db
def test_offline_leave_recording(stub_iam, user_ref):
    from modules.leave.services import record_offline_leave
    emp_id = 150
    admin_id = 999
    stub_iam(users={emp_id: user_ref(emp_id, name="Dr. Mehta", kind="faculty")})
    LeaveBalance.objects.create(user_id=emp_id, year=2026, cl_balance=Decimal("8.0"), is_faculty=True)

    app = record_offline_leave(
        admin_user_id=admin_id,
        employee_user_id=emp_id,
        category="CL",
        start_date=datetime.date(2026, 11, 2),
        end_date=datetime.date(2026, 11, 3),
        days_count=Decimal("2.0"),
        offline_reference_no="ESTT/2026/042",
        offline_sanction_date=datetime.date(2026, 11, 1),
        purpose="Medical emergency recorded offline",
    )
    assert app.status == "approved"
    assert app.is_offline_sanctioned is True
    assert app.offline_reference_no == "ESTT/2026/042"

    bal = LeaveBalance.objects.get(user_id=emp_id, year=2026)
    assert bal.cl_balance == Decimal("6.0")


@pytest.mark.django_db
def test_sla_reminder_and_escalation():
    from modules.leave.services import process_sla_thresholds
    from modules.leave.models import LeavePolicyConfig
    from django.utils import timezone
    LeavePolicyConfig.objects.create(key="sla.reminder_hours", value={"hours": 24})
    LeavePolicyConfig.objects.create(key="sla.escalation_hours", value={"hours": 48})
    LeavePolicyConfig.objects.create(key="sla.escalation_user_id", value={"user_id": 900})

    user_id = 160
    LeaveBalance.objects.create(user_id=user_id, year=2026, cl_balance=Decimal("8.0"))
    app = apply_for_leave(
        user_id=user_id,
        category="CL",
        start_date=datetime.date(2026, 11, 2),
        end_date=datetime.date(2026, 11, 3),
        purpose="Pending review test",
        unit_head_user_id=201,
    )
    # Simulate time passing beyond reminder threshold (30 hours)
    past_time = timezone.now() + datetime.timedelta(hours=30)
    res = process_sla_thresholds(now=past_time)
    assert res["reminders"] >= 1

    # Simulate time passing beyond escalation threshold (60 hours)
    past_escalate = timezone.now() + datetime.timedelta(hours=60)
    res2 = process_sla_thresholds(now=past_escalate)
    assert res2["escalations"] >= 1
