from django.db import transaction
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant
from modules.elm.api.serializers import (
    LeaveBalanceSerializer, LeaveDecisionSerializer, LeaveRequestCreateSerializer,
    LeaveRequestSerializer,
)
from modules.elm.models import LeaveAction, LeaveBalance, LeaveRequest

MODULE = HasModuleGrant("elm")


def _actor_id(request):
    principal = getattr(request, "principal", None)
    value = getattr(principal, "user_id", None)
    if value is None:
        value = getattr(principal, "id", None)
    if value is None:
        raise PermissionDenied("Authenticated Fusion employee identity is required.")
    return int(value)


class MyLeaveBalancesView(generics.ListAPIView):
    serializer_class = LeaveBalanceSerializer
    permission_classes = [MODULE]

    def get_queryset(self):
        return LeaveBalance.objects.filter(user_id=_actor_id(self.request)).order_by(
            "year", "category")


class LeaveRequestListCreateView(APIView):
    permission_classes = [MODULE]

    def get(self, request):
        actor_id = _actor_id(request)
        qs = LeaveRequest.objects.filter(applicant_user_id=actor_id).prefetch_related("actions")
        return Response(LeaveRequestSerializer(qs, many=True).data)

    def post(self, request):
        actor_id = _actor_id(request)
        payload = LeaveRequestCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = dict(payload.validated_data)
        substitute_id = data.get("substitute_user_id")
        if substitute_id == actor_id:
            raise ValidationError({"substitute_user_id": "Applicant cannot be their own substitute."})
        # This initial slice records the application and audit event. Full policy,
        # calendar, overlap, consent, and hierarchy validation remain follow-up work.
        status_value = "awaiting_substitute" if substitute_id else "unit_head_review"
        with transaction.atomic():
            obj = LeaveRequest.objects.create(
                applicant_user_id=actor_id, status=status_value, **data)
            LeaveAction.objects.create(
                request=obj, actor_user_id=actor_id, action="submitted",
                to_status=status_value, note="")
        return Response(LeaveRequestSerializer(obj).data, status=status.HTTP_201_CREATED)


class LeaveRequestDetailView(generics.RetrieveAPIView):
    serializer_class = LeaveRequestSerializer
    permission_classes = [MODULE]

    def get_queryset(self):
        actor_id = _actor_id(self.request)
        return LeaveRequest.objects.filter(applicant_user_id=actor_id).prefetch_related("actions")


class LeaveRequestDecisionView(APIView):
    permission_classes = [MODULE]

    def post(self, request, pk):
        actor_id = _actor_id(request)
        payload = LeaveDecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        action = payload.validated_data["action"]
        note = payload.validated_data["note"]
        with transaction.atomic():
            obj = LeaveRequest.objects.select_for_update().filter(pk=pk).first()
            if obj is None:
                return Response({"detail": "Not found."}, status=404)
            previous = obj.status
            if action == "withdraw":
                if obj.applicant_user_id != actor_id:
                    raise PermissionDenied("Only the applicant can withdraw this request.")
                if obj.status in ("approved", "rejected", "withdrawn", "cancelled"):
                    raise ValidationError({"action": "This request can no longer be withdrawn."})
                obj.status = "withdrawn"
            elif action in ("substitute_accept", "substitute_decline"):
                if obj.substitute_user_id != actor_id or obj.status != "awaiting_substitute":
                    raise PermissionDenied("No pending substitute response is assigned to you.")
                obj.substitute_response = "accepted" if action == "substitute_accept" else "declined"
                obj.status = "unit_head_review" if action == "substitute_accept" else "applicant_action_required"
            else:
                if obj.current_reviewer_user_id != actor_id:
                    raise PermissionDenied("This request is not assigned to you.")
                if action == "recommend":
                    obj.status = "higher_sanction"
                elif action == "not_recommend":
                    obj.status = "higher_sanction"
                elif action in ("approve", "reject"):
                    obj.status = "approved" if action == "approve" else "rejected"
                    obj.final_decision_by_user_id = actor_id
                    obj.final_decision_at = timezone.now()
                    obj.decision_note = note
                else:
                    raise ValidationError({"action": "Unsupported action."})
            obj.save()
            LeaveAction.objects.create(request=obj, actor_user_id=actor_id,
                action=action, note=note, from_status=previous, to_status=obj.status)
        return Response(LeaveRequestSerializer(obj).data)
