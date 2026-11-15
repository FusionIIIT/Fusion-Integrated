import csv
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.leave_elm.api import serializers as s
from modules.leave_elm.models import (
    ApprovalRecord,
    CancellationRecord,
    ExtensionRecord,
    HolidayCalendar,
    LeaveApplication,
    LeaveApplicationTransition,
    LeaveBalance,
    LeaveBalanceTransaction,
    LeaveCategory,
    OfflineSanctionedLeaveRecord,
    PolicyConfiguration,
    ResumptionRecord,
    SLAConfiguration,
    Substitute,
)
from modules.leave_elm.services import (
    ACTIVE_STATUSES,
    actor_has_assigned_role,
    apply_balance_delta,
    chargeable_days_by_year,
    next_sanctioning_role,
    review_application,
    routing_configuration,
    submit_application,
    validate_application,
)

MODULE = HasModuleGrant("leave_elm")
P_VIEW = "leave_elm.application.view_self"
P_CREATE = "leave_elm.application.create"
P_WITHDRAW = "leave_elm.application.withdraw"
P_REVIEW = "leave_elm.application.review"


def _actor(request):
    return request.principal


def _own_application(request, pk):
    row = LeaveApplication.objects.filter(pk=pk, user_id=_actor(request).user_id).first()
    if row is None:
        raise NotFound("No such leave application.")
    return row


class LeaveCategoryListView(APIView):
    permission_classes = [MODULE, HasPermission(P_VIEW, P_CREATE)]

    def get(self, request):
        rows = LeaveCategory.objects.filter(is_active=True).order_by("code")
        return Response({"results": s.LeaveCategorySerializer(rows, many=True).data})


class LeaveApplicationListView(APIView):
    permission_classes = [MODULE, HasPermission(P_VIEW, P_CREATE)]

    def get(self, request):
        rows = (
            LeaveApplication.objects.filter(user_id=_actor(request).user_id)
            .select_related("category")
            .order_by("-created_at")
        )
        return Response({"results": s.LeaveApplicationSerializer(rows, many=True).data})

    def post(self, request):
        self.check_permissions(request)
        self.permission_classes = [MODULE, HasPermission(P_CREATE)]
        self.check_permissions(request)
        payload = s.LeaveApplicationCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        application = submit_application(
            user_id=_actor(request).user_id,
            applicant_role=_actor(request).active_role or "",
            **payload.validated_data,
        )
        return Response(
            s.LeaveApplicationSerializer(application).data, status=status.HTTP_201_CREATED
        )


class LeaveApplicationDetailView(APIView):
    permission_classes = [MODULE, HasPermission(P_VIEW)]

    def get(self, request, pk):
        application = _own_application(request, pk)
        history = application.transitions.order_by("at")
        decisions = application.approval_records.order_by("created_at")
        data = s.LeaveApplicationSerializer(application).data
        data["history"] = [
            {"from": row.from_status, "to": row.to_status, "at": row.at, "reason": row.reason}
            for row in history
        ]
        data["decisions"] = [
            {"outcome": row.outcome, "comments": row.comments, "at": row.created_at}
            for row in decisions
        ]
        return Response(data)


class LeaveBalanceListView(APIView):
    permission_classes = [MODULE, HasPermission(P_VIEW)]

    def get(self, request):
        rows = (
            LeaveBalance.objects.filter(user_id=_actor(request).user_id)
            .select_related("category")
            .order_by("year", "category__code")
        )
        results = []
        for balance in rows:
            item = dict(s.LeaveBalanceSerializer(balance).data)
            item["transactions"] = [
                {
                    "type": transaction.transaction_type,
                    "amount": transaction.amount,
                    "note": transaction.note,
                    "at": transaction.at,
                }
                for transaction in balance.transactions.order_by("-at")
            ]
            results.append(item)
        return Response({"results": results})


class LeaveApplicationExportView(APIView):
    permission_classes = [MODULE, HasPermission(P_VIEW)]

    def get(self, request, pk):
        application = _own_application(request, pk)
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="leave-application-{application.pk}.csv"'
        )
        writer = csv.writer(response)
        writer.writerow(
            [
                "Application",
                "Employee",
                "Category",
                "Status",
                "Start",
                "End",
                "Days",
                "Purpose",
                "Station Leave",
                "Destination",
            ]
        )
        writer.writerow(
            [
                application.pk,
                application.user_id,
                application.category.code,
                application.status,
                application.starts_on,
                application.ends_on,
                application.requested_days,
                application.purpose,
                application.station_leave,
                application.station_destination,
            ]
        )
        return response


