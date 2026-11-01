"""API views for IWD complaints (intake, listing, and detail).

Implements UC-IWD-001 and UC-IWD-005 with strict permission gating and selector scoping.
"""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.iwd.api.serializers import (
    ComplaintAssessmentSerializer,
    ComplaintCreateSerializer,
    ComplaintDetailSerializer,
    ComplaintListSerializer,
    EstimateCreateSerializer,
    EstimateReviewActionSerializer,
    MaterialIssueActionSerializer,
)
from modules.iwd.selectors.complaints import get_complaint_for_user, visible_complaints
from modules.iwd.services.assessments import record_complaint_assessment
from modules.iwd.services.complaints import submit_complaint
from modules.iwd.services.estimates import resubmit_complaint_estimate, submit_complaint_estimate
from modules.iwd.services.inventory import execute_inventory_action
from modules.iwd.services.reviews import execute_estimate_review


class ComplaintListCreateView(APIView):
    """List complaints within caller's scope, or submit a new maintenance complaint."""

    permission_classes = [
        HasModuleGrant("iwd"),
        HasPermission("iwd.complaint.create", "iwd.complaint.view", "iwd.complaint.view_self"),
    ]

    @extend_schema(
        summary="List complaints visible to caller",
        description="Privileged users see all complaints; engineers see assigned; employees see own.",
        responses={200: ComplaintListSerializer(many=True)},
    )
    def get(self, request):
        p = getattr(request, "principal", None)
        if not p or not (p.has_permission("iwd.complaint.view") or p.has_permission("iwd.complaint.view_self")):
            raise PermissionDenied("You do not have permission to view complaints.")

        qs = visible_complaints(p)

        # Optional query filters
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        category_filter = request.query_params.get("category")
        if category_filter:
            qs = qs.filter(category=category_filter)

        unassigned = request.query_params.get("unassigned")
        if unassigned and unassigned.lower() == "true":
            qs = qs.filter(assigned_engineer_id__isnull=True)

        serializer = ComplaintListSerializer(qs.order_by("-created_at"), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Submit a new maintenance complaint",
        description="Creates a complaint in SUBMITTED state and attempts automatic engineer assignment.",
        request=ComplaintCreateSerializer,
        responses={201: ComplaintDetailSerializer},
    )
    def post(self, request):
        p = getattr(request, "principal", None)
        if not p or not p.has_permission("iwd.complaint.create"):
            raise PermissionDenied("You do not have permission to submit complaints.")

        serializer = ComplaintCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        complaint = submit_complaint(
            complainant_id=p.user_id,
            category=serializer.validated_data["category"],
            location=serializer.validated_data["location"],
            urgency=serializer.validated_data.get("urgency", "low"),
            remarks=serializer.validated_data.get("remarks", ""),
        )

        out_serializer = ComplaintDetailSerializer(complaint)
        return Response(out_serializer.data, status=status.HTTP_201_CREATED)


class ComplaintDetailView(APIView):
    """Retrieve complaint detail if within authorized scope, else 404."""

    permission_classes = [
        HasModuleGrant("iwd"),
        HasPermission("iwd.complaint.view", "iwd.complaint.view_self"),
    ]

    @extend_schema(
        summary="Retrieve complaint detail",
        description="Returns full complaint details and transition history. Returns 404 if out of scope.",
        responses={200: ComplaintDetailSerializer, 404: None},
    )
    def get(self, request, pk: int):
        p = getattr(request, "principal", None)
        complaint = get_complaint_for_user(pk, p)
        if complaint is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ComplaintDetailSerializer(complaint)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ComplaintAssessView(APIView):
    """Record technical assessment and repairs required for an assigned complaint (UC-IWD-015)."""

    permission_classes = [
        HasModuleGrant("iwd"),
        HasPermission("iwd.complaint.assess"),
    ]

    @extend_schema(
        summary="Record complaint technical assessment",
        description="Records repairs required and transitions complaint from Assigned to Assessed (BW-IWD-01 Step 3).",
        request=ComplaintAssessmentSerializer,
        responses={200: ComplaintDetailSerializer},
    )
    def post(self, request, pk: int):
        p = getattr(request, "principal", None)
        if not p or getattr(p, "active_role", None) != "iwd_engineer" or not p.has_permission("iwd.complaint.assess"):
            raise PermissionDenied("You must have active role 'iwd_engineer' and permission 'iwd.complaint.assess'.")

        serializer = ComplaintAssessmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        complaint = record_complaint_assessment(
            complaint_id=pk,
            principal=p,
            assessment_details=serializer.validated_data["assessment_details"],
        )

        out_serializer = ComplaintDetailSerializer(complaint)
        return Response(out_serializer.data, status=status.HTTP_200_OK)


