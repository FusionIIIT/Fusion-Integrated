from datetime import date

from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.elm.api.permissions import ScopedCollection
from modules.elm.api.serializers import CATEGORIES, ApplyInputSerializer, LeaveRequestSerializer
from modules.elm.models import LeaveRequest
from modules.elm.services.applications import submit_leave_request, withdraw_leave_request
from modules.elm.services.entitlements import get_balance


def _uid(request):
    return request.principal.user_id


def _gate(*codes):
    return [ScopedCollection(*codes)()]


class LeaveRequestListView(APIView):
    def get_permissions(self):
        code = "elm.leave.apply" if self.request.method == "POST" else "elm.leave.view_self"
        return _gate(code)

    def get(self, request):
        qs = LeaveRequest.objects.filter(applicant_user_id=_uid(request)).order_by("-id")
        return Response(LeaveRequestSerializer(qs, many=True).data)

    def post(self, request):
        data = ApplyInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        uid = _uid(request)
        result = submit_leave_request(applicant_user_id=uid, **data.validated_data)
        if not isinstance(result, LeaveRequest):
            result = LeaveRequest.objects.filter(applicant_user_id=uid).latest("id")
        return Response(LeaveRequestSerializer(result).data, status=201)


class LeaveRequestDetailView(APIView):
    def get_permissions(self):
        return _gate("elm.leave.view_self")

    def get(self, request, pk):
        obj = get_object_or_404(LeaveRequest, pk=pk, applicant_user_id=_uid(request))
        return Response(LeaveRequestSerializer(obj).data)


class LeaveRequestWithdrawView(APIView):
    def get_permissions(self):
        return _gate("elm.leave.withdraw")

    def post(self, request, pk):
        uid = _uid(request)
        obj = get_object_or_404(LeaveRequest, pk=pk, applicant_user_id=uid)
        withdraw_leave_request(obj.pk, uid)
        obj.refresh_from_db()
        return Response(LeaveRequestSerializer(obj).data)


class BalanceView(APIView):
    def get_permissions(self):
        return _gate("elm.leave.view_self")

    def get(self, request):
        raw = request.query_params.get("year")
        if raw is None:
            year = date.today().year
        else:
            try:
                year = int(raw)
            except ValueError:
                return Response({"detail": "year must be a whole number, for example 2026."},
                                status=400)
        uid = _uid(request)
        return Response([{"category": c, "amount": str(get_balance(uid, c, year))}
                         for c in CATEGORIES])
