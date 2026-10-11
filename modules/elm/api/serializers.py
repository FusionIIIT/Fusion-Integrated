from rest_framework import serializers
from elm.models import Leave

class LeaveSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Leave
        fields = ['url', 'employee', 'category', 'start_date', 'end_date', 'reason', 'status']
