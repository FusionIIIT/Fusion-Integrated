"""PHC API views — direct, prompt-generated style.

Each endpoint handles its own validation and writes inline so the code reads
like it came straight out of an LLM prompt: straightforward, repetitive, and
easy to trace. Role checks use the permission codes from registry.py.
"""
from __future__ import annotations

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, NotFoundError
from fusion_auth.permissions import HasModuleGrant
from modules.phc.api import serializers as s
from modules.phc.api.permissions import HasPhcPermission
from modules.phc.models import (
    AmbulanceLog,
    AuditLog,
    DoctorAttendance,
    DoctorSchedule,
    HealthAdvisory,
    InventoryItem,
    Patient,
    Prescription,
    ReimbursementClaim,
    Requisition,
    RequisitionItem,
    StockAdjustment,
    Visit,
)

MODULE = HasModuleGrant("phc")

# permission codes
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
P_INV_REQ_SUBMIT = "phc.inventory.requisition.submit"
P_INV_REQ_DECIDE = "phc.inventory.requisition.decide"
P_INV_REQ_FULFILL = "phc.inventory.requisition.fulfill"
P_AMBULANCE_LOG = "phc.ambulance.log"
P_ADVISORY_VIEW = "phc.advisory.view"
P_ADVISORY_PUBLISH = "phc.advisory.publish"
P_REPORTS_GENERATE = "phc.reports.generate"
P_AUDIT_VIEW = "phc.audit.view"


def _actor(request):
    return getattr(request, "principal", None)


def _audit(actor, action, target_type, target_id, detail=None):
    AuditLog.objects.create(
        actor=actor.user_id if actor else None,
        actor_role=getattr(actor, "active_role", "") or "",
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=detail or {},
    )


# ---------------- Doctor schedule & availability (CFR-001 / AFR-001..005) ----------------


@extend_schema(responses=s.DoctorScheduleSerializer(many=True))
class DoctorScheduleListView(APIView):
    permission_classes = [HasModuleGrant("phc"), HasPhcPermission(P_SCHEDULE_VIEW)]

    def get(self, request):
        schedules = DoctorSchedule.objects.filter(is_published=True)
        today = timezone.now().date()
        attendance = {
            a.doctor_name: a.status
            for a in DoctorAttendance.objects.filter(date=today)
        }
        data = s.DoctorScheduleSerializer(schedules, many=True).data
        return Response({"schedules": data, "attendance": attendance})


class DoctorScheduleCreateView(APIView):
    permission_classes = [HasModuleGrant("phc"), HasPhcPermission(P_SCHEDULE_MANAGE)]

    def post(self, request):
        ser = s.DoctorScheduleCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data
        schedule = DoctorSchedule.objects.create(
            doctor_name=v["doctor_name"],
            day_of_week=v["day_of_week"],
            start_time=v["start_time"],
            end_time=v["end_time"],
            is_published=False,
            published_by=_actor(request).user_id if _actor(request) else None,
        )
        _audit(_actor(request), "schedule.create", "schedule", schedule.id, v)
        return Response(s.DoctorScheduleSerializer(schedule).data,
                        status=status.HTTP_201_CREATED)


class DoctorScheduleMaintainView(APIView):
    permission_classes = [HasModuleGrant("phc"), HasPhcPermission(P_SCHEDULE_MANAGE)]

    def patch(self, request, pk):
        ser = s.DoctorScheduleMaintainSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data
        schedule = DoctorSchedule.objects.filter(pk=pk).first()
        if schedule is None:
            raise NotFoundError("schedule not found.", code="not_found")
        if "day_of_week" in v:
            schedule.day_of_week = v["day_of_week"]
        if "start_time" in v:
            schedule.start_time = v["start_time"]
        if "end_time" in v:
            schedule.end_time = v["end_time"]
        schedule.save()
        _audit(_actor(request), "schedule.maintain", "schedule", pk, v)
        return Response(s.DoctorScheduleSerializer(schedule).data)


class DoctorSchedulePublishView(APIView):
    permission_classes = [HasModuleGrant("phc"), HasPhcPermission(P_SCHEDULE_MANAGE)]

    def post(self, request, pk):
        schedule = DoctorSchedule.objects.filter(pk=pk).first()
        if schedule is None:
            raise NotFoundError("schedule not found.", code="not_found")
        schedule.is_published = True
        schedule.published_at = timezone.now()
        schedule.published_by = _actor(request).user_id if _actor(request) else None
        schedule.save()
        _audit(_actor(request), "schedule.publish", "schedule", pk, {})
        return Response(s.DoctorScheduleSerializer(schedule).data)