class LeaveApplicationWithdrawView(APIView):
    permission_classes = [MODULE, HasPermission(P_WITHDRAW)]

    @transaction.atomic
    def post(self, request, pk):
        application = _own_application(request, pk)
        if application.status not in {
            "awaiting_substitute",
            "awaiting_unit_head",
            "awaiting_establishment",
            "awaiting_sanction",
            "awaiting_self_sanction",
            "applicant_action_required",
        }:
            raise ValidationError("Only a pending request can be withdrawn.")
        old = application.status
        application.status = "withdrawn"
        application.save(update_fields=["status", "updated_at"])
        LeaveApplicationTransition.objects.create(
            application=application,
            from_status=old,
            to_status="withdrawn",
            actor_user_id=_actor(request).user_id,
            actor_label="Employee",
        )
        return Response(s.LeaveApplicationSerializer(application).data)


class SubstituteResponseView(APIView):
    permission_classes = [MODULE, HasPermission(P_VIEW)]

    @transaction.atomic
    def post(self, request, pk):
        payload = s.SubstituteResponseSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        assignment = (
            Substitute.objects.filter(
                application_id=pk,
                substitute_user_id=_actor(request).user_id,
                status="pending",
                application__status="awaiting_substitute",
            )
            .select_related("application")
            .first()
        )
        if assignment is None:
            raise NotFound("No pending substitute assignment.")
        response = payload.validated_data["response"]
        assignment.status = response
        assignment.response_at = timezone.now()
        assignment.save(update_fields=["status", "response_at", "updated_at"])
        application = assignment.application
        application.substitute_response = response
        if response == "accepted":
            if application.applicant_role.lower() == "director":
                application.status = "awaiting_self_sanction"
                application.assigned_role = "director"
            else:
                application.status = "awaiting_unit_head"
                application.assigned_role = "unit_head"
        else:
            application.status = "applicant_action_required"
            application.assigned_role = ""
        application.save(
            update_fields=["substitute_response", "status", "assigned_role", "updated_at"]
        )
        LeaveApplicationTransition.objects.create(
            application=application,
            from_status="awaiting_substitute",
            to_status=application.status,
            actor_user_id=_actor(request).user_id,
            actor_label="Substitute",
        )
        return Response(s.LeaveApplicationSerializer(application).data)


class LeaveReviewView(APIView):
    permission_classes = [MODULE, HasPermission(P_REVIEW)]

    @transaction.atomic
    def post(self, request, pk):
        application = (
            LeaveApplication.objects.select_for_update()
            .filter(pk=pk)
            .select_related("category")
            .first()
        )
        if application is None:
            raise NotFound("No such leave application.")
        payload = s.ReviewSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        application = review_application(
            application=application, actor=_actor(request), **payload.validated_data
        )
        return Response(s.LeaveApplicationSerializer(application).data)


class EstablishmentRouteView(APIView):
    permission_classes = [MODULE, HasPermission(P_REVIEW)]

    @transaction.atomic
    def post(self, request, kind, pk):
        if kind == "application":
            item = (
                LeaveApplication.objects.select_for_update()
                .filter(pk=pk, status="awaiting_establishment")
                .select_related("category")
                .first()
            )
        elif kind == "cancellation":
            item = (
                CancellationRecord.objects.select_for_update()
                .filter(pk=pk, status="awaiting_establishment")
                .select_related("application", "application__category")
                .first()
            )
        elif kind == "extension":
            item = (
                ExtensionRecord.objects.select_for_update()
                .filter(pk=pk, status="awaiting_establishment")
                .select_related("application", "application__category")
                .first()
            )
        else:
            raise NotFound("Unknown leave workflow type.")
        if item is None:
            raise NotFound("No request is awaiting Establishment routing.")
        if not actor_has_assigned_role(_actor(request), item.assigned_role):
            raise ValidationError("This request is assigned to another role.")
        application = item if kind == "application" else item.application
        item.status = "awaiting_sanction"
        from modules.leave_elm.services import next_sanctioning_role

        item.assigned_role = next_sanctioning_role(application.category)
        item.save(update_fields=["status", "assigned_role", "updated_at"])
        if kind == "application":
            LeaveApplicationTransition.objects.create(
                application=item,
                from_status="awaiting_establishment",
                to_status="awaiting_sanction",
                actor_user_id=_actor(request).user_id,
                actor_label=_actor(request).active_role or "",
                reason="Establishment routing completed",
            )
        return Response({"id": item.pk, "status": item.status, "assigned_role": item.assigned_role})


