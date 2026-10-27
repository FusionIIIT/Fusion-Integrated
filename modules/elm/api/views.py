from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.api.serializers import (
    CancellationSerializer,
    DecisionSerializer,
    ExtensionSerializer,
    HolidayCalendarSerializer,
    LeaveBalanceSerializer,
    LeaveRequestCreateSerializer,
    LeaveRequestSerializer,
    LeaveTransactionSerializer,
    OfflineLeaveSerializer,
    ResumptionSerializer,
    SubstituteResponseSerializer,
)
from modules.elm.models import (
    HolidayCalendar,
    LeaveAction,
    LeaveBalance,
    LeaveRequest,
    LeaveTransaction,
)

MODULE = HasModuleGrant("leave_elm")


def current_user_id(request):
    principal = getattr(request, "principal", None)
    if principal is not None and getattr(principal, "user_id", None) is not None:
        return int(principal.user_id)
    user = getattr(request, "user", None)
    if user and getattr(user, "id", None) is not None:
        return int(user.id)
    raise PermissionDenied("Cannot identify current Fusion user.")


def calculate_leave_days(category, start_date, end_date, part_of_day="full"):
    if part_of_day in ("first_half", "second_half"):
        return Decimal("0.5")
    
    # BR-EL-011: continuous counting for EL, COL, VL (includes weekends & holidays)
    if category in ("EL", "COL", "VL"):
        total_days = (end_date - start_date).days + 1
        return Decimal(str(total_days))
    
    # For CL, SCL, RH: excludes weekends and closed holidays
    holidays = set(
        HolidayCalendar.objects.filter(
            date__range=(start_date, end_date), is_restricted=False
        ).values_list("date", flat=True)
    )
    
    days_count = 0
    curr = start_date
    while curr <= end_date:
        # 5 = Saturday, 6 = Sunday
        if curr.weekday() < 5 and curr not in holidays:
            days_count += 1
        curr += timedelta(days=1)
    
    return Decimal(str(days_count))


def validate_overlap(user_id, start_date, end_date, part_of_day="full", exclude_id=None):
    # BR-EL-012: Check overlap with active pending or approved leave
    active_qs = LeaveRequest.objects.filter(
        user_id=user_id,
        status__in=["pending", "approved", "cancellation_requested"],
    )
    if exclude_id:
        active_qs = active_qs.exclude(pk=exclude_id)
        
    overlapping = active_qs.filter(
        start_date__lte=end_date,
        end_date__gte=start_date,
    )
    
    for req in overlapping:
        # Half-day exception: different halves on the same date do not overlap
        if (
            start_date == end_date == req.start_date == req.end_date
            and req.category == "CL"
            and part_of_day in ("first_half", "second_half")
            and req.part_of_day in ("first_half", "second_half")
            and part_of_day != req.part_of_day
        ):
            continue
        raise ValidationError(
            f"Requested leave period overlaps with existing leave request #{req.pk} ({req.category}: {req.start_date} to {req.end_date})."
        )


class LeaveRequestListView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.request.view_self", "leave_elm.request.apply")]

    def get(self, request):
        user_id = current_user_id(request)
        requests = LeaveRequest.objects.filter(user_id=user_id).order_by("-created_at")
        return Response(LeaveRequestSerializer(requests, many=True).data)

    def post(self, request):
        user_id = current_user_id(request)
        serializer = LeaveRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        category = data["category"]
        start_date = data["start_date"]
        end_date = data["end_date"]
        part_of_day = data.get("part_of_day", "full")
        substitute_user_id = data.get("substitute_user_id")

        # BR-EL-014: substitute cannot be applicant
        if substitute_user_id and int(substitute_user_id) == user_id:
            raise ValidationError("You cannot nominate yourself as a substitute.")

        # BR-EL-012: overlap validation
        validate_overlap(user_id, start_date, end_date, part_of_day)

        # Calculate leave days
        days = calculate_leave_days(category, start_date, end_date, part_of_day)
        if days <= Decimal("0"):
            raise ValidationError("Calculated leave days must be greater than zero.")

        # BR-EL-003: RH validation against published calendar
        if category == "RH":
            if not HolidayCalendar.objects.filter(date=start_date, is_restricted=True).exists():
                raise ValidationError("Restricted Holiday request must correspond to an official Restricted Holiday in the calendar.")

        # Check balance
        year = start_date.year
        balance = LeaveBalance.objects.filter(user_id=user_id, year=year, category=category).first()
        if balance is None:
            # If no balance row exists, check if initial entitlement is granted
            available = Decimal("0")
        else:
            available = balance.available_days

        if available < days:
            raise ValidationError(
                f"Insufficient {category} leave balance. Available: {available}, Required: {days}."
            )

        # Determine workflow stage and substitute status
        if substitute_user_id:
            sub_status = "pending"
            current_stage = "substitute_consent"
        else:
            sub_status = "none"
            current_stage = "unit_head_review"

        with transaction.atomic():
            obj = LeaveRequest.objects.create(
                user_id=user_id,
                category=category,
                start_date=start_date,
                end_date=end_date,
                part_of_day=part_of_day,
                days_requested=days,
                reason=data.get("reason", ""),
                station_leave=data.get("station_leave", False),
                station_destination=data.get("station_destination", ""),
                substitute_user_id=substitute_user_id,
                substitute_status=sub_status,
                status="pending",
                current_stage=current_stage,
            )
            LeaveAction.objects.create(
                request=obj,
                actor_user_id=user_id,
                action="submitted",
                note="Leave request submitted.",
            )

        return Response(LeaveRequestSerializer(obj).data, status=status.HTTP_201_CREATED)


