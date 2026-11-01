"""Visit requests: pre-registration by a requester, decision by the host."""
import secrets
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from fusion_auth.permissions import HasPermission
from modules.vms.models import (
    AccessPolicy, BlacklistEntry, VisitPass, VisitRequest, Visitor,
)

ID_DOC_TYPES = ["passport", "aadhaar", "driving_licence", "voter_id"]


def _uid(request):
    return request.principal.user_id


class PreRegistrationSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    phone = serializers.CharField(max_length=20)
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    id_doc_type = serializers.ChoiceField(choices=ID_DOC_TYPES)
    id_doc_number = serializers.CharField(max_length=60)
    host_user_id = serializers.IntegerField()
    purpose = serializers.CharField(max_length=255)
    scheduled_start = serializers.DateTimeField()
    scheduled_end = serializers.DateTimeField()
    requested_zones = serializers.PrimaryKeyRelatedField(
        many=True, required=False,
        queryset=VisitRequest.requested_zones.rel.model.objects.all())

    def validate(self, attrs):
        if attrs["scheduled_end"] <= attrs["scheduled_start"]:
            raise serializers.ValidationError("scheduled_end must follow scheduled_start.")
        return attrs


class VisitRequestSerializer(serializers.ModelSerializer):
    visitor_name = serializers.CharField(source="visitor.full_name")
    requested_zones = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = VisitRequest
        fields = ["id", "visitor_name", "host_user_id", "purpose", "scheduled_start",
                  "scheduled_end", "status", "requested_zones", "decision_note",
                  "decided_at", "created_at"]


class VisitPassSerializer(serializers.ModelSerializer):
    allowed_zones = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = VisitPass
        fields = ["id", "visit_request", "pass_type", "qr_token", "otp",
                  "valid_from", "valid_until", "is_active", "allowed_zones"]


class DecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject"])
    note = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


class PreRegistrationView(APIView):
    permission_classes = [HasPermission("vms.request.create")]

    def get(self, request):
        # VisitRequest records no creator, so "own" = requests whose visitor
        # email matches the principal's email; empty if the principal has none.
        email = getattr(request.principal, "email", "")
        rows = (VisitRequest.objects.filter(visitor__email__iexact=email)
                if email else VisitRequest.objects.none())
        rows = rows.select_related("visitor").order_by("-created_at")
        return Response({"results": VisitRequestSerializer(rows, many=True).data})

    def post(self, request):
        ser = PreRegistrationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        today = timezone.localdate()
        # VMS-BR-051: active, unexpired blacklist match on ID number.
        if (BlacklistEntry.objects.filter(is_active=True, id_doc_number=d["id_doc_number"])
                .exclude(expiry_date__lt=today).exists()):
            raise BadRequestError("This visitor is not permitted entry.",
                                  code="visitor_blacklisted")
        with transaction.atomic():
            visitor, _ = Visitor.objects.get_or_create(
                id_doc_number=d["id_doc_number"], id_doc_type=d["id_doc_type"],
                defaults={"full_name": d["full_name"], "phone": d["phone"],
                          "email": d["email"]})
            # VMS-BR-038: no duplicate pending request.
            if VisitRequest.objects.filter(
                    visitor=visitor, host_user_id=d["host_user_id"],
                    scheduled_start=d["scheduled_start"],
                    status=VisitRequest.Status.PENDING).exists():
                raise BadRequestError("A pending request already exists for this visit.",
                                      code="duplicate_request")
            vr = VisitRequest.objects.create(
                visitor=visitor, host_user_id=d["host_user_id"], purpose=d["purpose"],
                scheduled_start=d["scheduled_start"], scheduled_end=d["scheduled_end"])
            vr.requested_zones.set(d.get("requested_zones", []))
        return Response(VisitRequestSerializer(vr).data, status=status.HTTP_201_CREATED)


class HostPendingListView(APIView):
    permission_classes = [HasPermission("vms.request.decide")]

    def get(self, request):
        rows = (VisitRequest.objects
                .filter(host_user_id=_uid(request), status=VisitRequest.Status.PENDING)
                .select_related("visitor").order_by("scheduled_start"))
        return Response({"results": VisitRequestSerializer(rows, many=True).data})


class HostDecisionView(APIView):
    permission_classes = [HasPermission("vms.request.decide")]

    def post(self, request, pk):
        ser = DecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        with transaction.atomic():
            vr = (VisitRequest.objects.select_for_update()
                  .filter(pk=pk, host_user_id=_uid(request)).first())
            if vr is None:
                raise NotFoundError()
            if vr.status != VisitRequest.Status.PENDING:
                raise ConflictError("Only a pending request can be decided.")
            approve = d["decision"] == "approve"
            vr.status = VisitRequest.Status.APPROVED if approve else VisitRequest.Status.REJECTED
            vr.decision_note = d["note"]
            vr.decided_at = timezone.now()
            vr.save()
            if not approve:
                return Response(VisitRequestSerializer(vr).data)
            policy = (AccessPolicy.objects.filter(status=AccessPolicy.Status.PUBLISHED)
                      .order_by("-version").first())
            until = vr.scheduled_end
            if policy:
                until = min(until, vr.scheduled_start + timedelta(hours=policy.max_visit_hours))
            vp = VisitPass.objects.create(
                visit_request=vr, pass_type=VisitPass.PassType.PRE_REGISTERED,
                qr_token=secrets.token_urlsafe(32), otp=f"{secrets.randbelow(10**6):06d}",
                valid_from=vr.scheduled_start, valid_until=until,
                issued_by_user_id=_uid(request))
            vp.allowed_zones.set(vr.requested_zones.all())
        return Response(VisitPassSerializer(vp).data, status=status.HTTP_201_CREATED)
