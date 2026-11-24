"""Atomic leave submission, substitute consent, review, sanction, and lifecycle services."""

from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from modules.elm.domain.policy import (
    calculate_resumption_delta,
    convert_vl_to_el,
    count_days,
    eligible,
    is_director,
    overlaps,
    remaining,
    requires_higher_sanction,
)
from modules.elm.models import (
    EmployeeLeaveProfile,
    Holiday,
    LeaveAccountTransaction,
    LeaveApplication,
    LeaveBalance,
    LeaveEvent,
    LeaveNotification,
    SlaConfig,
)
from modules.elm.selectors.queries import get_published_dates


def log_event(
    application: LeaveApplication, actor_id: int, action: str, detail: str = ""
) -> LeaveEvent:
    return LeaveEvent.objects.create(
        application=application, actor_id=actor_id, action=action, detail=detail
    )


def create_notification(
    recipient_id: int,
    application: LeaveApplication | None,
    topic: str,
    message: str,
    is_reminder: bool = False,
    is_escalation: bool = False,
) -> LeaveNotification:
    return LeaveNotification.objects.create(
        recipient_id=recipient_id,
        application=application,
        topic=topic,
        message=message,
        is_reminder=is_reminder,
        is_escalation=is_escalation,
    )


def record_transaction(
    employee_id: int,
    year: int,
    category: str,
    transaction_type: str,
    amount: Decimal,
    balance_after: Decimal,
    reference: str = "",
) -> LeaveAccountTransaction:
    return LeaveAccountTransaction.objects.create(
        employee_id=employee_id,
        year=year,
        category=category,
        transaction_type=transaction_type,
        amount=amount,
        balance_after=balance_after,
        reference=reference,
    )


def _balance_for_update(employee_id: int, year: int, category: str) -> LeaveBalance:
    return get_object_or_404(
        LeaveBalance.objects.select_for_update(),
        employee_id=employee_id,
        year=year,
        category=category,
    )


def _validate_substitute_eligibility(
    applicant_id: int,
    substitute_user_id: int | None,
    start: date,
    end: date,
    exclude_app_id: int | None = None,
) -> None:
    if not substitute_user_id:
        return
    if substitute_user_id == applicant_id:
        raise ValidationError({"substitute_user_id": "Applicant cannot be their own substitute."})
    if not EmployeeLeaveProfile.objects.filter(user_id=substitute_user_id).exists():
        raise ValidationError(
            {"substitute_user_id": "Nominated substitute must be an institute employee."}
        )

    query = LeaveApplication.objects.filter(
        employee_id=substitute_user_id,
        status__in=(
            "AWAITING_SUB",
            "PENDING",
            "AWAITING_ESTABLISHMENT",
            "RECOMMENDED",
            "AWAITING_DIRECTOR",
            "APPROVED",
            "CANCELLATION_PENDING",
            "CANCELLATION_ESTABLISHMENT",
            "CANCELLATION_SANCTION",
            "EXTENSION_AWAITING_SUB",
            "EXTENSION_PENDING",
            "EXTENSION_ESTABLISHMENT",
            "EXTENSION_SANCTION",
            "RESUMPTION_PENDING",
        ),
        start_date__lte=end,
        end_date__gte=start,
    )
    if exclude_app_id:
        query = query.exclude(pk=exclude_app_id)
    if query.exists():
        raise ValidationError(
            {
                "substitute_user_id": (
                    "Substitute has overlapping leave during the responsibility period."
                )
            }
        )