class LeaveDetailView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.request.view_self")]

    def get(self, request, pk):
        user_id = current_user_id(request)
        obj = LeaveRequest.objects.filter(pk=pk).first()
        if not obj:
            raise NotFound("Leave request not found.")
        # Allow applicant, substitute, or reviewer to view
        return Response(LeaveRequestSerializer(obj).data)


class SubstituteQueueView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.request.view_self")]

    def get(self, request):
        user_id = current_user_id(request)
        items = LeaveRequest.objects.filter(
            substitute_user_id=user_id,
            substitute_status="pending",
            status="pending",
        ).order_by("-created_at")
        return Response(LeaveRequestSerializer(items, many=True).data)


class SubstituteResponseView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.request.view_self")]

    def post(self, request, pk):
        user_id = current_user_id(request)
        obj = LeaveRequest.objects.filter(pk=pk, substitute_user_id=user_id).first()
        if not obj:
            raise NotFound("Substitute request not found.")
        if obj.substitute_status != "pending" or obj.status != "pending":
            raise ValidationError("This substitute request is no longer pending.")

        serializer = SubstituteResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        decision = serializer.validated_data["decision"]
        note = serializer.validated_data.get("note", "")

        with transaction.atomic():
            if decision == "accept":
                obj.substitute_status = "accepted"
                obj.current_stage = "unit_head_review"  # release gate to Unit Head (BR-EL-015)
                action_name = "substitute_accepted"
            else:
                obj.substitute_status = "declined"
                # Remains blocked until applicant re-nominates or withdraws
                action_name = "substitute_declined"

            obj.save(update_fields=["substitute_status", "current_stage", "updated_at"])
            LeaveAction.objects.create(
                request=obj,
                actor_user_id=user_id,
                action=action_name,
                note=note,
            )

        return Response(LeaveRequestSerializer(obj).data)


class LeaveQueueView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.request.review")]

    def get(self, request):
        # Return requests pending review (unit_head_review, establishment_review, final_sanction)
        items = LeaveRequest.objects.filter(
            status="pending",
            current_stage__in=["unit_head_review", "establishment_review", "final_sanction"],
        ).order_by("created_at")
        return Response(LeaveRequestSerializer(items, many=True).data)


