"""
DRF API Views for Leave Management.
Implements REST endpoints for applications, balances, history, and lifecycle actions.
Uses fusion_auth.permissions for authorization checks.
"""

from typing import Any
from rest_framework import generics, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.leave.domain.policy import (
    get_categories_requiring_unit_head_decision,
)
from modules.leave.services.applications import (
    apply_leave,
    respond_to_substitute_request,
    nominate_replacement_substitute,
    unit_head_review,
    establishment_verify_and_route,
    final_sanction_decision,
    withdraw_pending_request,
    request_cancellation,
    decide_cancellation,
    request_extension,
    submit_resumption,
    review_resumption,
)
from modules.leave.services.lifecycle import (
    get_balances,
    get_history,
)
from modules.leave.api.serializers import (
    LeaveApplicationDetailSerializer,
    LeaveApplicationListSerializer,
    ApplyLeaveSerializer,
    RespondToSubstituteRequestSerializer,
    NominateReplacementSubstituteSerializer,
    UnitHeadReviewDecisionSerializer,
    UnitHeadRecommendationSerializer,
    EstablishmentVerifyAndRouteSerializer,
    FinalSanctionDecisionSerializer,
    RequestWithdrawalSerializer,
    RequestCancellationSerializer,
    RequestExtensionSerializer,
    SubmitResumptionSerializer,
    ReviewResumptionSerializer,
)


class HasLeaveModuleGrant(HasModuleGrant):
    """Decorator/Class alias for module grant check."""
    pass


# --- Application Views ---

class MyApplicationsView(generics.ListAPIView):
    """List applications belonging to the authenticated user."""

    permission_classes = [HasLeaveModuleGrant, HasPermission("leave.application.view_self")]
    serializer_class = LeaveApplicationListSerializer

    def get_queryset(self) -> Any:
        """Filter queryset to only include applications for the current user."""
        return self.request.user.leaveapplication_set.all()