@transaction.atomic
def submit(principal, data: dict) -> LeaveApplication:
    profile = get_object_or_404(EmployeeLeaveProfile, user_id=principal.user_id)
    category, start, end = data["category"], data["start_date"], data["end_date"]
    half_day = data.get("half_day", "NONE")
    substitute_user_id = data.get("substitute_user_id")
    applicant_is_director = is_director(profile.designation)

    if not eligible(category, profile.category):
        raise ValidationError({"category": "Leave type is not eligible for this employee."})
    if start.year != end.year:
        raise ValidationError({"end_date": "Leave interval must fall within a single year."})

    if not applicant_is_director:
        if not profile.unit_head_user_id:
            raise ValidationError({"hierarchy": "Leave Unit Head is not configured."})
        if requires_higher_sanction(category) and not profile.sanction_authority_user_id:
            raise ValidationError({"hierarchy": "Final Sanctioning Authority is not configured."})

    if data.get("station_leave") and not data.get("station_location", "").strip():
        raise ValidationError({"station_location": "Station Leave requires a destination."})

    _validate_substitute_eligibility(principal.user_id, substitute_user_id, start, end)

    if category == "VL":
        vacation_dates = get_published_dates(start, end, "VACATION")
        expected_days = (end - start).days + 1
        if len(vacation_dates) != expected_days:
            raise ValidationError(
                {"category": "Vacation leave requires published vacation calendar dates."}
            )
    if category == "RH" and (
        start != end or not Holiday.objects.filter(date=start, kind="RH", published=True).exists()
    ):
        raise ValidationError({"start_date": "Choose a published restricted holiday."})

    closed = get_published_dates(start, end, "CLOSED")
    try:
        duration = count_days(category, start, end, half_day, closed)
    except ValueError as exc:
        raise ValidationError({"duration": str(exc)}) from exc

    balance = _balance_for_update(principal.user_id, start.year, category)
    try:
        remaining(balance.allotted, balance.used, duration)
    except ValueError as exc:
        raise ValidationError({"balance": str(exc)}) from exc

    for existing in LeaveApplication.objects.select_for_update().filter(
        employee_id=principal.user_id,
        status__in=(
            "AWAITING_SUB",
            "ACTION_REQUIRED",
            "PENDING",
            "AWAITING_ESTABLISHMENT",
            "RECOMMENDED",
            "AWAITING_DIRECTOR",
            "APPROVED",
            "CANCELLATION_PENDING",
            "CANCELLATION_ESTABLISHMENT",
            "CANCELLATION_SANCTION",
            "EXTENSION_AWAITING_SUB",
            "EXTENSION_PENDING",
            "EXTENSION_ESTABLISHMENT",
            "EXTENSION_SANCTION",
            "RESUMPTION_PENDING",
        ),
        start_date__lte=end,
        end_date__gte=start,
    ):
        if overlaps(
            existing.start_date,
            existing.end_date,
            start,
            end,
            existing.half_day,
            half_day,
        ):
            raise ValidationError({"start_date": "An active leave request overlaps these dates."})

    has_sub = bool(substitute_user_id)
    if has_sub:
        initial_status = "AWAITING_SUB"
    elif applicant_is_director:
        initial_status = "AWAITING_DIRECTOR"
    else:
        initial_status = "PENDING"

    application = LeaveApplication.objects.create(
        employee_id=principal.user_id,
        category=category,
        start_date=start,
        end_date=end,
        half_day=half_day,
        duration=duration,
        reason=data["reason"].strip(),
        medical_evidence=data.get("medical_evidence", "").strip(),
        station_leave=data.get("station_leave", False),
        station_location=data.get("station_location", "").strip(),
        substitute_user_id=substitute_user_id,
        substitute_status="PENDING" if has_sub else "NOT_REQUIRED",
        status=initial_status,
        unit_head_id=None if applicant_is_director else profile.unit_head_user_id,
        establishment_id=None if applicant_is_director else profile.establishment_user_id,
        sanction_authority_id=principal.user_id
        if applicant_is_director
        else profile.sanction_authority_user_id,
    )
    log_event(application, principal.user_id, "submitted")

    if has_sub:
        create_notification(
            substitute_user_id,
            application,
            "substitute.assigned",
            f"You have been nominated as substitute by employee {principal.user_id} "
            f"for leave from {start} to {end}.",
        )
    elif applicant_is_director:
        create_notification(
            principal.user_id,
            application,
            "task.assigned",
            f"Director leave application #{application.id} is pending self-sanction.",
        )
    else:
        create_notification(
            profile.unit_head_user_id,
            application,
            "task.assigned",
            f"New leave application #{application.id} from employee {principal.user_id} "
            f"is awaiting your review.",
        )

    return application


@transaction.atomic
def nominate_replacement_substitute(
    principal, pk: int, replacement_substitute_user_id: int
) -> LeaveApplication:
    application = get_object_or_404(
        LeaveApplication.objects.select_for_update(), pk=pk, employee_id=principal.user_id
    )
    if application.status not in ("ACTION_REQUIRED", "EXTENSION_ACTION_REQUIRED"):
        raise ValidationError(
            {"status": "Substitute replacement is only permitted after substitute decline."}
        )

    _validate_substitute_eligibility(
        principal.user_id,
        replacement_substitute_user_id,
        application.start_date,
        application.end_date,
        exclude_app_id=application.id,
    )

    is_ext = application.status == "EXTENSION_ACTION_REQUIRED"
    application.substitute_user_id = replacement_substitute_user_id
    application.substitute_status = "PENDING"
    application.status = "EXTENSION_AWAITING_SUB" if is_ext else "AWAITING_SUB"
    application.save(
        update_fields=["substitute_user_id", "substitute_status", "status", "updated_at"]
    )

    log_event(
        application,
        principal.user_id,
        "replacement_substitute_nominated",
        f"New substitute {replacement_substitute_user_id}",
    )
    create_notification(
        replacement_substitute_user_id,
        application,
        "substitute.assigned",
        f"You have been nominated as replacement substitute by employee {principal.user_id}.",
    )
    return application


