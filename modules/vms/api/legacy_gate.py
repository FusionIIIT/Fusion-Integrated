"""Gate, blacklist and policy endpoints (SRS 3.14)."""
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, NotFoundError
from fusion_auth.permissions import HasPermission
from modules.vms.models import (
    AccessPolicy, BlacklistEntry, VisitLog, VisitPass, VisitRequest,
)

E = VisitLog.Event


def _uid(request):
    return request.principal.user_id


def _last_event(vp):
    log = (vp.logs.exclude(event=E.DENIED).order_by("-id").first())
    return log.event if log else None


def _deny(vp, request, reason, zone=None):
    VisitLog.objects.create(visit_pass=vp, event=E.DENIED, reason=reason,
                            zone=zone, logged_by_user_id=_uid(request))
    return Response({"detail": reason}, status=status.HTTP_403_FORBIDDEN)


def _find_pass(data):
    qs = VisitPass.objects.select_related("visit_request__visitor")
    if data.get("qr_token"):
        return qs.filter(qr_token=data["qr_token"]).first()
    if data.get("otp"):
        return qs.filter(otp=data["otp"], is_active=True).order_by("-id").first()
    raise BadRequestError("qr_token or otp is required.")


class GateValidateView(APIView):
    permission_classes = [HasPermission("vms.gate.operate")]

    @transaction.atomic
    def post(self, request):
        d = request.data
        vp = _find_pass(d)
        if vp is None:
            return Response({"detail": "Pass not found."}, status=403)
        now = timezone.now()
        zone = None
        if d.get("zone_id"):
            zone = vp.allowed_zones.filter(pk=d["zone_id"]).first()
        if not vp.is_active:
            return _deny(vp, request, "Pass is not active.")
        if not vp.valid_from <= now <= vp.valid_until:
            return _deny(vp, request, "Pass is outside its validity window.")
        doc = vp.visit_request.visitor.id_doc_number
        if doc and BlacklistEntry.objects.filter(id_doc_number=doc, is_active=True).exclude(
                expiry_date__lt=now.date()).exists():
            return _deny(vp, request, "Visitor is blacklisted.")
        if d.get("zone_id") and zone is None:
            return _deny(vp, request, "Zone not permitted for this pass.")
        if _last_event(vp) == E.CHECK_IN:
            return _deny(vp, request, "Already checked in.")
        VisitLog.objects.create(visit_pass=vp, event=E.CHECK_IN, zone=zone,
                                logged_by_user_id=_uid(request))
        return Response({"detail": "Checked in.", "visit_request_id": vp.visit_request_id})


class GateCheckoutView(APIView):
    permission_classes = [HasPermission("vms.gate.operate")]

    @transaction.atomic
    def post(self, request):
        vp = VisitPass.objects.filter(qr_token=request.data.get("qr_token") or "").first()
        if vp is None:
            raise NotFoundError("Pass not found.")
        if _last_event(vp) != E.CHECK_IN:
            raise BadRequestError("No open check-in for this pass.")
        VisitLog.objects.create(visit_pass=vp, event=E.CHECK_OUT,
                                logged_by_user_id=_uid(request))
        VisitRequest.objects.filter(pk=vp.visit_request_id).update(
            status=VisitRequest.Status.COMPLETED)
        return Response({"detail": "Checked out."})


class BlacklistSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlacklistEntry
        fields = "__all__"


class BlacklistView(APIView):
    permission_classes = [HasPermission("vms.blacklist.manage")]

    def get(self, request):
        rows = BlacklistEntry.objects.order_by("-id")
        return Response(BlacklistSerializer(rows, many=True).data)

    def post(self, request):
        ser = BlacklistSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data, status=status.HTTP_201_CREATED)


class PolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessPolicy
        fields = "__all__"


class PolicyPublishView(APIView):
    permission_classes = [HasPermission("vms.policy.publish")]

    def get(self, request, pk=None):
        rows = AccessPolicy.objects.order_by("-version")
        return Response(PolicySerializer(rows, many=True).data)

    def post(self, request, pk):
        policy = AccessPolicy.objects.filter(pk=pk).first()
        if policy is None:
            raise NotFoundError("Policy not found.")
        policy.status = AccessPolicy.Status.PUBLISHED
        policy.published_at = timezone.now()
        policy.save(update_fields=["status", "published_at"])
        return Response(PolicySerializer(policy).data)
