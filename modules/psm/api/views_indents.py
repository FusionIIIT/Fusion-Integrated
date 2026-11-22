# Indent HTTP views: submit, track, modify, withdraw, repeat, stock-check, and approvals.
from django.db.models import Case, IntegerField, When
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import NotFoundError
from core.api.pagination import CursorPagination
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.psm.api import serializers as ser
from modules.psm.selectors import scoping
from modules.psm.services import approvals, indents, procurement, stock


def _paginate(request, qs, serializer_cls):
    paginator = CursorPagination()
    page = paginator.paginate_queryset(qs, request)
    return paginator.get_paginated_response(serializer_cls(page, many=True).data)


class IndentListCreateView(APIView):
    def get_permissions(self):
        perm = "psm.indent.view" if self.request.method == "GET" else "psm.indent.create"
        return [HasModuleGrant("psm")(), HasPermission(perm)()]

    def get_throttles(self):
        if self.request.method == "POST":
            self.throttle_scope = "psm_write"
        return super().get_throttles()

    @extend_schema(
        tags=["psm"],
        summary="List scoped purchase indents",
        responses={200: ser.IndentReadSerializer(many=True)},
        examples=[
            OpenApiExample(
                "Indent list",
                value={
                    "next": None,
                    "previous": None,
                    "results": [
                        {"id": 1, "indent_number": "IND-20261122-ABC123", "status": "submitted"}
                    ],
                },
            )
        ],
    )
    def get(self, request):
        qs = scoping.indents_for(request.principal)
        status_f = (request.query_params.get("status") or "").strip()
        dept_f = (request.query_params.get("department") or "").strip()
        if status_f:
            qs = qs.filter(status=status_f)
        if dept_f:
            qs = qs.filter(department__iexact=dept_f)
        if request.query_params.get("queue") == "1":
            # Order approval queues by criticality first (BR-PSM-014, AFR-PSM-025).
            qs = qs.annotate(
                priority_rank=Case(
                    When(priority__in=("urgent", "critical"), then=0),
                    When(priority="high", then=1),
                    default=2,
                    output_field=IntegerField(),
                )
            ).order_by("priority_rank", "current_stage_since", "id")
            return Response({"results": ser.IndentReadSerializer(qs[:100], many=True).data})
        return _paginate(request, qs, ser.IndentReadSerializer)

    @extend_schema(
        tags=["psm"],
        summary="Create and submit a purchase indent (PSM-UC-001)",
        request=ser.IndentCreateSerializer,
        responses={201: ser.IndentReadSerializer},
        examples=[
            OpenApiExample(
                "Submit indent",
                value={
                    "department": "CSE",
                    "item_description": "Lab Switches",
                    "quantity": 5,
                    "estimated_cost": "45000.00",
                    "justification": "Networking lab upgrade",
                },
            )
        ],
    )
    def post(self, request):
        s = ser.IndentCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        obj = indents.create_indent(actor=request.principal, **s.validated_data)
        return Response(ser.IndentReadSerializer(obj).data, status=status.HTTP_201_CREATED)


class IndentDetailView(APIView):
    def get_permissions(self):
        perm = "psm.indent.view" if self.request.method == "GET" else "psm.indent.update"
        return [HasModuleGrant("psm")(), HasPermission(perm)()]

    def get_throttles(self):
        if self.request.method == "PATCH":
            self.throttle_scope = "psm_write"
        return super().get_throttles()

    @extend_schema(
        tags=["psm"],
        summary="Get scoped indent detail and history (PSM-UC-003)",
        responses={200: ser.IndentDetailSerializer},
    )
    def get(self, request, indent_id: int):
        obj = (
            scoping.indents_for(request.principal)
            .prefetch_related("versions", "transitions")
            .filter(pk=indent_id)
            .first()
        )
        if obj is None:
            raise NotFoundError("Indent not found.")
        return Response(ser.IndentDetailSerializer(obj).data)

    @extend_schema(
        tags=["psm"],
        summary="Modify a pending indent in a permissible state (PSM-UC-023)",
        request=ser.IndentUpdateSerializer,
        responses={200: ser.IndentReadSerializer},
    )
    def patch(self, request, indent_id: int):
        s = ser.IndentUpdateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        obj = indents.modify_indent(
            actor=request.principal, indent_id=indent_id, **s.validated_data
        )
        return Response(ser.IndentReadSerializer(obj).data)