@transaction.atomic
def decide(principal, pk: int, *, action: str, remarks: str = "") -> LeaveApplication:
    application = get_object_or_404(LeaveApplication.objects.select_for_update(), pk=pk)
    applicant_profile = get_object_or_404(EmployeeLeaveProfile, user_id=application.employee_id)
    applicant_is_director = is_director(applicant_profile.designation)

    # 1. Substitute consent gate
    if application.status in ("AWAITING_SUB", "EXTENSION_AWAITING_SUB"):
        if principal.user_id != application.substitute_user_id:
            raise PermissionDenied("Only the nominated substitute can respond now.")
        if action not in ("accept_substitute", "decline_substitute"):
            raise ValidationError({"action": "Substitute must accept or decline."})

        accepted = action == "accept_substitute"
        is_ext = application.status == "EXTENSION_AWAITING_SUB"
        application.substitute_status = "ACCEPTED" if accepted else "DECLINED"

        if accepted:
            if applicant_is_director:
                application.status = "AWAITING_DIRECTOR"
                create_notification(
                    application.employee_id,
                    application,
                    "task.assigned",
                    f"Substitute accepted. Director application #{application.id} "
                    f"is ready for self-sanction.",
                )
            else:
                application.status = "EXTENSION_PENDING" if is_ext else "PENDING"
                if application.unit_head_id:
                    create_notification(
                        application.unit_head_id,
                        application,
                        "task.assigned",
                        f"Substitute accepted. Leave application #{application.id} "
                        f"is awaiting your review.",
                    )
        else:
            application.status = "EXTENSION_ACTION_REQUIRED" if is_ext else "ACTION_REQUIRED"
            create_notification(
                application.employee_id,
                application,
                "substitute.declined",
                f"Your nominated substitute declined leave request #{application.id}. "
                f"Please nominate a replacement or withdraw.",
            )

        application.save(update_fields=["substitute_status", "status", "updated_at"])
        log_event(application, principal.user_id, action, remarks)
        return application

    # 2. Director Self-Sanction
    if application.status == "AWAITING_DIRECTOR":
        if principal.user_id != application.employee_id or not applicant_is_director:
            raise PermissionDenied("Only the Director can self-sanction this application.")
        if action not in ("approve", "reject"):
            raise ValidationError(
                {"action": "Director self-sanction action must be approve or reject."}
            )

        if action == "approve":
            balance = _balance_for_update(
                application.employee_id, application.start_date.year, application.category
            )
            remaining(balance.allotted, balance.used, application.duration)
            balance.used += application.duration
            balance.save(update_fields=["used"])
            record_transaction(
                application.employee_id,
                application.start_date.year,
                application.category,
                "DEBIT",
                application.duration,
                balance.allotted - balance.used,
                reference=f"LeaveApplication #{application.id} Director Self-Sanction",
            )
            application.status = "APPROVED"
        else:
            application.status = "REJECTED"

        application.approver_id = principal.user_id
        application.decision_remarks = remarks
        application.decided_at = timezone.now()
        application.save(
            update_fields=["status", "approver_id", "decision_remarks", "decided_at", "updated_at"]
        )
        log_event(application, principal.user_id, f"director_{action}", remarks)
        create_notification(
            application.employee_id,
            application,
            "decision.recorded",
            f"Director self-sanction recorded: {application.status} "
            f"for application #{application.id}.",
        )
        return application

    # For non-director cases, applicant cannot decide own request
    if application.employee_id == principal.user_id:
        raise PermissionDenied("The applicant cannot decide their own leave.")

    # 3. Unit Head Review on new leave (PENDING)
    if application.status == "PENDING":
        if principal.user_id != application.unit_head_id:
            raise PermissionDenied("Only the assigned Unit Head can act now.")

        if requires_higher_sanction(application.category):
            if action not in ("recommend", "not_recommend"):
                raise ValidationError(
                    {
                        "action": (
                            "Unit Head must recommend or not recommend for higher sanction leave."
                        )
                    }
                )
            application.recommendation = (
                "RECOMMENDED" if action == "recommend" else "NOT_RECOMMENDED"
            )
            if application.establishment_id:
                application.status = "AWAITING_ESTABLISHMENT"
                create_notification(
                    application.establishment_id,
                    application,
                    "task.assigned",
                    f"Leave application #{application.id} recommended by Unit Head; "
                    f"establishment routing pending.",
                )
            else:
                application.status = "RECOMMENDED"
                if application.sanction_authority_id:
                    create_notification(
                        application.sanction_authority_id,
                        application,
                        "task.assigned",
                        f"Leave application #{application.id} is awaiting your final "
                        f"sanction decision.",
                    )
            application.save(update_fields=["recommendation", "status", "updated_at"])
            log_event(application, principal.user_id, action, remarks)
            return application
        if action not in ("approve", "reject"):
            raise ValidationError(
                {"action": "Unit Head final action must be approve or reject for CL/RH."}
            )
        if action == "approve":
            balance = _balance_for_update(
                application.employee_id, application.start_date.year, application.category
            )
            remaining(balance.allotted, balance.used, application.duration)
            balance.used += application.duration
            balance.save(update_fields=["used"])
            record_transaction(
                application.employee_id,
                application.start_date.year,
                application.category,
                "DEBIT",
                application.duration,
                balance.allotted - balance.used,
                reference=f"LeaveApplication #{application.id} Unit Head Approved",
            )
        application.status = "APPROVED" if action == "approve" else "REJECTED"
        application.approver_id = principal.user_id
        application.decision_remarks = remarks
        application.decided_at = timezone.now()
        application.save(
            update_fields=[
                "status",
                "approver_id",
                "decision_remarks",
                "decided_at",
                "updated_at",
            ]
        )
        log_event(application, principal.user_id, action, remarks)
        create_notification(
            application.employee_id,
            application,
            "decision.recorded",
            f"Your leave application #{application.id} was "
            f"{application.status.lower()} by Unit Head.",
        )
        return application

    # 4. Optional Establishment Routing (EL-UC-004)
    if application.status in (
        "AWAITING_ESTABLISHMENT",
        "EXTENSION_ESTABLISHMENT",
        "CANCELLATION_ESTABLISHMENT",
    ):
        if application.establishment_id and principal.user_id != application.establishment_id:
            raise PermissionDenied("Only the assigned Establishment officer can verify and route.")
        if action not in ("verify_and_route", "forward_to_sanction"):
            raise ValidationError(
                {"action": "Establishment action must be verify_and_route or forward_to_sanction."}
            )

        if application.status == "AWAITING_ESTABLISHMENT":
            application.status = "RECOMMENDED"
        elif application.status == "EXTENSION_ESTABLISHMENT":
            application.status = "EXTENSION_SANCTION"
        else:
            application.status = "CANCELLATION_SANCTION"

        application.save(update_fields=["status", "updated_at"])
        log_event(application, principal.user_id, "establishment_routed", remarks)
        if application.sanction_authority_id:
            create_notification(
                application.sanction_authority_id,
                application,
                "task.assigned",
                f"Leave application #{application.id} forwarded by Establishment "
                f"for sanction decision.",
            )
        return application

    # 5. Higher Sanction Decision on new leave (RECOMMENDED)
    if application.status == "RECOMMENDED":
        if principal.user_id != application.sanction_authority_id:
            raise PermissionDenied("Only the assigned Sanctioning Authority can act now.")
        if action not in ("approve", "reject"):
            raise ValidationError({"action": "Final action must be approve or reject."})

        if action == "approve":
            balance = _balance_for_update(
                application.employee_id, application.start_date.year, application.category
            )
            remaining(balance.allotted, balance.used, application.duration)
            balance.used += application.duration
            balance.save(update_fields=["used"])
            record_transaction(
                application.employee_id,
                application.start_date.year,
                application.category,
                "DEBIT",
                application.duration,
                balance.allotted - balance.used,
                reference=f"LeaveApplication #{application.id} Sanction Authority Approved",
            )
        application.status = "APPROVED" if action == "approve" else "REJECTED"
        application.approver_id = principal.user_id
        application.decision_remarks = remarks
        application.decided_at = timezone.now()
        application.save(
            update_fields=["status", "approver_id", "decision_remarks", "decided_at", "updated_at"]
        )
        log_event(application, principal.user_id, action, remarks)
        create_notification(
            application.employee_id,
            application,
            "decision.recorded",
            f"Your leave application #{application.id} was "
            f"{application.status.lower()} by Sanction Authority.",
        )
        return application

    # 6. Cancellation Review and Sanction (CW-EL-02, BW-EL-10, BW-EL-11)
    if application.status == "CANCELLATION_PENDING":
        if principal.user_id != application.unit_head_id:
            raise PermissionDenied(
                "Only the assigned Unit Head can review this cancellation request."
            )

        if not requires_higher_sanction(application.category):
            # CL/RH: Unit Head final decision for cancellation
            if action not in ("approve_cancellation", "reject_cancellation"):
                raise ValidationError(
                    {"action": "Action must be approve_cancellation or reject_cancellation."}
                )
            if action == "approve_cancellation":
                balance = _balance_for_update(
                    application.employee_id, application.start_date.year, application.category
                )
                balance.used = max(Decimal("0"), balance.used - application.duration)
                balance.save(update_fields=["used"])
                record_transaction(
                    application.employee_id,
                    application.start_date.year,
                    application.category,
                    "CREDIT",
                    application.duration,
                    balance.allotted - balance.used,
                    reference=f"LeaveApplication #{application.id} Cancellation Approved",
                )
                application.status = "CANCELLED"
            else:
                application.status = "APPROVED"  # Rejection preserves original approved leave

            application.decision_remarks = remarks
            application.save(update_fields=["status", "decision_remarks", "updated_at"])
            log_event(application, principal.user_id, action, remarks)
            create_notification(
                application.employee_id,
                application,
                "cancellation.decision",
                f"Cancellation request for leave #{application.id} was "
                f"{application.status.lower()}.",
            )
            return application
        # SCL/EL/COL/VL: Unit Head recommendation for cancellation
        if action not in ("recommend_cancellation", "not_recommend_cancellation"):
            raise ValidationError(
                {"action": "Action must be recommend_cancellation or not_recommend_cancellation."}
            )
        application.recommendation = (
            "RECOMMENDED" if action == "recommend_cancellation" else "NOT_RECOMMENDED"
        )
        if application.establishment_id:
            application.status = "CANCELLATION_ESTABLISHMENT"
        else:
            application.status = "CANCELLATION_SANCTION"
        application.save(update_fields=["recommendation", "status", "updated_at"])
        log_event(application, principal.user_id, action, remarks)
        if application.sanction_authority_id:
            create_notification(
                application.sanction_authority_id,
                application,
                "task.assigned",
                f"Cancellation request for leave #{application.id} is awaiting "
                f"your sanction decision.",
            )
        return application

    if application.status == "CANCELLATION_SANCTION":
        if principal.user_id != application.sanction_authority_id:
            raise PermissionDenied(
                "Only the assigned Sanctioning Authority can decide on this cancellation."
            )
        if action not in ("approve_cancellation", "reject_cancellation"):
            raise ValidationError(
                {"action": "Action must be approve_cancellation or reject_cancellation."}
            )

        if action == "approve_cancellation":
            balance = _balance_for_update(
                application.employee_id, application.start_date.year, application.category
            )
            balance.used = max(Decimal("0"), balance.used - application.duration)
            balance.save(update_fields=["used"])
            record_transaction(
                application.employee_id,
                application.start_date.year,
                application.category,
                "CREDIT",
                application.duration,
                balance.allotted - balance.used,
                reference=f"LeaveApplication #{application.id} Cancellation Approved",
            )
            application.status = "CANCELLED"
        else:
            application.status = "APPROVED"  # original approved leave preserved

        application.decision_remarks = remarks
        application.save(update_fields=["status", "decision_remarks", "updated_at"])
        log_event(application, principal.user_id, action, remarks)
        create_notification(
            application.employee_id,
            application,
            "cancellation.decision",
            f"Cancellation request for leave #{application.id} was {application.status.lower()}.",
        )
        return application

    # 7. Extension Review and Sanction (CW-EL-03, BW-EL-12..14)
    if application.status == "EXTENSION_PENDING":
        if principal.user_id != application.unit_head_id:
            raise PermissionDenied("Only the assigned Unit Head can review this extension request.")
        if action not in ("recommend", "not_recommend"):
            raise ValidationError(
                {"action": "Unit Head must recommend or not recommend the extension."}
            )
        application.recommendation = "RECOMMENDED" if action == "recommend" else "NOT_RECOMMENDED"
        if application.establishment_id:
            application.status = "EXTENSION_ESTABLISHMENT"
        else:
            application.status = "EXTENSION_SANCTION"
        application.save(update_fields=["recommendation", "status", "updated_at"])
        log_event(application, principal.user_id, f"extension_{action}", remarks)
        if application.sanction_authority_id:
            create_notification(
                application.sanction_authority_id,
                application,
                "task.assigned",
                f"Extension request for leave #{application.id} is awaiting your final decision.",
            )
        return application

    if application.status == "EXTENSION_SANCTION":
        if principal.user_id != application.sanction_authority_id:
            raise PermissionDenied(
                "Only the assigned Sanctioning Authority can decide on this extension."
            )
        if action not in ("approve", "reject"):
            raise ValidationError({"action": "Extension decision must be approve or reject."})

        if action == "approve":
            balance = _balance_for_update(
                application.employee_id, application.start_date.year, application.category
            )
            remaining(balance.allotted, balance.used, application.duration)
            balance.used += application.duration
            balance.save(update_fields=["used"])
            record_transaction(
                application.employee_id,
                application.start_date.year,
                application.category,
                "DEBIT",
                application.duration,
                balance.allotted - balance.used,
                reference=f"Extension #{application.id} Approved",
            )
            application.status = "APPROVED"
        else:
            application.status = "REJECTED"

        application.approver_id = principal.user_id
        application.decision_remarks = remarks
        application.decided_at = timezone.now()
        application.save(
            update_fields=["status", "approver_id", "decision_remarks", "decided_at", "updated_at"]
        )
        log_event(application, principal.user_id, f"extension_{action}", remarks)
        create_notification(
            application.employee_id,
            application,
            "decision.recorded",
            f"Your leave extension #{application.id} was {application.status.lower()}.",
        )
        return application

    raise ValidationError(
        {"status": f"Application in state {application.status} is not currently actionable."}
    )


