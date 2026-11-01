from rest_framework import serializers

from modules.gymkhana.models import Club, Membership


class ClubSerializer(serializers.ModelSerializer):
    class Meta:
        model = Club
        fields = ["id", "name", "category", "description", "status", "coordinator_user_id",
                  "co_coordinator_user_id", "faculty_councillor_user_id"]
        read_only_fields = ["status"]


class MembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Membership
        fields = ["id", "club", "user_id", "description", "status", "remarks"]
        read_only_fields = ["user_id", "status", "remarks"]
