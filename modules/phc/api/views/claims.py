from rest_framework import generics, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from core.api.permissions import HasPermission
from modules.phc.domain.reimbursement import (
    PENDING_PHC_REVIEW,
    PENDING_ACCOUNTS_VERIFICATION,
    PENDING_SANCTION,
    APPROVED_FOR_PAYMENT,
    REIMBURSED,
    REJECTED,
)
from modules.phc.models import ReimbursementClaim, ReimbursementPayment
from modules.phc.services.common import record_audit
from modules.phc.services.reimbursement import (
    create_claim,
    transition_claim,
    pay_claim,
)

class ClaimListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, HasPermission("phc.reimbursement.view", "filters claimant_user_id=request.user.user_id")]

    @extend_schema(
        description="List reimbursement claims for the authenticated user.",
        responses={200: ReimbursementClaim},
    )
    def get(self, request):
        claims = ReimbursementClaim.objects.filter(claimant_user_id=request.user.id)
        return Response(claims, status=status.HTTP_200_OK)

    @extend_schema(
        description="Create a new reimbursement claim.",
        responses={201: ReimbursementClaim},
    )
    def post(self, request):
        data = request.data
        claim = create_claim(
            claimant_user_id=request.user.id,
            claimant_kind=data.get("claimant_kind"),
            prescription_id=data.get("prescription_id"),
            expense_date=data.get("expense_date"),
            claimed_amount=data.get("claimed_amount"),
            description=data.get("description"),
        )
        return Response(claim, status=status.HTTP_201_CREATED)


class ClaimDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated, HasPermission("phc.reimbursement.view")]

    @extend_schema(
        description="Retrieve a reimbursement claim by ID.",
        responses={200: ReimbursementClaim},
    )
    def get(self, request, pk):
        try:
            claim = ReimbursementClaim.objects.get(id=pk)
            if claim.claimant_user_id != request.user.id:
                raise NotFound("Claim not found or owned by another user")
            return Response(claim, status=status.HTTP_200_OK)
        except ReimbursementClaim.DoesNotExist:
            raise NotFound("Claim not found")


class ClaimReviewQueueView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, HasPermission("phc.reimbursement.review")]

    @extend_schema(
        description="List claims pending PHC review.",
        responses={200: ReimbursementClaim},
    )
    def get(self, request):
        claims = ReimbursementClaim.objects.filter(status=PENDING_PHC_REVIEW)
        return Response(claims, status=status.HTTP_200_OK)


class ClaimReviewActionView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated, HasPermission("phc.reimbursement.review")]

    @extend_schema(
        description="Transition a claim to the next review stage.",
        responses={200: ReimbursementClaim},
    )
    def post(self, request, pk):
        action = request.data.get("action")
        claim = transition_claim(claim_id=pk, action=action, actor_user_id=request.user.id, actor_role="reviewer")
        return Response(claim, status=status.HTTP_200_OK)


class ClaimVerifyQueueView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, HasPermission("phc.reimbursement_audit.review")]

    @extend_schema(
        description="List claims pending accounts verification.",
        responses={200: ReimbursementClaim},
    )
    def get(self, request):
        claims = ReimbursementClaim.objects.filter(status=PENDING_ACCOUNTS_VERIFICATION)
        return Response(claims, status=status.HTTP_200_OK)


class ClaimVerifyActionView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated, HasPermission("phc.reimbursement_audit.review")]

    @extend_schema(
        description="Transition a claim to the next verification stage.",
        responses={200: ReimbursementClaim},
    )
    def post(self, request, pk):
        action = request.data.get("action")
        claim = transition_claim(claim_id=pk, action=action, actor_user_id=request.user.id, actor_role="verifier")
        return Response(claim, status=status.HTTP_200_OK)


class ClaimSanctionQueueView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, HasPermission("phc.reimbursement.approve")]

    @extend_schema(
        description="List claims pending sanction.",
        responses={200: ReimbursementClaim},
    )
    def get(self, request):
        claims = ReimbursementClaim.objects.filter(status=PENDING_SANCTION)
        return Response(claims, status=status.HTTP_200_OK)


class ClaimSanctionActionView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated, HasPermission("phc.reimbursement.approve")]

    @extend_schema(
        description="Transition a claim to the next sanction stage.",
        responses={200: ReimbursementClaim},
    )
    def post(self, request, pk):
        action = request.data.get("action")
        claim = transition_claim(claim_id=pk, action=action, actor_user_id=request.user.id, actor_role="sanctioner")
        return Response(claim, status=status.HTTP_200_OK)


class ClaimPaymentQueueView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, HasPermission("phc.reimbursement_payment.create")]

    @extend_schema(
        description="List claims pending payment.",
        responses={200: ReimbursementClaim},
    )
    def get(self, request):
        claims = ReimbursementClaim.objects.filter(status=APPROVED_FOR_PAYMENT)
        return Response(claims, status=status.HTTP_200_OK)


class ClaimPayActionView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated, HasPermission("phc.reimbursement_payment.create")]

    @extend_schema(
        description="Record payment for a claim.",
        responses={201: ReimbursementPayment},
    )
    def post(self, request, pk):
        data = request.data
        payment = pay_claim(claim_id=pk, actor_user_id=request.user.id, actor_role="payer", paid_on=data.get("paid_on"), reference=data.get("reference"))
        return Response(payment, status=status.HTTP_201_CREATED)
