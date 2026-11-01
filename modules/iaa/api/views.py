from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError
from fusion_auth.permissions import HasPermission
from modules.iaa import services
from modules.iaa.api.serializers import (
    AnomalyFlagSerializer, AnomalyResolveSerializer, AnomalySerializer,
    AuditObservationSerializer, AuditRaiseSerializer, AuditRespondSerializer,
    AuditReviewCloseSerializer, DecisionInputSerializer, ExpenseCreateSerializer,
    ExpenseVoucherRequestSerializer, ReviewInputSerializer, TAClaimCreateSerializer,
    TAClaimSerializer,
)
from modules.iaa.models import Anomaly, AuditObservation, ExpenseVoucherRequest, TAClaim


def _actor_id(request) -> int:
    """Id of the logged-in person, as recorded against this module's rows."""
    p = getattr(request, "principal", None)
    if p is None:
        raise NotFound("No authenticated principal on this request.")
    return p.user_id


def _get_or_404(model, pk):
    try:
        return model.objects.get(pk=pk)
    except model.DoesNotExist as exc:
        raise NotFound(f"{model.__name__} not found.") from exc


def _as_domain_error(exc):
    return BadRequestError(str(exc), code="invalid_iaa_request")


# ---- Expense / Voucher requests -------------------------------------------

class ExpenseRequestsView(APIView):
    """GET: the caller's own requests. POST: create a new draft."""

    def get_permissions(self):
        code = "iaa.request.create" if self.request.method == "POST" else "iaa.request.view"
        return [HasPermission(code)()]

    def get(self, request):
        rows = ExpenseVoucherRequest.objects.filter(
            creator_id=_actor_id(request)).order_by("-created_at")
        return Response({"results": ExpenseVoucherRequestSerializer(rows, many=True).data})

    def post(self, request):
        data = ExpenseCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        req = services.create_draft_expense(_actor_id(request), **data.validated_data)
        return Response(ExpenseVoucherRequestSerializer(req).data,
                        status=status.HTTP_201_CREATED)


class ExpenseSubmitView(APIView):
    permission_classes = [HasPermission("iaa.request.create")]

    def post(self, request, pk):
        _get_or_404(ExpenseVoucherRequest, pk)
        try:
            req = services.submit_expense(pk, _actor_id(request))
        except ValueError as exc:
            raise _as_domain_error(exc) from exc
        return Response(ExpenseVoucherRequestSerializer(req).data)


class ExpenseFinanceReviewView(APIView):
    """BR-004/BR-102: finance validates or raises a budget query."""

    permission_classes = [HasPermission("iaa.finance.review")]

    def post(self, request, pk):
        _get_or_404(ExpenseVoucherRequest, pk)
        data = ReviewInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        req = services.finance_review_expense(pk, _actor_id(request), **data.validated_data)
        return Response(ExpenseVoucherRequestSerializer(req).data)


class ExpenseQueryRespondView(APIView):
    permission_classes = [HasPermission("iaa.request.create")]

    def post(self, request, pk):
        _get_or_404(ExpenseVoucherRequest, pk)
        text = request.data.get("response_text", "")
        req = services.respond_query_expense(pk, _actor_id(request), text)
        return Response(ExpenseVoucherRequestSerializer(req).data)


class ExpenseDecideView(APIView):
    """BR-001/BR-002/BR-005: segregation of duties, multi-level routing, remarks required."""

    permission_classes = [HasPermission("iaa.approval.decide")]

    def post(self, request, pk):
        _get_or_404(ExpenseVoucherRequest, pk)
        data = DecisionInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            req = services.decide_expense(pk, _actor_id(request), **data.validated_data)
        except ValueError as exc:
            raise _as_domain_error(exc) from exc
        return Response(ExpenseVoucherRequestSerializer(req).data)


class ExpenseEscalateView(APIView):
    permission_classes = [HasPermission("iaa.approval.decide")]

    def post(self, request, pk):
        _get_or_404(ExpenseVoucherRequest, pk)
        next_authority_id = request.data.get("next_authority_id")
        req = services.escalate_overdue_expense(pk, next_authority_id)
        return Response(ExpenseVoucherRequestSerializer(req).data)


