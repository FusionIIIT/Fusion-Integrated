"""Thin API views; domain rules live in services, not in HTTP handlers."""
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission, IsAuthenticatedPrincipal
from modules.elm.models import LeaveAccount, LeaveCancellationRequest, LeaveRequest


class LeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = (
            "id", "leave_type", "start_date", "end_date", "start_session",
            "end_session", "requested_days", "reason", "status", "submitted_at",
            "substitute_user_id", "substitute_consent",
        )
        read_only_fields = ("id", "status", "submitted_at", "requested_days", "substitute_consent")

    def validate(self, attrs):
        if attrs["end_date"] < attrs["start_date"]:
            raise serializers.ValidationError({"end_date": "End date must not precede start date."})
        return attrs


class LeaveRequestListCreateView(APIView):
    """List only the caller's requests; creation is wired through the service layer."""
    permission_classes = [IsAuthenticatedPrincipal, HasModuleGrant("leave_elm")]

    def get_permissions(self):
        required = "leave_elm.application.apply" if self.request.method == "POST" else "leave_elm.application.view_self"
        return [permission() for permission in self.permission_classes] + [HasPermission(required)()]

    def get(self, request):
        rows = LeaveRequest.objects.filter(user_id=request.principal.user_id).select_related("leave_type")
        return Response(LeaveRequestSerializer(rows, many=True).data)

    def post(self, request):
        from modules.elm.services.requests import submit_leave_request

        serializer = LeaveRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        row = submit_leave_request(
            actor=request.principal,
            leave_type_id=serializer.validated_data["leave_type"].pk,
            start_date=serializer.validated_data["start_date"],
            end_date=serializer.validated_data["end_date"],
            start_session=serializer.validated_data["start_session"],
            end_session=serializer.validated_data["end_session"],
            reason=serializer.validated_data["reason"],
            substitute_user_id=serializer.validated_data.get("substitute_user_id"),
            # Never trust a client-supplied category for eligibility decisions.
            employee_category=getattr(request.principal, "employee_category", "any"),
        )
        return Response(LeaveRequestSerializer(row).data, status=201)


class MyLeaveBalanceView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, HasModuleGrant("leave_elm")]

    def get_permissions(self):
        # Balance access is a distinct capability from viewing applications.
        # Keep the permission aligned with the IAM registry declaration.
        return [permission() for permission in self.permission_classes] + [
            HasPermission("leave_elm.balance.view_self")()
        ]

    def get(self, request):
        accounts = LeaveAccount.objects.filter(user_id=request.principal.user_id).select_related("leave_type")
        return Response([
            {"leave_type": a.leave_type.code, "leave_year": a.leave_year,
             "balance_days": str(a.balance_days)}
            for a in accounts
        ])


class LeaveRequestWithdrawView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, HasModuleGrant("leave_elm"), HasPermission("leave_elm.application.view_self")]

    def post(self, request, request_id):
        from modules.elm.services.requests import withdraw_leave_request
        row = withdraw_leave_request(actor=request.principal, request_id=request_id,
                                     reason=request.data.get("reason", ""))
        return Response(LeaveRequestSerializer(row).data)


class SubstituteConsentView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, HasModuleGrant("leave_elm")]

    def post(self, request, request_id):
        from modules.elm.services.requests import respond_to_substitute
        accept = request.data.get("accept")
        if not isinstance(accept, bool):
            raise serializers.ValidationError({"accept": "A boolean value is required."})
        row = respond_to_substitute(actor=request.principal, request_id=request_id, accept=accept)
        return Response(LeaveRequestSerializer(row).data)


class LeaveRequestDecisionView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, HasModuleGrant("leave_elm"), HasPermission("leave_elm.application.approve")]

    def post(self, request, request_id):
        from modules.elm.services.requests import decide_leave_request
        decision = request.data.get("decision", "")
        reason = request.data.get("reason", "")
        if not isinstance(reason, str):
            raise serializers.ValidationError({"reason": "Must be a string."})
        row = decide_leave_request(actor=request.principal, request_id=request_id,
                                   decision=decision, reason=reason)
        return Response(LeaveRequestSerializer(row).data)
class LeaveRequestReviewListView(APIView):
    """List leave applications awaiting a reviewer decision."""
    permission_classes = [
        IsAuthenticatedPrincipal,
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.application.view"),
    ]

    def get(self, request):
        rows = LeaveRequest.objects.filter(
            status__in=[
                LeaveRequest.PENDING_UNIT_HEAD,
                LeaveRequest.PENDING_HIERARCHY,
                LeaveRequest.CANCELLATION_PENDING,
            ]
        ).select_related("leave_type").order_by("submitted_at")
        return Response(LeaveRequestSerializer(rows, many=True).data)


class LeaveCancellationRequestView(APIView):
    """Let an employee request cancellation of their own approved leave."""
    permission_classes = [
        IsAuthenticatedPrincipal,
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.application.cancel"),
    ]

    def post(self, request, request_id):
        from modules.elm.services.requests import request_leave_cancellation

        reason = request.data.get("reason", "")
        if not isinstance(reason, str):
            raise serializers.ValidationError({"reason": "Must be a string."})

        cancellation = request_leave_cancellation(
            actor=request.principal,
            request_id=request_id,
            reason=reason,
        )
        return Response({
            "id": cancellation.pk,
            "leave_request": cancellation.leave_request_id,
            "reason": cancellation.reason,
            "status": cancellation.status,
        }, status=201)


class LeaveCancellationDecisionView(APIView):
    """Let an authorized reviewer approve or reject a cancellation."""
    permission_classes = [
        IsAuthenticatedPrincipal,
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.application.approve"),
    ]

    def post(self, request, cancellation_id):
        from modules.elm.services.requests import decide_leave_cancellation

        decision = request.data.get("decision", "")
        reason = request.data.get("reason", "")
        if not isinstance(reason, str):
            raise serializers.ValidationError({"reason": "Must be a string."})

        cancellation = decide_leave_cancellation(
            actor=request.principal,
            cancellation_id=cancellation_id,
            decision=decision,
            reason=reason,
        )
        return Response({
            "id": cancellation.pk,
            "leave_request": cancellation.leave_request_id,
            "status": cancellation.status,
            "decided_by_user_id": cancellation.decided_by_user_id,
            "decided_at": cancellation.decided_at,
        })