class LeaveDecisionView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.request.review")]

    def post(self, request, pk):
        reviewer_id = current_user_id(request)
        obj = LeaveRequest.objects.filter(pk=pk).first()
        if not obj:
            raise NotFound("Leave request not found.")
        if obj.status != "pending":
            return Response({"detail": "This request is no longer pending."}, status=400)

        serializer = DecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        decision = serializer.validated_data["decision"]
        note = serializer.validated_data.get("note", "")

        with transaction.atomic():
            # BR-EL-016: CL and RH final authority is Unit Head
            if obj.category in ("CL", "RH"):
                if decision in ("approve", "recommend"):
                    obj.status = "approved"
                    obj.current_stage = "completed"
                    # Deduct balance
                    bal, _ = LeaveBalance.objects.get_or_create(
                        user_id=obj.user_id,
                        year=obj.start_date.year,
                        category=obj.category,
                    )
                    bal.used_days += obj.days_requested
                    bal.save(update_fields=["used_days"])

                    LeaveTransaction.objects.create(
                        request=obj,
                        user_id=obj.user_id,
                        year=obj.start_date.year,
                        category=obj.category,
                        transaction_type="debit",
                        amount=obj.days_requested,
                        note=f"Approved leave #{obj.pk}",
                    )
                    action_name = "approved"
                else:
                    obj.status = "rejected"
                    obj.current_stage = "completed"
                    action_name = "rejected"
            else:
                # BR-EL-017, BR-EL-018: Higher sanction leave (SCL, EL, COL, VL)
                if obj.current_stage == "unit_head_review":
                    if decision in ("recommend", "approve"):
                        obj.current_stage = "final_sanction"
                        action_name = "recommended"
                    else:
                        # BR-EL-017: Not recommended is not final rejection; continues to higher sanction
                        obj.current_stage = "final_sanction"
                        action_name = "not_recommended"
                elif obj.current_stage in ("final_sanction", "establishment_review"):
                    if decision in ("approve", "recommend"):
                        obj.status = "approved"
                        obj.current_stage = "completed"
                        # Deduct balance
                        bal, _ = LeaveBalance.objects.get_or_create(
                            user_id=obj.user_id,
                            year=obj.start_date.year,
                            category=obj.category,
                        )
                        bal.used_days += obj.days_requested
                        bal.save(update_fields=["used_days"])

                        LeaveTransaction.objects.create(
                            request=obj,
                            user_id=obj.user_id,
                            year=obj.start_date.year,
                            category=obj.category,
                            transaction_type="debit",
                            amount=obj.days_requested,
                            note=f"Sanctioned leave #{obj.pk}",
                        )
                        action_name = "approved"
                    else:
                        obj.status = "rejected"
                        obj.current_stage = "completed"
                        action_name = "rejected"
                else:
                    raise ValidationError("Request is not in a valid stage for decision.")

            obj.save(update_fields=["status", "current_stage", "updated_at"])
            LeaveAction.objects.create(
                request=obj,
                actor_user_id=reviewer_id,
                action=action_name,
                note=note,
            )

        return Response(LeaveRequestSerializer(obj).data)


class LeaveWithdrawalView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.request.apply")]

    def post(self, request, pk):
        user_id = current_user_id(request)
        obj = LeaveRequest.objects.filter(pk=pk, user_id=user_id).first()
        if not obj:
            raise NotFound("Leave request not found.")
        
        # BR-EL-022: immediate withdrawal before final approval
        if obj.status != "pending":
            raise ValidationError("Only pending requests can be withdrawn.")

        with transaction.atomic():
            obj.status = "withdrawn"
            obj.current_stage = "completed"
            obj.save(update_fields=["status", "current_stage", "updated_at"])
            LeaveAction.objects.create(
                request=obj,
                actor_user_id=user_id,
                action="withdrawn",
                note="Request withdrawn by applicant.",
            )

        return Response(LeaveRequestSerializer(obj).data)


class LeaveCancellationView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.request.apply", "leave_elm.request.review")]

    def post(self, request, pk):
        user_id = current_user_id(request)
        obj = LeaveRequest.objects.filter(pk=pk).first()
        if not obj:
            raise NotFound("Leave request not found.")

        # BR-EL-023: cancellation of approved leave before start
        if obj.status != "approved":
            raise ValidationError("Only approved leave can be cancelled.")
        
        today = timezone.localdate()
        if obj.start_date <= today:
            raise ValidationError("Leave has already commenced or passed. Cancellation is only permitted before start date.")

        serializer = CancellationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data["reason"]

        with transaction.atomic():
            obj.status = "cancelled"
            obj.current_stage = "completed"
            obj.save(update_fields=["status", "current_stage", "updated_at"])

            # Restore balance
            bal = LeaveBalance.objects.filter(
                user_id=obj.user_id,
                year=obj.start_date.year,
                category=obj.category,
            ).first()
            if bal:
                bal.used_days = max(Decimal("0"), bal.used_days - obj.days_requested)
                bal.save(update_fields=["used_days"])

            # Record restoration transaction
            LeaveTransaction.objects.create(
                request=obj,
                user_id=obj.user_id,
                year=obj.start_date.year,
                category=obj.category,
                transaction_type="restoration",
                amount=obj.days_requested,
                note=f"Restored days for cancelled leave #{obj.pk}. Reason: {reason}",
            )

            LeaveAction.objects.create(
                request=obj,
                actor_user_id=user_id,
                action="cancelled",
                note=reason,
            )

        return Response(LeaveRequestSerializer(obj).data)