class IndentWithdrawView(APIView):
    permission_classes = [HasModuleGrant("psm"), HasPermission("psm.indent.delete")]
    throttle_scope = "psm_write"

    @extend_schema(
        tags=["psm"],
        summary="Withdraw or cancel a pending indent (PSM-UC-005)",
        request=ser.ReasonSerializer,
        responses={200: ser.IndentReadSerializer},
    )
    def post(self, request, indent_id: int):
        s = ser.ReasonSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        obj = indents.withdraw_indent(
            actor=request.principal, indent_id=indent_id, reason=s.validated_data["reason"]
        )
        return Response(ser.IndentReadSerializer(obj).data)


class IndentRepeatView(APIView):
    permission_classes = [HasModuleGrant("psm"), HasPermission("psm.indent.create")]
    throttle_scope = "psm_write"

    @extend_schema(
        tags=["psm"],
        summary="Repeat a previous indent as a new editable draft (PSM-UC-024)",
        request=None,
        responses={201: ser.IndentReadSerializer},
    )
    def post(self, request, indent_id: int):
        obj = indents.repeat_as_draft(actor=request.principal, indent_id=indent_id)
        return Response(ser.IndentReadSerializer(obj).data, status=status.HTTP_201_CREATED)


class IndentStockCheckView(APIView):
    permission_classes = [HasModuleGrant("psm"), HasPermission("psm.stock.update")]
    throttle_scope = "psm_write"

    @extend_schema(
        tags=["psm"],
        summary="Check departmental/central stock and reserve if available (PSM-UC-007)",
        request=None,
        responses={200: ser.IndentReadSerializer},
    )
    def post(self, request, indent_id: int):
        indent, reservation = stock.check_and_reserve(actor=request.principal, indent_id=indent_id)
        data = ser.IndentReadSerializer(indent).data
        data["reservation_id"] = reservation.pk if reservation else None
        return Response(data)


class IndentDeptAdminReviewView(APIView):
    permission_classes = [HasModuleGrant("psm"), HasPermission("psm.indent.review")]
    throttle_scope = "psm_write"

    @extend_schema(
        tags=["psm"],
        summary="Department Admin review, priority, and decision (PSM-UC-011)",
        request=ser.DeptAdminReviewSerializer,
        responses={200: ser.IndentReadSerializer},
    )
    def post(self, request, indent_id: int):
        s = ser.DeptAdminReviewSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        obj = approvals.dept_admin_review(
            actor=request.principal, indent_id=indent_id, **s.validated_data
        )
        return Response(ser.IndentReadSerializer(obj).data)


class IndentHodRecommendView(APIView):
    permission_classes = [HasModuleGrant("psm"), HasPermission("psm.indent.approve")]
    throttle_scope = "psm_write"

    @extend_schema(
        tags=["psm"],
        summary="Department Head review and recommendation (PSM-UC-016)",
        request=ser.HodRecommendSerializer,
        responses={200: ser.IndentReadSerializer},
    )
    def post(self, request, indent_id: int):
        s = ser.HodRecommendSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        obj = approvals.hod_recommend(
            actor=request.principal, indent_id=indent_id, **s.validated_data
        )
        return Response(ser.IndentReadSerializer(obj).data)


class IndentProcurementReviewView(APIView):
    permission_classes = [HasModuleGrant("psm"), HasPermission("psm.procurement.review")]
    throttle_scope = "psm_write"

    @extend_schema(
        tags=["psm"],
        summary="PS Admin review and procurement method selection (PSM-UC-025)",
        request=ser.ProcurementReviewSerializer,
        responses={200: ser.IndentReadSerializer},
    )
    def post(self, request, indent_id: int):
        s = ser.ProcurementReviewSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        obj = procurement.review_and_select_method(
            actor=request.principal, indent_id=indent_id, notes=s.validated_data["notes"]
        )
        return Response(ser.IndentReadSerializer(obj).data)


class IndentFinalDecisionView(APIView):
    permission_classes = [HasModuleGrant("psm"), HasPermission("psm.procurement.approve")]
    throttle_scope = "psm_write"

    @extend_schema(
        tags=["psm"],
        summary="Director/Registrar final approval or rejection (PSM-UC-012)",
        request=ser.FinalDecisionSerializer,
        responses={200: ser.IndentReadSerializer},
    )
    def post(self, request, indent_id: int):
        s = ser.FinalDecisionSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        obj = approvals.final_decision(
            actor=request.principal, indent_id=indent_id, **s.validated_data
        )
        return Response(ser.IndentReadSerializer(obj).data)