class ComplaintEstimateView(APIView):
    """Prepare and submit repair estimate for an assessed complaint (UC-IWD-021)."""

    permission_classes = [
        HasModuleGrant("iwd"),
        HasPermission("iwd.complaint.assess"),
    ]

    @extend_schema(
        summary="Submit repair estimate",
        description="Submits repair estimate and routes complaint to the applicable cost-band review queue (CW-IWD-01).",
        request=EstimateCreateSerializer,
        responses={201: ComplaintDetailSerializer},
    )
    def post(self, request, pk: int):
        p = getattr(request, "principal", None)
        if not p or getattr(p, "active_role", None) != "iwd_engineer" or not p.has_permission("iwd.complaint.assess"):
            raise PermissionDenied("You must have active role 'iwd_engineer' and permission 'iwd.complaint.assess'.")

        serializer = EstimateCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        complaint, estimate = submit_complaint_estimate(
            complaint_id=pk,
            principal=p,
            estimated_cost=serializer.validated_data["estimated_cost"],
            estimated_time=serializer.validated_data["estimated_time"],
            materials_summary=serializer.validated_data["materials_summary"],
            supporting_details=serializer.validated_data.get("supporting_details", ""),
        )

        out_serializer = ComplaintDetailSerializer(complaint)
        return Response(out_serializer.data, status=status.HTTP_201_CREATED)


class ComplaintEstimateReviewView(APIView):
    """Review an estimate and record approval, rejection, committee findings, or forwarding."""

    permission_classes = [
        HasModuleGrant("iwd"),
        HasPermission(
            "iwd.estimate.review_low",
            "iwd.estimate.review_committee",
            "iwd.estimate.review_mid",
            "iwd.estimate.review_director",
        ),
    ]

    @extend_schema(
        summary="Review estimate",
        description="Records approval, rejection, committee feasibility review, or forwarding based on cost band.",
        request=EstimateReviewActionSerializer,
        responses={200: ComplaintDetailSerializer},
    )
    def post(self, request, pk: int):
        p = getattr(request, "principal", None)
        if not p:
            raise PermissionDenied("Authentication required.")

        serializer = EstimateReviewActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        complaint = execute_estimate_review(
            complaint_id=pk,
            principal=p,
            action=serializer.validated_data["action"],
            remarks=serializer.validated_data.get("remarks", ""),
        )

        out_serializer = ComplaintDetailSerializer(complaint)
        return Response(out_serializer.data, status=status.HTTP_200_OK)


class ComplaintEstimateResubmitView(APIView):
    """Modify and resubmit a rejected repair estimate (BW-IWD-12..14 / UC-IWD-151)."""

    permission_classes = [
        HasModuleGrant("iwd"),
        HasPermission("iwd.complaint.assess"),
    ]

    @extend_schema(
        summary="Resubmit rejected repair estimate",
        description="Modifies and resubmits a rejected estimate, dynamically routing it to the appropriate cost-band review queue.",
        request=EstimateCreateSerializer,
        responses={201: ComplaintDetailSerializer},
    )
    def post(self, request, pk: int):
        p = getattr(request, "principal", None)
        if not p or getattr(p, "active_role", None) != "iwd_engineer" or not p.has_permission("iwd.complaint.assess"):
            raise PermissionDenied("You must have active role 'iwd_engineer' and permission 'iwd.complaint.assess'.")

        serializer = EstimateCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        complaint, estimate = resubmit_complaint_estimate(
            complaint_id=pk,
            principal=p,
            estimated_cost=serializer.validated_data["estimated_cost"],
            estimated_time=serializer.validated_data["estimated_time"],
            materials_summary=serializer.validated_data["materials_summary"],
            supporting_details=serializer.validated_data.get("supporting_details", ""),
        )

        out_serializer = ComplaintDetailSerializer(complaint)
        return Response(out_serializer.data, status=status.HTTP_201_CREATED)


class ComplaintInventoryActionView(APIView):
    """Inventory verification, material issuance, or stock shortage procurement (BW-IWD-06..08, CW-IWD-02)."""

    permission_classes = [
        HasModuleGrant("iwd"),
        HasPermission("iwd.inventory.manage"),
    ]

    @extend_schema(
        summary="Execute inventory or procurement action",
        description="IWD Admin checks stock, issues materials, or coordinates procurement for approved work (BW-IWD-06..08).",
        request=MaterialIssueActionSerializer,
        responses={200: ComplaintDetailSerializer},
    )
    def post(self, request, pk: int):
        p = getattr(request, "principal", None)
        if not p or getattr(p, "active_role", None) != "iwd_admin" or not p.has_permission("iwd.inventory.manage"):
            raise PermissionDenied("You must have active role 'iwd_admin' and permission 'iwd.inventory.manage'.")

        serializer = MaterialIssueActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        complaint, _ = execute_inventory_action(
            complaint_id=pk,
            principal=p,
            action=serializer.validated_data["action"],
            materials_summary=serializer.validated_data.get("materials_summary", ""),
            remarks=serializer.validated_data.get("remarks", ""),
        )

        out_serializer = ComplaintDetailSerializer(complaint)
        return Response(out_serializer.data, status=status.HTTP_200_OK)

