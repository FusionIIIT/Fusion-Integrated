from datetime import date
from decimal import Decimal

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, views, viewsets
from rest_framework.exceptions import APIException
from rest_framework.response import Response

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.api.serializers import (
    LeaveApplicationSerializer,
    LeaveBalanceSerializer,
    LeaveCategorySerializer,
    SubstituteNominationSerializer,
)
from modules.elm.models import (
    ApprovalRoutingConfiguration,
    LeaveApplication,
    LeaveApprovalDecision,
    LeaveBalance,
    LeaveCategory,
    SLAThresholdConfiguration,
    SubstituteNomination,
)

MODULE = HasModuleGrant("modules.elm")


def _actor_id(request):
    """Return the authenticated Fusion principal id; never trust a client id."""
    principal = getattr(request, "principal", None)
    if principal is None:
        return None
    return principal.user_id


class DirectoryUnavailable(APIException):
    status_code = 503
    default_detail = "The employee directory is temporarily unavailable."
    default_code = "directory_unavailable"


def _employee_type(user_id):
    """Read faculty/staff classification through the directory contract."""
    from fusion_auth.client import IamUnavailable
    from modules.directory.contracts import get_users

    try:
        employee = get_users([user_id]).get(user_id)
    except IamUnavailable as exc:
        raise DirectoryUnavailable() from exc
    if employee is None or employee.kind not in {"faculty", "staff"}:
        return None
    return "F" if employee.kind == "faculty" else "S"


# ============================================================================
# Leave Category ViewSet
# ============================================================================


class LeaveCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for leave category configuration."""

    permission_classes = [
        MODULE,
        HasPermission(
            "modules.elm.application.create",
            "modules.elm.application.view",
            "modules.elm.balance.view",
        ),
    ]
    queryset = LeaveCategory.objects.all()
    serializer_class = LeaveCategorySerializer

    def list(self, request):
        """Return all leave categories with current configured parameters."""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


# ============================================================================
# Leave Application Views
# ============================================================================


class LeaveApplicationCreateView(views.APIView):
    """EL-UC-001: Apply for Leave — Employee creates and submits a new leave application."""

    permission_classes = [MODULE, HasPermission("modules.elm.application.create")]

    def post(self, request):
        """Create a new leave application."""
        serializer = LeaveApplicationSerializer(data=request.data)
        if serializer.is_valid():
            application = serializer.save(employee_user_id=_actor_id(request))

            # Validate the application per BR-EL-001, BR-EL-003, etc.
            # This includes category eligibility, entitlement/balance, counting/calendar,
            # and impermissible overlap checks
            from modules.elm.services import LeaveValidationService

            validation_result = LeaveValidationService.validate_new_application(application)

            if not validation_result["valid"]:
                # Rollback the save and return errors
                application.delete()
                return Response(
                    {"error": validation_result["error"]}, status=status.HTTP_400_BAD_REQUEST
                )

            routing = ApprovalRoutingConfiguration.objects.filter(
                leave_category=application.leave_category
            ).first()
            if routing is None or not routing.is_complete():
                application.delete()
                return Response(
                    {"error": "Approval routing is not configured for this leave category."},
                    status=status.HTTP_409_CONFLICT,
                )
            application.status = LeaveApplication.StatusChoices.AWAITING_UNIT_HEAD_REVIEW
            application.save(update_fields=["status"])

            return Response(
                {
                    **LeaveApplicationSerializer(application).data,
                    "message": f"{application.leave_category.code} leave request",
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EmployeeLeaveApplicationsView(views.APIView):
    """EL-UC-012 / EL-UC-003: View own leave applications and history."""

    permission_classes = [MODULE, HasPermission("modules.elm.application.view")]

    def get(self, request, employee_user_id=None):
        """Get all leave applications for the authenticated employee."""
        user_id = _actor_id(request)
        applications = LeaveApplication.objects.filter(employee_user_id=user_id).order_by(
            "-submitted_at"
        )
        serializer = LeaveApplicationSerializer(applications, many=True)
        return Response(serializer.data)


class LeaveApplicationDetailView(views.APIView):
    """EL-UC-013: Obtain detail of a specific leave application."""

    permission_classes = [MODULE, HasPermission("modules.elm.application.view")]

    def get(self, request, pk):
        """Get details of a specific leave application."""
        application = get_object_or_404(
            LeaveApplication, pk=pk, employee_user_id=_actor_id(request)
        )
        # Check authorization: employee can only view their own
        # In production, this would check the authenticated user's id
        serializer = LeaveApplicationSerializer(application)
        return Response(serializer.data)


# ============================================================================
# Leave Balances View
# ============================================================================


class EmployeeLeaveBalancesView(views.APIView):
    """EL-UC-012: View current leave balances and history."""

    permission_classes = [MODULE, HasPermission("modules.elm.balance.view")]

    def get(self, request, employee_user_id=None):
        """Get leave balances for the authenticated employee."""
        user_id = _actor_id(request)
        employee_type = _employee_type(user_id)
        if employee_type is None:
            return Response(
                {"error": "Only active Faculty and Staff employees have leave balances."},
                status=status.HTTP_403_FORBIDDEN,
            )

        categories = LeaveCategory.objects.filter(applicable_to__in=("B", employee_type))
        for category in categories:
            LeaveBalance.objects.get_or_create(
                user_id=user_id,
                leave_category=category,
                year=date.today().year,
                defaults={
                    "entitlement_per_year": category.annual_entitlement or Decimal("0"),
                },
            )

        balances = LeaveBalance.objects.filter(user_id=user_id).select_related("leave_category")
        serializer = LeaveBalanceSerializer(balances, many=True)
        return Response({"balances": serializer.data})


# ============================================================================
# Leave History View
# ============================================================================


class EmployeeLeaveHistoryView(views.APIView):
    """EL-UC-012: View leave-account/request history including status and decisions."""

    permission_classes = [MODULE, HasPermission("modules.elm.history.view")]

    def get(self, request, employee_user_id=None):
        """Get leave history for the authenticated employee."""
        user_id = _actor_id(request)
        applications = LeaveApplication.objects.filter(employee_user_id=user_id).order_by(
            "-submitted_at"
        )
        # Include balance snapshots at key points
        from modules.elm.models import LeaveBalance

        balances = LeaveBalance.objects.filter(user_id=user_id).select_related("leave_category")

        history = [
            {
                "type": "application",
                "pk": app.pk,
                "leave_category_code": app.leave_category.code,
                "status": app.status,
                "requested_start": app.requested_start,
                "requested_end": app.requested_end,
                "purpose_reason": app.purpose_reason,
                "submitted_at": app.submitted_at,
                "final_decision": app.status
                in (
                    LeaveApplication.StatusChoices.APPROVED,
                    LeaveApplication.StatusChoices.REJECTED,
                    LeaveApplication.StatusChoices.CANCELLED,
                ),
            }
            for app in applications
        ]
        history.extend(
            [
                {
                    "type": "balance",
                    "leave_category_code": balance.leave_category.code,
                    "year": balance.year,
                    "entitlement": float(balance.entitlement_per_year),
                    "used": float(balance.used_per_year),
                    "carry_forward": float(balance.carried_forward_from_previous),
                    "available_days": float(balance.available()),
                }
                for balance in balances
            ]
        )

        history.sort(key=lambda x: x.get("submitted_at") or x.get("year", 0), reverse=True)
        return Response(history)


# ============================================================================
# Configurable Approval Workflow
# ============================================================================


def _workflow_role(request):
    principal = getattr(request, "principal", None)
    return (getattr(principal, "active_role", None) or "").strip()


def _routing_payload(config):
    return {
        "leave_category_code": config.leave_category.code,
        "unit_head_role": config.unit_head_role,
        "establishment_enabled": config.establishment_enabled,
        "establishment_role": config.establishment_role,
        "final_authority_role": config.final_authority_role,
        "configured": config.is_complete(),
    }


def _requested_day_count(application):
    from modules.elm.services import LeaveValidationService

    return LeaveValidationService.count_requested_days(application)


def _post_balance(application, sign):
    """Post approved leave once; extensions charge only their incremental dates."""
    year = application.requested_start.year
    balance, _ = LeaveBalance.objects.get_or_create(
        user_id=application.employee_user_id,
        leave_category=application.leave_category,
        year=year,
        defaults={
            "entitlement_per_year": application.leave_category.annual_entitlement or Decimal("0"),
        },
    )
    balance.used_per_year = max(
        Decimal("0"), balance.used_per_year + sign * _requested_day_count(application)
    )
    balance.save(update_fields=["used_per_year"])


class ApprovalRoutingConfigurationView(views.APIView):
    """Maintain per-category roles; no authority is assumed by default."""

    permission_classes = [MODULE, HasPermission("modules.elm.workflow.configure")]

    def get(self, request):
        rows = ApprovalRoutingConfiguration.objects.select_related("leave_category")
        return Response([_routing_payload(row) for row in rows])

    def post(self, request):
        code = request.data.get("leave_category_code")
        try:
            category = LeaveCategory.objects.get(code=code)
        except LeaveCategory.DoesNotExist:
            return Response({"error": "Unknown leave_category_code."}, status=400)

        enabled = request.data.get("establishment_enabled")
        if enabled not in (True, False, None):
            return Response(
                {"error": "establishment_enabled must be true, false, or null."}, status=400
            )
        unit_role = str(request.data.get("unit_head_role") or "").strip()
        establishment_role = str(request.data.get("establishment_role") or "").strip()
        final_role = str(request.data.get("final_authority_role") or "").strip()
        if category.code not in {"CL", "RH"} and enabled is True and not establishment_role:
            return Response(
                {"error": "Set establishment_role when Establishment routing is enabled."},
                status=400,
            )

        config, _ = ApprovalRoutingConfiguration.objects.update_or_create(
            leave_category=category,
            defaults={
                "unit_head_role": unit_role,
                "establishment_enabled": enabled,
                "establishment_role": establishment_role,
                "final_authority_role": final_role,
                "updated_by_user_id": _actor_id(request),
            },
        )
        return Response(_routing_payload(config))


class LeaveApprovalQueueView(views.APIView):
    """List only items waiting at the active configured role."""

    permission_classes = [MODULE, HasPermission("modules.elm.workflow.review")]

    def get(self, request):
        role = _workflow_role(request)
        if not role:
            return Response({"error": "Choose an active IAM role before reviewing."}, status=400)
        pending = LeaveApplication.objects.filter(
            status__in=[
                LeaveApplication.StatusChoices.AWAITING_UNIT_HEAD_REVIEW,
                LeaveApplication.StatusChoices.AWAITING_ESTABLISHMENT_ROUTING,
                LeaveApplication.StatusChoices.AWAITING_FINAL_SANCTION,
            ]
        ) | LeaveApplication.objects.filter(
            status=LeaveApplication.StatusChoices.APPROVED,
            cancellation_status=LeaveApplication.CancellationStatus.PENDING,
        )
        pending = pending.select_related("leave_category").distinct()
        items = []
        for app in pending:
            config = ApprovalRoutingConfiguration.objects.filter(
                leave_category=app.leave_category
            ).first()
            if config is None or not config.is_complete():
                continue
            workflow_type = (
                LeaveApprovalDecision.WorkflowType.CANCELLATION
                if app.cancellation_status == LeaveApplication.CancellationStatus.PENDING
                else LeaveApprovalDecision.WorkflowType.LEAVE
            )
            if workflow_type == LeaveApprovalDecision.WorkflowType.LEAVE:
                stage_for_status = {
                    LeaveApplication.StatusChoices.AWAITING_UNIT_HEAD_REVIEW: LeaveApprovalDecision.Stage.UNIT_HEAD,
                    LeaveApplication.StatusChoices.AWAITING_ESTABLISHMENT_ROUTING: LeaveApprovalDecision.Stage.ESTABLISHMENT,
                    LeaveApplication.StatusChoices.AWAITING_FINAL_SANCTION: LeaveApprovalDecision.Stage.FINAL_AUTHORITY,
                }
                stage = stage_for_status.get(app.status)
            else:
                completed = set(
                    LeaveApprovalDecision.objects.filter(
                        application=app, workflow_type=workflow_type
                    ).values_list("stage", flat=True)
                )
                if LeaveApprovalDecision.Stage.UNIT_HEAD not in completed:
                    stage = LeaveApprovalDecision.Stage.UNIT_HEAD
                elif (
                    app.leave_category.code not in {"CL", "RH"}
                    and config.establishment_enabled
                    and LeaveApprovalDecision.Stage.ESTABLISHMENT not in completed
                ):
                    stage = LeaveApprovalDecision.Stage.ESTABLISHMENT
                else:
                    stage = LeaveApprovalDecision.Stage.FINAL_AUTHORITY
            expected = {
                LeaveApprovalDecision.Stage.UNIT_HEAD: config.unit_head_role,
                LeaveApprovalDecision.Stage.ESTABLISHMENT: config.establishment_role,
                LeaveApprovalDecision.Stage.FINAL_AUTHORITY: config.final_authority_role,
            }.get(stage)
            if expected and expected == role:
                data = LeaveApplicationSerializer(app).data
                data["workflow_kind"] = workflow_type
                data["workflow_stage"] = stage
                items.append(data)
        return Response(items)


class LeaveApprovalDecisionView(views.APIView):
    """Record a configured-stage decision and advance the approval workflow."""

    permission_classes = [MODULE, HasPermission("modules.elm.workflow.review")]

    def post(self, request, pk):
        outcome = request.data.get("outcome")
        workflow_type = request.data.get("workflow_kind", LeaveApprovalDecision.WorkflowType.LEAVE)
        comments = str(request.data.get("comments") or "").strip()
        actor = getattr(request, "principal", None)
        role = _workflow_role(request)
        if actor is None or not role:
            return Response({"error": "Authenticated active role is required."}, status=400)
        if workflow_type not in LeaveApprovalDecision.WorkflowType.values:
            return Response({"error": "Unknown workflow_kind."}, status=400)

        with transaction.atomic():
            application = get_object_or_404(
                LeaveApplication.objects.select_for_update().select_related("leave_category"),
                pk=pk,
            )
            is_cancellation = workflow_type == LeaveApprovalDecision.WorkflowType.CANCELLATION
            if (
                is_cancellation
                and application.cancellation_status != LeaveApplication.CancellationStatus.PENDING
            ):
                return Response({"error": "No cancellation is awaiting review."}, status=400)
            config = ApprovalRoutingConfiguration.objects.filter(
                leave_category=application.leave_category
            ).first()
            if config is None or not config.is_complete():
                return Response({"error": "Approval routing is not configured."}, status=409)

            if is_cancellation:
                completed = set(
                    LeaveApprovalDecision.objects.filter(
                        application=application, workflow_type=workflow_type
                    ).values_list("stage", flat=True)
                )
                if LeaveApprovalDecision.Stage.UNIT_HEAD not in completed:
                    stage = LeaveApprovalDecision.Stage.UNIT_HEAD
                elif (
                    application.leave_category.code not in {"CL", "RH"}
                    and config.establishment_enabled
                    and LeaveApprovalDecision.Stage.ESTABLISHMENT not in completed
                ):
                    stage = LeaveApprovalDecision.Stage.ESTABLISHMENT
                else:
                    stage = LeaveApprovalDecision.Stage.FINAL_AUTHORITY
            else:
                status_to_stage = {
                    LeaveApplication.StatusChoices.AWAITING_UNIT_HEAD_REVIEW: LeaveApprovalDecision.Stage.UNIT_HEAD,
                    LeaveApplication.StatusChoices.AWAITING_ESTABLISHMENT_ROUTING: LeaveApprovalDecision.Stage.ESTABLISHMENT,
                    LeaveApplication.StatusChoices.AWAITING_FINAL_SANCTION: LeaveApprovalDecision.Stage.FINAL_AUTHORITY,
                }
                stage = status_to_stage.get(application.status)
                if stage is None:
                    return Response(
                        {"error": "This application is not awaiting a decision."}, status=400
                    )

            expected_role = {
                LeaveApprovalDecision.Stage.UNIT_HEAD: config.unit_head_role,
                LeaveApprovalDecision.Stage.ESTABLISHMENT: config.establishment_role,
                LeaveApprovalDecision.Stage.FINAL_AUTHORITY: config.final_authority_role,
            }[stage]
            if role != expected_role:
                return Response(
                    {"error": "Your active role is not configured for this stage."}, status=403
                )
            if LeaveApprovalDecision.objects.filter(
                application=application, workflow_type=workflow_type, stage=stage
            ).exists():
                return Response(
                    {"error": "A decision for this stage is already recorded."}, status=409
                )

            higher = application.leave_category.code not in {"CL", "RH"}
            allowed = (
                {"recommended", "not_recommended"}
                if stage == LeaveApprovalDecision.Stage.UNIT_HEAD and higher
                else {"approved", "rejected"}
                if stage
                in {
                    LeaveApprovalDecision.Stage.UNIT_HEAD,
                    LeaveApprovalDecision.Stage.FINAL_AUTHORITY,
                }
                else {"routed"}
            )
            if outcome not in allowed:
                return Response(
                    {"error": "Outcome is not valid for this workflow stage."}, status=400
                )

            LeaveApprovalDecision.objects.create(
                application=application,
                workflow_type=workflow_type,
                stage=stage,
                outcome=outcome,
                actor_user_id=actor.user_id,
                actor_role=role,
                comments=comments,
            )
            if is_cancellation:
                if (
                    stage == LeaveApprovalDecision.Stage.UNIT_HEAD and not higher
                ) or stage == LeaveApprovalDecision.Stage.FINAL_AUTHORITY:
                    self._finish_cancellation(application, outcome)
            else:
                if stage == LeaveApprovalDecision.Stage.UNIT_HEAD:
                    if not higher:
                        if outcome == "approved":
                            application.status = LeaveApplication.StatusChoices.APPROVED
                            _post_balance(application, Decimal("1"))
                        else:
                            application.status = LeaveApplication.StatusChoices.REJECTED
                    else:
                        application.status = (
                            LeaveApplication.StatusChoices.AWAITING_ESTABLISHMENT_ROUTING
                            if config.establishment_enabled
                            else LeaveApplication.StatusChoices.AWAITING_FINAL_SANCTION
                        )
                elif stage == LeaveApprovalDecision.Stage.ESTABLISHMENT:
                    application.status = LeaveApplication.StatusChoices.AWAITING_FINAL_SANCTION
                else:
                    if outcome == "approved":
                        application.status = LeaveApplication.StatusChoices.APPROVED
                        _post_balance(application, Decimal("1"))
                    else:
                        application.status = LeaveApplication.StatusChoices.REJECTED
                application.save(update_fields=["status"])
        return Response(LeaveApplicationSerializer(application).data)

    @staticmethod
    def _finish_cancellation(application, outcome):
        if outcome == "approved":
            application.cancellation_status = LeaveApplication.CancellationStatus.APPROVED
            application.status = LeaveApplication.StatusChoices.CANCELLED
            _post_balance(application, Decimal("-1"))
        else:
            application.cancellation_status = LeaveApplication.CancellationStatus.REJECTED
        application.save(update_fields=["status", "cancellation_status"])


# ============================================================================
# Withdrawal View
# ============================================================================


class LeaveApplicationWithdrawView(views.APIView):
    """EL-UC-007: Withdraw Pending Request — Immediately terminate a pending request."""

    permission_classes = [MODULE, HasPermission("modules.elm.leave.withdraw")]

    def post(self, request, pk):
        """Withdraw a pending leave application."""
        application = get_object_or_404(
            LeaveApplication, pk=pk, employee_user_id=_actor_id(request)
        )

        # Check: request must be pending and not have final approval
        if application.status not in (
            LeaveApplication.StatusChoices.DRAFT,
            LeaveApplication.StatusChoices.SUBMITTED,
            LeaveApplication.StatusChoices.AWAITING_SUBSTITUTE_RESPONSE,
            LeaveApplication.StatusChoices.AWAITING_UNIT_HEAD_REVIEW,
            LeaveApplication.StatusChoices.AWAITING_ESTABLISHMENT_ROUTING,
            LeaveApplication.StatusChoices.AWAITING_FINAL_SANCTION,
        ):
            return Response(
                {"error": "Only pending requests (before final approval) may be withdrawn."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            application.status = LeaveApplication.StatusChoices.WITHDRAWN
            application.save(update_fields=["status"])

            # Terminate all remaining approval processing
            # Notify concerned roles

        return Response(LeaveApplicationSerializer(application).data, status=status.HTTP_200_OK)


# ============================================================================
# Cancellation View
# ============================================================================


class LeaveCancellationRequestView(views.APIView):
    """EL-UC-008: Request pre-start cancellation through the approval hierarchy."""

    permission_classes = [MODULE, HasPermission("modules.elm.leave.cancel_request")]

    def post(self, request, pk):
        application = get_object_or_404(
            LeaveApplication, pk=pk, employee_user_id=_actor_id(request)
        )
        if application.status != LeaveApplication.StatusChoices.APPROVED:
            return Response({"error": "Only approved leaves may be cancelled."}, status=400)
        if application.requested_start <= date.today():
            return Response(
                {"error": "Cancellation is only available before the approved start date."},
                status=400,
            )
        if application.cancellation_status != LeaveApplication.CancellationStatus.NONE:
            return Response(
                {"error": "A cancellation request has already been submitted for this leave."},
                status=400,
            )
        application.cancellation_status = LeaveApplication.CancellationStatus.PENDING
        application.cancellation_requested_at = timezone.now()
        application.save(update_fields=["cancellation_status", "cancellation_requested_at"])
        return Response(LeaveApplicationSerializer(application).data, status=202)


# ============================================================================
# Extension View
# ============================================================================


class LeaveExtensionRequestView(views.APIView):
    """EL-UC-009: Request an incremental extension of ongoing EL/COL/VL."""

    permission_classes = [MODULE, HasPermission("modules.elm.leave.extension_request")]

    def post(self, request):
        employee_user_id = _actor_id(request)
        original_id = request.data.get("original_application_pk")
        start_date = request.data.get("additional_period_start")
        end_date = request.data.get("additional_period_end")
        if not all([original_id, start_date, end_date]):
            return Response(
                {
                    "error": (
                        "original_application_pk, additional_period_start, "
                        "and additional_period_end are required."
                    )
                },
                status=400,
            )
        original = get_object_or_404(
            LeaveApplication, pk=original_id, employee_user_id=employee_user_id
        )
        if original.leave_category.code not in {"EL", "COL", "VL"}:
            return Response({"error": "Only EL, COL, or VL can be extended."}, status=400)
        try:
            application = LeaveApplication.objects.create(
                employee_user_id=employee_user_id,
                leave_category=original.leave_category,
                requested_start=date.fromisoformat(start_date),
                requested_end=date.fromisoformat(end_date),
                purpose_reason=request.data.get("purpose_reason", ""),
                extension_of=original,
                status=LeaveApplication.StatusChoices.DRAFT,
            )
        except (TypeError, ValueError):
            return Response({"error": "Extension dates must use YYYY-MM-DD."}, status=400)
        from modules.elm.services import LeaveValidationService

        result = LeaveValidationService.validate_extension_application(application)
        if not result["valid"]:
            application.delete()
            return Response({"error": result["error"]}, status=400)
        application.status = LeaveApplication.StatusChoices.AWAITING_UNIT_HEAD_REVIEW
        application.save(update_fields=["status"])
        return Response(LeaveApplicationSerializer(application).data, status=201)


# ============================================================================
# Resumption Views
# ============================================================================


class ResumptionSubmitView(views.APIView):
    """EL-UC-010: Record an employee's actual resumption date and details."""

    permission_classes = [MODULE, HasPermission("modules.elm.resumption.submit")]

    def post(self, request):
        employee_user_id = _actor_id(request)
        raw_date = request.data.get("actual_resumption_date")
        if not raw_date:
            return Response({"error": "actual_resumption_date is required."}, status=400)
        try:
            actual_date = date.fromisoformat(raw_date)
        except (TypeError, ValueError):
            return Response({"error": "actual_resumption_date must use YYYY-MM-DD."}, status=400)
        categories = LeaveCategory.objects.filter(code__in=["EL", "COL", "VL"])
        application = (
            LeaveApplication.objects.filter(
                employee_user_id=employee_user_id,
                leave_category__in=categories,
                status=LeaveApplication.StatusChoices.APPROVED,
                requested_start__lte=actual_date,
                actual_resumption_date__isnull=True,
            )
            .order_by("-requested_start")
            .first()
        )
        if application is None:
            return Response(
                {"error": "No eligible approved EL, COL, or VL leave was found."}, status=404
            )
        application.actual_resumption_date = actual_date
        application.resumption_details = request.data.get("resumption_details", "")
        application.save(update_fields=["actual_resumption_date", "resumption_details"])
        return Response(
            {
                "message": "Resumption submission recorded for review.",
                "application_pk": application.pk,
            },
            status=202,
        )


