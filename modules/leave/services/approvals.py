"""Review and approval services for Unit Head, Establishment, and Sanctioning Authorities."""

from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError
from modules.leave.domain.entities import LeaveCategory, LeaveStatus, ReviewDecision
from modules.leave.models import LeaveActionLog, LeaveApplication, LeaveBalance


def review_at_unit_head(
    application_id: int,
    principal,
    decision: str,
    remarks: str = "",
) -> LeaveApplication:
    """Unit Head review (EL-UC-003, BR-EL-016, BR-EL-017)."""
    with transaction.atomic():
        try:
            app = LeaveApplication.objects.select_for_update().get(pk=application_id)
        except LeaveApplication.DoesNotExist:
            raise NotFoundError(f"Application #{application_id} not found.") from None

        if app.status != LeaveStatus.AWAITING_UNIT_HEAD.value:
            raise ConflictError(
                f"Application is not in AWAITING_UNIT_HEAD (status: '{app.status}')."
            )

        from_status = app.status
        app.unit_head_user_id = principal.user_id
        app.unit_head_remarks = remarks

        is_unit_head_final = app.leave_type in (LeaveCategory.CL.value, LeaveCategory.RH.value)

        if is_unit_head_final:
            # BR-EL-016: Final authority for CL and RH
            if decision == ReviewDecision.APPROVED.value:
                app.status = LeaveStatus.APPROVED.value
                app.unit_head_recommendation = ReviewDecision.APPROVED.value
                # Deduct balance
                bal = LeaveBalance.objects.select_for_update().get(
                    user_id=app.applicant_user_id,
                    year=app.start_date.year,
                    leave_type=app.leave_type,
                )
                bal.balance -= app.days_count
                bal.availed += app.days_count
                bal.save(update_fields=["balance", "availed", "updated_at"])
            else:
                app.status = LeaveStatus.REJECTED.value
                app.unit_head_recommendation = ReviewDecision.REJECTED.value
        else:
            # BR-EL-017: Unit Head records Recommended or Not Recommended; continues routing!
            if decision not in (
                ReviewDecision.RECOMMENDED.value,
                ReviewDecision.NOT_RECOMMENDED.value,
            ):
                decision = ReviewDecision.RECOMMENDED.value
            app.unit_head_recommendation = decision
            app.status = LeaveStatus.AWAITING_ESTABLISHMENT.value

        app.save(
            update_fields=[
                "unit_head_user_id",
                "unit_head_recommendation",
                "unit_head_remarks",
                "status",
                "updated_at",
            ]
        )

        LeaveActionLog.objects.create(
            application=app,
            actor_user_id=principal.user_id,
            action="UNIT_HEAD_REVIEW",
            from_status=from_status,
            to_status=app.status,
            remarks=f"{decision}: {remarks}".strip(),
        )

        return app


def route_at_establishment(
    application_id: int,
    principal,
    remarks: str = "",
) -> LeaveApplication:
    """Establishment processing and routing step (EL-UC-004)."""
    with transaction.atomic():
        try:
            app = LeaveApplication.objects.select_for_update().get(pk=application_id)
        except LeaveApplication.DoesNotExist:
            raise NotFoundError(f"Application #{application_id} not found.") from None

        if app.status != LeaveStatus.AWAITING_ESTABLISHMENT.value:
            raise ConflictError("Application is not in AWAITING_ESTABLISHMENT.")

        from_status = app.status
        app.establishment_remarks = remarks
        app.status = LeaveStatus.AWAITING_SANCTION.value
        app.save(update_fields=["establishment_remarks", "status", "updated_at"])

        LeaveActionLog.objects.create(
            application=app,
            actor_user_id=principal.user_id,
            action="ESTABLISHMENT_ROUTE",
            from_status=from_status,
            to_status=LeaveStatus.AWAITING_SANCTION.value,
            remarks=remarks or "Verified and routed to Sanctioning Authority",
        )

        return app


def final_sanction(
    application_id: int,
    principal,
    decision: str,
    remarks: str = "",
) -> LeaveApplication:
    """Final sanctioning decision by competent authority (EL-UC-005, BR-EL-018, BR-EL-025)."""
    with transaction.atomic():
        try:
            app = LeaveApplication.objects.select_for_update().get(pk=application_id)
        except LeaveApplication.DoesNotExist:
            raise NotFoundError(f"Application #{application_id} not found.") from None

        if app.status != LeaveStatus.AWAITING_SANCTION.value:
            raise ConflictError("Application is not in AWAITING_SANCTION.")

        from_status = app.status
        app.sanctioning_authority_user_id = principal.user_id
        app.sanction_remarks = remarks

        if decision == ReviewDecision.APPROVED.value:
            app.status = LeaveStatus.APPROVED.value
            app.sanction_decision = ReviewDecision.APPROVED.value
            # Deduct balance
            bal = LeaveBalance.objects.select_for_update().get(
                user_id=app.applicant_user_id,
                year=app.start_date.year,
                leave_type=app.leave_type,
            )
            bal.balance -= app.days_count
            bal.availed += app.days_count
            bal.save(update_fields=["balance", "availed", "updated_at"])

            # BR-EL-025: If this application is an extension, update parent leave
            if app.parent_leave_id:
                try:
                    parent = LeaveApplication.objects.select_for_update().get(
                        pk=app.parent_leave_id
                    )
                    parent.end_date = app.end_date
                    parent.days_count += app.days_count
                    parent.save(update_fields=["end_date", "days_count", "updated_at"])
                except LeaveApplication.DoesNotExist:
                    pass
        else:
            app.status = LeaveStatus.REJECTED.value
            app.sanction_decision = ReviewDecision.REJECTED.value

        app.save(
            update_fields=[
                "sanctioning_authority_user_id",
                "sanction_decision",
                "sanction_remarks",
                "status",
                "updated_at",
            ]
        )

        LeaveActionLog.objects.create(
            application=app,
            actor_user_id=principal.user_id,
            action="FINAL_SANCTION",
            from_status=from_status,
            to_status=app.status,
            remarks=f"{decision}: {remarks}".strip(),
        )

        return app