class LeaveCancellationView(APIView):
    permission_classes = [MODULE, HasPermission(P_CREATE)]

    @transaction.atomic
    def post(self, request, pk):
        application = _own_application(request, pk)
        if application.status != "approved" or application.starts_on <= timezone.localdate():
            raise ValidationError("Only approved leave that has not started can be cancelled.")
        if application.cancellations.filter(
            status__in={"pending", "awaiting_establishment", "awaiting_sanction"}
        ).exists():
            raise ValidationError("A cancellation request is already pending.")
        payload = s.CancellationCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = CancellationRecord.objects.create(
            application=application,
            requested_by_user_id=_actor(request).user_id,
            **payload.validated_data,
        )
        return Response({"id": row.pk, "status": row.status}, status=status.HTTP_201_CREATED)


class LeaveExtensionView(APIView):
    permission_classes = [MODULE, HasPermission(P_CREATE)]

    @transaction.atomic
    def post(self, request, pk):
        application = _own_application(request, pk)
        today = timezone.localdate()
        if (
            application.category.code not in {"EL", "COL", "VL"}
            or application.status != "approved"
            or not application.starts_on <= today <= application.ends_on
        ):
            raise ValidationError("Extensions are supported for ongoing EL, COL or VL.")
        if application.extensions.filter(
            status__in={
                "pending",
                "awaiting_substitute",
                "awaiting_establishment",
                "awaiting_sanction",
                "applicant_action_required",
            }
        ).exists():
            raise ValidationError("An extension request is already pending.")
        payload = s.ExtensionCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        if data["additional_starts_on"] <= application.ends_on:
            raise ValidationError("The extension must start after the approved period.")
        substitute_id = data.pop("substitute_user_id", None)
        if substitute_id == application.user_id:
            raise ValidationError("You cannot nominate yourself as substitute.")
        days_by_year = chargeable_days_by_year(
            application.category, data["additional_starts_on"], data["additional_ends_on"]
        )
        days = sum(days_by_year.values())
        validate_application(
            user_id=application.user_id,
            category=application.category,
            starts_on=data["additional_starts_on"],
            ends_on=data["additional_ends_on"],
            half_day="full",
            applicant_role=application.applicant_role,
        )
        if (
            substitute_id
            and LeaveApplication.objects.filter(
                user_id=substitute_id,
                status__in=ACTIVE_STATUSES,
                starts_on__lte=data["additional_ends_on"],
                ends_on__gte=data["additional_starts_on"],
            ).exists()
        ):
            raise ValidationError("The nominated substitute has overlapping leave.")
        if (
            substitute_id
            and ExtensionRecord.objects.filter(
                substitute_user_id=substitute_id,
                status__in={"pending", "awaiting_substitute", "awaiting_sanction"},
                additional_starts_on__lte=data["additional_ends_on"],
                additional_ends_on__gte=data["additional_starts_on"],
            ).exists()
        ):
            raise ValidationError("The nominated substitute has an overlapping extension.")
        row = ExtensionRecord.objects.create(
            application=application,
            requested_by_user_id=_actor(request).user_id,
            additional_days=days,
            additional_days_by_year={str(year): str(value) for year, value in days_by_year.items()},
            status="awaiting_substitute" if substitute_id else "pending",
            substitute_user_id=substitute_id,
            **data,
        )
        return Response({"id": row.pk, "status": row.status}, status=status.HTTP_201_CREATED)


class LeaveResumptionView(APIView):
    permission_classes = [MODULE, HasPermission(P_CREATE)]

    def post(self, request, pk):
        application = _own_application(request, pk)
        if application.category.code not in {"EL", "COL", "VL"}:
            raise ValidationError("Resumption applies to EL, COL or VL.")
        if application.status != "approved":
            raise ValidationError("Resumption requires approved leave.")
        if application.resumptions.filter(status="submitted").exists():
            raise ValidationError("A resumption review is already pending.")
        payload = s.ResumptionCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = ResumptionRecord.objects.create(
            application=application,
            user_id=_actor(request).user_id,
            assigned_role=(
                "director"
                if application.applicant_role.lower() == "director"
                else next_sanctioning_role(application.category)
            ),
            **payload.validated_data,
        )
        return Response({"id": row.pk, "status": row.status}, status=status.HTTP_201_CREATED)