class DoctorAttendanceMarkView(APIView):
    permission_classes = [HasModuleGrant("phc"), HasPhcPermission(P_SCHEDULE_MANAGE)]

    def post(self, request):
        ser = s.DoctorAttendanceMarkSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data
        att, _ = DoctorAttendance.objects.update_or_create(
            doctor_name=v["doctor_name"], date=v["date"],
            defaults={"status": v["status"],
                      "updated_by": _actor(request).user_id if _actor(request) else None},
        )
        _audit(_actor(request), "attendance.mark", "attendance", att.id, v)
        return Response(s.DoctorAttendanceSerializer(att).data,
                        status=status.HTTP_201_CREATED)


# ---------------- Patient records & prescriptions (CFR-002 / AFR-006..012) ----------------


class PatientSearchView(APIView):
    permission_classes = [HasModuleGrant("phc"), HasPhcPermission(P_RECORDS_MANAGE)]

    def get(self, request):
        q = (request.query_params.get("q") or "").strip()
        if len(q) < 2:
            return Response({"results": []})
        rows = Patient.objects.filter(
            display_name__icontains=q
        ).order_by("display_name")[:25]
        return Response({"results": [
            {"user_id": r.user_id, "display_name": r.display_name, "kind": r.kind}
            for r in rows
        ]})


class VisitCreateView(APIView):
    permission_classes = [HasModuleGrant("phc"), HasPhcPermission(P_RECORDS_MANAGE)]

    def post(self, request):
        ser = s.VisitCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data
        patient = Patient.objects.filter(pk=v["patient_id"]).first()
        if patient is None:
            raise NotFoundError("patient not found.", code="not_found")
        visit = Visit.objects.create(
            patient=patient,
            recorded_by=_actor(request).user_id if _actor(request) else None,
            notes=v.get("notes", ""),
        )
        _audit(_actor(request), "visit.create", "visit", visit.id,
               {"patient_id": visit.patient_id})
        return Response(s.VisitSerializer(visit).data,
                        status=status.HTTP_201_CREATED)


class PrescriptionCreateView(APIView):
    permission_classes = [HasModuleGrant("phc"), HasPhcPermission(P_RECORDS_MANAGE)]

    def post(self, request):
        ser = s.PrescriptionCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data
        visit = Visit.objects.filter(pk=v["visit_id"], patient_id=v["patient_id"]).first()
        if visit is None:
            raise NotFoundError("visit not found for this patient.", code="not_found")
        prescription = Prescription.objects.create(
            visit=visit,
            patient_id=v["patient_id"],
            medicine=v["medicine"],
            dosage=v.get("dosage", ""),
            recorded_by=_actor(request).user_id if _actor(request) else None,
        )
        _audit(_actor(request), "prescription.create", "prescription",
               prescription.id, {"patient_id": prescription.patient_id})
        return Response(s.PrescriptionSerializer(prescription).data,
                        status=status.HTTP_201_CREATED)


class PatientRecordsView(APIView):
    permission_classes = [HasModuleGrant("phc"), HasPhcPermission(P_RECORDS_VIEW_SELF)]

    def get(self, request):
        principal = _actor(request)
        visits = Visit.objects.filter(patient_id=principal.user_id).order_by("-visit_date")
        return Response({"results": s.VisitSerializer(visits, many=True).data})


class PatientPrescriptionsView(APIView):
    permission_classes = [HasModuleGrant("phc"), HasPhcPermission(P_RECORDS_VIEW_SELF)]

    def get(self, request):
        principal = _actor(request)
        prescriptions = Prescription.objects.filter(
            patient_id=principal.user_id).order_by("-created_at")
        return Response({"results": s.PrescriptionSerializer(prescriptions, many=True).data})


class RecordDownloadView(APIView):
    permission_classes = [HasModuleGrant("phc"), HasPhcPermission(P_RECORDS_VIEW_SELF)]

    def get(self, request, pk):
        principal = _actor(request)
        visit = Visit.objects.filter(pk=pk, patient_id=principal.user_id).first()
        if visit is None:
            raise NotFoundError("record not found or not yours.", code="not_found")
        prescriptions = Prescription.objects.filter(patient_id=principal.user_id,
                                                    visit=visit)
        payload = {
            "record_id": visit.id,
            "patient_id": visit.patient_id,
            "visit_date": visit.visit_date.isoformat(),
            "notes": visit.notes,
            "prescriptions": [
                {"medicine": p.medicine, "dosage": p.dosage} for p in prescriptions
            ],
        }
        return Response(payload)


