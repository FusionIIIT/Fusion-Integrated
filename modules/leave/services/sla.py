"""SLA reminder and escalation services for the Employee Leave Module (ELM).

Implements:
- BR-EL-032: SLA Reminder
- BR-EL-033: SLA Escalation
- BR-EL-035: Assignment Notification & Escalation Recipients
- BR-EL-038: Configurable SLA Thresholds
- EL-UC-021: Process SLA Threshold Event
- XTP-EL-01: Cross-cutting automatic SLA routing pattern
- Idempotent repeated execution and concurrent row-locking safeguards.
- Immutable audit recording via WorkflowTransition.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from modules.directory import contracts as directory_contracts
from modules.leave.domain.state_machine import LeaveState
from modules.leave.models import LeaveRequest, WorkflowTransition

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StageSlaConfig:
    """Configurable SLA thresholds and actor roles for a workflow stage."""

    reminder_threshold_hours: float
    escalation_threshold_hours: float
    responsible_role: str
    escalation_role: str
    auto_escalate_routing: bool = True


@dataclass
class SlaNotificationEvent:
    """Structured event emitted when an SLA reminder or escalation fires."""

    request_id: int
    application_number: str
    recipient_user_id: int | None
    recipient_role: str
    event_type: str  # "reminder" | "escalation"
    stage: str
    elapsed_hours: float
    threshold_hours: float
    message: str


@dataclass
class SlaProcessingReport:
    """Execution summary returned by the SLA processor."""

    inspected_requests: int = 0
    reminders_sent: int = 0
    escalations_sent: int = 0
    skipped_requests: int = 0
    notification_failures: int = 0
    exceptions: list[str] = field(default_factory=list)


DEFAULT_STAGE_SLA_CONFIGS: dict[str, StageSlaConfig] = {
    LeaveState.AWAITING_SUBSTITUTE: StageSlaConfig(
        reminder_threshold_hours=24.0,
        escalation_threshold_hours=48.0,
        responsible_role="Substitute",
        escalation_role="Applicant",
    ),
    LeaveState.AWAITING_EXTENSION_SUBSTITUTE: StageSlaConfig(
        reminder_threshold_hours=24.0,
        escalation_threshold_hours=48.0,
        responsible_role="Substitute",
        escalation_role="Applicant",
    ),
    LeaveState.AWAITING_UNIT_HEAD: StageSlaConfig(
        reminder_threshold_hours=48.0,
        escalation_threshold_hours=96.0,
        responsible_role="Unit Head",
        escalation_role="Sanctioning Authority",
    ),
    LeaveState.CANCELLATION_PENDING_UNIT_HEAD: StageSlaConfig(
        reminder_threshold_hours=48.0,
        escalation_threshold_hours=96.0,
        responsible_role="Unit Head",
        escalation_role="Sanctioning Authority",
    ),
    LeaveState.AWAITING_EXTENSION_UNIT_HEAD: StageSlaConfig(
        reminder_threshold_hours=48.0,
        escalation_threshold_hours=96.0,
        responsible_role="Unit Head",
        escalation_role="Sanctioning Authority",
    ),
    LeaveState.AWAITING_SANCTION: StageSlaConfig(
        reminder_threshold_hours=72.0,
        escalation_threshold_hours=144.0,
        responsible_role="Sanctioning Authority",
        escalation_role="Director",
    ),
    LeaveState.CANCELLATION_PENDING_SANCTION: StageSlaConfig(
        reminder_threshold_hours=72.0,
        escalation_threshold_hours=144.0,
        responsible_role="Sanctioning Authority",
        escalation_role="Director",
    ),
    LeaveState.EXTENSION_PENDING_SANCTION: StageSlaConfig(
        reminder_threshold_hours=72.0,
        escalation_threshold_hours=144.0,
        responsible_role="Sanctioning Authority",
        escalation_role="Director",
    ),
    LeaveState.AWAITING_DIRECTOR: StageSlaConfig(
        reminder_threshold_hours=72.0,
        escalation_threshold_hours=144.0,
        responsible_role="Director",
        escalation_role="Registrar",
    ),
    LeaveState.RESUMPTION_REVIEW_PENDING: StageSlaConfig(
        reminder_threshold_hours=48.0,
        escalation_threshold_hours=96.0,
        responsible_role="Unit Head",
        escalation_role="Sanctioning Authority",
    ),
}


def process_sla_events(
    *,
    now: datetime | None = None,
    stage_configs: dict[str, StageSlaConfig] | None = None,
    request_ids: Sequence[int] | None = None,
    notification_dispatcher: Callable[[SlaNotificationEvent], None] | None = None,
    dry_run: bool = False,
) -> SlaProcessingReport:
    """Evaluate SLA thresholds for actionable pending requests and trigger events.

    Args:
        now: Reference datetime. Defaults to timezone.now().
        stage_configs: Mapping of stage name to StageSlaConfig.
            Defaults to DEFAULT_STAGE_SLA_CONFIGS.
        request_ids: Optional subset of request IDs to inspect.
        notification_dispatcher: Optional callback receiving SlaNotificationEvent.
        dry_run: If True, rehearses evaluation inside a rolled-back transaction.

    Returns:
        SlaProcessingReport containing summary counts and any processing errors.
    """
    ref_time = now or timezone.now()
    configs = stage_configs if stage_configs is not None else DEFAULT_STAGE_SLA_CONFIGS
    report = SlaProcessingReport()

    # Validate thresholds
    for stage, cfg in configs.items():
        if cfg.reminder_threshold_hours < 0 or cfg.escalation_threshold_hours < 0:
            msg = f"Invalid negative SLA threshold for stage '{stage}'"
            logger.error(msg)
            report.exceptions.append(msg)
            return report
        if cfg.escalation_threshold_hours < cfg.reminder_threshold_hours:
            msg = (
                f"Escalation threshold ({cfg.escalation_threshold_hours}h) cannot be less than "
                f"reminder threshold ({cfg.reminder_threshold_hours}h) for stage '{stage}'"
            )
            logger.error(msg)
            report.exceptions.append(msg)
            return report

    if dry_run:
        with transaction.atomic():
            _execute_sla_processing(
                ref_time=ref_time,
                configs=configs,
                request_ids=request_ids,
                notification_dispatcher=notification_dispatcher,
                report=report,
            )
            transaction.set_rollback(True)
        return report

    _execute_sla_processing(
        ref_time=ref_time,
        configs=configs,
        request_ids=request_ids,
        notification_dispatcher=notification_dispatcher,
        report=report,
    )
    return report


def _execute_sla_processing(
    ref_time: datetime,
    configs: dict[str, StageSlaConfig],
    request_ids: Sequence[int] | None,
    notification_dispatcher: Callable[[SlaNotificationEvent], None] | None,
    report: SlaProcessingReport,
) -> None:
    qs = LeaveRequest.objects.filter(status__in=list(configs.keys()))
    if request_ids is not None:
        qs = qs.filter(id__in=request_ids)

    candidate_ids = list(qs.values_list("id", flat=True))
    report.inspected_requests = len(candidate_ids)

    for req_id in candidate_ids:
        try:
            with transaction.atomic():
                _process_single_request_sla(
                    request_id=req_id,
                    ref_time=ref_time,
                    configs=configs,
                    notification_dispatcher=notification_dispatcher,
                    report=report,
                )
        except Exception as exc:
            msg = f"Error processing SLA for request {req_id}: {exc}"
            logger.exception(msg)
            report.exceptions.append(msg)


def _process_single_request_sla(
    request_id: int,
    ref_time: datetime,
    configs: dict[str, StageSlaConfig],
    notification_dispatcher: Callable[[SlaNotificationEvent], None] | None,
    report: SlaProcessingReport,
) -> None:
    # 1. Lock the request row to ensure concurrency safety
    try:
        req = (
            LeaveRequest.objects.select_for_update().select_related("leave_type").get(pk=request_id)
        )
    except LeaveRequest.DoesNotExist:
        return

    # 2. Check if request is still in an SLA-governed pending state
    cfg = configs.get(req.status)
    if not cfg:
        report.skipped_requests += 1
        return

    # 3. Determine when the request entered its current stage
    last_transition = (
        req.transitions.filter(to_state=req.status)
        .exclude(action__startswith="sla_")
        .order_by("-created_at")
        .first()
    )
    stage_entered_at = last_transition.created_at if last_transition else req.updated_at
    elapsed_hours = (ref_time - stage_entered_at).total_seconds() / 3600.0

    if elapsed_hours < cfg.reminder_threshold_hours:
        # Not yet reached reminder threshold
        return

    # 4. Check past SLA transitions recorded during the CURRENT stage
    recent_transitions = req.transitions.filter(
        from_state=req.status,
        created_at__gte=stage_entered_at,
    )
    has_reminder = recent_transitions.filter(action="sla_reminder").exists()
    has_escalation = recent_transitions.filter(action="sla_escalation").exists()

    # 5. Evaluate escalation threshold first (higher priority if overdue)
    if elapsed_hours >= cfg.escalation_threshold_hours:
        if has_escalation:
            report.skipped_requests += 1
            return

        escalation_recipient_id = _resolve_escalation_recipient(req, cfg)
        event = SlaNotificationEvent(
            request_id=req.id,
            application_number=req.application_number,
            recipient_user_id=escalation_recipient_id,
            recipient_role=cfg.escalation_role,
            event_type="escalation",
            stage=req.status,
            elapsed_hours=elapsed_hours,
            threshold_hours=cfg.escalation_threshold_hours,
            message=(
                f"SLA Escalation: Request {req.application_number} has been pending in stage "
                f"'{req.status}' for {elapsed_hours:.1f} hours, exceeding the escalation "
                f"threshold of {cfg.escalation_threshold_hours:.1f} hours."
            ),
        )

        dispatch_ok = _safe_dispatch(event, notification_dispatcher)
        if dispatch_ok:
            WorkflowTransition.objects.create(
                request=req,
                from_state=req.status,
                to_state=req.status,
                action="sla_escalation",
                actor_user_id=0,
                actor_role="System",
                remarks=(
                    f"SLA escalation after {elapsed_hours:.1f}h pending "
                    f"(threshold {cfg.escalation_threshold_hours}h); "
                    f"escalated to {cfg.escalation_role} (user {escalation_recipient_id})"
                ),
            )
            if cfg.auto_escalate_routing:
                req.current_handler_role = cfg.escalation_role
                req.save(update_fields=["current_handler_role", "updated_at"])
            report.escalations_sent += 1
        else:
            report.notification_failures += 1

    # 6. Evaluate reminder threshold
    elif elapsed_hours >= cfg.reminder_threshold_hours:
        if has_reminder:
            report.skipped_requests += 1
            return

        responsible_recipient_id = _resolve_responsible_recipient(req, cfg)
        event = SlaNotificationEvent(
            request_id=req.id,
            application_number=req.application_number,
            recipient_user_id=responsible_recipient_id,
            recipient_role=cfg.responsible_role,
            event_type="reminder",
            stage=req.status,
            elapsed_hours=elapsed_hours,
            threshold_hours=cfg.reminder_threshold_hours,
            message=(
                f"SLA Reminder: Request {req.application_number} is pending your action in stage "
                f"'{req.status}' ({elapsed_hours:.1f} hours elapsed, threshold "
                f"{cfg.reminder_threshold_hours:.1f} hours)."
            ),
        )

        dispatch_ok = _safe_dispatch(event, notification_dispatcher)
        if dispatch_ok:
            WorkflowTransition.objects.create(
                request=req,
                from_state=req.status,
                to_state=req.status,
                action="sla_reminder",
                actor_user_id=0,
                actor_role="System",
                remarks=(
                    f"SLA reminder after {elapsed_hours:.1f}h pending "
                    f"(threshold {cfg.reminder_threshold_hours}h); "
                    f"reminded {cfg.responsible_role} (user {responsible_recipient_id})"
                ),
            )
            report.reminders_sent += 1
        else:
            report.notification_failures += 1


def _safe_dispatch(
    event: SlaNotificationEvent,
    dispatcher: Callable[[SlaNotificationEvent], None] | None,
) -> bool:
    """Dispatch notification safely without breaking workflow state on error."""
    if dispatcher is None:
        return True
    try:
        dispatcher(event)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Notification dispatcher failed for SLA event on %s: %s",
            event.application_number,
            exc,
        )
        return False
    else:
        return True


def _resolve_responsible_recipient(req: LeaveRequest, cfg: StageSlaConfig) -> int | None:
    """Resolve the responsible user ID for a pending task respecting department scope."""
    if req.status in (LeaveState.AWAITING_SUBSTITUTE, LeaveState.AWAITING_EXTENSION_SUBSTITUTE):
        pending_sub = req.substitutes.filter(status="pending").first()
        return pending_sub.substitute_user_id if pending_sub else None

    if req.current_handler_user_id:
        return req.current_handler_user_id

    # Department-scoped Unit Head resolution
    if cfg.responsible_role in ("Unit Head", "HOD"):
        employees = directory_contracts.get_employees()
        for emp in employees:
            if emp.department == req.department and emp.kind in ("faculty", "staff"):
                # First eligible officer in department
                return emp.user_id

    return None


def _resolve_escalation_recipient(req: LeaveRequest, cfg: StageSlaConfig) -> int | None:
    """Resolve the higher authority recipient ID for escalation."""
    if req.status in (LeaveState.AWAITING_SUBSTITUTE, LeaveState.AWAITING_EXTENSION_SUBSTITUTE):
        # Substitute non-response escalates to applicant
        return req.user_id

    # Unit head escalation goes to sanctioning authority / director
    if cfg.escalation_role in ("Director", "Sanctioning Authority"):
        employees = directory_contracts.get_employees()
        for emp in employees:
            if "director" in emp.display_name.lower():
                return emp.user_id

    return None
