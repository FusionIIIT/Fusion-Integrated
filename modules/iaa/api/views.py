from rest_framework import generics, status
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.iaa.models import IAAExpenseRequest, IAAApproval, IAAAnomaly, IAAAuditObservation, IATravelClaim, IAAPolicy, IAAAuditEvent
from modules.iaa.api import serializers as s
from modules.iaa.services import workflows

MODULE = HasModuleGrant("internal_audit_accounts")
P_CREATE = "internal_audit_accounts.request.create"
P_VIEW = "internal_audit_accounts.request.view"
P_FINANCE = "internal_audit_accounts.finance.review"
P_APPROVE = "internal_audit_accounts.request.approve"
P_AUDIT = "internal_audit_accounts.audit.manage"
P_POLICY = "internal_audit_accounts.policy.manage"


def actor(request): return getattr(request, "principal", None)
def uid(request): return int(actor(request).user_id)

class ExpenseListCreateView(generics.ListCreateAPIView):
    permission_classes = [MODULE]
    def get_serializer_class(self):
        return s.ExpenseWriteSerializer if self.request.method == "POST" else s.ExpenseSerializer
    def get_queryset(self):
        p = actor(self.request)
        qs = IAAExpenseRequest.objects.all()
        if not (p.has_permission(P_VIEW) or p.has_permission(P_FINANCE) or p.has_permission(P_APPROVE)):
            qs = qs.filter(claimant_user_id=uid(self.request))
        return qs
    def create(self, request, *args, **kwargs):
        if not actor(request).has_permission(P_CREATE): return Response({"detail":"Permission denied."}, status=403)
        ser=s.ExpenseWriteSerializer(data=request.data); ser.is_valid(raise_exception=True)
        obj=ser.save(claimant_user_id=uid(request))
        workflows.audit(kind="expense",pk=obj.pk,action="created",actor=actor(request),after={"status":obj.status})
        return Response(s.ExpenseSerializer(obj).data,status=201)

class ExpenseDetailView(generics.RetrieveUpdateAPIView):
    permission_classes=[MODULE]
    serializer_class=s.ExpenseSerializer
    http_method_names=["get","patch","head","options"]
    def get_queryset(self):
        p=actor(self.request); qs=IAAExpenseRequest.objects.all()
        if not (p.has_permission(P_VIEW) or p.has_permission(P_FINANCE) or p.has_permission(P_APPROVE)):
            qs=qs.filter(claimant_user_id=uid(self.request))
        return qs
    def patch(self, request, *args, **kwargs):
        obj=self.get_object()
        if obj.claimant_user_id != uid(request) or obj.status != "draft": return Response({"detail":"Only the owner may edit a draft."},status=403)
        ser=s.ExpenseWriteSerializer(obj,data=request.data,partial=True); ser.is_valid(raise_exception=True); ser.save()
        return Response(s.ExpenseSerializer(obj).data)

class ExpenseSubmitView(APIView):
    permission_classes=[MODULE]
    def post(self,request,pk):
        obj=IAAExpenseRequest.objects.get(pk=pk)
        return Response(s.ExpenseSerializer(workflows.submit_expense(obj,actor(request))).data)

class ExpenseDecisionView(APIView):
    permission_classes=[MODULE,HasPermission(P_APPROVE)]
    def post(self,request,pk):
        obj=IAAExpenseRequest.objects.get(pk=pk); ser=s.DecisionSerializer(data=request.data); ser.is_valid(raise_exception=True)
        d=ser.validated_data
        obj=workflows.decide_expense(obj,actor(request),decision=d["decision"],remarks=d["remarks"],level=d["level"],role=d.get("role",""))
        return Response(s.ExpenseSerializer(obj).data)

class ApprovalHistoryView(generics.ListAPIView):
    permission_classes=[MODULE]
    serializer_class=s.ExpenseSerializer
    def get_queryset(self): return IAAExpenseRequest.objects.filter(pk=self.kwargs["pk"])
    def list(self,request,*args,**kwargs):
        obj=self.get_queryset().first()
        if not obj: return Response({"detail":"Not found."},status=404)
        p=actor(request)
        if obj.claimant_user_id != uid(request) and not (p.has_permission(P_VIEW) or p.has_permission(P_APPROVE) or p.has_permission(P_FINANCE)): return Response(status=404)
        return Response([{"level":a.level,"approver_user_id":a.approver_user_id,"role":a.approver_role,"decision":a.decision,"remarks":a.remarks,"decided_at":a.decided_at} for a in obj.approvals.all()])

class TravelListCreateView(generics.ListCreateAPIView):
    permission_classes=[MODULE]
    def get_serializer_class(self): return s.TravelWriteSerializer if self.request.method=="POST" else s.TravelSerializer
    def get_queryset(self):
        p=actor(self.request); qs=IATravelClaim.objects.all()
        if not p.has_permission(P_VIEW): qs=qs.filter(claimant_user_id=uid(self.request))
        return qs
    def create(self,request,*args,**kwargs):
        ser=s.TravelWriteSerializer(data=request.data); ser.is_valid(raise_exception=True)
        obj=ser.save(claimant_user_id=uid(request)); workflows.audit(kind="travel_claim",pk=obj.pk,action="created",actor=actor(request))
        return Response(s.TravelSerializer(obj).data,status=201)

class TravelSubmitView(APIView):
    permission_classes=[MODULE]
    def post(self,request,pk):
        obj=IATravelClaim.objects.get(pk=pk)
        return Response(s.TravelSerializer(workflows.submit_travel(obj,actor(request))).data)

class AnomalyListCreateView(generics.ListCreateAPIView):
    permission_classes=[MODULE,HasPermission(P_AUDIT)]
    serializer_class=s.AnomalySerializer
    def get_queryset(self): return IAAAnomaly.objects.all()
    def create(self,request,*args,**kwargs):
        ser=s.AnomalyWriteSerializer(data=request.data); ser.is_valid(raise_exception=True)
        obj=ser.save(raised_by_user_id=uid(request)); workflows.audit(kind="anomaly",pk=obj.pk,action="flagged",actor=actor(request))
        return Response(s.AnomalySerializer(obj).data,status=201)

class ObservationListCreateView(generics.ListCreateAPIView):
    permission_classes=[MODULE,HasPermission(P_AUDIT)]
    serializer_class=s.ObservationSerializer
    queryset=IAAAuditObservation.objects.all()
    def create(self,request,*args,**kwargs):
        ser=s.ObservationWriteSerializer(data=request.data); ser.is_valid(raise_exception=True)
        obj=ser.save(raised_by_user_id=uid(request)); workflows.audit(kind="audit_observation",pk=obj.pk,action="raised",actor=actor(request))
        return Response(s.ObservationSerializer(obj).data,status=201)

class PolicyListCreateView(generics.ListCreateAPIView):
    permission_classes=[MODULE,HasPermission(P_POLICY)]
    serializer_class=s.PolicySerializer
    queryset=IAAPolicy.objects.all()
    def perform_create(self,serializer): serializer.save(updated_by_user_id=uid(self.request))

class AuditEventsView(generics.ListAPIView):
    permission_classes=[MODULE,HasPermission(P_AUDIT)]
    def list(self,request,*args,**kwargs):
        qs=IAAAuditEvent.objects.all()[:500]
        return Response([{"aggregate_type":x.aggregate_type,"aggregate_id":x.aggregate_id,"action":x.action,"actor_user_id":x.actor_user_id,"actor_role":x.actor_role,"before":x.before,"after":x.after,"remarks":x.remarks,"occurred_at":x.occurred_at} for x in qs])
