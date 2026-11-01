from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.models import Holiday, LeaveAction, LeaveBalance, LeavePolicy, LeaveRequest, SlaConfig
from .serializers import BalanceSerializer, HolidaySerializer, LeaveRequestSerializer, PolicySerializer, SlaSerializer

MODULE=HasModuleGrant("employee_leave_management")
P_VIEW="elm.leave.view_self"; P_CREATE="elm.leave.create"; P_WITHDRAW="elm.leave.withdraw"; P_REVIEW="elm.leave.review"; P_ADMIN="elm.admin.manage"; P_RECORD="elm.admin.records"; P_OFFLINE="elm.admin.offline"
CATEGORIES={"CL":Decimal("8"),"RH":Decimal("2"),"SCL":Decimal("15"),"EL":Decimal("30"),"COL":Decimal("20"),"VL":Decimal("60")}
CONTINUOUS={"EL","COL","VL"}

def actor(request): return request.principal
def leave_days(category,start,end,half):
    if half != "full": return Decimal("0.5")
    n=(end-start).days+1
    if category in CONTINUOUS: return Decimal(n)
    return Decimal(n)
def ensure_balance(uid,year,cat):
    b,_=LeaveBalance.objects.get_or_create(user_id=uid,year=year,category=cat,defaults={"entitled":CATEGORIES[cat]})
    return b
def overlaps(req):
    return LeaveRequest.objects.filter(user_id=req.user_id,status__in=["awaiting_substitute_response","awaiting_unit_head_review","awaiting_establishment_verification","awaiting_final_sanction","approved"],start_date__lte=req.end_date,end_date__gte=req.start_date).exclude(pk=req.pk).exists()
def next_state(req):
    if req.category in ("CL","RH"): return "awaiting_unit_head_review"
    return "awaiting_unit_head_review"
def log(req,request,action,to_status,note=""):
    old=req.status; req.status=to_status; req.save(update_fields=["status","updated_at"]); LeaveAction.objects.create(request=req,actor_user_id=actor(request).user_id,action=action,from_status=old,to_status=to_status,note=note)

class LeaveListCreateView(APIView):
    permission_classes=[MODULE,HasPermission(P_VIEW,P_CREATE)]
    def get(self,request):
        qs=LeaveRequest.objects.filter(user_id=actor(request).user_id).prefetch_related("actions")
        return Response(LeaveRequestSerializer(qs,many=True).data)
    def post(self,request):
        if not actor(request).has_permission(P_CREATE): return Response({"detail":"Not permitted."},status=403)
        data=request.data.copy(); required=["category","start_date","end_date"]
        if any(not data.get(k) for k in required): return Response({"detail":"category, start_date and end_date are required."},status=400)
        if data["category"] not in CATEGORIES: return Response({"detail":"Unsupported leave category."},status=400)
        from datetime import date
        start=date.fromisoformat(data["start_date"]); end=date.fromisoformat(data["end_date"])
        if end<start: return Response({"detail":"End date cannot precede start date."},status=400)
        days=leave_days(data["category"],start,end,data.get("half","full"))
        with transaction.atomic():
            req=LeaveRequest.objects.create(user_id=actor(request).user_id,category=data["category"],start_date=start,end_date=end,half=data.get("half","full"),days=days,reason=data.get("reason","")[:10000],station_leave_details=data.get("station_leave_details","")[:10000],substitute_user_id=data.get("substitute_user_id"),medical_evidence=data.get("medical_evidence","")[:10000],status="draft")
            LeaveAction.objects.create(request=req,actor_user_id=actor(request).user_id,action="created",from_status="",to_status="draft")
        return Response(LeaveRequestSerializer(req).data,status=201)

class LeaveSubmitView(APIView):
    permission_classes=[MODULE,HasPermission(P_CREATE)]
    def post(self,request,pk):
        try:req=LeaveRequest.objects.get(pk=pk,user_id=actor(request).user_id)
        except LeaveRequest.DoesNotExist:return Response({"detail":"Leave request not found."},status=404)
        if req.status!="draft": return Response({"detail":"Only draft requests can be submitted."},status=409)
        bal=ensure_balance(req.user_id,req.start_date.year,req.category)
        if bal.available < req.days: return Response({"detail":"Insufficient leave balance."},status=400)
        if overlaps(req): return Response({"detail":"Leave period overlaps another pending or approved leave."},status=400)
        if req.category=="RH" and not Holiday.objects.filter(date=req.start_date,is_restricted=True,published=True).exists(): return Response({"detail":"RH date is not in the effective published RH calendar."},status=400)
        target="awaiting_substitute_response" if req.substitute_user_id else next_state(req)
        log(req,request,"submitted",target)
        return Response(LeaveRequestSerializer(req).data)