@transaction.atomic
def withdraw(principal, pk: int) -> LeaveApplication:
    application = get_object_or_404(
        LeaveApplication.objects.select_for_update(),
        pk=pk,
        employee_id=principal.user_id,
    )
    pending_statuses = (
        "AWAITING_SUB",
        "ACTION_REQUIRED",
        "PENDING",
        "AWAITING_ESTABLISHMENT",
        "RECOMMENDED",
        "AWAITING_DIRECTOR",
        "EXTENSION_AWAITING_SUB",
        "EXTENSION_ACTION_REQUIRED",
        "EXTENSION_PENDING",
        "EXTENSION_ESTABLISHMENT",
        "EXTENSION_SANCTION",
    )
    if application.status not in pending_statuses:
        raise ValidationError({"status": "Only pending applications can be withdrawn."})

    application.status = "WITHDRAWN"
    application.save(update_fields=["status", "updated_at"])
    log_event(application, principal.user_id, "withdrawn")

    # Notify concerned roles
    concerned_ids = {
        application.unit_head_id,
        application.substitute_user_id,
        application.sanction_authority_id,
    } - {None, principal.user_id}
    for cid in concerned_ids:
        create_notification(
            cid,
            application,
            "application.withdrawn",
            f"Leave application #{application.id} from employee "
            f"{principal.user_id} has been withdrawn.",
        )
    return application