class ReplacementSubstituteView(APIView):
    permission_classes = [MODULE, HasPermission(P_CREATE)]

    def post(self, request, pk):
        application = _own_application(request, pk)
        if application.status != "applicant_action_required":
            raise ValidationError("The request is not awaiting a replacement substitute.")
        payload = s.ReplacementSubstituteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        substitute_id = payload.validated_data["substitute_user_id"]
        if substitute_id == application.user_id:
            raise ValidationError("You cannot nominate yourself as substitute.")
        Substitute.objects.filter(application=application, status="declined").update(
            status="replaced"
        )
        Substitute.objects.create(
            application=application, user_id=application.user_id, substitute_user_id=substitute_id
        )
        application.substitute_user_id = substitute_id
        application.substitute_response = ""
        application.status = "awaiting_substitute"
        application.save(
            update_fields=["substitute_user_id", "substitute_response", "status", "updated_at"]
        )
        LeaveApplicationTransition.objects.create(
            application=application,
            from_status="applicant_action_required",
            to_status="awaiting_substitute",
            actor_user_id=_actor(request).user_id,
            actor_label="Employee",
        )
        return Response(s.LeaveApplicationSerializer(application).data)


class ExtensionSubstituteResponseView(APIView):
    permission_classes = [MODULE, HasPermission(P_VIEW)]

    def post(self, request, pk):
        record = (
            ExtensionRecord.objects.select_related("application")
            .filter(pk=pk, substitute_user_id=_actor(request).user_id, status="awaiting_substitute")
            .first()
        )
        if record is None:
            raise NotFound("No pending extension substitute assignment.")
        payload = s.SubstituteResponseSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        record.substitute_response = payload.validated_data["response"]
        record.status = (
            "pending" if record.substitute_response == "accepted" else "applicant_action_required"
        )
        record.save(update_fields=["substitute_response", "status", "updated_at"])
        return Response({"id": record.pk, "status": record.status})


class ExtensionReplacementSubstituteView(APIView):
    permission_classes = [MODULE, HasPermission(P_CREATE)]

    def post(self, request, pk):
        record = (
            ExtensionRecord.objects.select_related("application")
            .filter(
                pk=pk,
                requested_by_user_id=_actor(request).user_id,
                status="applicant_action_required",
            )
            .first()
        )
        if record is None:
            raise NotFound("No extension request requires a replacement substitute.")
        payload = s.ReplacementSubstituteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        substitute_id = payload.validated_data["substitute_user_id"]
        application = record.application
        if substitute_id == application.user_id:
            raise ValidationError("You cannot nominate yourself as substitute.")
        if LeaveApplication.objects.filter(
            user_id=substitute_id,
            status__in=ACTIVE_STATUSES,
            starts_on__lte=record.additional_ends_on,
            ends_on__gte=record.additional_starts_on,
        ).exists():
            raise ValidationError("The nominated substitute has overlapping leave.")
        record.substitute_user_id = substitute_id
        record.substitute_response = ""
        record.status = "awaiting_substitute"
        record.save(
            update_fields=["substitute_user_id", "substitute_response", "status", "updated_at"]
        )
        return Response({"id": record.pk, "status": record.status})


class PolicyConfigurationView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.configuration.manage")]

    def get(self, request):
        rows = PolicyConfiguration.objects.select_related("category").order_by("key")
        return Response({"results": s.PolicyConfigurationSerializer(rows, many=True).data})

    def post(self, request):
        payload = s.PolicyConfigurationSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        item = payload.save(updated_by_user_id=_actor(request).user_id)
        return Response(s.PolicyConfigurationSerializer(item).data, status=status.HTTP_201_CREATED)


class PolicyConfigurationDetailView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.configuration.manage")]

    def patch(self, request, pk):
        item = PolicyConfiguration.objects.filter(pk=pk).first()
        if item is None:
            raise NotFound("No such policy configuration.")
        payload = s.PolicyConfigurationSerializer(item, data=request.data, partial=True)
        payload.is_valid(raise_exception=True)
        item = payload.save(updated_by_user_id=_actor(request).user_id)
        return Response(s.PolicyConfigurationSerializer(item).data)