# ---------------- Reimbursement (CFR-003, CFR-004, CFR-005 / AFR-013..023, 038) ----------------


class ReimbursementClaimCreateView(APIView):
    permission_classes = [HasModuleGrant("phc"), HasPhcPermission(P_CLAIM_SUBMIT)]

    def post(self, request):
        principal = _actor(request)
        kind = getattr(principal, "kind", "")
        if kind not in ("employee", "staff", "faculty"):
            raise BadRequestError("reimbursement is employee-only.", code="forbidden")
        ser = s.ReimbursementClaimCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data
        window_days = 90
        if (timezone.now().date() - v["expense_date"]).days > window_days:
            raise BadRequestError("expense outside submission window.", code="forbidden")
        prescription = Prescription.objects.filter(
            pk=v["prescription_id"], patient_id=principal.user_id).first()
        if prescription is None:
            raise BadRequestError("invalid prescription link.", code="forbidden")
        claim = ReimbursementClaim.objects.create(
            employee_id=principal.user_id,
            prescription=prescription,
            expense_date=v["expense_date"],
            amount=v["amount"],
            description=v.get("description", ""),
            state="submitted",
            stage_actor="PHC Staff",
            action_history=["submitted by employee"],
        )
        _audit(principal, "claim.submit", "claim", claim.claim_id,
               {"state": claim.state})
        return Response(s.ReimbursementClaimSerializer(claim).data,
                        status=status.HTTP_201_CREATED)


class MyClaimsView(APIView):
    permission_classes = [HasModuleGrant("phc"), HasPhcPermission(P_CLAIM_VIEW_SELF)]

    def get(self, request):
        principal = _actor(request)
        claims = ReimbursementClaim.objects.filter(
            employee_id=principal.user_id).order_by("-created_at")
        return Response({"results": s.ReimbursementClaimSerializer(claims, many=True).data})


class ClaimReviewView(APIView):
    permission_classes = [HasModuleGrant("phc"), HasPhcPermission(P_CLAIM_REVIEW)]

    def post(self, request, pk):
        principal = _actor(request)
        claim = ReimbursementClaim.objects.filter(
            pk=pk, state="submitted").first()
        if claim is None:
            raise NotFoundError("claim not found or not at review stage.",
                                code="not_found")
        claim.state = "pending_audit"
        claim.action_history = [*list(claim.action_history or []),
                                "PHC review forwarded to Accounts & Audit"]
        claim.save()
        _audit(principal, "claim.review", "claim", claim.claim_id,
               {"state": claim.state})
        return Response(s.ReimbursementClaimSerializer(claim).data)


class ClaimVerifyView(APIView):
    permission_classes = [HasModuleGrant("phc"), HasPhcPermission(P_CLAIM_VERIFY)]

    def post(self, request, pk):
        principal = _actor(request)
        claim = ReimbursementClaim.objects.filter(
            pk=pk, state="pending_audit").first()
        if claim is None:
            raise NotFoundError("claim not found or not at verification stage.",
                                code="not_found")
        claim.state = "pending_sanction"
        claim.action_history = [*list(claim.action_history or []),
                                "Accounts & Audit verified, forwarded for sanction"]
        claim.save()
        _audit(principal, "claim.verify", "claim", claim.claim_id,
               {"state": claim.state})
        return Response(s.ReimbursementClaimSerializer(claim).data)


class ClaimSanctionView(APIView):
    permission_classes = [HasModuleGrant("phc"), HasPhcPermission(P_CLAIM_SANCTION)]

    def post(self, request, pk):
        principal = _actor(request)
        ser = s.SanctionDecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data
        claim = ReimbursementClaim.objects.filter(
            pk=pk, state="pending_sanction").first()
        if claim is None:
            raise NotFoundError("claim not found or not at sanction stage.",
                                code="not_found")
        if v["decision"] == "approve":
            claim.state = "approved_for_payment"
            claim.action_history = [*list(claim.action_history or []),
                                    "Sanction approved"]
            claim.save()
            _audit(principal, "claim.sanction_approve", "claim",
                   claim.claim_id, {"state": claim.state})
        else:
            claim.state = "rejected"
            claim.action_history = [*list(claim.action_history or []),
                                    "Sanction rejected (terminal)"]
            claim.save()
            _audit(principal, "claim.sanction_reject", "claim",
                   claim.claim_id, {"state": claim.state})
        return Response(s.ReimbursementClaimSerializer(claim).data)


