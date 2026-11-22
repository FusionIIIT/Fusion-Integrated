"""PHC API: thin permission gates that delegate to services and selectors."""
from __future__ import annotations

from django.http import HttpResponse
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError
from fusion_auth.permissions import HasModuleGrant
from modules.phc.api import serializers as s
from modules.phc.api.permissions import HasPhcPermission
from modules.phc.selectors import scoping
from modules.phc.services import (
    advisories,
    ambulance,
    claims,
    inventory,
    records,
    reports,
    schedules,
)

_EX_SCHEDULE = [OpenApiExample("schedule", value={
    "doctor_name": "Dr A", "day_of_week": 0, "start_time": "09:00:00",
    "end_time": "13:00:00", "is_published": True}, response_only=True)]
_EX_ATT = [OpenApiExample("attendance", value={
    "doctor_name": "Dr A", "status": "available"}, response_only=True)]
_EX_OBJECT = [OpenApiExample("results", value={"results": []},
                             response_only=True)]
_EX_VISIT = [OpenApiExample("visit", value={"id": 1, "patient": 2001},
                            response_only=True)]
_EX_RX = [OpenApiExample("prescription", value={"id": 1,
          "medicine": "Paracetamol"}, response_only=True)]
_EX_CLAIM = [OpenApiExample("claim", value={"claim_id": 1,
             "state": "submitted"}, response_only=True)]
_EX_STOCK = [OpenApiExample("adjustment", value={"item": 1,
             "direction": "deduct", "quantity": 2}, response_only=True)]
_EX_ITEM = [OpenApiExample("item", value={"name": "Gloves", "quantity": 25},
                           response_only=True)]
_EX_REQ = [OpenApiExample("requisition", value={"requisition_id": 1,
           "state": "pending_approval"}, response_only=True)]
_EX_AMB = [OpenApiExample("ambulance", value={
    "patient_name": "Asha", "destination": "City Hospital"},
    response_only=True)]
_EX_ADV = [OpenApiExample("advisory", value={"title": "Flu season",
           "is_published": True}, response_only=True)]
_EX_REPORT = [OpenApiExample("report", value={
    "category": "demographics", "patient_count_by_kind": {"student": 10}},
    response_only=True)]
_EX_AUDIT = [OpenApiExample("audit", value={"action": "claim.submit",
             "target_type": "claim"}, response_only=True)]


MODULE = HasModuleGrant("phc")

P_SCHEDULE_VIEW = "phc.schedule.view"
P_SCHEDULE_MANAGE = "phc.schedule.manage"
P_RECORDS_VIEW_SELF = "phc.records.view_self"
P_RECORDS_MANAGE = "phc.records.manage"
P_CLAIM_SUBMIT = "phc.reimbursement.submit"
P_CLAIM_VIEW_SELF = "phc.reimbursement.view_self"
P_CLAIM_REVIEW = "phc.reimbursement.review"
P_CLAIM_VERIFY = "phc.reimbursement.verify"
P_CLAIM_SANCTION = "phc.reimbursement.sanction"
P_CLAIM_PAYMENT = "phc.reimbursement.payment"
P_INV_ADJUST = "phc.inventory.adjust"
P_INV_REQ_SUBMIT = "phc.requisition.submit"
P_INV_REQ_DECIDE = "phc.requisition.decide"
P_INV_REQ_FULFILL = "phc.requisition.fulfill"
P_AMBULANCE_LOG = "phc.ambulance.log"
P_ADVISORY_VIEW = "phc.advisory.view"
P_ADVISORY_PUBLISH = "phc.advisory.publish"
P_REPORTS_GENERATE = "phc.reports.generate"
P_AUDIT_VIEW = "phc.audit.view"


def _actor(request):
    return getattr(request, "principal", None)


def _positive_limit(raw, default=50, maximum=200) -> int:
    if raw is None:
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise BadRequestError(
            "limit must be a whole number between 1 and 200; omit it for the default."
        ) from None
    if not 1 <= value <= maximum:
        raise BadRequestError(f"limit must be between 1 and {maximum}.")
    return value


# ---- Doctor schedule & availability (CFR-001 / AFR-001..005) ----------------


@extend_schema(
    request=None,
    responses=s.DoctorScheduleSerializer(many=True),
    examples=[OpenApiExample(
        "published schedule",
        value={"schedules": [{"doctor_name": "Dr A", "day_of_week": 0,
                              "start_time": "09:00:00", "end_time": "13:00:00",
                              "is_published": True}],
               "attendance": {"Dr A": "available"}},
        response_only=True,
    )],
)
class DoctorScheduleListView(APIView):
    permission_classes = [MODULE, HasPhcPermission(P_SCHEDULE_VIEW)]

    def get(self, request):
        from django.utils import timezone
        return Response({
            "schedules": s.DoctorScheduleSerializer(
                scoping.published_schedules(), many=True).data,
            "attendance": {
                a.doctor_name: a.status
                for a in scoping.attendance_on(timezone.now().date())
            },
        })