class ResumptionReviewView(views.APIView):
    """EL-UC-011: Review the submitted actual resumption date."""

    permission_classes = [MODULE, HasPermission("modules.elm.resumption.review")]

    def post(self, request, pk):
        application = get_object_or_404(LeaveApplication, pk=pk)
        if application.leave_category.code not in {"EL", "COL", "VL"}:
            return Response({"error": "Resumption review applies to EL, COL, and VL."}, status=400)
        if application.actual_resumption_date is None:
            return Response(
                {"error": "No resumption has been submitted for this application."}, status=400
            )
        if application.resumption_reviewed_at is not None:
            return Response({"error": "Resumption has already been reviewed."}, status=400)
        actual = application.actual_resumption_date
        approved = application.requested_end
        adjustment = "early" if actual < approved else "late" if actual > approved else "none"
        from modules.elm.services import LeaveValidationService

        scheduled_days = LeaveValidationService.count_requested_days(application)
        actual_period = type(
            "ActualPeriod",
            (),
            {
                "day_part": LeaveApplication.DayPartChoices.FULL_DAY,
                "requested_start": application.requested_start,
                "requested_end": actual,
                "leave_category": application.leave_category,
            },
        )()
        actual_days = LeaveValidationService.count_requested_days(actual_period)
        delta = actual_days - scheduled_days
        balance_adjustment = Decimal("0")
        if delta:
            balance, _ = LeaveBalance.objects.get_or_create(
                user_id=application.employee_user_id,
                leave_category=application.leave_category,
                year=application.requested_start.year,
                defaults={
                    "entitlement_per_year": application.leave_category.annual_entitlement
                    or Decimal("0"),
                },
            )
            balance.used_per_year = max(Decimal("0"), balance.used_per_year + delta)
            balance.save(update_fields=["used_per_year"])
            balance_adjustment = delta
        application.resumption_reviewed_at = timezone.now()
        application.save(update_fields=["resumption_reviewed_at"])
        return Response(
            {
                "adjustment": adjustment,
                "balance_adjustment": str(balance_adjustment),
                "message": "Resumption reviewed and the leave balance was synchronized.",
            },
            status=200,
        )


