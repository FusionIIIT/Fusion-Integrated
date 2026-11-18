import csv
import io
import uuid
from decimal import InvalidOperation

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import HttpResponse
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import ConflictError, DomainError, NotFoundError
from modules.psm import models as m
from modules.psm import selectors, services
from modules.psm.access import member
from modules.psm.api.serializers import (
    SERIALIZERS,
    CommandSerializer,
    JsonCommandSerializer,
    representation,
)
from modules.psm.reporting import generate_report, schedule_report

CREATORS = {
    "indents": services.create_indent,
    "vendors": services.create_vendor,
    "tenders": services.create_tender,
    "bids": services.create_bid,
    "orders": services.create_order,
    "receipts": services.create_receipt,
    "cases": services.create_case,
    "invoices": services.create_invoice,
    "transfers": services.create_transfer,
    "stock": services.adjust_stock,
    "policies": services.configure_policy,
    "schedules": schedule_report,
}
ACTIONS = {
    "indents": services.indent_action,
    "vendors": services.vendor_action,
    "tenders": services.tender_action,
    "orders": services.order_action,
    "cases": services.case_action,
    "invoices": services.invoice_action,
    "transfers": services.transfer_action,
}


def execute(fn, *args):
    try:
        return fn(*args)
    except (ValidationError, ValueError, TypeError, InvalidOperation) as exc:
        raise DomainError("Invalid value: verify identifiers, numbers and field formats.") from exc
    except IntegrityError as exc:
        raise ConflictError(
            "A conflicting record already exists or an inventory invariant would be violated."
        ) from exc


class WorkspaceView(APIView):
    @extend_schema(
        responses=OpenApiTypes.OBJECT, tags=["psm"], summary="Scoped purchase and stores workspace"
    )
    def get(self, request):
        scope = member(request.principal)
        names = [
            "attachments",
            "vendor_history",
            "indents",
            "stock",
            "vendors",
            "tenders",
            "bids",
            "orders",
            "receipts",
            "cases",
            "invoices",
            "payments",
            "transfers",
            "ledger",
            "audit",
            "notifications",
            "communications",
            "schedules",
            "reports",
            "policies",
        ]
        payload = {}
        for name in names:
            qs = selectors.collection(request.principal, name).order_by("-created_at")
            payload[name] = SERIALIZERS[name](qs[:200], many=True).data
        # Unpublished competing bids are confidential until close.
        if scope.role in ("ps_admin", "committee"):
            visible = m.Tender.objects.filter(closes_at__lte=timezone.now()).values("id")
            payload["bids"] = SERIALIZERS["bids"](
                selectors.collection(request.principal, "bids").filter(tender_id__in=visible),
                many=True,
            ).data
        for vendor in payload["vendors"]:
            if scope.role not in ("ps_admin", "accounts", "auditor", "vendor"):
                vendor.pop("bank_details", None)
        payload["transfer_sources"] = []
        if scope.role in ("department_admin", "ps_admin"):
            payload["transfer_sources"] = [
                {
                    "id": str(s.pk),
                    "item": s.item,
                    "location": s.location,
                    "available": str(s.quantity - s.reserved),
                }
                for s in m.Stock.objects.all().order_by("item", "location")[:500]
            ]
        payload["viewer"] = {
            "user_id": request.principal.user_id,
            "name": request.principal.display_name,
            "role": scope.role,
            "department": scope.department,
        }
        qs = selectors.indents(request.principal)
        payload["metrics"] = {
            "requests": qs.count(),
            "pending": qs.exclude(status__in=["draft", *services.TERMINAL]).count(),
            "receipts_pending": qs.filter(
                status__in=["delivered", "dispatched", "grn_recorded"]
            ).count(),
            "open_cases": selectors.collection(request.principal, "cases")
            .exclude(status="resolved")
            .count(),
        }
        return Response(payload)