@extend_schema(request=s.DoctorScheduleCreateSerializer,
               responses=s.DoctorScheduleSerializer,
               examples=_EX_SCHEDULE)
class DoctorScheduleCreateView(APIView):
    permission_classes = [MODULE, HasPhcPermission(P_SCHEDULE_MANAGE)]

    def post(self, request):
        ser = s.DoctorScheduleCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        schedule = schedules.create(_actor(request), ser.validated_data)
        return Response(s.DoctorScheduleSerializer(schedule).data,
                        status=status.HTTP_201_CREATED)


@extend_schema(request=s.DoctorScheduleMaintainSerializer,
               responses=s.DoctorScheduleSerializer,
               examples=_EX_SCHEDULE)
class DoctorScheduleMaintainView(APIView):
    permission_classes = [MODULE, HasPhcPermission(P_SCHEDULE_MANAGE)]

    def patch(self, request, pk):
        ser = s.DoctorScheduleMaintainSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        schedule = schedules.maintain(_actor(request), pk, ser.validated_data)
        return Response(s.DoctorScheduleSerializer(schedule).data)


@extend_schema(request=None, responses=s.DoctorScheduleSerializer,
               examples=_EX_SCHEDULE)
class DoctorSchedulePublishView(APIView):
    permission_classes = [MODULE, HasPhcPermission(P_SCHEDULE_MANAGE)]

    def post(self, request, pk):
        schedule = schedules.publish(_actor(request), pk)
        return Response(s.DoctorScheduleSerializer(schedule).data)


@extend_schema(request=s.DoctorAttendanceMarkSerializer,
               responses=s.DoctorAttendanceSerializer,
               examples=_EX_ATT)
class DoctorAttendanceMarkView(APIView):
    permission_classes = [MODULE, HasPhcPermission(P_SCHEDULE_MANAGE)]

    def post(self, request):
        ser = s.DoctorAttendanceMarkSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        attendance = schedules.mark_attendance(_actor(request), ser.validated_data)
        return Response(s.DoctorAttendanceSerializer(attendance).data,
                        status=status.HTTP_201_CREATED)


# ---- Patient records & prescriptions (CFR-002 / AFR-006..012) --------------


@extend_schema(request=None, responses=OpenApiTypes.OBJECT, examples=_EX_OBJECT)
class PatientSearchView(APIView):
    permission_classes = [MODULE, HasPhcPermission(P_RECORDS_MANAGE)]

    def get(self, request):
        rows = records.search((request.query_params.get("q") or "").strip())
        return Response({"results": [
            {"user_id": r.user_id, "display_name": r.display_name, "kind": r.kind}
            for r in rows
        ]})


@extend_schema(request=s.VisitCreateSerializer, responses=s.VisitSerializer,
               examples=_EX_VISIT)
class VisitCreateView(APIView):
    permission_classes = [MODULE, HasPhcPermission(P_RECORDS_MANAGE)]

    def post(self, request):
        ser = s.VisitCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        visit = records.create_visit(_actor(request), ser.validated_data)
        return Response(s.VisitSerializer(visit).data,
                        status=status.HTTP_201_CREATED)


@extend_schema(request=s.PrescriptionCreateSerializer,
               responses=s.PrescriptionSerializer,
               examples=_EX_RX)
class PrescriptionCreateView(APIView):
    permission_classes = [MODULE, HasPhcPermission(P_RECORDS_MANAGE)]

    def post(self, request):
        ser = s.PrescriptionCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        prescription = records.create_prescription(_actor(request), ser.validated_data)
        return Response(s.PrescriptionSerializer(prescription).data,
                        status=status.HTTP_201_CREATED)


@extend_schema(request=None, responses=s.VisitSerializer, examples=_EX_VISIT)
class PatientRecordsView(APIView):
    permission_classes = [MODULE, HasPhcPermission(P_RECORDS_VIEW_SELF)]

    def get(self, request):
        return Response({"results": s.VisitSerializer(
            scoping.visits_for(_actor(request)), many=True).data})


@extend_schema(request=None, responses=s.PrescriptionSerializer, examples=_EX_RX)
class PatientPrescriptionsView(APIView):
    permission_classes = [MODULE, HasPhcPermission(P_RECORDS_VIEW_SELF)]

    def get(self, request):
        return Response({"results": s.PrescriptionSerializer(
            scoping.prescriptions_for(_actor(request)), many=True).data})