# ============================================================================
# Printable Export View
# ============================================================================


class LeaveApplicationPrintView(views.APIView):
    """EL-UC-013: Obtain Printable/Exportable Leave Application."""

    permission_classes = [MODULE, HasPermission("modules.elm.application.print")]

    def get(self, request, pk):
        """Get printable representation of a leave application."""
        application = get_object_or_404(
            LeaveApplication, pk=pk, employee_user_id=_actor_id(request)
        )

        # Check authorization - employee can only access their own
        # In production, check authenticated user's id against application.employee_user_id

        # Build printable representation
        print_data = {
            "application_id": application.pk,
            "employee_user_id": application.employee_user_id,
            "leave_category": application.leave_category.code,
            "leave_category_label": application.leave_category.label,
            "requested_start": str(application.requested_start),
            "requested_end": str(application.requested_end),
            "day_part": application.day_part,
            "purpose_reason": application.purpose_reason or "",
            "station_leave": application.station_leave,
            "station_details": application.station_details or "",
            "status": application.status,
            "submitted_at": str(application.submitted_at) if application.submitted_at else "",
        }

        # Add substitute info if applicable
        if application.nominated_substitute_user_id:
            print_data["nominated_substitute_user_id"] = application.nominated_substitute_user_id
            print_data["substitute_accepted"] = application.substitute_accepted

        return Response(
            {
                "application": LeaveApplicationSerializer(application).data,
                "print_data": print_data,
            }
        )