class CollectionView(APIView):
    @extend_schema(
        responses=OpenApiTypes.OBJECT, tags=["psm"], summary="List authorized PSM records"
    )
    def get(self, request, resource):
        if resource not in SERIALIZERS:
            raise NotFoundError()
        qs = selectors.collection(request.principal, resource).order_by("-created_at")
        if resource == "bids" and member(request.principal).role != "vendor":
            qs = qs.filter(tender__closes_at__lte=timezone.now())
        if resource == "audit":
            scope = member(request.principal)
            m.Audit.objects.create(
                actor_id=request.principal.user_id,
                department=scope.department,
                entity="audit",
                object_id=uuid.uuid4(),
                action="audit_accessed",
                snapshot={},
            )
        if resource == "indents":
            for key in ("status", "item", "department"):
                if request.query_params.get(key):
                    qs = qs.filter(**{key: request.query_params[key]})
        try:
            offset = max(0, int(request.query_params.get("offset", 0)))
        except ValueError as exc:
            raise DomainError("offset must be an integer.") from exc
        return Response(
            {
                "count": qs.count(),
                "results": SERIALIZERS[resource](qs[offset : offset + 100], many=True).data,
            }
        )

    @extend_schema(
        request=JsonCommandSerializer,
        responses=OpenApiTypes.OBJECT,
        tags=["psm"],
        examples=[
            OpenApiExample(
                "New indent",
                value={
                    "data": {
                        "item": "Lab chairs",
                        "quantity": "6",
                        "estimated_cost": "12000",
                        "justification": "Teaching lab",
                    }
                },
            )
        ],
    )
    def post(self, request, resource):
        if resource not in CREATORS:
            raise NotFoundError()
        body = JsonCommandSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        data = body.validated_data["data"]
        if resource == "schedules":
            data = {**data, "_credential": request.auth}
        obj = execute(CREATORS[resource], request.principal, data)
        return Response(representation(obj), status=201)


class ActionView(APIView):
    @extend_schema(
        request=CommandSerializer,
        responses=OpenApiTypes.OBJECT,
        tags=["psm"],
        examples=[OpenApiExample("Submit draft", value={"action": "submit", "data": {}})],
    )
    def post(self, request, resource, pk):
        body = CommandSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        action, data = body.validated_data["action"], body.validated_data["data"]
        if resource == "schedules":
            scope = selectors.collection(request.principal, "schedules").filter(pk=pk).first()
            if scope is None:
                raise NotFoundError()
            if action != "disable":
                raise DomainError("Only disable is supported.")
            scope.enabled = False
            scope.save()
            services.audit(request.principal, scope, "schedule_disabled")
            return Response(representation(scope))
        if resource == "notifications":
            obj = selectors.collection(request.principal, "notifications").filter(pk=pk).first()
            if obj is None:
                raise NotFoundError()
            if action != "read":
                raise DomainError("Unknown notification action.")
            obj.read_at = timezone.now()
            obj.save()
            return Response(representation(obj))
        if resource not in ACTIONS:
            raise NotFoundError()
        return Response(
            representation(execute(ACTIONS[resource], request.principal, pk, action, data))
        )


class ReportView(APIView):
    @extend_schema(
        request=JsonCommandSerializer,
        responses=OpenApiTypes.OBJECT,
        tags=["psm"],
        examples=[
            OpenApiExample("Stock report", value={"data": {"report": "stock", "filters": {}}})
        ],
    )
    def post(self, request):
        body = JsonCommandSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        data = body.validated_data["data"]
        run = execute(generate_report, request.principal, data)
        if data.get("format") == "csv":
            output = io.StringIO()
            rows = run.rows
            if rows:
                writer = csv.DictWriter(output, fieldnames=rows[0].keys())
                writer.writeheader()
                for row in rows:
                    writer.writerow(
                        {
                            k: (
                                "'" + str(v)
                                if str(v).startswith(("=", "+", "-", "@", "\t", "\r"))
                                else v
                            )
                            for k, v in row.items()
                        }
                    )
            response = HttpResponse(output.getvalue(), content_type="text/csv")
            response["Content-Disposition"] = 'attachment; filename="psm-report.csv"'
            return response
        return Response(representation(run))