@extend_schema(
    request=None,
    responses={(200, "application/pdf"): OpenApiTypes.BINARY,
               404: OpenApiResponse(description="No record owned by this user.")},
    examples=[OpenApiExample("pdf copy", value="%PDF-1.4 ...", response_only=True)],
)
class RecordDownloadView(APIView):
    permission_classes = [MODULE, HasPhcPermission(P_RECORDS_VIEW_SELF)]

    def get(self, request, pk):
        pdf = records.record_copy(_actor(request), pk)
        return HttpResponse(
            pdf, content_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="phc-record-{pk}.pdf"'},
        )


# ---- Reimbursement (CFR-003..005 / AFR-013..023, 038) ----------------------


@extend_schema(
    request=s.ReimbursementClaimCreateSerializer,
    responses=s.ReimbursementClaimSerializer,
    examples=[OpenApiExample(
        "submit claim",
        value={"prescription_id": 12, "expense_date": "2026-11-01",
               "amount": "1250.00", "description": "Consultation and medicine"},
        request_only=True,
    )],
)
class ReimbursementClaimCreateView(APIView):
    permission_classes = [MODULE, HasPhcPermission(P_CLAIM_SUBMIT)]
    throttle_scope = "phc_submit"

    def post(self, request):
        ser = s.ReimbursementClaimCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        claim = claims.submit(_actor(request), ser.validated_data)
        return Response(s.ReimbursementClaimSerializer(claim).data,
                        status=status.HTTP_201_CREATED)


@extend_schema(request=None, responses=s.ReimbursementClaimSerializer,
               examples=_EX_CLAIM)
class MyClaimsView(APIView):
    permission_classes = [MODULE, HasPhcPermission(P_CLAIM_VIEW_SELF)]

    def get(self, request):
        return Response({"results": s.ReimbursementClaimSerializer(
            scoping.claims_for(_actor(request)), many=True).data})


@extend_schema(request=None, responses=s.ReimbursementClaimSerializer,
               examples=_EX_CLAIM)
class ClaimReviewView(APIView):
    permission_classes = [MODULE, HasPhcPermission(P_CLAIM_REVIEW)]

    def post(self, request, pk):
        claim = claims.advance(_actor(request), pk, "review",
                               expected_updated_at=request.data.get("expected_updated_at"))
        return Response(s.ReimbursementClaimSerializer(claim).data)


@extend_schema(request=None, responses=s.ReimbursementClaimSerializer,
               examples=_EX_CLAIM)
class ClaimVerifyView(APIView):
    permission_classes = [MODULE, HasPhcPermission(P_CLAIM_VERIFY)]

    def post(self, request, pk):
        claim = claims.advance(_actor(request), pk, "verify",
                               expected_updated_at=request.data.get("expected_updated_at"))
        return Response(s.ReimbursementClaimSerializer(claim).data)


@extend_schema(request=s.SanctionDecisionSerializer,
               responses=s.ReimbursementClaimSerializer,
               examples=_EX_CLAIM)
class ClaimSanctionView(APIView):
    permission_classes = [MODULE, HasPhcPermission(P_CLAIM_SANCTION)]

    def post(self, request, pk):
        ser = s.SanctionDecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        action = ("sanction_approve" if ser.validated_data["decision"] == "approve"
                  else "sanction_reject")
        claim = claims.advance(_actor(request), pk, action,
                               ser.validated_data.get("note", ""),
                               expected_updated_at=request.data.get("expected_updated_at"))
        return Response(s.ReimbursementClaimSerializer(claim).data)


@extend_schema(request=None, responses=s.ReimbursementClaimSerializer,
               examples=_EX_CLAIM)
class ClaimPaymentView(APIView):
    permission_classes = [MODULE, HasPhcPermission(P_CLAIM_PAYMENT)]

    def post(self, request, pk):
        claim = claims.advance(_actor(request), pk, "payment",
                               expected_updated_at=request.data.get("expected_updated_at"))
        return Response(s.ReimbursementClaimSerializer(claim).data)


# ---- Inventory & procurement (CFR-006..007 / AFR-024..031) -----------------


@extend_schema(request=s.StockAdjustmentCreateSerializer,
               responses=s.StockAdjustmentSerializer,
               examples=_EX_STOCK)
class StockAdjustView(APIView):
    permission_classes = [MODULE, HasPhcPermission(P_INV_ADJUST)]

    def post(self, request):
        ser = s.StockAdjustmentCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        adjustment, _ = inventory.adjust_stock(_actor(request), ser.validated_data)
        return Response(s.StockAdjustmentSerializer(adjustment).data,
                        status=status.HTTP_201_CREATED)