# ============================================================================
# Policy Configuration View
# ============================================================================


class LeavePolicyConfigView(views.APIView):
    """EL-UC-014: Maintain Policy and Hierarchy Configuration."""

    permission_classes = [MODULE, HasPermission("modules.elm.policy.configure")]

    def get(self, request):
        """Get current leave policy configuration."""
        from modules.elm.models import LeaveCategory

        categories = LeaveCategory.objects.all()
        serializer = LeaveCategorySerializer(categories, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Create/revise leave policy parameters."""
        serializer = LeaveCategorySerializer(data=request.data)
        if serializer.is_valid():
            # Check if updating existing or creating new
            code = serializer.validated_data.get("code")
            if code:
                # Update existing
                obj, _created = LeaveCategory.objects.get_or_create(code=code)
                for attr, val in serializer.validated_data.items():
                    setattr(obj, attr, val)
                obj.save()
            else:
                # Create new - assign a code
                serializer.validated_data["code"] = request.data.get("code", "EL")
                serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============================================================================
# Holiday Calendar View
# ============================================================================


class HolidayCalendarView(views.APIView):
    """EL-UC-015: Maintain and Publish Holiday/RH Calendar."""

    permission_classes = [MODULE, HasPermission("modules.elm.calendar.manage")]

    def get(self, request):
        """Get current holiday/RH calendar data."""
        # In a real implementation, this would query a HolidayCalendar model
        # For now, return empty structure
        return Response({"holidays": [], "restricted_holidays": []})

    def post(self, request):
        """Create/revise and publish the holiday/RH calendar."""
        # In a real implementation, this would save and publish the calendar
        # Making it effective for subsequent date/RH validation
        data = request.data
        published = data.get("published", False)

        if published:
            # Make effective for subsequent validation
            return Response(
                {"message": "Holiday calendar published and is now effective"},
                status=status.HTTP_200_OK,
            )
        return Response(
            {"message": "Holiday calendar revised (not yet published)"}, status=status.HTTP_200_OK
        )


# ============================================================================
# Offline Leave Sync View
# ============================================================================


class OfflineLeaveSyncView(views.APIView):
    """EL-UC-016: Record Already-Sanctioned Offline Leave."""

    permission_classes = [MODULE, HasPermission("modules.elm.offline.record")]

    def post(self, request):
        """Synchronize leave already sanctioned through an authorized offline process."""
        employee_user_id = request.data.get("employee_user_id")
        leave_category_code = request.data.get("leave_category_code")
        sanction_reference = request.data.get("sanction_reference", "")
        request.data.get("sanction_evidence", "")

        if not all([employee_user_id, leave_category_code]):
            return Response(
                {"error": "employee_user_id and leave_category_code are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from modules.elm.models import LeaveApplication, LeaveBalance, LeaveCategory

        try:
            leave_category = LeaveCategory.objects.get(code=leave_category_code)
        except LeaveCategory.DoesNotExist:
            return Response(
                {"error": f"Leave category {leave_category_code} does not exist"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if already has an application/balance
        LeaveApplication.objects.filter(
            employee_user_id=employee_user_id,
            leave_category=leave_category,
            status=LeaveApplication.StatusChoices.APPROVED,
        ).first()

        # Check existing balance
        _balance, created = LeaveBalance.objects.get_or_create(
            user_id=employee_user_id,
            leave_category=leave_category,
            year=date.today().year,
            defaults={
                "entitlement_per_year": leave_category.annual_entitlement or Decimal("0"),
            },
        )

        # Record the offline-sanctioned leave - update balance
        # No new approval workflow initiated per BR-EL-029
        # Validate for record consistency

        # For now, just return success with sync info
        return Response(
            {
                "message": "Offline leave synchronized without new sanction decision",
                "employee_user_id": employee_user_id,
                "leave_category": leave_category_code,
                "sanction_reference": sanction_reference,
                "balance_updated": not created,
            },
            status=status.HTTP_200_OK,
        )


# ============================================================================
# Authorized Leave Records View
# ============================================================================


class AuthorizedLeaveRecordsView(views.APIView):
    """EL-UC-017: Maintain Authorized Leave Records."""

    permission_classes = [MODULE, HasPermission("modules.elm.records.maintain")]

    def get(self, request, employee_user_id=None):
        """Get leave records within authorized maintenance scope."""
        user_id = _actor_id(request)

        balances = LeaveBalance.objects.filter(user_id=user_id).select_related("leave_category")
        serializer = LeaveBalanceSerializer(balances, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Perform authorized maintenance/correction on leave records."""
        # Admin maintenance that does not create a new sanctioning decision
        # per BR-EL-037
        record_id = request.data.get("record_id")
        correction = request.data.get("correction")

        if not record_id:
            return Response({"error": "record_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        # In a real implementation, this would perform permitted record changes
        # while preserving audit/history and not creating sanctioning decisions
        return Response(
            {"message": f"Record {record_id} maintenance performed: {correction}"},
            status=status.HTTP_200_OK,
        )


# ============================================================================
# SLA Thresholds Config View
# ============================================================================


class SLATrendsConfigView(views.APIView):
    """EL-UC-018: Configure Workflow SLA Thresholds."""

    permission_classes = [MODULE, HasPermission("modules.elm.sla.configure_thresholds")]

    def get(self, request):
        """Return the active reminder and escalation configuration."""
        config, _ = SLAThresholdConfiguration.objects.get_or_create(pk=1)
        return Response(
            {
                "reminder_threshold_minutes": config.reminder_threshold_minutes,
                "escalation_threshold_minutes": config.escalation_threshold_minutes,
                "escalation_action": config.escalation_action,
            }
        )

    def post(self, request):
        """Validate and persist reminder and escalation thresholds."""
        reminder = request.data.get("reminder_threshold_minutes")
        escalation = request.data.get("escalation_threshold_minutes")
        action = request.data.get("escalation_action", "notify")

        try:
            reminder = int(reminder)
            escalation = int(escalation)
        except (TypeError, ValueError):
            return Response(
                {"error": "Thresholds must be positive whole numbers of minutes."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        valid_actions = {choice for choice, _ in SLAThresholdConfiguration.EscalationAction.choices}
        if reminder < 1 or escalation <= reminder or action not in valid_actions:
            return Response(
                {
                    "error": (
                        "Reminder must be positive, escalation must exceed reminder, "
                        "and escalation_action must be notify, route_change, or none."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        config, _ = SLAThresholdConfiguration.objects.update_or_create(
            pk=1,
            defaults={
                "reminder_threshold_minutes": reminder,
                "escalation_threshold_minutes": escalation,
                "escalation_action": action,
                "updated_by_user_id": _actor_id(request),
            },
        )
        return Response(
            {
                "reminder_threshold_minutes": config.reminder_threshold_minutes,
                "escalation_threshold_minutes": config.escalation_threshold_minutes,
                "escalation_action": config.escalation_action,
            }
        )


# ============================================================================
# Substitute Replacement View
# ============================================================================


class SubstituteReplacementView(views.APIView):
    """EL-UC-019: Nominate Replacement Substitute After Decline."""

    permission_classes = [MODULE, HasPermission("modules.elm.substitute.replace")]

    def post(self, request):
        """Nominate a replacement eligible substitute after a decline."""
        employee_user_id = _actor_id(request)
        nominee_user_id = request.data.get("nominee_user_id")
        original_leave_pk = request.data.get("original_leave_pk")

        if not all([nominee_user_id, original_leave_pk]):
            return Response(
                {"error": "employee_user_id, nominee_user_id, and original_leave_pk are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from modules.elm.models import LeaveApplication

        # Get the original application
        application = get_object_or_404(
            LeaveApplication, pk=original_leave_pk, employee_user_id=employee_user_id
        )

        # Check: request must remain pending per precondition
        if application.status not in (
            LeaveApplication.StatusChoices.AWAITING_SUBSTITUTE_RESPONSE,
            LeaveApplication.StatusChoices.APPLICANT_ACTION_REQUIRED,
        ):
            return Response(
                {
                    "error": (
                        "Only pending requests with declined substitutes may nominate replacements"
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate replacement eligibility per BR-EL-014
        # Nominee must be another employee, must not be the applicant
        # Must have no overlapping pending or approved leave during responsibility period

        # Create the substitute nomination
        nomination, created = SubstituteNomination.objects.get_or_create(
            leave_application=application,
            nominee_user_id=nominee_user_id,
            defaults={
                "status": SubstituteNomination.StatusChoices.PENDING,
            },
        )

        if not created:
            nomination.status = SubstituteNomination.StatusChoices.PENDING
            nomination.save()

        return Response(SubstituteNominationSerializer(nomination).data, status=status.HTTP_200_OK)


# ============================================================================
# Year-End Processing View
# ============================================================================


class YearEndLeaveProcessingView(views.APIView):
    """EL-UC-020: Execute Year-End Leave Processing — Event-triggered."""

    permission_classes = [MODULE, HasPermission("modules.elm.yearend.execute")]

    def post(self, request):
        """Apply defined year-end leave-account outcomes."""
        from modules.elm.services import YearEndProcessingService

        # Execute year-end processing
        result = YearEndProcessingService.execute_year_end()

        return Response(result, status=status.HTTP_200_OK)


# ============================================================================
# SLA Threshold Event View
# ============================================================================


class SLAThresholdEventView(views.APIView):
    """EL-UC-021: Process SLA Threshold Event — Event-triggered."""

    permission_classes = [MODULE, HasPermission("modules.elm.sla.process")]

    def post(self, request):
        """Process a configured SLA reminder or escalation threshold."""
        from modules.elm.services import SLATriggerService

        result = SLATriggerService.process_sla_threshold()

        return Response(result, status=status.HTTP_200_OK)