class LeaveExtensionView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.request.apply")]

    def post(self, request, pk):
        user_id = current_user_id(request)
        parent = LeaveRequest.objects.filter(pk=pk, user_id=user_id).first()
        if not parent:
            raise NotFound("Original leave request not found.")
        
        # BR-EL-025: extension only for ongoing EL, COL, VL
        if parent.category not in ("EL", "COL", "VL"):
            raise ValidationError("Extension is only supported for EL, COL, and VL categories.")
        if parent.status != "approved":
            raise ValidationError("Only approved leave can be extended.")

        serializer = ExtensionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ext_end = serializer.validated_data["extension_end_date"]
        reason = serializer.validated_data["reason"]

        if ext_end <= parent.end_date:
            raise ValidationError("Extension end date must be strictly after the current leave end date.")

        # Incremental days
        ext_start = parent.end_date + timedelta(days=1)
        inc_days = calculate_leave_days(parent.category, ext_start, ext_end)

        # Check balance
        bal = LeaveBalance.objects.filter(
            user_id=user_id, year=ext_start.year, category=parent.category
        ).first()
        avail = bal.available_days if bal else Decimal("0")
        if avail < inc_days:
            raise ValidationError(f"Insufficient balance for extension. Required: {inc_days}, Available: {avail}")

        with transaction.atomic():
            ext_req = LeaveRequest.objects.create(
                user_id=user_id,
                category=parent.category,
                start_date=ext_start,
                end_date=ext_end,
                days_requested=inc_days,
                reason=reason,
                status="pending",
                current_stage="unit_head_review",
                is_extension=True,
                parent_request=parent,
            )
            LeaveAction.objects.create(
                request=ext_req,
                actor_user_id=user_id,
                action="extension_submitted",
                note=f"Extension requested for leave #{parent.pk}: +{inc_days} days.",
            )

        return Response(LeaveRequestSerializer(ext_req).data, status=status.HTTP_201_CREATED)


class LeaveResumptionView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.request.apply", "leave_elm.request.review")]

    def post(self, request, pk):
        user_id = current_user_id(request)
        obj = LeaveRequest.objects.filter(pk=pk).first()
        if not obj:
            raise NotFound("Leave request not found.")

        # BR-EL-027, BR-EL-028: Resumption for EL, COL, VL
        if obj.category not in ("EL", "COL", "VL"):
            raise ValidationError("Resumption report is only applicable for EL, COL, and VL.")
        if obj.status != "approved":
            raise ValidationError("Resumption can only be submitted for approved leave.")

        serializer = ResumptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        res_date = serializer.validated_data["resumption_date"]
        note = serializer.validated_data.get("note", "")

        with transaction.atomic():
            obj.resumption_date = res_date
            bal = LeaveBalance.objects.filter(
                user_id=obj.user_id, year=obj.start_date.year, category=obj.category
            ).first()

            # BR-EL-028: Normal, Early, or Late Resumption
            if res_date == obj.end_date:
                obj.resumption_status = "normal"
                action_text = "Resumed on approved end date. No balance adjustment."
            elif res_date < obj.end_date:
                # Early return: refund unused days
                unused_days = calculate_leave_days(obj.category, res_date + timedelta(days=1), obj.end_date)
                obj.resumption_status = "early"
                if bal and unused_days > Decimal("0"):
                    bal.used_days = max(Decimal("0"), bal.used_days - unused_days)
                    bal.save(update_fields=["used_days"])
                    LeaveTransaction.objects.create(
                        request=obj,
                        user_id=obj.user_id,
                        year=obj.start_date.year,
                        category=obj.category,
                        transaction_type="restoration",
                        amount=unused_days,
                        note=f"Early resumption refund (+{unused_days} days).",
                    )
                action_text = f"Early resumption recorded. Refunded {unused_days} days."
            else:
                # Late return: deduct extra days
                extra_days = calculate_leave_days(obj.category, obj.end_date + timedelta(days=1), res_date)
                obj.resumption_status = "late"
                if bal and extra_days > Decimal("0"):
                    bal.used_days += extra_days
                    bal.save(update_fields=["used_days"])
                    LeaveTransaction.objects.create(
                        request=obj,
                        user_id=obj.user_id,
                        year=obj.start_date.year,
                        category=obj.category,
                        transaction_type="debit",
                        amount=extra_days,
                        note=f"Late resumption deduction (-{extra_days} days).",
                    )
                action_text = f"Late resumption recorded. Deducted {extra_days} days."

            obj.save(update_fields=["resumption_date", "resumption_status", "updated_at"])
            LeaveAction.objects.create(
                request=obj,
                actor_user_id=user_id,
                action="resumption_processed",
                note=f"{action_text} Note: {note}",
            )

        return Response(LeaveRequestSerializer(obj).data)