@extend_schema(request=s.InventoryItemCreateSerializer,
               responses=s.InventoryItemSerializer,
               examples=_EX_ITEM)
class InventoryItemListCreateView(APIView):
    permission_classes = [MODULE, HasPhcPermission(P_INV_ADJUST)]

    def get(self, request):
        return Response({"results": s.InventoryItemSerializer(
            scoping.inventory_items(), many=True).data})

    def post(self, request):
        ser = s.InventoryItemCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        item = inventory.create_item(ser.validated_data)
        return Response(s.InventoryItemSerializer(item).data,
                        status=status.HTTP_201_CREATED)


@extend_schema(request=s.RequisitionCreateSerializer,
               responses=s.RequisitionSerializer,
               examples=_EX_REQ)
class RequisitionCreateView(APIView):
    permission_classes = [MODULE, HasPhcPermission(P_INV_REQ_SUBMIT)]
    throttle_scope = "phc_submit"

    def post(self, request):
        ser = s.RequisitionCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        requisition = inventory.submit_requisition(_actor(request), ser.validated_data)
        return Response(s.RequisitionSerializer(requisition).data,
                        status=status.HTTP_201_CREATED)


@extend_schema(request=s.RequisitionDecisionSerializer,
               responses=s.RequisitionSerializer,
               examples=_EX_REQ)
class RequisitionDecideView(APIView):
    permission_classes = [MODULE, HasPhcPermission(P_INV_REQ_DECIDE)]

    def post(self, request, pk):
        ser = s.RequisitionDecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        requisition = inventory.decide_requisition(
            _actor(request), pk, ser.validated_data["decision"],
            ser.validated_data.get("note", ""),
            request.data.get("expected_updated_at"))
        return Response(s.RequisitionSerializer(requisition).data)


@extend_schema(request=None, responses=s.RequisitionSerializer, examples=_EX_REQ)
class RequisitionFulfillView(APIView):
    permission_classes = [MODULE, HasPhcPermission(P_INV_REQ_FULFILL)]

    def post(self, request, pk):
        requisition = inventory.fulfill_requisition(
            _actor(request), pk, request.data.get("expected_updated_at"))
        return Response(s.RequisitionSerializer(requisition).data)


# ---- Ambulance (CFR-008 / AFR-032) ----------------------------------------


@extend_schema(request=s.AmbulanceLogCreateSerializer,
               responses=s.AmbulanceLogSerializer,
               examples=_EX_AMB)
class AmbulanceLogCreateView(APIView):
    permission_classes = [MODULE, HasPhcPermission(P_AMBULANCE_LOG)]

    def post(self, request):
        ser = s.AmbulanceLogCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        entry = ambulance.log_usage(_actor(request), ser.validated_data)
        return Response(s.AmbulanceLogSerializer(entry).data,
                        status=status.HTTP_201_CREATED)


# ---- Health advisories (CFR-009 / AFR-033) --------------------------------


@extend_schema(request=s.HealthAdvisoryCreateSerializer,
               responses=s.HealthAdvisorySerializer,
               examples=_EX_ADV)
class HealthAdvisoryCreateView(APIView):
    permission_classes = [MODULE, HasPhcPermission(P_ADVISORY_PUBLISH)]

    def post(self, request):
        ser = s.HealthAdvisoryCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        advisory = advisories.publish(_actor(request), ser.validated_data)
        return Response(s.HealthAdvisorySerializer(advisory).data,
                        status=status.HTTP_201_CREATED)


@extend_schema(request=None, responses=s.HealthAdvisorySerializer, examples=_EX_ADV)
class HealthAdvisoryListView(APIView):
    permission_classes = [MODULE, HasPhcPermission(P_ADVISORY_VIEW)]

    def get(self, request):
        return Response({"results": s.HealthAdvisorySerializer(
            scoping.published_advisories(), many=True).data})


# ---- Reports (CFR-010 / AFR-034..035) -------------------------------------


@extend_schema(request=None, responses=OpenApiTypes.OBJECT, examples=_EX_REPORT)
class AdminReportView(APIView):
    permission_classes = [MODULE, HasPhcPermission(P_REPORTS_GENERATE)]

    def get(self, request):
        category = request.query_params.get("category", "demographics")
        return Response(reports.generate(_actor(request), category))


# ---- Audit trail (CFR-012 / AFR-037) --------------------------------------


@extend_schema(request=None, responses=s.AuditLogSerializer, examples=_EX_AUDIT)
class AuditLogView(APIView):
    permission_classes = [MODULE, HasPhcPermission(P_AUDIT_VIEW)]

    def get(self, request):
        limit = _positive_limit(request.query_params.get("limit"))
        return Response({"results": s.AuditLogSerializer(
            scoping.audit_logs(limit), many=True).data})