class HolidayCalendarView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.configuration.manage")]

    def get(self, request):
        rows = HolidayCalendar.objects.order_by("-year", "name")
        return Response({"results": s.HolidayCalendarSerializer(rows, many=True).data})

    def post(self, request):
        payload = s.HolidayCalendarSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        calendar = payload.save()
        return Response(s.HolidayCalendarSerializer(calendar).data, status=status.HTTP_201_CREATED)


class HolidayCalendarDetailView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.configuration.manage")]

    def patch(self, request, pk):
        calendar = HolidayCalendar.objects.filter(pk=pk, is_published=False).first()
        if calendar is None:
            raise NotFound("No unpublished holiday calendar to revise.")
        payload = s.HolidayCalendarSerializer(calendar, data=request.data, partial=True)
        payload.is_valid(raise_exception=True)
        calendar = payload.save()
        return Response(s.HolidayCalendarSerializer(calendar).data)


class HolidayCalendarPublishView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.configuration.manage")]

    def post(self, request, pk):
        calendar = HolidayCalendar.objects.filter(pk=pk).first()
        if calendar is None:
            raise NotFound("No such holiday calendar.")
        HolidayCalendar.objects.filter(year=calendar.year, is_published=True).exclude(
            pk=calendar.pk
        ).update(is_published=False)
        calendar.is_published = True
        calendar.published_at = timezone.now()
        calendar.published_by_user_id = _actor(request).user_id
        calendar.save(
            update_fields=["is_published", "published_at", "published_by_user_id", "updated_at"]
        )
        return Response(s.HolidayCalendarSerializer(calendar).data)


class SLAConfigurationView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.configuration.manage")]

    def get(self, request):
        rows = SLAConfiguration.objects.filter(is_active=True).order_by("workflow_name")
        return Response({"results": s.SLAConfigurationSerializer(rows, many=True).data})

    def post(self, request):
        payload = s.SLAConfigurationSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        item = payload.save()
        return Response(s.SLAConfigurationSerializer(item).data, status=status.HTTP_201_CREATED)


class SLAConfigurationDetailView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.configuration.manage")]

    def patch(self, request, pk):
        item = SLAConfiguration.objects.filter(pk=pk).first()
        if item is None:
            raise NotFound("No such SLA configuration.")
        payload = s.SLAConfigurationSerializer(item, data=request.data, partial=True)
        payload.is_valid(raise_exception=True)
        item = payload.save()
        return Response(s.SLAConfigurationSerializer(item).data)


class OfflineSanctionedLeaveView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.records.manage")]

    @transaction.atomic
    def post(self, request):
        payload = s.OfflineLeaveCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = dict(payload.validated_data)
        if data["ends_on"] < data["starts_on"]:
            raise ValidationError("ends_on must not precede starts_on")
        category = data["category"]
        balance = (
            LeaveBalance.objects.select_for_update()
            .filter(user_id=data["user_id"], category=category, year=data["starts_on"].year)
            .first()
        )
        if balance is None:
            raise ValidationError("No leave balance exists for this employee and year.")
        record = OfflineSanctionedLeaveRecord.objects.create(
            **data, recorded_by_user_id=_actor(request).user_id
        )
        balance.used += record.leave_days
        balance.closing_balance -= record.leave_days
        balance.save(update_fields=["used", "closing_balance", "updated_at"])
        LeaveBalanceTransaction.objects.create(
            balance=balance,
            transaction_type="deduction",
            amount=record.leave_days,
            note=f"Offline sanction {record.sanction_reference}",
        )
        return Response({"id": record.pk, "balance_id": balance.pk}, status=status.HTTP_201_CREATED)


