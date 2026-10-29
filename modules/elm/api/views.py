from django.db.models import Q
from rest_framework import generics, status
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.models import LeaveRequest, LeaveAccount, LeavePolicy
from modules.elm.api.serializers import LeaveRequestSerializer, LeaveAccountSerializer, LeavePolicySerializer
from modules.elm.services.workflow import submit, transition

MODULE = HasModuleGrant("elm")
P_SELF = "elm.leave.view_self"
P_APPLY = "elm.leave.apply"
P_RESPOND = "elm.substitute.respond"
P_REVIEW = "elm.leave.review"
P_CONFIG = "elm.leave.configure"

def actor(request): return getattr(request, "principal", None)


class MyLeaveView(generics.ListAPIView):
    serializer_class = LeaveRequestSerializer
    permission_classes = [MODULE, HasPermission(P_SELF)]
    def get_queryset(self): return LeaveRequest.objects.filter(user_id=actor(self.request).user_id)


class ApplyLeaveView(APIView):
    permission_classes = [MODULE, HasPermission(P_APPLY)]
    def post(self, request):
        serializer = LeaveRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = submit(actor=actor(request), data=serializer.validated_data)
        return Response(LeaveRequestSerializer(obj).data, status=status.HTTP_201_CREATED)

class LeaveActionView(APIView):
    permission_classes = [MODULE]
    def post(self, request, pk):
        action = request.data.get("action", "")
        if action in ("withdraw",):
            permission = HasPermission(P_SELF)
        elif action in ("accept_substitute","decline_substitute"):
            permission = HasPermission(P_RESPOND)
        elif action in ("approve","not_recommended","final_approve","final_reject"):
            permission = HasPermission(P_REVIEW)
        else:
            return Response({"detail":"Unsupported action."}, status=400)
        if not permission().has_permission(request, self): return Response({"detail":"Permission denied."},status=403)
        qs = LeaveRequest.objects.all()
        if action == "withdraw": qs = qs.filter(user_id=actor(request).user_id)
        obj = qs.filter(pk=pk).first()
        if not obj: return Response({"detail":"Leave request not found."},status=404)
        obj = transition(request_obj=obj, actor=actor(request), action=action, reason=request.data.get("reason", ""))
        return Response(LeaveRequestSerializer(obj).data)
class LeaveAccountsView(generics.ListAPIView):
    serializer_class = LeaveAccountSerializer
    permission_classes = [MODULE, HasPermission(P_SELF)]
    def get_queryset(self): return LeaveAccount.objects.filter(user_id=actor(self.request).user_id).order_by("category")
class PendingApprovalsView(generics.ListAPIView):
    serializer_class = LeaveRequestSerializer
    permission_classes = [MODULE, HasPermission(P_REVIEW)]
    def get_queryset(self): return LeaveRequest.objects.filter(status__in=["awaiting_unit_head_review","awaiting_final_sanction_decision","awaiting_director_self_sanction"]).order_by("created_at")
class SubstituteRequestsView(generics.ListAPIView):
    serializer_class = LeaveRequestSerializer
    permission_classes = [MODULE, HasPermission(P_RESPOND)]
    def get_queryset(self): return LeaveRequest.objects.filter(substitute_user_id=actor(self.request).user_id,status="awaiting_substitute_response")
class LeavePolicyView(generics.ListCreateAPIView):
    serializer_class = LeavePolicySerializer
    permission_classes = [MODULE, HasPermission(P_CONFIG)]
    queryset = LeavePolicy.objects.all().order_by("category")
