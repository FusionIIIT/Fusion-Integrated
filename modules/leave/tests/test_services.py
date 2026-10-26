"""Integration tests for leave services and workflow lifecycles."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from fusion_auth.principal import Principal
from modules.leave.models import (
    LeaveApplication,
    LeaveBalance,
    LeaveHierarchyConfig,
)
from modules.leave.services import (
    applications as app_services,
)
from modules.leave.services import (
    approvals as approval_services,
)
from modules.leave.services import (
    balances as balance_services,
)
from modules.leave.services import (
    cancellations as cancellation_services,
)
from modules.leave.services import (
    extensions as extension_services,
)
from modules.leave.services import (
    offline as offline_services,
)
from modules.leave.services import (
    resumptions as resumption_services,
)
from modules.leave.services import (
    substitutes as substitute_services,
)
from modules.leave.services import (
    yearend as yearend_services,
)


def make_principal(user_id=1001, username="testuser", kind="staff", role="staff"):
    return Principal(
        user_id=user_id,
        username=username,
        display_name=f"User {user_id}",
        kind=kind,
        active_role=role,
        roles=(role,),
        permissions=frozenset(
            [
                "leave.request.create",
                "leave.request.view_self",
                "leave.request.delete",
                "leave.request.substitute",
                "leave.request.view",
                "leave.request.approve",
                "leave.balance.update",
                "leave.type.manage",
                "leave.calendar.view",
                "leave.offline.record",
            ]
        ),
        modules=("leave",),
    )


@pytest.mark.django_db
def test_new_cl_without_substitute_workflow_bw_el_01():
    """BW-EL-01: CL applied -> Unit Head approves -> Approved & balance deducted."""
    applicant = make_principal(user_id=101, kind="staff")
    unit_head = make_principal(user_id=201, role="HOD")

    balance_services.ensure_user_balances_initialized(101, 2026, "staff")
    init_bal = LeaveBalance.objects.get(user_id=101, year=2026, leave_type="CL").balance

    app = app_services.submit_application(
        principal=applicant,
        data={
            "leave_type": "CL",
            "start_date": date(2026, 10, 5),
            "end_date": date(2026, 10, 6),
            "reason": "Family function",
        },
    )
    assert app.status == "AWAITING_UNIT_HEAD"
    assert app.days_count == Decimal("2.0")

    app_approved = approval_services.review_at_unit_head(
        application_id=app.pk,
        principal=unit_head,
        decision="APPROVED",
        remarks="Approved by HOD",
    )
    assert app_approved.status == "APPROVED"

    new_bal = LeaveBalance.objects.get(user_id=101, year=2026, leave_type="CL").balance
    assert new_bal == init_bal - Decimal("2.0")


@pytest.mark.django_db
def test_substitute_flow_and_decline_replacement_bw_el_03():
    """BW-EL-03: Substitute declines -> replacement nominated -> replacement accepts -> Unit Head approves."""
    applicant = make_principal(user_id=102, kind="staff")
    sub1 = make_principal(user_id=301, kind="staff")
    sub2 = make_principal(user_id=302, kind="staff")
    unit_head = make_principal(user_id=201, role="HOD")

    balance_services.ensure_user_balances_initialized(102, 2026, "staff")

    app = app_services.submit_application(
        principal=applicant,
        data={
            "leave_type": "CL",
            "start_date": date(2026, 10, 12),
            "end_date": date(2026, 10, 12),
            "reason": "Personal work",
            "substitute_user_id": 301,
        },
    )
    assert app.status == "AWAITING_SUBSTITUTE"

    app_declined = substitute_services.respond_substitute(
        app.pk, sub1, accept=False, remarks="Busy"
    )
    assert app_declined.status == "SUBSTITUTE_DECLINED"

    app_replaced = substitute_services.replace_substitute(app.pk, applicant, new_substitute_id=302)
    assert app_replaced.status == "AWAITING_SUBSTITUTE"
    assert app_replaced.substitute_user_id == 302

    app_accepted = substitute_services.respond_substitute(
        app.pk, sub2, accept=True, remarks="Will cover"
    )
    assert app_accepted.status == "AWAITING_UNIT_HEAD"

    final_app = approval_services.review_at_unit_head(app.pk, unit_head, decision="APPROVED")
    assert final_app.status == "APPROVED"


@pytest.mark.django_db
def test_director_self_sanction_with_substitute_bw_el_08():
    """BW-EL-08: Director applies with substitute -> substitute accepts -> self-sanction approved immediately."""
    director_id = 900
    director = make_principal(user_id=director_id, role="Director")
    substitute = make_principal(user_id=305, kind="faculty")

    LeaveHierarchyConfig.objects.create(
        department="Administration",
        unit_head_user_id=800,
        director_user_id=director_id,
    )

    balance_services.ensure_user_balances_initialized(director_id, 2026, "faculty")
    init_bal = LeaveBalance.objects.get(user_id=director_id, year=2026, leave_type="CL").balance

    app = app_services.submit_application(
        principal=director,
        data={
            "leave_type": "CL",
            "start_date": date(2026, 10, 19),
            "end_date": date(2026, 10, 20),
            "reason": "Official academic conference",
            "substitute_user_id": 305,
        },
    )
    assert app.status == "AWAITING_SUBSTITUTE"

    # Substitute accepts
    app_accepted = substitute_services.respond_substitute(
        app.pk, substitute, accept=True, remarks="Coverage confirmed"
    )
    # Directly approved without Unit Head!
    assert app_accepted.status == "APPROVED"

    new_bal = LeaveBalance.objects.get(user_id=director_id, year=2026, leave_type="CL").balance
    assert new_bal == init_bal - Decimal("2.0")


@pytest.mark.django_db
def test_higher_sanction_flow_bw_el_04():
    """BW-EL-04: EL -> Unit Head recommends -> Establishment routes -> Final sanction."""
    applicant = make_principal(user_id=103, kind="staff")
    unit_head = make_principal(user_id=201, role="HOD")
    estt = make_principal(user_id=202, role="dr_establishment")
    director = make_principal(user_id=203, role="Director")

    balance_services.ensure_user_balances_initialized(103, 2026, "staff")

    app = app_services.submit_application(
        principal=applicant,
        data={
            "leave_type": "EL",
            "start_date": date(2026, 10, 5),
            "end_date": date(2026, 10, 9),
            "reason": "Annual leave",
        },
    )
    assert app.status == "AWAITING_UNIT_HEAD"

    app = approval_services.review_at_unit_head(app.pk, unit_head, decision="RECOMMENDED")
    assert app.status == "AWAITING_ESTABLISHMENT"

    app = approval_services.route_at_establishment(app.pk, estt, remarks="Service verified")
    assert app.status == "AWAITING_SANCTION"

    app = approval_services.final_sanction(
        app.pk, director, decision="APPROVED", remarks="Sanctioned"
    )
    assert app.status == "APPROVED"


@pytest.mark.django_db
def test_extension_approval_syncs_parent_leave_bw_el_12():
    """BR-EL-025: Approving an extension updates the parent leave end_date and total days."""
    applicant = make_principal(user_id=107, kind="staff")
    director = make_principal(user_id=203, role="Director")

    balance_services.ensure_user_balances_initialized(107, 2026, "staff")

    parent = LeaveApplication.objects.create(
        applicant_user_id=107,
        leave_type="EL",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=4),
        days_count=Decimal("5.0"),
        reason="Initial medical recuperation",
        status="APPROVED",
    )
    bal = LeaveBalance.objects.get(user_id=107, year=date.today().year, leave_type="EL")
    bal.balance -= Decimal("5.0")
    bal.availed += Decimal("5.0")
    bal.save()

    # Request 3 more days
    ext_end = parent.end_date + timedelta(days=3)
    ext_app = extension_services.request_extension(
        parent_application_id=parent.pk,
        principal=applicant,
        new_end_date=ext_end,
        reason="Further recuperation advised",
    )
    ext_app.status = "AWAITING_SANCTION"
    ext_app.save(update_fields=["status"])

    # Final sanction approves extension
    approval_services.final_sanction(ext_app.pk, director, decision="APPROVED", remarks="Granted")
    ext_app.refresh_from_db()
    assert ext_app.status == "APPROVED"

    # Parent leave end date is updated to ext_end and days_count increased!
    parent.refresh_from_db()
    assert parent.end_date == ext_end
    assert parent.days_count == Decimal("8.0")


@pytest.mark.django_db
def test_cancellation_and_balance_restoration_cw_el_02():
    """CW-EL-02: Approved leave cancellation restores deducted balance."""
    applicant = make_principal(user_id=104, kind="staff")
    unit_head = make_principal(user_id=201, role="HOD")

    balance_services.ensure_user_balances_initialized(104, 2026, "staff")
    init_bal = LeaveBalance.objects.get(user_id=104, year=2026, leave_type="CL").balance

    future_start = date.today() + timedelta(days=10)
    future_end = future_start + timedelta(days=1)

    app = app_services.submit_application(
        principal=applicant,
        data={
            "leave_type": "CL",
            "start_date": future_start,
            "end_date": future_end,
            "reason": "Future trip",
        },
    )
    approval_services.review_at_unit_head(app.pk, unit_head, decision="APPROVED")

    bal_after_approval = LeaveBalance.objects.get(user_id=104, year=2026, leave_type="CL").balance
    assert bal_after_approval < init_bal

    cancellation_services.request_cancellation(app.pk, applicant, reason="Trip cancelled")
    app.refresh_from_db()
    assert app.status == "AWAITING_CANCELLATION"

    cancellation_services.review_cancellation(app.pk, unit_head, decision="APPROVED")
    app.refresh_from_db()
    assert app.status == "CANCELLED"

    bal_after_cancel = LeaveBalance.objects.get(user_id=104, year=2026, leave_type="CL").balance
    assert bal_after_cancel == init_bal


@pytest.mark.django_db
def test_resumption_review_cw_el_04():
    """CW-EL-04: Early resumption refunds balance difference."""
    applicant = make_principal(user_id=105, kind="staff")
    sanction_auth = make_principal(user_id=203, role="Director")

    balance_services.ensure_user_balances_initialized(105, 2026, "staff")

    app = LeaveApplication.objects.create(
        applicant_user_id=105,
        leave_type="EL",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 10),
        days_count=Decimal("10.0"),
        reason="Medical recuperation",
        status="APPROVED",
    )
    bal = LeaveBalance.objects.get(user_id=105, year=2026, leave_type="EL")
    bal.balance -= Decimal("10.0")
    bal.availed += Decimal("10.0")
    bal.save()

    resumption_services.submit_resumption(
        app.pk, applicant, actual_resumption_date=date(2026, 10, 8)
    )
    app.refresh_from_db()
    assert app.resumption_status == "SUBMITTED"

    resumption_services.review_resumption(app.pk, sanction_auth)
    app.refresh_from_db()
    assert app.resumption_status == "REVIEWED"
    assert app.resumption_days_adjusted == Decimal("-2.0")

    bal.refresh_from_db()
    assert bal.balance == Decimal("22.0")


@pytest.mark.django_db
def test_retrospective_offline_leave_el_uc_016():
    """EL-UC-016: Offline leave recorded with sanction reference and balance synchronized."""
    admin = make_principal(user_id=999, role="admin")

    app = offline_services.record_offline_leave(
        admin_principal=admin,
        applicant_user_id=106,
        applicant_kind="staff",
        leave_type="CL",
        start_date=date(2026, 10, 5),
        end_date=date(2026, 10, 5),
        reason="Medical emergency offline approved",
        sanction_ref="ESTT/2026/OFF/001",
        sanction_date=date(2026, 10, 4),
        sanctioned_by="Registrar",
    )
    assert app.status == "APPROVED"
    assert app.is_offline is True
    assert app.offline_sanction_ref == "ESTT/2026/OFF/001"

    bal = LeaveBalance.objects.get(user_id=106, year=2026, leave_type="CL")
    assert bal.availed == Decimal("1.0")
    assert bal.balance == Decimal("7.0")


@pytest.mark.django_db
def test_year_end_processing_el_uc_020():
    """EL-UC-020: Year-end processing lapsing CL/RH and converting Faculty VL 2:1 to EL."""
    LeaveBalance.objects.create(
        user_id=2001,
        year=2026,
        leave_type="VL",
        credited=Decimal("60.0"),
        availed=Decimal("20.0"),
        balance=Decimal("40.0"),
    )
    LeaveBalance.objects.create(
        user_id=2001,
        year=2026,
        leave_type="CL",
        credited=Decimal("8.0"),
        availed=Decimal("3.0"),
        balance=Decimal("5.0"),
    )

    res = yearend_services.execute_year_end_processing(2026)
    assert res["employees_processed"] >= 1

    cl_2027 = LeaveBalance.objects.get(user_id=2001, year=2027, leave_type="CL")
    assert cl_2027.balance == Decimal("8.0")

    el_2027 = LeaveBalance.objects.get(user_id=2001, year=2027, leave_type="EL")
    assert el_2027.balance == Decimal("20.0")