class CancellationReviewView(APIView):
    permission_classes = [MODULE, HasPermission(P_REVIEW)]

    @transaction.atomic
    def post(self, request, pk):
        record = (
            CancellationRecord.objects.select_for_update()
            .filter(pk=pk, status__in={"pending", "awaiting_sanction", "awaiting_establishment"})
            .select_related("application", "application__category")
            .first()
        )
        if record is None:
            raise NotFound("No pending cancellation request.")
        payload = s.ReviewSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        outcome = payload.validated_data["outcome"]
        application = record.application
        if not actor_has_assigned_role(_actor(request), record.assigned_role):
            raise ValidationError("This cancellation is assigned to another role.")
        if application.category.code in {"CL", "RH"}:
            if record.status != "pending" or outcome not in {"approved", "rejected"}:
                raise ValidationError("CL/RH cancellation requires a Unit Head final decision.")
        elif record.status == "pending":
            if record.assigned_role != "unit_head" or outcome not in {
                "recommended",
                "not_recommended",
            }:
                raise ValidationError("Unit Head must record a recommendation.")
            route = routing_configuration(application.category)
            establishment_role = route.get("establishment_role")
            if establishment_role:
                record.status = "awaiting_establishment"
                record.assigned_role = establishment_role
            else:
                from modules.leave_elm.services import next_sanctioning_role

                record.status = "awaiting_sanction"
                record.assigned_role = next_sanctioning_role(application.category)
            record.save(update_fields=["status", "assigned_role", "updated_at"])
            ApprovalRecord.objects.create(
                application=application,
                actor_user_id=_actor(request).user_id,
                actor_role=_actor(request).active_role or "",
                outcome=outcome,
                comments=f"Cancellation #{record.pk}: {payload.validated_data['comments']}",
            )
            return Response({"id": record.pk, "status": record.status})
        elif record.status == "awaiting_establishment":
            raise ValidationError("Use the establishment routing action for this request.")
        elif record.status == "awaiting_sanction":
            route = routing_configuration(application.category)
            roles = route.get("sanctioning_roles")
            if isinstance(roles, str):
                roles = [roles]
            if not roles or not any(
                actor_has_assigned_role(_actor(request), role) for role in roles
            ):
                raise ValidationError("You are not the configured sanctioning authority.")
            if outcome not in {"approved", "rejected"}:
                raise ValidationError("Final authority must approve or reject.")
        else:
            raise ValidationError("This cancellation is not awaiting a decision.")
        ApprovalRecord.objects.create(
            application=application,
            actor_user_id=_actor(request).user_id,
            actor_role=_actor(request).active_role or "",
            outcome=outcome,
            comments=f"Cancellation #{record.pk}: {payload.validated_data['comments']}",
        )
        record.status = outcome
        record.decided_by_user_id = _actor(request).user_id
        record.decided_at = timezone.now()
        record.save(update_fields=["status", "decided_by_user_id", "decided_at", "updated_at"])
        if outcome == "approved":
            application.status = "cancelled"
            application.save(update_fields=["status", "updated_at"])
            allocations = application.requested_days_by_year or {
                str(application.starts_on.year): str(application.requested_days)
            }
            apply_balance_delta(
                user_id=application.user_id,
                category=application.category,
                allocations=allocations,
                application=application,
                transaction_type="restoration",
                note="Approved leave cancellation",
            )
        return Response({"id": record.pk, "status": record.status})