class ClaimPaymentView(APIView):
    permission_classes = [HasModuleGrant("phc"), HasPhcPermission(P_CLAIM_PAYMENT)]

    def post(self, request, pk):
        principal = _actor(request)
        claim = ReimbursementClaim.objects.filter(
            pk=pk, state="approved_for_payment").first()
        if claim is None:
            raise NotFoundError("claim not found or not approved for payment.",
                                code="not_found")
        claim.state = "reimbursed"
        claim.action_history = [*list(claim.action_history or []),
                                "Payment processed, claim reimbursed"]
        claim.save()
        _audit(principal, "claim.payment", "claim", claim.claim_id,
               {"state": claim.state})
        return Response(s.ReimbursementClaimSerializer(claim).data)


# ---------------- Inventory & procurement (CFR-006, CFR-007 / AFR-024..031) ----------------


class StockAdjustView(APIView):
    permission_classes = [HasModuleGrant("phc"), HasPhcPermission(P_INV_ADJUST)]

    def post(self, request):
        principal = _actor(request)
        ser = s.StockAdjustmentCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data
        item = InventoryItem.objects.filter(pk=v["item_id"]).first()
        if item is None:
            raise NotFoundError("item not found.", code="not_found")
        delta = v["quantity"] if v["direction"] == "add" else -v["quantity"]
        item.quantity = max(0, item.quantity + delta)
        item.save()
        adjustment = StockAdjustment.objects.create(
            item=item, quantity=v["quantity"], direction=v["direction"],
            adjusted_by=principal.user_id if principal else None,
            reason=v.get("reason", ""),
        )
        below = item.quantity < item.reorder_threshold
        _audit(principal, "inventory.adjust", "inventory", item.id,
               {"direction": v["direction"], "quantity": v["quantity"],
                "below_threshold": below})
        return Response(s.StockAdjustmentSerializer(adjustment).data,
                        status=status.HTTP_201_CREATED)


class InventoryItemListCreateView(APIView):
    permission_classes = [HasModuleGrant("phc"), HasPhcPermission(P_INV_ADJUST)]

    def get(self, request):
        rows = InventoryItem.objects.order_by("name")
        return Response({"results": s.InventoryItemSerializer(rows, many=True).data})

    def post(self, request):
        ser = s.InventoryItemCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data
        item = InventoryItem.objects.create(
            name=v["name"],
            unit=v.get("unit", "units"),
            reorder_threshold=v.get("reorder_threshold", 0),
        )
        return Response(s.InventoryItemSerializer(item).data,
                        status=status.HTTP_201_CREATED)


class RequisitionCreateView(APIView):
    permission_classes = [HasModuleGrant("phc"), HasPhcPermission(P_INV_REQ_SUBMIT)]

    def post(self, request):
        principal = _actor(request)
        ser = s.RequisitionCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data
        requisition = Requisition.objects.create(
            originator_id=principal.user_id if principal else None,
            state="pending_approval",
        )
        for line in v["items"]:
            RequisitionItem.objects.create(
                requisition=requisition,
                item_id=line["item_id"],
                quantity=line["quantity"],
            )
        _audit(principal, "requisition.submit", "requisition",
               requisition.requisition_id, {"state": requisition.state})
        return Response(s.RequisitionSerializer(requisition).data,
                        status=status.HTTP_201_CREATED)


class RequisitionDecideView(APIView):
    permission_classes = [HasModuleGrant("phc"), HasPhcPermission(P_INV_REQ_DECIDE)]

    def post(self, request, pk):
        principal = _actor(request)
        ser = s.RequisitionDecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data
        requisition = Requisition.objects.filter(
            pk=pk, state="pending_approval").first()
        if requisition is None:
            raise NotFoundError("requisition not found or not pending.",
                                code="not_found")
        requisition.state = "approved" if v["decision"] == "approve" else "rejected"
        requisition.decided_by = principal.user_id if principal else None
        requisition.decided_at = timezone.now()
        requisition.decision_note = v.get("note", "")
        requisition.save()
        action = "requisition.approve" if requisition.state == "approved" \
            else "requisition.reject"
        _audit(principal, action, "requisition", requisition.requisition_id,
               {"state": requisition.state})
        return Response(s.RequisitionSerializer(requisition).data)


