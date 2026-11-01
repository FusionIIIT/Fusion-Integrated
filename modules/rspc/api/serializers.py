from rest_framework import serializers
from modules.rspc.models import ResearchProposal, ProposalDecision

class ProposalDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProposalDecision
        fields = ['id', 'proposal', 'stage', 'actor_id', 'outcome', 'remarks', 'decided_at']
        read_only_fields = ['proposal', 'stage', 'actor_id', 'outcome', 'remarks', 'decided_at']

class ResearchProposalSerializer(serializers.ModelSerializer):
    decisions = ProposalDecisionSerializer(many=True, read_only=True)

    class Meta:
        model = ResearchProposal
        fields = ['id', 'title', 'objectives', 'start_date', 'end_date', 'budget', 'funding_agency', 'resource_requirements', 'department', 'pi_id', 'status', 'decisions']
        read_only_fields = ['pi_id', 'status']

    def validate(self, data):
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        budget = data.get('budget')

        if end_date and start_date and end_date < start_date:
            raise serializers.ValidationError("End date must be after start date.")

        if budget is not None and budget <= 0:
            raise serializers.ValidationError("Budget must be greater than zero.")

        return data