@transaction.atomic
def request_cancellation(principal, pk: int, *, remarks: str = "") -> LeaveApplication:
    application = get_object_or_404(
        LeaveApplication.objects.select_for_update(),
        pk=pk,
        employee_id=principal.user_id,
    )
    if application.status != "APPROVED":
        raise ValidationError({"status": "Only approved leave can be cancelled."})
    if timezone.localdate() >= application.start_date:
        raise ValidationError({"start_date": "Approved leave cannot be cancelled once started."})

    application.status = "CANCELLATION_PENDING"
    application.save(update_fields=["status", "updated_at"])
    log_event(application, principal.user_id, "cancellation_requested", remarks)

    if application.unit_head_id:
        create_notification(
            application.unit_head_id,
            application,
            "cancellation.requested",
            f"Cancellation request submitted for approved leave #{application.id} "
            f"by employee {principal.user_id}.",
        )
    return application


# Legacy alias maintained for backwards compatibility
def cancel_approved(principal, pk: int, *, remarks: str = "") -> LeaveApplication:
    return request_cancellation(principal, pk, remarks=remarks)


@transaction.atomic
def submit_extension(principal, pk: int, data: dict) -> LeaveApplication:
    parent_app = get_object_or_404(
        LeaveApplication.objects.select_for_update(), pk=pk, employee_id=principal.user_id
    )
    if parent_app.status != "APPROVED":
        raise ValidationError({"status": "Extension is only available for approved leave."})
    if parent_app.category not in ("EL", "COL", "VL"):
        raise ValidationError(
            {"category": "Extension is supported only for ongoing EL, COL, or VL."}
        )

    today = timezone.localdate()
    # Ongoing check: must have started and not be excessively past end_date
    if today < parent_app.start_date:
        raise ValidationError({"start_date": "Cannot extend a leave that has not started yet."})

    new_end_date = data["end_date"]
    if new_end_date <= parent_app.end_date:
        raise ValidationError(
            {"end_date": "Extension end date must be after current approved end date."}
        )

    extension_start = parent_app.end_date + timedelta(days=1)
    substitute_user_id = data.get("substitute_user_id")
    _validate_substitute_eligibility(
        principal.user_id, substitute_user_id, extension_start, new_end_date
    )

    closed = get_published_dates(extension_start, new_end_date, "CLOSED")
    try:
        inc_duration = count_days(
            parent_app.category, extension_start, new_end_date, "NONE", closed
        )
    except ValueError as exc:
        raise ValidationError({"duration": str(exc)}) from exc

    balance = _balance_for_update(principal.user_id, extension_start.year, parent_app.category)
    try:
        remaining(balance.allotted, balance.used, inc_duration)
    except ValueError as exc:
        raise ValidationError({"balance": str(exc)}) from exc

    has_sub = bool(substitute_user_id)
    initial_status = "EXTENSION_AWAITING_SUB" if has_sub else "EXTENSION_PENDING"

    ext_app = LeaveApplication.objects.create(
        employee_id=principal.user_id,
        category=parent_app.category,
        start_date=extension_start,
        end_date=new_end_date,
        half_day="NONE",
        duration=inc_duration,
        reason=data.get("reason", f"Extension of leave #{parent_app.id}").strip(),
        substitute_user_id=substitute_user_id,
        substitute_status="PENDING" if has_sub else "NOT_REQUIRED",
        status=initial_status,
        unit_head_id=parent_app.unit_head_id,
        establishment_id=parent_app.establishment_id,
        sanction_authority_id=parent_app.sanction_authority_id,
        extended_from=parent_app,
    )
    log_event(
        ext_app,
        principal.user_id,
        "extension_requested",
        f"Extending #{parent_app.id} by {inc_duration} days",
    )

    if has_sub:
        create_notification(
            substitute_user_id,
            ext_app,
            "substitute.assigned",
            f"You are nominated as substitute for leave extension #{ext_app.id}.",
        )
    elif parent_app.unit_head_id:
        create_notification(
            parent_app.unit_head_id,
            ext_app,
            "task.assigned",
            f"Leave extension request #{ext_app.id} awaiting your review.",
        )

    return ext_app


