from rest_framework import serializers

class LeaveRequestSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    category = serializers.ChoiceField(choices=["annual", "sick", "maternity"])
    reason = serializers.CharField()

class LeaveDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approved", "rejected"])
    comment = serializers.CharField(required=False)
