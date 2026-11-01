from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from modules.rspc.models import ResearchProposal, ProposalDecision
from modules.rspc.api.serializers import ResearchProposalSerializer, ProposalDecisionSerializer
from fusion_auth.permissions import HasModuleGrant, HasPermission
from django.shortcuts import get_object_or_404

MODULE = HasModuleGrant("rspc")

class ResearchProposalView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.proposal.submit")]

    def post(self, request):
        data = request.data
        serializer = ResearchProposalSerializer(data=data)
        if serializer.is_valid():
            serializer.save(pi_id=request.user.user_id, status="submitted")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ResearchProposalMineView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.proposal.view_self")]

    def get(self, request):
        proposals = ResearchProposal.objects.filter(pi_id=request.user.user_id)
        serializer = ResearchProposalSerializer(proposals, many=True)
        return Response(serializer.data)

class ResearchProposalQueueView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.proposal.view_queue")]

    def get(self, request):
        if request.principal.has_permission("rspc.proposal.recommend"):
            status = "submitted"
        elif request.principal.has_permission("rspc.proposal.verify"):
            status = "dept_recommended"
        elif request.principal.has_permission("rspc.proposal.decide"):
            status = "admin_verified"
        elif request.principal.has_permission("rspc.proposal.authorize"):
            status = "forwarded_to_director"
        else:
            raise ValidationError("User does not have permission to view queue.")

        proposals = ResearchProposal.objects.filter(status=status)
        serializer = ResearchProposalSerializer(proposals, many=True)
        return Response(serializer.data)

class ProposalDecisionView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.proposal.recommend")]

    def post(self, request, proposal_id):
        proposal = get_object_or_404(ResearchProposal, pk=proposal_id)
        data = request.data
        outcome = data.get('outcome')
        remarks = data.get("remarks", "")

        if outcome not in ['recommended', 'not_recommended']:
            raise ValidationError("Invalid outcome. Must be 'recommended' or 'not_recommended'.")

        if proposal.status != "submitted":
            raise ValidationError("Proposal must be in 'submitted' status to recommend.")

        decision = ProposalDecision(proposal=proposal, stage="HoD", actor_id=request.user.user_id, outcome=outcome, remarks=remarks)
        decision.save()

        proposal.status = "dept_recommended" if outcome == "recommended" else "dept_not_recommended"
        proposal.save()

        return Response({'message': 'Proposal recommended successfully'}, status=status.HTTP_200_OK)

class ProposalVerifyView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.proposal.verify")]

    def post(self, request, proposal_id):
        proposal = get_object_or_404(ResearchProposal, pk=proposal_id)
        data = request.data
        outcome = data.get('outcome')
        remarks = data.get("remarks", "")

        if outcome not in ['eligible', 'not_eligible']:
            raise ValidationError("Invalid outcome. Must be 'eligible' or 'not_eligible'.")

        if proposal.status != "dept_recommended":
            raise ValidationError("Proposal must be in 'dept_recommended' status to verify.")

        decision = ProposalDecision(proposal=proposal, stage="RSPC Admin", actor_id=request.user.user_id, outcome=outcome, remarks=remarks)
        decision.save()

        proposal.status = "admin_verified" if outcome == "eligible" else "not_eligible"
        proposal.save()

        return Response({'message': 'Proposal verified successfully'}, status=status.HTTP_200_OK)

class ProposalDecideView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.proposal.decide")]

    def post(self, request, proposal_id):
        proposal = get_object_or_404(ResearchProposal, pk=proposal_id)
        data = request.data
        outcome = data.get('outcome')
        remarks = data.get("remarks", "")

        if outcome not in ['approve', 'forward', 'not_approve']:
            raise ValidationError("Invalid outcome. Must be 'approve', 'forward', or 'not_approve'.")

        if proposal.status == "admin_verified":
            if outcome == "approve":
                proposal.status = "approved"
                proposal.save()
                decision = ProposalDecision(proposal=proposal, stage="Dean-RSPC", actor_id=request.user.user_id, outcome=outcome, remarks=remarks)
                decision.save()
            elif outcome == "forward":
                proposal.status = "forwarded_to_director"
                proposal.save()
                decision = ProposalDecision(proposal=proposal, stage="Dean-RSPC", actor_id=request.user.user_id, outcome=outcome, remarks=remarks)
                decision.save()
            elif outcome == "not_approve":
                proposal.status = "dean_not_approved"
                proposal.save()
                decision = ProposalDecision(proposal=proposal, stage="Dean-RSPC", actor_id=request.user.user_id, outcome=outcome, remarks=remarks)
                decision.save()
            else:
                raise ValidationError("Proposal must be in 'admin_verified' status to decide.")
        else:
            raise ValidationError("Proposal status does not allow this action.")

        return Response({'message': 'Proposal decision made successfully'}, status=status.HTTP_200_OK)

class ProposalAuthorizeView(APIView):
    permission_classes = [MODULE, HasPermission("rspc.proposal.authorize")]

    def post(self, request, proposal_id):
        proposal = get_object_or_404(ResearchProposal, pk=proposal_id)
        data = request.data
        outcome = data.get('outcome')
        remarks = data.get("remarks", "")

        if outcome not in ['approve', 'not_approve']:
            raise ValidationError("Invalid outcome. Must be 'approve' or 'not_approve'.")

        if proposal.status == "forwarded_to_director":
            if outcome == "approve":
                proposal.status = "approved"
                proposal.save()
                decision = ProposalDecision(proposal=proposal, stage="Director", actor_id=request.user.user_id, outcome=outcome, remarks=remarks)
                decision.save()
            elif outcome == "not_approve":
                proposal.status = "director_not_approved"
                proposal.save()
                decision = ProposalDecision(proposal=proposal, stage="Director", actor_id=request.user.user_id, outcome=outcome, remarks=remarks)
                decision.save()
            else:
                raise ValidationError("Proposal must be in 'forwarded_to_director' status to authorize.")
        else:
            raise ValidationError("Proposal status does not allow this action.")

        return Response({'message': 'Proposal authorization made successfully'}, status=status.HTTP_200_OK)