@transaction.atomic
def submit_resumption(principal, pk: int, actual_date: date, remarks: str = "") -> LeaveApplication:
    application = get_object_or_404(
        LeaveApplication.objects.select_for_update(), pk=pk, employee_id=principal.user_id
    )
    if application.status != "APPROVED":
        raise ValidationError({"status": "Resumption can only be submitted for approved leave."})
    if application.category not in ("EL", "COL", "VL"):
        raise ValidationError({"category": "Resumption is supported only for EL, COL, and VL."})
    if actual_date < application.start_date:
        raise ValidationError({"actual_date": "Resumption date cannot be before leave start date."})

    application.actual_resumption_date = actual_date
    application.resumption_remarks = remarks
    application.status = "RESUMPTION_PENDING"
    application.save(
        update_fields=["actual_resumption_date", "resumption_remarks", "status", "updated_at"]
    )
    log_event(
        application, principal.user_id, "resumption_submitted", f"Actual return: {actual_date}"
    )

    review_authority_id = application.sanction_authority_id or application.unit_head_id
    if review_authority_id:
        create_notification(
            review_authority_id,
            application,
            "resumption.pending_review",
            f"Employee {principal.user_id} submitted duty resumption for leave "
            f"#{application.id} (return: {actual_date}).",
        )
    return application


@transaction.atomic
def review_resumption(principal, pk: int, remarks: str = "") -> LeaveApplication:
    application = get_object_or_404(LeaveApplication.objects.select_for_update(), pk=pk)
    if application.status != "RESUMPTION_PENDING":
        raise ValidationError({"status": "Application is not awaiting resumption review."})

    review_authority_id = application.sanction_authority_id or application.unit_head_id
    if principal.user_id != review_authority_id:
        raise PermissionDenied("Only the designated sanction authority can review duty resumption.")

    actual_date = application.actual_resumption_date
    if not actual_date:
        raise ValidationError({"actual_resumption_date": "Actual resumption date is missing."})

    closed = get_published_dates(application.start_date, actual_date, "CLOSED")
    actual_duration = count_days(
        application.category, application.start_date, actual_date, "NONE", closed
    )

    adj_type, delta = calculate_resumption_delta(application.duration, actual_duration)
    balance = _balance_for_update(
        application.employee_id, application.start_date.year, application.category
    )

    if adj_type == "RESTORE" and delta > 0:
        balance.used = max(Decimal("0"), balance.used - delta)
        balance.save(update_fields=["used"])
        record_transaction(
            application.employee_id,
            application.start_date.year,
            application.category,
            "CREDIT",
            delta,
            balance.allotted - balance.used,
            reference=f"LeaveApplication #{application.id} Early Resumption Balance Restore",
        )
    elif adj_type == "DEBIT" and delta > 0:
        balance.used += delta
        balance.save(update_fields=["used"])
        record_transaction(
            application.employee_id,
            application.start_date.year,
            application.category,
            "DEBIT",
            delta,
            balance.allotted - balance.used,
            reference=f"LeaveApplication #{application.id} Late Resumption Balance Debit",
        )

    application.duration = actual_duration
    application.end_date = actual_date
    application.resumed_at = actual_date
    # AFR-EL-021.10: Do not impose generic Closed state on normal resumption
    application.status = "APPROVED"
    application.save(update_fields=["duration", "end_date", "resumed_at", "status", "updated_at"])
    log_event(
        application,
        principal.user_id,
        "resumption_reviewed",
        f"Outcome: {adj_type} {delta} days. {remarks}".strip(),
    )
    create_notification(
        application.employee_id,
        application,
        "resumption.reviewed",
        f"Duty resumption for leave #{application.id} verified. "
        f"Final duration: {actual_duration} days.",
    )
    return application