class ExpenseRecordView(APIView):
    """BR-006: internal record-keeping only — no payment is triggered."""

    permission_classes = [HasPermission("iaa.finance.review")]

    def post(self, request, pk):
        _get_or_404(ExpenseVoucherRequest, pk)
        try:
            req = services.process_record_expense(pk, _actor_id(request))
        except ValueError as exc:
            raise _as_domain_error(exc) from exc
        return Response(ExpenseVoucherRequestSerializer(req).data)


# ---- TA Claims --------------------------------------------------------------

class TAClaimsView(APIView):
    def get_permissions(self):
        code = "iaa.request.create" if self.request.method == "POST" else "iaa.request.view"
        return [HasPermission(code)()]

    def get(self, request):
        rows = TAClaim.objects.filter(
            employee_id=_actor_id(request)).order_by("-created_at")
        return Response({"results": TAClaimSerializer(rows, many=True).data})

    def post(self, request):
        data = TAClaimCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        claim = services.submit_ta_claim(_actor_id(request), **data.validated_data)
        return Response(TAClaimSerializer(claim).data, status=status.HTTP_201_CREATED)


class TAVerifyView(APIView):
    """BR-202: high-value claims are routed on to approval instead of direct verification."""

    permission_classes = [HasPermission("iaa.finance.review")]

    def post(self, request, pk):
        _get_or_404(TAClaim, pk)
        data = ReviewInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        claim = services.verify_ta_claim(pk, _actor_id(request), **data.validated_data)
        return Response(TAClaimSerializer(claim).data)


class TADecideView(APIView):
    permission_classes = [HasPermission("iaa.approval.decide")]

    def post(self, request, pk):
        _get_or_404(TAClaim, pk)
        data = DecisionInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            claim = services.decide_ta_claim(pk, _actor_id(request), **data.validated_data)
        except ValueError as exc:
            raise _as_domain_error(exc) from exc
        return Response(TAClaimSerializer(claim).data)


class TARecordView(APIView):
    permission_classes = [HasPermission("iaa.finance.review")]

    def post(self, request, pk):
        _get_or_404(TAClaim, pk)
        try:
            claim = services.process_record_ta_claim(pk, _actor_id(request))
        except ValueError as exc:
            raise _as_domain_error(exc) from exc
        return Response(TAClaimSerializer(claim).data)


# ---- Anomalies ---------------------------------------------------------------

class AnomaliesView(APIView):
    permission_classes = [HasPermission("iaa.anomaly.manage")]

    def get(self, request):
        rows = Anomaly.objects.order_by("-created_at")
        return Response({"results": AnomalySerializer(rows, many=True).data})

    def post(self, request):
        data = AnomalyFlagSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        anomaly = services.flag_anomaly(_actor_id(request), **data.validated_data)
        return Response(AnomalySerializer(anomaly).data, status=status.HTTP_201_CREATED)


class AnomalyResolveView(APIView):
    permission_classes = [HasPermission("iaa.anomaly.manage")]

    def post(self, request, pk):
        _get_or_404(Anomaly, pk)
        data = AnomalyResolveSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        anomaly = services.resolve_or_escalate_anomaly(pk, _actor_id(request),
                                                        **data.validated_data)
        return Response(AnomalySerializer(anomaly).data)


# ---- Audit observations ------------------------------------------------------

class AuditObservationsView(APIView):
    permission_classes = [HasPermission("iaa.audit.manage")]

    def get(self, request):
        rows = AuditObservation.objects.order_by("-created_at")
        return Response({"results": AuditObservationSerializer(rows, many=True).data})

    def post(self, request):
        data = AuditRaiseSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        obs = services.raise_audit_observation(_actor_id(request), **data.validated_data)
        return Response(AuditObservationSerializer(obs).data, status=status.HTTP_201_CREATED)


class AuditRespondView(APIView):
    """The audited party (not the auditor) answers the observation."""

    permission_classes = [HasPermission("iaa.request.create")]

    def post(self, request, pk):
        _get_or_404(AuditObservation, pk)
        data = AuditRespondSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        obs = services.respond_audit_observation(pk, _actor_id(request), **data.validated_data)
        return Response(AuditObservationSerializer(obs).data)


class AuditReviewCloseView(APIView):
    permission_classes = [HasPermission("iaa.audit.manage")]

    def post(self, request, pk):
        _get_or_404(AuditObservation, pk)
        data = AuditReviewCloseSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            obs = services.review_close_audit_observation(pk, _actor_id(request),
                                                           **data.validated_data)
        except ValueError as exc:
            raise _as_domain_error(exc) from exc
        return Response(AuditObservationSerializer(obs).data)