class ExtensionReviewView(APIView):
    permission_classes = [MODULE, HasPermission(P_REVIEW)]

    @transaction.atomic
    def post(self, request, pk):
        record = (
            ExtensionRecord.objects.select_for_update()
            .filter(pk=pk, status__in={"pending", "awaiting_sanction", "awaiting_establishment"})
            .select_related("application", "application__category")
            .first()
        )
        if record is None:
            raise NotFound("No pending extension request.")
        payload = s.ReviewSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        outcome = payload.validated_data["outcome"]
        application = record.application
        if record.status == "awaiting_substitute":
            raise ValidationError("The substitute must accept before review.")
        if not actor_has_assigned_role(_actor(request), record.assigned_role):
            raise ValidationError("This extension is assigned to another role.")
        if record.status == "pending" and outcome in {"recommended", "not_recommended"}:
            if application.category.code in {"CL", "RH"}:
                raise ValidationError("Extensions are supported only for EL, COL or VL.")
            route = routing_configuration(application.category)
            establishment_role = route.get("establishment_role")
            if establishment_role:
                record.status = "awaiting_establishment"
                record.assigned_role = establishment_role
            else:
                from modules.leave_elm.services import next_sanctioning_role

                record.status = "awaiting_sanction"
                record.assigned_role = next_sanctioning_role(application.category)
            record.save(update_fields=["status", "assigned_role", "updated_at"])
            ApprovalRecord.objects.create(
                application=application,
                actor_user_id=_actor(request).user_id,
                actor_role=_actor(request).active_role or "",
                outcome=outcome,
                comments=f"Extension #{record.pk}: {payload.validated_data['comments']}",
            )
            return Response({"id": record.pk, "status": record.status})
        if record.status == "pending" and application.category.code not in {"CL", "RH"}:
            raise ValidationError("Unit Head must recommend or not recommend this extension.")
        if record.status == "awaiting_establishment":
            raise ValidationError("Use the establishment routing action for this request.")
        if record.status == "awaiting_sanction":
            route = routing_configuration(application.category)
            roles = route.get("sanctioning_roles")
            if isinstance(roles, str):
                roles = [roles]
            if not roles or not any(
                actor_has_assigned_role(_actor(request), role) for role in roles
            ):
                raise ValidationError("You are not the configured sanctioning authority.")
        if outcome not in {"approved", "rejected"}:
            raise ValidationError("Final authority must approve or reject.")
        ApprovalRecord.objects.create(
            application=application,
            actor_user_id=_actor(request).user_id,
            actor_role=_actor(request).active_role or "",
            outcome=outcome,
            comments=f"Extension #{record.pk}: {payload.validated_data['comments']}",
        )
        record.status = outcome
        record.decided_by_user_id = _actor(request).user_id
        record.decided_at = timezone.now()
        record.save(update_fields=["status", "decided_by_user_id", "decided_at", "updated_at"])
        if outcome == "approved":
            allocations = record.additional_days_by_year or {
                str(record.additional_starts_on.year): str(record.additional_days)
            }
            apply_balance_delta(
                user_id=application.user_id,
                category=application.category,
                allocations={year: -Decimal(str(amount)) for year, amount in allocations.items()},
                application=application,
                transaction_type="deduction",
                note=f"Approved leave extension #{record.pk}",
            )
        return Response({"id": record.pk, "status": record.status})


class ResumptionReviewView(APIView):
    permission_classes = [MODULE, HasPermission(P_REVIEW)]

    @transaction.atomic
    def post(self, request, pk):
        record = (
            ResumptionRecord.objects.select_for_update()
            .filter(pk=pk, status="submitted")
            .select_related("application", "application__category")
            .first()
        )
        if record is None:
            raise NotFound("No submitted resumption record.")
        application = record.application
        if not actor_has_assigned_role(_actor(request), record.assigned_role):
            raise ValidationError("This resumption is assigned to another role.")
        if record.actual_resumption_date < application.starts_on:
            raise ValidationError("Resumption date cannot precede the approved leave.")
        if record.actual_resumption_date == application.ends_on:
            actual_end = application.ends_on
            actual_allocations = application.requested_days_by_year or {
                str(application.starts_on.year): str(application.requested_days)
            }
            days = application.requested_days
        else:
            actual_end = record.actual_resumption_date - timedelta(days=1)
            actual_allocations = chargeable_days_by_year(
                application.category, application.starts_on, actual_end
            )
            days = sum(actual_allocations.values())
            original_allocations = application.requested_days_by_year or {
                str(application.starts_on.year): str(application.requested_days)
            }
            delta_years = set(original_allocations) | {str(year) for year in actual_allocations}
            balance_deltas = {}
            for year in delta_years:
                original = Decimal(str(original_allocations.get(year, "0")))
                actual = Decimal(str(actual_allocations.get(int(year), "0")))
                balance_deltas[year] = original - actual
            apply_balance_delta(
                user_id=application.user_id,
                category=application.category,
                allocations=balance_deltas,
                application=application,
                transaction_type="adjustment",
                note="Resumption review adjustment",
            )
        record.actual_days_by_year = {
            str(year): str(value) for year, value in actual_allocations.items()
        }
        record.actual_leave_days = days
        record.actual_leave_end = actual_end
        record.status = "reviewed"
        record.reviewed_by_user_id = _actor(request).user_id
        record.reviewed_at = timezone.now()
        record.save(
            update_fields=[
                "actual_days_by_year",
                "actual_leave_days",
                "actual_leave_end",
                "status",
                "reviewed_by_user_id",
                "reviewed_at",
                "updated_at",
            ]
        )
        return Response({"id": record.pk, "status": record.status, "actual_leave_days": days})
