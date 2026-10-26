from rest_framework import serializers
from modules.elm.models import Holiday, LeaveAction, LeaveBalance, LeavePolicy, LeaveRequest, SlaConfig

class PolicySerializer(serializers.ModelSerializer):
    class Meta:
        model=LeavePolicy; fields="__all__"
class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model=Holiday; fields="__all__"
class BalanceSerializer(serializers.ModelSerializer):
    available=serializers.SerializerMethodField()
    def get_available(self,obj): return str(obj.available)
    class Meta:
        model=LeaveBalance; fields=["id","year","category","entitled","used","carried_forward","available"]
class ActionSerializer(serializers.ModelSerializer):
    class Meta:
        model=LeaveAction; fields="__all__"
class LeaveRequestSerializer(serializers.ModelSerializer):
    actions=ActionSerializer(many=True,read_only=True)
    class Meta:
        model=LeaveRequest; fields="__all__"
        read_only_fields=["user_id","status","days","decision","decided_at","substitute_status"]
class SlaSerializer(serializers.ModelSerializer):
    class Meta:
        model=SlaConfig; fields="__all__"