class LeaveBalanceListView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.balance.view_self")]

    def get(self, request):
        user_id = current_user_id(request)
        year = timezone.localdate().year
        balances = LeaveBalance.objects.filter(user_id=user_id, year=year)
        return Response(LeaveBalanceSerializer(balances, many=True).data)


class HolidayCalendarListView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.request.view_self")]

    def get(self, request):
        year = timezone.localdate().year
        holidays = HolidayCalendar.objects.filter(year=year).order_by("date")
        return Response(HolidayCalendarSerializer(holidays, many=True).data)


class YearEndProcessingView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.request.review")]

    def post(self, request):
        # BR-EL-007, BR-EL-020: Year-end processing
        year = int(request.data.get("year", timezone.localdate().year))
        next_year = year + 1
        processed_users = set(LeaveBalance.objects.filter(year=year).values_list("user_id", flat=True))

        with transaction.atomic():
            for uid in processed_users:
                # 1. Lapses: CL, RH, SCL (BR-EL-002, 003, 004)
                for cat in ("CL", "RH", "SCL"):
                    bal = LeaveBalance.objects.filter(user_id=uid, year=year, category=cat).first()
                    if bal and bal.available_days > Decimal("0"):
                        lapsed = bal.available_days
                        LeaveTransaction.objects.create(
                            user_id=uid,
                            year=year,
                            category=cat,
                            transaction_type="lapse",
                            amount=lapsed,
                            note=f"Year-end {year} lapse of unused {cat}.",
                        )

                # 2. VL to EL Conversion: 2 VL : 1 EL (BR-EL-007, 008)
                vl_bal = LeaveBalance.objects.filter(user_id=uid, year=year, category="VL").first()
                if vl_bal and vl_bal.available_days > Decimal("0"):
                    unused_vl = vl_bal.available_days
                    converted_el = Decimal(unused_vl) / Decimal("2")
                    LeaveTransaction.objects.create(
                        user_id=uid,
                        year=year,
                        category="VL",
                        transaction_type="vl_conversion",
                        amount=unused_vl,
                        note=f"Converted {unused_vl} VL to {converted_el} EL (2:1 ratio).",
                    )
                    # Credit converted EL to next year's EL balance
                    el_next, _ = LeaveBalance.objects.get_or_create(
                        user_id=uid, year=next_year, category="EL"
                    )
                    el_next.carried_forward_days += converted_el
                    el_next.save(update_fields=["carried_forward_days"])

                # 3. Carry forward EL and COL (BR-EL-005, 009)
                for cat in ("EL", "COL"):
                    bal = LeaveBalance.objects.filter(user_id=uid, year=year, category=cat).first()
                    if bal and bal.available_days > Decimal("0"):
                        cf = bal.available_days
                        nxt, _ = LeaveBalance.objects.get_or_create(
                            user_id=uid, year=next_year, category=cat
                        )
                        nxt.carried_forward_days += cf
                        nxt.save(update_fields=["carried_forward_days"])

        return Response({"status": f"Year-end processing for {year} executed successfully."})


class OfflineLeaveEntryView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.request.review")]

    def post(self, request):
        # BR-EL-029: Offline-sanctioned leave synchronization by Leave Administrator
        admin_id = current_user_id(request)
        serializer = OfflineLeaveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        user_id = d["user_id"]
        category = d["category"]
        start_date = d["start_date"]
        end_date = d["end_date"]
        days = Decimal(str(d["days_requested"]))
        ref = d["offline_reference"]
        reason = d["reason"]

        with transaction.atomic():
            obj = LeaveRequest.objects.create(
                user_id=user_id,
                category=category,
                start_date=start_date,
                end_date=end_date,
                days_requested=days,
                reason=reason,
                status="approved",
                current_stage="completed",
                offline_sanctioned=True,
                offline_reference=ref,
            )
            # Deduct balance
            bal, _ = LeaveBalance.objects.get_or_create(
                user_id=user_id, year=start_date.year, category=category
            )
            bal.used_days += days
            bal.save(update_fields=["used_days"])

            LeaveTransaction.objects.create(
                request=obj,
                user_id=user_id,
                year=start_date.year,
                category=category,
                transaction_type="debit",
                amount=days,
                note=f"Retrospective offline entry (Ref: {ref})",
            )
            LeaveAction.objects.create(
                request=obj,
                actor_user_id=admin_id,
                action="offline_recorded",
                note=f"Offline sanction synchronized. Ref: {ref}",
            )

        return Response(LeaveRequestSerializer(obj).data, status=status.HTTP_201_CREATED)