class RequisitionFulfillView(APIView):
    permission_classes = [HasModuleGrant("phc"), HasPhcPermission(P_INV_REQ_FULFILL)]

    def post(self, request, pk):
        principal = _actor(request)
        requisition = Requisition.objects.filter(
            pk=pk, state="approved").first()
        if requisition is None:
            raise NotFoundError("requisition not found or not approved.",
                                code="not_found")
        requisition.state = "fulfilled"
        requisition.save()
        _audit(principal, "requisition.fulfill", "requisition",
               requisition.requisition_id, {"state": requisition.state})
        return Response(s.RequisitionSerializer(requisition).data)


# ---------------- Ambulance (CFR-008 / AFR-032) ----------------


class AmbulanceLogCreateView(APIView):
    permission_classes = [HasModuleGrant("phc"), HasPhcPermission(P_AMBULANCE_LOG)]

    def post(self, request):
        principal = _actor(request)
        ser = s.AmbulanceLogCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data
        log = AmbulanceLog.objects.create(
            timestamp=v["timestamp"],
            patient_name=v["patient_name"],
            destination=v["destination"],
            logged_by=principal.user_id if principal else None,
        )
        _audit(principal, "ambulance.log", "ambulance", log.id,
               {"patient_name": log.patient_name})
        return Response(s.AmbulanceLogSerializer(log).data,
                        status=status.HTTP_201_CREATED)


# ---------------- Health advisories (CFR-009 / AFR-033) ----------------


class HealthAdvisoryCreateView(APIView):
    permission_classes = [HasModuleGrant("phc"), HasPhcPermission(P_ADVISORY_PUBLISH)]

    def post(self, request):
        principal = _actor(request)
        ser = s.HealthAdvisoryCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data
        advisory = HealthAdvisory.objects.create(
            title=v["title"],
            content=v["content"],
            is_published=True,
            published_at=timezone.now(),
            published_by=principal.user_id if principal else None,
        )
        _audit(principal, "advisory.publish", "advisory", advisory.id,
               {"title": advisory.title})
        return Response(s.HealthAdvisorySerializer(advisory).data,
                        status=status.HTTP_201_CREATED)


class HealthAdvisoryListView(APIView):
    permission_classes = [HasModuleGrant("phc"), HasPhcPermission(P_ADVISORY_VIEW)]

    def get(self, request):
        rows = HealthAdvisory.objects.filter(is_published=True).order_by("-published_at")
        return Response({"results": s.HealthAdvisorySerializer(rows, many=True).data})


# ---------------- Reports (CFR-010 / AFR-034..035) ----------------


class AdminReportView(APIView):
    permission_classes = [HasModuleGrant("phc"), HasPhcPermission(P_REPORTS_GENERATE)]

    def get(self, request):
        category = request.query_params.get("category", "demographics")
        if category == "demographics":
            kinds = {}
            for p in Patient.objects.all():
                kinds[p.kind] = kinds.get(p.kind, 0) + 1
            report = {
                "category": "demographics",
                "patient_count_by_kind": kinds,
                "note": "counts only; no patient-identifiable information",
            }
        elif category == "utilization":
            report = {
                "category": "utilization",
                "visits": Visit.objects.count(),
                "prescriptions": Prescription.objects.count(),
                "ambulance_logs": AmbulanceLog.objects.count(),
                "claims": ReimbursementClaim.objects.count(),
                "requisitions": Requisition.objects.count(),
                "note": "aggregate counts only",
            }
        elif category == "inventory":
            low = [i.name for i in InventoryItem.objects.all()
                   if i.quantity < i.reorder_threshold]
            report = {
                "category": "inventory",
                "stock_adjustments": StockAdjustment.objects.count(),
                "items": InventoryItem.objects.count(),
                "low_stock_items": low,
                "note": "item names only; no patient data",
            }
        else:
            report = {"category": category, "error": "unknown report category"}
        _audit(_actor(request), "report.generate", "report", 0,
               {"category": category})
        return Response(report)


# ---------------- Audit trail (CFR-012 / AFR-037) ----------------


class AuditLogView(APIView):
    permission_classes = [HasModuleGrant("phc"), HasPhcPermission(P_AUDIT_VIEW)]

    def get(self, request):
        limit = int(request.query_params.get("limit", 50))
        rows = AuditLog.objects.all()[:limit]
        return Response({"results": s.AuditLogSerializer(rows, many=True).data})