@transaction.atomic
def record_offline_leave(principal, data: dict) -> LeaveApplication:
    """Synchronize an already-sanctioned offline/paper leave (CFR-EL-027, BR-EL-029, EL-UC-016)."""
    employee_id = data["employee_id"]
    profile = get_object_or_404(EmployeeLeaveProfile, user_id=employee_id)
    category = data["category"]
    start = data["start_date"]
    end = data["end_date"]
    half_day = data.get("half_day", "NONE")
    reference = data.get("sanction_reference", "").strip()

    if not reference:
        raise ValidationError(
            {"sanction_reference": "Sanction reference evidence is required for offline leave."}
        )
    if not eligible(category, profile.category):
        raise ValidationError({"category": "Leave type is not eligible for this employee."})
    if start.year != end.year:
        raise ValidationError(
            {"end_date": "Leave interval must fall within a single calendar year."}
        )

    closed = get_published_dates(start, end, "CLOSED")
    duration = count_days(category, start, end, half_day, closed)

    balance = _balance_for_update(employee_id, start.year, category)
    try:
        remaining(balance.allotted, balance.used, duration)
    except ValueError as exc:
        raise ValidationError({"balance": str(exc)}) from exc

    balance.used += duration
    balance.save(update_fields=["used"])
    record_transaction(
        employee_id,
        start.year,
        category,
        "DEBIT",
        duration,
        balance.allotted - balance.used,
        reference=f"Offline Sanction: {reference}",
    )

    application = LeaveApplication.objects.create(
        employee_id=employee_id,
        category=category,
        start_date=start,
        end_date=end,
        half_day=half_day,
        duration=duration,
        reason=data.get("reason", "Offline sanctioned leave").strip(),
        status="APPROVED",
        is_offline=True,
        sanction_reference=reference,
        unit_head_id=profile.unit_head_user_id or principal.user_id,
        sanction_authority_id=profile.sanction_authority_user_id or principal.user_id,
        approver_id=principal.user_id,
        decided_at=timezone.now(),
        decision_remarks="Synchronized from offline sanction evidence",
    )
    log_event(application, principal.user_id, "offline_leave_synchronized", reference)
    return application


@transaction.atomic
def execute_year_end_processing(year: int) -> dict:
    """Execute year-end outcomes (CFR-EL-028, BR-EL-002..009, EL-UC-020)."""
    summary = {
        "year": year,
        "lapsed_records": 0,
        "vl_converted_faculty": 0,
        "carried_forward": 0,
        "exceptions": [],
    }

    # 1. Lapse unused CL, RH, SCL
    for bal in LeaveBalance.objects.select_for_update().filter(
        year=year, category__in=("CL", "RH", "SCL")
    ):
        unused = max(Decimal("0"), bal.allotted - bal.used)
        if unused > 0:
            record_transaction(
                bal.employee_id,
                year,
                bal.category,
                "LAPSE",
                unused,
                Decimal("0"),
                reference=f"Year-End {year} Lapse",
            )
            bal.used = bal.allotted
            bal.save(update_fields=["used"])
            summary["lapsed_records"] += 1

    # 2. Convert unused Faculty VL to EL (2:1 fractional)
    faculty_profiles = EmployeeLeaveProfile.objects.filter(category="faculty")
    for profile in faculty_profiles:
        vl_bal = (
            LeaveBalance.objects.select_for_update()
            .filter(employee_id=profile.user_id, year=year, category="VL")
            .first()
        )
        if not vl_bal:
            continue
        unavailed_vl = max(Decimal("0"), vl_bal.allotted - vl_bal.used)
        if unavailed_vl > 0:
            next_el, _ = LeaveBalance.objects.select_for_update().get_or_create(
                employee_id=profile.user_id,
                year=year + 1,
                category="EL",
                defaults={"allotted": Decimal("0"), "used": Decimal("0")},
            )
            credited, new_el_allotted = convert_vl_to_el(unavailed_vl, next_el.allotted)
            next_el.allotted = new_el_allotted
            next_el.save(update_fields=["allotted"])

            record_transaction(
                profile.user_id,
                year,
                "VL",
                "CONVERSION",
                unavailed_vl,
                Decimal("0"),
                reference=f"Year-End {year} Converted {unavailed_vl} VL to {credited} EL",
            )
            record_transaction(
                profile.user_id,
                year + 1,
                "EL",
                "CREDIT_FROM_VL",
                credited,
                next_el.allotted - next_el.used,
                reference=f"Year-End {year} Credit from VL Conversion",
            )
            vl_bal.used = vl_bal.allotted
            vl_bal.save(update_fields=["used"])
            summary["vl_converted_faculty"] += 1

    # 3. Carry forward EL and COL
    for bal in LeaveBalance.objects.select_for_update().filter(
        year=year, category__in=("EL", "COL")
    ):
        unused = max(Decimal("0"), bal.allotted - bal.used)
        if unused > 0:
            next_bal, _ = LeaveBalance.objects.select_for_update().get_or_create(
                employee_id=bal.employee_id,
                year=year + 1,
                category=bal.category,
                defaults={"allotted": Decimal("0"), "used": Decimal("0")},
            )
            next_bal.allotted += unused
            next_bal.save(update_fields=["allotted"])
            record_transaction(
                bal.employee_id,
                year + 1,
                bal.category,
                "CARRY_FORWARD",
                unused,
                next_bal.allotted - next_bal.used,
                reference=f"Year-End {year} Carry Forward",
            )
            summary["carried_forward"] += 1

    return summary