class LeaveWithdrawView(APIView):
    permission_classes=[MODULE,HasPermission(P_WITHDRAW)]
    def post(self,request,pk):
        try:req=LeaveRequest.objects.get(pk=pk,user_id=actor(request).user_id)
        except LeaveRequest.DoesNotExist:return Response({"detail":"Leave request not found."},status=404)
        if req.status in ("approved","rejected","cancelled","withdrawn"): return Response({"detail":"This request can no longer be withdrawn."},status=409)
        log(req,request,"withdrawn","withdrawn")
        return Response(LeaveRequestSerializer(req).data)

class ReviewListView(APIView):
    permission_classes=[MODULE,HasPermission(P_REVIEW)]
    def get(self,request):
        qs=LeaveRequest.objects.exclude(status__in=["draft","approved","rejected","withdrawn","cancelled","completed"]).order_by("created_at")
        return Response(LeaveRequestSerializer(qs,many=True).data)

class ReviewActionView(APIView):
    permission_classes=[MODULE,HasPermission(P_REVIEW)]
    def post(self,request,pk):
        try:req=LeaveRequest.objects.get(pk=pk)
        except LeaveRequest.DoesNotExist:return Response({"detail":"Leave request not found."},status=404)
        action=request.data.get("action")
        if action not in ("approve","reject","recommend","accept_substitute","decline_substitute"): return Response({"detail":"Unsupported review action."},status=400)
        if action=="accept_substitute": req.substitute_status="accepted"; req.save(update_fields=["substitute_status","updated_at"]); log(req,request,"substitute_accepted","awaiting_unit_head_review")
        elif action=="decline_substitute": req.substitute_status="declined"; req.save(update_fields=["substitute_status","updated_at"]); log(req,request,"substitute_declined","withdrawn")
        elif action=="recommend": log(req,request,"recommended","awaiting_final_sanction")
        elif action=="reject": req.decision="rejected"; req.decision_note=request.data.get("note",""); req.decided_at=timezone.now(); req.save(update_fields=["decision","decision_note","decided_at","updated_at"]); log(req,request,"rejected","rejected")
        else:
            req.decision="approved"; req.decision_note=request.data.get("note",""); req.decided_at=timezone.now(); req.save(update_fields=["decision","decision_note","decided_at","updated_at"]);
            bal=ensure_balance(req.user_id,req.start_date.year,req.category); bal.used += req.days; bal.save(update_fields=["used","updated_at"]); log(req,request,"approved","approved")
        return Response(LeaveRequestSerializer(req).data)

class BalancesView(APIView):
    permission_classes=[MODULE,HasPermission(P_VIEW)]
    def get(self,request):
        year=int(request.query_params.get("year",timezone.now().year)); rows=[ensure_balance(actor(request).user_id,year,c) for c in CATEGORIES]
        return Response(BalanceSerializer(rows,many=True).data)

class PolicyView(APIView):
    permission_classes=[MODULE,HasPermission(P_ADMIN)]
    def get(self,request):
        for c,v in CATEGORIES.items(): LeavePolicy.objects.get_or_create(category=c,defaults={"annual_entitlement":v,"carry_forward":c in {"EL","COL"},"half_day_allowed":c=="CL","continuous_days":c in CONTINUOUS})
        return Response(PolicySerializer(LeavePolicy.objects.all(),many=True).data)
    def put(self,request,pk):
        p=LeavePolicy.objects.get(pk=pk); s=PolicySerializer(p,data=request.data,partial=True); s.is_valid(raise_exception=True); s.save(); return Response(s.data)

class HolidayView(APIView):
    permission_classes=[MODULE,HasPermission(P_ADMIN)]
    def get(self,request): return Response(HolidaySerializer(Holiday.objects.all(),many=True).data)
    def post(self,request): s=HolidaySerializer(data=request.data); s.is_valid(raise_exception=True); return Response(HolidaySerializer(s.save()).data,status=201)

class SlaView(APIView):
    permission_classes=[MODULE,HasPermission(P_ADMIN)]
    def get(self,request): return Response(SlaSerializer(SlaConfig.objects.all(),many=True).data)
    def post(self,request): s=SlaSerializer(data=request.data); s.is_valid(raise_exception=True); return Response(SlaSerializer(s.save()).data,status=201)