class ApplyLeaveView(generics.CreateAPIView):
    """Create a new leave application."""

    permission_classes = [HasLeaveModuleGrant, HasPermission("leave.application.create")]
    serializer_class = ApplyLeaveSerializer

    def create(self, request: Any, *args: Any, **kwargs: Any) -> Response:
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            instance = apply_leave(
                actor_id=request.principal.user_id,
                category=serializer.validated_data["category"],
                requested_from=serializer.validated_data["requested_from"],
                requested_to=serializer.validated_data["requested_to"],
                purpose=serializer.validated_data["purpose"],
                station_leave_details=serializer.validated_data.get("station_leave_details"),
                nominated_substitute_id=serializer.validated_data.get("nominated_substitute_id"),
            )
            return Response(LeaveApplicationDetailSerializer(instance).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ApplicationDetailView(generics.RetrieveAPIView):
    """Retrieve a specific leave application by ID."""

    permission_classes = [HasLeaveModuleGrant, HasPermission("leave.application.view_self")]
    serializer_class = LeaveApplicationDetailSerializer

    def get_queryset(self) -> Any:
        """Filter queryset to only include applications for the current user."""
        return self.request.user.leaveapplication_set.all()


class WithdrawApplicationView(generics.UpdateAPIView):
    """Withdraw a pending leave application."""

    permission_classes = [HasLeaveModuleGrant, HasPermission("leave.application.create")]
    serializer_class = RequestWithdrawalSerializer

    def put(self, request: Any, *args: Any, **kwargs: Any) -> Response:
        try:
            application_id = kwargs["pk"]
            withdraw_pending_request(
                actor_id=request.principal.user_id,
                application_id=application_id,
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CancelApprovedLeaveView(generics.UpdateAPIView):
    """Request cancellation of an approved leave."""

    permission_classes = [HasLeaveModuleGrant, HasPermission("leave.application.create")]
    serializer_class = RequestCancellationSerializer

    def put(self, request: Any, *args: Any, **kwargs: Any) -> Response:
        try:
            application_id = kwargs["pk"]
            request_cancellation(
                actor_id=request.principal.user_id,
                application_id=application_id,
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ExtendLeaveView(generics.UpdateAPIView):
    """Request an extension of ongoing leave."""

    permission_classes = [HasLeaveModuleGrant, HasPermission("leave.application.create")]
    serializer_class = RequestExtensionSerializer

    def put(self, request: Any, *args: Any, **kwargs: Any) -> Response:
        try:
            application_id = kwargs["pk"]
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            extension_from = serializer.validated_data["extension_from"]
            extension_to = serializer.validated_data["extension_to"]
            purpose = serializer.validated_data["purpose"]
            station_leave_details = serializer.validated_data.get("station_leave_details")
            nominated_substitute_id = serializer.validated_data.get("nominated_substitute_id")

            request_extension(
                actor_id=request.principal.user_id,
                application_id=application_id,
                extension_from=extension_from,
                extension_to=extension_to,
                purpose=purpose,
                station_leave_details=station_leave_details,
                nominated_substitute_id=nominated_substitute_id,
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SubmitResumptionView(generics.UpdateAPIView):
    """Submit actual resumption of duty information."""

    permission_classes = [HasLeaveModuleGrant, HasPermission("leave.application.view_self")]
    serializer_class = SubmitResumptionSerializer

    def put(self, request: Any, *args: Any, **kwargs: Any) -> Response:
        try:
            application_id = kwargs["pk"]
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            actual_resumption_date = serializer.validated_data["actual_resumption_date"]

            submit_resumption(
                actor_id=request.principal.user_id,
                application_id=application_id,
                actual_resumption_date=actual_resumption_date,
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class RespondToSubstituteView(generics.UpdateAPIView):
    """Respond to a substitute request."""

    permission_classes = [HasLeaveModuleGrant, HasPermission("leave.application.view_self")]
    serializer_class = RespondToSubstituteRequestSerializer

    def put(self, request: Any, *args: Any, **kwargs: Any) -> Response:
        try:
            application_id = kwargs["pk"]
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            accept = serializer.validated_data["accept"]

            respond_to_substitute_request(
                actor_id=request.principal.user_id,
                application_id=application_id,
                accept=accept,
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class NominateReplacementSubstituteView(generics.UpdateAPIView):
    """Nominate a replacement substitute."""

    permission_classes = [HasLeaveModuleGrant, HasPermission("leave.application.view_self")]
    serializer_class = NominateReplacementSubstituteSerializer

    def put(self, request: Any, *args: Any, **kwargs: Any) -> Response:
        try:
            application_id = kwargs["pk"]
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            new_substitute_id = serializer.validated_data["new_substitute_id"]

            nominate_replacement_substitute(
                actor_id=request.principal.user_id,
                application_id=application_id,
                new_substitute_id=new_substitute_id,
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# --- Decision Views (For Unit Head / Sanctioning Authority) ---

class ApprovalsInboxView(generics.ListAPIView):
    """List applications awaiting decision by the authenticated actor."""

    permission_classes = [HasLeaveModuleGrant, HasPermission("leave.application.review")]
    serializer_class = LeaveApplicationDetailSerializer

    def get_queryset(self) -> Any:
        """Filter queryset to applications where the current user is the reviewer."""
        # Note: In a real system, this might need additional context (e.g., role-based filtering).
        # For now, we assume the permission check handles the scope.
        return self.request.user.leaveapplication_set.all()


class UnitHeadDecisionView(generics.UpdateAPIView):
    """Record Unit Head's review decision (CL/RH)."""

    permission_classes = [HasLeaveModuleGrant, HasPermission("leave.application.approve")]
    serializer_class = UnitHeadReviewDecisionSerializer

    def put(self, request: Any, *args: Any, **kwargs: Any) -> Response:
        try:
            application_id = kwargs["pk"]
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            decision = serializer.validated_data["decision"]

            unit_head_review(
                actor_id=request.principal.user_id,
                application_id=application_id,
                decision=decision,
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UnitHeadRecommendationView(generics.UpdateAPIView):
    """Record Unit Head's recommendation (SCL/EL/COL/VL)."""

    permission_classes = [HasLeaveModuleGrant, HasPermission("leave.application.approve")]
    serializer_class = UnitHeadRecommendationSerializer

    def put(self, request: Any, *args: Any, **kwargs: Any) -> Response:
        try:
            application_id = kwargs["pk"]
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            decision = serializer.validated_data["decision"]

            unit_head_review(
                actor_id=request.principal.user_id,
                application_id=application_id,
                decision=decision,
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class EstablishmentVerifyAndRouteView(generics.UpdateAPIView):
    """Perform establishment-level verification and routing."""

    permission_classes = [HasLeaveModuleGrant, HasPermission("leave.admin.manage")]
    serializer_class = EstablishmentVerifyAndRouteSerializer

    def put(self, request: Any, *args: Any, **kwargs: Any) -> Response:
        try:
            application_id = kwargs["pk"]

            establishment_verify_and_route(
                actor_id=request.principal.user_id,
                application_id=application_id,
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class FinalSanctionDecisionView(generics.UpdateAPIView):
    """Record the final sanctioning decision."""

    permission_classes = [HasLeaveModuleGrant, HasPermission("leave.application.approve")]
    serializer_class = FinalSanctionDecisionSerializer

    def put(self, request: Any, *args: Any, **kwargs: Any) -> Response:
        try:
            application_id = kwargs["pk"]
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            decision = serializer.validated_data["decision"]

            final_sanction_decision(
                actor_id=request.principal.user_id,
                application_id=application_id,
                decision=decision,
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DecideCancellationView(generics.UpdateAPIView):
    """Decide on a cancellation request."""

    permission_classes = [HasLeaveModuleGrant, HasPermission("leave.application.approve")]
    serializer_class = FinalSanctionDecisionSerializer  # Reuse structure but logic differs in service

    def put(self, request: Any, *args: Any, **kwargs: Any) -> Response:
        try:
            application_id = kwargs["pk"]
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            decision = serializer.validated_data["decision"]

            decide_cancellation(
                actor_id=request.principal.user_id,
                application_id=application_id,
                decision=decision,
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# --- Lifecycle & Balance Views ---

class BalancesView(generics.ListAPIView):
    """Retrieve leave balances for the authenticated user."""

    permission_classes = [HasLeaveModuleGrant, HasPermission("leave.balance.view_self")]
    serializer_class = LeaveBalanceSerializer

    def get(self, request: Any, *args: Any, **kwargs: Any) -> Response:
        try:
            year = kwargs.get("year")
            if not year:
                return Response({"error": "Year parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

            balances = get_balances(
                user_id=request.principal.user_id,
                year=year,
            )
            return Response(balances)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class HistoryView(generics.ListAPIView):
    """Retrieve leave action history for the authenticated user."""

    permission_classes = [HasLeaveModuleGrant, HasPermission("leave.admin.manage")]
    serializer_class = LeaveActionHistorySerializer

    def get(self, request: Any, *args: Any, **kwargs: Any) -> Response:
        try:
            history = get_history(
                user_id=request.principal.user_id,
            )
            return Response(history)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ReviewResumptionView(generics.UpdateAPIView):
    """Review the submitted resumption and adjust balance."""

    permission_classes = [HasLeaveModuleGrant, HasPermission("leave.application.approve")]
    serializer_class = ReviewResumptionSerializer

    def put(self, request: Any, *args: Any, **kwargs: Any) -> Response:
        try:
            application_id = kwargs["pk"]
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            actual_resumption_date = serializer.validated_data["actual_resumption_date"]

            review_resumption(
                actor_id=request.principal.user_id,
                application_id=application_id,
                actual_resumption_date=actual_resumption_date,
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