@transaction.atomic
def process_sla_thresholds() -> dict:
    """Evaluate SLA reminder and escalation thresholds for still-pending tasks
    (CFR-EL-031, CFR-EL-032, EL-UC-021).
    """
    now = timezone.now()
    configs = {c.task_type: c for c in SlaConfig.objects.all()}
    default_config = SlaConfig(task_type="default", reminder_hours=24, escalation_hours=72)

    pending_apps = LeaveApplication.objects.filter(
        status__in=(
            "AWAITING_SUB",
            "PENDING",
            "AWAITING_ESTABLISHMENT",
            "RECOMMENDED",
            "AWAITING_DIRECTOR",
            "CANCELLATION_PENDING",
            "CANCELLATION_ESTABLISHMENT",
            "CANCELLATION_SANCTION",
            "EXTENSION_AWAITING_SUB",
            "EXTENSION_PENDING",
            "EXTENSION_SANCTION",
            "RESUMPTION_PENDING",
        )
    )

    reminded_count = 0
    escalated_count = 0

    for app in pending_apps:
        cfg = configs.get(app.status, default_config)
        elapsed_hours = (now - app.created_at).total_seconds() / 3600.0

        # Responsible recipient based on current task
        if app.status in ("AWAITING_SUB", "EXTENSION_AWAITING_SUB"):
            target_user = app.substitute_user_id
        elif app.status in ("PENDING", "CANCELLATION_PENDING", "EXTENSION_PENDING"):
            target_user = app.unit_head_id
        elif app.status in (
            "AWAITING_ESTABLISHMENT",
            "CANCELLATION_ESTABLISHMENT",
            "EXTENSION_ESTABLISHMENT",
        ):
            target_user = app.establishment_id
        elif app.status in (
            "RECOMMENDED",
            "CANCELLATION_SANCTION",
            "EXTENSION_SANCTION",
            "RESUMPTION_PENDING",
        ):
            target_user = app.sanction_authority_id
        elif app.status == "AWAITING_DIRECTOR":
            target_user = app.employee_id
        else:
            target_user = None

        if not target_user:
            continue

        # Reminder threshold
        if elapsed_hours >= cfg.reminder_hours:
            already_reminded = LeaveNotification.objects.filter(
                application=app, recipient_id=target_user, is_reminder=True
            ).exists()
            if not already_reminded:
                create_notification(
                    target_user,
                    app,
                    "sla.reminder",
                    f"Reminder: Actionable task for application #{app.id} is still pending.",
                    is_reminder=True,
                )
                log_event(app, 0, "sla_reminder_issued", f"Reminded user {target_user}")
                reminded_count += 1

        # Escalation threshold
        if elapsed_hours >= cfg.escalation_hours:
            already_escalated = LeaveNotification.objects.filter(
                application=app, is_escalation=True
            ).exists()
            if not already_escalated:
                escalate_to = (
                    cfg.escalate_to_user_id or app.sanction_authority_id or app.unit_head_id
                )
                if escalate_to and escalate_to != target_user:
                    create_notification(
                        escalate_to,
                        app,
                        "sla.escalation",
                        f"Escalation: Task for application #{app.id} has exceeded "
                        f"{cfg.escalation_hours}h SLA.",
                        is_escalation=True,
                    )
                    log_event(app, 0, "sla_escalation_issued", f"Escalated to user {escalate_to}")
                    escalated_count += 1

    return {"reminded": reminded_count, "escalated": escalated_count}


@transaction.atomic
def upsert_profile(data: dict) -> tuple[EmployeeLeaveProfile, bool]:
    payload = dict(data)
    user_id = payload.pop("user_id")
    return EmployeeLeaveProfile.objects.update_or_create(user_id=user_id, defaults=payload)


@transaction.atomic
def allot_balance(data: dict) -> LeaveBalance:
    payload = dict(data)
    allot = payload.pop("allotted")
    get_object_or_404(EmployeeLeaveProfile, user_id=payload["employee_id"])
    obj, _ = LeaveBalance.objects.select_for_update().get_or_create(
        **payload, defaults={"allotted": allot, "used": 0}
    )
    if obj.used > allot:
        raise ValidationError({"allotted": "Allotment cannot be less than already used leave."})
    obj.allotted = allot
    obj.save(update_fields=["allotted"])
    return obj


@transaction.atomic
def upsert_holiday(data: dict) -> Holiday:
    payload = dict(data)
    holiday_date = payload.pop("date")
    obj, _ = Holiday.objects.update_or_create(date=holiday_date, defaults=payload)
    return obj
